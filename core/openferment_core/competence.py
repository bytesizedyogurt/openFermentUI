"""Competence, mirrored.

`src/engine/competence.ts` is the reference implementation; this is its
mirror, for the one place the service needs a level: deciding whether the
person cosigning a run, or claiming to have run a step alone, holds the skill.
The two are held together by a fixture the TypeScript side writes
(`pnpm export:competence-fixtures`, run by `pnpm test:core`), which
tests/test_competence.py replays here. If they disagree, the TypeScript side
is right.

Only what a rule needs is mirrored: the ladder, the lapse, the suspension,
the effective level, and (since checks are proposed by the service at night) the confidence sort.

A SKILL WITH NO POLICY (alpha 2.2 E.8). The skills are the project's skills
catalogue (catalogues.py, `as_skills`), and an entry there may be kept with
no policy: no criticality, no recency, no count of supervised runs. Such a
skill is left out of every level (`unrated`): its level is 0, nobody holds
it, and the rules that read a level (guild.py's cosign and run alone,
checks.py's ranking and a check asked for by name) say so in words. The
browser's skills are the same catalogue's (alpha 2.2 E.12), and
competence.ts leaves such a skill out the same way: the competence fixture
holds skills that each carry a policy, and competence-unrated.json a skill
kept with none beside one that needs it, each held equal here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from .models import GuildEvidence, GuildPerson

PERFORMED = frozenset({"witnessed", "supervised", "independent"})
# A skill's policy, as its catalogue entry holds it: how critical it is, how
# many days a qualification stands with nobody seeing the person perform, and
# how many cosigned runs come before a witnessed check can qualify.
POLICY = ("criticality", "recencyDays", "supervisedRuns")


def unrated(skill: dict[str, Any]) -> str | None:
    """Why Guild rates nobody on `skill`, in words: a skill whose catalogue
    entry holds no policy. None when it holds one."""
    if all(skill.get(k) is not None for k in POLICY):
        return None
    return (f"{skill.get('name') or skill.get('id')} has no policy in the project's skills catalogue (its criticality, "
            "how many days a qualification stands and how many supervised runs come before a witnessed check), so "
            "Guild rates nobody on it")


@dataclass(frozen=True)
class Status:
    level: int
    effective: int
    lapsed: bool
    suspended: bool
    lapsesAt: str | None
    supervisedCount: int
    knowledgeComplete: bool
    confidence: str = "low"


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


def days_between(a: str, b: str) -> int:
    """Days from `a` to `b`, both read as calendar days."""
    return (date.fromisoformat(b[:10]) - date.fromisoformat(a[:10])).days


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
        # A skill kept with no policy is left out of every level (`unrated`).
        if skill is None or unrated(skill) or k in self._visiting:
            return 0
        self._visiting.add(k)
        ev = self._entries(person_id, skill_id)

        def passed(kind: str) -> bool:
            return any(e.kind == kind and e.outcome == "pass" for e in ev)

        knowledge = _signed_off(ev)
        supervised = sum(1 for e in ev if e.kind == "supervised" and e.outcome == "pass")
        prereq_ok = all(self.level(person_id, p) >= 2 for p in skill.get("prerequisites") or ())
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
        supervised_count = sum(1 for e in ev if e.kind == "supervised" and e.outcome == "pass")
        if unrated(skill):
            # Left out of every level: nothing lapses or is suspended, and the confidence sort has nothing to read.
            return Status(level=0, effective=0, lapsed=False, suspended=False, lapsesAt=None,
                          supervisedCount=supervised_count, knowledgeComplete=_signed_off(ev))
        performed = [e for e in ev if e.kind in PERFORMED and e.outcome == "pass"]
        last = _day(performed[-1].at) if performed else None
        witnessed = [e for e in ev if e.kind == "witnessed"]
        lapses_at = _add_days(last, skill["recencyDays"]) if lvl == 3 and last else None
        lapsed = bool(lapses_at and lapses_at < self.today)
        suspended = lvl == 3 and bool(witnessed) and witnessed[-1].outcome == "fail"

        # The confidence sort, as competence.ts scores it.
        today = self.today
        score = 0
        if lvl == 4:
            score += 3
        if any(e.outcome == "pass" and days_between(e.at, today) <= skill["recencyDays"] for e in witnessed):
            score += 2
        score += min(2, sum(1 for e in performed if days_between(e.at, today) <= 60))
        score -= 2 * sum(1 for e in ev if e.kind == "deviation" and days_between(e.at, today) <= 90)
        if suspended:
            score -= 3
        if lapsed:
            score -= 2
        elif lapses_at and days_between(today, lapses_at) <= 21:
            score -= 1
        if lvl == 2 and supervised_count >= skill["supervisedRuns"]:
            score += 1
        confidence = "high" if score >= 3 else "medium" if score >= 1 else "low"
        return Status(
            level=lvl,
            effective=2 if (lapsed or suspended) else lvl,
            lapsed=lapsed,
            suspended=suspended,
            lapsesAt=lapses_at,
            supervisedCount=supervised_count,
            knowledgeComplete=_signed_off(ev),
            confidence=confidence,
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
