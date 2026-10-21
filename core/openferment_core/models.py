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

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    # OF-BLD-015 §7.2: module rows it rests on, as `<module>/<kind>/<id>`,
    # each returned by a module's read tool in this run.
    moduleRefs: list[str] = Field(default_factory=list)


class PassageRef(BaseModel):
    """A sentence a claim quotes, and the passage it stands in."""

    passageId: str
    quote: str


TraceKind = Literal["coverage", "tool", "restart", "final"]
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


# ── Coverage (OF-BLD-015 §7.1) ─────────────────────────────────────────
#
# Before Postdoc's first turn, code sweeps every module store for what the
# question names, so Postdoc never calls a thing absent that a screen shows.

# The one state every module row reads as (OF-BLD-015 §7.2). It is computed
# in `module_stores.py` from the module's own word (a clearance state, a
# runbook's status and lock, a check's state), never chosen by a model.
ModuleState = Literal["open", "fenced", "approved", "locked", "proposed", "retired"]
ModuleName = Literal["dominion", "runbooks", "geneos", "fermos", "pureos", "proforma", "biorepo", "guild",
                     "primer", "intake", "home"]


class CoverageHit(BaseModel):
    """One row of one module that the question names."""

    # `<module>/<kind>/<id>`, the id a claim cites it by.
    ref: str
    id: str
    kind: str
    label: str
    state: ModuleState


class ModuleCoverage(BaseModel):
    """What the sweep found in one module."""

    module: ModuleName
    label: str
    # How many rows match; `hits` lists at most COVERAGE_HITS of them.
    count: int = 0
    hits: list[CoverageHit] = Field(default_factory=list)
    # The question names the module itself ("what is open in Dominion").
    named: bool = False
    # Set when part of the module lives only in a browser, in words.
    partial: str | None = None
    # Set when the module's store could not be read, in words.
    error: str | None = None


class ModuleRow(BaseModel):
    """One row a module's read tool returns (OF-BLD-015 §7.2): what the
    module holds, where it stands, and how it is marked."""

    module: ModuleName
    kind: str
    id: str
    # `<module>/<kind>/<id>`, what a claim cites.
    ref: str
    label: str
    # Computed from `status` by module_stores, never by a model.
    state: ModuleState
    # The module's own word: a clearance state, a runbook status, an ingest state.
    status: str
    # The row's provenance mark when the module keeps one; null for a seed
    # row that carries none (a lesson, a unit operation).
    provenance: Provenance | None = None
    # A few named fields the module shows, kept short.
    detail: dict[str, Any] = Field(default_factory=dict)


class AuditEntry(BaseModel):
    """One line of core/data/audit.jsonl (OF-BLD-015 §7.3): a write a model
    made, or a proposal a person carried out or dismissed."""

    at: str
    agent: Literal["model", "person"]
    # The model id, or the person's name.
    who: str
    module: ModuleName
    action: str
    # The state the write left behind, or `proposed`, `done`, `dismissed`.
    state: str
    target: str | None = None
    askId: str | None = None
    effort: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


ProposalState = Literal["proposed", "done", "dismissed"]


class Proposal(BaseModel):
    """What a model asked for at a gate (OF-BLD-015 §7.4), until a person
    carries it out or dismisses it on Home."""

    id: str
    at: str
    module: ModuleName
    action: str
    gate: str
    title: str
    why: str
    # What the button does, in words, and where it takes the person when the
    # server cannot act itself.
    how: str
    route: str | None = None
    server: bool = False
    target: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    note: str = ""
    # The model that proposed it.
    by: str
    askId: str | None = None
    state: ProposalState = "proposed"
    carriedOutBy: str | None = None
    carriedOutAt: str | None = None
    result: str | None = None


class Proposals(BaseModel):
    """core/data/proposals.json."""

    version: Literal[1] = 1
    proposals: list[Proposal] = Field(default_factory=list)


class ProposalAction(BaseModel):
    """A person carrying out or dismissing a proposal."""

    person: str
    reason: str = ""
    # The Guild person id the browser is acting as: a check is asked for by a
    # person on Guild, which knows people by id, never by the reviewer name
    # (OF-BLD-016 §1.R finding 11). None when nobody is chosen.
    actingId: str | None = None


class ArchivedCoverage(BaseModel):
    """What the question names in one archived program, left out of the
    sweep while archived programs are hidden (OF-BLD-016 §2.3, E.2′): the
    trace says "found in archived program PHA (hidden)" and the plan carries a
    gap naming the switch."""

    # The program's id and its name, as src/data/programs.ts declares them.
    program: str
    name: str
    # The question's own words that named it.
    entities: list[str] = Field(default_factory=list)
    # How many hidden rows the question names, and the modules they sit in.
    count: int = 0
    modules: list[ModuleName] = Field(default_factory=list)


class CoverageMap(BaseModel):
    """The sweep, module by module, in the order the rail lists them."""

    # Names the question was found to hold, in its own words.
    entities: list[str] = Field(default_factory=list)
    searched: int = 0
    found: int = 0
    modules: list[ModuleCoverage] = Field(default_factory=list)
    # OF-BLD-016 §2.3: whether archived programs were swept (the browser's
    # switch), and, when they were not, what the question names in them.
    includeArchived: bool = False
    archived: list[ArchivedCoverage] = Field(default_factory=list)


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
    # OF-BLD-015 §7.1: the modules swept before the first turn, and what each
    # held. The answer's footer reads it; null on the single-call path.
    coverage: CoverageMap | None = None
    # OF-BLD-015 §7.2: the module rows the claims cite.
    rows: list[ModuleRow] = Field(default_factory=list)
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
    # OF-BLD-016 §2.3: the browser's "show archived programs" switch. Off,
    # the evidence pool, the passages, the coverage pass and every read tool
    # leave archived programs out. It rides in the tools' context from this
    # request; no tool input carries it.
    includeArchived: bool = False


# ── Programs (OF-BLD-016 §2.1, E.1′, E.2′) ──────────────────────────────
#
# A program is data: the corpus threads that are its papers, a name, and
# whether it is active or archived. Declared in src/data/programs.ts and
# written into corpus.json and modules.json by `pnpm export:corpus`;
# `programs.py` reads them. Mirrors `Program` in src/data/types.ts.

ProgramStatus = Literal["active", "archived"]


class Program(BaseModel):
    id: str
    name: str
    letters: list[str]
    status: ProgramStatus
    summary: str


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
    # (nobody chosen as learning).
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
    # Module rows a plan may cite (OF-BLD-015 §7.2).
    rows: list[ModuleRow] = Field(default_factory=list)
    # The whole of what a summary cuts to the cap, for the HTTP endpoint and
    # the MCP server: a model reads `summary` alone (OF-BLD-019 §6.1:
    # `stream_table`'s whole stream table). Nothing here is citable.
    data: dict[str, Any] | None = None


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
    # The model fitted (OF-BLD-020 §3.1): the closed-form logistic,
    # `logistic_v0`, as before, or a kinetics family by id (`batch_v1`).
    family: str = "logistic_v0"


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
    # Why a kinetics family's fit reports it unidentified (OF-BLD-020 §3.R,
    # finding 3), in the order a reader names them: the run's lack of a
    # biomass series held X0 at a gauge it scales with ("gauge"), μmax by rule
    # ("rule"), the optimizer's budget ("budget"), the Jacobian's null space
    # ("null-space"), the interval reaching zero ("interval"). Left out of a
    # parameter it does not apply to, so a logistic fit's file is unchanged.
    unidentifiedBy: list[Literal["gauge", "rule", "budget", "null-space", "interval"]] | None = Field(
        default=None, exclude_if=lambda v: v is None)


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
    """Logistic growth, Luedeking–Piret production and the substrate balance
    (`logistic_v0`), or a kinetics family fitted to the same series
    (OF-BLD-020 §3.1)."""

    params: list[FitParam] = Field(default_factory=list)
    quality: list[SeriesFitQuality] = Field(default_factory=list)
    # The covariance of `params`, in their order, for a forecast to draw from.
    covariance: list[list[float]] = Field(default_factory=list)
    series: list[FermosSeries] = Field(default_factory=list)
    reason: str | None = None
    # The model fitted. A fit kept before OF-BLD-020 holds no `model` and
    # reads as `logistic_v0`, which it is.
    model: str = "logistic_v0"
    # What the fit says of itself in words: the terms it held, a parameter
    # reported unidentified by rule, the optimizer's passes.
    notes: list[str] = Field(default_factory=list)


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
    # Who set the length; a length a person set is that person's assumption
    # (OF-BLD-020 §3.R). Unset: the one who changed a starting value, if any.
    durationBy: str | None = None
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
    # The thread the questions were drawn from (OF-BLD-016 §4.1), or None for
    # every paper. Every search ran over the whole index either way.
    thread: str | None = None
    # The lane search runs on now (core/data/index/config.json), which a person
    # may hold apart from the rule's choice; the API fills it when it serves the
    # report, and the stored report leaves it None (OF-BLD-016 §4.1).
    laneInUse: str | None = None


class RagSearchRequest(BaseModel):
    question: str
    k: int = 8
    # A lane by name, or None for the chosen one.
    lane: str | None = None
    # OF-BLD-016 §2.3: the browser's switch; off leaves archived programs'
    # passages out.
    includeArchived: bool = False


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
    # person typed it; 'artifact': a fermOS fit or forecast a person chose
    # computes it (OF-BLD-019 §5.1, D10), its source naming the artifact;
    # 'waiting': none of these yet, so the scenario cannot run.
    binding: Literal["records", "assumption", "artifact", "waiting"]
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
    # The older field (OF-BLD-014 §8.4): a named person's values by input
    # key. Accepted for one release as a shim (OF-BLD-020 §2.2): each is read
    # as an Override of `proforma:<scenarioId>`, and the run's basis says
    # which field it read.
    assumptions: list[InputAssumption] = Field(default_factory=list)
    # A person's changes in the parameter panel (OF-BLD-020 D3), each an
    # Override of scope `proforma:<scenarioId>`: a named assumption that wins
    # over the records and any fermOS fit for its input, and that the run's
    # basis names with the person. The service keeps none.
    overrides: list[Override] = Field(default_factory=list)
    host: str | None = None
    seed: int = 0
    # How many Latin hypercube samples the run draws (OF-BLD-019 D7). The
    # default is proforma.SAMPLES, held equal by test_proforma, and
    # proforma.run refuses more than proforma.MAX_SAMPLES, in words.
    samples: int = 500
    # The shelf flowsheet a scenario made in the browser runs (OF-BLD-019
    # §2.3, D6): a seed scenario runs its own and needs none; a scenario id
    # that is not a seed scenario's runs this one, bound as
    # GET /api/proforma/bind binds it. A reference biorefinery, the toy or an
    # id the shelf does not hold is refused in words.
    flowsheet: str | None = None
    # The fermOS fits a person chose, by input key: titre, yield and
    # productivity, each the id of a kept `kinetic_fit` or `growth_forecast`
    # artifact (OF-BLD-019 §5.1, D10). The service computes each value from
    # the artifact; a model never picks one. A fit that cannot feed an input
    # is refused in words naming the parameter.
    fits: dict[str, str] = Field(default_factory=dict)


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
    # OF-BLD-019 §2.1 (D1): the base case's tables, as the one run artifact
    # holds them; `ProformaTables` says what each is. All defaulted, so a run
    # stored before them still reads.
    flowsheet: str | None = None
    tablesSource: str | None = None
    tea: TeaBreakdown | None = None
    streams: list[StreamRow] = Field(default_factory=list)
    units: list[UnitRow] = Field(default_factory=list)
    utilities: UtilityDuties | None = None
    diagram: str | None = None
    diagramNote: str | None = None
    unitOrder: list[str] = Field(default_factory=list)
    tableUnits: dict[str, str] = Field(default_factory=dict)


# ── A fermOS fit feeds the fermenter (OF-BLD-019 §5.1, D10) ─────────────


class FitFeed(BaseModel):
    """What one fermOS artifact gives one input of a flowsheet: the value in
    the input's unit, with the 5th and 95th percentile of the forecast's band
    for readings, or why it gives nothing, in words naming the parameter."""

    key: str
    unit: str
    value: float | None = None
    low: float | None = None
    high: float | None = None
    # How the value is computed from the artifact, in words.
    derivation: str
    # Why it gives nothing; None when it gives the value.
    refused: str | None = None


class FermosFitInfo(BaseModel):
    """A kinetic fit or a forecast fermOS keeps, and what it can feed one
    shelf flowsheet (GET /api/fermos/fits). A person picks it; a model never
    does."""

    artifactId: str
    # 'kinetic_fit' or 'growth_forecast'.
    tool: str
    provenance: Provenance
    createdAt: str
    flowsheet: str
    # The run the fit was made on, and the kinetic fit a forecast rests on
    # (a kinetic fit's own id for a fit).
    depositionId: str | None = None
    fitArtifactId: str | None = None
    # The product and sugar series, by the labels the run gave them.
    productSeries: str | None = None
    substrateSeries: str | None = None
    # The batch time a productivity is the titre over: the hour a forecast's
    # median sugar runs out, or a simulation's harvest hour.
    batchTimeH: float | None = None
    # How that hour was found, in words chosen by the tool that kept it (a
    # forecast's grid or a simulation's harvest, OF-BLD-020 §8.R): what the
    # run's `fit batch time` input and the page say of it.
    batchTimeNote: str | None = None
    feeds: list[FitFeed] = Field(default_factory=list)
    # Words printed beside it, such as a product series that names no product.
    flags: list[str] = Field(default_factory=list)
    # Why it feeds nothing at all, in words.
    refused: str | None = None


# ── The geneOS ceiling check (OF-BLD-019 §5.2, D11) ─────────────────────
#
# A scenario's fermenter yield read against the newest stored geneOS
# ceiling of each shelf model of its organism, on its flowsheet's sugar.
# A flag, never a bound: nothing is clamped, and the binding and the run
# are untouched. Computed on read (GET /api/proforma/ceiling-check) and
# kept nowhere; every number is the ceiling artifact's, a record's, a
# person's assumption's or a fit's, converted through units.py and the
# conventions the ceiling's own basis names.


class CeilingRow(BaseModel):
    """One stored ceiling beside the scenario's yield, both on the ceiling's
    own footing, grams of product per gram of sugar and mol per mol."""

    modelId: str
    # The model as geneOS's shelf names it, and as the ceiling's basis names it.
    modelName: str
    modelBasis: str
    # The strain the reconstruction describes, and how the scenario's organism
    # maps to it: 'strain' (the same strain) or 'species' (another strain of
    # its species), with the words that say so.
    host: str | None = None
    match: Literal["strain", "species"]
    matchWords: str
    product: str
    substrate: str
    # The newest stored `geneos.ceiling` of this model, product and sugar, and
    # how many older ones it stands in front of.
    artifactId: str
    provenance: Provenance
    createdAt: str
    older: int = 0
    # The ceiling as its artifact holds it.
    ceilingGPerG: float
    ceilingMolPerMol: float | None = None
    # The product and sugar conventions the ceiling's basis names, in its words.
    conventions: list[str] = Field(default_factory=list)
    # The scenario's yield in the ceiling's basis: g per g through units.py,
    # and mol per mol at the ceiling's own conventions (its molPerMol over its
    # gPerG); None where the yield waits or the ceiling is zero.
    yieldGPerG: float | None = None
    yieldLowGPerG: float | None = None
    yieldHighGPerG: float | None = None
    yieldMolPerMol: float | None = None
    # 'above' when the yield or its high end exceeds the ceiling; 'within' at
    # or under it; 'no-yield' when the yield waits for a source.
    flag: Literal["above", "within", "no-yield"]
    words: str
    # The bound records whose own value is above the ceiling, each for a
    # reviewer to check its basis.
    recordsAbove: list[str] = Field(default_factory=list)


class CeilingCheck(BaseModel):
    """GET /api/proforma/ceiling-check: one scenario's fermenter yield beside
    every stored ceiling of its organism's shelf models on its sugar."""

    scenarioId: str
    flowsheet: str
    # What the flowsheet makes and the sugar its feed is, as geneOS names them.
    product: str
    substrate: str
    sugarWords: str
    # The scenario's organism: its host filter, else the strains its yield's
    # records name, else its program's one species; and how that was read.
    host: str | None = None
    strains: list[str] = Field(default_factory=list)
    species: list[str] = Field(default_factory=list)
    organismWords: str
    # The shelf models of that organism with a route to the product.
    models: list[str] = Field(default_factory=list)
    # The yield as the scenario binds it, in the input's unit.
    yieldBinding: Literal["records", "assumption", "artifact", "waiting"]
    yieldValue: float | None = None
    yieldLow: float | None = None
    yieldHigh: float | None = None
    yieldUnit: str
    yieldSource: BasisSource | None = None
    # The tool of the artifact a yield bound to one came from ('kinetic_fit',
    # 'growth_forecast', 'fermos.simulation'), so the page names it as what
    # it is (§8.R); None for any other binding.
    yieldTool: str | None = None
    yieldRecords: int = 0
    yieldWords: str
    rows: list[CeilingRow] = Field(default_factory=list)
    flagged: bool = False
    # With no ceiling on file: what is missing, and where one is computed.
    empty: str | None = None
    computeAt: str
    # Sugars other stored ceilings of these models are on, left aside here.
    otherSugars: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ── Proforma's shelf and the run's tables (OF-BLD-019 §2.1) ─────────────
#
# The shelf is data (flowsheets/shelf.py, D2). A run is one `proforma.run`
# artifact (D1) holding the price, the sensitivity and, for its base case,
# every table below, each read by the Proforma worker from BioSTEAM's own
# objects; nothing recomputes them on read. Units are BioSTEAM's: a
# stream's T in K and P in Pa, flows in kg/hr, a unit's duties in kJ/hr and
# its power in kW, costs in USD, annual amounts in USD/yr; `tableUnits` in
# the artifact names them, and UtilityDuties carries each unit as the
# UnitGroup states it.


class FlowsheetInput(BaseModel):
    """One input a shelf flowsheet takes. It names the ontology fields whose
    records bind it; with none, a named person's assumption or a stated
    convention sets it. The file of the flowsheet holds no value for it."""

    key: str
    name: str
    # The unit table's family where the unit has one (src/engine/units.ts:
    # massConc, yield, volProd, costUSD), else a word: massFlow, fraction.
    dimension: str
    unit: str
    fields: list[str] = Field(default_factory=list)
    kind: Literal["process", "economic", "convention"]
    note: str


class FlowsheetInfo(BaseModel):
    id: str
    title: str
    description: str
    # The package and version it comes from ('biorefineries 2.35.1,
    # cornstover'), or 'this repository'.
    source: str
    # A program id from src/data/programs.ts; None for a general flowsheet.
    program: str | None = None
    # A published reference biorefinery, run whole on its package's defaults.
    reference: bool = False
    inputs: list[FlowsheetInput] = Field(default_factory=list)
    # The names its evaluation (or its whole run) reports.
    outputs: list[str] = Field(default_factory=list)
    # Which output is the price, and what it is a price of.
    priceOutput: str | None = None
    priceBasis: str | None = None
    leavesOut: list[str] = Field(default_factory=list)
    # The inputs a run's grid walks, for the sliders; none, no grid.
    gridInputs: list[str] = Field(default_factory=list)
    # A reference biorefinery's own regression test, cited as file::test
    # ('biorefineries/tests/test_biorefineries.py::test_corn'); its values
    # are read from the installed file (PackageRegression), never retyped.
    packageTest: str | None = None


# ── A reference biorefinery's run (OF-BLD-019 §2.2, D3) ──────────────────
#
# A published biorefinery runs whole on its package's defaults and is kept
# as one `proforma.reference` artifact: the package's outputs, the
# quantities its own test asserts as this installation computed them, the
# defaults read back, and every table a `proforma.run` artifact holds. The
# test's values come from the installed test file, parsed, with the file
# and test named.


class RegressionValue(BaseModel):
    """One value a package's own test asserts, as its test file writes it."""

    # The expression the test asserts on ('tea.IRR', 'units.get_heating_duty()').
    expression: str
    label: str
    unit: str
    # The value the test asserts, and the relative tolerance it allows.
    package: float
    rtol: float


class PackageRegression(BaseModel):
    """A reference biorefinery's regression values, read from the package's
    installed test file: which package, which file, which test."""

    package: str
    file: str
    test: str
    values: list[RegressionValue] = Field(default_factory=list)


class RegressionCheck(BaseModel):
    """One of the package test's values beside what this installation computed."""

    expression: str
    label: str
    unit: str
    measured: float | None = None
    package: float
    rtol: float
    # |measured − package| / |package|; None when the package's value is zero
    # (the check is then |measured| within rtol of nothing, as numpy's allclose
    # with its default absolute tolerance has it).
    relDiff: float | None = None
    within: bool


class ProformaReference(BaseModel):
    """GET and POST /api/proforma/reference/{id}: the shelf's entry, the
    newest stored reference run (or None), the package test's values, and
    where the simulator is."""

    flowsheet: FlowsheetInfo
    artifact: Artifact | None = None
    regression: PackageRegression | None = None
    simulator: dict[str, Any] = Field(default_factory=dict)


class StreamRow(BaseModel):
    """One stream of the base case, as BioSTEAM holds it after the run."""

    id: str
    # The unit it leaves and the unit it enters; None for a feed or a product.
    source: str | None = None
    sink: str | None = None
    phase: str
    T: float
    P: float
    massFlow: float
    # Mass flow by component, the components that flow alone.
    massFlows: dict[str, float] = Field(default_factory=dict)
    # USD/kg, when the stream carries a price.
    price: float | None = None


class UnitRow(BaseModel):
    """One unit operation, in run order."""

    id: str
    # The BioSTEAM class, and BioSTEAM's own name for its line.
    unitClass: str
    line: str | None = None
    order: int
    ins: list[str] = Field(default_factory=list)
    outs: list[str] = Field(default_factory=list)
    installedCost: float
    purchaseCost: float
    # None where the unit has no heat utility, or draws no power.
    heatingDuty: float | None = None
    coolingDuty: float | None = None
    power: float | None = None


class UtilityDuties(BaseModel):
    """BioSTEAM's UnitGroup over the plant's units: each total with the unit
    the UnitGroup states for it."""

    group: str
    heating: float
    heatingUnit: str
    cooling: float
    coolingUnit: str
    electricityConsumption: float
    electricityConsumptionUnit: str
    electricityProduction: float
    electricityProductionUnit: str


class TeaLine(BaseModel):
    """One line of the price, per year and per unit of the price's basis.
    The lines sum to the main product's revenue by construction."""

    key: Literal["feedstock", "otherMaterials", "utilities", "otherVariable", "fixedOperating",
                 "capitalRecovery", "coproductCredits"]
    label: str
    usdPerYear: float
    perUnit: float | None = None
    # Which attribute or method of the TEA object it is read from, in words.
    reads: str


class TeaBreakdown(BaseModel):
    """The TEA object's own numbers for the base case, read through its
    attributes and methods, never recomputed."""

    teaClass: str
    product: str
    feedstock: str | None = None
    # The product stream's price per kg as the run solved it (or as the
    # package left it), and the flow in kg/hr the per-unit lines divide by.
    productPrice: float | None = None
    basisFlow: float | None = None
    basis: str | None = None
    operatingHours: float
    sales: float
    materialCost: float
    feedstockCost: float | None = None
    otherMaterialCost: float
    utilityCost: float
    purchaseCost: float
    installedEquipmentCost: float
    FCI: float
    TCI: float
    FOC: float
    laborCost: float | None = None
    # Sales less the annual operating cost: at a solved price, the return
    # on and of the capital and the tax on it, as the cash-flow analysis
    # requires.
    capitalRecovery: float
    coproductCredits: float
    IRR: float | None = None
    incomeTax: float | None = None
    lines: list[TeaLine] = Field(default_factory=list)


class ProformaTables(BaseModel):
    """What a reader takes from a `proforma.run` artifact (proforma.tables_of):
    the flowsheet, what made the tables, and the tables themselves."""

    flowsheet: str | None = None
    # 'BioSTEAM <version>, thermosteam <version>', or the stand-in's label.
    tablesSource: str | None = None
    tea: TeaBreakdown | None = None
    streams: list[StreamRow] = Field(default_factory=list)
    units: list[UnitRow] = Field(default_factory=list)
    utilities: UtilityDuties | None = None
    # SVG text when Graphviz's dot is on the path (D8); else None, the words
    # why, and the units in run order.
    diagram: str | None = None
    diagramNote: str | None = None
    unitOrder: list[str] = Field(default_factory=list)
    tableUnits: dict[str, str] = Field(default_factory=dict)


# ProformaRunResult names the table models defined after it.
ProformaRunResult.model_rebuild()


# ── pureOS reads the train (OF-BLD-019 §4.1, D1) ────────────────────────
#
# A train is read from one `proforma.run` artifact's stream and unit tables
# (pureos.train_of) and never typed: the product is the component the run's
# price is per, else the largest component of its product stream, and every
# mass below is that component's kg/hr in the run's base case. A unit's
# outlets that lead on toward the product stream (directly, through later
# units, or round a recycle) carry the product onward; the others lose it.


class TrainUnit(BaseModel):
    """One unit of a run's train, in run order, with the product's flow
    through it as the stream table states it."""

    id: str
    unitClass: str
    line: str | None = None
    order: int
    ins: list[str] = Field(default_factory=list)
    outs: list[str] = Field(default_factory=list)
    # Whether any of its outlets leads on to the product stream.
    onPath: bool
    # Every component, kg/hr, summed over its inlets and its outlets.
    massIn: float
    massOut: float
    # The product's kg/hr; None when the run names no product.
    productIn: float | None = None
    productOut: float | None = None
    # Of productOut: what leaves by an outlet leading on, and what does not.
    productOnward: float | None = None
    productLost: float | None = None
    # The outlets that carry product off the path.
    lostTo: list[str] = Field(default_factory=list)
    # productOnward / productIn; None, with `note` saying why, when no
    # product enters the unit or the unit is off the path.
    recovery: float | None = None
    # 1 less the product lost at this unit and every on-path unit before it,
    # over everything the path delivers or loses; None off the path.
    cumulative: float | None = None
    note: str | None = None


class Train(BaseModel):
    """A run's train as pureOS reads it, for `/pureos/train/:scenarioId`
    and `pureos_read`."""

    # The scenario the run belongs to (the basis's `scenario`, else the one
    # seed scenario whose modelId is the run's flowsheet); None when no
    # scenario claims it, and the train is then known by its artifact id.
    scenarioId: str | None = None
    scenarioName: str | None = None
    artifactId: str
    flowsheet: str | None = None
    createdAt: str
    provenance: Provenance
    program: str | None = None
    tablesSource: str | None = None
    # The stream the run's TEA prices, and the component traced through it.
    productStream: str | None = None
    product: str | None = None
    # How the product was read from the run, in words.
    productBasis: str
    # The product's kg/hr in the product stream, the sum of every unit's
    # productLost, and productOut over the two together.
    productOut: float | None = None
    productLost: float | None = None
    overallRecovery: float | None = None
    units: list[TrainUnit] = Field(default_factory=list)
    streams: list[StreamRow] = Field(default_factory=list)
    tableUnits: dict[str, str] = Field(default_factory=dict)
    # How many runs of this scenario are on file; the newest is read.
    runs: int = 1
    note: str | None = None
    # OF-BLD-020 §5.2: the artifact a train is read from, a Proforma run or
    # a `pureos.train_run`, and for a train run the train it ran (its id and
    # name as the browser keeps it, D9); None for a Proforma run.
    tool: str = "proforma.run"
    trainId: str | None = None
    trainName: str | None = None


class TrainSummary(BaseModel):
    """One train on file, for pureOS's index: the newest run of a scenario."""

    scenarioId: str | None = None
    scenarioName: str | None = None
    artifactId: str
    flowsheet: str | None = None
    createdAt: str
    provenance: Provenance
    program: str | None = None
    product: str | None = None
    unitCount: int
    overallRecovery: float | None = None
    runs: int = 1
    note: str | None = None
    # As Train's (OF-BLD-020 §5.2).
    tool: str = "proforma.run"
    trainId: str | None = None
    trainName: str | None = None


# ── thermosteam answers property questions (OF-BLD-019 §4.2, D9) ───────
#
# A question names a mixture already on file, never a number: a stream of a
# Proforma run (its artifact id and the stream's id), or a preset the service
# fills — `ethanol-water-azeotrope` (the composition the library's own VLE
# gives) or `beer-at-titre-of` an ethanol titre record (the record's value
# through units.py into a water–ethanol mass fraction). thermo.py keeps the
# answer as one `thermo_props` artifact.


class ThermoPropsRequest(BaseModel):
    """`POST /api/thermo/props`: a run's stream, or a preset (with its
    record for `beer-at-titre-of`). Ids and words only."""

    artifactId: str | None = None
    streamId: str | None = None
    preset: str | None = None
    recordId: str | None = None


class ThermoProps(BaseModel):
    """What a `thermo_props` artifact holds (its `output`): thermosteam's
    answer for one mixture, every number the library's, in its units."""

    # stream, ethanol-water-azeotrope or beer-at-titre-of.
    kind: str
    # The mixture in words, as a page and a label say it.
    subject: str
    runArtifactId: str | None = None
    streamId: str | None = None
    preset: str | None = None
    recordId: str | None = None
    # "thermosteam <version>", read in the worker.
    library: str
    T: float
    P: float
    phase: str
    # "given" (the stream's own) or "thermosteam's Stream default".
    TSource: str
    PSource: str
    # kg/kg, as the library holds the mixture.
    massFractions: dict[str, float] = Field(default_factory=dict)
    density: float | None = None
    Cp: float | None = None
    viscosity: float | None = None
    # Temperatures at the mixture's own pressure.
    bubblePoint: float | None = None
    dewPoint: float | None = None
    # The first bubble's mole fractions.
    vapourAtBubble: dict[str, float] | None = None
    # The library's units for each key above.
    units: dict[str, str] = Field(default_factory=dict)
    # A preset's solve: what was found, and how, in words.
    solved: dict[str, Any] | None = None
    # A property the library could not compute, with its reason; and what
    # the mixture leaves out.
    notes: list[str] = Field(default_factory=list)


# ── a product's properties (OF-BLD-020 §7.1, D12) ───────────────────────
#
# What pureOS's proposer reads about a product: from its sequence, through
# Biopython's ProtParam (protparam.py, one `protparam` artifact), and from its
# thermodynamics, through thermosteam in the Proforma worker (thermo.py, one
# `volatility` artifact). A question names a product by id, never a sequence
# or a number.


class ProductPropertyRequest(BaseModel):
    """`POST /api/protparam` and `POST /api/thermo/volatility`: the product,
    by its id. Nothing else is taken, a sequence least of all."""

    model_config = ConfigDict(extra="forbid")

    product: str


class ProtParam(BaseModel):
    """What a `protparam` artifact holds (its `output`): Biopython's
    ProtParam on one sequence, every number the library's."""

    # "the sequence of product <id>", "the sequence of record <id>".
    subject: str
    product: str | None = None
    # Where the sequence was read, in words (the product entry's
    # sequenceSource, or the record).
    sequenceSource: str
    # Residues in the chain.
    length: int
    # "Biopython <version>".
    library: str
    molecularWeight: float
    isoelectricPoint: float
    # At 280 nm: every cysteine reduced, and every pair of cysteines a cystine.
    extinctionReduced: float
    extinctionCystines: float
    gravy: float
    # The unit of each key above ("" for none).
    units: dict[str, str] = Field(default_factory=dict)
    # How the library computes each, in words.
    how: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class Volatility(BaseModel):
    """What a `volatility` artifact holds (its `output`): thermosteam's
    normal boiling points for a product's chemical and its partner (water),
    and whether the library's own vapour-liquid equilibrium gives the pair a
    minimum-boiling azeotrope, every number the library's."""

    product: str
    # The library's own name for the product, and the partner it is asked with.
    chemical: str
    partner: str
    subject: str
    # "thermosteam <version>", read in the worker.
    library: str
    P: float
    # "given", or "thermosteam's Stream default".
    PSource: str
    # The library's normal boiling point (Tb) of each; null when it holds none.
    boilingPoint: float | None = None
    partnerBoilingPoint: float | None = None
    # Which of the two boils lower, the one whose mole fraction is scanned.
    lighter: str | None = None
    # true: found; false: none on the grid `searched`; null: not searched, or
    # the library could not say (the notes say why).
    azeotrope: bool | None = None
    # The azeotrope's liquid as the chemical's mole and mass fractions, and the
    # temperature it boils at, at P.
    azeotropeMoleFraction: float | None = None
    azeotropeMassFraction: float | None = None
    azeotropeT: float | None = None
    # The grid searched: the lighter chemical's mole fraction from, to, the
    # points, and the halvings that refine a bracket.
    searched: dict[str, Any] | None = None
    # The library's unit for each key above.
    units: dict[str, str] = Field(default_factory=dict)
    how: str = ""
    notes: list[str] = Field(default_factory=list)


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


# ── One parameter panel (OF-BLD-020 §2.1, D2–D4) ────────────────────────
#
# Every model family, vessel design, catalogue unit and shelf flowsheet
# declares its parameters once, in Python, as `ParameterSpec`s; the service
# resolves each to a `ParameterValue` naming where its value came from, in
# the order its `sourceRule` gives. A person's change is an `Override`: a
# named assumption the browser keeps (D3) and a run carries, which the
# basis names as an `assumption`, so the result's provenance is `demo`.
# Bounds are conventions with a written reason (D4): a value outside them
# is kept and flagged in words, never clamped. `params.py` holds the rules.

# The chip a value shows: finer than BasisSource.kind, because a fit and a
# simulation are both artifacts and a library's default is a model source.
# `not-read`: a parameter the request's other choices leave unread (a
# fed-batch's mu_set under a constant feed), which waits for nothing
# (OF-BLD-020 §3.R, finding 16).
ParamOrigin = Literal["fit", "record", "artifact", "simulation", "assumption", "convention", "library-default", "waiting",
                      "not-read"]
# What a scope parameterises: a fermOS model family, a vessel designed for
# a simulation, one unit of a pureOS train, or a Proforma scenario.
ParamScopeKind = Literal["fermos-family", "fermos-vessel", "fermos-forecast", "pureos-unit", "proforma"]
# The entries a sourceRule may hold besides a record's, which names its
# field as "record:<ontology field id>".
SOURCE_RULE_ENTRIES = ("fit", "artifact", "simulation", "assumption", "convention", "library-default")


class ParameterSpec(BaseModel):
    """One parameter as its model, unit or flowsheet declares it. No value
    lives here but the stated convention and the bounds, each with its
    reason."""

    key: str
    label: str
    # As written in the equations, plain Unicode; empty when it has none.
    symbol: str
    # What the symbol means, in words: the panel's Why.
    gloss: str
    # A units.ts family (massConc, yield, volProd, costUSD) or a word.
    dimension: str
    # Empty for a share, a dimensionless number or a choice.
    unit: str
    min: float | None = None
    max: float | None = None
    step: float | None = None
    scale: Literal["linear", "log"] = "linear"
    group: str
    # Ordered: fit, record:<field id>, artifact, simulation, assumption,
    # convention, library-default. The first with a value wins; an Override
    # wins over all of them.
    sourceRule: list[str]
    note: str | None = None
    # Required (D4): a physical limit, an ontology plausibility range, or
    # the library's validity range, said in words.
    boundsReason: str
    # A parameter chosen from words (a feed profile, a kLa method, a vessel
    # material); None for a number.
    choices: list[str] | None = None
    # The stated convention, when the rule holds "convention"; its reason
    # is in `note`.
    convention: float | str | None = None

    @field_validator("boundsReason")
    @classmethod
    def _bounds_have_a_reason(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("every parameter's bounds carry a written reason (OF-BLD-020 D4)")
        return v

    @field_validator("sourceRule")
    @classmethod
    def _rule_is_known(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("a parameter names where its value comes from")
        for entry in v:
            if entry in SOURCE_RULE_ENTRIES or (entry.startswith("record:") and entry[len("record:"):].strip()):
                continue
            raise ValueError(f"{entry!r} is not a source: a rule holds fit, record:<field id>, artifact, simulation, "
                             "assumption, convention or library-default")
        return v


class ParameterValue(BaseModel):
    """A parameter's value in one scope, with where it came from."""

    key: str
    # None while it waits.
    value: float | str | None
    low: float | None = None
    high: float | None = None
    # None while it waits.
    source: BasisSource | None
    origin: ParamOrigin
    # Set only when the origin is a fit.
    identified: bool | None = None
    # The person's name, when an Override set it.
    overriddenBy: str | None = None
    # BioSTEAM's default read from its code at import, else None.
    libraryDefault: float | str | None = None
    # The records behind it, when its origin is records.
    recordIds: list[str] = Field(default_factory=list)
    # Words: how many records and their range, or why it waits and which
    # field would bind it.
    detail: str | None = None
    # The warning in words when the value lies outside the bounds; the value
    # is kept, never clamped.
    outOfBounds: str | None = None


class Override(BaseModel):
    """A person's change to one parameter of one scope: a named assumption,
    kept in the browser that typed it and sent with the run (D3)."""

    scope: str
    key: str
    value: float | str
    low: float | None = None
    high: float | None = None
    by: str
    at: str
    note: str | None = None

    @field_validator("value", "low", "high", mode="before")
    @classmethod
    def _no_true_or_false(cls, v: Any) -> Any:
        # OF-BLD-020 §2.R (finding 6): pydantic reads a JSON true or false as
        # 1.0 or 0.0 before any check sees it, a number nobody typed.
        if isinstance(v, bool):
            raise ValueError("an override's value, low and high are numbers or words, never true or false")
        return v


class ParamScope(BaseModel):
    """GET /api/params/{scope}: a scope's specs with their current values."""

    scope: str
    kind: ParamScopeKind
    title: str
    specs: list[ParameterSpec]
    values: list[ParameterValue]
    # The keys with no source yet.
    waiting: list[str]
    notes: list[str] = Field(default_factory=list)


class ParamResolveRequest(BaseModel):
    """POST /api/params/{scope}/resolve. Runs nothing."""

    overrides: list[Override] = Field(default_factory=list)
    # A Proforma scenario made in the browser names the shelf flowsheet it
    # runs, as ProformaRunRequest.flowsheet does; a seed scenario needs none.
    flowsheet: str | None = None
    # A strain filter on the records, as GET /api/proforma/bind takes it.
    host: str | None = None
    # The fermOS fits a person chose, by parameter key (artifact ids), as
    # ProformaRunRequest.fits carries them.
    fits: dict[str, str] = Field(default_factory=dict)
    # fermOS's vessel scope (OF-BLD-020 §4.1): the aerated design a scope is
    # for; None is BioSTEAM's own default design. An anaerobic design takes none.
    vesselType: Literal["stirred-tank", "bubble-column"] | None = None
    # fermOS's family scope (OF-BLD-020 §3.2), bound as a simulation binds:
    # the strain whose records bind (None: every strain of the program's
    # organism), the product, the sugar the records must name, the fit a
    # person chose, where the simulation starts (`records`, `fit` or
    # `simulation:<artifact id>`), the run-length preset, and the program
    # switch, which decides what the evidence pool shows.
    strain: str | None = None
    product: str | None = None
    sugar: str | None = None
    fit: str | None = None
    startFrom: str | None = None
    durationPreset: Literal["until-sugar-runs-out", "fit-length"] | None = None
    includeArchived: bool = False
    # pureOS's unit scope (OF-BLD-020 §5.1): the catalogue id of the unit's
    # type, when no train is sent; with a train it must agree with the unit's.
    unitType: str | None = None
    # pureOS's unit scope (§5.2): the whole train, as the browser keeps it
    # (D9), so the unit's per-component keys expand over the train's
    # chemicals and its records bind by the train's program and product; the
    # scope `pureos:unit:<train id>:inlet` is the train's inlet. Its units'
    # typed values are not laid on here: a resolve's `overrides` are.
    train: TrainSpec | None = None


class ParamResolveResult(BaseModel):
    scope: str
    values: list[ParameterValue]
    waiting: list[str]
    # What the overrides would add to a run's basis, each an `assumption`
    # naming the person and what it rests on: the inputs a run of the scope
    # writes for them, built by the function the run builds them with (a
    # Proforma scope's value, low and high, and the line saying the run read
    # overrides; OF-BLD-020 §2.R).
    basisInputs: list[BasisInput]
    # A value outside its bounds, in words.
    warnings: list[str]
    # What the scope's provider says of its values (as ParamScope.notes).
    notes: list[str] = Field(default_factory=list)


# ── fermOS's vessel on BioSTEAM (OF-BLD-020 §4.1, D7) ──────────────────
#
# A vessel is designed for a kept simulation (or, anaerobic only, a kinetic
# fit or forecast) in the Proforma worker: BioSTEAM's AeratedBioreactor or
# NRELAnaerobicBatchBioreactor, every design parameter a ParameterValue with
# its source, and one `fermos.vessel` artifact.


class VesselRequest(BaseModel):
    """POST /api/fermos/vessel. Exactly one of `simulation` and `fit`."""

    # A `fermos.simulation` artifact id.
    simulation: str | None = None
    # A `kinetic_fit` or `growth_forecast` artifact id, read through
    # proforma.fit_info for titre, yield and batch time: anaerobic only.
    fit: str | None = None
    # The aerated design; None is BioSTEAM's own default. An anaerobic
    # design takes none. A person's override of `design` in the panel says
    # the same in BioSTEAM's words, and the two must agree (§4.2).
    vesselType: Literal["stirred-tank", "bubble-column"] | None = None
    # A kLa correlation by the name BioSTEAM registers it ('Riet', 'Dewes'),
    # one its class runs for the design; a convention of this request, as
    # fermos_vessel names it (OF-BLD-020 §4.2, D13). None is the class's own.
    klaMethod: str | None = None
    # A person's changes, each a named assumption (D3), scope
    # `fermos:vessel:<simulation or fit id>`.
    overrides: list[Override] = Field(default_factory=list)
    includeArchived: bool = False


class VesselDesignRow(BaseModel):
    """One line of the design table, read from BioSTEAM's objects."""

    label: str
    value: float | str | bool | None
    # BioSTEAM's unit for it ('m3', 'hr', 'kW', 'kJ/hr'); empty for a count or a word.
    unit: str
    # Where it was read: a design_results key, an auxiliary unit, an attribute.
    readFrom: str


class VesselOxygen(BaseModel):
    """The oxygen balance over the batch: the simulated uptake against the
    transfer the vessel BioSTEAM sized gives (D7)."""

    # Hours, and the simulated uptake at each, in `unit`.
    t: list[float]
    our: list[float]
    # The transfer while the vessel reacts: kLa times the log-mean driving
    # force the class sizes with, in `unit`.
    otr: float
    unit: str
    # [[from, to], …] hours the simulated uptake rises above `otr`.
    short: list[list[float]]
    # kLa achieved and what the peak would need, in `kLaUnit`; None with no aeration.
    kLa: float | None
    kLaNeededAtPeak: float | None
    kLaUnit: str
    # BioSTEAM's correlation, by its registered name ('Riet', 'Dewes').
    method: str | None
    aerated: bool
    # 'peak' or 'batch-average': what the air was sized for.
    oxygenBasis: str | None = None
    # The uptake the air was sized for, and the one the reaction's yields
    # balance (before the scale), per working volume, in `unit`.
    targetUptake: float | None = None
    sized: float | None = None
    balancedUptake: float | None = None
    # The factor the reaction's oxygen was scaled by.
    scale: float
    # Oxygen saturation at the sparged gas, the broth at θ of it, and the
    # log-mean driving force, mmol L⁻¹.
    cStar: float | None = None
    cL: float | None = None
    drivingForce: float | None = None
    # The reaction's oxygen as its yields balance it, kmol h⁻¹.
    reactionO2KmolPerH: float | None = None
    # OF-BLD-020 §4.R. The oxygen the vessel's reaction consumes as designed
    # (after the scale), kmol h⁻¹; the oxygen the simulation took up, per
    # hour of the plant (the trapezoid integral of its uptake over the batch
    # to harvest, times each vessel's working volume and the vessels, over
    # the cycle), kmol h⁻¹; and the floor at or below which BioSTEAM's
    # AeratedBioreactor sizes no air, read from its code, kmol h⁻¹.
    scaledO2KmolPerH: float | None = None
    simulatedO2KmolPerH: float | None = None
    floorKmolPerH: float | None = None


class VesselHeat(BaseModel):
    """The vessel's duty as BioSTEAM found it, beside a cross-check from the
    oxygen the simulation took up at a stated convention (D7, §4.R)."""

    bst: float
    convention: float | None = None
    conventionNote: str
    unit: str = "kJ/hr"
    # OF-BLD-020 §4.R. How BioSTEAM found `bst`: 'heats-of-formation' (the
    # enthalpy and heats of formation out less in) or 'forced-per-oxygen'
    # (a person's Q_O2_consumption times the oxygen the vessel consumed,
    # `consumedKmolPerH`, kmol h⁻¹); None on a design kept before §4.R.
    method: str | None = None
    consumedKmolPerH: float | None = None
    # The oxygen the convention's estimate rests on, kmol h⁻¹: the
    # simulation's (VesselOxygen.simulatedO2KmolPerH).
    oxygenKmolPerH: float | None = None
    # BioSTEAM's duty in words: which way it was found, and whose heat per
    # oxygen when a person forced one.
    dutyNote: str | None = None


class VesselCostItem(BaseModel):
    purchase: float
    installed: float


class VesselCost(BaseModel):
    """BioSTEAM's own cost correlations, read; nothing summed here."""

    purchase: float
    installed: float
    byItem: dict[str, VesselCostItem]
    # USD per hour.
    utility: float
    costIndex: float
    # The year BioSTEAM's source says its default index is of; None when the
    # index set is not that default.
    costIndexYear: int | None = None
    note: str


class VesselDesign(BaseModel):
    """POST /api/fermos/vessel: one `fermos.vessel` artifact, read."""

    artifactId: str
    provenance: Provenance
    createdAt: str
    # The simulation or fit the vessel was designed for, and its tool.
    source: str
    sourceTool: str
    aerobic: bool
    # BioSTEAM's class, and the unit id it was built under.
    unitClass: str
    unitId: str
    # 'stirred-tank' or 'bubble-column' for an aerated vessel; None anaerobic.
    vesselType: str | None = None
    design: list[VesselDesignRow]
    # None for an anaerobic vessel, and `oxygenNote` says so.
    oxygen: VesselOxygen | None = None
    oxygenNote: str | None = None
    heat: VesselHeat
    cost: VesselCost
    # Every design parameter with its source (D2).
    parameters: list[ParameterValue]
    # What the unit held when it was simulated, read back.
    used: dict[str, float | str | bool | None]
    # How the broth fed per hour was found (plant scale or batch volume).
    scale: dict[str, Any]
    # The reaction set built from what the batch made.
    reaction: dict[str, Any]
    flags: list[str] = Field(default_factory=list)
    versions: dict[str, str]
    # The design as one citable value with its basis (OF-BLD-020 §4.2): its
    # id is the artifact's, as fermos_vessel returns it to Postdoc; the
    # screen reads the basis from it.
    evidence: Evidence


class VesselSummary(BaseModel):
    """GET /api/fermos/vessels: one kept `fermos.vessel` artifact."""

    artifactId: str
    provenance: Provenance
    createdAt: str
    source: str
    sourceTool: str
    unitClass: str
    vesselType: str | None = None
    vessels: float | None = None
    volume: float | None = None
    installed: float | None = None


# ── fermOS simulates (OF-BLD-020 §3.1, D1, D5) ─────────────────────────
#
# A model family (kinetics.py) is code with its equations in its docstring
# and its parameters declared as ParameterSpecs; a simulation resolves them
# with their sources (params.resolve), integrates on scipy, and keeps one
# `fermos.simulation` artifact whose basis names every parameter, start
# value and override, and whose provenance is basis_provenance over them
# (a person's override makes it `demo`).


class FamilyInfo(BaseModel):
    """GET /api/fermos/families: a model family as the panel shows it."""

    id: str
    title: str
    # One plain line: what it is.
    what: str
    # Its equations, plain Unicode, as its docstring writes them.
    equations: str
    states: list[str]
    # g L⁻¹ for a concentration, L for V.
    stateUnits: dict[str, str]
    # A socket is declared with its parameters and refuses to run.
    socket: bool
    specs: list[ParameterSpec]
    # The panel's groups this family's specs fall into, in order.
    groups: list[str]
    # The program the family is archived with (storage_v1: PHA), or None for
    # a general one.
    program: str | None = None


class SimulationRequest(BaseModel):
    """POST /api/fermos/simulate."""

    family: str
    strain: str | None = None
    product: str | None = None
    sugar: str | None = None
    # A person's changes, each an Override of scope fermos:family:<family>.
    overrides: list[Override] = Field(default_factory=list)
    fitArtifact: str | None = None
    # `records`, `fit`, or `simulation:<artifact id>`.
    startFrom: str = "records"
    durationPreset: Literal["until-sugar-runs-out", "fit-length"] = "until-sugar-runs-out"
    includeArchived: bool = False
    # A parameter bound to exactly these records of the evidence pool, by
    # spec key (OF-BLD-020 §3.4, D13): each must be in the pool, carry a
    # field the parameter binds from, pass the aggregate gate and convert
    # into its unit, or the request is refused in words. Ids, never values.
    recordsByParam: dict[str, list[str]] = Field(default_factory=dict)


class FermosBinding(BaseModel):
    """GET /api/fermos/bind (OF-BLD-020 §3.2): a family's parameters bound
    for a strain, product and sugar from a fit, the records, a kept
    simulation and the conventions, starting no integration."""

    values: list[ParameterValue]
    # The keys a simulation would refuse for, each named with the field that
    # would bind it in its value's detail.
    waiting: list[str]
    # What the family would refuse these values for though nothing waits (a
    # start value below zero, a yield of zero, a run length of none), in the
    # words the run refuses with (OF-BLD-020 §8.R, findings 12 and 14);
    # None when a run would go ahead.
    refused: str | None = None
    # What bound from where: the program's papers, whose records, the sugar,
    # the fit and the kept simulation, and what they could not give.
    notes: list[str] = Field(default_factory=list)


class OxygenUptake(BaseModel):
    """OUR(t) = qO2·X on the time course's hours, and its peak read on the
    solver's own steps."""

    t: list[float]
    value: list[float]
    unit: str
    peak: float
    peakH: float | None = None
    # Why it is zero, when the culture is anaerobic.
    note: str | None = None


class MassBalance(BaseModel):
    # The larger relative error of the two checks (kinetics.mass_balance).
    closure: float
    ok: bool
    note: str


class SimulationCeilingRow(BaseModel):
    """Yp/s beside the newest stored geneOS ceiling of one host model on
    the sugar, read and never clamped."""

    modelId: str
    modelName: str
    match: Literal["strain", "species"]
    matchWords: str
    artifactId: str
    provenance: Provenance
    ceilingGPerG: float
    ypsGPerG: float | None = None
    yieldAchievedGPerG: float | None = None
    above: bool
    words: str


class SimulationCeiling(BaseModel):
    product: str
    sugar: str
    strain: str
    rows: list[SimulationCeilingRow] = Field(default_factory=list)
    flagged: bool = False
    # Why no row, in words: no host model, or no ceiling on file yet.
    empty: str | None = None
    # Where a ceiling is computed (geneOS → Model).
    computeAt: str


class SteadyState(BaseModel):
    """chemostat_v1's steady state and washout (D5 as built, 6)."""

    washout: bool
    dilutionRate: float
    # The general washout rate, μ(Sf, P = 0) − kd, and D5's expression.
    dWashout: float
    dWashoutD5: float
    X: float
    S: float
    P: float
    # D·P at the steady state, g L⁻¹ h⁻¹; None at washout.
    productivity: float | None = None
    words: str
    # OF-BLD-020 §3.R (finding 1): the most μ(S, P = 0) − kd reaches over S
    # from 0 to Sf, at or above which no culture holds; whether a culture
    # holds and washout is stable too (D ≥ dWashout), so a run reaches one or
    # the other by where it starts; and which one this run's path reached
    # by its end (None: still on its way to one).
    dWashoutMax: float | None = None
    bistable: bool = False
    reached: Literal["culture", "washout"] | None = None


class SimulationResult(BaseModel):
    """One kept `fermos.simulation` artifact as every reader reads it."""

    artifactId: str
    provenance: Provenance
    family: str
    title: str
    strain: str | None = None
    product: str | None = None
    sugar: str | None = None
    parameters: list[ParameterValue]
    start: list[ParameterValue]
    # {"t": hours, "<state>": values} in `units`.
    series: dict[str, list[float]]
    units: dict[str, str]
    our: OxygenUptake
    # The state where the integration ended, and its hour as "t".
    end: dict[str, float]
    sugarRunsOutH: float | None = None
    harvestH: float
    # The product (the store, for storage_v1) at harvest, g L⁻¹.
    finalTitre: float | None = None
    # Product made over sugar used to harvest, g g⁻¹.
    yieldAchieved: float | None = None
    # The final titre over the harvest hour, g L⁻¹ h⁻¹.
    productivity: float | None = None
    massBalance: MassBalance
    ceiling: SimulationCeiling | None = None
    flags: list[str] = Field(default_factory=list)
    aerobic: bool
    steadyState: SteadyState | None = None
    notes: list[str] = Field(default_factory=list)
    basis: ComputedBasis


class SimulationSummary(BaseModel):
    """GET /api/fermos/simulations: one kept simulation, newest first."""

    artifactId: str
    family: str
    title: str
    strain: str | None = None
    product: str | None = None
    sugar: str | None = None
    finalTitre: float | None = None
    harvestH: float | None = None
    createdAt: str
    provenance: Provenance


# ── pureOS's unit catalogue (OF-BLD-020 §5.1, D8) ──────────────────────
#
# Each entry is one unit type a train can hold: a BioSTEAM class, or one of
# the three in-house `bst.Unit` subclasses BioSTEAM lacks, with every
# parameter its constructor takes either declared as a ParameterSpec or named
# as not offered, with why. Its id is the vocabulary's (src/data/vocabulary.ts
# UNIT_OPERATIONS). pureos/catalogue.py holds the data; BioSTEAM's defaults
# are read in the Proforma worker and never typed.

# Where a unit sits in a train, fermenter to product.
UnitStage = Literal["harvest", "disruption", "clarification", "concentration", "capture", "polish", "formulation",
                    "drying", "utility"]


class UnitPort(BaseModel):
    """One inlet or outlet of a catalogue unit, in words."""

    side: Literal["in", "out"]
    index: int
    name: str
    what: str
    # An outlet the product goes on by, by default; a train may route another.
    onward: bool = False
    # An inlet's stream: from the unit before ("upstream"), one the train
    # supplies beside the line ("side": a solvent), or one the unit sizes
    # itself ("unit": a buffer, air, fuel). None for an outlet.
    source: Literal["upstream", "side", "unit"] | None = None
    # Takes any number of streams here, which the class mixes.
    many: bool = False


class NotOffered(BaseModel):
    """A parameter the class's constructor takes that the panel does not
    offer, and why, in words."""

    name: str
    why: str


class UnitNeed(BaseModel):
    """What a unit needs set before it runs: one of `alternatives`, each a
    list of keys that must all hold a value."""

    alternatives: list[list[str]]
    why: str


class UnitType(BaseModel):
    """A catalogue entry without its specs (GET /api/pureos/catalogue)."""

    id: str
    name: str
    # What it does, in words.
    line: str
    stage: UnitStage
    biosteamClass: str | None = None
    inhouseClass: str | None = None
    insOuts: list[UnitPort]
    # Whether BioSTEAM costs it; the in-house units have no cost model.
    costModel: bool
    notes: list[str] = Field(default_factory=list)
    notOffered: list[NotOffered] = Field(default_factory=list)
    needs: list[UnitNeed] = Field(default_factory=list)
    # The vocabulary ids it stands for beside its own (cell disruption:
    # homogenisation and bead milling; chromatography: one per mode).
    maps: list[str] = Field(default_factory=list)
    specCount: int


class UnitDefault(BaseModel):
    """A parameter's default as the class gives it, read from its code in
    the worker, and where it was read; None when the class gives none or
    decides at run time."""

    key: str
    value: float | str | None = None
    readFrom: str


class UnitParamMap(BaseModel):
    """How one spec reaches the class: under which of the class's own names,
    as a constructor argument or an attribute set after construction, and
    whether its key is a template expanded per component or per effect
    (`split` → `split.<chemical>`, `P` → `P.<effect>`)."""

    key: str
    name: str
    via: Literal["argument", "attribute"]
    per: Literal["component", "effect"] | None = None
    how: str | None = None


class UnitSpecs(BaseModel):
    """GET /api/pureos/catalogue/{id}/specs: an entry's ParameterSpecs with
    the choices and bounds the class gives, each parameter's default read
    from the class, and how each reaches it."""

    id: str
    biosteamClass: str | None = None
    inhouseClass: str | None = None
    specs: list[ParameterSpec]
    defaults: list[UnitDefault]
    params: list[UnitParamMap]
    notOffered: list[NotOffered]
    needs: list[UnitNeed]
    # The chemicals a chemical-valued parameter chooses from: the yeast
    # program's set, until a train names its own (§5.2).
    chemicals: list[str] = Field(default_factory=list)
    versions: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


# ── pureOS builds the train (OF-BLD-020 §5.2, D9, D10, E.2‴) ──────────
#
# A train is data: an inlet, then units in order, each a catalogue type with
# the values a person typed (Override-shaped, D3), the records named for a
# parameter, the routing of each outlet (onward, waste, or back to an earlier
# unit), and optionally a shelf flowsheet's own unit whose values it reads.
# pureos/train_spec.py validates it and resolves every parameter with its source;
# the Proforma worker builds and runs it; one `pureos.train_run` artifact
# keeps it, and pureos.train_of reads it as it reads a Proforma run.


class TrainParam(BaseModel):
    """A value a person typed for one parameter of a train's unit or inlet:
    an Override without its scope and key, which its place in the train
    names (D3, D9)."""

    model_config = ConfigDict(extra="forbid")

    value: float | str
    low: float | None = None
    high: float | None = None
    by: str
    at: str
    note: str | None = None

    @field_validator("value", "low", "high", mode="before")
    @classmethod
    def _no_true_or_false(cls, v: Any) -> Any:
        if isinstance(v, bool):
            raise ValueError("a typed value, low and high are numbers or words, never true or false")
        return v


class TrainInlet(BaseModel):
    """Where the broth a train takes comes from (D10): a kept fermOS
    simulation's harvest, a stream of a kept run, or a composition typed
    under a person's name."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["simulation", "run-stream", "typed"]
    # The artifact: a `fermos.simulation`, or a `proforma.run`,
    # `proforma.reference` or `pureos.train_run` whose stream is the inlet;
    # None for a typed inlet.
    ref: str | None = None
    # The stream of that run (run-stream alone).
    streamId: str | None = None
    # A `fermos.vessel` design of the simulation, whose working volume, vessels
    # and cycle time give the broth flow (simulation alone).
    vessel: str | None = None
    # The inlet's own values a person typed, by key (broth_flow,
    # harvest_hour, conc.<chemical>, T, P): scope `pureos:unit:<train>:inlet`.
    params: dict[str, TrainParam] = Field(default_factory=dict)


class TrainUnitReadFrom(BaseModel):
    """A shelf flowsheet's own unit whose values a train's unit takes, as
    the flowsheet's package builds it: read from the built unit in the
    worker, never typed."""

    model_config = ConfigDict(extra="forbid")

    flowsheet: str
    unit: str


class TrainUnitSpec(BaseModel):
    """One unit of a train, in order (D9)."""

    model_config = ConfigDict(extra="forbid")

    # The BioSTEAM unit id it is built under: a letter, then letters, digits
    # or underscores.
    id: str
    # A catalogue id (pureos/catalogue.py).
    type: str
    # What a person typed, by key: `split.<chemical>` and the other
    # per-component and per-effect keys expanded (catalogue.expand), and a
    # side inlet's `<port>.<chemical>` flows in kg/hr.
    params: dict[str, TrainParam] = Field(default_factory=dict)
    # Outlet name → `onward`, `waste` or `recycle:<an earlier unit's id>`;
    # an outlet not named takes the catalogue's default (its onward port on,
    # the rest to waste).
    outlets: dict[str, str] = Field(default_factory=dict)
    # Record ids named for a parameter, by key: they bind it, and no other
    # record does.
    records: dict[str, list[str]] = Field(default_factory=dict)
    readFrom: TrainUnitReadFrom | None = None


class TrainSpec(BaseModel):
    """A train as data (D9): the browser keeps it whole and sends it with a
    run; the service keeps the runs."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    program: str
    # A product id (thermo.CHEMICALS names the library's chemical it is).
    product: str
    inlet: TrainInlet
    units: list[TrainUnitSpec] = Field(default_factory=list)


class TrainValidation(BaseModel):
    """POST /api/pureos/train/validate: every refusal at once, in words;
    runs nothing."""

    ok: bool
    refusals: list[str] = Field(default_factory=list)


class TrainRunRequest(BaseModel):
    """POST /api/pureos/train/run."""

    model_config = ConfigDict(extra="forbid")

    train: TrainSpec
    # A person's changes in a unit's or the inlet's panel, each an Override
    # of `pureos:unit:<train id>:<unit id | inlet>`: laid over the values the
    # train carries, an override replacing the train's value of its key.
    overrides: list[Override] = Field(default_factory=list)
    # The person an override that names nobody is by.
    by: str | None = None
    includeArchived: bool = False


class StreamImpurity(BaseModel):
    chemical: str
    massFraction: float


class StreamPurity(BaseModel):
    """One stream of a train run: the product's share of its mass, and its
    largest other components by mass, read from the stream table."""

    stream: str
    massFlow: float
    # None for a stream that carries nothing.
    productFraction: float | None = None
    impurities: list[StreamImpurity] = Field(default_factory=list)


class TrainPurity(BaseModel):
    # The chemical traced (the library's name for the train's product).
    product: str
    productStream: str | None = None
    productFraction: float | None = None
    streams: list[StreamPurity] = Field(default_factory=list)
    # How many of each stream's largest other components are named (a
    # reading convention).
    impuritiesShown: int
    note: str


class TrainUnitCost(BaseModel):
    """One unit's cost as BioSTEAM gives it, or why there is none."""

    unit: str
    type: str
    unitClass: str
    # Whether the catalogue's class carries a cost model (the in-house
    # units do not).
    costModel: bool
    purchaseCost: float | None = None
    installedCost: float | None = None
    # BioSTEAM's purchase cost by item (Unit.purchase_costs), USD.
    items: dict[str, float] = Field(default_factory=dict)
    note: str | None = None


class TrainInletRead(BaseModel):
    """What a train run's inlet was and where it came from (D10)."""

    kind: Literal["simulation", "run-stream", "typed"]
    ref: str | None = None
    refTool: str | None = None
    streamId: str | None = None
    vessel: str | None = None
    chemicals: list[str] = Field(default_factory=list)
    # g L⁻¹ by chemical (a simulation's harvest, or typed), water aside.
    concentrations: dict[str, float] | None = None
    # kg/hr by chemical as the worker built the stream, water included.
    flows: dict[str, float] = Field(default_factory=dict)
    # The water the balance gave, kg/hr, and how.
    water: float | None = None
    waterNote: str | None = None
    # m³/hr.
    brothFlow: float | None = None
    harvestHour: float | None = None
    T: float
    P: float
    phase: str
    # What the simulation's family does not model, in words.
    absent: str | None = None
    notes: list[str] = Field(default_factory=list)


class TrainUnitParameters(BaseModel):
    """One unit's parameters as its run's basis holds them, each with its
    source."""

    unit: str
    type: str
    unitClass: str
    values: list[ParameterValue] = Field(default_factory=list)


class TrainRun(BaseModel):
    """POST /api/pureos/train/run: the one `pureos.train_run` artifact, read."""

    artifactId: str
    provenance: Provenance
    createdAt: str
    spec: TrainSpec
    train: Train
    purity: TrainPurity
    costs: list[TrainUnitCost] = Field(default_factory=list)
    inlet: TrainInletRead
    parameters: list[TrainUnitParameters] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    basis: ComputedBasis


# Claim and AnswerPlan name Passage and Evidence, which are defined further
# down; resolve the names now that every model exists.
Claim.model_rebuild()
# ProformaRunRequest names Override, which is defined further down (OF-BLD-020 §2.2).
ProformaRunRequest.model_rebuild()
# ParamResolveRequest names TrainSpec, defined further down (OF-BLD-020 §5.2).
ParamResolveRequest.model_rebuild()
AnswerPlan.model_rebuild()
ToolResult.model_rebuild()
