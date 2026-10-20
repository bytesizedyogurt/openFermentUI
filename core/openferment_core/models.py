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

from pydantic import BaseModel, ConfigDict, Field

# Mirrors the Provenance union in src/data/types.ts, weakest last. The order IS
# the ranking: `weakest_provenance` walks this list, so adding a class in the
# wrong place silently changes what a claim claims.
Provenance = Literal[
    "measured",
    "gold",
    "verified",
    "curated",
    "computed",
    "unverified",
    "user",
    "industry-estimate",
    "demo",
]

# The same order as PROVENANCE_RANK in src/store.ts, member for member;
# `check:plan` parses both and fails on any difference (OF-BLD-014 §3.1, E.4).
# `computed` follows every experimental class, because no experiment stands
# behind it, and precedes `unverified`, because anyone can reproduce it from
# its basis.
PROVENANCE_ORDER: list[str] = [
    "measured",
    "gold",
    "verified",
    "curated",
    "computed",
    "unverified",
    "user",
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
    # OF-BLD-014 §5.1: sentences the claim quotes, each checked verbatim
    # against its passage, and computed values it rests on, by evidence id.
    passages: list[PassageRef] = Field(default_factory=list)
    evidenceIds: list[str] = Field(default_factory=list)


class PassageRef(BaseModel):
    """A sentence a claim quotes, and the passage it stands in."""

    passageId: str
    quote: str


TraceKind = Literal["tool", "restart", "final"]
StopReason = Literal["done", "rounds", "calls", "cost", "time"]


class TraceStep(BaseModel):
    """One step of Postdoc's loop, as the browser shows it (OF-BLD-014 §5.1)."""

    n: int
    kind: TraceKind
    tool: str | None = None
    input: dict[str, Any] | None = None
    # One line, written by code.
    summary: str
    ms: int
    ok: bool


class Usage(BaseModel):
    inputTokens: int = 0
    outputTokens: int = 0
    # Prompt tokens read from and written to the prompt cache (OF-BLD-014
    # §3.3). `inputTokens` excludes both, as the API reports it.
    cacheReadTokens: int = 0
    cacheWriteTokens: int = 0
    # Computed from the response's own token counts, not estimated. Surfaced in
    # the UI because a visible per-query cost is what makes budget gating real
    # rather than theoretical.
    costUsd: float = 0.0
    # The models that answered, in order: one, or the primary and the model it
    # fell back to (llm.py). Empty for a saved fixture that never called one.
    models: list[str] = Field(default_factory=list)


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

    # OF-BLD-014 §5.1: what the agent's claims may cite beyond records — the
    # computed values and the passages its tools returned and its claims
    # cite — and how the loop ran and why it stopped.
    evidence: list[Evidence] = Field(default_factory=list)
    passages: list[Passage] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)
    stopped: StopReason = "done"
    # OF-BLD-014 §9.2: a runbook the agent drafted, its numbers written by the
    # service (runbook_draft.py), for a person to adopt and lock.
    runbookDraft: "RunbookDraft | None" = None


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


class PriorTurn(BaseModel):
    """One earlier turn of the conversation a follow-up belongs to, in words:
    the question as the person asked it, and the claims' text, the gaps and
    the decline of the plan that answered it. The validator already held each
    of these to Rule 1; the loop drops any that still holds a number. No id,
    value or quote travels: a follow-up searches again before it cites."""

    question: str
    claims: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    declined: str | None = None


class AskRequest(BaseModel):
    question: str
    # §6 caps evidence at 30 records. A caller asking for more is clamped rather
    # than refused — the cap is a token-budget contract, not a permission.
    maxEvidence: int = 30
    # OF-BLD-014 §5.3: `agent` is the bounded loop (postdoc_agent.py), the
    # default; `single` is one retrieval and one call (postdoc.py).
    mode: Literal["agent", "single"] = "agent"
    # The earlier turns of the same conversation, oldest first. The agent
    # reads the last few as context; `single` mode ignores them.
    history: list[PriorTurn] = Field(default_factory=list)


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
    """What the JATS <license> element said, or what an OSTI report or an SGD
    strain entry states of itself. Stored beside every fetched text, because
    Europe PMC's open-access subset spans several licences and the text is
    kept local partly on that account (§2.2)."""

    href: str | None = None
    text: str | None = None


FetchStatus = Literal["complete", "failed:fetch", "failed:parse"]
# Who served a fetched text: Europe PMC's JATS, an OSTI report's PDF, or a
# Saccharomyces Genome Database strain entry (thread Q). A file cached before
# the field existed was fetched from Europe PMC, and reads as such.
FetchSource = Literal["europepmc", "osti", "sgd"]


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
    # Size of the document as received: the XML, the PDF or the JSON. A sanity
    # figure for the batch table and the quickest tell that a "success" was
    # actually an error page.
    bytes: int = 0
    source: FetchSource = "europepmc"


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
    source: FetchSource = "europepmc"


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
    # Who served the text, so the reader names its source rather than
    # assuming Europe PMC.
    source: FetchSource = "europepmc"


class Overlay(BaseModel):
    """GET /api/biorepo/overlay (§2.1). The store applies it in one action on
    top of the seed; with the service down the app is exactly the seed.

    `papers` from fulltext/ (§5); `runs` and `candidates` recomputed from
    candidates/ against the seed by `witness.py` (§6.2); `records` from
    biorepo.json (§7).

    `candidates` and `runs` are a LIST OR NULL (OF-BLD-012.1 F3). The service
    always sends the full list, so an empty list means the extractor produced
    nothing and the store drops what it had. `None` means "not supplied" and
    the store keeps what it had — nothing here sends it, and it exists so that
    "empty" and "unknown" can never be the same value again."""

    papers: dict[str, OverlayPaper] = Field(default_factory=dict)
    records: dict[str, "ReviewDecision"] = Field(default_factory=dict)
    candidates: list["Candidate"] | None = Field(default_factory=list)
    runs: list["ExtractRun"] | None = Field(default_factory=list)


# ── Extraction and review (OF-BLD-012 §2.5, §6, §7) ──────────────────────

RecordStatus = Literal["unverified", "verified", "rejected"]
# Mirrors ExtractorRun in types.ts. 'claude-1' is the first run that runs for
# real: Claude Opus 5.5, with Claude Sonnet 5.5 where Opus declined (llm.py).
ExtractorRun = Literal["v0.3", "v0.4", "v0.4r", "claude-1"]
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


# How §2.4 rule 3 found the value in the sentence (OF-BLD-012.1 F1.2).
# Computed by the anchoring rules; never set by a model or a reviewer.
ValueBasis = Literal[
    "exact", "converted", "range-midpoint", "range-low", "range-high", "negation"
]


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
    # OF-BLD-014 §2.1. `organism` is the strain id when anchoring resolved the
    # extractor's wording to one (`validate.strain_id`), the wording otherwise;
    # `organismText` keeps the wording when it was resolved.
    organism: str | None = None
    organismText: str | None = None
    # What the cells were fed, in the paper's words. Kept only when the words
    # stand in the cited section and carry no number; dropped otherwise, with
    # the candidate kept and the drop counted (`ExtractResponse.fieldDrops`).
    carbonSource: str | None = None
    componentTag: str | None = None
    goldOnly: bool | None = None
    extractorRun: ExtractorRun = "claude-1"
    rejectReason: str | None = None
    isPrimary: bool = True
    citesRecordId: str | None = None
    method: str | None = None
    numbering: str | None = None
    curationRef: str | None = None
    range: Range | None = None
    comparativeBaseline: str | None = None
    negativeResult: bool | None = None
    valueBasis: ValueBasis | None = None


class DecisionCheck(BaseModel):
    """What `POST /api/biorepo/check` answers (OF-BLD-012.1 F1.5): whether
    `biorepo.write` would store this decision, and the rule it would refuse
    it under. The browser asks before the reviewer presses the key, so the
    screen says what the service would say rather than a mirror of it."""

    ok: bool
    rule: str | None = None
    why: str | None = None


class DroppedCandidate(BaseModel):
    """A candidate anchoring refused (§2.4), kept beside the survivors so the
    run can be scored honestly (§6.2): a candidate whose value agreed with the
    seed and whose quote failed is a `span_error` in Witness — the extractor
    produced it, and dropping it from BioRepo does not undo that. Never enters
    BioRepo; never repaired."""

    paperId: str
    sectionId: str
    field: str
    value: float | str | None = None
    unit: str = ""
    rule: str
    detail: str = ""


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
    # The models that answered the run's papers, from their usage records.
    models: list[str] = Field(default_factory=list)


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


class BioRepo(BaseModel):
    """core/data/biorepo.json (§2.2, §7.1) — the one data file that is
    committed, because it holds human decisions and the short quotes that
    anchor them. This file IS the corpus growing.

    `decisions` is keyed by recordId. `records` holds the candidates those
    decisions were made about — accepted ones, which are new records, and
    rejected ones, which Witness lists as false positives — copied here
    because candidates/ is gitignored and a decision about a candidate nobody
    can see any more would be a decision about nothing. The copy keeps the
    candidate's own status; the decision is the authority.
    """

    version: Literal[1] = 1
    decisions: dict[str, ReviewDecision] = Field(default_factory=dict)
    records: list[Candidate] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    """What one extraction produced (§6.1, §6.3), and what
    `candidates/{paperId}.json` holds.

    `candidates` are the survivors of anchoring. `audit` is the event every
    one of them shares — the Candidate model carries none (§2.5), so it lives
    beside them here and is copied onto a record at promotion (§7).
    `rejectionReasons` is keyed by anchoring rule; a rising count is the
    signal that the prompt has drifted."""

    paperId: str
    run: ExtractorRun = "claude-1"
    extractedAt: str
    candidates: list[Candidate] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)
    rejected: int = 0
    rejectionReasons: dict[str, int] = Field(default_factory=dict)
    rejectionDetails: list[str] = Field(default_factory=list)
    dropped: list[DroppedCandidate] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    notes: list[str] = Field(default_factory=list)
    # How many model calls this took, and which sections still would not fit
    # (OF-BLD-012.1 F8). One call is the ordinary case; more means the paper
    # was halved because the response hit the token limit. `truncatedSections`
    # is what even splitting could not reach — the honest gap in this paper's
    # extraction, rather than a silent zero.
    calls: int = 1
    truncatedSections: list[str] = Field(default_factory=list)
    # Fields anchoring removed from a candidate it KEPT, by reason (OF-BLD-014
    # §2.1). Not rejections, and not in `rejected`: the candidate is in
    # `candidates` without the field. Today the one reason is `carbonSource`.
    fieldDrops: dict[str, int] = Field(default_factory=dict)


# ── Guild (OF-BLD-013) ───────────────────────────────────────────────────
#
# Who may verify, extended from records to the people running protocol steps.
# The ledger is core/data/guild.json, written only by `guild.write_*`, and it is
# gitignored: the repository is public and a competence ledger is personnel
# data. Mirrored in src/data/types.ts and held to it by `check:plan`.

GuildRole = Literal["member", "lead", "auditor"]

# Every kind the ledger will ever hold. Sign-offs and designations come from
# Guild; runs alone, cosigned runs and deviations from Deposition as a step is
# completed; a lesson passed and a practice session from Primer, each with
# nobody watching.
EvidenceKind = Literal[
    "witnessed",
    "supervised",
    "independent",
    "deviation",
    "scenario",
    "knowledge",
    "designation",
]

EvidenceSourceKind = Literal["signoff", "lead", "deposition", "lesson", "scenario", "check"]


class GuildPerson(BaseModel):
    """One person on the ledger. `id` is chosen by the browser so a person
    added offline keeps their id when it is posted later."""

    id: str
    name: str
    role: GuildRole = "member"
    title: str = ""
    joinedAt: str
    active: bool = True
    addedBy: str | None = None
    addedAt: str
    updatedBy: str | None = None
    updatedAt: str | None = None


class EvidenceSource(BaseModel):
    """Where an entry came from. For a sign-off, `ref` is what the assessor
    names (a protocol id, or a paper training record), and `stepId` the step
    when there is one."""

    kind: EvidenceSourceKind
    ref: str
    stepId: str | None = None


class GuildEvidence(BaseModel):
    """One thing a person did that bears on one skill. Append-only: a mistake
    is withdrawn, never edited, and the withdrawal stays on the entry."""

    id: str
    personId: str
    skillId: str
    kind: EvidenceKind
    outcome: Literal["pass", "fail"] = "pass"
    # When it happened. A sign-off may be backdated to the day it was seen.
    at: str
    observerId: str | None = None
    source: EvidenceSource
    # The observer's own words, kept verbatim and never rewritten.
    raw: str
    # When the service stored it, stamped by the service.
    recordedAt: str | None = None
    withdrawnAt: str | None = None
    withdrawnBy: str | None = None
    withdrawReason: str | None = None


class GuildWithdrawal(BaseModel):
    """A request to withdraw one entry: who, when, and why."""

    evidenceId: str
    by: str
    at: str
    reason: str


GateMode = Literal["advise", "enforce"]


class GuildPolicy(BaseModel):
    """The lead's choices for the team (OF-BLD-013 §5.1). In advise mode the
    run-mode gate warns and records a deviation; in enforce mode it holds the
    step until a cosigner is recorded, or someone qualified takes over. Set
    per criticality: a routine skill and a critical one can differ."""

    routineGate: GateMode = "advise"
    criticalGate: GateMode = "enforce"
    # The witnessed checks each holder of a critical skill gets at least,
    # every quarter. Fewer puts them in the assessors' queue.
    checksPerQuarter: int = 1
    updatedBy: str | None = None
    updatedAt: str | None = None


class Guild(BaseModel):
    """core/data/guild.json — the people and everything recorded about them."""

    version: Literal[1] = 1
    people: list[GuildPerson] = Field(default_factory=list)
    evidence: list[GuildEvidence] = Field(default_factory=list)
    policy: GuildPolicy = Field(default_factory=GuildPolicy)


# ── Practice (OF-BLD-013 §4) ────────────────────────────────────────────
#
# A practice scenario is drafted by the model from protocol steps and bench
# runs, and a tutor questions the trainee's reasoning in short turns. The
# model writes words and cites sources; every value a trainee sees is copied
# by the service from the source it cites, so no quantity in a scenario comes
# from model weights. core/data/practice.json holds the scenarios and the
# sessions, and never enters git: a session is a person's own words.

PracticeSourceKind = Literal["step", "material", "entry", "observation"]
PracticeMove = Literal["why", "change", "next", "close"]


class PracticeStepRef(BaseModel):
    protocolId: str
    stepId: str


class PracticeSource(BaseModel):
    """What a value in the evidence pane was copied from: a protocol step or
    material, or a Deposition's entry or observation."""

    kind: PracticeSourceKind
    protocolId: str | None = None
    stepId: str | None = None
    material: str | None = None
    depositionId: str | None = None
    itemId: str | None = None


class PracticeValue(BaseModel):
    """One item in a scenario's evidence pane. `label` is the model's words
    naming it; `text`, `value`, `unit` and `at` are the source's, copied by
    the service."""

    id: str
    label: str
    source: PracticeSource
    text: str
    value: float | None = None
    unit: str | None = None
    at: str | None = None
    # For a run's entry, the runbook's name for what was measured.
    measure: str | None = None
    # For a protocol's step or material, the batch its amounts are written for.
    basis: str | None = None


class PracticeScenario(BaseModel):
    id: str
    skillId: str
    title: str
    # The situation and the question, as the trainee reads them. [v1] marks
    # where an item of the evidence pane belongs.
    situation: str
    prompt: str
    # What a sound answer would reach. The tutor reads it; the trainee does not.
    watchFor: list[str] = Field(default_factory=list)
    evidence: list[PracticeValue] = Field(default_factory=list)
    steps: list[PracticeStepRef] = Field(default_factory=list)
    depositionIds: list[str] = Field(default_factory=list)
    model: str
    usage: Usage = Field(default_factory=Usage)
    createdAt: str


class PracticeDepositionEntry(BaseModel):
    id: str
    stepId: str
    at: str
    value: float
    unit: str
    raw: str
    label: str | None = None
    # An entry nobody has confirmed may be a misheard number ("four two" as
    # forty-two), so Practice never teaches from one.
    confirmed: bool = True


class PracticeDepositionObservation(BaseModel):
    id: str
    stepId: str
    at: str
    raw: str


class PracticeDeposition(BaseModel):
    """A Deposition as the browser sends it for drafting: Depositions live in
    the browser's Durable tier, so the service sees the ones it is shown."""

    id: str
    protocolId: str
    startedAt: str
    entries: list[PracticeDepositionEntry] = Field(default_factory=list)
    observations: list[PracticeDepositionObservation] = Field(default_factory=list)


class PracticeDraftRequest(BaseModel):
    skillId: str
    depositions: list[PracticeDeposition] = Field(default_factory=list, max_length=40)


class PracticeTurn(BaseModel):
    role: Literal["trainee", "tutor"]
    text: str
    move: PracticeMove | None = None
    steps: list[PracticeStepRef] = Field(default_factory=list)
    at: str


class PracticeObservation(BaseModel):
    """What the tutor observed, in plain words, with the steps it bears on.
    No grade: the schema has no field for one."""

    text: str
    steps: list[PracticeStepRef] = Field(default_factory=list)


class PracticeSession(BaseModel):
    id: str
    scenarioId: str
    skillId: str
    # A person on Guild's ledger, or None for a session nobody's record keeps
    # (the sample team, or nobody chosen).
    personId: str | None = None
    turns: list[PracticeTurn] = Field(default_factory=list)
    observed: list[PracticeObservation] = Field(default_factory=list)
    startedAt: str
    closedAt: str | None = None
    # The ledger entry written when the session closed, when there is one.
    evidenceId: str | None = None
    usage: Usage = Field(default_factory=Usage)


class PracticeTurnRequest(BaseModel):
    scenarioId: str
    sessionId: str | None = None
    personId: str | None = None
    answer: str


class Practice(BaseModel):
    """core/data/practice.json — every scenario drafted and every session held."""

    version: Literal[1] = 1
    scenarios: list[PracticeScenario] = Field(default_factory=list)
    sessions: list[PracticeSession] = Field(default_factory=list)


# ── Checks (OF-BLD-013 §5) ──────────────────────────────────────────────
#
# A check is proposed by fixed rules over the ledger (checks.py, mirroring
# src/engine/checks.ts), or asked for by the person or an assessor, then
# scheduled and run at the bench by an assessor. Running it writes one
# witnessed entry per skill through guild.write_evidence, with the check as
# its source. core/data/checks.json never enters git.

CheckState = Literal["proposed", "scheduled", "done", "dismissed"]
CheckReasonKind = Literal["suspended", "lapsed", "lapsing", "ready", "deviation", "confidence", "rate", "requested"]


class CheckReason(BaseModel):
    """Why a check is proposed, written by fixed rules from the ledger."""

    kind: CheckReasonKind
    skillId: str
    text: str


class CheckCriterion(BaseModel):
    """One of a skill's mastery criteria, by its place in src/data/skills.ts."""

    skillId: str
    index: int


class CheckBrief(BaseModel):
    """What the model suggests the assessor watch for. Steps and criteria are
    references the service resolves; questions are words with no number."""

    steps: list[PracticeStepRef] = Field(default_factory=list)
    criteria: list[CheckCriterion] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    model: str
    usage: Usage = Field(default_factory=Usage)
    draftedAt: str


class CheckResult(BaseModel):
    """The assessor's call on one criterion, with their own words."""

    skillId: str
    criterion: int
    meets: bool
    note: str = ""


class Check(BaseModel):
    id: str
    personId: str
    skillIds: list[str]
    reasons: list[CheckReason] = Field(default_factory=list)
    state: CheckState = "proposed"
    score: int = 0
    proposedAt: str
    # None for the nightly ranking; otherwise who asked for it.
    proposedBy: str | None = None
    # Who scheduled or ran it.
    assessorId: str | None = None
    # The day the assessor picked. The person is not told.
    scheduledFor: str | None = None
    brief: CheckBrief | None = None
    results: list[CheckResult] = Field(default_factory=list)
    evidenceIds: list[str] = Field(default_factory=list)
    closedAt: str | None = None
    dismissedBy: str | None = None
    dismissReason: str | None = None


class Checks(BaseModel):
    """core/data/checks.json — every check proposed, asked for, run or dismissed."""

    version: Literal[1] = 1
    checks: list[Check] = Field(default_factory=list)


class CheckRequest(BaseModel):
    personId: str
    skillIds: list[str]
    by: str


class CheckSchedule(BaseModel):
    by: str
    scheduledFor: str


class CheckDismiss(BaseModel):
    by: str
    reason: str


class CheckNote(BaseModel):
    """The assessor's own words on one skill, kept verbatim as the entry's raw."""

    skillId: str
    text: str


class CheckRecord(BaseModel):
    by: str
    at: str
    results: list[CheckResult]
    notes: list[CheckNote]


# ── computed values (OF-BLD-014 §3.1, E.4) ─────────────────────────────
#
# A number no paper states: a converted value, a yield ceiling, a fitted rate,
# a price. It carries the calculation that produced it, and every input names
# where it came from. Its provenance is `basis.basis_provenance(...)`, never a
# model's or a person's choice.

BasisSourceKind = Literal["record", "deposition", "artifact", "model", "convention", "assumption"]


class BasisSource(BaseModel):
    kind: BasisSourceKind
    # The record, deposition, artifact or model file the input was read from.
    id: str | None = None
    # What the convention is, or what the assumption rests on.
    note: str | None = None
    # The named person, for an assumption.
    by: str | None = None


class BasisInput(BaseModel):
    name: str
    value: float | str
    unit: str
    source: BasisSource


class ComputedBasis(BaseModel):
    tool: str
    # Package versions and model file hash, joined.
    toolVersion: str
    inputs: list[BasisInput]
    artifactId: str
    at: str
    # For anything sampled.
    seed: int | None = None


class Evidence(BaseModel):
    """A computed value a plan may cite. Its label is built by code."""

    id: str
    label: str
    value: float | str
    unit: str
    interval: Range | None = None
    provenance: Provenance
    basis: ComputedBasis
    # Which figure draws this artifact: 'ceiling', 'frontier', 'trajectory',
    # 'distribution'.
    figure: str | None = None


# ── artifacts (OF-BLD-014 §3.2, E.5) ───────────────────────────────────


class Artifact(BaseModel):
    """What was computed, kept so it can be read and replayed."""

    # First 16 hex of sha256 over tool, toolVersion, canonical inputs (and the
    # seed, when there is one).
    id: str
    tool: str
    toolVersion: str
    inputs: list[BasisInput]
    # Tool-specific; small enough to read on a page.
    output: dict[str, Any]
    # sha256 of the canonical output JSON.
    outputHash: str
    provenance: Provenance
    createdAt: str
    durationMs: int
    seed: int | None = None


class ReplayDifference(BaseModel):
    """One place a replayed output differs from the stored one."""

    # Where in the output, as `a.b[2]`; empty for the output as a whole.
    path: str
    stored: Any = None
    replayed: Any = None


class ReplayResult(BaseModel):
    artifactId: str
    identical: bool
    storedHash: str
    replayedHash: str
    differences: list[ReplayDifference] = Field(default_factory=list)
    durationMs: int


# ── tools (OF-BLD-014 §3.4, E.6) ───────────────────────────────────────


class ToolInfo(BaseModel):
    """One tool as `GET /api/tools` lists it."""

    name: str
    description: str
    inputSchema: dict[str, Any]


class ToolResult(BaseModel):
    """What a tool returns to whoever called it: Postdoc's loop, the HTTP
    endpoint or the MCP server (E.6)."""

    # What the model reads; at most 9,000 characters as JSON.
    summary: dict[str, Any] = Field(default_factory=dict)
    # Computed values a plan may cite.
    evidence: list[Evidence] = Field(default_factory=list)
    # Records a plan may cite.
    recordIds: list[str] = Field(default_factory=list)
    # Passages a plan may quote (OF-BLD-014 §5.2).
    passages: list[Passage] = Field(default_factory=list)
    # A refusal or an unavailable tool, in words.
    error: str | None = None
    # What the tool spent on models (a search lane that calls one), charged
    # to the question that called it (OF-BLD-014 §5.R).
    usage: Usage = Field(default_factory=Usage)
    # A runbook draft the service assembled (OF-BLD-014 §9.2, E.6).
    draft: "RunbookDraft | None" = None


# ── geneOS (OF-BLD-014 §6.3) ───────────────────────────────────────────


class GeneosModelInfo(BaseModel):
    """One model on geneOS's shelf, as the browser lists it."""

    id: str
    name: str
    # The strain id the model describes, when the catalogue has one.
    host: str | None = None
    scope: str
    route: str
    licence: str
    source: str
    # Why it cannot be loaded here (its file is not fetched), or None.
    unavailable: str | None = None
    # The sugar a view opens on: one the model can take up.
    feed: str
    notes: list[str] = Field(default_factory=list)
    # The product a view opens on, and every product the shelf names a route
    # to in this model ("phb", "ethanol"); the worker decides what it makes.
    product: str
    products: list[str] = Field(default_factory=list)


GeneosKind = Literal["ceiling", "frontier", "mix"]


class GeneosResult(BaseModel):
    """A ceiling, a frontier or a sugar mix: an artifact and its evidence, or
    a finding in words with no number."""

    kind: GeneosKind
    modelId: str
    product: str
    substrates: list[str]
    finding: str | None = None
    artifactId: str | None = None
    evidence: Evidence | None = None
    # The worker's output as the artifact stores it.
    output: dict[str, Any] = Field(default_factory=dict)


# ── fermOS (OF-BLD-014 §7.2) ───────────────────────────────────────────

SeriesRole = Literal["biomass", "product", "substrate"]


class FermosPoint(BaseModel):
    # Hours into the run.
    t: float
    value: float
    entryId: str
    confirmed: bool = False


class FermosSeries(BaseModel):
    """One measure's readings in time order, as the browser's `seriesOf` makes them."""

    measureId: str
    label: str
    unit: str
    role: SeriesRole | None = None
    points: list[FermosPoint] = Field(default_factory=list)


class FermosFitRequest(BaseModel):
    depositionId: str
    series: list[FermosSeries]
    # The sample run: computed inline, kept nowhere (§7.4).
    sample: bool = False


class FitParam(BaseModel):
    """One fitted parameter, its 95 % interval and its unit."""

    name: str
    value: float
    low: float
    high: float
    unit: str
    # μ and Xmax: the interval excludes zero. A rate coefficient: the interval
    # includes zero, so the run cannot tell it from nothing.
    identified: bool | None = None
    indistinguishableFromZero: bool | None = None


class GrowthFit(BaseModel):
    """ln X against t over the best window of four or more readings."""

    measureId: str
    unit: str
    mu: FitParam | None = None
    doublingTimeH: float | None = None
    r2: float | None = None
    window: list[float] = Field(default_factory=list)
    points: int = 0
    reason: str | None = None


class SeriesFitQuality(BaseModel):
    measureId: str
    role: SeriesRole
    r2: float
    # The residual scatter, in the measure's unit, under the constant-scatter assumption.
    scatter: float
    residuals: list[float] = Field(default_factory=list)


class KineticFit(BaseModel):
    """Logistic growth, Luedeking–Piret production and the substrate balance."""

    params: list[FitParam] = Field(default_factory=list)
    quality: list[SeriesFitQuality] = Field(default_factory=list)
    # The covariance of `params`, in their order, for a forecast to draw from.
    covariance: list[list[float]] = Field(default_factory=list)
    series: list[FermosSeries] = Field(default_factory=list)
    reason: str | None = None


class FermosFitResponse(BaseModel):
    depositionId: str
    growth: GrowthFit | None = None
    kinetic: KineticFit | None = None
    growthArtifactId: str | None = None
    kineticArtifactId: str | None = None
    # The share of the readings a person confirmed.
    confirmedShare: float
    sample: bool = False
    notes: list[str] = Field(default_factory=list)


class StartValues(BaseModel):
    """A forecast's starting values; unset ones are the fitted run's own."""

    X0: float | None = None
    P0: float | None = None
    S0: float | None = None


class ForecastRequest(BaseModel):
    # A kept kinetic fit, or the fit itself inline for the sample run.
    fitArtifactId: str | None = None
    fit: KineticFit | None = None
    start: StartValues = Field(default_factory=StartValues)
    # Who changed a starting value; a changed one is that person's assumption.
    changedBy: str | None = None
    # Hours; unset is the fitted run's own length.
    durationH: float | None = None
    sample: bool = False


class Band(BaseModel):
    """One series' band for readings: the 5th to 95th percentile, and the median."""

    role: SeriesRole
    unit: str
    low: list[float]
    median: list[float]
    high: list[float]


class Interval(BaseModel):
    role: str
    unit: str
    low: float
    median: float
    high: float


class ForecastResult(BaseModel):
    times: list[float]
    bands: list[Band]
    finals: list[Interval]
    # Product made per substrate used, when the two share a mass unit.
    yieldInterval: Interval | None = None
    # Where the median substrate curve reaches zero, the forecast ends.
    substrateRunsOutH: float | None = None
    draws: int
    seed: int
    artifactId: str | None = None
    evidence: Evidence | None = None
    sample: bool = False
    notes: list[str] = Field(default_factory=list)


# ── passages (OF-BLD-014 §4.1) ─────────────────────────────────────────

PassageKind = Literal["abstract", "prose", "table", "figure"]


class Passage(BaseModel):
    """A piece of a fetched paper's own text, as a search returns it."""

    # `<paperId>:<sectionId>:<n>`
    id: str
    paperId: str
    sectionId: str
    heading: str
    kind: PassageKind
    text: str
    # Offsets into the section's text.
    start: int
    end: int


class RagLane(BaseModel):
    name: str
    available: bool
    # Why it is unavailable, or what it needs, in words.
    why: str | None = None


class RagStatus(BaseModel):
    papersIndexed: int
    passages: int
    lanes: list[RagLane]
    chosenLane: str
    # The index's manifest, so a scorecard made on another index shows it.
    manifestHash: str = ""


class PassageHit(BaseModel):
    """One passage a search returned (OF-BLD-014 §4.2)."""

    passage: Passage
    # The fused score: the sum over lanes of 1 / (60 + rank).
    score: float
    # Where each lane ranked it, 1 for first: "bm25", "dense", "phrasing-1", …
    lanes: dict[str, int] = Field(default_factory=dict)
    # From the grading reader, when a rerank lane ran: its grade, and the
    # sentence it copied, checked verbatim against the passage.
    grade: int | None = None
    sentence: str | None = None


# ── retrieval scorecard (OF-BLD-014 §4.3) ──────────────────────────────


class RagMetrics(BaseModel):
    """One lane on one question set."""

    questions: int
    recall5: float
    recall10: float
    recall20: float
    mrr10: float
    ndcg10: float
    medianSeconds: float
    costPerQuestion: float


class RagLaneReport(BaseModel):
    lane: str
    available: bool
    why: str | None = None
    paid: bool
    # Mean nDCG@10 over K and S (the sets present); None when it did not run.
    score: float | None = None
    sets: dict[str, RagMetrics] = Field(default_factory=dict)
    # Questions left unscored because the helper model declined them.
    refused: int = 0


class RagSetInfo(BaseModel):
    name: str
    questions: int
    # How the set was built and what it holds, in words.
    note: str


class RagReport(BaseModel):
    date: str
    manifestHash: str
    papersIndexed: int
    passages: int
    sets: list[RagSetInfo]
    lanes: list[RagLaneReport]
    chosenLane: str
    # The rule that chose it, in words.
    rule: str
    totalCostUsd: float


class RagSearchRequest(BaseModel):
    question: str
    k: int = 8
    # A lane by name, or None for the chosen one.
    lane: str | None = None


class RagSearchResponse(BaseModel):
    """What `POST /api/rag/search` returns (OF-BLD-014 §4.4)."""

    lane: str
    hits: list[PassageHit]
    # The other phrasings the expand lane searched, when it ran.
    phrasings: list[str] = Field(default_factory=list)
    # Sentences the grading reader returned that were not in their passage.
    unverifiedSentences: int = 0
    costUsd: float = 0.0
    # Why another lane ran in place of the chosen one, when it did.
    note: str | None = None


# ── Proforma's BioSTEAM scenario (OF-BLD-014 §8.3) ──────────────────────


class BoundRecord(BaseModel):
    """One record an input was bound to, in the input's unit."""

    id: str
    paperId: str
    value: float
    organism: str | None = None
    carbonSource: str | None = None
    provenance: Provenance


class ScenarioInput(BaseModel):
    key: str
    label: str
    unit: str
    # 'records': the median and range of bound records; 'assumption': a named
    # person typed it; 'waiting': neither yet, so the scenario cannot run.
    binding: Literal["records", "assumption", "waiting"]
    value: float | None = None
    low: float | None = None
    high: float | None = None
    # 'triangular' over min, median, max; 'uniform' over a pair or an
    # assumption's range; 'fixed' for a single source.
    sampling: Literal["triangular", "uniform", "fixed"] | None = None
    source: BasisSource | None = None
    recordIds: list[str] = Field(default_factory=list)
    records: list[BoundRecord] = Field(default_factory=list)
    # Records of the field left out because they name no carbon source, or
    # one that is not a sugar or a hydrolysate.
    leftOutNoCarbon: int = 0
    leftOutOtherCarbon: int = 0
    # Words the inputs table prints: 'single source', a clip to the ceiling,
    # a refused conversion.
    flags: list[str] = Field(default_factory=list)


class InputAssumption(BaseModel):
    key: str
    value: float
    low: float
    high: float
    by: str
    at: str
    note: str | None = None


class ProformaScenarioInfo(BaseModel):
    id: str
    name: str
    product: str
    flowsheet: str
    host: str | None = None
    hosts: list[str] = Field(default_factory=list)
    inputs: list[ScenarioInput]
    waiting: list[str] = Field(default_factory=list)
    leavesOut: list[str] = Field(default_factory=list)
    priceBasis: str


class ProformaRunRequest(BaseModel):
    scenarioId: str
    assumptions: list[InputAssumption] = Field(default_factory=list)
    host: str | None = None
    seed: int = 0


class HistogramBin(BaseModel):
    low: float
    high: float
    count: int


class InputSensitivity(BaseModel):
    key: str
    rho: float
    sourceKind: str


class ProformaGrid(BaseModel):
    dims: list[dict[str, Any]]
    msp: list[float | None]
    costLines: dict[str, list[float | None]]
    infeasible: int


class ProformaRunResult(BaseModel):
    scenarioId: str
    artifactId: str
    provenance: Provenance
    inputs: list[ScenarioInput]
    basePrice: float | None
    baseCostLines: dict[str, float] | None
    baseInfeasible: str | None = None
    quantiles: dict[str, float]
    histogram: list[HistogramBin]
    sensitivity: list[InputSensitivity]
    samples: int
    feasible: int
    infeasible: dict[str, int]
    grid: ProformaGrid
    readBack: dict[str, float]
    leavesOut: list[str]
    priceBasis: str
    evidence: Evidence


# ── Runbook drafts (OF-BLD-014 §9.2) ────────────────────────────────────


class Prediction(BaseModel):
    """Mirrors `Prediction` in src/data/types.ts (§9.1)."""

    id: str
    label: str
    value: float
    unit: str
    confidence: Literal["high", "medium", "low"]
    basis: str
    kind: Literal["point", "interval", "bound"] | None = None
    interval: Range | None = None
    artifactId: str | None = None
    recordIds: list[str] | None = None


class Measure(BaseModel):
    """Mirrors `Measure` in src/data/types.ts."""

    id: str
    label: str
    unit: str
    timepoint: str
    predictionId: str | None = None


DraftTimepoint = Literal["start", "mid-run", "harvest", "after recovery"]


class DraftItem(BaseModel):
    """One prediction the agent asks for: one computed evidence item, or
    records of one field. The pair it leaves unused is empty."""

    model_config = ConfigDict(extra="forbid")

    label: str
    evidenceId: str = ""
    field: str = ""
    recordIds: list[str] = Field(default_factory=list)


class DraftMeasure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    unit: str
    timepoint: DraftTimepoint
    itemLabel: str


class RunbookDraft(BaseModel):
    title: str
    productId: str
    strainId: str
    predictions: list[Prediction]
    measures: list[Measure]


# Claim and AnswerPlan name Passage and Evidence, which are defined further
# down; resolve the names now that every model exists.
Claim.model_rebuild()
AnswerPlan.model_rebuild()
ToolResult.model_rebuild()
