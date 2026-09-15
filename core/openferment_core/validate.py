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

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from .models import Candidate, Claim, DroppedCandidate, Quantity, Range, weakest_provenance
from .units import (
    UnitError,
    convert,
    field as ontology_field,
    in_range,
    normalize as normalize_unit,
    to_canonical,
    to_si,
)

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
# Superscripts are two different things and are folded two different ways.
# On a unit they are an exponent spelled with a minus: 'L⁻¹' becomes 'L-1',
# the spelling the JATS split writes. On a NUMBER they are a power of ten:
# '10⁶' must become '10^6', not '106' — the first version folded both the
# same way and a titre of 2 × 10⁶ could never anchor, while a value of 106
# anchored falsely. `parse_numbers` reads the caret form below.
_SUP_DIGITS = "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079"
_SUPERSCRIPTS = str.maketrans(_SUP_DIGITS, "0123456789")
_POWER = re.compile(rf"(?<=\d) ?(\u207b?)([{_SUP_DIGITS}]+)")  # after a digit: an exponent
_UNIT_EXP = re.compile(rf"\u207b([{_SUP_DIGITS}]+)")  # superscript minus: a unit exponent
_DASHES = dict.fromkeys(map(ord, "\u2212\u2010\u2011\u2012\u2013\u2014\u2015\u207b"), "-")
_SOFT_HYPHEN = "\u00ad"
_SPACES = re.compile(r"\s+")

MAX_QUOTE_CHARS = 300
# §2.4 rule 3: tolerates 4.2 against 4.20, refuses 4.2 against 42.
VALUE_TOLERANCE = 0.005


def normalize_text(text: str) -> str:
    """§2.4 rule 2's normalisation, applied to quotes and sections alike."""
    out = text.replace(_SOFT_HYPHEN, "")
    out = _POWER.sub(lambda m: "^" + ("-" if m.group(1) else "") + m.group(2).translate(_SUPERSCRIPTS), out)
    out = _UNIT_EXP.sub(lambda m: "-" + m.group(1).translate(_SUPERSCRIPTS), out)
    out = out.translate(_DASHES).translate(_SUPERSCRIPTS)
    return _SPACES.sub(" ", out).strip()


# A number as a paper writes one: 4.2, 4,200, 0.15, 1e6, 12%, 7-10 (both).
# A leading minus counts only when nothing numeric precedes it, so the '-10'
# in '7-10' is ten, not minus ten. Commas are thousands separators. A digit
# glued to a letter ('OD600') is an identifier, and a digit after a letter and
# a hyphen ('L-1', 'h-1', 'm-2') is a unit exponent — neither is a value, and
# the first version of this read every 'g L-1' as containing the number one.
_NUMBER = re.compile(r"(?<![\w.])(?<![A-Za-z]-)-?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?")
# Scientific notation as a paper writes it after normalisation: '2 × 10^6',
# '2 x 10^6', '2·10^-3', or a bare '10^6'. The caret comes from
# normalize_text folding a superscript on a number. Matched first, and the
# span it covers is not re-read as the plain numbers 2, 10 and 6.
_SCI = re.compile(
    r"(?<![\w.])(?:(-?\d[\d,]*(?:\.\d+)?)\s*[×x*·]\s*)?10\^(-?\d+)(?![\w.])"
)


def parse_numbers(text: str) -> list[float]:
    """Every number in a (normalised) quote, as floats, in order."""
    found: list[tuple[int, float]] = []
    taken: list[tuple[int, int]] = []
    for m in _SCI.finditer(text):
        mantissa = float(m.group(1).replace(",", "")) if m.group(1) else 1.0
        found.append((m.start(), mantissa * 10.0 ** int(m.group(2))))
        taken.append(m.span())
    for m in _NUMBER.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        raw = m.group(0).replace(",", "")
        try:
            found.append((m.start(), float(raw)))
        except ValueError:
            continue
    return [v for _, v in sorted(found, key=lambda t: t[0])]


# ── the quantities a sentence states (OF-BLD-012.1 F1.2) ───────────────
#
# Rule 3 asks whether the sentence says this number. Read as bare numbers it
# cannot see three things the curators recorded and the papers write plainly:
# a number in another unit ("15 mg/L" for 0.015 g/L), a range ("7-10 days",
# whose midpoint the curator recorded), and a number written in words ("all
# eight sites"). So the quote is parsed into QUANTITIES — a number, and the
# unit token the sentence attached to it — and into the RANGES those
# quantities form. Both lists below are closed: adding to either is a commit
# with a test (OF-BLD-012.1 §7).

# Cardinals only. Ordinals ('second', 'third'), fractions ('half', 'quarter')
# and 'once/twice' are deliberately absent: 'the second impeller' is not the
# number two, and a validator that reads it as one gets switched off.
_CARDINAL_VALUE = {
    "zero": 0.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
    "eleven": 11.0, "twelve": 12.0, "thirteen": 13.0, "fourteen": 14.0,
    "fifteen": 15.0, "sixteen": 16.0, "seventeen": 17.0, "eighteen": 18.0,
    "nineteen": 19.0, "twenty": 20.0, "thirty": 30.0, "forty": 40.0,
    "fifty": 50.0, "sixty": 60.0, "seventy": 70.0, "eighty": 80.0,
    "ninety": 90.0, "hundred": 100.0,
}
# A scale word multiplies the number beside it: 'USD 1 million/kg' is 1e6.
_SCALE_VALUE = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
_WORD_VALUE = {**_CARDINAL_VALUE, **_SCALE_VALUE}
_WORD_QUANTITY = re.compile(
    r"(?<![A-Za-z])(" + "|".join(sorted(_WORD_VALUE, key=len, reverse=True)) + r")(?![A-Za-z])",
    re.IGNORECASE,
)

# An absence is a measurement the paper made. A curator who recorded
# negativeResult recorded that this sentence states one; these are the
# spellings the corpus uses for it. Closed, and matched case-insensitively.
NEGATION_MARKERS = (
    "no detectable", "not detected", "not phosphorylated", "non-phosphorylated",
    "unphosphorylated", "dephosphorylated", "did not", "no ", "none", "absent",
    "unsuccessful", "hardly", "failed to",
)

# How far past a number a unit may sit, and how many whitespace-separated
# tokens it may span: 'g L-1' is two, '% of total protein' is four.
# Whitespace, an approximation mark, and the pipe a fetched table row puts
# between its cells ('Fed-batch | 4200 | mg L-1'). No wider: a wider gap
# would swallow the unit it is looking for, because in '45-50%' the '%' IS
# the unit.
_UNIT_GAP = re.compile(r"[\s~\u2248|]{0,3}")
_UNIT_TOKENS = 4
_RANGE_CONNECTOR = re.compile(r"\s*(?:-|to|through)\s*", re.IGNORECASE)
_BETWEEN = re.compile(r"between\s*$", re.IGNORECASE)
_AND_CONNECTOR = re.compile(r"\s*and\s*", re.IGNORECASE)


@dataclass(frozen=True)
class QuoteQuantity:
    """One number the sentence states, with the unit token it wrote beside it.

    `unit` is None when the sentence gave none — then it compares as a bare
    number, which is what rule 3 did for every number before F1.2."""

    value: float
    unit: str | None
    start: int
    end: int
    """Where the number ends; `unitEnd` is where its unit token ends."""
    unitEnd: int


@dataclass(frozen=True)
class QuoteRange:
    """Two quantities the sentence joined: '7-10 days', '0.6 mg/L to 1 g/L'."""

    low: QuoteQuantity
    high: QuoteQuantity


def _numbers_with_spans(text: str) -> list[tuple[int, int, float]]:
    """Every number in a normalised text, with the span it occupies."""
    found: list[tuple[int, int, float]] = []
    taken: list[tuple[int, int]] = []
    for m in _SCI.finditer(text):
        mantissa = float(m.group(1).replace(",", "")) if m.group(1) else 1.0
        found.append((m.start(), m.end(), mantissa * 10.0 ** int(m.group(2))))
        taken.append(m.span())
    for m in _NUMBER.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        try:
            found.append((m.start(), m.end(), float(m.group(0).replace(",", ""))))
        except ValueError:
            continue
    return sorted(found, key=lambda t: t[0])


def _unit_after(text: str, end: int) -> tuple[str | None, int]:
    """The unit token a sentence attached to the number ending at `end`.

    Longest first, so 'g L-1' wins over 'g'. Nothing is read as a unit when
    the next thing is another number — in '12-15 mg/L' the 12 is bare, and
    reading '-15' as its unit would be reading the range as a unit."""
    gap = _UNIT_GAP.match(text, end)
    at = gap.end() if gap else end
    rest = text[at:]
    if not rest or _NUMBER.match(rest) or _SCI.match(rest):
        return None, end
    tokens = rest.split()
    for n in range(min(_UNIT_TOKENS, len(tokens)), 0, -1):
        spelled = " ".join(tokens[:n]).rstrip(".,;:)]")
        if not spelled:
            continue
        normalised = normalize_unit(spelled)
        if normalised:
            return normalised, at + len(spelled)
    return None, end


def parse_quantities(text: str) -> list[QuoteQuantity]:
    """Every quantity a (normalised) sentence states, in order.

    Numbers as digits, numbers written in words, and a number multiplied by
    the scale word beside it. The unit is the token the sentence wrote after
    the number, when that token is one the unit engine knows."""
    norm = normalize_text(text)
    atoms: list[tuple[int, int, float, bool]] = [
        (a, b, v, False) for a, b, v in _numbers_with_spans(norm)
    ]
    for m in _WORD_QUANTITY.finditer(norm):
        word = m.group(1).lower()
        atoms.append((m.start(), m.end(), _WORD_VALUE[word], word in _SCALE_VALUE))
    atoms.sort(key=lambda t: t[0])

    out: list[QuoteQuantity] = []
    i = 0
    while i < len(atoms):
        start, end, value, is_scale = atoms[i]
        # A number followed by a scale word is one quantity: '1 million'.
        if not is_scale and i + 1 < len(atoms) and atoms[i + 1][3]:
            nxt = atoms[i + 1]
            if norm[end : nxt[0]].strip() == "":
                value, end = value * nxt[2], nxt[1]
                i += 1
        unit, unit_end = _unit_after(norm, end)
        out.append(QuoteQuantity(value=value, unit=unit, start=start, end=end, unitEnd=unit_end))
        i += 1
    return out


def parse_ranges(text: str) -> list[QuoteRange]:
    """The ranges a (normalised) sentence states: adjacent quantities joined
    by a dash, by 'to', or by 'and' after 'between'."""
    norm = normalize_text(text)
    quantities = parse_quantities(norm)
    out: list[QuoteRange] = []
    for a, b in zip(quantities, quantities[1:]):
        gap = norm[a.unitEnd : b.start]
        joined = bool(_RANGE_CONNECTOR.fullmatch(gap)) or (
            bool(_AND_CONNECTOR.fullmatch(gap)) and bool(_BETWEEN.search(norm[: a.start]))
        )
        if joined:
            out.append(QuoteRange(low=a, high=b))
    return out


def _as_candidate_unit(value: float, unit: str | None, candidate_unit: str) -> float:
    """A quote's number in the candidate's unit. Bare when either side has no
    unit, and bare when the two do not convert — which is what rule 3 did for
    every number before F1.2, so conversion only ever lets more through."""
    if not unit or not candidate_unit:
        return value
    try:
        return convert(value, unit, candidate_unit)
    except (UnitError, ValueError, TypeError):
        return value


def _close(a: float, b: float) -> bool:
    if b == 0:
        return a == 0
    return abs(a - b) / abs(b) <= VALUE_TOLERANCE


def recorded_range(raw: Any) -> tuple[float, float] | None:
    """The range the curators recorded, from a dict or a Range."""
    r = raw.get("range") if isinstance(raw, dict) else getattr(raw, "range", None)
    if r is None:
        return None
    low = r.get("low") if isinstance(r, dict) else getattr(r, "low", None)
    high = r.get("high") if isinstance(r, dict) else getattr(r, "high", None)
    try:
        return float(low), float(high)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def value_basis(
    number: float,
    quote: str,
    candidate_unit: str,
    *,
    recorded_range: tuple[float, float] | None = None,
    negative_result: bool = False,
) -> str | None:
    """How this sentence says this number, or None when it does not (§2.4
    rule 3 as F1.2 rewrites it). Computed here and nowhere else: no model
    output and no reviewer sets it."""
    norm = normalize_text(quote)

    # A range the curators recorded, stated by the sentence in whatever units
    # the paper used. The value is then the midpoint or an endpoint of it.
    if recorded_range is not None:
        low, high = recorded_range
        for r in parse_ranges(norm):
            a = _as_candidate_unit(r.low.value, r.low.unit or r.high.unit, candidate_unit)
            b = _as_candidate_unit(r.high.value, r.high.unit or r.low.unit, candidate_unit)
            if not (_close(a, low) and _close(b, high)):
                continue
            if _close(number, (a + b) / 2):
                return "range-midpoint"
            if _close(number, a):
                return "range-low"
            if _close(number, b):
                return "range-high"

    # An absence the curators recorded. Zero is the reading; the sentence has
    # to say the absence in one of the words the corpus uses for it.
    if negative_result and number == 0:
        lowered = norm.lower()
        if any(marker in lowered for marker in NEGATION_MARKERS):
            return "negation"

    for q in parse_quantities(norm):
        if not _close(_as_candidate_unit(q.value, q.unit, candidate_unit), number):
            continue
        converted = bool(q.unit) and bool(candidate_unit) and q.unit != normalize_unit(candidate_unit)
        return "converted" if converted else "exact"
    return None


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


def content_id(
    prefix: str,
    paper_id: str,
    section_id: str,
    field_id: str,
    value: Any,
    unit: str,
    quote: str,
    *,
    method: str | None = None,
    is_primary: bool = True,
) -> str:
    """The id of an anchored candidate: '<run>-<paperId>-<8 hex of its content>'.

    Content-addressed, not positional. A reviewer's decision is about a
    sentence and a number; keyed by position it would follow the id onto
    whatever a re-extraction put there next. Keyed by content, a re-run that
    produces the same candidate produces the same id and the decision holds,
    and a different candidate gets a different id and starts undecided.

    The content is the NORMALISED form, so spelling the model varies does
    not split one candidate into two: the quote after §2.4 rule 2's
    normalisation (a superscript or a double space is the same sentence),
    the number to nine significant digits (a string '1.1 × 10⁻⁵' and a JSON
    1.1e-5 differ by an ulp after parsing), the canonical unit, a categorical
    value lower-cased. Method and primacy are in, because on a field that
    requires a method they are what the record is.
    """
    number = f"{value:.9g}" if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value).strip().lower()
    material = "\x1f".join(
        (paper_id, section_id, field_id, number, unit, normalize_text(quote), method or "", "1" if is_primary else "0")
    )
    return f"{prefix}-{paper_id}-{hashlib.sha1(material.encode('utf-8')).hexdigest()[:8]}"


@dataclass
class AnchorResult:
    accepted: list[Candidate] = field(default_factory=list)
    rejected: int = 0
    reasons: dict[str, int] = field(default_factory=lambda: {r: 0 for r in ANCHOR_RULES})
    details: list[str] = field(default_factory=list)
    # What was refused, with the rule — for `match_run` (§6.2), never BioRepo.
    dropped: list[DroppedCandidate] = field(default_factory=list)
    # Emissions that collapsed onto an earlier one under the same content id.
    duplicates: int = 0


def _why_not_in_quote(
    number: float,
    norm_quote: str,
    recorded: tuple[float, float] | None,
    negative: bool,
) -> str:
    """Why rule 3 refused, said so a reviewer knows what to do about it."""
    head = f"no number in the quote equals {number} within {VALUE_TOLERANCE:.1%}"
    if recorded is not None:
        low, high = recorded
        return f"{head}; the quote does not state the recorded range {low:g}-{high:g} either"
    if negative and number == 0:
        return (
            f"{head}; the record is marked a negative result, and the quote does not "
            "state an absence in any of the words the corpus uses for one"
        )
    if parse_quantities(norm_quote):
        return (
            f"{head}; the value is derived from the quote's numbers; edit it to the "
            "paper's spelling or record the derivation"
        )
    return f"{head}; the quote states no quantity at all"


def anchor_candidate(
    raw: dict[str, Any],
    sections: list[dict[str, Any]],
    *,
    paper_id: str,
    candidate_id: str | None = None,
    id_prefix: str = "hk1",
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

    # 3. The value is inside the quote — as the sentence states it (F1.2):
    #    in the units the paper used, as the range the curators recorded, as
    #    the absence it reports, or written in words.
    value = raw.get("value")
    categorical = bool(spec.get("categorical"))
    # The unit is normalised HERE, before the value is checked, because rule 3
    # reads the quote in the units the paper wrote and converts them into the
    # candidate's. The unit REFUSALS stay where they were, in rule 4 below, so
    # a candidate with both a bad unit and a bad value still refuses on the
    # value, exactly as it did before.
    unit_raw = str(raw.get("unit") or "")
    unit_normalised = normalize_unit(unit_raw) or ""
    basis: str | None = "exact"
    if categorical:
        if not isinstance(value, str) or not value.strip():
            return None, "value", "categorical field needs a string value"
        if normalize_text(value).lower() not in norm_quote.lower():
            return None, "value", f"value {value!r} does not appear in the quote"
        unit = ""
        canonical: float | None = None
        si = Quantity(value=value.strip(), unit="")
    else:
        # The tool asks for the number as the paper wrote it, and a paper
        # writes '4,200', '12.5%' or '1.5 × 10⁶'. A string is read the way a
        # quote is; it has to hold exactly one number.
        if isinstance(value, bool):
            return None, "value", f"value {value!r} is not a number"
        if isinstance(value, str):
            numbers = parse_numbers(normalize_text(value))
            if len(numbers) != 1:
                return None, "value", f"value {value!r} is not a single number"
            number = numbers[0]
        else:
            try:
                number = float(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return None, "value", f"value {value!r} is not a number"
        if number != number:  # NaN
            return None, "value", "value is NaN"
        recorded = recorded_range(raw)
        negative = bool(raw.get("negativeResult"))
        basis = value_basis(
            number, norm_quote, unit_normalised, recorded_range=recorded, negative_result=negative
        )
        if basis is None:
            return None, "value", _why_not_in_quote(number, norm_quote, recorded, negative)

        # 4. The unit normalises, into the field's family.
        unit = unit_normalised
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

    anchored_value = value.strip() if categorical else number  # type: ignore[union-attr]
    # §2.4 rule 3's answer, computed here and nowhere else (OF-BLD-012.1 §7):
    # no model output and no reviewer sets it.
    is_primary = bool(raw.get("isPrimary", True))
    recorded_span = recorded_range(raw)
    recorded_low, recorded_high = recorded_span or (0.0, 0.0)
    return (
        Candidate(
            id=candidate_id
            or content_id(
                id_prefix, paper_id, section_id, field_id, anchored_value, unit, quote,
                method=method or None, is_primary=is_primary,
            ),
            paperId=paper_id,
            sectionId=section_id,
            quote=quote,
            field=field_id,
            value=anchored_value,
            unit=unit,
            si=si,
            confidence=confidence,
            organism=(str(raw["organism"]).strip() or None) if raw.get("organism") else None,
            isPrimary=is_primary,
            method=method or None,
            valueBasis=basis,
            range=Range(low=recorded_low, high=recorded_high) if recorded_span else None,
            negativeResult=bool(raw.get("negativeResult")) or None,
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
    """Every candidate through `anchor_candidate`; survivors keep document
    order under content-addressed ids (`content_id`), exact duplicates
    collapse, rejections are counted per rule. The counts are the response's
    rejection report and the log line."""
    out = AnchorResult()
    by_id: dict[str, int] = {}
    for raw in raws:
        candidate, rule, detail = anchor_candidate(raw, sections, paper_id=paper_id, id_prefix=id_prefix)
        if candidate is not None:
            # Content-addressed ids: the same sentence, field and number
            # emitted twice is one candidate, not two. The more confident
            # emission is the one kept, and the collapse is counted.
            at = by_id.get(candidate.id)
            if at is not None:
                out.duplicates += 1
                if candidate.confidence > out.accepted[at].confidence:
                    out.accepted[at] = candidate
                continue
            by_id[candidate.id] = len(out.accepted)
            out.accepted.append(candidate)
        else:
            out.rejected += 1
            out.reasons[rule or "quote"] += 1
            out.details.append(f"{rule}: {detail}")
            value = raw.get("value")
            out.dropped.append(
                DroppedCandidate(
                    paperId=paper_id,
                    sectionId=str(raw.get("sectionId") or ""),
                    field=str(raw.get("field") or ""),
                    value=value if isinstance(value, (int, float, str)) and not isinstance(value, bool) else None,
                    unit=str(raw.get("unit") or ""),
                    rule=rule or "quote",
                    detail=detail or "",
                )
            )
    return out
