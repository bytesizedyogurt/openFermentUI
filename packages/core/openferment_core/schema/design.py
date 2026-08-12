"""Parchment claims and the design-record tier cascade — OF-FE-003 §4.4 and
OF-FE-004 §2.

Ported from `src/data/types.ts`. As with `ledger.py`, this module is not in the
migration brief's module list: the brief was enumerating an earlier `types.ts`,
and by the time the port ran these types were real and the application imported
them. Generating a `types.ts` without them would have broken the build.

Two concerns share the file because they are the same argument made twice. A
Parchment claim is only useful because its bounds are expressed in the corpus
ontology, and a design record is only honest because a tier that did not run
says so. Both refuse to let an unevaluated thing read as a cleared one.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from ._base import OFModel
from .ontology import FieldId

__all__ = [
    "ClaimBound",
    "ClaimScope",
    "DesignRecord",
    "EmbargoStatus",
    "MSPDistribution",
    "Patent",
    "PatentStatus",
    "PublicationStatus",
    "ScopeHit",
    "SensitivityEntry",
    "Tier",
    "TierResult",
    "TierState",
    "TierValue",
]


# ── OF-FE-003 §4.4 — Parchment ─────────────────────────────────────────


class ClaimBound(OFModel):
    """One bound in `ClaimScope.bounds`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    field: FieldId
    # The six members are operators rather than words, and `Literal` keeps them
    # legible as such — a StrEnum would have to invent names (LT, LTE, …) that
    # appear nowhere in the corpus.
    op: Literal["<", "<=", ">", ">=", "in", "eq"]
    # `number | [number, number] | string` in the TypeScript. The order is the
    # TypeScript's own; Pydantic's smart mode picks by input shape rather than by
    # position, so a range arrives as a tuple and a categorical bound stays a
    # string.
    value: float | tuple[float, float] | str
    unit: str | None = None


class ClaimScope(OFModel):
    number: int  # a claim number, not a measurement
    independent: bool
    bounds: list[ClaimBound] = Field(
        description=(
            "Claim scope expressed in the SAME ontology as the literature. This "
            "comparability is the entire value of Parchment: it is what lets a Ledger "
            "record be tested against a claim instead of read beside it."
        )
    )
    raw_text: str
    parse_uncertain: bool | None = Field(
        default=None,
        description="True when the parse is uncertain. Never render a shaky parse as confident.",
    )


class PatentStatus(StrEnum):
    PENDING = "pending"
    GRANTED = "granted"
    LAPSED = "lapsed"
    REVOKED = "revoked"


class Patent(OFModel):
    id: str
    jurisdiction: str
    number: str  # the published patent number, a string — not a count
    title: str
    assignee: str
    priority_date: str
    status: PatentStatus
    claims: list[ClaimScope]
    verify_needed: bool | None = Field(
        default=None,
        description="Same discipline as papers: no invented identifiers, ever.",
    )
    paper_id: str | None = Field(
        default=None, description="The corpus entry this was catalogued from."
    )


# ── OF-FE-004 §2 — design records and the tier cascade ─────────────────


class Tier(StrEnum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"


class TierState(StrEnum):
    """A tier either ran or it did not. `absent` is a first-class state, not a
    failure and not a pass: T1 needs a genome-scale model and T2 a reactor model,
    and neither exists in this build. Rendering an absent tier as passed would
    claim the biology was checked when only the economics were modelled.
    """

    PASSED = "passed"
    FAILED = "failed"
    ABSENT = "absent"


class TierValue(OFModel):
    """One entry in `TierResult.values` — a number with the unit it was computed in.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    value: float
    unit: str


class MSPDistribution(OFModel):
    """The minimum selling price as a distribution, in `TierResult.msp`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    median: float
    p05: float
    p95: float
    unit: str


class SensitivityEntry(OFModel):
    """One row of `TierResult.sensitivity`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    field: FieldId | None = None
    label: str
    rho: float


class TierResult(OFModel):
    tier: Tier
    state: TierState
    absent_reason: str | None = Field(
        default=None,
        description="Why the tier is absent, when it is. Shown in place of a result.",
    )
    binding_constraint: str = Field(
        description="The constraint that bound the result — the most useful string on the page."
    )
    values: dict[str, TierValue]
    msp: MSPDistribution | None = Field(
        default=None,
        description="T3 only. Never a bare point estimate presented as a distribution.",
    )
    sensitivity: list[SensitivityEntry] | None = Field(
        default=None,
        description="T3 only, sorted by |rho| descending. Drives the experiment loop.",
    )
    engine_version: str


class EmbargoStatus(OFModel):
    """The one object member of `PublicationStatus`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model. An embargo is the only publication state that carries data — the date
    it lifts — which is why it alone is an object.
    """

    kind: Literal["embargo"] = "embargo"
    until: str


# A union of a scalar and an object, which is unusual and is what the TypeScript
# actually says: five bare string literals plus one `{ kind: 'embargo'; until }`.
# It is not a discriminated union — only the object member has a `kind` — so the
# members are matched by shape.
PublicationStatus = (
    Literal["draft", "counsel-review", "hold", "publish", "published"] | EmbargoStatus
)


class ScopeHit(OFModel):
    """One patent claim this design falls within, in `DesignRecord.scopeHits`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    patent_id: str
    claim: int  # a claim number, not a measurement


class DesignRecord(OFModel):
    id: str
    label: str
    scenario_id: str
    config: dict[str, float]
    tiers: list[TierResult]
    consumed_record_ids: list[str] = Field(
        description="Exact records consumed — the basis for staleness."
    )
    scope: Literal["clear", "adjacent", "claimed"] = Field(
        description=(
            "'clear' means Parchment has not evaluated this design, NOT that it is "
            "unencumbered. Parchment holds no parsed claim bounds, so it cannot decide; "
            "the word must never imply it did."
        )
    )
    scope_evaluated: bool
    scope_hits: list[ScopeHit]
    publication: PublicationStatus
