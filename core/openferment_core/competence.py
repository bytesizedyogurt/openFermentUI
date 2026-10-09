"""Competence, mirrored (OF-BLD-013 §2.1).

`src/engine/competence.ts` is the reference implementation; this is its
mirror, for the one place the service needs a level: deciding whether the
person cosigning a run, or claiming to have run a step alone, holds the skill.
The two are held together by a fixture the TypeScript side writes
(`pnpm export:competence-fixtures`, run by `pnpm test:core`), which
tests/test_competence.py replays here. If they disagree, the TypeScript side
is right.

Only what a rule needs is mirrored: the ladder, the lapse, the suspension and
the effective level. Confidence is the browser's alone; nothing the service
decides depends on it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from .models import GuildEvidence, GuildPerson

PERFORMED = frozenset({"witnessed", "supervised", "independent"})


@dataclass(frozen=True)
class Status:
    level: int
    effective: int
    lapsed: bool
    suspended: bool
    lapsesAt: str | None
    supervisedCount: int
    knowledgeComplete: bool


def _day(at: str) -> str:
    return at[:10]


# An entry the service has not stored yet is the newest of its day.
NOT_YET_RECORDED = "\uffff"


def _when(e: GuildEvidence) -> tuple[str, str, str]:
    """Ledger order: by the day it happened, then by when it was recorded, then id."""
    return (_day(e.at), e.recordedAt or NOT_YET_RECORDED, e.id)


def _signed_off(ev: list[GuildEvidence]) -> bool:
    """Knowledge an assessor signed off. A lesson passed is knowledge too, and
    puts the person at Learning; only the sign-off moves them to Supervised."""
    return any(e.kind == "knowledge" and e.outcome == "pass" and e.source.kind == "signoff" for e in ev)


def _add_days(day: str, n: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


class Competence:
    """Levels over one ledger, computed on demand and remembered."""

    def __init__(self, evidence: Iterable[GuildEvidence], skills: dict[str, dict[str, Any]], today: str):
        self.skills = skills
        self.today = today
        self._by_key: dict[tuple[str, str], list[GuildEvidence]] = {}
        for e in sorted((e for e in evidence if not e.withdrawnAt), key=_when):
            self._by_key.setdefault((e.personId, e.skillId), []).append(e)
        self._base: dict[tuple[str, str], int] = {}
        self._visiting: set[tuple[str, str]] = set()

    def _entries(self, person_id: str, skill_id: str) -> list[GuildEvidence]:
        return self._by_key.get((person_id, skill_id), [])

    def level(self, person_id: str, skill_id: str) -> int:
        k = (person_id, skill_id)
        if k in self._base:
            return self._base[k]
        skill = self.skills.get(skill_id)
        if skill is None or k in self._visiting:
            return 0
        self._visiting.add(k)
        ev = self._entries(person_id, skill_id)

        def passed(kind: str) -> bool:
            return any(e.kind == kind and e.outcome == "pass" for e in ev)

        knowledge = _signed_off(ev)
        supervised = sum(1 for e in ev if e.kind == "supervised" and e.outcome == "pass")
        prereq_ok = all(self.level(person_id, p) >= 2 for p in skill["prerequisites"])
        if passed("designation"):
            lvl = 4
        elif knowledge and prereq_ok and passed("witnessed") and supervised >= skill["supervisedRuns"]:
            lvl = 3
        elif knowledge and prereq_ok:
            lvl = 2
        elif ev:
            lvl = 1
        else:
            lvl = 0
        self._visiting.discard(k)
        self._base[k] = lvl
        return lvl

    def status(self, person_id: str, skill_id: str) -> Status:
        skill = self.skills[skill_id]
        ev = self._entries(person_id, skill_id)
        lvl = self.level(person_id, skill_id)
        performed = [e for e in ev if e.kind in PERFORMED and e.outcome == "pass"]
        last = _day(performed[-1].at) if performed else None
        witnessed = [e for e in ev if e.kind == "witnessed"]
        lapses_at = _add_days(last, skill["recencyDays"]) if lvl == 3 and last else None
        lapsed = bool(lapses_at and lapses_at < self.today)
        suspended = lvl == 3 and bool(witnessed) and witnessed[-1].outcome == "fail"
        return Status(
            level=lvl,
            effective=2 if (lapsed or suspended) else lvl,
            lapsed=lapsed,
            suspended=suspended,
            lapsesAt=lapses_at,
            supervisedCount=sum(1 for e in ev if e.kind == "supervised" and e.outcome == "pass"),
            knowledgeComplete=_signed_off(ev),
        )

    def holds(self, person_id: str, skill_id: str) -> bool:
        """Qualified or above, and neither lapsed nor suspended: may perform alone and cosign."""
        return self.status(person_id, skill_id).effective >= 3


def all_statuses(
    evidence: list[GuildEvidence], people: list[GuildPerson], skills: dict[str, dict[str, Any]], today: str
) -> dict[tuple[str, str], Status]:
    c = Competence(evidence, skills, today)
    return {
        (p.id, s): c.status(p.id, s)
        for p in people
        if p.role != "auditor"
        for s in skills
    }
