"""One read tool per module (OF-BLD-015 §7.2).

`dominion_read`, `runbooks_read`, `geneos_read`, `fermos_read`, `pureos_read`,
`proforma_read`, `biorepo_read`, `guild_read`, `primer_read`, `intake_read`
and `home_read`. The build document writes them `dominion.read`; the Messages
API refuses a tool name outside `^[a-zA-Z0-9_-]{1,128}$` (measured on
2026-10-19 with the free token-count endpoint), so the registry, the
endpoints and the MCP server all use the underscore.

Every one takes the same input, ids and words: ids or refs to read, words
to search, one of the module's kinds, one state from the enum, and how many.
Every one returns rows in one shape (`ModuleRow`): the module's own word for
where a row stands, the one `state` computed from it in `module_stores.py`,
and the row's provenance mark. The rows go back on `ToolResult.rows`, which
is what lets a claim cite them (`SeenSet`).

A module part of which lives only in a browser says so in `partial`, and the
tool reads what the service has. Nothing here writes.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .. import module_stores
from ..models import ModuleState, ToolResult
from . import MAX_SUMMARY_CHARS, Tool, ToolContext, register

MAX_ROWS = 20
# Room left in a summary for everything but the rows.
ROW_BUDGET = MAX_SUMMARY_CHARS - 1_500

WHAT = {
    "dominion": "the molecule catalogue and the clearance findings: which molecules are open to make and which are fenced, "
                "with the headline clearance and its basis",
    "runbooks": "the runbooks (their status, lock and what they predict) and the protocols (their versions)",
    "geneos": "the hosts, the pathways, the genome-scale models on the shelf and the ceilings computed on them",
    "fermos": "the growth fits and forecasts computed from deposited runs",
    "pureos": "the downstream unit operations, by stage",
    "proforma": "the cost scenarios and the price runs kept as artifacts",
    "biorepo": "the records, the extractor's candidates, the computed artifacts and the Witness runs that score the extractor",
    "guild": "the people on the ledger (name, role, whether active) and the competence checks on skills; no level is stored "
             "and none is read",
    "primer": "the lessons, by module, and the skills each counts toward",
    "intake": "the sources (papers) and how far each is prepared: fetched with full text, failed and why, or waiting",
    "home": "what waits for a person: candidates awaiting review and open checks",
}


class ModuleReadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[str] = Field(description="Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list.")
    words: str = Field(description="Words to search the module for, or an empty string for no word search.")
    kind: str | None = Field(description="One of the module's kinds, named in the tool's description, or null for every kind.")
    state: ModuleState | None = Field(description="One of open, fenced, approved, locked, proposed, retired; or null for every state.")
    limit: int = Field(description=f"How many rows to return, at most {MAX_ROWS}.")

    @field_validator("kind", "state", mode="before")
    @classmethod
    def _unused_is_null(cls, v: Any) -> Any:
        # As in search_records: an empty value, or quotes around nothing, is null.
        if isinstance(v, str) and v.strip() in ("", '""', "''"):
            return None
        return v


def _summary(module: str, inp: ModuleReadInput, matched: list[Any], rows: list[dict[str, Any]], cut: bool) -> dict[str, Any]:
    states: dict[str, int] = {}
    for r in matched:
        states[r.state] = states.get(r.state, 0) + 1
    out: dict[str, Any] = {
        "module": module_stores.LABEL[module],
        "count": len(matched),
        "returned": len(rows),
        "states": states,
        "rows": rows,
    }
    if cut:
        out["note"] = "fewer rows than asked, so that the result stays readable; ask by id or with words for the rest"
    partial = module_stores.PARTIAL.get(module)
    if partial:
        out["partial"] = partial
    return out


def _runner(module: str):
    def run(inp: ModuleReadInput, ctx: ToolContext) -> ToolResult:
        name = f"{module}_read"
        kinds = module_stores.KINDS[module]
        if inp.kind is not None and inp.kind not in kinds:
            return ToolResult(error=f"{name} refused: {inp.kind!r} is not a kind {module_stores.LABEL[module]} holds; "
                                    f"the kinds are {', '.join(kinds)}.")
        stores = ctx.stores
        error = stores.error(module)
        if error:
            return ToolResult(error=f"{name} could not read the module: {error}")
        matched = module_stores.find(stores, module, ids=inp.ids, words=inp.words, kind=inp.kind, state=inp.state)
        limit = max(0, min(inp.limit, MAX_ROWS))
        picked = [r.model() for r in matched[:limit]]
        dumped = [r.model_dump(mode="json", exclude={"module"}) for r in picked]
        cut = False
        while dumped and len(json.dumps(dumped, ensure_ascii=False)) > ROW_BUDGET:
            dumped.pop()
            picked.pop()
            cut = True
        return ToolResult(summary=_summary(module, inp, matched, dumped, cut), rows=picked)

    return run


def _description(module: str) -> str:
    label = module_stores.LABEL[module]
    kinds = ", ".join(module_stores.KINDS[module])
    partial = module_stores.PARTIAL.get(module)
    return (
        f"Read {label}: {WHAT[module]}. Kinds: {kinds}. Pass ids or refs, words, a kind and a state to narrow; pass an "
        f"empty list, an empty string and nulls to list the module. Returns at most {MAX_ROWS} rows, each with its "
        "ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the "
        "service), the module's own status word and its provenance; and the count of every match by state."
        + (f" Read in part: {partial}." if partial else "")
    )


TOOLS = {
    module: register(Tool(name=f"{module}_read", description=_description(module), input_model=ModuleReadInput,
                          run=_runner(module)))
    for module in module_stores.MODULES
}
