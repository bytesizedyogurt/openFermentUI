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

from .models import Candidate, Claim, Quantity, weakest_provenance
from .units import UnitError, field as ontology_field, in_range, normalize as normalize_unit, to_canonical, to_si

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


# ── Anchoring — the mirror of Rule 1 (OF-BLD-012 §2.4) ───────────────────
#
# Rule 1 says the model originates no quantity. Its mirror for extraction: A
# QUANTITY ENTERS BIOREPO ONLY WHEN IT IS STANDING INSIDE A SENTENCE THE PAPER
# ACTUALLY WROTE. A candidate names a section, a verbatim quote, and a value;
# it is accepted only when the quote is in that section, the value is in that
# quote, the unit is one the field is denominated in, the converted value is
# inside the field's range, and a field that needs a method has one.
#
# Six rules, each with a code, so the rejection counts say WHICH rule is
# tripping. A rising rejection rate is the only signal that the extraction
# prompt has drifted, and "rejected: 40" is not a signal anybody can act on;
# "rejected: 40, all `quote`" is a prompt edit.
#
# REJECTED CANDIDATES ARE DROPPED AND COUNTED, NEVER REPAIRED. Trimming a quote
# until it matches, or rounding a value until it agrees, would produce an
# extraction the model never made from a sentence the paper may not contain.

# The normalisation both sides of a comparison go through before the quote is
# looked for in the section. Quotes arrive with a dozen dashes, superscript
# digits, soft hyphens from PDF-derived text and runs of whitespace; none of
# those is a difference in what the paper said.
# U+207B, superscript minus, is folded with the superscript digits it sits in
# front of: 'L⁻¹' has to become 'L-1', the spelling the JATS split writes.
_DASHES = dict.fromkeys(map(ord, "\u2212\u2010\u2011\u2012\u2013\u2014\u2015\u207b"), "-")
_SUPERSCRIPTS = str.maketrans("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079", "0123456789")
_SOFT_HYPHEN = "\u00ad"
_SPACES = re.compile(r"\s+")

MAX_QUOTE_CHARS = 300
# §2.4 rule 3: tolerates 4.2 against 4.20, refuses 4.2 against 42.
VALUE_TOLERANCE = 0.005


def normalize_text(text: str) -> str:
    """§2.4 rule 2's normalisation, applied to quotes and sections alike."""
    out = text.replace(_SOFT_HYPHEN, "").translate(_DASHES).translate(_SUPERSCRIPTS)
    return _SPACES.sub(" ", out).strip()


# A number as a paper writes one: 4.2, 4,200, 0.15, 1e6, 12%, 7-10 (both).
# A leading minus counts only when nothing numeric precedes it, so the '-10'
# in '7-10' is ten, not minus ten. Commas are thousands separators. A digit
# glued to a letter ('OD600') is an identifier, and a digit after a letter and
# a hyphen ('L-1', 'h-1', 'm-2') is a unit exponent — neither is a value, and
# the first version of this read every 'g L-1' as containing the number one.
_NUMBER = re.compile(r"(?<![\w.])(?<![A-Za-z]-)-?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?")


def parse_numbers(text: str) -> list[float]:
    """Every number in a (normalised) quote, as floats."""
    out: list[float] = []
    for m in _NUMBER.finditer(text):
        raw = m.group(0).replace(",", "")
        try:
            out.append(float(raw))
        except ValueError:
            continue
    return out


def _value_in_quote(value: float, quote: str) -> bool:
    for n in parse_numbers(quote):
        if value == 0:
            if n == 0:
                return True
            continue
        if abs(n - value) / abs(value) <= VALUE_TOLERANCE:
            return True
    return False


# Rule codes, in rule order. The counts are keyed by these.
ANCHOR_RULES = ("field", "section", "quote", "value", "unit", "range", "method")


@dataclass
class AnchorResult:
    accepted: list[Candidate] = field(default_factory=list)
    rejected: int = 0
    reasons: dict[str, int] = field(default_factory=lambda: {r: 0 for r in ANCHOR_RULES})
    details: list[str] = field(default_factory=list)


def anchor_candidate(
    raw: dict[str, Any],
    sections: list[dict[str, Any]],
    *,
    paper_id: str,
    candidate_id: str,
) -> tuple[Candidate | None, str | None, str | None]:
    """One candidate against §2.4. Returns (candidate, None, None) when it
    anchors, or (None, rule, detail) naming the rule that refused it.

    `raw` is what the extractor emitted — sectionId, field, value, unit, quote,
    and optionally method, organism, isPrimary, confidence. `sections` are the
    paper's fetched sections. The ontology and unit tables come from
    corpus.json through `units`, the same tables the browser ships.
    """
    field_id = str(raw.get("field") or "").strip()
    spec = ontology_field(field_id)
    if spec is None:
        return None, "field", f"{field_id!r} is not an ontology field"

    # 1. The section exists in the fetched text.
    section_id = str(raw.get("sectionId") or "").strip()
    section = next((s for s in sections if s.get("id") == section_id), None)
    if section is None:
        return None, "section", f"sectionId {section_id!r} is not a fetched section of {paper_id}"

    # 2. The quote is verbatim, and short enough to be a quote.
    quote = str(raw.get("quote") or "").strip()
    if not quote:
        return None, "quote", "empty quote"
    if len(quote) > MAX_QUOTE_CHARS:
        return None, "quote", f"quote is {len(quote)} characters; the limit is {MAX_QUOTE_CHARS}"
    norm_quote = normalize_text(quote)
    if norm_quote not in normalize_text(str(section.get("text") or "")):
        return None, "quote", f"quote is not in section {section_id} after normalisation"

    # 3. The value is inside the quote.
    value = raw.get("value")
    categorical = bool(spec.get("categorical"))
    if categorical:
        if not isinstance(value, str) or not value.strip():
            return None, "value", "categorical field needs a string value"
        if value.strip().lower() not in norm_quote.lower():
            return None, "value", f"value {value!r} does not appear in the quote"
        unit = ""
        canonical: float | None = None
        si = Quantity(value=value.strip(), unit="")
    else:
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None, "value", f"value {value!r} is not a number"
        if number != number:  # NaN
            return None, "value", "value is NaN"
        if not _value_in_quote(number, norm_quote):
            return None, "value", f"no number in the quote equals {number} within {VALUE_TOLERANCE:.1%}"

        # 4. The unit normalises, into the field's family.
        unit_raw = str(raw.get("unit") or "")
        unit = normalize_unit(unit_raw) or ""
        if not unit and unit_raw.strip():
            return None, "unit", f"unit {unit_raw!r} does not normalise"
        if not unit and spec["canonicalUnit"]:
            return None, "unit", f"field {field_id} is denominated in {spec['canonicalUnit']!r}; no unit given"
        try:
            canonical = to_canonical(number, unit, field_id)
        except UnitError as e:
            why = e.reason or str(e)
            return None, "unit", f"unit {unit!r} is not in the family of {spec['canonicalUnit']!r}: {why}"

        # 5. Inside the field's range, in canonical units.
        if not in_range(canonical, field_id):
            low, high = spec["range"]
            return None, "range", (
                f"{canonical:g} {spec['canonicalUnit']} is outside the range "
                f"{low:g}–{high:g} for {field_id}"
            )
        si_value, si_unit = to_si(number, unit)
        si = Quantity(value=si_value, unit=si_unit)

    # 6. A field that needs a method has one. 'undetermined' is a legitimate
    #    answer — the analysis was not done — and is not the same as absent.
    method = raw.get("method")
    method = str(method).strip() if method is not None else ""
    if spec.get("requiresMethod") and not method:
        return None, "method", f"{field_id} requires a method and none was given"

    confidence = raw.get("confidence", 0.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0

    return (
        Candidate(
            id=candidate_id,
            paperId=paper_id,
            sectionId=section_id,
            quote=quote,
            field=field_id,
            value=value.strip() if categorical else float(value),  # type: ignore[union-attr]
            unit=unit,
            si=si,
            confidence=confidence,
            organism=(str(raw["organism"]).strip() or None) if raw.get("organism") else None,
            isPrimary=bool(raw.get("isPrimary", True)),
            method=method or None,
        ),
        None,
        None,
    )


def anchor_all(
    raws: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    *,
    paper_id: str,
    id_prefix: str = "hk1",
) -> AnchorResult:
    """Every candidate through `anchor_candidate`; survivors numbered in order,
    rejections counted per rule. The counts are the response's rejection
    report and the log line."""
    out = AnchorResult()
    for raw in raws:
        n = len(out.accepted) + 1
        candidate, rule, detail = anchor_candidate(
            raw, sections, paper_id=paper_id, candidate_id=f"{id_prefix}-{paper_id}-{n}"
        )
        if candidate is not None:
            out.accepted.append(candidate)
        else:
            out.rejected += 1
            out.reasons[rule or "quote"] += 1
            out.details.append(f"{rule}: {detail}")
    return out
