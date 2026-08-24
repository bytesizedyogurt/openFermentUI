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

from typing import Literal

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
