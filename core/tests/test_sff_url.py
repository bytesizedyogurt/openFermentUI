"""An SFF file imported by its https address (alpha 2.2 D10, and its
amendment at C.6; docs/api/sff.md, A file by its address), offline.

The network is a STAND-IN: an httpx.MockTransport answers every request the
fetch makes as a host would, and keeps each one, so a test can say what was
asked, of which address, how often and with which headers; nothing leaves
this machine. The system's resolver is a STAND-IN too: every name resolves to
PUBLIC, a public address no test dials, unless the test says otherwise. The
toolkit's verdicts come from test_sff's stand-in for the Proforma worker's SFF
ops, and the file is test_sff's small plant.
"""
from __future__ import annotations

import hashlib
import re
import socket
import threading
import time
from collections.abc import AsyncIterator, Callable

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient

from openferment_core.api import app
from openferment_core.engine import sff, simulator
from openferment_core.literature import collectors
from openferment_core.workers import WorkerCrashed

from test_sff import PROJECT, StandInToolkit, as_bytes, corpus, small_doc, toolkit  # noqa: F401

ADDRESS = "https://flowsheets.example.org/plants/small.sff.json"
MIRROR = "https://mirror.example.org/plants/small.sff.json"
JSON = {"content-type": "application/json"}
#: Public addresses the stand-in resolver answers with. No test dials them:
#: the stand-in network answers in their place.
PUBLIC = "93.184.216.34"
PUBLIC_V6 = "2606:2800:220:1:248:1893:25c8:1946"

Answer = httpx.Response | Callable[[httpx.Request], object]


class Host:
    """A STAND-IN for the hosts the test's addresses name and for the
    resolver that finds them. Each address answers what the test set for it,
    in order, and every request is kept with the address it was sent to; a
    response answers one request, and a function making one, last in its
    address's list, answers every later request. Each name resolves to what
    the test set for it (a list of addresses, or a function giving one), and
    to PUBLIC otherwise."""

    def __init__(self) -> None:
        self.answers: dict[str, list[Answer]] = {}
        self.asked: list[httpx.Request] = []
        self.addresses: dict[str, list[str] | Callable[[], list[str]]] = {}
        self.resolved: list[tuple[str, int]] = []

    def answer(self, url: str, *answers: Answer) -> None:
        self.answers[url] = list(answers)

    def resolve(self, name: str, port: int) -> list[str]:
        self.resolved.append((name, port))
        said = self.addresses.get(name, [PUBLIC])
        return said() if callable(said) else list(said)

    @staticmethod
    def named(request: httpx.Request) -> str:
        """The address a request asked for, its host the name the fetch checked."""
        return str(request.url.copy_with(host=request.extensions.get("sni_hostname", request.url.host)))

    def __call__(self, request: httpx.Request):
        self.asked.append(request)
        queue = self.answers.get(self.named(request)) or []
        if not queue:
            raise AssertionError(f"the stand-in host was asked for {self.named(request)}, which the test set no "
                                 "answer for")
        said = queue[0]
        if isinstance(said, httpx.Response) or len(queue) > 1:
            queue.pop(0)
        return said if isinstance(said, httpx.Response) else said(request)

    def urls(self) -> list[str]:
        return [self.named(r) for r in self.asked]

    def dialled(self) -> list[str]:
        """The address each request was sent to."""
        return [r.url.host for r in self.asked]


@pytest.fixture
def host(monkeypatch) -> Host:
    """The stand-in host and resolver, reached by every fetch by address in
    the test: the route's (`collectors.fetch_file`, read at call time) and a
    direct call alike. The throttle is counted and waits for nothing."""
    stand_in = Host()
    real = collectors.fetch_file
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "0")
    monkeypatch.setattr(collectors, "MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(collectors, "fetch_file",
                        lambda url, *, limit, transport=None, resolve=None: real(
                            url, limit=limit, transport=transport or httpx.MockTransport(stand_in),
                            resolve=resolve or stand_in.resolve))
    return stand_in


@pytest.fixture
def throttled(monkeypatch) -> list[float]:
    """Each time the collectors' throttle is passed, as it is called."""
    passed: list[float] = []
    real = collectors._throttle

    def counted() -> None:
        passed.append(time.monotonic())
        real()

    monkeypatch.setattr(collectors, "_throttle", counted)
    return passed


def fetch(url: str = ADDRESS, limit: int = sff.MAX_FILE) -> collectors.Fetched:
    return collectors.fetch_file(url, limit=limit)


def served(data: bytes) -> Callable[[httpx.Request], httpx.Response]:
    """The file, served as JSON to every request that asks for it."""
    return lambda request: httpx.Response(200, content=data, headers=JSON)


# ── the fetch, with the collectors' manners ─────────────────────────────


def test_a_file_is_fetched_with_the_collectors_manners(host, throttled, monkeypatch):
    monkeypatch.setenv("OPENFERMENT_CONTACT", "a.reader@example.org")
    data = as_bytes(small_doc())
    host.answer(ADDRESS, served(data))
    got = fetch()
    assert (got.data, got.url, got.served, got.kind) == (data, ADDRESS, ADDRESS, "application/json")
    [asked] = host.asked
    assert asked.method == "GET" and asked.headers["user-agent"] == collectors._user_agent()
    assert "a.reader@example.org" in asked.headers["user-agent"], "the User-Agent names somebody to write to"
    timeouts = asked.extensions["timeout"]
    assert timeouts["connect"] == timeouts["read"] == collectors.TIMEOUT_S, "connecting and each read are held to the " \
                                                                            "collectors' timeout"
    assert len(throttled) == 1, "every request passes the throttle"


def test_the_request_goes_to_the_address_its_host_was_checked_as(host):
    host.answer(ADDRESS, served(as_bytes(small_doc())))
    fetch()
    [asked] = host.asked
    assert host.resolved == [("flowsheets.example.org", 443)], "the host is resolved once, before connecting"
    assert asked.url.host == PUBLIC, "the request is sent to the checked address by its digits"
    assert asked.headers["host"] == "flowsheets.example.org", "the host is asked for by its name"
    assert asked.extensions["sni_hostname"] == "flowsheets.example.org", "TLS names the host and checks its certificate"

    host.asked.clear()
    host.resolved.clear()
    port = "https://flowsheets.example.org:8443/plants/small.sff.json"
    host.answer(port, served(as_bytes(small_doc())))
    fetch(port)
    assert host.resolved == [("flowsheets.example.org", 8443)] and host.asked[0].url.port == 8443
    assert host.asked[0].headers["host"] == "flowsheets.example.org:8443"


def test_a_name_that_resolves_elsewhere_on_a_second_lookup_is_sent_where_it_was_checked(host):
    lookups = iter([[PUBLIC], ["127.0.0.1"]])
    host.addresses["flowsheets.example.org"] = lambda: next(lookups)
    data = as_bytes(small_doc())
    host.answer(ADDRESS, httpx.Response(503), served(data))
    assert fetch().data == data
    assert host.dialled() == [PUBLIC, PUBLIC], "the retry goes to the address checked, with no second lookup"
    assert len(host.resolved) == 1


def test_each_address_a_host_resolves_to_is_tried_in_order_until_one_connects(host):
    other = "93.184.216.35"
    host.addresses["flowsheets.example.org"] = [PUBLIC_V6, other]
    data = as_bytes(small_doc())

    def v6_unreachable(request: httpx.Request) -> httpx.Response:
        if request.url.host == PUBLIC_V6:
            raise httpx.ConnectError("Network is unreachable", request=request)
        return httpx.Response(200, content=data, headers=JSON)

    host.answer(ADDRESS, v6_unreachable)
    assert fetch().data == data and host.dialled() == [PUBLIC_V6, other]


@pytest.mark.parametrize(("url", "said"), [
    ("http://flowsheets.example.org/plants/small.sff.json", "is not an https address"),
    ("ftp://flowsheets.example.org/small.sff.json", "is not an https address"),
    ("flowsheets.example.org/small.sff.json", "is not an https address"),
    ("https:///small.sff.json", "is not an https address"),
    ("   ", "an empty address is not an https address"),
    ("https://reader:secret@flowsheets.example.org/small.sff.json", "names a user or a password"),
])
def test_an_address_that_is_not_https_is_refused_before_anything_is_asked(host, url, said):
    with pytest.raises(collectors.AddressRefused, match=said):
        fetch(url)
    assert host.asked == [] and host.resolved == []


def test_the_password_in_a_refused_address_is_never_repeated(host):
    with pytest.raises(collectors.AddressRefused) as refused:
        fetch("https://reader:secret@flowsheets.example.org/small.sff.json")
    assert "secret" not in str(refused.value) and "flowsheets.example.org" in str(refused.value)


def test_fixture_mode_refuses_the_network_as_the_collectors_do(host, monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    with pytest.raises(collectors.NetworkRefused, match=f"OPENFERMENT_FIXTURES is set; refusing to GET {ADDRESS}"):
        fetch()
    assert host.asked == [] and host.resolved == []


# ── a public address alone (D10's amendment at C.6) ──────────────────────

#: An address of each class a fetch by address refuses, IPv4 and IPv6, by the
#: words the refusal names it with.
REFUSED = [
    ("127.0.0.1", "a loopback address"),
    ("::1", "a loopback address"),
    ("10.0.0.5", "a private address"),
    ("172.16.0.1", "a private address"),
    ("192.168.1.10", "a private address"),
    ("fd12:3456::1", "a private address"),
    ("fec0::1", "a private address"),
    ("169.254.169.254", "a link-local address"),
    ("fe80::1", "a link-local address"),
    ("224.0.0.1", "a multicast address"),
    ("ff02::1", "a multicast address"),
    ("240.0.0.1", "a reserved address"),
    ("4000::1", "a reserved address"),
    ("0.0.0.0", "the unspecified address"),
    ("::", "the unspecified address"),
    ("100.64.0.1", "an address outside the public internet"),
    ("::ffff:127.0.0.1", "a loopback address"),
    ("::ffff:10.0.0.5", "a private address"),
]


def _bracketed(address: str) -> str:
    return f"[{address}]" if ":" in address else address


@pytest.mark.parametrize(("address", "said"), REFUSED)
def test_an_address_outside_the_public_internet_is_refused_before_connecting(host, address, said):
    with pytest.raises(collectors.AddressRefused, match=re.escape(f"{address} is {said}; a file is fetched from a "
                                                                  "public address alone")):
        fetch(f"https://{_bracketed(address)}/plants/small.sff.json")
    assert host.asked == [] and host.resolved == [], "an address named by its digits is read, never resolved"


@pytest.mark.parametrize(("address", "said"), REFUSED)
def test_a_name_that_resolves_outside_the_public_internet_is_refused_before_connecting(host, address, said):
    host.addresses["flowsheets.example.org"] = [address]
    with pytest.raises(collectors.AddressRefused, match=re.escape(f"flowsheets.example.org resolves to {address}; "
                                                                  f"{address} is {said}")):
        fetch()
    assert host.asked == [] and host.resolved == [("flowsheets.example.org", 443)]


def test_a_name_that_resolves_to_a_public_and_a_private_address_is_refused(host):
    host.addresses["flowsheets.example.org"] = [PUBLIC, "192.168.1.10"]
    with pytest.raises(collectors.AddressRefused, match=re.escape(
            f"flowsheets.example.org resolves to {PUBLIC}, 192.168.1.10; 192.168.1.10 is a private address")):
        fetch()
    assert host.asked == []


@pytest.mark.parametrize("host_said", ["127.1", "2130706433", "0x7f000001", "0x7f.1"])
def test_an_address_in_a_short_or_numeric_form_is_read_as_the_system_reads_it(host, host_said):
    with pytest.raises(collectors.AddressRefused, match=re.escape(f"{host_said} reads as 127.0.0.1, a loopback "
                                                                  "address")):
        fetch(f"https://{host_said}:8443/plants/small.sff.json")
    assert host.asked == [] and host.resolved == []


def test_a_name_localhost_and_a_scoped_link_local_address_are_refused(host):
    host.addresses["localhost"] = ["127.0.0.1", "::1"]
    with pytest.raises(collectors.AddressRefused, match="localhost resolves to 127.0.0.1, ::1; 127.0.0.1 is a loopback"):
        fetch("https://localhost/plants/small.sff.json")
    host.addresses["printer.example.org"] = ["fe80::1%eth0"]
    with pytest.raises(collectors.AddressRefused, match="is a link-local address"):
        fetch("https://printer.example.org/x.json")
    assert host.asked == []


def test_a_public_address_named_by_its_digits_is_fetched(host):
    data = as_bytes(small_doc())
    for url in (f"https://{PUBLIC}/plants/small.sff.json", f"https://[{PUBLIC_V6}]/plants/small.sff.json"):
        host.answer(url, served(data))
        assert fetch(url).data == data
    assert host.dialled() == [PUBLIC, PUBLIC_V6] and host.resolved == []


def test_a_redirect_to_an_address_outside_the_public_internet_is_refused_before_it_is_asked(host):
    host.answer(ADDRESS, httpx.Response(302, headers={"Location": "https://192.168.1.10/plants/small.sff.json"}))
    with pytest.raises(collectors.AddressRefused, match=re.escape(
            f"{ADDRESS} redirected to https://192.168.1.10/plants/small.sff.json: 192.168.1.10 is a private "
            "address; a file is fetched from a public address alone")):
        fetch()
    assert host.urls() == [ADDRESS], "the private address is never asked"

    host.asked.clear()
    host.addresses["intranet.example.org"] = ["10.0.0.5"]
    host.answer(ADDRESS, httpx.Response(307, headers={"Location": "https://intranet.example.org/x.json"}))
    with pytest.raises(collectors.AddressRefused, match="redirected to https://intranet.example.org/x.json: "
                                                         "intranet.example.org resolves to 10.0.0.5"):
        fetch()
    assert host.urls() == [ADDRESS]


def test_a_redirect_is_resolved_again_so_a_name_that_moves_inside_is_refused(host):
    lookups = iter([[PUBLIC], ["127.0.0.1"]])
    host.addresses["flowsheets.example.org"] = lambda: next(lookups)
    moved = "https://flowsheets.example.org/moved/small.sff.json"
    host.answer(ADDRESS, httpx.Response(301, headers={"Location": "/moved/small.sff.json"}))
    with pytest.raises(collectors.AddressRefused, match=f"redirected to {moved}: flowsheets.example.org resolves to "
                                                         "127.0.0.1; 127.0.0.1 is a loopback address"):
        fetch()
    assert host.urls() == [ADDRESS] and len(host.resolved) == 2, "each redirect's host is resolved before it is asked"


def test_a_name_the_resolver_cannot_find_is_said_in_words(host):
    def unknown() -> list[str]:
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    host.addresses["flowsheets.example.org"] = unknown
    with pytest.raises(collectors.HostFailed, match="the host name flowsheets.example.org could not be found"):
        fetch()
    host.addresses["flowsheets.example.org"] = []
    with pytest.raises(collectors.HostFailed, match="resolves to no address"):
        fetch()
    assert host.asked == []


# ── redirects, sizes and time ───────────────────────────────────────────


def test_a_redirect_is_followed_to_another_https_address_alone(host, throttled):
    data = as_bytes(small_doc())
    host.answer(ADDRESS, httpx.Response(302, headers={"Location": MIRROR}))
    host.answer(MIRROR, served(data))
    got = fetch()
    assert (got.url, got.served, got.data) == (ADDRESS, MIRROR, data)
    assert host.urls() == [ADDRESS, MIRROR] and len(throttled) == 2, "each request passes the throttle"
    assert [n for n, _ in host.resolved] == ["flowsheets.example.org", "mirror.example.org"]

    relative = "https://flowsheets.example.org/moved/small.sff.json"
    host.answer(ADDRESS, httpx.Response(301, headers={"Location": "/moved/small.sff.json"}))
    host.answer(relative, served(data))
    assert fetch().served == relative, "a relative redirect is read against the address that gave it"

    host.asked.clear()
    host.answer(ADDRESS, httpx.Response(302, headers={"Location": "http://flowsheets.example.org/small.sff.json"}))
    with pytest.raises(collectors.AddressRefused, match="redirected to http://flowsheets.example.org/small.sff.json, "
                                                         "which is not an https address"):
        fetch()
    assert host.urls() == [ADDRESS], "the http address is never asked"

    host.asked.clear()
    host.answer(ADDRESS, httpx.Response(302, headers={"Location": "https://reader:secret@mirror.example.org/x.json"}))
    with pytest.raises(collectors.AddressRefused, match=r"names a user or a password \(mirror.example.org\)") as named:
        fetch()
    assert "secret" not in str(named.value) and host.urls() == [ADDRESS], "the address naming a password is never asked"


def test_an_address_that_redirects_without_end_is_said_in_words(host):
    host.answer(ADDRESS, lambda request: httpx.Response(307, headers={"Location": ADDRESS}))
    with pytest.raises(collectors.HostFailed, match=f"redirected more than {collectors.MAX_REDIRECTS} times"):
        fetch()
    assert len(host.asked) == collectors.MAX_REDIRECTS + 1


async def chunks(n: int, size: int, yielded: list[int]) -> AsyncIterator[bytes]:
    for _ in range(n):
        yielded.append(size)
        yield b" " * size


def test_a_body_past_the_size_is_refused_as_it_streams_before_the_rest_is_read(host):
    yielded: list[int] = []
    host.answer(ADDRESS, httpx.Response(200, content=chunks(1000, 4, yielded), headers=JSON))
    with pytest.raises(collectors.TooLarge, match="larger than the 10 bytes an import takes"):
        fetch(limit=10)
    assert sum(yielded) == 12, "the stream is left once it passes the size"

    async def unread() -> AsyncIterator[bytes]:
        raise AssertionError("the body of a file whose stated length is past the size was read")
        yield b""

    host.answer(ADDRESS, httpx.Response(200, content=unread(), headers={**JSON, "Content-Length": str(17 * 2**20)}))
    with pytest.raises(collectors.TooLarge, match=f"is {17 * 2**20} bytes, larger than the 16 MB an import takes"):
        fetch()


def test_a_file_that_takes_too_long_to_arrive_is_said_in_words(host, monkeypatch):
    monkeypatch.setattr(collectors, "FILE_TIMEOUT_S", 0.2)

    async def slow() -> AsyncIterator[bytes]:
        for _ in range(100):
            await anyio.sleep(0.06)
            yield b" "

    host.answer(ADDRESS, httpx.Response(200, content=slow(), headers=JSON))
    started = time.monotonic()
    with pytest.raises(collectors.HostFailed, match="did not serve the whole file within 0.2 s"):
        fetch()
    assert time.monotonic() - started < 1.5, "the file is left at the deadline"


def test_a_host_that_holds_back_its_headers_is_left_at_the_deadline(host, monkeypatch):
    monkeypatch.setattr(collectors, "FILE_TIMEOUT_S", 0.3)

    async def late(request: httpx.Request) -> httpx.Response:
        await anyio.sleep(30)
        return httpx.Response(200, content=as_bytes(small_doc()), headers=JSON)

    host.answer(ADDRESS, late)
    started = time.monotonic()
    with pytest.raises(collectors.HostFailed, match=f"{re.escape(ADDRESS)} did not serve the whole file within 0.3 s"):
        fetch()
    assert time.monotonic() - started < 1.5, "the whole exchange, its headers included, is held to the deadline"


def test_a_resolver_that_does_not_answer_is_left_at_the_deadline(host, monkeypatch):
    monkeypatch.setattr(collectors, "FILE_TIMEOUT_S", 0.3)
    released = threading.Event()

    def stuck() -> list[str]:
        released.wait(10)
        return [PUBLIC]

    host.addresses["flowsheets.example.org"] = stuck
    started = time.monotonic()
    try:
        with pytest.raises(collectors.HostFailed, match="did not serve the whole file within 0.3 s"):
            fetch()
        assert time.monotonic() - started < 1.5, "the resolution is held to the deadline too"
    finally:
        released.set()
    assert host.asked == []


def test_a_host_that_fails_or_answers_an_error_is_said_in_words(host):
    host.answer(ADDRESS, httpx.Response(404))
    with pytest.raises(collectors.HostFailed, match=f"{ADDRESS} answered 404 Not Found"):
        fetch()
    assert len(host.asked) == 1, "a 4xx is the host's answer, asked once"

    host.asked.clear()
    host.answer(ADDRESS, httpx.Response(503), httpx.Response(503))
    with pytest.raises(collectors.HostFailed, match="answered 503 Service Unavailable"):
        fetch()
    assert len(host.asked) == 2, "a 5xx is asked again once"

    host.asked.clear()
    data = as_bytes(small_doc())
    host.answer(ADDRESS, httpx.Response(502), served(data))
    assert fetch().data == data and len(host.asked) == 2, "a 5xx that the retry outlives is the file"

    def raising(error: type[httpx.HTTPError], words: str) -> Callable[[httpx.Request], httpx.Response]:
        def answer(request: httpx.Request) -> httpx.Response:
            raise error(words, request=request)

        return answer

    for error, words, said in [
        (httpx.ConnectError, "[Errno 111] Connection refused", "the host refused the connection"),
        (httpx.ConnectError, "[Errno 113] No route to host", "the host could not be reached"),
        (httpx.ConnectError, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed", "the host's certificate "
                                                                                           "could not be verified"),
        (httpx.ConnectTimeout, "timed out", f"the host did not answer within {collectors.TIMEOUT_S:g} s"),
    ]:
        host.answer(ADDRESS, raising(error, words))
        with pytest.raises(collectors.HostFailed) as failed:
            fetch()
        assert str(failed.value) == f"{ADDRESS} could not be fetched: {said}", "said in a person's words"

    async def stalls() -> AsyncIterator[bytes]:
        yield b"{"
        raise httpx.ReadTimeout("the read timed out")

    host.answer(ADDRESS, lambda request: httpx.Response(200, content=stalls(), headers=JSON))
    with pytest.raises(collectors.HostFailed, match=f"could not be fetched: the host sent nothing for "
                                                     f"{collectors.TIMEOUT_S:g} s"):
        fetch()


# ── the record ─────────────────────────────────────────────────────────


def test_a_fetched_file_is_kept_with_its_address_and_its_hash(toolkit, host):  # noqa: F811
    data = as_bytes(small_doc())
    host.answer(ADDRESS, served(data))
    got = fetch()
    record = sff.import_url(got.url, got.data, served=got.served, kind=got.kind, project_id=PROJECT, by="A. Reader")
    assert toolkit.ops() == ["sff_validate", "sff_score"], "checked in the worker as an uploaded file is"
    assert (record.origin, record.url, record.source) == ("imported", ADDRESS, f"the file at {ADDRESS}, imported")
    assert record.sha256 == hashlib.sha256(data).hexdigest() and record.bytes == len(data)
    assert record.id == f"sff-{record.sha256[:16]}" and record.title == "Corn stover → Ethanol"
    assert record.createdBy == "A. Reader" and len(record.graph.nodes) == 4
    assert sff.document(record.id, project_id=PROJECT).encode("utf-8") == data, "the file is held byte for byte"
    assert sff.get(record.id, project_id=PROJECT).model_dump() == record.model_dump()


def test_a_file_served_after_a_redirect_names_both_addresses_and_one_naming_no_title_its_path(toolkit, host):  # noqa: F811
    doc = small_doc()
    doc["metadata"] = {"sff_version": "0.2.4"}
    data = as_bytes(doc)
    host.answer(ADDRESS, httpx.Response(302, headers={"Location": MIRROR}))
    host.answer(MIRROR, served(data))
    got = fetch()
    record = sff.import_url(got.url, got.data, served=got.served, kind=got.kind, project_id=PROJECT, by="A. Reader")
    assert record.source == f"the file at {ADDRESS}, served from {MIRROR}, imported" and record.url == ADDRESS
    assert record.title == "small.sff", "a file naming no title is called by the last part of its address"


def test_the_same_address_and_bytes_twice_is_one_record(toolkit, host):  # noqa: F811
    data = as_bytes(small_doc())
    host.answer(ADDRESS, served(data))
    first = sff.import_url(ADDRESS, fetch().data, project_id=PROJECT, by="A. Reader")
    again = sff.import_url(ADDRESS, fetch().data, project_id=PROJECT, by="B. Reader")
    assert again.model_dump() == first.model_dump() and toolkit.ops() == ["sff_validate", "sff_score"]
    assert [r.id for r in sff.listed(project_id=PROJECT)] == [first.id]
    uploaded = sff.import_sff(data, "small.sff.json", project_id=PROJECT, by="C. Reader")
    assert uploaded.model_dump() == first.model_dump(), "the same file by another door is the record already held"


def test_two_imports_of_one_file_in_flight_together_keep_the_first_record_whole(monkeypatch):
    """Both imports find no record held before either writes (the stand-in
    toolkit holds each check until both have begun), so the second write
    meets the first's row: it keeps that row whole and answers with it."""
    toolkit = StandInToolkit()
    both_checking = threading.Barrier(2, timeout=10)

    def checks(op: str, args: dict):
        if op == "sff_validate":
            both_checking.wait()
        return toolkit(op, args)

    monkeypatch.setattr(simulator, "call", checks)
    data = as_bytes(small_doc())
    answers: dict[str, object] = {}

    def keep(who: str, url: str) -> None:
        try:
            answers[who] = sff.import_url(url, data, project_id=PROJECT, by=who)
        except Exception as e:  # said to the test below
            answers[who] = e

    threads = [threading.Thread(target=keep, args=("A. Reader", "https://a.example.org/race.sff.json")),
               threading.Thread(target=keep, args=("B. Reader", "https://b.example.org/race.sff.json"))]
    for th in threads:
        th.start()
    for th in threads:
        th.join(30)
    a, b = answers["A. Reader"], answers["B. Reader"]
    assert isinstance(a, sff.SFFFlowsheet) and isinstance(b, sff.SFFFlowsheet), answers
    assert toolkit.ops().count("sff_validate") == 2, "each import checked the file before either was kept"
    held = sff.get(a.id, project_id=PROJECT)
    assert a.model_dump() == b.model_dump() == held.model_dump(), "both imports answer with the one record kept"
    assert held.createdBy in ("A. Reader", "B. Reader")
    assert held.url == {"A. Reader": "https://a.example.org/race.sff.json",
                        "B. Reader": "https://b.example.org/race.sff.json"}[held.createdBy], \
        "the record's address and its maker are one import's"
    assert [r.id for r in sff.listed(project_id=PROJECT)] == [a.id]


def test_a_fetched_file_that_is_a_reference_flowsheet_keeps_its_address_beside_the_librarys_words(toolkit, corpus):  # noqa: F811
    record = sff.import_url(ADDRESS, corpus["data"], served=MIRROR, project_id=PROJECT, by="A. Reader")
    assert (record.origin, record.libraryId, record.url) == ("library", "SF_BST_99", ADDRESS)
    assert record.source.startswith("the PISCES SFF reference flowsheet SF_BST_99")
    assert record.source.endswith(f", fetched from {ADDRESS}, served from {MIRROR}"), record.source


def test_what_an_address_serves_that_is_no_sff_file_is_refused_in_a_persons_words(toolkit):  # noqa: F811
    with pytest.raises(sff.SFFRefused) as page:
        sff.import_url(ADDRESS, b"<!doctype html><title>A page</title>", kind="text/html", project_id=PROJECT,
                       by="A. Reader")
    assert str(page.value) == (f"the file at {ADDRESS} is not an SFF file: the address served an HTML page (text/html), "
                               "and an SFF file is JSON")
    with pytest.raises(sff.SFFRefused, match="is not JSON: its text stops reading as JSON at line 1, column 2$"):
        sff.import_url(ADDRESS, b"{not json", kind="application/json", project_id=PROJECT, by="A. Reader")
    with pytest.raises(sff.SFFRefused, match=r"is not an SFF flowsheet: an SFF file is a JSON object .*streams$"):
        sff.import_url(ADDRESS, b"[1, 2]", kind="text/plain", project_id=PROJECT, by="A. Reader")
    assert toolkit.calls == [] and sff.listed(project_id=PROJECT) == []


# ── the route ──────────────────────────────────────────────────────────


def test_the_route_fetches_checks_and_keeps_a_file_by_its_address(toolkit, host):  # noqa: F811
    client = TestClient(app)
    data = as_bytes(small_doc())
    host.answer(ADDRESS, served(data))
    made = client.post("/api/flowsheets/import-url", json={"url": ADDRESS, "by": "A. Reader"})
    assert made.status_code == 200, made.text
    body = made.json()
    assert (body["origin"], body["url"], body["source"]) == ("imported", ADDRESS, f"the file at {ADDRESS}, imported")
    assert body["sha256"] == hashlib.sha256(data).hexdigest() and body["createdBy"] == "A. Reader"
    assert [r["id"] for r in client.get("/api/flowsheets").json()] == [body["id"]]
    assert client.get(f"/api/flowsheets/{body['id']}/file").content == data

    again = client.post("/api/flowsheets/import-url", json={"url": ADDRESS, "by": "B. Reader"})
    assert again.status_code == 200 and again.json() == body, "the same address and bytes twice is one record"
    assert len(client.get("/api/flowsheets").json()) == 1 and toolkit.ops() == ["sff_validate", "sff_score"]
    assert len(host.asked) == 2, "each import fetches the address once"
    assert host.dialled() == [PUBLIC, PUBLIC], "the route's fetch goes to the checked address"


def _stalls(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectTimeout("timed out", request=request)


@pytest.mark.parametrize(("answers", "url", "status", "said"), [
    ([], "http://flowsheets.example.org/small.sff.json", 422, "is not an https address"),
    ([], "https://127.0.0.1:8443/small.sff.json", 422, "127.0.0.1 is a loopback address; a file is fetched from a "
                                                       "public address alone"),
    ([], "https://169.254.169.254/latest/meta-data/", 422, "is a link-local address"),
    ([httpx.Response(302, headers={"Location": "http://flowsheets.example.org/x.json"})], ADDRESS, 422,
     "which is not an https address; a redirect is followed to another https address alone"),
    ([httpx.Response(302, headers={"Location": "https://10.0.0.5/x.json"})], ADDRESS, 422,
     "redirected to https://10.0.0.5/x.json: 10.0.0.5 is a private address"),
    ([httpx.Response(200, content=b"{}", headers={**JSON, "Content-Length": str(sff.MAX_FILE + 1)})], ADDRESS, 413,
     "larger than the 16 MB an import takes"),
    ([httpx.Response(200, content=b"<!doctype html>", headers={"content-type": "text/html; charset=utf-8"})], ADDRESS,
     422, "is not an SFF file: the address served an HTML page \\(text/html\\), and an SFF file is JSON"),
    ([httpx.Response(200, content=b'{"units": []}', headers=JSON)], ADDRESS, 422, "is not an SFF flowsheet"),
    ([httpx.Response(404)], ADDRESS, 502, "answered 404 Not Found"),
    ([httpx.Response(500), httpx.Response(500)], ADDRESS, 502, "answered 500 Internal Server Error"),
    ([_stalls], ADDRESS, 502, "could not be fetched: the host did not answer within 20 s"),
])
def test_the_route_says_each_refusal_in_words_and_keeps_nothing(toolkit, host, answers, url, status, said):  # noqa: F811
    if answers:
        host.answer(url, *answers)
    client = TestClient(app)
    refused = client.post("/api/flowsheets/import-url", json={"url": url, "by": "A. Reader"})
    assert refused.status_code == status, refused.text
    assert re.search(said, refused.json()["detail"]), refused.json()["detail"]
    assert client.get("/api/flowsheets").json() == [] and toolkit.calls == []


def test_the_route_says_a_host_name_it_cannot_find_is_a_host_failure(toolkit, host):  # noqa: F811
    def unknown() -> list[str]:
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    host.addresses["flowsheets.example.org"] = unknown
    refused = TestClient(app).post("/api/flowsheets/import-url", json={"url": ADDRESS, "by": "A. Reader"})
    assert refused.status_code == 502 and refused.json()["detail"] == ("the host name flowsheets.example.org could "
                                                                        "not be found")
    assert host.asked == [] and toolkit.calls == []


def test_the_route_refuses_in_fixture_mode_as_the_collectors_do(toolkit, host, monkeypatch):  # noqa: F811
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    refused = TestClient(app).post("/api/flowsheets/import-url", json={"url": ADDRESS, "by": "A. Reader"})
    assert refused.status_code == 422 and refused.json()["detail"] == f"OPENFERMENT_FIXTURES is set; refusing to GET {ADDRESS}"
    assert host.asked == [] and toolkit.calls == []


def test_the_route_says_when_the_worker_could_not_check_the_file(host, monkeypatch):
    def crashed(op: str, args: dict):
        raise WorkerCrashed("the worker ended")

    monkeypatch.setattr(simulator, "call", crashed)
    host.answer(ADDRESS, served(as_bytes(small_doc())))
    client = TestClient(app)
    refused = client.post("/api/flowsheets/import-url", json={"url": ADDRESS, "by": "A. Reader"})
    assert refused.status_code == 503
    assert refused.json()["detail"] == f"the Proforma simulator could not check the file at {ADDRESS}: the worker ended"
    assert client.get("/api/flowsheets").json() == []


def test_the_route_names_who_keeps_the_file_and_declares_its_refusals(host):
    nameless = TestClient(app).post("/api/flowsheets/import-url", json={"url": ADDRESS})
    assert nameless.status_code == 422 and host.asked == []
    operation = app.openapi()["paths"]["/api/flowsheets/import-url"]["post"]
    assert {"200", "413", "422", "502", "503"} <= set(operation["responses"])
    assert operation["x-openferment-scope"] == "project"
