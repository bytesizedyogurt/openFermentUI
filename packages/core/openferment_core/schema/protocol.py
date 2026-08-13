"""Protocols, their versions, and the state of a run against one.

Ported from `src/data/types.ts`. A `Protocol` is the executable half of the
platform: a `ProtocolVersion` is what a bench operator actually follows, a
`RunState` is where they are in it, and a `RunOutcome` is what the finished run
deposits back into openLab.

The phase brief for this migration listed only the first ten types
(`ProtocolCategory`, `ScalingClass`, `Material`, `Step`, `ProtocolVersion`,
`Protocol`, `Deviation`, `RunState`, `TimerState` and their inline objects).
`ResultField` and `RunOutcome` live here too, and are ported here rather than
left for a later module: `ProtocolVersion.resultSchema` is a list of
`ResultField`, and `RunOutcome` is what a finished run deposits, so both are
part of this concern even though the TypeScript declares them further down the
file under the openLab heading.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from ._base import OFModel
from .ontology import FieldId

__all__ = [
    "BaseBatch",
    "DecisiveMeasurement",
    "Deviation",
    "EstimatedMinutes",
    "Material",
    "Protocol",
    "ProtocolCategory",
    "ProtocolReference",
    "ProtocolVersion",
    "ResultField",
    "RunOutcome",
    "RunState",
    "ScalingClass",
    "Step",
    "StockSolution",
    "TimerState",
]


class ProtocolCategory(StrEnum):
    MEDIA = "media"
    CULTURE = "culture"
    ANALYTICS = "analytics"
    HARVEST = "harvest"
    FERMENTATION = "fermentation"
    SOP = "sop"


class ScalingClass(StrEnum):
    PER_BATCH_VOLUME = "per_batch_volume"
    FIXED = "fixed"
    PER_UNIT_BIOMASS = "per_unit_biomass"


class StockSolution(OFModel):
    """The stock a material is made up from, where it is not weighed out neat.

    Inline in the TypeScript (`stock?: { conc: number; unit: string }`); named
    here because Pydantic has no anonymous model.
    """

    conc: float = Field(
        gt=0,
        description=(
            "Strictly positive, and enforced rather than assumed. A stock of zero "
            "concentration is not a dilute stock, it is an absent one: no volume of it "
            "delivers any solute. Unconstrained, the two implementations disagreed about "
            "what to do with it — `scale_material` raises ZeroDivisionError while "
            "`scaleMaterial` yields Infinity, which the bench sheet then renders as an "
            "em dash, so a browser would print \"use — mL of stock\" while the pipeline "
            "crashed on the same protocol. The divergence was documented in scale.py and "
            "reachable by any curator; a constraint here makes it unauthorable instead, "
            "which is the only way a disagreement about an impossible input stops "
            "mattering."
        ),
    )
    unit: str


class Material(OFModel):
    name: str
    amount: float
    unit: str
    scaling: ScalingClass
    precision: float = Field(
        description=(
            "The rounding INCREMENT the scaled amount is snapped to, not a count of "
            "decimal places: 0.05 means 'to the nearest 0.05 g', and the corpus uses "
            "0.001 through 0.5. `roundToPrecision` in src/engine/units.ts is what "
            "consumes it, so that a scaled recipe stays pipettable at the bench "
            "rather than asking for 3.847 g."
        )
    )
    stock: StockSolution | None = None
    source_record_id: str | None = None


class Step(OFModel):
    id: str
    text: str = Field(description="may contain {{qty:materialName}} placeholders")
    # Timer durations are seconds but need not be whole ones, so float.
    timer_sec: float | None = None
    timer_label: str | None = None
    multi_check: list[str] | None = None
    note: str | None = None
    refs: list[str] | None = Field(default=None, description="record or paper ids")


class DecisiveMeasurement(OFModel):
    """The single uncertainty this protocol exists to resolve (OF-FE-003 §4.5).

    This is the return leg of the experiment loop: a sensitivity tornado names
    the parameter whose uncertainty moves the answer most, and a protocol that
    declares itself the measurement for that parameter is what turns the naming
    into work someone can do. Without it the loop points at a parameter page and
    stops.

    Inline in the TypeScript (`decisive?: { ... }`); named here because Pydantic
    has no anonymous model.
    """

    field: FieldId
    current_uncertainty: str = Field(
        description="Plain sentence: what is not known, and why it matters here."
    )
    what_would_change: str = Field(
        description='What a result would settle — "if below X, design D2 wins".'
    )


class BaseBatch(OFModel):
    """The batch size every material amount in this version is stated at.

    Inline in the TypeScript (`baseBatch: { value: number; unit: string; label:
    string }`); named here because Pydantic has no anonymous model.
    """

    value: float
    unit: str
    label: str


class EstimatedMinutes(OFModel):
    """Hands-on and wall-clock time for a version.

    Inline in the TypeScript (`estMinutes: { active: number; total: number }`);
    named here because Pydantic has no anonymous model. These are minutes and
    may be fractional, so float rather than int.
    """

    active: float
    total: float


class ProtocolReference(OFModel):
    """One entry in `ProtocolVersion.references`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model. Every member is optional in the TypeScript and stays optional here —
    a reference may point at a corpus entry, at an extraction record, or be a
    bare note.
    """

    paper_id: str | None = None
    record_id: str | None = None
    note: str | None = None


class ProtocolVersion(OFModel):
    version: str
    changelog: str | None = None
    decisive: DecisiveMeasurement | None = None
    result_schema: list[ResultField] | None = Field(
        default=None,
        description="Shape of the result form an openLab deposit generates from a run.",
    )
    base_batch: BaseBatch
    materials: list[Material]
    equipment: list[str]
    safety: list[str]
    steps: list[Step]
    est_minutes: EstimatedMinutes
    references: list[ProtocolReference]


class Protocol(OFModel):
    id: str
    title: str
    category: ProtocolCategory
    organisms: list[str]
    # Biosafety level is a two-valued classification here, not a measurement.
    bsl: Literal[1, 2]
    purpose: str
    versions: list[ProtocolVersion]
    current_version: str
    provenance_note: str


class Deviation(OFModel):
    at: str
    step_id: str
    text: str


class RunState(OFModel):
    id: str
    protocol_id: str
    version: str
    scale: float = Field(description="multiplier vs baseBatch")
    started_at: float = Field(description="epoch ms")
    # Which step the operator is on — an index into `steps`, so int.
    current_step: int
    completed: dict[str, float] = Field(description="stepId -> epoch ms completed")
    skipped: dict[str, str] = Field(description="stepId -> reason")
    checks: dict[str, list[bool]] = Field(description="stepId -> multiCheck states")
    deviations: list[Deviation]
    timers: list[TimerState]
    finished_at: float | None = Field(default=None, description="epoch ms")


class TimerState(OFModel):
    id: str
    step_id: str
    label: str
    # Timer durations are seconds but need not be whole ones, so float.
    total_sec: float
    remaining_sec: float
    running: bool
    started_at: float | None = Field(default=None, description="epoch ms")


class RunOutcome(OFModel):
    """A failed run is a first-class outcome, not an error."""

    run_id: str
    outcome: Literal["success", "failure", "abandoned"]
    failure_reason: str | None = Field(
        default=None,
        description="Real bench prose: contamination, a pump, an ambiguous reading.",
    )
    results: dict[str, float | str | bool]
    operator: str
    deposited_at: str | None = None
    produced_record_ids: list[str] = Field(
        description="Records created by this deposit — evidenceClass: 'experiment'."
    )


class ResultField(OFModel):
    id: str
    field: FieldId | None = None
    label: str
    type: Literal["number", "text", "boolean"]
    unit: str | None = None
    required: bool


# `ProtocolVersion.resultSchema` and `RunState.timers` are declared above the
# models they refer to, matching the order of `src/data/types.ts`; the forward
# references are resolved here.
ProtocolVersion.model_rebuild()
RunState.model_rebuild()
