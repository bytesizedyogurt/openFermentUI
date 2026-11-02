"""`docs/TOOLS.md`, written from the registry (execution prompt §7.3 item 7, A5).

`render()` is the whole file: what every tool takes and says, as a model and an
outside assistant read it, its family, whether it writes, and its scope; the
gate table from `gates.GATES`; and the MCP server's own two names. `pnpm
gen:tools` writes it (scripts/gen-tools.py); `pnpm check:tools` fails when the
file on disk differs from it. Nothing in the file is written by hand: a change
to a tool is a change to its registration, and the file follows.
"""
from __future__ import annotations

from typing import Any

from . import COUNT_FIELDS, MAX_SUMMARY_CHARS, QUANTITY_FIELDS, REGISTRY, WHITELIST, gates

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
    "modules": "Module reads",
    "writes": "Module writes",
}
ORDER = ("Records", "Literature", "Units", "Engine", "Studies", "Proforma", "fermOS", "pureOS", "geneOS",
         "thermosteam", "Runbooks", "Module reads", "Module writes")

HEADER = """# The tools

<!-- Written by `pnpm gen:tools` (core/openferment_core/tools/reference.py) from the registry in
core/openferment_core/tools/. Edit a tool's registration, never this file: `pnpm check:tools` fails
when the two differ. -->

One registry, three callers: Postdoc's loop, the HTTP endpoints (`GET /api/tools`, `POST
/api/tools/{{name}}`) and the MCP server (`openferment`) run every tool through `tools.run`, so a rule
the registry holds, it holds for each of them.

- **Inputs** carry ids, words and quantities (ADR-006). A number stands only inside a quantity, an
  object of `value` and `unit` (and `low` and `high` for a range), where a tool asks for one; a
  number anywhere else, outside the count fields `k` and `limit`, refuses the call. The service
  writes each quantity's origin from who called: the answering model's estimate with its id, or the
  named person's assumption (`?by=` at the HTTP endpoint); a quantity nobody can be named for is
  refused.
- **Outputs** are a summary a model reads, at most {max_summary} characters, and beside it what a
  claim may cite (records, passages, evidence, module rows); the whole of a large output travels in
  `data`, which no model reads.
- **Scope**: every tool acts in one project (ADR-005): the request's, the question's, or the one the
  MCP server was started in.
- **Writes**: a tool marked *writes* keeps something new in the project, audited as its caller's,
  through `tools/writes.py`; a read keeps nothing but the computations it caches.

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


def _gates() -> list[str]:
    rows = ["## The gates (OF-BLD-015 §7.4)", "",
            "A write tool whose module and action a gate names writes nothing: the call becomes a proposal with "
            "`state: proposed`, and Home shows it with the one button a person presses (`tools/gates.py`).", "",
            "| Gate | Covers | Actions | The button |", "|---|---|---|---|"]
    for g in gates.GATES:
        actions = ", ".join(f"`{module} {action}`" for module, action in g.actions)
        rows.append(f"| `{g.id}` | {_cell(g.covers)} | {actions} | {_cell(g.how)} |")
    return rows + [""]


def _mcp() -> list[str]:
    from .. import mcp_server

    return ["## The MCP server", "",
            f"`{mcp_server.NAME}` (`core/openferment_core/mcp_server.py`, started by `.mcp.json`) lists every tool "
            "above under its own name, description and input schema, and adds "
            + " and ".join(f"`{n}`" for n in mcp_server.EXTRA)
            + ": Postdoc's loop on a question, and a kept artifact by its id. It acts in one project, the one "
              "`--project` names or else `OPENFERMENT_PROJECT`, and a number an outside assistant types into a "
              f"quantity is marked as an estimate by `{mcp_server.AUTHOR}`.", ""]


def render() -> str:
    lines = [HEADER.format(max_summary=f"{MAX_SUMMARY_CHARS:,}", count=len(WHITELIST)), "## The registry", "",
             "| Tool | Family | Kind | Scope |", "|---|---|---|---|"]
    for name in WHITELIST:
        tool = REGISTRY[name]
        lines.append(f"| `{name}` | {family(name)} | {'writes' if tool.writes else 'read'} | {tool.scope} |")
    lines.append("")
    for fam in ORDER:
        names = [n for n in WHITELIST if family(n) == fam]
        if names:
            lines += [f"## {fam}", ""]
            for n in names:
                lines += _tool(n)
    lines += _gates() + _mcp()
    return "\n".join(lines).rstrip() + "\n"
