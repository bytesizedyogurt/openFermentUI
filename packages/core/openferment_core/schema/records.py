"""Extraction records, their audit trail, and extractor-run output.

Ported from `src/data/types.ts`, with `isAggregatable` and `aggregateExclusion`
brought over from `src/engine/aggregation.ts` and attached to
`ExtractionRecord` itself. In the TypeScript they are free functions in the
engine layer because that layer may not import app state; in Python the record
is the natural home, and putting the gate on the model means nothing can hold a
record without also holding the rule that decides whether it counts.

The docstrings came with the types. They record why a citation of a
measurement is not a measurement, why `undetermined` is a legitimate method,
and why an excluded record still renders. They are not decoration.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from ._base import OFModel
from .corpus import EvidenceClass, Provenance
from .ontology import AnalysisMethod, FieldId, NumberingConvention

__all__ = [
    "EXCLUSION_NOTE",
    "AggregateExclusion",
    "AuditEvent",
    "CorrectedValue",
    "CuratorNote",
    "ExtractedValue",
    "ExtractionRecord",
    "ExtractorRun",
    "FalsePositive",
    "GoldValue",
    "RecordStatus",
    "RunOutcomeKind",
    "RunOutput",
    "RunResult",
    "SIValue",
    "ValueRange",
]


class RecordStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ExtractorRun(StrEnum):
    V0_3 = "v0.3"
    V0_4 = "v0.4"
    V0_4R = "v0.4r"


class AuditEvent(OFModel):
    at: str
    who: str
    action: str
    # `from` is a Python keyword, so the field is `from_` with an explicit
    # alias. `to` is given the same explicit-alias treatment purely for
    # symmetry: the two are a pair, they are read as a pair, and writing one
    # with a hand alias and the other without invites a later reader to think
    # the difference is meaningful. `to_camel('to')` is 'to' anyway, so the
    # explicit alias changes nothing on the wire.
    from_: Any = Field(default=None, alias="from")
    to: Any = Field(default=None, alias="to")


class SIValue(OFModel):
    """`ExtractionRecord.si` — the value in its canonical SI unit.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    value: float
    unit: str


class GoldValue(OFModel):
    """`ExtractionRecord.gold` — the gold-set answer this record is scored
    against.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model. Its `value` is `number | string` where `CorrectedValue.value` is
    `number` alone: a gold answer may be categorical (kinase_identity,
    glycan_species) while a reviewer correction, as the TypeScript has it, may
    not. That asymmetry is in the TypeScript and is reproduced, not fixed —
    changing it here would put the two implementations out of agreement, which
    is the exact failure this migration exists to prevent.
    """

    value: float | str
    unit: str


class CorrectedValue(OFModel):
    """`ExtractionRecord.corrected` — the reviewer's replacement value.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model. See `GoldValue` on why this one's `value` is numeric only.
    """

    value: float
    unit: str


class ValueRange(OFModel):
    """`ExtractionRecord.range` — a value the source states as an interval.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    low: float
    high: float


class AggregateExclusion(StrEnum):
    """Why a record is held out of aggregate statistics, or null when nothing
    holds it out (OF-COR-001 §16 O8 and §19). Industry estimates are not
    evidence, and a paper reciting someone else's number is not an independent
    measurement — counting either one overstates consensus.

    This is the reason, not just the verdict, so a screen can say which records
    it left out of a median instead of silently dropping them. Exclusion applies
    to the statistic only: the records stay visible in per-record tables and
    plots, because they are real values, just not independent evidence.
    """

    REJECTED = "rejected"
    INDUSTRY_ESTIMATE = "industry-estimate"
    DEMO = "demo"
    NOT_PRIMARY = "not-primary"


EXCLUSION_NOTE: dict[AggregateExclusion, str] = {
    AggregateExclusion.REJECTED: "rejected — excluded from statistics",
    AggregateExclusion.INDUSTRY_ESTIMATE: "industry estimate — excluded from statistics",
    AggregateExclusion.DEMO: "modeled, not measured — excluded from statistics",
    AggregateExclusion.NOT_PRIMARY: (
        "reports another study’s measurement — excluded from statistics"
    ),
}
"""Short phrase a per-record view can print next to a held-out value."""


class ExtractionRecord(OFModel):
    id: str
    paper_id: str
    section_id: str
    quote: str
    field: FieldId
    value: float | str = Field(
        description="Categorical fields (kinase_identity, glycan_species) carry a string."
    )
    unit: str
    si: SIValue
    confidence: float
    status: RecordStatus
    provenance: Provenance = Field(
        description=(
            "Explicit provenance. Extractor output is 'unverified' until reviewed; "
            "values transcribed from OF-COR-001 are 'curated'; market figures are "
            "'industry-estimate' and never enter the gold set."
        )
    )
    organism: str | None = None
    component_tag: str | None = None
    gold: GoldValue | None = None
    gold_only: bool | None = None
    extractor_run: ExtractorRun | None = Field(
        default=None,
        description="Absent for curated records — they did not come from an extractor run.",
    )
    reject_reason: str | None = None
    corrected: CorrectedValue | None = None
    reviewer: str | None = None
    audit: list[AuditEvent]

    # ── OF-COR-001 additions ───────────────────────────────────────────
    is_primary: bool = Field(
        description=(
            "False. This paper is quoting someone else's measurement (OF-COR-001 §19, "
            "fifth trap). Citation-of-a-citation is the most common false-independence "
            "error in literature aggregation: 15 mg/L appears in both C2 (the "
            "measurement) and C6 (a citation of it), and a strip plot that counts both "
            "overstates consensus. Aggregate statistics must filter on this."
        )
    )
    evidence_class: EvidenceClass = Field(
        description=(
            "What kind of thing produced this value. Every seeded record is "
            "'literature'; the field is required so that a prediction written by geneOS "
            "or a measurement deposited by openLab cannot enter the store wearing the "
            "same face as a paper. `check:seed` enforces its presence."
        )
    )
    cites_record_id: str | None = Field(
        default=None, description="When not primary, the record this one is quoting."
    )
    method: AnalysisMethod | None = Field(
        default=None,
        description=(
            "How the value was measured. Mandatory for PTM and functional fields "
            "(OF-COR-001 §17 Rule 1) — 'undetermined' is a legitimate answer and means "
            "the analysis was never done, not that the result was negative."
        ),
    )
    numbering: NumberingConvention | None = Field(
        default=None,
        description="Required on phospho_site_position — mature and precursor differ by 15.",
    )
    curation_ref: str | None = Field(
        default=None,
        description="Where in OF-COR-001 a 'curated' value was transcribed from, e.g. '§9 H4'.",
    )
    range: ValueRange | None = Field(
        default=None, description="A value the source states as a range rather than a point."
    )
    comparative_baseline: str | None = Field(
        default=None,
        description='For comparative claims ("12-fold higher than X"), the baseline.',
    )
    negative_result: bool | None = Field(
        default=None,
        description="Value is a reported negative/absent result, not a missing measurement.",
    )

    # ── the aggregation gate (src/engine/aggregation.ts) ────────────────

    def aggregateExclusion(self) -> AggregateExclusion | None:
        """Why this record is held out of aggregate statistics, or None when
        nothing holds it out.

        Named for its TypeScript counterpart rather than snake_cased, so that
        the two implementations grep as one thing; `isAggregatable` is required
        to keep its exact name and it would read oddly for its only helper to
        be spelled differently.

        The three exclusions, in the order the TypeScript checks them:

        - `rejected` — a reviewer looked at this and said no. It is kept in the
          store because rejection is evidence about the extractor, but it is
          not evidence about the world.
        - `industry-estimate` — market and vendor figures (OF-COR-001 §16 O8).
          Useful for framing, useless as evidence.
        - `demo` — modeled rather than measured: simulation response grids,
          scripted agent text, anything derived from them. CLAUDE.md invariant 3
          names it alongside industry-estimate and BOTH implementations omitted
          it, so a demo value would have entered a median unremarked. No record
          carries it today, which is why nothing noticed; the gate is supposed
          to hold whether or not the corpus currently tests it.
        - `not-primary` — the paper is quoting someone else's measurement
          (OF-COR-001 §19, fifth trap). The same number counted twice is not
          two studies agreeing.

        `isPrimary is False` is checked explicitly rather than by falsiness,
        matching `r.isPrimary === false` in the TypeScript.
        """
        if self.status == RecordStatus.REJECTED:
            return AggregateExclusion.REJECTED
        if self.provenance == Provenance.INDUSTRY_ESTIMATE:
            return AggregateExclusion.INDUSTRY_ESTIMATE
        if self.provenance == Provenance.DEMO:
            return AggregateExclusion.DEMO
        if self.is_primary is False:
            return AggregateExclusion.NOT_PRIMARY
        return None

    def isAggregatable(self) -> bool:
        """Records that may enter a median, range or count-based summary.

        This is the single gate on every statistic in the app (invariant 3 in
        CLAUDE.md). Nothing else decides what counts: if a screen wants a
        median, a spread or an n, it filters on this and on nothing else, so
        that there is exactly one place where the policy lives and exactly one
        place to change it.

        Exclusion is not deletion. An excluded record still renders in
        per-record tables and plots with its provenance tick — it is a real
        value, just not independent evidence. `aggregateExclusion` returns the
        reason so a view can say which records it left out rather than
        silently dropping them.
        """
        return self.aggregateExclusion() is None


class RunOutcomeKind(StrEnum):
    """How one gold record fared in an extractor run.

    Named `RunOutcomeKind` rather than `RunOutcome` because that name belongs
    to a different type in `protocol.py`.
    """

    MATCH = "match"
    VALUE_MISMATCH = "value_mismatch"
    UNIT_ERROR = "unit_error"
    SPAN_ERROR = "span_error"
    MISS = "miss"


class ExtractedValue(OFModel):
    """What an extractor actually produced for a record.

    Inline in the TypeScript, in both `RunResult.extracted` and
    `FalsePositive.extracted`; named once here because Pydantic has no
    anonymous model and the two shapes are identical.
    """

    value: float
    unit: str


class RunResult(OFModel):
    """One gold record's outcome in an extractor run.

    Inline in the TypeScript as an element of `RunOutput.results`; named here
    because Pydantic has no anonymous model.
    """

    gold_record_id: str
    outcome: RunOutcomeKind
    extracted: ExtractedValue | None = None


class FalsePositive(OFModel):
    """A value an extractor produced that no gold record claims.

    Inline in the TypeScript as an element of `RunOutput.falsePositives`;
    named here because Pydantic has no anonymous model.
    """

    id: str
    paper_id: str
    field: FieldId
    extracted: ExtractedValue
    note: str


class RunOutput(OFModel):
    """The scored output of one extractor run.

    No instance of this is seeded. `RUN_OUTPUTS` stays empty until a real
    extractor runs (invariant 2 in CLAUDE.md) — the shape exists so that real
    output has somewhere to land, not so that plausible numbers can be written
    into it.
    """

    run: ExtractorRun
    results: list[RunResult]
    false_positives: list[FalsePositive]


class CuratorNote(OFModel):
    at: str
    who: str
    text: str
