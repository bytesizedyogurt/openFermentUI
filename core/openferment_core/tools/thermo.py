"""`thermo_props`: what thermosteam says of a mixture on file (OF-BLD-019 §4.2, D9).

Ids and words in, never a number: a Proforma run's artifact id with one of
its streams, or a preset the service fills — `ethanol-water-azeotrope`, or
`beer-at-titre-of` with an ethanol titre record's id. The service reads the
composition, temperature and pressure from what is on file (thermo.py), the
Proforma worker asks thermosteam, and the answer is kept as one
`thermo_props` artifact. Each property the library answered comes back as
its own `Evidence`, citable by its id like any computed value (`SeenSet`
keeps it, `validate_plan` takes its provenance); a chemical the library
lacks, a stream not on file or a record that is no titre is refused in words.

Offered loose, the module tools' way (OF-BLD-015 §7.2): every field is a
string and an empty one means "not this".
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .. import thermo
from ..models import ThermoPropsRequest, ToolResult
from ..workers import WorkerCrashed, WorkerError, WorkerTimeout
from . import Tool, ToolContext, register

NAME = "thermo_props"
# How many components of a mixture the summary names, largest first; the
# artifact holds every one.
MAX_COMPONENTS = 12


class ThermoPropsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifactId: str = Field(description="A Proforma run's artifact id (tool proforma.run), with streamId; or an empty string.")
    streamId: str = Field(description="One stream of that run's stream table, by its id; or an empty string.")
    preset: str = Field(description=(
        f"{thermo.AZEOTROPE} (the composition thermosteam's own vapour-liquid equilibrium gives), or {thermo.BEER} "
        "with recordId (water and ethanol at that record's titre); or an empty string when a stream is named."))
    recordId: str = Field(description=f"An ethanol titre record's id (field {thermo.TITRE_FIELD}), for {thermo.BEER}; or an empty string.")


def _hidden_run(aid: str, ctx: ToolContext) -> str | None:
    """With the switch off, a run of an archived program is refused as its
    train is hidden (OF-BLD-016 §2.R); the switch is never an input. The rule
    is every reader's (`module_stores.hidden_run_refusal`, OF-BLD-019 §6.R)."""
    from .. import artifacts, module_stores

    if ctx.include_archived or not aid:
        return None
    try:
        art = artifacts.get(aid)
    except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged):
        return None  # said by the service below, in its words
    if art.tool != thermo.RUN:
        return None
    return module_stores.hidden_run_refusal(NAME, art, ctx.include_archived)


def _run(inp: ThermoPropsInput, ctx: ToolContext) -> ToolResult:
    req = ThermoPropsRequest(artifactId=inp.artifactId, streamId=inp.streamId, preset=inp.preset, recordId=inp.recordId)
    refused = _hidden_run(inp.artifactId.strip(), ctx)
    if refused:
        return ToolResult(error=refused)
    try:
        kind, _ = thermo.question(req)
        art = thermo.props(req, pool=ctx.pool if kind == thermo.BEER else None)
    except (thermo.ThermoRefused, thermo.ThermoNotFound) as e:
        return ToolResult(error=f"{NAME} refused: {e}")
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        return ToolResult(error=f"{NAME} could not ask thermosteam: {e}")
    o = thermo.output_of(art)
    evidence = thermo.evidence_of(art)
    biggest = sorted(o.massFractions.items(), key=lambda kv: -kv[1])[:MAX_COMPONENTS]
    return ToolResult(
        summary={
            "artifactId": art.id,
            "subject": o.subject,
            "library": o.library,
            "provenance": art.provenance,
            "conditions": {"T": o.T, "P": o.P, "phase": o.phase, "TSource": o.TSource, "PSource": o.PSource,
                           "units": {"T": o.units.get("T"), "P": o.units.get("P")}},
            "massFractions": dict(biggest),
            "componentsNotListed": max(0, len(o.massFractions) - len(biggest)),
            "properties": [{"evidenceId": e.id, "what": e.label, "value": e.value, "unit": e.unit} for e in evidence],
            "solved": o.solved,
            "notes": o.notes,
            "meaning": "what thermosteam, BioSTEAM's property engine, computes for this mixture from its own chemical "
                       "models; each property is cited by its evidence id",
        },
        evidence=evidence,
    )


TOOL = register(
    Tool(
        name=NAME,
        description=(
            "Density, heat capacity, viscosity, and bubble and dew points of a mixture already on file, as thermosteam "
            "(BioSTEAM's property engine) computes them, kept as a computed value with its basis. Name a Proforma run's "
            f"artifact id and one of its streams; or the preset {thermo.AZEOTROPE}; or {thermo.BEER} with an ethanol "
            "titre record's id (water and ethanol at that titre; the beer's cells and sugar are not in it). The service "
            "fills every number from what is on file. Returns one evidence id a property to cite. A chemical the "
            "library lacks is refused in words naming it."
        ),
        input_model=ThermoPropsInput,
        run=_run,
        strict=False,
    )
)
