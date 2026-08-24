"""Rule 1 enforcement (OF-BLD-007 §5).

THE PART THAT MATTERS. Claim text may not contain a number. The model writes
prose and cites a record; the interface renders the value from that record.
This is the strongest available implementation of Rule 1, because the model is
not being asked to be careful with quantities — it has no slot to put one in.

    model emits   "Titre in cw15 under mixotrophic conditions"  + ["r-A1-1"]
    UI renders    Titre in cw15 under mixotrophic conditions — 4.2 g/L (verified)

A claim is rejected when any of these hold:

    1. the text contains a number, in digits or in words
    2. a cited record id does not resolve against the corpus
    3. a cited paper id does not resolve
    4. there are no record ids and the claim does not admit to being unsupported

REJECTED CLAIMS ARE DROPPED AND COUNTED, NEVER REPAIRED. Stripping the number
out of a bad claim would produce a sentence the model never wrote, attached to
citations chosen to support the sentence it did write. A validator that patches
model output is a validator that hides model failure, and the rejection count
is the only signal that a prompt has drifted — a rate that climbs is the alarm.

Built and tested against hand-written good and bad plans before the first API
call, so it is trusted before any model output reaches it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import Claim, weakest_provenance

# Digits in any form a model might reach for: 4, 4.2, 4,200, 1e6, ½, ٤ (Arabic
# -Indic), Ⅳ (Roman numeral forms), ² (superscript). `\d` in Python is already
# Unicode-aware, which covers most non-ASCII digit sets on its own.
_DIGIT = re.compile(r"[\d¼-¾⅐-↏⁰-₟]")

# Written numerals, and the words that turn them into quantities. Bounded with
# explicit boundaries rather than \b so that "oneself", "tension" and "often"
# do not trip it — a validator with false positives gets switched off, which is
# the one failure mode worse than a missed number.
_WORD_NUMBERS = (
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty "
    "thirty forty fifty sixty seventy eighty ninety hundred thousand million "
    "billion trillion half quarter third dozen "
    "first second third fourth fifth sixth seventh eighth ninth tenth "
    "once twice thrice"
).split()
_WORD_NUMBER = re.compile(
    r"(?<![a-z])(" + "|".join(_WORD_NUMBERS) + r")(?![a-z])", re.IGNORECASE
)

# Ranges and comparisons written without digits are quantities too: "roughly
# an order of magnitude higher" is a number wearing a coat.
_MAGNITUDE = re.compile(
    r"(?<![a-z])(an?\s+order\s+of\s+magnitude|orders\s+of\s+magnitude|"
    r"[a-z]+-?fold)(?![a-z])",
    re.IGNORECASE,
)


# Identifiers carry digits and are not quantities. Strain designations (cw15,
# UVM4, Elow47, CC-4350), assay names (OD600), proteins (CK2) and corpus ids
# (A1, H4, r-A1-1) all contain digits, and a claim that cannot name the strain
# it is about is useless — "Titre in cw15 under mixotrophic conditions" is the
# specification's own worked example of a GOOD claim.
#
# The distinguishing feature is position: an identifier's digits are attached to
# letters, letters first. A quantity's digits stand alone or lead — "4.2 g/L",
# "0.2%", "12-fold", "1e6". So identifier-shaped spans are blanked before the
# digit search, and everything else still trips it.
#
# This is deliberately narrow. "titre4200" would slip through, and that is an
# accepted cost: it is not a sentence a model writes, and widening the carve-out
# to catch it would start admitting real quantities.
_IDENTIFIER = re.compile(r"(?<![0-9.])[A-Za-z][A-Za-z]*(?:[-\u2013][A-Za-z]*)*\d[A-Za-z0-9-]*")


def find_number(text: str) -> str | None:
    """The first number-like thing in the text, or None.

    Returns what it found rather than a bool, so a rejection can say what
    tripped it. "Rejected: contains a number" is unactionable when the prompt
    needs tightening; "Rejected: contains 'twofold'" is a prompt edit.
    """
    # Blank rather than delete, so the remaining spans keep their boundaries and
    # a word-numeral straddling an identifier cannot be created by the removal.
    masked = _IDENTIFIER.sub(lambda m: " " * len(m.group(0)), text)
    if m := _DIGIT.search(masked):
        return m.group(0)
    if m := _WORD_NUMBER.search(masked):
        return m.group(0)
    if m := _MAGNITUDE.search(masked):
        return m.group(0)
    return None


@dataclass
class ValidationResult:
    claims: list[Claim] = field(default_factory=list)
    rejected: int = 0
    reasons: list[str] = field(default_factory=list)


def validate_claims(
    raw_claims: list[dict[str, Any]],
    records_by_id: dict[str, Any],
    papers_by_id: dict[str, Any],
) -> ValidationResult:
    """Filter model claims down to the ones that can be trusted and rendered.

    Provenance is COMPUTED here, from the cited records, and whatever the model
    put in that field is discarded. A model grading its own evidence grades it
    generously; and the weakest-citation rule means a claim resting on one gold
    record and one industry estimate is an industry estimate.
    """
    out = ValidationResult()

    for index, raw in enumerate(raw_claims):
        claim_id = str(raw.get("id") or f"c{index + 1}")
        text = str(raw.get("text") or "").strip()
        record_ids = [str(r) for r in (raw.get("recordIds") or [])]
        paper_ids = [str(p) for p in (raw.get("paperIds") or [])]
        support = raw.get("support") or "direct"
        if support not in ("direct", "inferred", "unsupported"):
            support = "direct"

        def reject(why: str) -> None:
            out.rejected += 1
            out.reasons.append(f"{claim_id}: {why}")

        if not text:
            reject("empty claim text")
            continue

        # 1. Rule 1 itself.
        if found := find_number(text):
            reject(f"claim text contains a number ({found!r}) — values come from the record")
            continue

        # 2 & 3. Citations must resolve. A claim citing a record that does not
        # exist is not a slightly-wrong claim; it is a claim with nothing under
        # it, and the UI has no value to render beside it.
        ghost_records = [r for r in record_ids if r not in records_by_id]
        if ghost_records:
            reject(f"cites records that do not exist: {', '.join(ghost_records)}")
            continue

        ghost_papers = [p for p in paper_ids if p not in papers_by_id]
        if ghost_papers:
            reject(f"cites papers that do not exist: {', '.join(ghost_papers)}")
            continue

        # 4. No citation and no admission. 'unsupported' is a legitimate claim
        # — "nobody has measured this in this host" is a useful answer — but it
        # has to be declared, not arrived at by omission.
        if not record_ids and support != "unsupported":
            reject(f"no recordIds and support is '{support}', not 'unsupported'")
            continue

        # Papers are derived from the cited records rather than trusted from the
        # model, so a claim can never point at a paper its evidence does not
        # come from. Anything the model additionally named and that resolves is
        # kept, in case it cited a paper with no extracted record.
        derived = {records_by_id[r]["paperId"] for r in record_ids}
        papers = sorted(derived | set(paper_ids))

        out.claims.append(
            Claim(
                id=claim_id,
                text=text,
                recordIds=record_ids,
                paperIds=papers,
                support=support,
                provenance=weakest_provenance(
                    [records_by_id[r]["provenance"] for r in record_ids]
                ),
            )
        )

    return out


def decline_reason(result: ValidationResult, model_declined: str | None) -> str | None:
    """What to put in `declined`, if anything.

    The model's own decline wins when it gave one: it knows what it was missing
    and can say so specifically. Otherwise, if every claim was rejected, the
    plan declines rather than returning empty — a plan with no claims and no
    explanation renders as a blank screen, which reads as "no answer" when the
    truth is "the answer was thrown away for failing validation".
    """
    if model_declined:
        return model_declined
    if result.claims:
        return None
    if result.rejected:
        return (
            f"Postdoc produced {result.rejected} "
            f"claim{'s' if result.rejected != 1 else ''}, none of which passed "
            "validation, so none of them are shown. This is a fault in the "
            "answer, not in the corpus — the evidence may well be there."
        )
    return (
        "The corpus does not contain evidence that bears on this question, so "
        "there is nothing to answer from."
    )
