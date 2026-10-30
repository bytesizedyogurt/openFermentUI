"""The project's studies, for Postdoc (alpha 2.0 stage 6; execution prompt
§4.6, §9.1 step 6; ADR-006).

`study_scenario` keeps a scenario on a plant from the library shelf: each value
a parameter's key and a quantity in the parameter's unit, typed by the caller
and marked by the service as the caller's (a model's estimate with its id, or
a named person's assumption, `tools.stamped`), with what it rests on in words.
`study_compare` sets two to twelve kept runs side by side as one
`study.comparison` artifact. Both keep through `tools/writes.py`, audited as
the caller's. `study_read` lists the project's scenarios, comparisons and the
runbooks studies made.

A COMPARISON'S EVIDENCE. Each output the runs answer, each later run's change
from the first run's value as a fraction of it, is one Evidence whose id is
`<artifact id>:<block>.<key>:<run>` (the run's place, from two), on the
comparison's artifact and with its provenance, the weakest of the runs'.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ..models import ComparisonReport, ComputedBasis, Evidence, ToolResult
from . import QuantityIn, Tool, ToolContext, register

MAX_ROWS = 40


def comparison_evidence(report: ComparisonReport) -> list[Evidence]:
    """A comparison's changes as evidence a claim may cite: each output, each
    later run's change from the first's, as a fraction of the first's."""
    art = report.artifact
    basis = ComputedBasis(tool=art.tool, toolVersion=art.toolVersion, inputs=art.inputs, artifactId=art.id,
                          at=art.createdAt, seed=art.seed)
    out: list[Evidence] = []
    for row in art.output.get("rows") or []:
        for n, change in enumerate(row.get("change") or [], start=1):
            if n == 1 or not isinstance(change, (int, float)) or isinstance(change, bool):
                continue
            out.append(Evidence(id=f"{art.id}:{row['key']}:{n}",
                                label=f"{row['key']}: run {n}'s change from run 1, a fraction of run 1's",
                                value=change, unit="fraction", provenance=art.provenance, basis=basis))
    return out[:MAX_ROWS]


def comparison_result(report: ComparisonReport, *, state: str = "open") -> ToolResult:
    evidence = comparison_evidence(report)
    c, out = report.comparison, report.artifact.output
    rows = [{"key": r["key"], "unit": r.get("unit"), "values": r.get("values"), "change": r.get("change")}
            for r in (out.get("rows") or [])][:MAX_ROWS]
    return ToolResult(
        summary={"state": state, "comparisonId": c.id, "title": c.title, "runIds": c.runIds,
                 "artifactId": c.artifactId, "provenance": c.provenance, "rows": rows,
                 "valuesSet": out.get("values") or [],
                 "evidence": [{"id": e.id, "label": e.label, "value": e.value} for e in evidence]},
        evidence=evidence,
    )


# ── study_scenario ──────────────────────────────────────────────────────


class ScenarioValueIn(BaseModel):
    key: str = Field(max_length=200, description="The parameter's key, as engine_parameters gives it.")
    quantity: QuantityIn = Field(description="The value, in the parameter's own unit, with what it rests on.")


class StudyScenarioInput(BaseModel):
    title: str = Field(max_length=200, description="What the scenario asks, in words.")
    plant: str = Field(max_length=80, description="A plant's id, as engine_plants gives it.")
    configuration: str = Field(default="", max_length=40, description="One of the plant's configurations; empty for its own.")
    values: list[ScenarioValueIn] = Field(
        max_length=24, description="The parameters it sets, each a quantity in the parameter's own unit with a note "
                                   "saying what the value rests on; every other parameter keeps the library's default.")
    note: str = Field(default="", max_length=2000, description="Why the scenario, in words.")


def _scenario(inp: StudyScenarioInput, ctx: ToolContext) -> ToolResult:
    from .writes import make_scenario

    return make_scenario("study_scenario", inp, ctx)


# ── study_compare ───────────────────────────────────────────────────────


class StudyCompareInput(BaseModel):
    title: str = Field(max_length=200, description="What the comparison asks, in words.")
    runs: list[str] = Field(min_length=2, max_length=12,
                            description="Kept runs' ids, the first the one each change is reckoned from.")


def _compare(inp: StudyCompareInput, ctx: ToolContext) -> ToolResult:
    from .writes import make_comparison

    return make_comparison("study_compare", inp.title, inp.runs, ctx)


# ── study_read ──────────────────────────────────────────────────────────


class StudyReadInput(BaseModel):
    kind: Literal["scenario", "comparison", "runbook", ""] = Field(
        default="", description="scenario, comparison or runbook; empty for every kind.")
    words: str = Field(default="", max_length=200, description="Words to narrow by; empty for all.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


def _said(row: dict[str, Any], words: list[str]) -> bool:
    text = " ".join(str(v) for v in row.values() if isinstance(v, str)).lower()
    return all(w in text for w in words)


def _read(inp: StudyReadInput, ctx: ToolContext) -> ToolResult:
    from ..studies import comparisons, runbooks, scenarios

    words = [w for w in inp.words.lower().split() if w]
    rows: list[dict[str, Any]] = []
    if inp.kind in ("scenario", ""):
        for s in scenarios.listed():
            rows.append({"kind": "scenario", "id": s.id, "title": s.title, "plant": s.plant,
                         "configuration": s.configuration, "runIds": s.runIds, "by": s.by, "at": s.at,
                         "values": [{"key": v.key, "value": v.quantity.value, "unit": v.quantity.unit,
                                     "origin": v.quantity.origin.kind, "by": v.quantity.origin.by} for v in s.values]})
    if inp.kind in ("comparison", ""):
        for c in comparisons.listed():
            rows.append({"kind": "comparison", "id": c.id, "title": c.title, "runIds": c.runIds,
                         "provenance": c.provenance, "by": c.by, "at": c.at})
    if inp.kind in ("runbook", ""):
        for r in runbooks.listed():
            rows.append({"kind": "runbook", "id": r.id, "title": r.title, "status": r.status,
                         "lockedAt": r.lockedAt})
    matched = [r for r in rows if _said(r, words)]
    return ToolResult(summary={"matched": len(matched), "rows": matched[: inp.limit],
                               "note": "A scenario runs with engine_run; a kept run reads with engine_report; "
                                       "a comparison is cited through study_compare's evidence ids."})


SCENARIO_TOOL = register(Tool(
    name="study_scenario",
    description=(
        "Keep a study scenario on a plant from the library shelf: a title, the plant and its configuration, and "
        "the values it sets, each a parameter's key and a quantity (value and unit, the parameter's own unit) "
        "with a note saying in words what the value rests on. Each value is marked as your estimate, with your "
        "model id, and a run of the scenario is assumed. Checked against the plant's parameters: a key it does "
        "not read, a unit it does not use or a value of the wrong kind is refused before anything is kept. The "
        "same plant and values are one scenario. Run it with engine_run."
    ),
    input_model=StudyScenarioInput, run=_scenario, strict=False, writes=True,
))

COMPARE_TOOL = register(Tool(
    name="study_compare",
    description=(
        "Set two to twelve kept engine runs side by side as one comparison, kept in the project: every output "
        "the runs answer with each run's value and its change from the first run's, and every value any run set "
        "with its origin. Each later run's change from the first is an evidence id to cite; the comparison's "
        "provenance is the weakest of its runs'."
    ),
    input_model=StudyCompareInput, run=_compare, strict=False, writes=True,
))

READ_TOOL = register(Tool(
    name="study_read",
    description=(
        "List the project's study scenarios (each with the values it sets, their origins and the runs made of "
        "it), its comparisons and the runbooks studies made. Narrow by kind and words. Returns ids and words to "
        "act on; a run's numbers are read with engine_report."
    ),
    input_model=StudyReadInput, run=_read, strict=False,
))
