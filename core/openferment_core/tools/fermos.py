"""`growth_forecast`: a band for the next run, from a fitted one (OF-BLD-014 §7.3).

Ids in: a kept kinetic fit's artifact id. The forecast runs under the fitted
run's own starting values and length; one `Evidence` comes back with the hint
`trajectory`. A fit whose growth rate or ceiling the run did not identify is
refused, and the refusal says what run would identify it.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .. import fermos
from ..models import ToolResult
from . import Tool, ToolContext, register

NAME = "growth_forecast"


class GrowthForecastInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fitArtifactId: str = Field(description="The artifact id of a kept kinetic fit (tool kinetic_fit).")


def _run(inp: GrowthForecastInput, ctx: ToolContext) -> ToolResult:
    try:
        r = fermos.forecast_run(fit_artifact=inp.fitArtifactId)
    except fermos.FitRefused as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    return ToolResult(
        summary={
            "evidenceId": r.evidence.id,
            "finals": [f.model_dump() for f in r.finals],
            "yield": r.yieldInterval.model_dump() if r.yieldInterval else None,
            "substrateRunsOutH": r.substrateRunsOutH,
            "provenance": r.evidence.provenance,
            "artifactId": r.artifactId,
            "meaning": "a band for readings of a run like the fitted one; variation from run to run is not in it",
        },
        evidence=[r.evidence],
    )


TOOL = register(
    Tool(
        name=NAME,
        description=(
            "Forecast a run like a fitted one: biomass, product and substrate as bands for readings, from a kept "
            "kinetic fit's artifact id, under the fitted run's own starting values and length. Returns one evidence "
            "id to cite and the final values as intervals. A fit whose growth rate or ceiling was not identified is "
            "refused with what run would identify it."
        ),
        input_model=GrowthForecastInput,
        run=_run,
    )
)
