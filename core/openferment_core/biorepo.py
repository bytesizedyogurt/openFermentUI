"""BioRepo — one write function for the corpus (OF-BLD-012 §2.3, §7.1).

Every change to core/data/biorepo.json goes through `write(decision)`. There
is no second path: not the API, not a script, not a test helper. The file is
the one data file this increment commits, because it holds human decisions
and the short quotes that anchor them, and a file that several functions can
write is a file whose history nobody can explain.

`write` refuses a decision when any of these hold, and says which:

  record     recordId resolves to nothing in the seed or the candidates
  reviewer   reviewer is empty, shorter than two characters, or one of the
             placeholders nobody is called ('you', 'me', 'reviewer', 'user',
             'test') — the committed file records who decided what
  fulltext   a verified or gold decision names a record whose paper has no
             fetched full text — there is nothing for a promotion to anchor to
  quote      a verified or gold decision carries a quote that fails §2.4
             anchoring; or a gold decision has no quote that anchors at all,
             its own or the record's, because gold means "this sentence in
             this paper says this number" and a gold record without a
             sentence is a curated record wearing a badge
  paper      the record's paper carries no PMCID, DOI or PMID — the rule
             `check:biorepo` enforces on the committed file (§7.4), enforced
             here first so a decision the build would reject is never stored
  range      a promotion's value — corrected or gold — is outside the field's
             range in canonical units, or its unit does not normalise: §2.4
             rule 5, applied to what a reviewer typed as well as to what the
             model emitted
  status     a gold decision that is not a verified one: gold is a promotion,
             and a promotion with another status would be stored and never
             merged

Refusals reach the API as 422 with the rule and the reason. Nothing repairs a
bad decision: a quote that fails is not trimmed, a missing reviewer is not
filled in, an unfetched paper is not fetched on the way through.

What a stored decision looks like: exactly what the browser sent, plus — for
a gold decision that anchored on the record's own quote — that quote and
section copied onto it, so `check:biorepo`'s rule that every gold decision
has a quote holds by construction and not by convention.
"""
from __future__ import annotations

import logging
from typing import Any

from . import extract, intake
from .corpus import load_corpus
from .models import BioRepo, Candidate, Quantity, ReviewDecision
from .units import UnitError, field as ontology_field, in_range, to_canonical
from .validate import anchor_candidate

log = logging.getLogger("openferment.biorepo")

PATH = intake.DATA_DIR / "biorepo.json"

RULES = ("record", "reviewer", "fulltext", "quote", "paper", "range", "status")

# Names that are not a person (OF-BLD-012.1 F2). The README says a verified
# record is one a NAMED reviewer promoted; a file signed 'you' is signed by
# nobody, and this file is the record of who decided what. Closed list,
# matched case-insensitively after trimming; adding to it is a commit with a
# test.
PLACEHOLDER_REVIEWERS = frozenset({"you", "me", "reviewer", "user", "test"})
MIN_REVIEWER_CHARS = 2


class WriteRefused(ValueError):
    """A decision biorepo.write would not store. `rule` names which of §2.3's
    conditions held; the message says why in words."""

    def __init__(self, rule: str, why: str):
        assert rule in RULES, rule
        super().__init__(f"{rule}: {why}")
        self.rule = rule
        self.why = why


# ── the file ───────────────────────────────────────────────────────────


def read() -> BioRepo:
    """The committed decisions. A missing file is an empty repository, not an
    error — a fresh clone has made no decisions yet."""
    if not PATH.exists():
        return BioRepo()
    return BioRepo.model_validate_json(PATH.read_text(encoding="utf-8"))


def _persist(repo: BioRepo) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(repo.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8")


def decisions() -> dict[str, ReviewDecision]:
    return read().decisions


def records() -> list[Candidate]:
    return read().records


# ── resolving a record ─────────────────────────────────────────────────


def _resolve(record_id: str) -> dict[str, Any] | Candidate | None:
    """What this id names: the extractor's current candidate under it first —
    a decision is about what the extractor says NOW, and the copy kept here is
    refreshed on write — then the copy biorepo.json keeps (the only one on a
    checkout that never ran the extractor), then the seed record."""
    for response in extract.all_cached():
        for c in response.candidates:
            if c.id == record_id:
                return c
    for c in records():
        if c.id == record_id:
            return c
    seed = load_corpus().record(record_id)
    if seed is not None and seed.get("source", "seed") == "seed":
        return seed
    return None


def _field(rec: dict[str, Any] | Candidate, name: str) -> Any:
    return rec.get(name) if isinstance(rec, dict) else getattr(rec, name, None)


def _is_promotion(d: ReviewDecision) -> bool:
    return d.status == "verified" or d.provenance == "gold" or d.gold is not None


def _is_gold(d: ReviewDecision) -> bool:
    return d.provenance == "gold" or d.gold is not None


# ── the write ──────────────────────────────────────────────────────────


def write(decision: ReviewDecision, *, dry_run: bool = False) -> ReviewDecision:
    """Store one decision, or refuse it with the rule that failed (§2.3).

    `dry_run` runs every rule and writes nothing — the question the browser
    asks through `POST /api/biorepo/check` before the reviewer presses the
    key (OF-BLD-012.1 F1.5). There is still only one place the rules live;
    asking and deciding cannot drift apart because they are the same code.
    """
    reviewer = (decision.reviewer or "").strip()
    if not reviewer:
        raise WriteRefused("reviewer", "a decision needs a reviewer; an empty name is nobody deciding")
    if len(reviewer) < MIN_REVIEWER_CHARS or reviewer.lower() in PLACEHOLDER_REVIEWERS:
        raise WriteRefused(
            "reviewer",
            f"{reviewer!r} is a placeholder, not a person. Set a reviewer name in Settings — "
            "the committed file is the record of who decided what",
        )

    rec = _resolve(decision.recordId)
    if rec is None:
        raise WriteRefused(
            "record", f"{decision.recordId} is not a seed record and not a candidate anyone extracted"
        )
    paper_id = _field(rec, "paperId")
    paper = load_corpus().paper(paper_id) or {}
    if not (paper.get("pmcid") or paper.get("doi") or paper.get("pmid")):
        raise WriteRefused(
            "paper",
            f"{decision.recordId} is on {paper_id}, which carries no PMCID, DOI or PMID; "
            "a decision on it could not be committed (check:biorepo, §7.4)",
        )
    if _is_gold(decision) and decision.status != "verified":
        raise WriteRefused("status", f"a gold decision is a verified one; this one says {decision.status!r}")

    # What a reviewer typed is held to §2.4 rule 5 like what the model
    # emitted — whatever the record's status, and BOTH typed values when a
    # decision carries a gold value and a correction: the value, in
    # canonical units, inside the field's range. A correction on an
    # unverified seed record still reaches corpus.json (an unverified
    # candidate is not a record, and is not appended).
    field_id = _field(rec, "field")
    categorical = bool((ontology_field(field_id) or {}).get("categorical"))
    for what, typed in (("gold", decision.gold), ("corrected", decision.corrected)):
        if typed is None or categorical:
            continue
        if isinstance(typed.value, str) or isinstance(typed.value, bool):
            raise WriteRefused("range", f"the {what} value {typed.value!r} for {field_id} is not a number")
        try:
            canonical = to_canonical(float(typed.value), typed.unit, field_id)
        except (TypeError, ValueError, UnitError) as e:
            raise WriteRefused("range", f"the {what} value {typed.value!r} {typed.unit!r} for {field_id}: {e}") from e
        if not in_range(canonical, field_id):
            raise WriteRefused(
                "range",
                f"the {what} value {typed.value!r} {typed.unit!r} is outside the range of {field_id} in canonical units",
            )

    stored = decision.model_copy()
    if _is_promotion(decision):
        fetched = intake.cached(paper_id)
        if fetched is None or fetched.status != "complete" or not fetched.sections:
            raise WriteRefused(
                "fulltext",
                f"{decision.recordId} is on {paper_id}, which has no fetched full text — "
                "a promotion has to anchor in the paper's own words, and there are none here",
            )
        sections = [s.model_dump() for s in fetched.sections]

        # The quote a promotion stands on: the decision's if it brought one,
        # the record's own for gold. Accept without a quote proceeds (§7.3).
        quote = decision.quote
        section_id = decision.sectionId or _field(rec, "sectionId")
        if quote is None and _is_gold(decision):
            quote = _field(rec, "quote")
        if quote is not None:
            # Every value the promoted record will carry has to sit in the
            # quote: the correction (which becomes the record's value) and
            # the gold value, or the record's own when neither was typed.
            typed_values = [q for q in (decision.corrected, decision.gold) if q is not None]
            to_anchor: list[Quantity] = typed_values or [
                Quantity(value=_field(rec, "value"), unit=_field(rec, "unit"))
            ]
            for value_unit in to_anchor:
                raw = {
                    "sectionId": section_id,
                    "field": _field(rec, "field"),
                    "value": value_unit.value,
                    "unit": value_unit.unit,
                    "quote": quote,
                    "method": _field(rec, "method"),
                    # What the curators recorded about the value (F1.3). A
                    # gold decision on a record whose source states a range
                    # anchors on that range, with no reviewer edit; one on a
                    # recorded absence reads its zero out of the sentence.
                    "range": _field(rec, "range"),
                    "negativeResult": _field(rec, "negativeResult"),
                }
                _, rule, detail = anchor_candidate(
                    raw, sections, paper_id=paper_id, candidate_id=decision.recordId
                )
                if rule is not None:
                    raise WriteRefused(
                        "quote",
                        f"the quote for {decision.recordId} fails anchoring on rule '{rule}': {detail}",
                    )
            stored.quote = quote
            stored.sectionId = section_id

    repo = read()
    repo.decisions[decision.recordId] = stored
    if isinstance(rec, Candidate):
        # The candidate the decision is about, kept where the decision is.
        repo.records = [c for c in repo.records if c.id != rec.id] + [rec]
    if dry_run:
        return stored
    _persist(repo)
    log.info(
        "biorepo: %s → %s%s by %s",
        decision.recordId,
        stored.status,
        " (gold)" if _is_gold(stored) else "",
        stored.reviewer,
    )
    return stored
