"""Checks — proposed by fixed rules, scheduled and run by an assessor
(OF-BLD-013 §5.2).

`rank_pairs` and `propose` mirror src/engine/checks.ts, which is the
reference; the competence fixture holds the two together
(`pnpm export:competence-fixtures`, replayed by tests/test_checks.py). When
they disagree, the TypeScript side is right. The nightly job proposes; an
assessor can ask for a run of the ranking at any time, and a person or an
assessor can ask for a check by name.

core/data/checks.json keeps every check, and never enters git. Every write
is a read-modify-write under one lock, refused with the rule that held:

  person     the person is not active on the ledger, or is an auditor
  skill      a skill named is not in src/data/skills.ts, or a check names none
  authority  the one acting may not do this: proposing and dismissing take an
             assessor or the lead; scheduling and running take an assessor on
             every skill in the check, and never the person checked; asking
             takes the person or an assessor
  state      the check has closed, or a run of it is already on the ledger
  duplicate  an open check already covers these skills for this person
  note       a dismissal or a skill's note with no words to audit
  date       a day that is not a date, or later than tomorrow
  results    a run that does not call every criterion of every skill once
  check      no such check

Running a check writes one witnessed entry per skill through
guild.write_evidence, with the check as its source and the assessor's own
words as its raw: passed when every criterion of that skill was met. Every
entry is asked first with dry_run, so a run lands whole or not at all.
"""
from __future__ import annotations

import logging
import secrets
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from . import atomic, guild, intake
from .competence import Competence, days_between
from .models import (
    Check,
    CheckDismiss,
    CheckReason,
    CheckRecord,
    CheckRequest,
    Checks,
    CheckSchedule,
    EvidenceSource,
    Guild,
    GuildEvidence,
)

log = logging.getLogger("openferment.checks")

PATH = intake.DATA_DIR / "checks.json"
_WRITE_LOCK = threading.Lock()

RULES = ("person", "skill", "authority", "state", "duplicate", "note", "date", "results", "check")
OPEN = ("proposed", "scheduled")

LAPSING_DAYS = 21
DEVIATION_DAYS = 30
SKILLS_PER_CHECK = 3
PROPOSALS_PER_RUN = 5
WEIGHT = {"suspended": 5, "lapsed": 4, "lapsing": 3, "ready": 3, "deviation": 3, "confidence": 2, "rate": 2, "requested": 0}


class CheckRefused(ValueError):
    def __init__(self, rule: str, why: str):
        assert rule in RULES, rule
        super().__init__(f"{rule}: {why}")
        self.rule = rule
        self.why = why


# ── the file ───────────────────────────────────────────────────────────


def read() -> Checks:
    if not PATH.exists():
        return Checks()
    return Checks.model_validate_json(PATH.read_text(encoding="utf-8"))


def _persist(checks: Checks) -> None:
    atomic.write_text(PATH, checks.model_dump_json(indent=2, exclude_none=True) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _id() -> str:
    return f"ck-{int(time.time() * 1000):x}-{secrets.token_hex(3)}"


def get(check_id: str) -> Check | None:
    return next((c for c in read().checks if c.id == check_id), None)


def covered(checks: Checks) -> set[str]:
    """person|skill pairs an open check already covers."""
    return {f"{c.personId}|{s}" for c in checks.checks if c.state in OPEN for s in c.skillIds}


# ── the ranking, mirrored from src/engine/checks.ts ────────────────────


def quarter_start(day: str) -> str:
    m = int(day[5:7])
    return f"{day[:4]}-{(m - 1) // 3 * 3 + 1:02d}-01"


def _ready(status, skill: dict[str, Any], blocked: bool) -> bool:
    return status.level == 2 and not blocked and status.supervisedCount >= skill["supervisedRuns"]


def rank_pairs(ledger: Guild, skills: dict[str, dict[str, Any]], today: str, cover: set[str] | None = None) -> list[dict[str, Any]]:
    cover = cover or set()
    comp = Competence(ledger.evidence, skills, today)
    policy = ledger.policy
    quarter = quarter_start(today)
    live = [e for e in ledger.evidence if not e.withdrawnAt]
    out: list[dict[str, Any]] = []
    for person in ledger.people:
        if not person.active or person.role == "auditor":
            continue
        for skill_id, skill in skills.items():
            if f"{person.id}|{skill_id}" in cover:
                continue
            st = comp.status(person.id, skill_id)
            if st.level not in (2, 3):
                continue
            mine = [e for e in live if e.personId == person.id and e.skillId == skill_id]
            reasons: list[dict[str, str]] = []

            def add(kind: str, text: str) -> None:
                reasons.append({"kind": kind, "skillId": skill_id, "text": text})

            if st.level == 3 and st.suspended:
                failed = max(e.at[:10] for e in mine if e.kind == "witnessed" and e.outcome == "fail")
                add("suspended", f"Did not meet every criterion at the witnessed check on {failed}; a passed re-check lifts the suspension.")
            if st.level == 3 and st.lapsed:
                add("lapsed", f"Lapsed on {st.lapsesAt}: nothing on the ledger shows it performed within {skill['recencyDays']} days.")
            elif st.level == 3 and st.lapsesAt and days_between(today, st.lapsesAt) <= LAPSING_DAYS:
                add("lapsing", f"Lapses on {st.lapsesAt}.")
            blocked = any(comp.level(person.id, p) < 2 for p in skill["prerequisites"])
            if _ready(st, skill, blocked):
                add("ready", f"Supervised runs done ({st.supervisedCount} of {skill['supervisedRuns']}); a passed check would make it Qualified.")
            deviated = [
                e.at[:10] for e in mine if e.kind == "deviation" and 0 <= days_between(e.at, today) <= DEVIATION_DAYS
            ]
            if deviated:
                add("deviation", f"A deviation recorded on {max(deviated)}.")
            if st.level == 3 and not st.lapsed and not st.suspended and st.confidence == "low":
                add("confidence", "Qualified and current, with low confidence on the ledger’s own evidence.")
            if st.level == 3 and skill["criticality"] == "critical" and policy.checksPerQuarter > 0:
                checked = sum(1 for e in mine if e.kind == "witnessed" and quarter <= e.at[:10] <= today)
                if checked < policy.checksPerQuarter:
                    add(
                        "rate",
                        f"A critical skill with {checked} witnessed check{'' if checked == 1 else 's'} this quarter; "
                        f"the lead asks for {policy.checksPerQuarter}.",
                    )
            if not reasons:
                continue
            score = sum(WEIGHT[r["kind"]] for r in reasons) + (1 if skill["criticality"] == "critical" else 0)
            out.append({"personId": person.id, "skillId": skill_id, "score": score, "reasons": reasons})
    # Python's sort is stable and compares strings by code point, as the
    # TypeScript comparator does.
    return sorted(out, key=lambda p: (-p["score"], p["personId"], p["skillId"]))


def propose_from(ledger: Guild, skills: dict[str, dict[str, Any]], today: str, cover: set[str] | None = None, limit: int = PROPOSALS_PER_RUN) -> list[dict[str, Any]]:
    by_person: dict[str, list[dict[str, Any]]] = {}
    for pair in rank_pairs(ledger, skills, today, cover):
        pairs = by_person.setdefault(pair["personId"], [])
        if len(pairs) < SKILLS_PER_CHECK:
            pairs.append(pair)
    proposals = [
        {
            "personId": pid,
            "skillIds": [p["skillId"] for p in pairs],
            "score": sum(p["score"] for p in pairs),
            "reasons": [r for p in pairs for r in p["reasons"]],
        }
        for pid, pairs in by_person.items()
    ]
    return sorted(proposals, key=lambda p: (-p["score"], p["personId"]))[:limit]


# ── who may do what ────────────────────────────────────────────────────


def _person(ledger: Guild, person_id: str | None):
    return next((p for p in ledger.people if p.id == person_id and p.active), None)


def _assessor(ledger: Guild, person_id: str | None, skill_id: str) -> bool:
    p = _person(ledger, person_id)
    return bool(p and p.role != "auditor" and guild._assessor_on(ledger, p.id, skill_id))


def _assessor_anywhere(ledger: Guild, person_id: str | None) -> bool:
    return any(_assessor(ledger, person_id, s) for s in guild.skills())


def _lead(ledger: Guild, person_id: str | None) -> bool:
    p = _person(ledger, person_id)
    return bool(p and p.role == "lead")


def _day(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


# ── the writes ─────────────────────────────────────────────────────────


def propose(by: str | None, *, today: str | None = None, limit: int = PROPOSALS_PER_RUN) -> list[Check]:
    """Run the ranking and keep what it proposes beside the open checks.
    `by` is None for the nightly job, else an assessor or the lead."""
    ledger = guild.read()
    if by is not None and not (_lead(ledger, by) or _assessor_anywhere(ledger, by)):
        raise CheckRefused("authority", "the ranking is run by an assessor or the lead")
    day = today or date.today().isoformat()
    with _WRITE_LOCK:
        checks = read()
        made = [
            Check(
                id=_id(),
                personId=p["personId"],
                skillIds=p["skillIds"],
                reasons=[CheckReason(**r) for r in p["reasons"]],
                score=p["score"],
                proposedAt=_now(),
                proposedBy=by,
            )
            for p in propose_from(ledger, guild.skills(), day, covered(checks), limit)
        ]
        checks.checks.extend(made)
        _persist(checks)
    log.info("checks: %d proposed%s", len(made), f" by {by}" if by else " by the nightly ranking")
    return made


def request(asked: CheckRequest) -> Check:
    """A check asked for by name: by the person, who is ready, or by an assessor."""
    ledger = guild.read()
    known = guild.skills()
    person = _person(ledger, asked.personId)
    if person is None or person.role == "auditor":
        raise CheckRefused("person", f"{asked.personId!r} is not an active person who can hold skills")
    if not asked.skillIds or any(s not in known for s in asked.skillIds):
        raise CheckRefused("skill", "a check names the skills it is for, from src/data/skills.ts")
    if asked.by != asked.personId and not any(_assessor(ledger, asked.by, s) for s in asked.skillIds):
        raise CheckRefused("authority", "a check is asked for by the person, or by an assessor on one of its skills")
    with _WRITE_LOCK:
        checks = read()
        cover = covered(checks)
        fresh = [s for s in dict.fromkeys(asked.skillIds) if f"{asked.personId}|{s}" not in cover]
        if not fresh:
            raise CheckRefused("duplicate", "an open check already covers these skills for this person")
        who = "the person themselves" if asked.by == asked.personId else (_person(ledger, asked.by).name if _person(ledger, asked.by) else asked.by)
        made = Check(
            id=_id(),
            personId=asked.personId,
            skillIds=fresh,
            reasons=[CheckReason(kind="requested", skillId=s, text=f"Asked for by {who}.") for s in fresh],
            proposedAt=_now(),
            proposedBy=asked.by,
        )
        checks.checks.append(made)
        _persist(checks)
    return made


def _open(checks: Checks, check_id: str) -> Check:
    c = next((x for x in checks.checks if x.id == check_id), None)
    if c is None:
        raise CheckRefused("check", f"{check_id!r} is not a check")
    if c.state not in OPEN:
        raise CheckRefused("state", f"{c.id} is {c.state}")
    return c


def _replace(checks: Checks, c: Check) -> Check:
    checks.checks = [c if x.id == c.id else x for x in checks.checks]
    _persist(checks)
    return c


def schedule(check_id: str, s: CheckSchedule) -> Check:
    ledger = guild.read()
    day = _day(s.scheduledFor)
    if day is None:
        raise CheckRefused("date", f"{s.scheduledFor!r} is not a date")
    with _WRITE_LOCK:
        checks = read()
        c = _open(checks, check_id)
        if s.by == c.personId or not all(_assessor(ledger, s.by, k) for k in c.skillIds):
            raise CheckRefused("authority", "a check is scheduled by an assessor on every one of its skills, never by the person checked")
        return _replace(checks, c.model_copy(update={"state": "scheduled", "assessorId": s.by, "scheduledFor": day.isoformat()}))


def dismiss(check_id: str, d: CheckDismiss) -> Check:
    ledger = guild.read()
    if len(d.reason.strip()) < 2:
        raise CheckRefused("note", "a dismissal says why; it is kept for the audit trail")
    with _WRITE_LOCK:
        checks = read()
        c = _open(checks, check_id)
        if d.by == c.personId or not (_lead(ledger, d.by) or any(_assessor(ledger, d.by, k) for k in c.skillIds)):
            raise CheckRefused("authority", "a check is dismissed by an assessor on one of its skills or by the lead, never by the person checked")
        made = c.model_copy(update={"state": "dismissed", "dismissedBy": d.by, "dismissReason": d.reason.strip(), "closedAt": _now()})
        log.info("checks: %s dismissed by %s: %s", c.id, d.by, made.dismissReason)
        return _replace(checks, made)


def record(check_id: str, r: CheckRecord) -> Check:
    """The run at the bench: every criterion of every skill called, the
    assessor's words on each skill, one witnessed entry per skill."""
    ledger = guild.read()
    known = guild.skills()
    day = _day(r.at)
    if day is None:
        raise CheckRefused("date", f"{r.at!r} is not a date")
    if day > date.today() + timedelta(days=1):
        raise CheckRefused("date", f"{r.at} is in the future")
    with _WRITE_LOCK:
        checks = read()
        c = _open(checks, check_id)
        if r.by == c.personId or not all(_assessor(ledger, r.by, k) for k in c.skillIds):
            raise CheckRefused("authority", "a check is run by an assessor on every one of its skills, never by the person checked")
        calls: dict[tuple[str, int], bool] = {}
        for res in r.results:
            if res.skillId not in c.skillIds or not 0 <= res.criterion < len(known[res.skillId]["mastery"]):
                raise CheckRefused("results", f"{res.skillId} criterion {res.criterion} is not one this check asks about")
            if (res.skillId, res.criterion) in calls:
                raise CheckRefused("results", f"{res.skillId} criterion {res.criterion} is called twice")
            calls[(res.skillId, res.criterion)] = res.meets
        for k in c.skillIds:
            missing = [i for i in range(len(known[k]["mastery"])) if (k, i) not in calls]
            if missing:
                raise CheckRefused("results", f"every criterion of {known[k]['name']} is called before the check is signed")
        notes = {n.skillId: n.text.strip() for n in r.notes}
        for k in c.skillIds:
            if len(notes.get(k, "")) < 2:
                raise CheckRefused("note", f"write what you saw on {known[k]['name']}; an empty note cannot be audited")
        entries = [
            GuildEvidence(
                id=f"e-{_id()[3:]}",
                personId=c.personId,
                skillId=k,
                kind="witnessed",
                outcome="pass" if all(calls[(k, i)] for i in range(len(known[k]["mastery"]))) else "fail",
                at=day.isoformat(),
                observerId=r.by,
                source=EvidenceSource(kind="check", ref=c.id),
                raw=notes[k],
            )
            for k in c.skillIds
        ]
        # Every entry asked first, so the run lands whole or not at all.
        for e in entries:
            guild.write_evidence(e, dry_run=True)
        stored = [guild.write_evidence(e) for e in entries]
        done = c.model_copy(
            update={
                "state": "done",
                "assessorId": r.by,
                "results": r.results,
                "evidenceIds": [e.id for e in stored],
                "closedAt": _now(),
            }
        )
        log.info("checks: %s run by %s, %s", c.id, r.by, ", ".join(f"{e.skillId} {e.outcome}" for e in stored))
        return _replace(checks, done)


def main(argv: list[str]) -> int:
    """`python -m openferment_core.checks propose`, which the nightly job runs."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if argv[:1] == ["propose"]:
        made = propose(None)
        print(f"{len(made)} check(s) proposed")
        for c in made:
            print(f"  {c.id} {c.personId}: {', '.join(c.skillIds)} (score {c.score})")
        return 0
    print("usage: python -m openferment_core.checks propose", file=sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
