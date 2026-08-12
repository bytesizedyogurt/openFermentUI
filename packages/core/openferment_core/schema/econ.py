"""Cost scenarios, sweep axes, and where an assumption's number comes from.

Ported from `src/data/types.ts`. `AssumptionBasis` is the piece to read first:
it is the discriminator that keeps a cost assumption attached to the record it
came from, and its docstring explains why that attachment is the architecture's
central circuit.

Two neighbouring types in the TypeScript are deliberately NOT modelled here.

`CostModel` carries `evaluate: (point) => Record<CostLine, number>`, a
FUNCTION. Neither Pydantic nor JSON Schema can express a function, and a model
that dropped the field would generate a TypeScript interface missing the only
member anything calls. It stays hand-written in TypeScript.

`ResultGrid` carries `Float64Array` members, which is a JavaScript typed array
with no JSON Schema equivalent. Same treatment.

Both are runtime shapes rather than data shapes, and saying so is more honest
than approximating them.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ._base import OFModel
from .corpus import Provenance
from .ontology import FieldId

__all__ = [
    "AssumptionBasis",
    "BasisModel",
    "BasisRecord",
    "BasisUnsourced",
    "CostLine",
    "GridPointResult",
    "Scenario",
    "ScenarioAssumption",
    "ScenarioDim",
    "SensitivityRow",
]


class CostLine(StrEnum):
    CAPEX = "capex"
    MEDIA = "media"
    UTILITIES = "utilities"
    LABOR = "labor"
    DOWNSTREAM = "downstream"
    OTHER = "other"


class ScenarioDim(OFModel):
    paper_id: str | None = Field(
        default=None,
        description="Cite a paper where a sweep default came from the literature.",
    )
    key: str
    label: str
    unit: str
    values: list[float]
    source_record_id: str | None = None
    field: FieldId | None = Field(
        default=None,
        description=(
            "The ontology parameter this dimension sweeps, where it is one. Set only for "
            "dimensions that vary a Ledger parameter — a fermenter scale or a milk price "
            "is a process or market input, not a parameter the corpus measures, and must "
            "not claim otherwise. T0 checks a configured value against this field's "
            "declared range."
        ),
    )


class BasisRecord(OFModel):
    """Bound to a Ledger record. The value must equal that record's SI value."""

    kind: Literal["record"] = "record"
    record_id: str


class BasisModel(OFModel):
    """A deliberate modeling choice, or a literature value the ontology has no
    field to hold. Legitimate, but must declare itself in writing.
    """

    kind: Literal["model"] = "model"
    justification: str


class BasisUnsourced(OFModel):
    """DEFECT. A number with no record and no declared justification."""

    kind: Literal["unsourced"] = "unsourced"


AssumptionBasis = Annotated[BasisRecord | BasisModel | BasisUnsourced, Field(discriminator="kind")]
"""Where a scenario assumption's number comes from (OF-FE-004 §1.1).

The architecture's central circuit is: cost sensitivity names the dominant
uncertainty, a protocol measures it, the result updates the record, every
design re-scores. With assumptions citing papers rather than records that
circuit is severed at its most important joint — a corrected record cannot
reach an MSP. This discriminator is what closes it.
"""


class ScenarioAssumption(OFModel):
    paper_id: str | None = Field(
        default=None,
        description="Cite a paper when the assumption rests on a source but no single record.",
    )
    label: str
    value: float
    unit: str
    provenance: Provenance
    record_id: str | None = None
    basis: AssumptionBasis = Field(
        description="Required. `check:seed` verifies a record binding against the record."
    )
    note: str


class Scenario(OFModel):
    id: str
    model_id: Literal["S1", "S2", "S3"]
    name: str
    description: str
    product: str
    dims: list[ScenarioDim]
    point: dict[str, float]
    assumptions: list[ScenarioAssumption]
    pinned: bool


class GridPointResult(OFModel):
    msp: float
    cost_lines: dict[CostLine, float]


class SensitivityRow(OFModel):
    assumption: str
    # Percentages, not counts — a tornado bound can be -12.5%.
    low_pct: float
    hi_pct: float
    field: FieldId | None = Field(
        default=None,
        description=(
            "The parameter this row varies, when the assumption behind it is "
            "record-bound. Makes each tornado bar a link to its parameter page, which is "
            "the entry to the whole experiment loop and the single most valuable "
            "navigation in the app."
        ),
    )
