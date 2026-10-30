"""fermOS's tools: `growth_forecast` (OF-BLD-014 §7.3), `fermos_simulate`
(OF-BLD-020 §3.4) and `fermos_vessel` (OF-BLD-020 §4.2).

`growth_forecast`: a band for the next run, from a fitted one. Ids in: a
kept kinetic fit's artifact id. The forecast runs under the fitted run's own
starting values and length; one `Evidence` comes back with the hint
`trajectory`. A fit whose growth rate or ceiling the run did not identify is
refused, and the refusal says what run would identify it.

`fermos_simulate` (D13): ids and words in, a kept simulation out. A model
family's id, a strain, a product and a sugar by their ids, the records that
bind a parameter by their ids (`recordsByParam`), a kept fit's artifact id,
where to start (`records`, `fit` or `simulation:<artifact id>`) and a
run-length preset. A number anywhere refuses the call, as the registry does
for every tool, and no field of its schema is numeric (E.4‴, `check:tools`).
It is a free write, the same run as `fermos_write`'s `simulate`
(`tools/writes.py`'s `run_simulation`, the one call to `fermos.simulate`, so
`check:tools` reads it there), at no gate, audited with the model as agent.
The service holds no person's assumption, so a parameter nothing binds
waits, and the call returns the refusal's words. It returns the simulation
as one `Evidence` whose id is the artifact's, and a summary that names the
family, what bound each parameter (in words and counts; the values are in
the artifact) and the artifact id.

`fermos_vessel` (D7, D13): the vessel a kept simulation needs, designed on
BioSTEAM. Ids and words in: a kept simulation's artifact id (or, anaerobic, a
kept kinetic fit's), the vessel type (`stirred-tank` or `bubble-column`) and a
kLa correlation by BioSTEAM's own name; every field is a string (E.4‴). It is
a free write, offered loose like the module tools: it keeps one
`fermos.vessel` artifact through `writes.design_vessel`, the function
`fermos_write`'s `design_vessel` runs, audited with the model as agent. A
design needs a plant scale or one vessel's batch volume, which only a named
person types (in fermOS → Vessel); the service holds none, so without one the
tool returns the refusal's words. A design comes back as one `Evidence` whose
id is the artifact's; its numbers are read from it, never stated by the model.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import fermos, kinetics
from ..models import SimulationRequest, ToolResult
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


# ── fermos_simulate (OF-BLD-020 §3.4, D13) ────────────────────────────────

SIM_NAME = "fermos_simulate"


def _offered() -> list[str]:
    """The families a description may name: every family kinetics.py holds."""
    return list(kinetics.FAMILIES)


def _bindable(families: list[str]) -> str:
    """The offered families' parameters a record can bind, each with its
    fields and, when not every family has it, the families that do: what
    recordsByParam takes, in words."""
    running = [f for f in families if not kinetics.FAMILIES[f].socket]
    keys: dict[str, tuple[str, list[str]]] = {}
    for fid in running:
        for spec in kinetics.FAMILIES[fid].specs():
            fields = [e.split(":", 1)[1] for e in spec.sourceRule if e.startswith("record:")]
            if fields:
                keys.setdefault(spec.key, (" or ".join(fields), []))[1].append(fid)
    return ", ".join(f"{k} ({fields}" + ("" if len(fams) == len(running) else f"; {', '.join(fams)}") + ")"
                     for k, (fields, fams) in keys.items())


_FAMILIES = _offered()


class FermosSimulateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str = Field(description=(
        "A model family's id" + (f" ({', '.join(_FAMILIES)})" if _FAMILIES else "")
        + "; GET /api/fermos/families and fermOS → Simulate list them with their equations."))
    strain: str = Field("", description=(
        "A strain's id from geneOS's hosts (geneos_read, kind host), or an empty string: then the records of every "
        "strain bind."))
    product: str = Field("", description="The product's id (ethanol), or an empty string.")
    sugar: str = Field("", description="The sugar's carbon-source id (glucose), or an empty string.")
    recordsByParam: dict[str, list[str]] = Field(default_factory=dict, description=(
        "A parameter's key to the record ids that bind it, exactly those records (search_records returns them): "
        "each must be a record of a field the parameter binds from, kept by the aggregate gate. Ids only, never a "
        "value. An empty object, and the records the rule finds bind each parameter."))
    fitArtifact: str = Field("", description=(
        "A kept kinetic fit's or forecast's artifact id (fermos_read lists them), whose parameters bind first; or an "
        "empty string."))
    startFrom: str = Field("records", description=(
        "records, fit (the fit named in fitArtifact), or simulation:<artifact id> (a kept simulation's values bind "
        "where no fit or record does)."))
    durationPreset: Literal["until-sugar-runs-out", "fit-length"] = Field("until-sugar-runs-out", description=(
        "until-sugar-runs-out (the run ends when the sugar runs out), or fit-length (as long as the fitted run, "
        "with a fit named)."))


def _simulate(inp: FermosSimulateInput, ctx: ToolContext) -> ToolResult:
    from .writes import run_simulation

    req = SimulationRequest(family=inp.family, strain=inp.strain.strip() or None, product=inp.product.strip() or None,
                            sugar=inp.sugar.strip() or None, fitArtifact=inp.fitArtifact.strip() or None,
                            startFrom=inp.startFrom.strip() or "records", durationPreset=inp.durationPreset,
                            recordsByParam={k: list(v) for k, v in inp.recordsByParam.items()})
    return run_simulation(SIM_NAME, req, "", ctx)


SIMULATE_TOOL = register(
    Tool(
        name=SIM_NAME,
        description=(
            "Simulate a fermentation with one of fermOS's model families (batch with Monod growth, product and "
            "substrate inhibition and Luedeking–Piret production; fed-batch; chemostat) and keep it: one artifact "
            "holding the time course of cells, sugar and product, the oxygen uptake, the end state, the hour the "
            "sugar runs out, the mass balance and the product yield beside the geneOS ceiling. Each parameter binds "
            "from a fit you name, the records (the ones you name for it in recordsByParam, else those the rule "
            "finds for the strain and sugar), a kept simulation, or a stated convention, and the summary says what "
            "bound each one. You never type a number: name the family, the strain, the product, the sugar, record "
            "ids and artifact ids. A parameter nothing binds waits for a named person's assumption, typed in "
            "fermOS → Simulate; the call then refuses and names each parameter that waits and the field that would "
            "bind it, and nothing is kept. Returns one evidence id to cite (the simulation's artifact id): a titre, "
            "a yield or a productivity read from a simulation is cited by it and never stated. It spends no model "
            "money and is at no gate; the simulation is marked as yours in the audit log until a person promotes it."
            + (f" The parameters a record can bind, with the fields they bind from: {_bindable(_FAMILIES)}."
               if _FAMILIES else "")
            + (" light_v1 is declared and not built: it refuses in words." if "light_v1" in _FAMILIES else "")
        ),
        input_model=FermosSimulateInput,
        run=_simulate,
        strict=False,
    )
)


# ── fermos_vessel (OF-BLD-020 §4.2, D7, D13) ───────────────────────────────

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
