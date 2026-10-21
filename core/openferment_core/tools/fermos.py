"""fermOS's tools.

`growth_forecast`: a band for the next run, from a fitted one (OF-BLD-014 §7.3).
Ids in: a kept kinetic fit's artifact id. The forecast runs under the fitted
run's own starting values and length; one `Evidence` comes back with the hint
`trajectory`. A fit whose growth rate or ceiling the run did not identify is
refused, and the refusal says what run would identify it.

`fermos_vessel`: the vessel a kept simulation needs, designed on BioSTEAM
(OF-BLD-020 §4.2, D7, D13). Ids and words in: a kept simulation's artifact id
(or, anaerobic, a kept kinetic fit's), the vessel type (`stirred-tank` or
`bubble-column`) and a kLa correlation by BioSTEAM's own name. It is a free
write, offered loose like the module tools: it keeps one `fermos.vessel`
artifact through `writes.design_vessel`, the function `fermos_write`'s
`design_vessel` runs, audited with the model as agent. A design needs a plant
scale or one vessel's batch volume, which only a named person types (in
fermOS → Vessel); the service holds none, so without one the tool returns the
refusal's words. A design comes back as one `Evidence` whose id is the
artifact's; its numbers are read from it, never stated by the model.
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


VESSEL = "fermos_vessel"


class FermosVesselInput(BaseModel):
    """No field is nullable (the module tools' rule): an empty string means
    "none" or "BioSTEAM's own"."""

    model_config = ConfigDict(extra="forbid")

    simulationArtifact: str = Field(description="The artifact id of a kept fermOS simulation (fermos_read lists them), "
                                                "or an empty string when a fit is named.")
    fitArtifact: str = Field(description="The artifact id of a kept kinetic fit or forecast, for an anaerobic vessel "
                                         "(a fit gives no oxygen uptake), or an empty string.")
    vesselType: str = Field(description="stirred-tank or bubble-column for an aerobic simulation, or an empty string "
                                        "for BioSTEAM's own default; an anaerobic vessel takes none.")
    klaMethod: str = Field(description="A kLa correlation by the name BioSTEAM registers it (Riet for a stirred tank, "
                                       "Dewes for a bubble column), or an empty string for the class's own.")


def _vessel(inp: FermosVesselInput, ctx: ToolContext) -> ToolResult:
    from .writes import design_vessel

    return design_vessel(VESSEL, inp.simulationArtifact, inp.fitArtifact, inp.vesselType, inp.klaMethod, "", ctx)


VESSEL_TOOL = register(
    Tool(
        name=VESSEL,
        description=(
            "Design on BioSTEAM the vessel a kept fermOS simulation needs: BioSTEAM's AeratedBioreactor (a stirred "
            "tank or a bubble column) for an aerobic simulation, its NREL batch fermenter for an anaerobic one or a "
            "kept kinetic fit. Pass the simulation's artifact id (or the fit's), the vessel type and a kLa correlation "
            "by name, or empty strings; never type a number. The design needs a plant scale or a batch volume, which "
            "only a named person types in fermOS → Vessel: without one the tool refuses in words, and you say in gaps "
            "that the design waits for it. A design is kept as an artifact, marked as yours, and comes back as one "
            "evidence id (the artifact's) with the vessels, volumes, times, powers, kLa, oxygen balance, heat and cost "
            "read from it; cite them by that id."
        ),
        input_model=FermosVesselInput,
        run=_vessel,
        strict=False,
    )
)
