"""AnswerPlan (OF-BLD-007 §3).

The only representation of an answer in the system. Defined here and mirrored
exactly in `src/data/types.ts`; `pnpm check:plan` fails the build if the two
drift, because a shape that exists twice and is enforced once is a shape that
is about to disagree with itself.

THE PLAN IS NOT A TRANSCRIPT. The scripted path this replaces replayed prose a
human wrote. A plan is a set of claims, each one a sentence with no number in
it and a list of records it rests on. The browser renders the value from the
record, never from the model's text — which is what makes the model
structurally incapable of originating a quantity (§5).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Mirrors the Provenance union in src/data/types.ts, weakest last. The order IS
# the ranking: `weakest_provenance` walks this list, so adding a class in the
# wrong place silently changes what a claim claims.
Provenance = Literal[
    "measured",
    "gold",
    "verified",
    "curated",
    "unverified",
    "user",
    "industry-estimate",
    "demo",
]

PROVENANCE_ORDER: list[str] = [
    "measured",
    "gold",
    "verified",
    "curated",
    "user",
    "unverified",
    "industry-estimate",
    "demo",
]

Support = Literal["direct", "inferred", "unsupported"]


class Claim(BaseModel):
    """One assertion, and everything it rests on."""

    id: str
    text: str = Field(
        description=(
            "Prose with NO number in it. Name what was measured and under what "
            "conditions; the interface renders the value from the cited record."
        )
    )
    recordIds: list[str] = Field(default_factory=list)
    paperIds: list[str] = Field(default_factory=list)
    support: Support = "direct"
    # Computed server-side as the weakest of the cited records, never chosen by
    # the model. A model that grades its own evidence grades it generously.
    provenance: Provenance = "unverified"


class Usage(BaseModel):
    inputTokens: int = 0
    outputTokens: int = 0
    # Computed from the response's own token counts, not estimated. Surfaced in
    # the UI because a visible per-query cost is what makes budget gating real
    # rather than theoretical.
    costUsd: float = 0.0


class AnswerPlan(BaseModel):
    question: str
    claims: list[Claim] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list, description="What evidence is missing.")
    declined: str | None = Field(
        default=None,
        description="Set when the corpus cannot support an answer. Says what is missing.",
    )
    usage: Usage = Field(default_factory=Usage)

    # Not part of §3's shape and deliberately additive: how many claims the
    # validator dropped, and why. §5 requires rejections to be counted, and a
    # count that only reaches a log file is a count nobody looks at.
    rejected: int = 0
    rejectionReasons: list[str] = Field(default_factory=list)


def weakest_provenance(provenances: list[str]) -> str:
    """The weakest class among cited records — provenance propagation (§3).

    A claim is worth exactly as much as its worst evidence. Citing one gold
    record and one industry estimate does not make a claim gold; it makes it an
    industry estimate with a gold record standing next to it.

    Unknown classes are treated as the weakest thing there is rather than
    ignored, because an unrecognised provenance is not a reason for confidence.
    """
    if not provenances:
        return "unverified"
    ranked = [
        PROVENANCE_ORDER.index(p) if p in PROVENANCE_ORDER else len(PROVENANCE_ORDER)
        for p in provenances
    ]
    worst = max(ranked)
    return PROVENANCE_ORDER[worst] if worst < len(PROVENANCE_ORDER) else "demo"


class AskRequest(BaseModel):
    question: str
    # §6 caps evidence at 30 records. A caller asking for more is clamped rather
    # than refused — the cap is a token-budget contract, not a permission.
    maxEvidence: int = 30


# ── Intake (OF-BLD-012 §2.5, §5) ────────────────────────────────────────
#
# Mirrored in src/data/types.ts and named in scripts/check-plan.mjs PAIRS, like
# everything else in this file. `FetchedSection` mirrors the browser's
# `PaperSection` under a different name because that interface already exists
# and this is the service's word for the same shape.


class FetchedSection(BaseModel):
    """One section of a paper's own text. Same shape as PaperSection."""

    id: str
    heading: str
    text: str


class FetchLicense(BaseModel):
    """What the JATS <license> element said. Stored beside every fetched text,
    because Europe PMC's open-access subset spans several licences and the
    text is kept local partly on that account (§2.2)."""

    href: str | None = None
    text: str | None = None


FetchStatus = Literal["complete", "failed:fetch", "failed:parse"]


class FetchResult(BaseModel):
    """What `intake.fetch_paper` produced, and what `fulltext/{paperId}.json`
    holds. A failure is a result with a reason, not an exception — the UI
    already renders `failed:fetch` and `failed:parse` (§5.2)."""

    paperId: str
    pmcid: str | None = None
    status: FetchStatus
    reason: str | None = None
    fetchedAt: str
    license: FetchLicense | None = None
    sections: list[FetchedSection] = Field(default_factory=list)
    # Size of the XML as received. A sanity figure for the batch table and the
    # quickest tell that a "success" was actually an error page.
    bytes: int = 0


class IntakeStatus(BaseModel):
    """One row of `GET /api/intake/status` — a paper's fetch state, summarised."""

    paperId: str
    pmcid: str | None = None
    ingest: str
    textSource: Literal["full-text", "curation-note"]
    sections: int = 0
    tables: int = 0
    license: str | None = None
    fetchedAt: str | None = None
    reason: str | None = None


class OverlayPaper(BaseModel):
    """What the overlay says about one paper (§2.1): its fetch state and, when
    the fetch succeeded, the paper's own sections in place of the seed's
    curation note. A failed fetch is here too, with its reason — the ingest
    board renders it, and a board that only showed successes would be lying by
    omission about the twenty-six DOI-only papers."""

    ingest: str
    textSource: Literal["full-text", "curation-note"]
    sections: list[FetchedSection] = Field(default_factory=list)
    license: str | None = None
    fetchedAt: str | None = None
    reason: str | None = None


class Overlay(BaseModel):
    """GET /api/biorepo/overlay (§2.1). The store applies it in one action on
    top of the seed; with the service down the app is exactly the seed.

    `records`, `candidates` and `runs` are typed loosely here and in
    types.ts until §7 and §6 define ReviewDecision, Candidate and ExtractRun;
    the field names are fixed now so the shape does not move under the UI."""

    papers: dict[str, OverlayPaper] = Field(default_factory=dict)
    records: dict[str, dict] = Field(default_factory=dict)
    candidates: list[dict] = Field(default_factory=list)
    runs: list[dict] = Field(default_factory=list)


# ── Extraction and review (OF-BLD-012 §2.5, §6, §7) ──────────────────────

RecordStatus = Literal["unverified", "verified", "rejected"]
# Mirrors ExtractorRun in types.ts. 'haiku-1' is the first run that actually ran.
ExtractorRun = Literal["v0.3", "v0.4", "v0.4r", "haiku-1"]
Outcome = Literal["match", "value_mismatch", "unit_error", "span_error", "miss"]


class AuditEvent(BaseModel):
    """One entry in a record's audit trail. Mirrors the browser's AuditEvent."""

    at: str
    who: str
    action: str
    from_: Any | None = Field(default=None, alias="from")
    to: Any | None = None

    model_config = {"populate_by_name": True}


class Quantity(BaseModel):
    """A value and its unit. Categorical fields carry a string value."""

    value: float | str
    unit: str


class Range(BaseModel):
    low: float
    high: float


class Candidate(BaseModel):
    """An extraction the anchoring rules accepted (§2.4), before any human has
    looked at it. Mirrors the browser's ExtractionRecord minus the four fields
    review owns — audit, gold, corrected, reviewer — because a candidate has
    no review history yet and must not be able to claim one.

    Provenance and status are fixed at 'unverified' by construction. The model
    does not get a slot to set either.
    """

    id: str
    paperId: str
    sectionId: str
    quote: str
    field: str
    value: float | str
    unit: str
    si: Quantity
    confidence: float = 0.0
    status: RecordStatus = "unverified"
    provenance: Provenance = "unverified"
    organism: str | None = None
    componentTag: str | None = None
    goldOnly: bool | None = None
    extractorRun: ExtractorRun = "haiku-1"
    rejectReason: str | None = None
    isPrimary: bool = True
    citesRecordId: str | None = None
    method: str | None = None
    numbering: str | None = None
    curationRef: str | None = None
    range: Range | None = None
    comparativeBaseline: str | None = None
    negativeResult: bool | None = None


class ExtractRunResult(BaseModel):
    """One seed record scored against a run (§6.2)."""

    goldRecordId: str
    outcome: Outcome
    extracted: Quantity | None = None


class ExtractRunFalsePositive(BaseModel):
    """A candidate a reviewer rejected — the only way one gets here (§6.2)."""

    id: str
    paperId: str
    field: str
    extracted: Quantity
    note: str


class ExtractRun(BaseModel):
    """Mirrors the browser's RunOutput: what Witness computes metrics from."""

    run: ExtractorRun
    results: list[ExtractRunResult] = Field(default_factory=list)
    falsePositives: list[ExtractRunFalsePositive] = Field(default_factory=list)


class ReviewDecision(BaseModel):
    """What a reviewer decided about one record (§7.1).

    The first six fields are exactly the browser's DurableReviewDecision — the
    shape the Durable tier already persists — so a decision made offline and a
    decision posted to the service are the same object. The rest say which
    record, when, and, for a promotion that re-anchors a curated quote to the
    paper's own words, the replacement span.
    """

    status: RecordStatus
    provenance: Provenance
    gold: Quantity | None = None
    corrected: Quantity | None = None
    rejectReason: str | None = None
    reviewer: str | None = None
    recordId: str
    at: str
    quote: str | None = None
    sectionId: str | None = None


class ExtractResponse(BaseModel):
    """What one extraction produced (§6.1, §6.3), and what
    `candidates/{paperId}.json` holds.

    `candidates` are the survivors of anchoring. `audit` is the event every
    one of them shares — the Candidate model carries none (§2.5), so it lives
    beside them here and is copied onto a record at promotion (§7).
    `rejectionReasons` is keyed by anchoring rule; a rising count is the
    signal that the prompt has drifted."""

    paperId: str
    run: ExtractorRun = "haiku-1"
    extractedAt: str
    candidates: list[Candidate] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)
    rejected: int = 0
    rejectionReasons: dict[str, int] = Field(default_factory=dict)
    rejectionDetails: list[str] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    notes: list[str] = Field(default_factory=list)
