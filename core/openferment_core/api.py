"""FastAPI app — openferment-core's first surface (OF-BLD-007 §4).

The seam is Python rather than a Node proxy on purpose. An API key cannot live
in the browser, so a server is required either way; and every tool Postdoc will
eventually orchestrate — COBRApy, BioSTEAM, the sequence stack — is Python.
A throwaway JS proxy would mean building this boundary twice.

Run it from `core/`:

    uv run uvicorn openferment_core.api:app --reload

The browser never sees a key and never renders model prose. It renders a plan.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from . import biorepo, extract, intake, witness
from .corpus import load_corpus
from .models import (
    AnswerPlan,
    AskRequest,
    ExtractResponse,
    ExtractRun,
    FetchResult,
    IntakeStatus,
    Overlay,
    ReviewDecision,
    Usage,
)
from .postdoc import MODEL, PostdocUnavailable, ask_model
from .validate import decline_reason, validate_claims

# core/.env, which is gitignored. Loaded here rather than by the shell so that
# `uv run uvicorn ...` works with no ceremony; `override=False` means a real
# environment variable still wins, which is what CI would set.
load_dotenv(Path(__file__).parent.parent / ".env", override=False)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("openferment.api")

app = FastAPI(title="openferment-core", version="0.1.0")

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
        "model": MODEL,
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
        return AnswerPlan(question=question, declined=str(e), usage=Usage())

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
    """One forced tool call over the paper's cached full text (§6.1, §6.3).

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
    candidates = witness.overlay_candidates()
    try:
        runs = witness.runs()
    except FileNotFoundError as e:
        log.warning("overlay without runs — %s", e)
        runs = []
    return Overlay(
        papers=intake.overlay_papers(),
        records=biorepo.decisions(),
        candidates=candidates,
        runs=runs,
    )


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
