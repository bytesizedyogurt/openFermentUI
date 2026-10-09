"""Guild — the competence ledger, and the only functions that write it (OF-BLD-013 §1.2, §2.1, §3.1).

core/data/guild.json holds the people on the team and every entry recorded
about them: a passed lesson, a training briefing, a supervised run, a run
alone, a deviation, a witnessed check, the lead's designation of an assessor. A person's level on a skill is never
stored. The browser computes it from these entries (src/engine/competence.ts),
so the ledger only has to be right about what happened and who saw it.

Four writes, each a read-modify-write under one lock, each refusing with the
rule that failed and the reason in words, each with a `dry_run` that runs
every rule and writes nothing:

  write_person      add someone, or change their title, role or active flag
  write_evidence    append one entry
  withdraw          mark one entry withdrawn, keeping it for the audit trail
  write_policy      the lead's gate modes and check rate (§5.1)

The rules, by name:

  name        a person's name is empty, shorter than two characters, or a
              placeholder nobody is called ('you', 'me', 'reviewer', 'user',
              'test'), the same list biorepo.write refuses
  role        the ledger's first person is someone other than its lead, a
              change would leave no active lead, or an auditor is named as
              holding a skill
  added       a person is added or changed by someone who is not an active lead
  duplicate   an entry id or a new person id is already on the ledger, or a
              practice session already stands behind another entry
  person      an entry names a person who is not on the ledger, or not active
  skill       an entry names a skill the projection does not hold
  source      an entry pairs a kind with a source that does not produce it,
              comes from a run without naming its step, names a protocol
              step that does not carry the skill, names a lesson that does
              not count toward it, names a practice session that is not a
              closed session of this person on this skill, or names a check
              that is not an open check of this person on this skill
  observer    a sign-off, designation or cosigned run has no observer, an
              observer who is not an active person, or the person themselves;
              or an operator's own record of a run, a lesson passed or a
              practice session names one
  authority   a sign-off by someone with no assessor designation on the skill,
              a cosign by someone who does not hold it, a run alone by someone
              who does not hold it (both judged on the day of the run), any
              entry observed by an auditor, a designation by anyone but the
              lead, or a withdrawal by anyone but the entry's observer or the
              lead
  outcome     a failed entry of a kind that cannot fail
  note        an entry or a withdrawal with no words to audit
  date        `at` that is not a date, or is later than tomorrow
  evidence    a withdrawal naming an entry that does not exist or is already
              withdrawn
  policy      a check rate outside none to twelve a quarter

Nothing is repaired on the way through. The skills, the protocol steps that
need them and the lessons that count toward them live in TypeScript and
arrive as skills.json, written by `pnpm export:corpus` beside the corpus.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import atomic, intake
from .biorepo import MIN_REVIEWER_CHARS, PLACEHOLDER_REVIEWERS
from .competence import Competence
from .models import Guild, GuildEvidence, GuildPerson, GuildPolicy, GuildWithdrawal

log = logging.getLogger("openferment.guild")

PATH = intake.DATA_DIR / "guild.json"
PROJECTION = Path(__file__).parent / "data" / "skills.json"

_WRITE_LOCK = threading.Lock()

RULES = (
    "name",
    "role",
    "added",
    "duplicate",
    "person",
    "skill",
    "source",
    "observer",
    "authority",
    "outcome",
    "note",
    "date",
    "evidence",
    "policy",
)

# What the ledger accepts, kind by kind, and from which sources (OF-BLD-013
# §1, §2, §3). A sign-off is an assessor's; a designation is the lead's; a run
# is Deposition's, recorded as the operator completes a step; a lesson passed
# is Primer's, recorded as the learner answers its last checkpoint question;
# practice is Primer's too, recorded as a tutor session closes.
ACCEPTED: dict[str, frozenset[str]] = {
    "knowledge": frozenset({"signoff", "lesson"}),
    "supervised": frozenset({"signoff", "deposition"}),
    "witnessed": frozenset({"signoff", "check"}),
    "designation": frozenset({"lead"}),
    "independent": frozenset({"deposition"}),
    "deviation": frozenset({"deposition"}),
    "scenario": frozenset({"scenario"}),
}

# Only a witnessed check can fail; a failed one is what suspends a skill.
CAN_FAIL = frozenset({"witnessed"})

PERSON_ID = re.compile(r"^p-[a-z0-9][a-z0-9-]{0,62}$")
EVIDENCE_ID = re.compile(r"^e-[A-Za-z0-9-]{4,64}$")


class GuildRefused(ValueError):
    """A write guild.py would not make. `rule` names which condition held."""

    def __init__(self, rule: str, why: str):
        assert rule in RULES, rule
        super().__init__(f"{rule}: {why}")
        self.rule = rule
        self.why = why


# ── the projection ─────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _projection(path: str) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"{target} not found. Generate it with `pnpm export:corpus` from the repository root; "
            "the skills live in src/data/skills.ts and this is a projection of them."
        )
    return json.loads(target.read_text(encoding="utf-8"))


def projection() -> dict[str, Any]:
    return _projection(str(PROJECTION))


def skills() -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in projection()["skills"]}


def step_skills(protocol_id: str, step_id: str) -> list[str] | None:
    """The skills a step needs, across every version of its protocol, or None
    when no version of that protocol has that step."""
    found: list[str] | None = None
    for st in projection()["steps"]:
        if st["protocolId"] == protocol_id and st["stepId"] == step_id:
            found = (found or []) + [s for s in st["skills"] if s not in (found or [])]
    return found


def lesson_skills(lesson_id: str) -> list[str] | None:
    """The skills a lesson counts toward, or None when Primer has no such lesson."""
    for lesson in projection().get("lessons", []):
        if lesson["lessonId"] == lesson_id:
            return list(lesson["skills"])
    return None


def protocol_ids() -> set[str]:
    return {st["protocolId"] for st in projection()["steps"]}


# ── the file ───────────────────────────────────────────────────────────


def read() -> Guild:
    """The ledger. A missing file is an empty ledger: nobody has been added."""
    if not PATH.exists():
        return Guild()
    return Guild.model_validate_json(PATH.read_text(encoding="utf-8"))


def _persist(ledger: Guild) -> None:
    atomic.write_text(PATH, ledger.model_dump_json(indent=2, exclude_none=True) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _day(value: str) -> date | None:
    """The calendar day an `at` names, or None when it names none."""
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def _people(ledger: Guild) -> dict[str, GuildPerson]:
    return {p.id: p for p in ledger.people}


def _active_lead(ledger: Guild, person_id: str | None) -> bool:
    p = _people(ledger).get(person_id or "")
    return bool(p and p.active and p.role == "lead")


def _assessor_on(ledger: Guild, person_id: str, skill_id: str) -> bool:
    """Whether the lead has designated this person an assessor on this skill,
    and the designation still stands."""
    return any(
        e.personId == person_id
        and e.skillId == skill_id
        and e.kind == "designation"
        and e.outcome == "pass"
        and e.withdrawnAt is None
        for e in ledger.evidence
    )


def _check_name(name: str) -> None:
    clean = (name or "").strip()
    if len(clean) < MIN_REVIEWER_CHARS or clean.lower() in PLACEHOLDER_REVIEWERS:
        raise GuildRefused(
            "name",
            f"{clean!r} is a placeholder, not a person; the ledger is the record of who did what",
        )


# ── people ─────────────────────────────────────────────────────────────


def write_policy(policy: GuildPolicy, *, dry_run: bool = False) -> GuildPolicy:
    """The lead's choices for the team, or a refusal. Only an active lead
    changes them, and the change names who made it."""
    if not 0 <= policy.checksPerQuarter <= 12:
        raise GuildRefused("policy", "checks per quarter is a whole number from none to twelve")
    with _WRITE_LOCK:
        ledger = read()
        if not _active_lead(ledger, policy.updatedBy):
            raise GuildRefused("authority", "only an active lead changes the team's gate and check rate")
        stored = policy.model_copy(update={"updatedAt": _now()})
        if dry_run:
            return stored
        ledger.policy = stored
        _persist(ledger)
    log.info("guild: policy %s/%s, %d checks a quarter, by %s", stored.routineGate, stored.criticalGate, stored.checksPerQuarter, stored.updatedBy)
    return stored


def write_person(person: GuildPerson, *, dry_run: bool = False) -> GuildPerson:
    """Add a person, or change one, or refuse with the rule that failed.

    The ledger's first person is its lead and is added by nobody. Everyone
    after is added by an active lead. A change names who made it in
    `updatedBy`, also an active lead, and may change the title, role and
    active flag; the name is held to the same rule as on the way in, and the
    dates and the person who added them are kept as first written.
    """
    _check_name(person.name)
    if not PERSON_ID.match(person.id):
        raise GuildRefused("duplicate", f"{person.id!r} is not a person id (p- and lower-case letters, digits, hyphens)")
    if _day(person.joinedAt) is None:
        raise GuildRefused("date", f"joinedAt {person.joinedAt!r} is not a date")

    with _WRITE_LOCK:
        ledger = read()
        existing = _people(ledger).get(person.id)
        if existing is None:
            if any(p.name.strip().lower() == person.name.strip().lower() for p in ledger.people):
                raise GuildRefused("duplicate", f"{person.name!r} is already on the ledger under another id")
            if not ledger.people:
                if person.role != "lead":
                    raise GuildRefused(
                        "role",
                        "the ledger's first person is its lead: someone has to be able to add the rest "
                        "and designate assessors",
                    )
                if person.addedBy is not None:
                    raise GuildRefused("added", "the first person on the ledger is added by nobody")
            elif not _active_lead(ledger, person.addedBy):
                raise GuildRefused("added", f"{person.addedBy!r} is not an active lead; only a lead adds people")
            stored = person.model_copy(update={"addedAt": _now(), "updatedBy": None, "updatedAt": None})
            ledger.people.append(stored)
        else:
            if not _active_lead(ledger, person.updatedBy):
                raise GuildRefused("added", f"{person.updatedBy!r} is not an active lead; only a lead changes a person")
            leads_after = [
                p for p in ledger.people
                if p.active and p.role == "lead" and p.id != person.id
            ] + ([person] if person.active and person.role == "lead" else [])
            if not leads_after:
                raise GuildRefused("role", "this change would leave the ledger with no active lead")
            stored = existing.model_copy(
                update={
                    "name": person.name.strip(),
                    "title": person.title,
                    "role": person.role,
                    "active": person.active,
                    "updatedBy": person.updatedBy,
                    "updatedAt": _now(),
                }
            )
            ledger.people = [stored if p.id == person.id else p for p in ledger.people]
        if dry_run:
            return stored
        _persist(ledger)
    log.info("guild: person %s (%s) %s", stored.id, stored.role, "changed" if existing else "added")
    return stored


# ── evidence ───────────────────────────────────────────────────────────


def write_evidence(entry: GuildEvidence, *, dry_run: bool = False) -> GuildEvidence:
    """Append one entry, or refuse it with the rule that failed.

    `dry_run` is what `POST /api/guild/check` asks before the assessor signs:
    every rule runs and nothing is written, so asking and deciding are the
    same code. An entry with a check as its source is refused here: it is
    written by running the check (`checks.record`), which calls every
    criterion first (OF-BLD-013 §5.5).
    """
    return _write_entries([entry], dry_run=dry_run, from_check=None)[0]


def write_check_entries(entries: list[GuildEvidence], check_id: str, *, dry_run: bool = False) -> list[GuildEvidence]:
    """A check's run: one witnessed entry per skill, every one asked against
    the same ledger and written in one write, so the run lands whole or not
    at all. Only `checks.record` calls this."""
    return _write_entries(entries, dry_run=dry_run, from_check=check_id)


def _precheck(entry: GuildEvidence, known: dict[str, dict[str, Any]], from_check: str | None) -> date:
    """Every rule that needs no ledger. Returns the entry's day."""
    if not EVIDENCE_ID.match(entry.id):
        raise GuildRefused("duplicate", f"{entry.id!r} is not an entry id (e- and 4 to 64 letters, digits or hyphens)")
    if entry.skillId not in known:
        raise GuildRefused("skill", f"{entry.skillId!r} is not a skill in src/data/skills.ts")

    kind = entry.kind
    src = entry.source.kind
    if src not in ACCEPTED.get(kind, frozenset()):
        raise GuildRefused(
            "source",
            f"a {kind} entry comes from {' or '.join(sorted(ACCEPTED.get(kind, {'another source'})))}; "
            f"this one says {src!r}",
        )
    if not entry.source.ref.strip():
        raise GuildRefused("source", "a sign-off names what it rests on: a protocol id or a training record")
    if src == "deposition" and not entry.source.stepId:
        raise GuildRefused("source", "an entry from a run names the protocol step it was recorded at")
    if entry.source.stepId:
        tags = step_skills(entry.source.ref, entry.source.stepId)
        if tags is None:
            raise GuildRefused("source", f"{entry.source.ref} has no step {entry.source.stepId}")
        if entry.skillId not in tags:
            raise GuildRefused(
                "source",
                f"{entry.source.ref} step {entry.source.stepId} does not need {entry.skillId}; it needs "
                + (", ".join(tags) or "no skill"),
            )
    if src == "lesson":
        counts = lesson_skills(entry.source.ref)
        if counts is None:
            raise GuildRefused("source", f"Primer has no lesson {entry.source.ref}")
        if entry.skillId not in counts:
            raise GuildRefused(
                "source",
                f"lesson {entry.source.ref} does not count toward {entry.skillId}; it counts toward "
                + (", ".join(counts) or "no skill"),
            )
    if src == "check":
        from . import checks  # checks writes through here; imported late to keep the two apart

        if from_check != entry.source.ref:
            raise GuildRefused("source", "an entry from a check is written by running the check at the bench, which calls every criterion")

        ck = checks.get(entry.source.ref)
        if ck is None:
            raise GuildRefused("source", f"{entry.source.ref!r} is not a check")
        if ck.state not in checks.OPEN:
            raise GuildRefused("source", f"check {ck.id} is {ck.state}")
        if ck.personId != entry.personId or entry.skillId not in ck.skillIds:
            raise GuildRefused("source", f"check {ck.id} is for someone else, or for other skills")
    if src == "scenario":
        from . import practice  # practice writes through here; imported late to keep the two apart

        held = practice.session(entry.source.ref)
        if held is None:
            raise GuildRefused("source", f"{entry.source.ref!r} is not a practice session")
        if held.closedAt is None:
            raise GuildRefused("source", f"practice session {held.id} is still open")
        if held.personId != entry.personId or held.skillId != entry.skillId:
            raise GuildRefused("source", f"practice session {held.id} is someone else's, or on another skill")
        if entry.at[:10] != held.closedAt[:10]:
            raise GuildRefused("date", f"practice session {held.id} closed on {held.closedAt[:10]}, and the entry is dated otherwise")

    if entry.outcome == "fail" and kind not in CAN_FAIL:
        raise GuildRefused("outcome", f"a {kind} entry records something that happened; only a witnessed check can fail")
    if len(entry.raw.strip()) < 2:
        raise GuildRefused("note", "an entry needs the observer's words; an empty note cannot be audited")
    day = _day(entry.at)
    if day is None:
        raise GuildRefused("date", f"{entry.at!r} is not a date")
    if day > date.today() + timedelta(days=1):
        raise GuildRefused("date", f"{entry.at} is in the future; a sign-off records something already seen")
    return day


def _write_entries(entries: list[GuildEvidence], *, dry_run: bool, from_check: str | None) -> list[GuildEvidence]:
    known = skills()
    days = [_precheck(e, known, from_check) for e in entries]
    with _WRITE_LOCK:
        ledger = read()
        people = _people(ledger)
        stored_all: list[GuildEvidence] = []
        for entry, day in zip(entries, days):
            stored_all.append(_admit(entry, day, ledger, people, known, stored_all))
        if dry_run:
            return stored_all
        ledger.evidence.extend(stored_all)
        _persist(ledger)
    for stored in stored_all:
        log.info("guild: %s %s on %s for %s by %s", stored.kind, stored.outcome, stored.skillId, stored.personId, stored.observerId)
    return stored_all


def _admit(
    entry: GuildEvidence,
    day: date,
    ledger: Guild,
    people: dict[str, GuildPerson],
    known: dict[str, dict[str, Any]],
    batch: list[GuildEvidence],
) -> GuildEvidence:
    """Every rule that reads the ledger, with `batch` the entries already
    admitted beside this one in the same write."""
    src = entry.source.kind
    kind = entry.kind
    held = ledger.evidence + batch
    if any(e.id == entry.id for e in held):
        raise GuildRefused("duplicate", f"{entry.id} is already on the ledger")
    if src == "scenario" and any(
        e.source.kind == "scenario" and e.source.ref == entry.source.ref and not e.withdrawnAt for e in held
    ):
        raise GuildRefused("duplicate", f"practice session {entry.source.ref} is already on the ledger")
    if src == "check" and any(
        e.source.kind == "check" and e.source.ref == entry.source.ref and e.skillId == entry.skillId and not e.withdrawnAt
        for e in held
    ):
        raise GuildRefused("duplicate", f"check {entry.source.ref} is already on the ledger for {entry.skillId}")
    person = people.get(entry.personId)
    if person is None or not person.active:
        raise GuildRefused("person", f"{entry.personId!r} is not an active person on the ledger")
    if person.role == "auditor":
        raise GuildRefused("role", f"{person.name} is an auditor; an auditor reads the ledger and holds no skills")
    skill_name = known[entry.skillId]["name"]

    def holds(person_id: str) -> bool:
        # Judged on the day the step was run, from what the ledger held
        # by then: a run recorded offline and posted days later is held
        # to the level its operator and cosigner had when they did it.
        on = day.isoformat()
        seen = [e for e in ledger.evidence if e.at[:10] <= on]
        return Competence(seen, known, on).holds(person_id, entry.skillId)

    if src in ("lesson", "scenario"):
        # Primer records it as the learner passes the checkpoint, or as a
        # tutor session closes; no person watched, and the entry says so
        # by naming nobody.
        if entry.observerId is not None:
            raise GuildRefused(
                "observer",
                f"a {'lesson passed' if src == 'lesson' else 'practice session'} is recorded by Primer and names no observer; "
                "an assessor's briefing is a training sign-off",
            )
    elif kind in ("independent", "deviation"):
        # The operator's own record of a run: nobody else's name on it.
        if entry.observerId is not None:
            raise GuildRefused(
                "observer",
                f"a {kind} entry is the operator's own record and names no observer; "
                "a run with someone beside them is a supervised run",
            )
        if kind == "independent" and not holds(person.id):
            raise GuildRefused(
                "authority",
                f"{person.name} does not hold {skill_name} today, so a run of it alone is a deviation, "
                "or a supervised run with a cosigner",
            )
    else:
        observer = people.get(entry.observerId or "")
        if observer is None or not observer.active:
            raise GuildRefused("observer", f"a {kind} entry needs an observer who is an active person on the ledger")
        if observer.id == person.id:
            raise GuildRefused("observer", "nobody signs off their own work")
        if observer.role == "auditor":
            raise GuildRefused(
                "authority",
                f"{observer.name} is an auditor; an auditor reads the ledger and signs nothing, "
                "whatever entries they held before",
            )
        if kind == "designation":
            if observer.role != "lead":
                raise GuildRefused("authority", f"{observer.name} is not the lead; only the lead designates assessors")
        elif src == "deposition":
            if not holds(observer.id):
                raise GuildRefused(
                    "authority",
                    f"{observer.name} does not hold {skill_name} today, so cannot cosign it",
                )
        elif not _assessor_on(ledger, observer.id, entry.skillId):
            raise GuildRefused(
                "authority",
                f"{observer.name} holds no assessor designation on {skill_name}, so cannot sign it off",
            )

    stored = entry.model_copy(
        update={"raw": entry.raw.strip(), "recordedAt": _now(), "withdrawnAt": None, "withdrawnBy": None, "withdrawReason": None}
    )
    return stored


def withdraw(request: GuildWithdrawal, *, dry_run: bool = False) -> GuildEvidence:
    """Mark one entry withdrawn. The entry stays, with who withdrew it, when
    and why; the browser leaves it out of every level from then on."""
    if len(request.reason.strip()) < 2:
        raise GuildRefused("note", "a withdrawal says why")
    if _day(request.at) is None:
        raise GuildRefused("date", f"{request.at!r} is not a date")
    with _WRITE_LOCK:
        ledger = read()
        target = next((e for e in ledger.evidence if e.id == request.evidenceId), None)
        if target is None:
            raise GuildRefused("evidence", f"{request.evidenceId} is not on the ledger")
        if target.withdrawnAt is not None:
            raise GuildRefused("evidence", f"{request.evidenceId} was withdrawn on {target.withdrawnAt}")
        by = _people(ledger).get(request.by)
        if by is None or not by.active:
            raise GuildRefused("authority", f"{request.by!r} is not an active person on the ledger")
        if by.id != target.observerId and not _active_lead(ledger, by.id):
            raise GuildRefused("authority", "an entry is withdrawn by the person who observed it, or by the lead")
        stored = target.model_copy(
            update={"withdrawnAt": request.at, "withdrawnBy": by.id, "withdrawReason": request.reason.strip()}
        )
        if dry_run:
            return stored
        ledger.evidence = [stored if e.id == target.id else e for e in ledger.evidence]
        _persist(ledger)
    log.info("guild: %s withdrawn by %s", stored.id, stored.withdrawnBy)
    return stored
