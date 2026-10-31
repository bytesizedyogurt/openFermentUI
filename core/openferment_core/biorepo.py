"""BioRepo — one write function for a project's review decisions (OF-BLD-012 §2.3, §7.1).

Every review decision goes through `write(decision)`. There is no second
path: not the API, not a script, not a test helper. A project's decisions
are rows of the `decisions` table (ADR-001), one per decision in the order
made, each signed by its reviewer and carrying the candidate it was about;
the newest on a record holds. An undo is a row too, so what was decided and
taken back stays readable, and `read()` replays the rows into the decisions
that stand.

`write` refuses a decision when any of these hold, and says which:

  record     recordId names no candidate the extractor produced in this
             project, or kept with a decision
  reviewer   reviewer is empty, shorter than two characters, or one of the
             placeholders nobody is called ('you', 'me', 'reviewer', 'user',
             'test') — the decisions record who decided what
  fulltext   a verified or gold decision names a record on a document whose
             text the project does not hold in its literature (ADR-002) —
             there is nothing for a promotion to anchor to
  quote      a verified or gold decision carries a quote that fails §2.4
             anchoring; or a gold decision has no quote that anchors at all,
             its own or the record's, because gold means "this sentence in
             this paper says this number" and a gold record without a
             sentence is a curated record wearing a badge
  paper      the record's paper is not a document the project holds — a
             decision stands on a text a reader can look up (§7.4)
  unit       a typed value — corrected or gold — is not a number, or its unit
             does not convert into the field's canonical unit: §2.4 rule 4,
             applied to what a reviewer typed as well as to what the model
             emitted
  status     a gold decision that is not a verified one: gold is a promotion,
             and a promotion with another status would be stored and never
             merged

Refusals reach the API as 422 with the rule and the reason. Nothing repairs a
bad decision: a quote that fails is not trimmed, a missing reviewer is not
filled in, an unfetched paper is not fetched on the way through.

What a stored decision looks like: what the browser sent, with its
provenance computed from what the decision is (`provenance_of`; ADR-006: no
person sets provenance), plus — for a gold decision that anchored on the
record's own quote — that quote and section copied onto it, so every gold
decision has a quote by construction.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import insert, select

from . import db, extract, projects
from .basis import EstimateRefused, refuse_estimates
from .literature import kit
from .db import models as t
from .models import BioRepo, Candidate, Quantity, ReviewDecision
from .units import UnitError, field as ontology_field, to_canonical
from .validate import anchor_candidate

log = logging.getLogger("openferment.biorepo")

RULES = ("record", "reviewer", "fulltext", "quote", "paper", "unit", "status", "estimate")

# Names that are not a person (OF-BLD-012.1 F2). The README says a verified
# record is one a NAMED reviewer promoted; a file signed 'you' is signed by
# nobody, and this file is the record of who decided what. Closed list,
# matched case-insensitively after trimming; adding to it is a commit with a
# test.
PLACEHOLDER_REVIEWERS = frozenset({"you", "me", "reviewer", "user", "test"})
MIN_REVIEWER_CHARS = 2


def reviewer_refusal(name: str) -> str | None:
    """The reviewer-name rule `write` applies, for any caller that records a
    person's name (an override, an assumption): None when the name passes."""
    if any(ch.isspace() and ch != " " for ch in (name or "")) or any(not ch.isprintable() for ch in (name or "")):
        return "a name is one line of plain text"
    name = (name or "").strip()
    if not name:
        return "an approval needs a name; an empty name is nobody approving"
    if len(name) < MIN_REVIEWER_CHARS or name.lower() in PLACEHOLDER_REVIEWERS:
        return f"{name!r} is a placeholder, not a person"
    return None


class WriteRefused(ValueError):
    """A decision biorepo.write would not store. `rule` names which of §2.3's
    conditions held; the message says why in words."""

    def __init__(self, rule: str, why: str):
        assert rule in RULES, rule
        super().__init__(f"{rule}: {why}")
        self.rule = rule
        self.why = why


# ── the decisions ──────────────────────────────────────────────────────


async def _standing(project_id: str) -> BioRepo:
    """The decisions that stand, replayed from the rows in the order made: a
    decision on a record replaces the one before it in place, an undo takes
    the record out, and the candidates are those of the standing decisions,
    the most recently decided last."""
    async with db.session() as s:
        rows = (
            await s.execute(
                select(t.decisions.c.record_id, t.decisions.c.body, t.decisions.c.record)
                .where(t.decisions.c.project_id == project_id)
                .order_by(t.decisions.c.seq)
            )
        ).all()
    repo = BioRepo()
    for row in rows:
        decision = ReviewDecision.model_validate(row.body)
        repo.records = [c for c in repo.records if c.id != row.record_id]
        if _is_withdrawal(decision):
            repo.decisions.pop(row.record_id, None)
            continue
        repo.decisions[row.record_id] = decision
        if row.record is not None:
            repo.records.append(Candidate.model_validate(row.record))
    return repo


def read() -> BioRepo:
    """The project's standing decisions; none before anyone has decided."""
    return db.run(_standing(projects.current()))


async def _keep(project_id: str, decision: ReviewDecision, record: Candidate | None, *, undo: bool) -> None:
    """Add one row under the project's lock. An undo of a record with no
    standing decision adds nothing: there is nothing to take back."""
    async with db.session() as s:
        await db.lock(s, "biorepo", project_id)
        if undo and decision.recordId not in (await _standing(project_id)).decisions:
            return
        await s.execute(
            insert(t.decisions).values(
                project_id=project_id,
                record_id=decision.recordId,
                body=decision.model_dump(mode="json", exclude_none=True),
                record=record.model_dump(mode="json", exclude_none=True) if record is not None else None,
                created_by=(decision.reviewer or "").strip(),
            )
        )


def decisions() -> dict[str, ReviewDecision]:
    return read().decisions


def records() -> list[Candidate]:
    return read().records


# ── resolving a record ─────────────────────────────────────────────────


# A paper id is letters, digits and underscores ('B5', 'O8m'), as a
# candidate id carries it (OF-BLD-012.1 §6.9).
_CANDIDATE_ID = re.compile(r"^[^-]+-(?P<paper>[A-Za-z0-9_]+)-[0-9a-f]{8}$")
# A candidate a model wrote by hand ('mw1-B5-0000', OF-BLD-015 §7.3), kept in
# its own row beside the extractor's (OF-BLD-016 §1.R).
_HAND_ID = re.compile(rf"^{extract.MODEL_PREFIX}-(?P<paper>[A-Za-z0-9_]+)-[0-9]{{4}}$")


def _held(paper_id: str) -> bool:
    """Whether a reader can look the paper up: a document the project holds
    in its literature, whose text and citation the kit keeps."""
    return db.run(kit.linked(projects.current(), paper_id)) is not None


def _resolve(record_id: str) -> Candidate | None:
    """What this id names: the extractor's current candidate under it first —
    a decision is about what the extractor says NOW, and the copy kept with a
    decision is refreshed on write — then the copy kept with its standing
    decision.

    A candidate id names its paper ('cl1-T5-276fbb61'), so that paper's row
    alone is read; an id that names no paper reads no candidates."""
    m = _CANDIDATE_ID.match(record_id)
    hand = _HAND_ID.match(record_id)
    response = extract.cached(m.group("paper")) if m else extract.hand(hand.group("paper")) if hand else None
    for c in response.candidates if response else []:
        if c.id == record_id:
            return c
    for c in records():
        if c.id == record_id:
            return c
    return None


def _is_promotion(d: ReviewDecision) -> bool:
    return d.status == "verified" or d.provenance == "gold" or d.gold is not None


def _is_gold(d: ReviewDecision) -> bool:
    return d.provenance == "gold" or d.gold is not None


def _is_withdrawal(d: ReviewDecision) -> bool:
    """A decision that decides nothing — 'unverified' with nothing typed,
    nothing rejected — is what an undo posts: the record as it was."""
    return (
        d.status == "unverified"
        and d.gold is None
        and d.corrected is None
        and not d.rejectReason
        and d.provenance != "gold"
    )


def provenance_of(d: ReviewDecision) -> str:
    """The class a decision gives its record, computed from what the decision
    is: gold for a gold value, verified for a record a named reviewer
    promoted against the paper's own words, and unverified for anything else,
    a rejection or a correction left unverified among them. The client's
    `provenanceOf` reads a decided record the same way."""
    if d.status == "verified":
        return "gold" if _is_gold(d) else "verified"
    return "unverified"


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
            "the decisions are the record of who decided what",
        )

    try:
        refuse_estimates(decision, "BioRepo")
    except EstimateRefused as e:
        raise WriteRefused("estimate", f"{decision.recordId}: {e}") from None

    rec = _resolve(decision.recordId)
    if rec is None:
        raise WriteRefused(
            "record", f"{decision.recordId} is no candidate anyone extracted in this project"
        )
    paper_id = rec.paperId
    if not _held(paper_id):
        raise WriteRefused(
            "paper",
            f"{decision.recordId} is on {paper_id}, which is not a document this project holds; a decision "
            "stands on a text a reader can look up (§7.4)",
        )
    if _is_gold(decision) and decision.status != "verified":
        raise WriteRefused("status", f"a gold decision is a verified one; this one says {decision.status!r}")

    # What a reviewer typed is held to §2.4 rule 4 like what the model
    # emitted — whatever the record's status, and BOTH typed values when a
    # decision carries a gold value and a correction: a number, in a unit
    # that converts into the field's canonical unit.
    field_id = rec.field
    categorical = bool((ontology_field(field_id) or {}).get("categorical"))
    for what, typed in (("gold", decision.gold), ("corrected", decision.corrected)):
        if typed is None or categorical:
            continue
        if isinstance(typed.value, str) or isinstance(typed.value, bool):
            raise WriteRefused("unit", f"the {what} value {typed.value!r} for {field_id} is not a number")
        try:
            to_canonical(float(typed.value), typed.unit, field_id)
        except (TypeError, ValueError, UnitError) as e:
            raise WriteRefused("unit", f"the {what} value {typed.value!r} {typed.unit!r} for {field_id}: {e}") from e

    stored = decision.model_copy(update={"provenance": provenance_of(decision)})
    typed = decision.corrected is not None or decision.gold is not None
    if _is_withdrawal(decision):
        # An undo: the record as it was before anyone decided, the candidate
        # it was about with it. Idempotent when there was none.
        if not dry_run:
            db.run(_keep(projects.current(), stored, None, undo=True))
            log.info("biorepo: %s withdrawn by %s", decision.recordId, reviewer)
        return stored
    if _is_promotion(decision) or typed:
        try:
            sections = extract.passages(paper_id)
        except extract.ExtractUnavailable as e:
            raise WriteRefused(
                "fulltext",
                f"{decision.recordId} is on {paper_id}, whose text this project does not hold — "
                + ("a promotion" if _is_promotion(decision) else "a typed value")
                + " has to anchor in the document's own words, and there are none here",
            ) from e

        # The quote a decision stands on: the decision's if it brought one,
        # else the record's own whenever there is a NUMBER to place — gold,
        # or a correction, which becomes the record's value and has to sit
        # in a sentence the paper wrote like any other (§6.9). Accept
        # without a quote and without a typed value proceeds (§7.3).
        quote = decision.quote
        section_id = decision.sectionId or rec.sectionId
        if quote is None and (_is_gold(decision) or typed):
            quote = rec.quote
        if quote is not None:
            # Every value the promoted record will carry has to sit in the
            # quote: the correction (which becomes the record's value) and
            # the gold value, or the record's own when neither was typed.
            typed_values = [q for q in (decision.corrected, decision.gold) if q is not None]
            to_anchor: list[Quantity] = typed_values or [
                Quantity(value=rec.value, unit=rec.unit)
            ]
            for value_unit in to_anchor:
                raw = {
                    "sectionId": section_id,
                    "field": rec.field,
                    "value": value_unit.value,
                    "unit": value_unit.unit,
                    "quote": quote,
                    "method": rec.method,
                    # What the curators recorded about the value (F1.3). A
                    # gold decision on a record whose source states a range
                    # anchors on that range, with no reviewer edit; one on a
                    # recorded absence reads its zero out of the sentence.
                    "range": rec.range,
                    "negativeResult": rec.negativeResult,
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

    if dry_run:
        return stored
    # The candidate the decision is about, kept with the decision.
    db.run(_keep(projects.current(), stored, rec, undo=False))
    log.info(
        "biorepo: %s → %s%s by %s",
        decision.recordId,
        stored.status,
        " (gold)" if _is_gold(stored) else "",
        stored.reviewer,
    )
    return stored
