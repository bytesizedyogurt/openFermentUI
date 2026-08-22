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
    "AccuracyClass",
    "AccuracyStated",
    "AccuracyUnstated",
    "AssumptionBasis",
    "BasisModel",
    "BasisRecord",
    "BasisUnsourced",
    "CostIndex",
    "CostLine",
    "FxTreatment",
    "GridPointResult",
    "QuotationBasis",
    "Region",
    "RegionDeclared",
    "RegionUndeclared",
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


# ── The frame a price is quoted in ────────────────────────────────────────
#
# A techno-economic result is a function of two things: the flowsheet, and the
# basis it is discounted and indexed against. The flowsheet gets a whole screen.
# The basis usually gets a footnote — which is how two plants end up compared at
# two different discount rates and nobody notices.
#
# `AssumptionBasis` above is a different thing and the names must not be
# confused: that says where ONE NUMBER came from, this says what frame a PRICE
# is quoted in. A record binding and a discount rate are not the same kind of
# claim.
#
# WHY THIS IS PYTHON. Every member is a BioSTEAM TEA constructor argument — IRR,
# duration, income tax, operating days, the cost index — and CLAUDE.md routes
# cost-model authoring to BioSTEAM. More decisively, `EconomicsAdapter` has to
# be able to return one: a server that hands back a minimum selling price
# without the basis it was solved against has handed back a number, not an
# answer. A TypeScript-only twin would be hand-maintained the day that server
# exists, which is the failure this package exists to prevent.


class CostIndex(OFModel):
    """The index a capital estimate is scaled to.

    A correlation fitted against 2007 quotations returns 2007 dollars. Dropping
    the ratio is not a rounding error, it is a different answer, and it is the
    easiest way to make a capital estimate look cheap without lying about
    anything a reviewer can see.
    """

    name: str = Field(description="e.g. 'CEPCI' — the index, not the value.")
    year: int | None = Field(
        default=None,
        description=(
            "The year the index value is taken from. None means the value was set "
            "directly rather than chosen from a year, which is a legitimate thing to "
            "do and a thing a reader is entitled to be told."
        ),
    )
    value: float
    covers: tuple[int, int] | None = Field(
        default=None,
        description=(
            "The years the index table actually spans. Stated because a project "
            "priced outside that span is being indexed by extrapolation, and the "
            "gap is a fact about the estimate rather than a bug to paper over."
        ),
    )
    note: str = ""


class FxTreatment(OFModel):
    """How a conversion between currencies was performed, when one was.

    A floating rate makes two identical quantities disagree by the date they
    were viewed. Whatever is done here, it is stated.
    """

    pair: str = Field(description="e.g. 'EUR/USD'.")
    rate: float
    as_of: str | None = Field(
        default=None,
        description="ISO date, or None when the rate is fixed by convention rather than dated.",
    )
    note: str = ""


class RegionDeclared(OFModel):
    """A stated place, with whatever adjustment that place implies."""

    kind: Literal["declared"] = "declared"
    jurisdiction: str = Field(description="ISO country or jurisdiction code, e.g. 'RW', 'US'.")
    locality: str | None = None
    location_factor: float | None = Field(
        default=None,
        description=(
            "Multiplier applied to installed capital for this location. None means no "
            "factor was applied, which is different from a factor of 1.0 — one is a "
            "decision not to adjust, the other is a claim that no adjustment is due."
        ),
    )
    source: str = Field(description="What established the factor, or how the place was chosen.")


class RegionUndeclared(OFModel):
    """No place has been stated, and the reason is carried rather than implied.

    NOT A DEFECT, unlike `BasisUnsourced`. A corpus of β-casein literature says
    nothing about where a plant would be built, so naming a region would be
    fabrication. This is the same move as `year: 0` and the venue sentinel: the
    gap is shown rather than guessed.
    """

    kind: Literal["undeclared"] = "undeclared"
    why: str


Region = Annotated[RegionDeclared | RegionUndeclared, Field(discriminator="kind")]


class AccuracyStated(OFModel):
    """An estimate that declares how wrong it may be.

    AACE Class 5 carries −30/+50 %. A crisp line drawn without that band is a
    promise the number cannot keep.
    """

    kind: Literal["class"] = "class"
    label: str = Field(description="e.g. 'AACE Class 5 (−30 / +50 %)'.")
    low_pct: float
    high_pct: float


class AccuracyUnstated(OFModel):
    """No class has been assigned, and that is said rather than left to be assumed."""

    kind: Literal["unstated"] = "unstated"
    why: str


AccuracyClass = Annotated[AccuracyStated | AccuracyUnstated, Field(discriminator="kind")]


class QuotationBasis(OFModel):
    """Everything a price has to declare before it means anything.

    `excludes` is the field the whole model exists for. A basis that lists what
    it covers is marketing; one that lists what it does not is an estimate.
    """

    stated_for: str = Field(
        description="The model, plant or concept this frames. A basis has an address too."
    )
    currency: str = "USD"
    fx: FxTreatment | None = Field(
        default=None, description="None means no conversion was performed."
    )
    cost_index: CostIndex
    discount_rate: float | None = None
    discount_rate_kind: Literal["IRR", "capital-charge"] = Field(
        default="IRR",
        description=(
            "An internal rate of return solved against a full cash flow and a flat "
            "capital charge applied to installed cost are different claims, and a "
            "reader comparing two numbers has to know which they are looking at."
        ),
    )
    project_life: tuple[int, int] | None = None
    income_tax: float | None = None
    tax_note: str = ""
    operating_days: int | None = None
    region: Region
    accuracy: AccuracyClass
    excludes: list[str] = Field(
        description=(
            "What is explicitly NOT in this price, in a reader's words. Required and "
            "non-empty: every estimate excludes something, and an empty list means "
            "nobody has looked rather than that nothing is missing."
        ),
        min_length=1,
    )
