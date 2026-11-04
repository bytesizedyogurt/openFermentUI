"""openFerment's tools for assistants outside the app (OF-BLD-014 §10.1).

An MCP server over stdio. It lists every tool in the registry under the
registry's own name, description and input schema, and adds the two E.6
names: `ask_postdoc(question)`, which runs Postdoc's loop and returns the
plan, and `get_artifact(id)`. Every registry call goes through `tools.run`
with the arguments exactly as the client sent them, so the registry's rules
hold here as at the HTTP endpoint and inside the loop: a number in an input
is refused, and a refusal comes back as the tool's error.

No tool here writes to BioRepo, to Guild's ledger or to any store a person
signs.

`.mcp.json` at the repository root starts it:

    uv run --project core --all-extras python -m openferment_core.mcp_server [--project <id>] [--service <origin>]

IT ACTS IN ONE PROJECT (ADR-005; execution prompt §7.3 item 4): the one
`--project` names, else OPENFERMENT_PROJECT. A server started in none answers
every call with the words to start it in one.

IT REACHES THE PROJECT ONE OF TWO WAYS (alpha 2.2 D.0).

- Through a running openFerment service, `--service <origin>`. Every registry
  call is `POST <origin>/api/tools/<name>` with the arguments as the client
  sent them, the project in X-OpenFerment-Project and the client's name in
  X-OpenFerment-Assistant, and the service runs it through `tools.run` in the
  model's lane under that name, as this process would; `ask_postdoc` is
  `POST <origin>/api/ask` and `get_artifact` is
  `GET <origin>/api/biorepo/artifacts/<id>`. The origin is `http://` or
  `https://`, the host 127.0.0.1, [::1] or localhost, and an explicit port,
  with nothing after the port (`service_origin`): the service binds loopback,
  and this server sends to that address alone, `localhost` as 127.0.0.1,
  through no proxy, following no redirect. A value outside that rule is
  refused in words when the server starts, a user or a password never
  repeated, and every call then answers with those words. A call waits
  SERVICE_TIMEOUT_S for the service, an ask ASK_TIMEOUT_S; past that the
  call is said in words while the service may carry on. In this mode the
  server opens no database and reads core/.env for OPENFERMENT_PROJECT
  alone, when --project names none; what it writes is what that service's
  `GET /api/audit` reads, and a project the service does not hold comes back
  in the service's words.
- In its own process, with no --service. Every call runs through `tools.run`
  on the database OPENFERMENT_DATABASE_URL names (ADR-001). The project and
  the address are read from the environment, or from core/.env when the
  environment lacks them; nothing else is read from that file here. The
  project is checked against that database at the first call, and a project
  it does not hold is said in words at every call (`_Store`).

A number an outside assistant types into a quantity is its estimate
(ADR-006), and a write it makes is audited as its own: both are marked with
the name its client declares when it connects (MCP's `clientInfo`), as
`<name>/<version>` (`caller`), and with `AUTHOR` when it declares none or only
the SDK's own default. The name is a label the client chooses: a write it
marks stays in the model's open lane until a person promotes it.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote, urlsplit

import httpx
from dotenv import dotenv_values

from mcp.client.session import DEFAULT_CLIENT_INFO
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from pydantic import ConfigDict, Field

from . import db, projects, tools
from .engine import simulator
from .models import AnswerPlan, Artifact, ToolResult

NAME = "openferment"
EXTRA = ("ask_postdoc", "get_artifact")
# Who an outside assistant's typed numbers and writes are marked as when its
# client declares no name of its own (ADR-006).
AUTHOR = "an assistant over MCP"
# The longest name a client's writes are marked with.
MAX_CALLER = tools.MAX_CALLER
NO_PROJECT = ("This openFerment server acts in no project. Start it with --project <id>, or set OPENFERMENT_PROJECT "
              "(in the environment or core/.env) to the project's id.")
SERVICE = "--service"
# The hosts --service may name: the service binds loopback (CLAUDE.md, §7.6).
LOOPBACK = ("127.0.0.1", "::1", "localhost")
# A call sent to the service waits as long as the longest tool may take
# there: the Proforma worker's start and one call of it, and a minute more.
SERVICE_TIMEOUT_S = simulator.START_TIMEOUT_S + simulator.CALL_TIMEOUT_S + 60.0
# An ask waits for Postdoc's whole loop: its wall time (postdoc_agent's
# MAX_SECONDS, which test_mcp_service holds this to, so this module imports
# no part of the loop), then the longest one tool may take past it, and a
# minute more for the plan.
ASK_SECONDS = 360.0
ASK_TIMEOUT_S = ASK_SECONDS + SERVICE_TIMEOUT_S
CONNECT_TIMEOUT_S = 10.0


class _Raw(ArgModelBase):
    """Every argument, as sent: the registry validates, never this layer."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def model_dump_one_level(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


def _flag(args: list[str], name: str) -> str | None:
    """What `name` names in `args`, written `name value` or `name=value`:
    None when the flag is absent, an empty string when it names nothing."""
    for n, arg in enumerate(args):
        if arg == name:
            value = args[n + 1] if n + 1 < len(args) else ""
            return "" if value.startswith("--") else value
        if arg.startswith(f"{name}="):
            return arg[len(name) + 1:]
    return None


def named_project(argv: list[str] | None = None) -> str | None:
    """The project this server acts in: `--project <id>`, else OPENFERMENT_PROJECT."""
    args = list(sys.argv[1:] if argv is None else argv)
    named = (_flag(args, "--project") or "").strip()
    return named or (os.environ.get(projects.ENV) or "").strip() or None


def named_service(argv: list[str] | None = None) -> str | None:
    """What `--service` names, as given; None when the flag is absent."""
    return _flag(list(sys.argv[1:] if argv is None else argv), SERVICE)


class ServiceRefused(ValueError):
    """A --service value this server sends nothing to, in words."""


def service_origin(raw: str) -> str:
    """The origin of the running service `--service` names, written
    `<scheme>://<host>:<port>`: the scheme `http` or `https`, the host
    127.0.0.1, [::1] or localhost, an explicit port, and nothing after the
    port. `localhost` is sent to 127.0.0.1, the address the service binds,
    so no resolver is asked where it is. Anything else is refused in words
    (ServiceRefused); a value holding `@`, where a user or a password would
    stand, is refused in words that never repeat it."""
    given = (raw or "").strip()
    shape = "http://127.0.0.1:<port>, the address of the running service"
    if not given:
        raise ServiceRefused(f"--service names no address: give it as {shape}")
    if "@" in given:
        raise ServiceRefused(f"--service names a user or a password; the origin is a scheme, a host and a port "
                             f"alone: give it as {shape}")
    try:
        parts = urlsplit(given)
        port = parts.port
    except ValueError as e:
        raise ServiceRefused(f"--service {given!r} is no address this server reads ({e}): give it as {shape}") from None
    if parts.scheme not in ("http", "https"):
        raise ServiceRefused(f"--service {given!r} is no http:// or https:// address: give it as {shape}")
    if parts.hostname not in LOOPBACK:
        raise ServiceRefused(f"--service {given!r} names the host {parts.hostname!r}. The service binds loopback, and "
                             "this server sends to 127.0.0.1, [::1] or localhost alone")
    if not port:
        raise ServiceRefused(f"--service {given!r} names no port: give the port the service listens on, as {shape}")
    host = {"::1": "[::1]", "localhost": "127.0.0.1"}.get(parts.hostname, parts.hostname)
    if given.lower() != f"{parts.scheme}://{parts.netloc}".lower():
        raise ServiceRefused(f"--service {given!r} holds more than an origin: give the scheme, the host and the port "
                             f"alone, {parts.scheme}://{host}:{port}")
    return f"{parts.scheme}://{host}:{port}"


def caller(ctx: Any) -> str:
    """Who a call's writes and typed numbers are marked as: the name the
    client declared when it connected, with its version as `<name>/<version>`;
    AUTHOR for a client that declared none, or only the SDK's own default, and
    for a call made in process with no client at all."""
    try:
        params = ctx.request_context.session.client_params
    except Exception:  # no session behind the call: no name was declared
        return AUTHOR
    info = getattr(params, "client_info", None) or getattr(params, "clientInfo", None)
    name = tools.caller_name(str(getattr(info, "name", "") or ""))
    version = tools.caller_name(str(getattr(info, "version", "") or ""))
    if not name or (name, version) == (DEFAULT_CLIENT_INFO.name, DEFAULT_CLIENT_INFO.version):
        return AUTHOR
    named = name if not version or name.endswith(f"/{version}") else f"{name}/{version}"
    return named[:MAX_CALLER]


def _plan(plan: AnswerPlan) -> str:
    """An answer of `ask_postdoc`, as JSON with its null fields left out."""
    return plan.model_dump_json(exclude_none=True)


def artifact_refusal(artifact_id: str) -> str | None:
    """Why `get_artifact` reads nothing for an id, in words, or None when the
    id has an artifact's shape (sixteen hex digits, artifacts.ID_PATTERN);
    nothing is read or sent for an id refused here."""
    from .artifacts import ID_PATTERN

    if ID_PATTERN.match(artifact_id or ""):
        return None
    return (f"no readable artifact {artifact_id!r}: an artifact's id is sixteen hex digits, as a tool's result names "
            "it (an artifactId), so nothing was read")


# ── through a running service (--service) ─────────────────────────────────


def _said(r: httpx.Response, origin: str) -> str:
    """The words of an answer from the service other than a result: its
    `detail`, or FastAPI's list of field errors, or what it answered."""
    try:
        detail = r.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    if isinstance(detail, list):
        said = "; ".join(f"{'.'.join(str(p) for p in d.get('loc') or ()) or 'input'}: {d.get('msg')}"
                         for d in detail if isinstance(d, dict))
        if said:
            return said
    return f"the service at {origin} answered {r.status_code} {r.reason_phrase}: {r.text.strip()[:300] or 'nothing'}"


class Service:
    """The running openFerment service this server sends every call to, in
    one project (--service). Through no proxy: the call is a loopback one,
    and a cloud container's HTTPS_PROXY names a proxy elsewhere. A redirect
    is answered as the service's words and followed nowhere."""

    def __init__(self, origin: str, project: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self.origin = origin
        self.project = project
        self.http = httpx.Client(base_url=origin, trust_env=False, follow_redirects=False, transport=transport,
                                 timeout=httpx.Timeout(SERVICE_TIMEOUT_S, connect=CONNECT_TIMEOUT_S))
        # httpx says each request it sends at INFO, on the stderr a client
        # reads the server's words from; a call's answer says what happened.
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def _send(self, method: str, path: str, *, assistant: str | None = None, body: Any = None,
              timeout: float | None = None) -> httpx.Response:
        headers: dict[str, Any] = {projects.HEADER: self.project}
        if assistant is not None:
            # The name as UTF-8, which the service reads it as (api.py).
            headers[tools.ASSISTANT_HEADER] = assistant.encode("utf-8")
        content = None
        if body is not None:
            # The arguments as the client sent them, every number among them,
            # so the registry refuses at the service what it refuses here;
            # each character past ASCII written as JSON's \u escape, which
            # holds any text the client sent.
            headers["content-type"] = "application/json"
            content = json.dumps(body).encode("ascii")
        waits = httpx.Timeout(timeout, connect=CONNECT_TIMEOUT_S) if timeout is not None else httpx.USE_CLIENT_DEFAULT
        return self.http.request(method, path, headers=headers, content=content, timeout=waits)

    def _silent(self, e: httpx.HTTPError) -> str:
        return f"the service at {self.origin} did not answer: {str(e).strip() or type(e).__name__}"

    def tool(self, name: str, arguments: dict[str, Any], assistant: str) -> str:
        """One registry tool, run by the service under the client's name."""
        try:
            r = self._send("POST", f"/api/tools/{name}", assistant=assistant, body=arguments)
        except httpx.HTTPError as e:
            return json.dumps({"error": self._silent(e)})
        if r.status_code != 200:
            return json.dumps({"error": _said(r, self.origin)})
        try:
            return ToolResult.model_validate(r.json()).model_dump_json(exclude_none=True)
        except ValueError as e:
            return json.dumps({"error": f"the service at {self.origin} answered no tool result: {str(e)[:300]}"})

    def ask(self, question: str, by: str) -> str:
        """Postdoc's plan for a question, asked of the service by the client's
        name; it waits ASK_TIMEOUT_S for the plan."""
        try:
            r = self._send("POST", "/api/ask", body={"question": question, "by": by}, timeout=ASK_TIMEOUT_S)
        except httpx.HTTPError as e:
            return _plan(AnswerPlan(question=question, declined=f"Postdoc could not run: {self._silent(e)}"))
        if r.status_code != 200:
            return _plan(AnswerPlan(question=question, declined=f"Postdoc could not run: {_said(r, self.origin)}"))
        try:
            return _plan(AnswerPlan.model_validate(r.json()))
        except ValueError as e:
            return _plan(AnswerPlan(question=question, declined=f"Postdoc could not run: the service at {self.origin} "
                                                               f"answered no plan: {str(e)[:300]}"))

    def artifact(self, artifact_id: str) -> str:
        """One kept artifact, read from the service."""
        try:
            r = self._send("GET", f"/api/biorepo/artifacts/{quote(artifact_id, safe='')}")
        except httpx.HTTPError as e:
            return json.dumps({"error": self._silent(e)})
        if r.status_code != 200:
            return json.dumps({"error": f"no readable artifact {artifact_id!r}: {_said(r, self.origin)}"})
        try:
            return Artifact.model_validate(r.json()).model_dump_json(exclude_none=True)
        except ValueError as e:
            return json.dumps({"error": f"no readable artifact {artifact_id!r}: the service at {self.origin} "
                                        f"answered no artifact: {str(e)[:300]}"})


# ── in this process ───────────────────────────────────────────────────────


def _where() -> str:
    """The database this process reads, in words (its password never)."""
    try:
        url = db.database_url()
    except db.DatabaseUnavailable:
        return "The database"
    return f"The database {url.database} on {url.host}:{url.port or 5432}"


class _Store:
    """The project in this process's own store, checked against the database
    at the first call: held, it is never asked again; missing, or the
    database silent, each call says so in words and asks again."""

    def __init__(self, project: str) -> None:
        self.project = project
        self._held = False

    def refusal(self) -> str | None:
        if self._held:
            return None
        try:
            held = db.run(projects.held(self.project))
        except Exception as e:  # unset or silent: said, and asked again at the next call
            said = f"{e}".strip().rstrip(".")
            return (f"This openFerment server could not read its database: {type(e).__name__}: {said}. Start it with "
                    f"{SERVICE} <origin> to act through a running service.")
        if not held:
            return (f"{_where()} holds no project named {self.project!r}. Start this server with --project naming a "
                    f"project it holds, or with {SERVICE} <origin> to act through a running service that holds it.")
        self._held = True
        return None


def _blocked(acting: str | None, service: str | None) -> tuple[str | None, str | None]:
    """The origin a server started so sends to, and the words every call
    answers when it can run none: a --service value refused, no project."""
    origin = refused = None
    if service is not None:
        try:
            origin = service_origin(service)
        except ServiceRefused as e:
            refused = str(e)
    words = " ".join(w for w in (refused and f"{refused}.", None if acting else NO_PROJECT) if w)
    return origin, words or None


def _register(server: MCPServer, name: str, run: Callable[[str, dict[str, Any], str], str]) -> None:
    tool = tools.REGISTRY[name]

    def call(ctx: Context, **arguments: Any) -> str:
        return run(name, arguments, caller(ctx))

    server.add_tool(call, name=name, description=tool.description, structured_output=False)
    registered = server._tool_manager.get_tool(name)
    registered.parameters = tool.input_model.model_json_schema()
    registered.fn_metadata.arg_model = _Raw


def build(project: str | None = None, service: str | None = None, *,
          transport: httpx.BaseTransport | None = None) -> MCPServer:
    """The server, acting in `project` (OPENFERMENT_PROJECT when None):
    through the running service `service` names (--service), else in this
    process. `transport` stands in for the network in a test."""
    acting = project or named_project([])
    origin, blocked = _blocked(acting, service)
    remote = Service(origin, acting, transport=transport) if origin and acting and not blocked else None
    store = _Store(acting) if acting and service is None else None

    def refusal() -> str | None:
        """Why a call runs nothing, in words, or None when it runs."""
        if blocked is not None:
            return blocked
        return store.refusal() if store is not None else None

    said = blocked or (f"openFerment's tools, acting in the project {acting} through the service at {origin}."
                       if remote is not None else f"openFerment's tools, acting in the project {acting}.")
    server = MCPServer(NAME, instructions=said)

    def run(name: str, arguments: dict[str, Any], who: str) -> str:
        why = refusal()
        if why is not None:
            return json.dumps({"error": why})
        if remote is not None:
            return remote.tool(name, arguments, who)
        result = tools.run(name, arguments, tools.ToolContext(project=acting, model=who, via="mcp"))
        return result.model_dump_json(exclude_none=True)

    for info in tools.infos():
        _register(server, info.name, run)

    @server.tool(name="ask_postdoc", description=(
        "Ask Postdoc a question. It runs its bounded loop over openFerment's tools and returns the plan: claims "
        "that carry no numbers of their own, each citing records, quoted sentences or computed values."))
    def ask_postdoc(question: Annotated[str, Field(description="The question, in words.")], ctx: Context) -> str:
        from . import postdoc_agent

        # §10.R: a loop that cannot run declines in words, as over HTTP,
        # rather than surfacing as a protocol error.
        why = refusal()
        if why is not None:
            return _plan(AnswerPlan(question=question, declined=why))
        if remote is not None:
            return remote.ask(question, caller(ctx))
        try:
            with projects.using(acting):
                return _plan(postdoc_agent.ask(question, ctx=tools.ToolContext(project=acting)))
        except Exception as e:
            return _plan(AnswerPlan(question=question, declined=f"Postdoc could not run: {e}"))

    @server.tool(name="get_artifact", description="Read one kept artifact by its id: what was computed, from which inputs, with its provenance.")
    def get_artifact(id: Annotated[str, Field(description=(  # noqa: A002 (the E.6 name)
            "The artifact's id, sixteen hex digits, as a tool's result names it (an artifactId)."))]) -> str:
        from . import artifacts

        why = refusal() or artifact_refusal(id)
        if why is not None:
            return json.dumps({"error": why})
        if remote is not None:
            return remote.artifact(id)
        try:
            with projects.using(acting):
                return artifacts.get(id).model_dump_json(exclude_none=True)
        except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged) as e:
            return json.dumps({"error": f"no readable artifact {id!r}: {e}"})

    return server


def _settings(*, service: bool = False, project_named: bool = False) -> None:
    """The database address and the project, from core/.env when the
    environment does not set them: these two names alone. A server acting
    through a running service (--service) reads the project alone, and only
    when --project names none."""
    names = (projects.ENV,) if service else (db.URL_SETTING, projects.ENV)
    if service and project_named:
        return
    held = dotenv_values(Path(__file__).parent.parent / ".env")
    for name in names:
        if held.get(name) and not os.environ.get(name):
            os.environ[name] = str(held[name])


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    service = named_service(args)
    _settings(service=service is not None, project_named=bool((_flag(args, "--project") or "").strip()))
    project = named_project(args)
    _, blocked = _blocked(project, service)
    if blocked is not None:
        # Said where a person starting it by hand reads it; every call says it too.
        print(f"{NAME}: {blocked}", file=sys.stderr)
    build(project, service).run("stdio")


if __name__ == "__main__":
    main()
