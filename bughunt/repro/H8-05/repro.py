"""H8-05: POST /api/flowsheets/import-url answers 500 when a public host's redirect carries a Location
with a scheme and no host ('https:127.0.0.1/x', 'javascript:alert(1)').

Run from core/ with OPENFERMENT_DATABASE_URL naming a fresh bh_ test database (run.sh does this).
The app is driven in process through FastAPI's TestClient. The network is a stand-in: httpx's
AsyncHTTPTransport is replaced, in this process alone, by a MockTransport, and the collectors'
resolver by a stand-in that maps public.test to 93.184.216.34 (a public address). Nothing leaves
the machine: every request the fetch makes is answered by `handler` below and listed in the output.
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")
import httpx  # noqa: E402

PROJECT = "h8-05"
SEEN: list[str] = []
LOCATIONS = {
    "/to-http": "http://public.test/x",          # control: a redirect off https, refused 422 in words
    "/bad-location": "https:127.0.0.1/x",        # a scheme and no host
    "/js-location": "javascript:alert(1)",       # a scheme and no host
}


async def handler(request: httpx.Request) -> httpx.Response:
    SEEN.append(f"{request.url.host} Host={request.headers.get('host')} path={request.url.raw_path.decode()}")
    path = request.url.raw_path.decode()
    if path in LOCATIONS:
        return httpx.Response(302, headers={"location": LOCATIONS[path]})
    return httpx.Response(404)


httpx.AsyncHTTPTransport = lambda *a, **k: httpx.MockTransport(handler)  # type: ignore[misc]


def stand_in_resolver(host: str, port: int) -> list[str]:
    return ["93.184.216.34"] if host == "public.test" else []


from fastapi.testclient import TestClient  # noqa: E402

from openferment_core import api  # noqa: E402
from openferment_core.literature import collectors  # noqa: E402

assert not collectors.fixtures_only(), "OPENFERMENT_FIXTURES is set; the fetch would be refused before the network"
collectors._resolve = stand_in_resolver

client = TestClient(api.app, raise_server_exceptions=False, base_url="http://127.0.0.1")
made = client.post("/api/projects", json={"id": PROJECT, "name": PROJECT, "by": "h8-05"})
print(f"project {PROJECT}: POST /api/projects -> {made.status_code}")

answers: dict[str, tuple[int, str]] = {}
for path, location in LOCATIONS.items():
    url = f"https://public.test{path}"
    r = client.post("/api/flowsheets/import-url", json={"url": url, "by": "h8-05"},
                    headers={"X-OpenFerment-Project": PROJECT})
    answers[path] = (r.status_code, r.text)
    print(f"POST /api/flowsheets/import-url {url} (302 Location: {location!r}) -> {r.status_code} {r.text[:240]}")

print("requests the stand-in network answered:")
for line in SEEN:
    print("   ", line)

# The cause, one level down: fetch_file through its documented test seams (transport, resolve).
escaped, kinds = "nothing", ""
try:
    collectors.fetch_file("https://public.test/bad-location", limit=1 << 20,
                          transport=httpx.MockTransport(handler), resolve=stand_in_resolver)
    print("fetch_file(https://public.test/bad-location): returned")
except Exception as e:  # noqa: BLE001
    named = (collectors.AddressRefused, collectors.TooLarge, collectors.HostFailed, collectors.NetworkRefused)
    escaped = f"{type(e).__module__}.{type(e).__name__}"
    print(f"fetch_file(https://public.test/bad-location) raised {escaped}: {e}")
    kinds = (f"an httpx.HTTPError: {isinstance(e, httpx.HTTPError)}; one of the four refusals fetch_file documents "
             f"(AddressRefused, TooLarge, HostFailed, NetworkRefused): {isinstance(e, named)}")
    print("   " + kinds)

control = answers["/to-http"]
bad = {p: answers[p] for p in ("/bad-location", "/js-location")}


def in_words(status: int, text: str) -> bool:
    try:
        detail = json.loads(text).get("detail")
    except ValueError:
        return False
    return status in (422, 502) and isinstance(detail, str) and "public.test" in detail


print("EXPECTED: each redirect to a malformed Location ('https:127.0.0.1/x', 'javascript:alert(1)') answered "
      "502 (or 422) with words naming the address, as the control redirect to http:// is answered "
      f"(control: {control[0]} {control[1][:120]}); nothing kept")
print("OBSERVED: " + "; ".join(f"{p} -> {s} {t[:60]!r}" for p, (s, t) in bad.items())
      + f"; fetch_file raised {escaped} ({kinds})")
defect = in_words(*control) and any(not in_words(s, t) for s, t in bad.values())
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
