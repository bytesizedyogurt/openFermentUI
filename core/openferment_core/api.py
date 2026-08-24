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
from fastapi import FastAPI

from .corpus import load_corpus
from .models import AnswerPlan, AskRequest, Usage
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
