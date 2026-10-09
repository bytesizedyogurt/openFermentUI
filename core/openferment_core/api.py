"""FastAPI app — openferment-core's first surface (OF-BLD-007 §4).

The seam is Python rather than a Node proxy on purpose. An API key cannot live
in the browser, so a server is required either way; and every tool Postdoc will
eventually orchestrate — COBRApy, BioSTEAM, the sequence stack — is Python.
A throwaway JS proxy would mean building this boundary twice.

Run it from `core/`:

    uv run uvicorn openferment_core.api:app --reload

After a `pnpm build` the same process serves the app itself at / (§B.4 at the
bottom of this file), so http://127.0.0.1:8000 is the whole of openFerment.

The browser never sees a key and never renders model prose. It renders a plan.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import biorepo, extract, guard, guild, intake, practice, witness
from .corpus import load_corpus
from .models import (
    AnswerPlan,
    AskRequest,
    DecisionCheck,
    ExtractResponse,
    ExtractRun,
    FetchResult,
    Guild,
    GuildEvidence,
    GuildPerson,
    GuildWithdrawal,
    IntakeStatus,
    Overlay,
    Practice,
    PracticeDraftRequest,
    PracticeScenario,
    PracticeSession,
    PracticeTurnRequest,
    ReviewDecision,
    Usage,
)
from . import llm
from .postdoc import PostdocUnavailable, ask_model
from .validate import decline_reason, validate_claims

# core/.env, which is gitignored. Loaded here rather than by the shell so that
# `uv run uvicorn ...` works with no ceremony; `override=False` means a real
# environment variable still wins, which is what CI would set.
load_dotenv(Path(__file__).parent.parent / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("openferment.api")

app = FastAPI(title="openferment-core", version="0.1.0")


@app.middleware("http")
async def refuse_changes_from_elsewhere(request: Request, call_next):
    """A changing request from another site, or under a hostile name, stops
    here with a 403 that says why (guard.py, OF-BLD-012 §B.6)."""
    why = guard.refusal(request.method, request.headers)
    if why is not None:
        log.warning("refused %s %s: %s", request.method, request.url.path, why)
        return JSONResponse(status_code=403, content={"detail": why})
    return await call_next(request)

# §6 caps evidence at 30 records. The cap is the contract with the token budget.
MAX_EVIDENCE = 30


@app.get("/api/health")
def health() -> dict:
    """Liveness, and what the service can actually do right now.

    `hasKey` lets the UI tell "the service is down" from "the service is up but
    has no key" — two different problems with two different fixes, and a single
    "unavailable" would send somebody to restart a process that is running fine.
    """
    try:
        corpus = load_corpus()
        records = len(corpus.records)
        corpus_error = None
    except FileNotFoundError as e:
        records = 0
        corpus_error = str(e)
    return {
        "ok": corpus_error is None,
        "service": "openferment-core",
        "model": llm.primary(),
        # The model a call falls back to when the primary declines or is
        # unavailable (llm.py).
        "fallbackModel": llm.fallback(),
        "hasKey": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "records": records,
        "corpusError": corpus_error,
    }


@app.post("/api/ask", response_model=AnswerPlan)
def ask(request: AskRequest) -> AnswerPlan:
    """One question in, one AnswerPlan out. One retrieval, one call, no loop.

    Every failure below returns a plan with `declined` set rather than an HTTP
    error, because a declined plan is a thing the UI already knows how to
    render honestly and a 500 is a thing it can only apologise for. The one
    exception is the service being unreachable, which the browser detects
    itself — there is no response to put a reason in.
    """
    question = request.question.strip()
    if not question:
        return AnswerPlan(question="", declined="Ask a question and Postdoc will answer it.")

    try:
        corpus = load_corpus()
    except FileNotFoundError as e:
        log.error("corpus missing: %s", e)
        return AnswerPlan(
            question=question,
            declined=(
                "The corpus has not been generated. Run `pnpm export:corpus` from "
                "the repository root and restart the service."
            ),
        )

    limit = max(1, min(request.maxEvidence, MAX_EVIDENCE))
    records = corpus.search(question, limit=limit)
    log.info(
        "ask: %r → %d records%s",
        question[:80],
        len(records),
        f" (top: {records[0]['id']} on {records[0]['matchedTerms']})" if records else "",
    )

    try:
        raw, usage = ask_model(question, records, corpus)
    except PostdocUnavailable as e:
        log.error("postdoc unavailable: %s", e)
        return AnswerPlan(question=question, declined=str(e), usage=e.usage)

    result = validate_claims(
        raw.get("claims") or [],
        corpus.records_by_id,
        corpus.papers_by_id,
    )

    # §5 — log the rejection rate. A rate that climbs is the signal that the
    # prompt has drifted, and it is the only signal there is.
    if result.rejected:
        log.warning(
            "validator dropped %d/%d claims: %s",
            result.rejected,
            result.rejected + len(result.claims),
            "; ".join(result.reasons),
        )

    gaps = [str(g) for g in (raw.get("gaps") or []) if str(g).strip()]

    return AnswerPlan(
        question=question,
        claims=result.claims,
        gaps=gaps,
        declined=decline_reason(result, raw.get("declined")),
        usage=usage,
        rejected=result.rejected,
        rejectionReasons=result.reasons,
    )


# ── Intake (OF-BLD-012 §5.2) ────────────────────────────────────────────


@app.post("/api/intake/{paper_id}/fetch", response_model=FetchResult)
def intake_fetch(paper_id: str, force: bool = False) -> FetchResult:
    """Fetch one paper's full text from Europe PMC, split it, cache it.

    A fetch that fails returns HTTP 200 with `status: failed:fetch` or
    `failed:parse` and a reason — the ingest board renders both, and a 5xx
    would render as nothing. The only errors here are a paper the corpus has
    never heard of, and a corpus that has not been generated.
    """
    try:
        corpus = load_corpus()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    paper = corpus.paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"{paper_id} is not in the corpus")
    result = intake.fetch_paper(paper, force=force)
    log.info("intake: %s → %s%s", paper_id, result.status, f" ({result.reason})" if result.reason else "")
    return result


@app.get("/api/intake/status")
def intake_status() -> dict[str, IntakeStatus]:
    """Every paper with a cached fetch, success or failure, summarised."""
    return intake.all_statuses()


@app.post("/api/intake/{paper_id}/extract", response_model=ExtractResponse)
def intake_extract(paper_id: str, force: bool = False) -> ExtractResponse:
    """One structured model response over the paper's cached full text (§6.1, §6.3).

    422 when the paper has no cached full text — there is nothing to anchor
    to, and an extraction over a curation note would be an extraction over
    the curator. 503 when there is no key or the API cannot be reached; the
    detail says which.
    """
    try:
        corpus = load_corpus()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    if corpus.paper(paper_id) is None:
        raise HTTPException(status_code=404, detail=f"{paper_id} is not in the corpus")
    fetched = intake.cached(paper_id)
    if fetched is None or fetched.status != "complete":
        raise HTTPException(
            status_code=422,
            detail=f"{paper_id} has no cached full text. POST /api/intake/{paper_id}/fetch first.",
        )
    try:
        result = extract.extract_paper(paper_id, force=force)
    except extract.ExtractTruncated as e:
        # Not cached, so the next attempt is a real one; 502 because the
        # upstream answered and the answer was unusable.
        raise HTTPException(status_code=502, detail=str(e)) from e
    except extract.ExtractUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    log.info(
        "extract: %s → %d anchored, %d rejected, $%.4f",
        paper_id, len(result.candidates), result.rejected, result.usage.costUsd,
    )
    return result


# ── the overlay (OF-BLD-012 §2.1) ───────────────────────────────────────


@app.get("/api/biorepo/overlay", response_model=Overlay)
def biorepo_overlay() -> Overlay:
    """What the service knows that the seed does not.

    Papers from fulltext/ (§5); the run and the new candidates recomputed
    from candidates/ against the seed (§6.2); the reviewers' decisions from
    biorepo.json (§7.2). The store applies whatever is here in one action at
    load, and nothing here changes a record's status — that path goes
    through `biorepo.write` alone. A missing corpus.json costs the run, not
    the overlay.
    """
    runs, candidates, decisions = witness.overlay_bundle()
    # Always the FULL lists, never None (OF-BLD-012.1 F3): an empty list here
    # means the extractor has produced nothing, and the store drops what it
    # was holding. None is reserved for a caller that supplies neither, and
    # nothing in this service is such a caller.
    return Overlay(papers=intake.overlay_papers(), records=decisions, candidates=candidates, runs=runs)


@app.post("/api/biorepo/decisions", response_model=ReviewDecision)
def biorepo_decisions(decision: ReviewDecision) -> ReviewDecision:
    """The one way a decision reaches biorepo.json (§2.3, §7.2): through
    `biorepo.write`, which stores it or refuses it with the rule that failed.
    422 carries the rule and the reason; nothing is repaired on the way."""
    try:
        return biorepo.write(decision)
    except biorepo.WriteRefused as e:
        log.warning("biorepo refused %s — %s", decision.recordId, e)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/biorepo/check", response_model=DecisionCheck)
def biorepo_check(decision: ReviewDecision) -> DecisionCheck:
    """Would `biorepo.write` keep this decision? (OF-BLD-012.1 F1.5)

    Every rule of §2.3 runs; nothing is written. A refusal is an ANSWER, not
    an error, so it comes back 200 with the rule and the reason — the browser
    is asking a question, and a 422 here would read as a failed decision in
    the console of a reviewer who has not decided anything yet.
    """
    try:
        biorepo.write(decision, dry_run=True)
        return DecisionCheck(ok=True)
    except biorepo.WriteRefused as e:
        return DecisionCheck(ok=False, rule=e.rule, why=e.why)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# ── Guild (OF-BLD-013 §1.2) ──────────────────────────────────────────────
#
# The competence ledger. Reads are open like every read here; each write goes
# through one function in guild.py, which stores it or refuses it with the
# rule that failed. 422 carries the rule and the reason, the same shape
# /api/biorepo/decisions uses, and /api/guild/check answers 200 either way.


def _refused(e: guild.GuildRefused, what: str) -> HTTPException:
    log.warning("guild refused %s — %s", what, e)
    return HTTPException(status_code=422, detail=str(e))


@app.get("/api/guild", response_model=Guild)
def guild_ledger() -> Guild:
    """The whole ledger: people and every entry, withdrawn ones included.
    The browser applies it at load the way it applies the overlay, and
    computes every level from it."""
    return guild.read()


@app.post("/api/guild/people", response_model=GuildPerson)
def guild_people(person: GuildPerson) -> GuildPerson:
    try:
        return guild.write_person(person)
    except guild.GuildRefused as e:
        raise _refused(e, person.id) from e


@app.post("/api/guild/evidence", response_model=GuildEvidence)
def guild_evidence(entry: GuildEvidence) -> GuildEvidence:
    try:
        return guild.write_evidence(entry)
    except guild.GuildRefused as e:
        raise _refused(e, entry.id) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/guild/check", response_model=DecisionCheck)
def guild_check(entry: GuildEvidence) -> DecisionCheck:
    """Would `guild.write_evidence` keep this entry? Every rule runs and
    nothing is written. A refusal is an answer, so it comes back 200."""
    try:
        guild.write_evidence(entry, dry_run=True)
        return DecisionCheck(ok=True)
    except guild.GuildRefused as e:
        return DecisionCheck(ok=False, rule=e.rule, why=e.why)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/guild/withdraw", response_model=GuildEvidence)
def guild_withdraw(request: GuildWithdrawal) -> GuildEvidence:
    try:
        return guild.withdraw(request)
    except guild.GuildRefused as e:
        raise _refused(e, request.evidenceId) from e


# ── Practice (OF-BLD-013 §4) ────────────────────────────────────────────
#
# Scenarios drafted by the model and checked by practice.py, which copies
# every value from the source a draft cites and refuses a draft that states a
# number of its own. 422 carries the rule and the reason, as Guild's do; 503
# means no key, no network, or every model declined.


@app.get("/api/practice", response_model=Practice)
def practice_read() -> Practice:
    return practice.read()


@app.post("/api/practice/draft", response_model=PracticeScenario)
def practice_draft(request: PracticeDraftRequest) -> PracticeScenario:
    try:
        return practice.draft(request)
    except practice.PracticeRefused as e:
        log.warning("practice refused a draft for %s — %s ($%.4f spent)", request.skillId, e, e.usage.costUsd)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except practice.PracticeUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/practice/turn", response_model=PracticeSession)
def practice_turn(request: PracticeTurnRequest) -> PracticeSession:
    """The trainee's answer and the tutor's reply, kept together or not at all.
    The session that closes for a person on the ledger puts practice on it."""
    try:
        return practice.turn(request)
    except practice.PracticeRefused as e:
        log.warning("practice refused a turn on %s — %s ($%.4f spent)", request.scenarioId, e, e.usage.costUsd)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except practice.PracticeUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# ── Witness (OF-BLD-012 §6.3) ────────────────────────────────────────────


@app.get("/api/witness/runs", response_model=list[ExtractRun])
def witness_runs() -> list[ExtractRun]:
    """RunOutput[] recomputed from every candidates/*.json against the seed.
    Empty until something has been extracted. 503 when the corpus has not
    been generated, because there is nothing to score against."""
    try:
        return witness.runs()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# ── The built app (OF-BLD-012 §B.4) ──────────────────────────────────────

# One process, one port. When `pnpm build` has produced dist/, the service
# serves it at / beside /api, so the whole app is one address: the browser's
# relative /api calls land on this same process, and the Mac Mini daemon
# (scripts/host/) runs nothing else. With no dist/ (a fresh clone, the test
# suite, `pnpm dev` before a first build) nothing is mounted and the service
# answers /api alone, exactly as before.
#
# Mounted LAST, and that is load-bearing: Starlette tries routes in order and
# a mount at "/" matches every path, so each /api route above answers first.
# StaticFiles resolves every request and refuses one that leaves the
# directory, the same confinement scripts/lib/serve-dist.mjs gives the test
# servers (OF-BLD-012.1 §6.9). OPENFERMENT_DIST_DIR overrides the location; a
# relative value is taken from the repository root, like the data overrides.
DIST_DIR = intake._env_path("OPENFERMENT_DIST_DIR", Path(__file__).parent.parent.parent / "dist")


IMMUTABLE = "public, max-age=31536000, immutable"


class AppFiles(StaticFiles):
    """dist/, with caching that survives a deploy. A build names its scripts
    and styles by content hash under assets/ and deletes the old ones, so a
    browser holding last week's index.html would ask for files that are gone
    and show a blank page. The page and anything else outside assets/ is
    revalidated on every load; what is under assets/ never changes under its
    name and is kept for a year."""

    async def get_response(self, path: str, scope):  # type: ignore[override]
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            response.headers["Cache-Control"] = IMMUTABLE if path.startswith("assets/") else "no-cache"
        return response


def mount_app(target: FastAPI, dist: Path) -> bool:
    """Serve `dist` at / on `target` when it holds a build. True if mounted."""
    if not (dist / "index.html").is_file():
        return False
    target.mount("/", AppFiles(directory=dist, html=True), name="app")
    return True


if mount_app(app, DIST_DIR):
    log.info("serving the built app from %s at /", DIST_DIR)
