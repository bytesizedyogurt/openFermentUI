"""The Haiku call (OF-BLD-007 §6).

One retrieval, one call, no agent loop. Structured output comes from forced
tool use rather than from asking for JSON in prose: a single tool,
`emit_answer_plan`, with `tool_choice` pinned to it, so the model has exactly
one way to respond and the response is schema-checked by the API before it
reaches us.

WHAT THIS MODULE IS NOT ALLOWED TO DO. It does not decide whether a claim is
good — `validate.py` does, and it runs on everything that comes back. It does
not compute provenance. It does not repair. Its only job is to turn a question
plus evidence into raw claims, and to be honest about the cost.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

from .models import Usage

log = logging.getLogger("openferment.postdoc")

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2000

# Haiku 4.5, per million tokens. Stated here rather than inlined so the number
# a cost is computed from is the number somebody can check against the pricing
# page — a cost figure whose source is buried is a cost figure nobody audits.
USD_PER_MTOK_IN = 1.00
USD_PER_MTOK_OUT = 5.00

SYSTEM = """You are Postdoc, a research assistant for precision fermentation \
in the openFerment platform.

You may only make claims supported by the evidence records you are given. You \
have no other sources. If you know something from elsewhere and no record \
supports it, you may not claim it here.

NEVER WRITE A NUMBER IN CLAIM TEXT. Not in digits, not in words, not as \
"twofold" or "an order of magnitude". Name what was measured and under what \
conditions, and cite the record; the interface renders the value from that \
record beside your sentence. A claim containing a number is discarded whole — \
it is not corrected and it is not shown.

  good:  "Titre at harvest in cw15 under mixotrophic conditions"  cites r-A1-1
  bad:   "Titre reached 4.2 g/L in cw15"
  bad:   "Titre roughly doubled under mixotrophic conditions"

Strain and assay names that contain digits are fine — cw15, UVM4, OD600, CK2 \
are identifiers, not quantities.

Cite the record ids you actually used, exactly as given. A citation that does \
not resolve discards the claim.

If the evidence does not support an answer, decline and say what is missing. \
Prefer naming what is absent over speculating: "nobody has measured this in \
this host" is a useful answer and is often the true one. A claim that asserts \
an absence carries support "unsupported" and no record ids.

Put what you could not establish in `gaps` — the evidence a reader would need \
to go and find. Be specific about the missing measurement, not vague about \
uncertainty."""

# The schema is AnswerPlan minus `usage` (which the server computes from the
# response) and minus `provenance` on a claim (which the server computes from
# the cited records — see validate.py). Giving the model a provenance field
# would invite it to grade its own evidence.
TOOL = {
    "name": "emit_answer_plan",
    "description": (
        "Return the answer as a plan: a list of claims, each a sentence with no "
        "number in it plus the records it rests on. This is the only way to "
        "respond."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "description": "One entry per assertion. Empty if declining.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Short id, e.g. 'c1'."},
                        "text": {
                            "type": "string",
                            "description": (
                                "The claim, in prose, containing NO NUMBER in digits "
                                "or words. Name what was measured and under what "
                                "conditions."
                            ),
                        },
                        "recordIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Record ids from the evidence, exactly as given.",
                        },
                        "paperIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Paper ids from the evidence, exactly as given.",
                        },
                        "support": {
                            "type": "string",
                            "enum": ["direct", "inferred", "unsupported"],
                            "description": (
                                "'direct' — a cited record states this. 'inferred' — "
                                "it follows from cited records. 'unsupported' — an "
                                "absence claim with no record behind it."
                            ),
                        },
                    },
                    "required": ["id", "text", "recordIds", "support"],
                },
            },
            "gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Evidence a reader would need that the corpus does not have.",
            },
            "declined": {
                "type": ["string", "null"],
                "description": (
                    "Set only when the corpus cannot support an answer at all. Say "
                    "what is missing. Null otherwise."
                ),
            },
        },
        "required": ["claims", "gaps", "declined"],
    },
}


class PostdocUnavailable(RuntimeError):
    """No key, or the API could not be reached. Distinct from a bad answer."""


def cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Cost from the response's own token counts, never an estimate."""
    return round(
        input_tokens / 1_000_000 * USD_PER_MTOK_IN
        + output_tokens / 1_000_000 * USD_PER_MTOK_OUT,
        6,
    )


def _evidence_payload(records: list[dict[str, Any]], corpus) -> list[dict[str, Any]]:
    """Records as structured JSON, not prose (§6).

    Trimmed to what a claim needs. The BM25 score and matched terms are dropped:
    they are retrieval diagnostics, and handing the model its own ranking invites
    it to treat rank as relevance.
    """
    payload = []
    for r in records:
        paper = corpus.paper(r["paperId"]) or {}
        payload.append(
            {
                "recordId": r["id"],
                "paperId": r["paperId"],
                "paperTitle": paper.get("title"),
                "year": paper.get("year"),
                # Whether the section text is the paper's own or a curator's
                # note. A claim built on a curation note is not built on the
                # source, and the model is told which it has.
                "textSource": paper.get("textSource"),
                "measurement": r.get("fieldLabel"),
                "value": r.get("value"),
                "unit": r.get("unit"),
                "quote": r.get("quote"),
                "strain": r.get("strainId"),
                "conditions": r.get("conditions"),
                "provenance": r.get("provenance"),
                # False means this paper is quoting somebody else's measurement.
                # Told so the model does not present a citation-of-a-citation as
                # corroboration.
                "isFirstHand": r.get("primary", True),
                "quotesRecord": r.get("citesRecordId"),
            }
        )
    return payload


def ask_model(question: str, records: list[dict[str, Any]], corpus) -> tuple[dict[str, Any], Usage]:
    """One question, one call. Returns the model's raw plan and what it cost.

    The plan is RAW — unvalidated, provenance not yet computed. Everything that
    comes back goes through validate.py before anybody sees it.
    """
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise PostdocUnavailable(
            "ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and "
            "restart the service."
        )

    client = anthropic.Anthropic(api_key=key)
    evidence = _evidence_payload(records, corpus)

    user_turn = (
        f"Question: {question}\n\n"
        f"Evidence records ({len(evidence)}):\n"
        f"{json.dumps(evidence, indent=None, ensure_ascii=False)}"
    )
    if not evidence:
        user_turn = (
            f"Question: {question}\n\n"
            "Evidence records: none. Retrieval found nothing in the corpus that "
            "bears on this question. Decline, and say what would need to be in "
            "the corpus to answer it."
        )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": user_turn}],
            tools=[TOOL],
            # Forced, not suggested. The model has exactly one way to respond,
            # and the API validates the shape before we see it — far more
            # reliable than asking for JSON in prose and parsing what comes back.
            tool_choice={"type": "tool", "name": "emit_answer_plan"},
        )
    except anthropic.APIConnectionError as e:
        raise PostdocUnavailable(f"Could not reach the Anthropic API: {e}") from e
    except anthropic.AuthenticationError as e:
        raise PostdocUnavailable(
            "The Anthropic API rejected the key in core/.env."
        ) from e
    except anthropic.RateLimitError as e:
        raise PostdocUnavailable(
            "Rate limited by the Anthropic API. Wait and try again."
        ) from e
    except anthropic.APIStatusError as e:
        raise PostdocUnavailable(f"Anthropic API error {e.status_code}: {e.message}") from e

    usage = Usage(
        inputTokens=response.usage.input_tokens,
        outputTokens=response.usage.output_tokens,
        costUsd=cost_usd(response.usage.input_tokens, response.usage.output_tokens),
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "emit_answer_plan":
            # Tool inputs are parsed, never string-matched — escaping varies.
            raw = block.input if isinstance(block.input, dict) else json.loads(block.input)
            return raw, usage

    # Forced tool choice makes this close to unreachable, but "close to" is not
    # "never", and a silently empty plan would render as a blank answer.
    log.warning("no tool_use block in response; stop_reason=%s", response.stop_reason)
    return (
        {
            "claims": [],
            "gaps": [],
            "declined": (
                "Postdoc did not return an answer in the expected form. Nothing is "
                "shown rather than guessing at what it meant."
            ),
        },
        usage,
    )
