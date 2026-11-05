"""`docs/TOOLS.md`, written from the registry (execution prompt §7.3 item 7, A5).

`render()` is the whole file: what every tool takes and says, as a model and an
outside assistant read it, its family, whether it writes, and its scope; what
a module read answers (`models.ModuleRead`) and what each kind's rows hold
(`module_stores.DETAIL`); the gate table from `gates.GATES`; and the MCP
server: its own two names, read from its listing, how it starts, the two ways
it reaches a project, and what a client of it reads. `pnpm gen:tools` writes
it (scripts/gen-tools.py); `pnpm check:tools` fails when the file on disk
differs from it. Nothing in the file
is written by hand: a change to a tool is a change to its registration, and
the file follows.
"""
from __future__ import annotations

import asyncio
from typing import Any

from . import ASSISTANT_HEADER, COUNT_FIELDS, MAX_SUMMARY_CHARS, QUANTITY_FIELDS, REGISTRY, WHITELIST, gates

# Each tool's family, by the file it is registered from, in the order the file lists them.
FAMILIES = {
    "records": "Records",
    "units": "Units",
    "passages": "Literature",
    "literature": "Literature",
    "geneos": "geneOS",
    "fermos": "fermOS",
    "pureos": "pureOS",
    "proforma": "Proforma",
    "thermo": "thermosteam",
    "runbook": "Runbooks",
    "engine": "Engine",
    "studies": "Studies",
    "catalogues": "Catalogues",
    "flowsheets": "Flowsheets",
    "modules": "Module reads",
    "writes": "Module writes",
}
ORDER = ("Records", "Catalogues", "Literature", "Units", "Engine", "Flowsheets", "Studies", "Proforma", "fermOS",
         "pureOS", "geneOS", "thermosteam", "Runbooks", "Module reads", "Module writes")

HEADER = """# The tools

<!-- Written by `pnpm gen:tools` (core/openferment_core/tools/reference.py) from the registry in
core/openferment_core/tools/. Edit a tool's registration, never this file: `pnpm check:tools` fails
when the two differ. -->

One registry, three callers: Postdoc's loop, the HTTP endpoints (`GET /api/tools`, `POST
/api/tools/{{name}}`) and the MCP server (`openferment`) run every tool through `tools.run`
(`core/openferment_core/tools/__init__.py`), so a rule the registry holds, it holds for each of them.

**For a client.** [The MCP server](#the-mcp-server), at the end of this page, says how to start it
and the two ways it reaches a project, and [A client](#a-client) is the recipe: the SDK's names, the
environment to hand the server, the shape of every answer, and where a write's audit row is read.
What a module read answers, and what each kind of row holds, closes [Module reads](#module-reads).

- **Inputs** carry ids, words and quantities (ADR-006). A number stands only inside a quantity, an
  object of `value` and `unit` (and `low` and `high` for a range), where a tool asks for one; a
  number anywhere else, outside the count fields `k` and `limit`, refuses the call. A number is a
  JSON number: digits inside a string, an id or a name among them, are words. The service writes
  each quantity's origin from who called: the answering model's estimate with its id, an
  assistant's estimate under the name it declares (over MCP its `clientInfo`, at the HTTP endpoint
  the `{assistant}` header), or the named person's assumption (`?by=` at the HTTP
  endpoint); a quantity nobody can be named for is refused, and over MCP a client that declares no
  name is named `{author}`.
- **Outputs** are a `summary` object a model reads, at most {max_summary} characters as JSON, and
  beside it what a claim may cite: records (`recordIds`), passages, evidence and module rows
  (`rows`; `moduleRefs` are the module rows a claim of Postdoc's plan cites, each by its `ref`). The
  whole of a large output travels in `data`, which no model reads, and a refusal is `error`, in
  words. `auditIds` names each audit row the call wrote, oldest first, by the id `GET /api/audit`
  serves it under: a write names the row of what it kept, a gated write the row of its proposal,
  and a read names none.
- **Scope**: every tool acts in one project (ADR-005): the request's, the question's, or the one the
  MCP server was started in.
- **Writes**: a tool marked *writes* keeps something new in the project, audited as its caller's,
  through `core/openferment_core/tools/writes.py`; a read keeps nothing but the computations it
  caches. At the HTTP endpoint a write names its caller: a person with `?by=<their name>`, or an
  assistant with the `{assistant}` header (`<name>/<version>`, UTF-8 text), whose
  call runs in the model's lane under that name, as over MCP. A call that names nobody, or names
  both, is a 422 in words, with nothing run. A write of the model's lane names the door it came in by
  on its audit row (`detail.via`: `postdoc` for Postdoc's loop, `mcp` for the MCP server in its own
  process, `http` for the header), and only Postdoc's carries an `effort`. A write's row keeps the
  note its call carried as `detail.note` (a gated write's proposal keeps it), and the call's answer
  names the row in `auditIds`. The person named is the write's author: its audit row
  (agent `person`), a proposal it makes (which waits for a person to carry it out, as every
  proposal does) and what it keeps; pureOS's kept trains hold a model's work alone, and a person's
  call to keep one is refused in the store's words.
- *strict* or *loose* says how Postdoc's model is offered a tool: strict holds the model to the
  schema as it writes the call; the registry validates every caller's input alike, an MCP client's
  among them.

{count} tools.
"""


def family(name: str) -> str:
    module = REGISTRY[name].run.__module__.rsplit(".", 1)[-1]
    return FAMILIES.get(module, module)


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _type(schema: dict[str, Any]) -> str:
    """A JSON schema's type in words: `string`, `list of string`, `QuantityIn`, `string or null`."""
    if "$ref" in schema:
        return f"`{schema['$ref'].rsplit('/', 1)[-1]}`"
    if "anyOf" in schema:
        return " or ".join(_type(s) for s in schema["anyOf"])
    if "enum" in schema:
        return "one of " + ", ".join(f"`{v}`" if v != "" else "empty" for v in schema["enum"])
    kind = schema.get("type")
    if kind == "array":
        return f"list of {_type(schema.get('items') or {})}"
    if kind == "object" and isinstance(schema.get("additionalProperties"), dict):
        return f"map to {_type(schema['additionalProperties'])}"
    if isinstance(kind, list):
        return " or ".join(kind)
    return str(kind or "any")


def _fields(schema: dict[str, Any], *, top: bool) -> list[str]:
    props = schema.get("properties") or {}
    if not props:
        return ["Takes no fields."]
    required = set(schema.get("required") or [])
    rows = ["| Field | Type | Required | What it is |", "|---|---|---|---|"]
    quantity = "value" in props and "unit" in props
    for name, prop in props.items():
        what = prop.get("description", "")
        if top and name in COUNT_FIELDS:
            what = (what + " A count.").strip()
        if quantity and name in QUANTITY_FIELDS:
            what = (what + " A number of the quantity, marked as its caller's.").strip()
        rows.append(f"| `{name}` | {_cell(_type(prop))} | {'yes' if name in required else 'no'} | {_cell(what)} |")
    return rows


def _tool(name: str) -> list[str]:
    tool = REGISTRY[name]
    schema = tool.info().inputSchema
    marks = ["writes" if tool.writes else "read", f"scope: {tool.scope}", "strict" if tool.strict else "loose"]
    out = [f"### `{name}`", "", f"*{' · '.join(marks)}*", "", _cell(tool.description), "", *_fields(schema, top=True)]
    for def_name, sub in (schema.get("$defs") or {}).items():
        out += ["", f"`{def_name}`: {_cell(sub.get('description', ''))}".rstrip(": "), "", *_fields(sub, top=False)]
    return out + [""]


def _module_reads() -> list[str]:
    """What a module read answers (ModuleRead) and what each kind's rows hold
    in `detail` (module_stores.DETAIL), after the read tools."""
    from .. import module_stores
    from ..models import ModuleRead

    out = ["### What a module read answers", "",
           "Each `<module>_read` answers its rows twice: as the result's `rows`, each a `ModuleRow` "
           "(`docs/api/openapi.json`), and inside its `summary`, a `ModuleRead`:", "",
           *_fields(ModuleRead.model_json_schema(), top=False), "",
           "### What each kind's `detail` holds", "",
           "A module row's `detail` holds the few named fields of its kind below, each text cut at 300 characters "
           "and each list at its first ten.", "",
           "| Module | Kind | `detail` |", "|---|---|---|"]
    for module in module_stores.MODULES:
        for kind in module_stores.KINDS[module]:
            out.append(f"| `{module}` | `{kind}` | {_cell(module_stores.DETAIL[module][kind])} |")
    return out + [""]


def _gates() -> list[str]:
    rows = ["## The gates (OF-BLD-015 §7.4)", "",
            "A write tool whose module and action a gate names writes nothing: the call becomes a proposal with "
            "`state: proposed`, and Home shows it with the one button a person presses "
            "(`core/openferment_core/tools/gates.py`).", "",
            "| Gate | Covers | Actions | The button |", "|---|---|---|---|"]
    for g in gates.GATES:
        actions = ", ".join(f"`{module} {action}`" for module, action in g.actions)
        rows.append(f"| `{g.id}` | {_cell(g.covers)} | {actions} | {_cell(g.how)} |")
    return rows + [""]


def _mcp() -> list[str]:
    from .. import mcp_server

    listed = {t.name: t for t in asyncio.run(mcp_server.build().list_tools())}
    module = "python -m openferment_core.mcp_server"
    out = ["## The MCP server", "",
           f"`{mcp_server.NAME}` (`core/openferment_core/mcp_server.py`, started by `.mcp.json`) lists every tool "
           "above under its own name, description and input schema, and adds "
           + " and ".join(f"`{n}`" for n in mcp_server.EXTRA)
           + ": Postdoc's loop on a question, and a kept artifact by its id. It acts in one project, the one "
             "`--project` names or else `OPENFERMENT_PROJECT`.", ""]
    for name in mcp_server.EXTRA:
        out += [f"### `{name}`", "", _cell(listed[name].description), "", *_fields(listed[name].input_schema, top=True), ""]
    out += ["### Starting it", "",
            "- Start it from the repository's root. `.mcp.json` names no project: a client appends `--project <id>` "
            f"after the module, `uv run --project core --all-extras {module} --project <id>` (the first "
            "`--project`, uv's, names the directory `core`), or sets `OPENFERMENT_PROJECT` in the server's "
            "environment.",
            f"- **Through a running service**: add `{mcp_server.SERVICE} <origin>`, the running openFerment "
            f"service's own address: `uv run --project core --all-extras {module} --project <id> "
            f"{mcp_server.SERVICE} http://127.0.0.1:<port>`. The origin is `http://` or `https://`, the host "
            "`127.0.0.1`, `[::1]` or `localhost`, and an explicit port, with nothing after the port and no user or "
            "password: the service binds loopback, and the server sends to that address alone (`localhost` as "
            "`127.0.0.1`), through no proxy, following no redirect. Every call then goes to that service, in the "
            "project named: a tool above as `POST <origin>/api/tools/<name>` with the arguments as the client sent "
            f"them, the project in `X-OpenFerment-Project` and the client's name in `{ASSISTANT_HEADER}`; "
            "`ask_postdoc` as `POST <origin>/api/ask`; `get_artifact` as `GET <origin>/api/biorepo/artifacts/<id>`. "
            "In this mode the server opens no database, needs no `OPENFERMENT_DATABASE_URL`, and reads `core/.env` "
            "for `OPENFERMENT_PROJECT` alone, when `--project` names none. What it writes is what that service's "
            "`GET /api/audit` reads. An origin outside that rule is refused in words when the server starts, and "
            "every call then answers with those words; a service that does not answer is said in words at each "
            f"call. A call waits up to {mcp_server.SERVICE_TIMEOUT_S / 60:.0f} minutes for the service's answer, the "
            f"longest one tool may take there, and `ask_postdoc` up to {mcp_server.ASK_TIMEOUT_S / 60:.0f}, Postdoc's "
            "whole loop; past that the call answers in words that the service did not answer, and the service may "
            "carry on with it.",
            "- **In its own process**: with no `--service`, the server opens the database "
            "`OPENFERMENT_DATABASE_URL` names (its environment, then `core/.env`) at its first call, and runs every "
            "call there.",
            "- With no project, or one its store does not hold, the server connects and answers every call with "
            "words saying which, and nothing is read or made; through a service, a project it does not hold comes "
            "back in the service's own words.",
            "- In its own process it reads `OPENFERMENT_DATABASE_URL` and `OPENFERMENT_PROJECT` from its "
            "environment, else from `core/.env`, and `ask_postdoc` runs on the key its environment holds "
            "(`ANTHROPIC_API_KEY`); through a service, `ask_postdoc` runs on the service's own key. uv reads the "
            "proxy variables. A Python client hands the server its own environment with `VIRTUAL_ENV` taken out "
            "(`env = dict(os.environ); env.pop(\"VIRTUAL_ENV\", None)`, then `StdioServerParameters(command=\"uv\", "
            "args=[...], cwd=<root>, env=env)`): the SDK alone hands the server `HOME`, `PATH` and four names more, "
            "and a client run by `uv run <script>` holds its own environment's `VIRTUAL_ENV`, which the server's "
            "`uv run --project core` warns of at every start and leaves unused.",
            "- In a fresh checkout the first start syncs core's environment with every extra from PyPI, which takes "
            "minutes; `uv sync --project core --all-extras` from the repository's root beforehand leaves a start of "
            "a few seconds. Once the environment is built the server answers `initialize` in a few seconds (about "
            "4 s here) and opens nothing until its first call; it needs no key, and `ask_postdoc` alone spends.",
            "",
            "### A client", "",
            "- The server runs on `mcp` 2.3 (`core/uv.lock`). A client of that SDK imports `ClientSession` and "
            "`StdioServerParameters` from `mcp`, `stdio_client` from `mcp.client.stdio` and `Implementation` from "
            "`mcp.types`. It opens `stdio_client(params)` as `(read, write)` and `ClientSession(read, write, "
            "client_info=Implementation(name=..., version=...))` inside it, calls `await session.initialize()` "
            "first (2.3 sends the handshake there, and a call before it is refused as invalid request parameters), "
            "then `await session.list_tools()` and `await session.call_tool(<name>, <arguments>)`; a tool's JSON is "
            "`result.content[0].text`. 2.3 spells the SDK's fields in snake case: a result's `content`, `is_error` "
            "and `structured_content`, a listed tool's `input_schema`.",
            "- A client runs in core's environment, `uv run --project core --all-extras python <script>` from the "
            "repository's root, or in one of its own naming `mcp>=2.3,<3` (a PEP 723 header and `uv run <script>`).",
            "- Over MCP each tool answers one text block holding its result as JSON, its null fields left out: a "
            "tool above its ToolResult, `ask_postdoc` an `AnswerPlan`, `get_artifact` an `Artifact` "
            "(`docs/api/openapi.json` holds each schema). A tool's refusal is its ToolResult with `error` set, and "
            "`ask_postdoc`'s an `AnswerPlan` whose `declined` holds the words. A refusal the server writes itself "
            "(no project, a project its store lacks, an origin refused, a service that did not answer or refused "
            "the call, an artifact id of no artifact's shape) is `{\"error\": <words>}` alone for a tool and for "
            "`get_artifact`, and an `AnswerPlan` holding the question and `declined` for `ask_postdoc`, so a client "
            "reads every other key with a default. `is_error` stays false, and no `structured_content` is sent.",
            "- A client is known by the name it declares when it connects: MCP's `clientInfo`, written "
            "`<name>/<version>`. A number it types into a quantity is that name's estimate, and every write it "
            "makes is audited under that name: the entry or the run it keeps names it as `by`, and the audit row "
            "as `who`, with agent `model`, the door in `detail.via` (`mcp` in the server's own process; `http` "
            "through a service, the door the service saw) and no `effort`, since no model of the service ran. A "
            "catalogue entry it keeps reads `<name>/<version>, over MCP` as its source in the server's own process "
            "and `<name>/<version>, at the HTTP endpoint` through a service. A client that declares no name, or "
            f"only the SDK's own (`mcp` 0.1.0), is marked `{mcp_server.AUTHOR}`.",
            "- No tool reads the audit: a client reads it at the service's `GET /api/audit` with the project header, "
            "the newest `limit` rows (200 unless asked, at most 500), newest last, narrowed by `action`, `target` "
            "and `who`, each matched exactly as a row names it "
            "(`?action=catalogue_write&target=skill/<id>&who=<name>/<version>`), so a write of any age is found by "
            "what it was. Each row carries its `id`, the id the write's answer named in `auditIds`; `who` is the "
            "client's `<name>/<version>` and `at` ISO 8601 in UTC, as a catalogue entry's `at` is. A row leaves its "
            "null fields out, as an answer over MCP does, so a client reads `target`, `askId` and `effort` with a "
            "default.",
            "- An example client in this repository writes placeholder words alone: an entry named as a "
            "placeholder (`A placeholder skill`) with a note saying it is one. Its files and its writes name no "
            "real strain, species or product, since the repository ships software alone.",
            "- The server has no offline stand-in: a client is checked against a migrated store, and "
            "`pnpm prove --keep` leaves one running behind a service, printing its address, project and database.",
            ""]
    return out


def render() -> str:
    from .. import mcp_server

    header = HEADER.format(max_summary=f"{MAX_SUMMARY_CHARS:,}", count=len(WHITELIST), assistant=ASSISTANT_HEADER,
                           author=mcp_server.AUTHOR)
    lines = [header, "## The registry", "", "| Tool | Family | Kind | Scope |", "|---|---|---|---|"]
    for name in WHITELIST:
        tool = REGISTRY[name]
        lines.append(f"| `{name}` | {family(name)} | {'writes' if tool.writes else 'read'} | {tool.scope} |")
    lines.append("")
    # Every tool stands in a section: a family the order does not name would
    # leave its tools off the page a client reads.
    unplaced = sorted({family(n) for n in WHITELIST} - set(ORDER))
    if unplaced:
        raise ValueError(f"docs/TOOLS.md has no section for the families {unplaced}: add each to ORDER")
    for fam in ORDER:
        names = [n for n in WHITELIST if family(n) == fam]
        if names:
            lines += [f"## {fam}", ""]
            for n in names:
                lines += _tool(n)
            if fam == "Module reads":
                lines += _module_reads()
    lines += _gates() + _mcp()
    return "\n".join(lines).rstrip() + "\n"
