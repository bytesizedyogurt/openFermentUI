"""The MCP server through a running service (alpha 2.2 D.0; docs/TOOLS.md).

`--service <origin>` names a running openFerment service on loopback, and the
server sends every call there: a registry tool to `POST /api/tools/<name>`
with the arguments as the client sent them, the project in
X-OpenFerment-Project and the client's declared name in
X-OpenFerment-Assistant; `ask_postdoc` and `get_artifact` to the service's own
routes. An origin outside the loopback rule is refused in words, and so is
whatever the service refuses. The tool door reads the header and runs the
call in the model's lane under that name. The last test starts the real
server over stdio against the app served on a free loopback port, with no
database address in the server's environment. Every value here is a
placeholder.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp import Client
from mcp.types import Implementation

from openferment_core import api, audit, catalogues, db, mcp_server, projects, tools
from openferment_core.models import AnswerPlan, Artifact, ToolResult

CORE = Path(__file__).resolve().parent.parent
PROJECT = "test-project"
# The origin the stand-in transport answers for: nothing listens there.
ORIGIN = "http://127.0.0.1:9"
ENTRY = {"kind": "skill", "id": "example-test.skill", "name": "A placeholder skill", "note": "a placeholder entry"}
EXAMPLE = Implementation(name="example-test", version="0.1")


def _text(result) -> dict:
    return json.loads(result.content[0].text)


async def _call(server, name: str, arguments: dict, info: Implementation | None = EXAMPLE) -> dict:
    """One call through an in-memory MCP client that declares `info`."""
    async with Client(server, client_info=info) as client:
        return _text(await client.call_tool(name, arguments))


def _through(answer, project: str | None = PROJECT, origin: str = ORIGIN):
    """The server started with `--service origin`, sending to a stand-in
    service that answers with `answer`, and the requests that service saw."""
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answer(request)

    return mcp_server.build(project, origin, transport=httpx.MockTransport(handle)), seen


@pytest.fixture
def no_database(monkeypatch):
    """A store call in this test is a failure: the server through a service opens none."""
    def opened(*_args, **_kw):
        raise AssertionError("the server read a database")

    with monkeypatch.context() as patched:
        patched.setattr(db, "run", opened)
        patched.setattr(db, "arun", opened)
        yield


# ── the origin --service names ────────────────────────────────────────────


@pytest.mark.parametrize("given, origin", [
    ("http://127.0.0.1:8000", "http://127.0.0.1:8000"),
    ("https://localhost:8443", "https://127.0.0.1:8443"),
    ("http://localhost:8000", "http://127.0.0.1:8000"),
    ("http://[::1]:8000", "http://[::1]:8000"),
    ("HTTP://LOCALHOST:8000", "http://127.0.0.1:8000"),
    (" http://127.0.0.1:8000 ", "http://127.0.0.1:8000"),
])
def test_an_origin_on_loopback_with_its_port_is_taken(given, origin):
    """localhost is sent to 127.0.0.1, the address the service binds, so no
    resolver is asked where it is."""
    assert mcp_server.service_origin(given) == origin


@pytest.mark.parametrize("given, words", [
    ("", "names no address"),
    ("127.0.0.1:8000", "is no http:// or https:// address"),
    ("ftp://127.0.0.1:21", "is no http:// or https:// address"),
    ("http://example.com:8000", "names the host 'example.com'. The service binds loopback"),
    ("http://10.0.0.1:8000", "names the host '10.0.0.1'"),
    ("http://127.0.0.2:8000", "names the host '127.0.0.2'"),
    ("http://127.0.0.1", "names no port"),
    ("http://[::1]", "names no port"),
    ("http://127.0.0.1:0", "names no port"),
    ("http://127.0.0.1:70000", "is no address this server reads"),
    ("http://127.0.0.1:8000/", "holds more than an origin"),
    ("http://127.0.0.1:8000/api", "holds more than an origin"),
    ("http://127.0.0.1:8000?x=1", "holds more than an origin"),
    ("http://127.0.0.1:8000#top", "holds more than an origin"),
    ("http://127.0.0.1:80\t00", "holds more than an origin"),
    ("http://placeholder@127.0.0.1:8000", "names a user or a password"),
])
def test_an_origin_outside_the_rule_is_refused_in_words(given, words):
    with pytest.raises(mcp_server.ServiceRefused, match=re.escape(words)):
        mcp_server.service_origin(given)


@pytest.mark.parametrize("given", [
    "http://placeholder:not-a-secret@127.0.0.1:8000",
    "http://placeholder:not/a-secret@127.0.0.1:8000",
    "http://placeholder:not?a-secret@127.0.0.1:8000",
    "http://placeholder:not#a-secret@127.0.0.1:8000",
    "http://not-a-secret@example.com:8000",
])
def test_a_password_in_a_refused_origin_is_never_repeated(given):
    """However the password is written (a `/`, `?` or `#` in it among them),
    the refusal says a user or a password stands there and repeats nothing
    of the value: at the start, in the server's instructions, at every call."""
    with pytest.raises(mcp_server.ServiceRefused) as refused:
        mcp_server.service_origin(given)
    assert "secret" not in str(refused.value) and "names a user or a password" in str(refused.value)
    server, seen = _through(lambda r: httpx.Response(200, json={}), origin=given)
    assert "secret" not in (server.instructions or "") and "names a user or a password" in server.instructions
    assert "secret" not in _text(asyncio.run(server.call_tool("catalogue_read", {"kind": "skill"})))["error"]
    assert seen == []


def test_the_flags_are_read_either_way_they_are_written(monkeypatch):
    monkeypatch.setenv(projects.ENV, "from-the-environment")
    assert mcp_server.named_service(["--project", "p-1", "--service", ORIGIN]) == ORIGIN
    assert mcp_server.named_service([f"--service={ORIGIN}"]) == ORIGIN
    assert mcp_server.named_service(["--service"]) == "" == mcp_server.named_service(["--service", "--project", "p"])
    assert mcp_server.named_service(["--project", "p-1"]) is None
    assert mcp_server.named_project(["--project=p-3"]) == "p-3"
    assert mcp_server.named_project(["--project", "--service", ORIGIN]) == "from-the-environment"


def test_a_refused_origin_answers_every_call_with_its_words(no_database):
    refused, seen = _through(lambda r: httpx.Response(200, json={}), origin="http://example.com:8000")
    for name, args, field in (("catalogue_read", {"kind": "skill"}, "error"), ("ask_postdoc", {"question": "q?"}, "declined"),
                              ("get_artifact", {"id": "0123456789abcdef"}, "error")):
        assert "names the host 'example.com'" in _text(asyncio.run(refused.call_tool(name, args)))[field]
    blank, _ = _through(lambda r: httpx.Response(200, json={}), origin="")
    assert "--service names no address" in _text(asyncio.run(blank.call_tool("catalogue_read", {"kind": "skill"})))["error"]
    origin, words = mcp_server._blocked(None, "http://example.com:8000")
    assert origin is None and "example.com" in words and mcp_server.NO_PROJECT in words
    assert mcp_server._blocked(PROJECT, ORIGIN) == (ORIGIN, None)
    assert seen == [], "a refused origin is sent nothing"


def test_through_a_service_a_server_in_no_project_says_how_to_name_one(no_database, monkeypatch):
    monkeypatch.delenv(projects.ENV)
    server, seen = _through(lambda r: httpx.Response(200, json={}), project=None)
    assert _text(asyncio.run(server.call_tool("catalogue_read", {"kind": "skill"}))) == {"error": mcp_server.NO_PROJECT}
    assert seen == []


# ── every call sent to the service ────────────────────────────────────────


def test_a_tool_call_goes_to_the_service_as_the_client_sent_it(no_database):
    kept = ToolResult(summary={"state": "open", "kind": "skill", "id": ENTRY["id"], "by": "example-test/0.1"})
    server, seen = _through(lambda r: httpx.Response(200, json=json.loads(kept.model_dump_json())))
    arguments = {**ENTRY, "limit": 3, "nested": {"words": ["a", "b", "é"]}}
    assert asyncio.run(_call(server, "catalogue_write", arguments)) == json.loads(kept.model_dump_json(exclude_none=True))
    (request,) = seen
    assert (request.method, str(request.url)) == ("POST", f"{ORIGIN}/api/tools/catalogue_write")
    assert json.loads(request.content) == arguments and request.headers["content-type"] == "application/json"
    assert request.headers[projects.HEADER] == PROJECT
    assert request.headers[tools.ASSISTANT_HEADER] == "example-test/0.1"
    asyncio.run(_call(server, "catalogue_read", {"kind": "skill"}, info=None))
    assert seen[-1].headers[tools.ASSISTANT_HEADER] == mcp_server.AUTHOR, "the SDK's own name is no name"


def test_a_name_the_client_declares_reaches_the_service_as_utf8(no_database):
    server, seen = _through(lambda r: httpx.Response(200, json={}))
    asyncio.run(_call(server, "catalogue_read", {"kind": "skill"}, info=Implementation(name="agent-é", version="0.1")))
    sent = {name.lower(): value for name, value in seen[0].headers.raw}
    assert sent[tools.ASSISTANT_HEADER.lower().encode()] == "agent-é/0.1".encode("utf-8")


@pytest.mark.parametrize("answer, words", [
    (httpx.Response(404, json={"detail": "no project named 'test-project'"}), "no project named 'test-project'"),
    (httpx.Response(422, json={"detail": "catalogue_write keeps something in the project in its caller's name"}),
     "catalogue_write keeps something in the project in its caller's name"),
    (httpx.Response(422, json={"detail": [{"loc": ["body"], "msg": "Input should be a valid dictionary"}]}),
     "body: Input should be a valid dictionary"),
    (httpx.Response(503, text="the database did not answer"),
     f"the service at {ORIGIN} answered 503 Service Unavailable: the database did not answer"),
    (httpx.Response(200, text="no JSON here"), f"the service at {ORIGIN} answered no tool result"),
])
def test_what_the_service_refuses_comes_back_as_the_calls_error_in_words(no_database, answer, words):
    server, _ = _through(lambda r: answer)
    out = asyncio.run(_call(server, "catalogue_read", {"kind": "skill"}))
    assert set(out) == {"error"} and out["error"].startswith(words)


def test_a_redirect_the_service_answers_is_followed_nowhere(no_database):
    """A 307 to another origin comes back as the call's error in words, and
    nothing is sent to the address it names."""
    elsewhere = "http://127.0.0.1:10/api/tools/catalogue_read"
    server, seen = _through(lambda r: httpx.Response(307, headers={"location": elsewhere}, text="moved"))
    out = asyncio.run(_call(server, "catalogue_read", {"kind": "skill"}))
    assert out == {"error": f"the service at {ORIGIN} answered 307 Temporary Redirect: moved"}
    assert [str(r.url) for r in seen] == [f"{ORIGIN}/api/tools/catalogue_read"]


def test_a_call_waits_for_the_longest_tool_and_an_ask_for_postdocs_whole_loop(no_database):
    from openferment_core import postdoc_agent

    assert mcp_server.ASK_SECONDS == postdoc_agent.MAX_SECONDS, "the ask's wait follows Postdoc's wall time"
    server, seen = _through(lambda r: httpx.Response(200, json={"question": "q?"} if r.url.path == "/api/ask" else {}))
    asyncio.run(_call(server, "catalogue_read", {"kind": "skill"}))
    asyncio.run(_call(server, "ask_postdoc", {"question": "q?"}))
    tool, ask = (r.extensions["timeout"] for r in seen)
    assert (tool["read"], ask["read"]) == (mcp_server.SERVICE_TIMEOUT_S, mcp_server.ASK_TIMEOUT_S)
    assert tool["connect"] == ask["connect"] == mcp_server.CONNECT_TIMEOUT_S
    assert mcp_server.ASK_TIMEOUT_S > mcp_server.SERVICE_TIMEOUT_S


def test_through_a_service_the_server_writes_no_line_a_request_of_its_own(no_database):
    import logging

    said = logging.getLogger("httpx")
    was = said.level
    try:
        said.setLevel(logging.INFO)
        _through(lambda r: httpx.Response(200, json={}))
        assert said.level == logging.WARNING, "httpx's INFO line a request is said nowhere"
    finally:
        said.setLevel(was)


def test_a_service_that_does_not_answer_is_said_in_words(no_database):
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("[Errno 111] Connection refused", request=request)

    server, _ = _through(down)
    said = f"the service at {ORIGIN} did not answer: [Errno 111] Connection refused"
    assert asyncio.run(_call(server, "catalogue_read", {"kind": "skill"})) == {"error": said}
    assert asyncio.run(_call(server, "ask_postdoc", {"question": "Which records?"}))["declined"] == \
        f"Postdoc could not run: {said}"
    assert asyncio.run(_call(server, "get_artifact", {"id": "0123456789abcdef"})) == {"error": said}


def test_ask_postdoc_and_get_artifact_go_to_the_services_own_routes(no_database):
    plan = AnswerPlan(question="Which records name a placeholder?", gaps=["a placeholder gap"])
    kept = Artifact(id="0123456789abcdef", tool="example.tool", toolVersion="0", inputs=[], output={"words": "a"},
                    outputHash="0" * 64, provenance="computed", createdAt="2026-11-04T00:00:00Z", durationMs=1)

    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/ask":
            return httpx.Response(200, json=json.loads(plan.model_dump_json()))
        if request.url.path == f"/api/biorepo/artifacts/{kept.id}":
            return httpx.Response(200, json=json.loads(kept.model_dump_json()))
        return httpx.Response(404, json={"detail": f"no artifact {request.url.path.rsplit('/', 1)[-1]!r}"})

    server, seen = _through(answer)
    answered = asyncio.run(_call(server, "ask_postdoc", {"question": plan.question}))
    assert answered == json.loads(plan.model_dump_json(exclude_none=True)) and "declined" not in answered, \
        "null fields left out: an answer holds no declined"
    asked = seen[-1]
    assert (asked.method, asked.url.path, asked.headers[projects.HEADER]) == ("POST", "/api/ask", PROJECT)
    assert json.loads(asked.content) == {"question": plan.question, "by": "example-test/0.1"}
    assert asyncio.run(_call(server, "get_artifact", {"id": kept.id})) == json.loads(kept.model_dump_json(exclude_none=True))
    assert (seen[-1].method, seen[-1].url.path, seen[-1].headers[projects.HEADER]) == (
        "GET", f"/api/biorepo/artifacts/{kept.id}", PROJECT)
    sent = len(seen)
    for given in ("..", ".", "", "../tools/catalogue_write", "0123456789ABCDEF", "0123456789abcdef0"):
        missing = asyncio.run(_call(server, "get_artifact", {"id": given}))
        assert missing == {"error": f"no readable artifact {given!r}: an artifact's id is sixteen hex digits, as a "
                                    "tool's result names it (an artifactId), so nothing was read"}, given
    assert len(seen) == sent, "an id of no artifact's shape is sent nowhere, a dot segment among them"
    refused = _through(lambda r: httpx.Response(422, json={"detail": "the loop cannot run"}))[0]
    assert asyncio.run(_call(refused, "ask_postdoc", {"question": "q?"}))["declined"] == \
        "Postdoc could not run: the loop cannot run"


def test_in_its_own_process_a_database_it_cannot_read_is_said_in_whole_sentences(monkeypatch):
    def unread(coroutine, *_args, **_kw):
        coroutine.close()
        raise db.DatabaseUnavailable("OPENFERMENT_DATABASE_URL names no database.")

    monkeypatch.setattr(db, "run", unread)
    said = _text(asyncio.run(mcp_server.build(PROJECT).call_tool("catalogue_read", {"kind": "skill"})))["error"]
    assert said == ("This openFerment server could not read its database: DatabaseUnavailable: "
                    "OPENFERMENT_DATABASE_URL names no database. Start it with --service <origin> to act through a "
                    "running service.")


def test_through_a_service_the_server_reads_the_project_alone_from_core_env(monkeypatch):
    held = {db.URL_SETTING: "postgresql://placeholder@127.0.0.1:5432/placeholder", projects.ENV: "from-the-file"}
    read: list[object] = []

    def values(path):
        read.append(path)
        return dict(held)

    monkeypatch.setattr(mcp_server, "dotenv_values", values)
    monkeypatch.delenv(db.URL_SETTING, raising=False)
    monkeypatch.delenv(projects.ENV, raising=False)
    mcp_server._settings(service=True, project_named=True)
    assert read == [] and projects.ENV not in os.environ, "with --project named, core/.env is read for nothing"
    mcp_server._settings(service=True, project_named=False)
    assert os.environ[projects.ENV] == "from-the-file" and db.URL_SETTING not in os.environ
    mcp_server._settings()
    assert os.environ[db.URL_SETTING] == held[db.URL_SETTING], "in its own process it reads the address too"


# ── the tool door's assistant ─────────────────────────────────────────────


def test_the_tool_door_runs_a_named_assistant_in_the_models_lane():
    client = TestClient(api.app)
    kept = client.post("/api/tools/catalogue_write", json=ENTRY, headers={tools.ASSISTANT_HEADER: "example-test/0.1"})
    assert kept.status_code == 200 and kept.json()["error"] is None, kept.text
    summary = kept.json()["summary"]
    assert (summary["by"], summary["agent"], summary["via"], summary["note"], summary["state"]) == (
        "example-test/0.1", "model", "http", ENTRY["note"], "open"), "the entry as kept, its own note among it"
    assert summary["source"] == "example-test/0.1, at the HTTP endpoint" and summary["at"].endswith("+00:00")
    entry = catalogues.get("skill", ENTRY["id"])
    assert (entry.by, entry.agent, entry.via, entry.source) == (
        "example-test/0.1", "model", "http", "example-test/0.1, at the HTTP endpoint")
    (line,) = [a for a in audit.read() if a.target == f"skill/{ENTRY['id']}"]
    assert (line.agent, line.who, line.module, line.action, line.state, line.effort, line.askId) == (
        "model", "example-test/0.1", "guild", "catalogue_write", "open", None, None)
    assert line.detail == {"tool": "catalogue_write", "kind": "skill", "note": ENTRY["note"], "via": "http"}
    assert kept.json()["auditIds"] == [line.id], "the write's answer names its audit row"
    rows = client.get("/api/audit").json()
    assert [(r["id"], r["agent"], r["who"], r["detail"]["via"]) for r in rows
            if r.get("target") == f"skill/{ENTRY['id']}"] == [(line.id, "model", "example-test/0.1", "http")]


def test_an_assistant_at_the_door_leaves_postdocs_entries_as_they_are():
    """An assistant that declares Postdoc's model id is no Postdoc: an entry
    Postdoc kept stays as it is, refused in words naming who kept it, and its
    audit rows tell the two apart by their door."""
    postdoc = tools.ToolContext(model="claude-placeholder-model")
    assert tools.run("catalogue_write", ENTRY, postdoc).error is None
    taken = TestClient(api.app).post("/api/tools/catalogue_write", json={**ENTRY, "name": "Taken over"},
                                     headers={tools.ASSISTANT_HEADER: "claude-placeholder-model"}).json()
    assert taken["error"].startswith(f"catalogue_write refused: the project's skill catalogue holds {ENTRY['id']}, "
                                     "kept by claude-placeholder-model in Postdoc's name"), taken["error"]
    entry = catalogues.get("skill", ENTRY["id"])
    assert (entry.name, entry.via, entry.source) == (ENTRY["name"], "postdoc", "Postdoc (claude-placeholder-model)")
    (line,) = [a for a in audit.read() if a.action == "catalogue_write"]
    assert line.detail["via"] == "postdoc" and line.effort, "Postdoc's row names its door and its model's effort"
    over_mcp = tools.ToolContext(model="claude-placeholder-model", via="mcp")
    assert "in Postdoc's name" in tools.run("catalogue_write", {**ENTRY, "name": "Taken"}, over_mcp).error


def test_a_person_named_with_by_is_read_as_the_door_reads_a_name():
    """?by= drops control and format characters as the header does, so an
    audit row reads one name whichever way the caller is named."""
    client = TestClient(api.app)
    made = client.post("/api/tools/catalogue_write", params={"by": "Ada\nMoreno\u202e"}, json=ENTRY)
    assert made.status_code == 200 and made.json()["error"] is None, made.text
    (line,) = [a for a in audit.read() if a.action == "catalogue_write"]
    assert (line.agent, line.who) == ("person", "Ada Moreno") and "via" not in line.detail
    assert catalogues.get("skill", ENTRY["id"]).by == "Ada Moreno"
    keep = client.post("/api/catalogues/skill", json={"entry": {"kind": "skill", "id": "example-test.other",
                                                                "name": "Another"}, "by": "Grace\tHopper\u200b"})
    assert keep.status_code == 200 and (keep.json()["by"], keep.json()["agent"]) == ("Grace Hopper", "person")


def test_a_number_an_assistant_types_at_the_door_is_its_estimate(monkeypatch):
    from openferment_core.engine import library, simulator
    from test_tools_study import Priced, dearer_cane

    monkeypatch.setattr(simulator, "call", Priced())
    monkeypatch.setattr(library, "_PARAMETERS", {})
    made = TestClient(api.app).post("/api/tools/study_scenario", json=dearer_cane(),
                                    headers={tools.ASSISTANT_HEADER: "example-test/0.1"}).json()
    assert made["error"] is None, made["error"]
    (value,) = made["summary"]["values"]
    assert (value["origin"], value["by"]) == ("model-estimate", "example-test/0.1")


def test_the_door_refuses_a_caller_named_twice_or_named_nobody():
    client = TestClient(api.app)
    both = client.post("/api/tools/catalogue_write", params={"by": "Ada Moreno"}, json=ENTRY,
                       headers={tools.ASSISTANT_HEADER: "example-test/0.1"})
    assert both.status_code == 422 and "names its caller twice" in both.json()["detail"]
    assert "'Ada Moreno' (?by=)" in both.json()["detail"] and "'example-test/0.1'" in both.json()["detail"]
    nobody = client.post("/api/tools/catalogue_write", json=ENTRY)
    assert nobody.status_code == 422 and "this call names nobody" in nobody.json()["detail"]
    assert "?by=<their name>" in nobody.json()["detail"] and tools.ASSISTANT_HEADER in nobody.json()["detail"]
    blank = client.post("/api/tools/catalogue_write", json=ENTRY, headers={tools.ASSISTANT_HEADER: "\x01"})
    assert blank.status_code == 422 and f"{tools.ASSISTANT_HEADER} names nobody" in blank.json()["detail"]
    assert catalogues.listed("skill") == [] and audit.read() == [], "a refused call runs nothing"
    read = client.post("/api/tools/catalogue_read", json={"kind": "skill"}, headers={tools.ASSISTANT_HEADER: "x/1"})
    assert read.status_code == 200 and read.json()["error"] is None


def test_an_assistants_name_is_read_as_utf8_text_and_held_to_its_rule():
    name = "agent-é/0.1"
    kept = TestClient(api.app).post("/api/tools/catalogue_write", json=ENTRY,
                                    headers={tools.ASSISTANT_HEADER: name.encode("utf-8")})
    assert kept.json()["summary"]["by"] == name
    assert tools.caller_name("  a\x00b \t c\n") == "ab c"
    assert tools.caller_name("agent‮1.0/x​") == "agent1.0/x", "a bidi override or a zero width is no name"
    assert tools.caller_name("agent-\ud800/0.1") == "agent-/0.1", "a surrogate is no text UTF-8 holds"
    assert len(tools.caller_name("n" * 500)) == tools.MAX_CALLER


# ── the real server over stdio, through a real service ────────────────────


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def service():
    """The app served on a free loopback port by uvicorn in a thread of this
    process, so its requests act on the test's own database transaction."""
    import uvicorn

    catalogues.listed("skill")  # the test's database made, and its project written, before the service is asked
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=port, log_level="warning",
                                           log_config=None, lifespan="off"))
    thread = threading.Thread(target=server.run, name="test-service", daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started:
        assert thread.is_alive() and time.monotonic() < deadline, "the service did not start"
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(15)


def test_the_server_started_with_service_writes_through_it_and_the_audit_names_the_client(service, tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = {**os.environ, db.URL_SETTING: ""}
    env.pop(projects.ENV, None)
    params = StdioServerParameters(command=sys.executable, cwd=str(CORE), env=env, args=[
        "-m", "openferment_core.mcp_server", "--project", PROJECT, "--service", service])

    async def go(errlog):
        async with stdio_client(params, errlog=errlog) as (read, write), \
                ClientSession(read, write, client_info=EXAMPLE) as session:
            started = await session.initialize()
            listed = await session.list_tools()
            wrote = await session.call_tool("catalogue_write", ENTRY)
            records = await session.call_tool("biorepo_read", {"ids": [], "words": "", "kind": "record", "state": "",
                                                               "limit": 5})
            return started, listed, wrote, records

    said = tmp_path / "server-stderr.txt"
    with said.open("w", encoding="utf-8") as errlog:
        started, listed, wrote, records = asyncio.run(asyncio.wait_for(go(errlog), timeout=120))
    assert service in (started.instructions or "") and PROJECT in (started.instructions or "")
    assert len(listed.tools) == len(tools.WHITELIST) + len(mcp_server.EXTRA)
    kept = _text(wrote)
    assert "error" not in kept, kept
    assert (kept["summary"]["id"], kept["summary"]["by"]) == (ENTRY["id"], "example-test/0.1")
    assert "error" not in _text(records) and _text(records)["summary"]["count"] == 0
    assert "HTTP Request" not in said.read_text(encoding="utf-8"), "a forwarded request writes no line of its own"
    named = {projects.HEADER: PROJECT}
    asked = {"action": "catalogue_write", "target": f"skill/{ENTRY['id']}", "who": "example-test/0.1"}
    rows = httpx.get(f"{service}/api/audit", headers=named, params=asked, trust_env=False).json()
    (row,) = rows
    assert [row["id"]] == kept["auditIds"], "the write's answer over MCP names the row the service serves"
    assert (row["agent"], row["who"], row["action"], row["module"], row["detail"]["via"]) == (
        "model", "example-test/0.1", "catalogue_write", "guild", "http")
    assert "effort" not in row and "askId" not in row, "the HTTP audit leaves its null fields out, as MCP does"
    entry = httpx.get(f"{service}/api/catalogues/skill/{ENTRY['id']}", headers=named, trust_env=False).json()
    assert (entry["by"], entry["agent"], entry["via"], entry["source"]) == (
        "example-test/0.1", "model", "http", "example-test/0.1, at the HTTP endpoint")
