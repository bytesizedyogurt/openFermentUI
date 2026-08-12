"""Ledger, referee, and aggregate — OF-FE-003 §4.

Ported from `src/data/types.ts`. This module is not in the migration brief's
module list: the brief was enumerating an earlier `types.ts`, and by the time
the port ran these four types were real and the application imported them.
Generating a `types.ts` without them would have broken the build. They live in
their own module rather than in `records.py` because they are Ledger concerns —
what the referee says about a *set* of records, and what an aggregate over that
set is allowed to claim — not record concerns.

`Contradiction.note` carries a documented requirement ("Required when status
leaves 'open'") that is deliberately NOT enforced by a `model_validator` here.
The TypeScript only documents it; adding the check would invent behaviour the
source does not have, and a model that rejects data the TypeScript accepts is a
second implementation that disagrees with the first. The comment ports; the rule
does not.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ._base import OFModel
from .ontology import FieldId, ParameterDef

__all__ = [
    "Aggregate",
    "AggregateStratum",
    "ConsistentStatus",
    "ConstraintCheck",
    "ContradictedStatus",
    "Contradiction",
    "ContradictionKind",
    "ContradictionStatus",
    "DetectedBy",
    "ExcludedRecord",
    "ParameterView",
    "RefereeStatus",
    "UncheckedStatus",
]


class ContradictionKind(StrEnum):
    BALANCE = "balance"
    SPECIFICATION = "specification"
    SCALE = "scale"
    DIRECT = "direct"


class DetectedBy(StrEnum):
    BALANCE = "balance"
    FLUX = "flux"
    REACTOR = "reactor"
    ONTOLOGY = "ontology"
    MANUAL = "manual"


class ContradictionStatus(StrEnum):
    OPEN = "open"
    EXPLAINED = "explained"
    RESOLVED = "resolved"


class ConstraintCheck(OFModel):
    """The machine form of a contradiction, for the referee panel.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    expression: str
    residual: float
    tolerance: float
    unit: str


class Contradiction(OFModel):
    """A set of entries that cannot all be true. The referee flags the *set*;
    it does not need to identify which member is wrong to be useful.
    """

    id: str
    kind: ContradictionKind
    record_ids: list[str] = Field(description="Every participating record. Minimum two.")
    statement: str = Field(
        description="One plain sentence a non-specialist can read. Rendered as the headline."
    )
    constraint: ConstraintCheck = Field(description="Machine form for the referee panel.")
    detected_by: DetectedBy
    status: ContradictionStatus
    note: str | None = Field(
        default=None,
        description="Required when status leaves 'open'. Displayed permanently.",
    )


class UncheckedStatus(OFModel):
    state: Literal["unchecked"] = "unchecked"


class ConsistentStatus(OFModel):
    state: Literal["consistent"] = "consistent"
    checks: list[str]


class ContradictedStatus(OFModel):
    state: Literal["contradicted"] = "contradicted"
    contradiction_ids: list[str]


RefereeStatus = Annotated[
    UncheckedStatus | ConsistentStatus | ContradictedStatus,
    Field(discriminator="state"),
]
"""Never imply a check that did not run: 'unchecked' and 'consistent' are
different claims, and 'consistent' has to name which checks it passed.
"""


class AggregateStratum(OFModel):
    """One grouping in `Aggregate.strata` — by organism, by method, by year.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    key: str
    label: str
    n: int  # a count of records, not a measurement
    median: float


class Aggregate(OFModel):
    """Deliberately not a Bayesian posterior. With 134 curated records and none
    verified, a hierarchical fit would be false precision. Median-of-primary with
    a visible interquartile range is honest at this corpus size, and this shape
    lets a posterior replace the internals later without any screen changing.
    """

    median: float
    p25: float
    p75: float
    min: float
    max: float
    n: int  # a count of contributing records
    n_primary: int  # likewise a count
    unit: str
    strata: list[AggregateStratum] = Field(
        description="Grouping actually used — by organism, by method, by year."
    )
    method: str = Field(description="Named, so a screen can say how the number was produced.")


class ExcludedRecord(OFModel):
    """One record held out of the aggregate, with the reason.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    record_id: str
    reason: str


class ParameterView(OFModel):
    """Derived at load from RECORDS. Never seeded — see engine/posterior.ts."""

    field: FieldId
    def_: ParameterDef = Field(alias="def")
    record_ids: list[str]
    aggregate: Aggregate | None = Field(
        description="Only records passing isAggregatable() contribute."
    )
    contradictions: list[Contradiction]
    referee: RefereeStatus
    excluded: list[ExcludedRecord] = Field(
        description="Records held out of the aggregate, each with the reason."
    )
