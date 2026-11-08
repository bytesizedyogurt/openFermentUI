"""The plan Postdoc answers in: its system prompt, its schema
and the shape evidence takes in a tool's result.

The bounded loop in `postdoc_agent.py` builds on this prompt and adds its
tools. The answer comes back as JSON that matches the `emit_answer_plan`
schema, through structured outputs (llm.py): the model has exactly one way to
respond and the API checks the shape before it reaches us. The routing table
(`llm.ROUTES`) names the models; llm.py says which answered and what it cost.

WHAT THIS MODULE IS NOT ALLOWED TO DO. It does not decide whether a claim is
good — `validate.py` does, and it runs on everything that comes back. It does
not compute provenance. It does not repair.
"""
from __future__ import annotations

from typing import Any


# A plan is a handful of claims, but these models think before they answer and
# the thinking counts against a turn's limit. Room for both: every turn has
# MIN_TOKENS, which the loop always holds back for the answer, and as many
# more, up to MAX_TOKENS, as the question's budget has left to pay for
# (postdoc_agent._turn_tokens). Alpha 2.1 raised the ceiling from 8,000: asked
# on Opus at effort high which of a project's 22 documents report an ethanol
# titre, the answer ran out of room after 17 tool calls
# (docs/reports/live-questions-2026-11.md). A turn pays for what it writes.
MIN_TOKENS = 8000
MAX_TOKENS = 32000
# The ceiling by the plan route's effort, where the effort thinks past
# MAX_TOKENS. Alpha 2.2 F.2g: asked on Opus at effort max, each of four
# questions spent its 24 tool calls and the answer then ran out of room at
# 32,000 tokens, its thinking spending the turn (ADR-008, Implementation 16).
# At max a turn may write 128,000 tokens, the output ceiling of every model
# the routes name (Opus 5.5, Sonnet 5.5 and Haiku 5.5, a streamed call);
# the question's budget still bounds each turn (postdoc_agent._turn_tokens).
ROOM = {"xhigh": 64_000, "max": 128_000}


def ceiling(effort: str) -> int:
    """The most a plan turn may write at `effort`, its thinking included:
    MAX_TOKENS at high and below, ROOM's tokens above."""
    return ROOM.get(effort, MAX_TOKENS)

SYSTEM = """You are Postdoc, a research assistant for fermentation and \
bioprocess research in the openFerment platform.

You may only make claims supported by evidence your tools return. You have no \
other sources. If you know something from elsewhere and no tool returned it, \
you may not claim it here.

NEVER WRITE A NUMBER IN CLAIM TEXT. Not in digits, not in words, not as \
"twofold" or "an order of magnitude". Name what was measured and under what \
conditions, and cite the record; the interface renders the value from that \
record beside your sentence. A claim containing a number is discarded whole — \
it is not corrected and it is not shown.

  good:  "Ethanol yield on glucose in cenpk113-7d under anaerobic batch conditions"  cites its record
  bad:   "Ethanol titre reached 4.2 g/L in cenpk113-7d"
  bad:   "Ethanol titre roughly doubled under anaerobic conditions"

Strain, model and assay names that contain digits are fine — cenpk113-7d, \
CEN.PK113-7D, S288C, iMM904, Yeast9, OD600 are identifiers, not quantities.

Ordinals, fractions and labels are numbers too: not "the first paper" or \
"the second strain", not "a third", "a quarter" or "half", not "Table 1" or \
"Figure 2", not a count such as "three documents". Name a document by its \
title or its subject; the passage a claim cites says where in the document it \
stands, and a change a run made is stated as a typed value.

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


def evidence_payload(records: list[dict[str, Any]], papers) -> list[dict[str, Any]]:
    """Records as structured JSON, not prose (§6).

    Trimmed to what a claim needs. The BM25 score and matched terms are dropped:
    they are retrieval diagnostics, and handing the model its own ranking invites
    it to treat rank as relevance.
    """
    payload = []
    for r in records:
        paper = papers.paper(r["paperId"]) or {}
        payload.append(
            {
                "recordId": r["id"],
                "paperId": r["paperId"],
                "paperTitle": paper.get("title"),
                "year": paper.get("year"),
                # Whether the section text is the document's own: every
                # document the project holds is full text (intake.py), and the
                # model is told which it has.
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
