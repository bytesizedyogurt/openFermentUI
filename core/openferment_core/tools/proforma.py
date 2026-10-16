"""`selling_price`: the price a person's run produced (OF-BLD-014 §8.5).

Ids in: a scenario id. The most recent run artifact of that scenario comes
back as one `Evidence` with the hint `distribution`: the median price and
its 5th to 95th percentile, with the run's provenance, which is `demo` while
any input rests on an assumption. With no run, the tool refuses and names
the inputs still waiting for a source. It never runs a scenario and never
makes an assumption: both are a person's, in Proforma.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .. import proforma
from ..models import ToolResult
from . import Tool, ToolContext, register

NAME = "selling_price"


class SellingPriceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenarioId: str = Field(description=f"A BioSTEAM scenario's id, e.g. {proforma.SCENARIO_ID}.")


def _run(inp: SellingPriceInput, ctx: ToolContext) -> ToolResult:
    if inp.scenarioId != proforma.SCENARIO_ID:
        return ToolResult(error=f"{NAME} refused: there is no BioSTEAM scenario {inp.scenarioId!r}; the one there is is {proforma.SCENARIO_ID}")
    art = proforma.latest_run(inp.scenarioId)
    if art is None:
        info = proforma.scenario(pool=ctx.pool)
        waiting = [i.label for i in info.inputs if i.binding == "waiting"]
        why = f"inputs still waiting for a source: {', '.join(waiting)}" if waiting else "every input has a source, and nobody has run it"
        return ToolResult(error=f"{NAME} refused: no run of {inp.scenarioId} exists; {why}. A person runs it in Proforma.")
    try:
        ev = proforma.evidence_of(art)
    except proforma.ScenarioRefused as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    o = art.output
    assumed = sorted({i.name.split(" ")[0] for i in art.inputs if i.source.kind == "assumption"})
    return ToolResult(
        summary={
            "evidenceId": ev.id,
            "median": ev.value,
            "interval": ev.interval.model_dump() if ev.interval else None,
            "unit": ev.unit,
            "provenance": ev.provenance,
            "feasible": o["feasible"],
            "samples": o["samples"],
            "infeasible": o["infeasible"],
            "assumedInputs": assumed,
            "leavesOut": proforma.LEAVES_OUT,
            "meaning": "a draft flowsheet's price across its inputs' ranges, from a run a person produced",
        },
        evidence=[ev],
    )


TOOL = register(
    Tool(
        name=NAME,
        description=(
            "The minimum selling price a person's most recent run of a BioSTEAM scenario produced, as one evidence id "
            "to cite: the median with its 5th to 95th percentile, the infeasible share, which inputs rest on an "
            "assumption, and what the flowsheet leaves out. Refuses when no run exists, naming the inputs still "
            "waiting for a source. It cannot run a scenario or make an assumption."
        ),
        input_model=SellingPriceInput,
        run=_run,
    )
)
