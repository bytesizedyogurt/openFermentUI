"""One read tool per module (OF-BLD-015 §7.2).

`runbooks_read`, `geneos_read`, `fermos_read`, `pureos_read`, `proforma_read`,
`biorepo_read`, `guild_read`, `primer_read`, `intake_read` and `home_read`,
one per module of `module_stores.MODULES`. The build document
wrote them `runbooks.read`; the Messages
API refuses a tool name outside `^[a-zA-Z0-9_-]{1,128}$` (measured on
2026-10-19 with the free token-count endpoint), so the registry, the
endpoints and the MCP server all use the underscore.

Every one takes the same input, ids and words: ids or refs to read, words
to search, one of the module's kinds, one state from the enum, and how many.
Every one returns rows in one shape (`ModuleRow`): the module's own word for
where a row stands, the one `state` computed from it in `module_stores.py`,
and the row's provenance mark. The rows go back on `ToolResult.rows`, which
is what lets a claim cite them (`SeenSet`).

A read that leaves part of a module out says so in `partial`. Nothing here
writes.
"""
from __future__ import annotations

import json
from typing import Any

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .. import module_stores
from ..models import ToolResult
from . import MAX_SUMMARY_CHARS, Tool, ToolContext, register

MAX_ROWS = 20
# Room left in a summary for everything but the rows.
ROW_BUDGET = MAX_SUMMARY_CHARS - 1_500

WHAT = {
    "runbooks": "the runbooks (their status, lock and what they predict) and the protocols (their versions)",
    "geneos": "the hosts, the pathways, the genome-scale models on the shelf and the ceilings computed on them",
    "fermos": "the growth fits and forecasts computed from deposited runs (kind artifact), the kept simulations "
              "of a model family (kind simulation: its family, strain, product and sugar, and what bound each "
              "parameter, in words; its numbers stay in the artifact, cited by the row's ref or the evidence id "
              "fermos_simulate returns), and the vessels BioSTEAM designed for kept simulations (kind vessel, read "
              "by the design's artifact id or the simulation's)",
    "pureos": "the downstream unit operations, by stage (each with the BioSTEAM classes it is), and the trains Proforma's "
              "runs simulated (kind train, one a scenario: read by the scenario id or the run's artifact id); kind "
              "train-unit is one unit of a train, in run order, with the product in and out and the recovery read "
              "from the run's stream table. Kind train also holds the trains a model built with pureos_build (read by "
              "the train's id: its product, inlet and units in words and ids, who made it, its runs' ids), and kind "
              "train-run is one kept run of such a train (pureos/train-run/<artifact id>, read by its id or its "
              "train's: its train, product, units and product stream in words; its numbers stay in the artifact, "
              "cited by the row's ref or the evidence id pureos_build returns)",
    "proforma": "the cost scenarios and the runs kept as artifacts: each scenario's runs and the reference "
                "biorefineries' runs (stream_table reads a run's streams)",
    "biorepo": "the records, the extractor's candidates, the computed artifacts and the Witness runs that score the extractor",
    "guild": "the people on the ledger (name, role, whether active) and the competence checks on skills; no level is stored "
             "and none is read",
    "primer": "the lessons, by module, and the skills each counts toward",
    "intake": "the documents the project holds in its literature: title, year, where each came from, its licence class and passages",
    "home": "what waits for a person: candidates awaiting review and open checks",
}


class ModuleReadInput(BaseModel):
    """No field is nullable. Strict tools allow sixteen nullable or union
    parameters across a whole request, and eleven tools with two each sent
    twenty-five: the API answered 400 (live, 2026-10-19). An empty string
    means "any", and `test_module_tools` counts the unions."""

    model_config = ConfigDict(extra="forbid")

    ids: list[str] = Field(description="Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list.")
    words: str = Field(description="Words to search the module for, or an empty string for no word search.")
    kind: str = Field(description="One of the module's kinds, named in the tool's description, or an empty string for every kind.")
    state: Literal["", "open", "fenced", "approved", "locked", "proposed", "retired"] = Field(
        description="One of open, fenced, approved, locked, proposed, retired; or an empty string for every state.")
    limit: int = Field(description=f"How many rows to return, at most {MAX_ROWS}.")

    @field_validator("kind", "state", mode="before")
    @classmethod
    def _unused_is_empty(cls, v: Any) -> Any:
        # As in search_records: null, or quotes around nothing, means unused.
        if v is None or (isinstance(v, str) and v.strip() in ('""', "''")):
            return ""
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
        if inp.kind and inp.kind not in kinds:
            return ToolResult(error=f"{name} refused: {inp.kind!r} is not a kind {module_stores.LABEL[module]} holds; "
                                    f"the kinds are {', '.join(kinds)}.")
        stores = ctx.stores
        error = stores.error(module)
        if error:
            return ToolResult(error=f"{name} could not read the module: {error}")
        matched = module_stores.find(stores, module, ids=inp.ids, words=inp.words, kind=inp.kind or None, state=inp.state or None)
        limit = max(0, min(inp.limit, MAX_ROWS))
        picked = [r.model() for r in matched[:limit]]
        dumped = [r.model_dump(mode="json", exclude={"module"}) for r in picked]
        cut = False
        while dumped and len(json.dumps(dumped, ensure_ascii=False)) > ROW_BUDGET:
            dumped.pop()
            picked.pop()
            cut = True
        summary = _summary(module, inp, matched, dumped, cut)
        return ToolResult(summary=summary, rows=picked)

    return run


def _description(module: str) -> str:
    label = module_stores.LABEL[module]
    kinds = ", ".join(module_stores.KINDS[module])
    partial = module_stores.PARTIAL.get(module)
    return (
        f"Read {label}: {WHAT[module]}. Kinds: {kinds}. Pass ids or refs, words, a kind and a state to narrow; pass an "
        f"empty list and empty strings to list the module. Returns at most {MAX_ROWS} rows, each with its "
        "ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the "
        "service), the module's own status word and its provenance; and the count of every match by state."
        + (f" Read in part: {partial}." if partial else "")
    )


TOOLS = {
    # Offered loose: eighteen strict tools compile to a grammar the API
    # refuses (live, 2026-10-19). `tools.run` validates the input all the same.
    module: register(Tool(name=f"{module}_read", description=_description(module), input_model=ModuleReadInput,
                          run=_runner(module), strict=False))
    for module in module_stores.MODULES
}
