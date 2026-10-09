"""guild.py — the competence ledger and its rules (OF-BLD-013 §1.2, §2.1, §3.1).

Every rule that keeps a bad write off the ledger has a test that presents
that write and reads the refusal's rule. Then what a good write leaves behind:
the entry as sent, stamped by the service, persisted whole; a withdrawal that
keeps the entry; a dry run that writes nothing; and the four endpoints, which
answer with the same rules over HTTP. The skills projection is the one
`pnpm export:corpus` writes; `pnpm test:core` runs that export first.
"""
from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import guild, practice
from openferment_core.api import app
from openferment_core.models import EvidenceSource, GuildEvidence, GuildPerson, GuildWithdrawal

TODAY = date.today().isoformat()


@pytest.fixture(autouse=True)
def _ledger(monkeypatch, tmp_path):
    monkeypatch.setattr(guild, "PATH", tmp_path / "guild.json")
    monkeypatch.setattr(practice, "PATH", tmp_path / "practice.json")


def person(pid: str, name: str, role: str = "member", added_by: str | None = "p-sean", **extra) -> GuildPerson:
    return GuildPerson(
        id=pid, name=name, role=role, title=extra.pop("title", ""), joinedAt="2026-06-01",
        addedBy=added_by, addedAt="2026-06-01T00:00:00Z", **extra,
    )


def entry(eid: str, person_id: str, skill: str = "SK-OD", kind: str = "witnessed", observer: str | None = "p-eric", **extra) -> GuildEvidence:
    source = extra.pop("source", None) or EvidenceSource(kind="lead" if kind == "designation" else "signoff", ref="PR-OD-01")
    return GuildEvidence(
        id=eid, personId=person_id, skillId=skill, kind=kind, outcome=extra.pop("outcome", "pass"),
        at=extra.pop("at", TODAY), observerId=observer, source=source,
        raw=extra.pop("raw", "Met every criterion at the bench"), **extra,
    )


def team() -> None:
    """Sean leads; Eric is designated an assessor on OD750; Patrick trains."""
    guild.write_person(person("p-sean", "Sean Creighton", role="lead", added_by=None))
    guild.write_person(person("p-eric", "Eric Habimana"))
    guild.write_person(person("p-patrick", "Patrick Mugisha"))
    guild.write_evidence(entry("e-desig-eric-od", "p-eric", kind="designation", observer="p-sean", raw="Founding assessor"))


def refused(rule: str, fn, *args, **kwargs) -> str:
    with pytest.raises(guild.GuildRefused) as caught:
        fn(*args, **kwargs)
    assert caught.value.rule == rule, f"expected {rule!r}, got {caught.value.rule!r}: {caught.value.why}"
    return caught.value.why


# ── the projection ─────────────────────────────────────────────────────


def test_projection_holds_the_seed_skills_and_tags():
    skills = guild.skills()
    assert "SK-OD" in skills and "SK-CIP" in skills
    assert guild.step_skills("PR-OD-01", "o4") == ["SK-OD"]
    assert guild.step_skills("PR-CIP-01", "c4") == ["SK-CIP", "SK-CAUSTIC"]
    assert guild.step_skills("PR-OD-01", "nope") is None


# ── people ─────────────────────────────────────────────────────────────


def test_the_first_person_is_the_lead_and_added_by_nobody():
    refused("role", guild.write_person, person("p-eric", "Eric Habimana", added_by=None))
    refused("added", guild.write_person, person("p-sean", "Sean Creighton", role="lead", added_by="p-sean"))
    guild.write_person(person("p-sean", "Sean Creighton", role="lead", added_by=None))
    assert [p.id for p in guild.read().people] == ["p-sean"]


def test_only_an_active_lead_adds_people():
    team()
    refused("added", guild.write_person, person("p-grace", "Grace Ingabire", added_by="p-eric"))
    refused("added", guild.write_person, person("p-grace", "Grace Ingabire", added_by="p-nobody"))
    guild.write_person(person("p-grace", "Grace Ingabire"))


@pytest.mark.parametrize("name", ["", " ", "x", "you", "Reviewer", " TEST "])
def test_a_placeholder_is_not_a_person(name):
    refused("name", guild.write_person, person("p-sean", name, role="lead", added_by=None))


def test_a_person_id_and_a_name_are_taken_once():
    team()
    refused("duplicate", guild.write_person, person("p-eric2", "eric habimana"))
    refused("duplicate", guild.write_person, person("P-Upper", "Someone Else"))


def test_a_change_is_made_by_a_lead_and_keeps_what_was_first_written():
    team()
    change = person("p-patrick", "Patrick Mugisha", title="Operator", updatedBy="p-eric")
    refused("added", guild.write_person, change)
    stored = guild.write_person(change.model_copy(update={"updatedBy": "p-sean", "addedBy": "p-eric", "joinedAt": "2020-01-01"}))
    assert stored.title == "Operator" and stored.addedBy == "p-sean" and stored.joinedAt == "2026-06-01"
    assert stored.updatedBy == "p-sean" and stored.updatedAt


def test_the_ledger_never_loses_its_last_lead():
    team()
    demote = person("p-sean", "Sean Creighton", role="member", added_by=None, updatedBy="p-sean")
    refused("role", guild.write_person, demote)
    refused("role", guild.write_person, demote.model_copy(update={"role": "lead", "active": False}))


# ── evidence ───────────────────────────────────────────────────────────


def test_a_good_signoff_is_stored_whole_and_stamped():
    team()
    stored = guild.write_evidence(entry("e-check-1", "p-patrick", raw="  Inverted, blanked on spent medium  "))
    assert stored.raw == "Inverted, blanked on spent medium"
    assert stored.recordedAt and stored.withdrawnAt is None
    on_disk = json.loads(guild.PATH.read_text())
    assert [e["id"] for e in on_disk["evidence"]] == ["e-desig-eric-od", "e-check-1"]


def test_dry_run_runs_every_rule_and_writes_nothing():
    team()
    before = guild.PATH.read_text()
    guild.write_evidence(entry("e-check-1", "p-patrick"), dry_run=True)
    assert guild.PATH.read_text() == before
    refused("observer", guild.write_evidence, entry("e-check-2", "p-patrick", observer=None), dry_run=True)


def test_unknown_skill_and_person():
    team()
    refused("skill", guild.write_evidence, entry("e-try-1", "p-patrick", skill="SK-NOPE"))
    refused("person", guild.write_evidence, entry("e-try-2", "p-ghost"))


def test_an_auditor_holds_no_skills():
    team()
    guild.write_person(person("p-qa", "Client QA", role="auditor"))
    refused("role", guild.write_evidence, entry("e-try-1", "p-qa"))


def test_practice_comes_from_a_practice_session():
    team()
    refused("source", guild.write_evidence, entry("e-try-scenario", "p-patrick", kind="scenario"))
    refused("source", guild.write_evidence, entry("e-try-scenario2", "p-patrick", kind="scenario", observer=None,
                                                  source=EvidenceSource(kind="scenario", ref="pt-nope")))


def test_a_kind_comes_from_its_own_source():
    team()
    refused("source", guild.write_evidence, entry("e-try-1", "p-patrick", source=EvidenceSource(kind="lesson", ref="l0-1")))
    refused("source", guild.write_evidence, entry("e-try-2", "p-patrick", kind="designation", observer="p-sean", source=EvidenceSource(kind="signoff", ref="x")))


def test_a_named_step_has_to_need_the_skill():
    team()
    refused("source", guild.write_evidence, entry("e-try-1", "p-patrick", source=EvidenceSource(kind="signoff", ref="PR-OD-01", stepId="o99")))
    why = refused("source", guild.write_evidence, entry("e-try-2", "p-patrick", source=EvidenceSource(kind="signoff", ref="PR-OD-01", stepId="o1")))
    assert "SK-DCW" in why
    guild.write_evidence(entry("e-try-3", "p-patrick", source=EvidenceSource(kind="signoff", ref="PR-OD-01", stepId="o4")))


def test_observer_rules():
    team()
    refused("observer", guild.write_evidence, entry("e-try-1", "p-patrick", observer=None))
    refused("observer", guild.write_evidence, entry("e-try-2", "p-patrick", observer="p-ghost"))
    guild.write_evidence(entry("e-desig-pat", "p-patrick", kind="designation", observer="p-sean", raw="designated"))
    refused("observer", guild.write_evidence, entry("e-try-3", "p-patrick", observer="p-patrick"))


def test_a_signoff_needs_an_assessor_on_that_skill():
    team()
    refused("authority", guild.write_evidence, entry("e-try-1", "p-patrick", skill="SK-CIP"))
    refused("authority", guild.write_evidence, entry("e-try-2", "p-patrick", observer="p-sean"))


def test_only_the_lead_designates():
    team()
    refused("authority", guild.write_evidence, entry("e-try-1", "p-patrick", kind="designation", observer="p-eric", raw="designated"))


def test_a_withdrawn_designation_stops_granting_authority():
    team()
    guild.withdraw(GuildWithdrawal(evidenceId="e-desig-eric-od", by="p-sean", at=TODAY, reason="Left the team"))
    refused("authority", guild.write_evidence, entry("e-try-1", "p-patrick"))


def test_only_a_witnessed_check_can_fail():
    team()
    guild.write_evidence(entry("e-fail-1", "p-patrick", outcome="fail", raw="Read a standing sample"))
    refused("outcome", guild.write_evidence, entry("e-fail-2", "p-patrick", kind="supervised", outcome="fail"))


def test_notes_and_dates():
    team()
    refused("note", guild.write_evidence, entry("e-try-1", "p-patrick", raw="  "))
    refused("date", guild.write_evidence, entry("e-try-2", "p-patrick", at="last tuesday"))
    later = (date.today() + timedelta(days=3)).isoformat()
    refused("date", guild.write_evidence, entry("e-try-3", "p-patrick", at=later))
    guild.write_evidence(entry("e-try-4", "p-patrick", at="2026-03-02", raw="Backfilled from the paper matrix"))


def test_entry_ids_are_shaped_and_taken_once():
    team()
    guild.write_evidence(entry("e-check-1", "p-patrick"))
    refused("duplicate", guild.write_evidence, entry("e-check-1", "p-patrick"))
    refused("duplicate", guild.write_evidence, entry("bad id", "p-patrick"))


# ── withdrawal ─────────────────────────────────────────────────────────


def test_a_withdrawal_keeps_the_entry_and_says_who_and_why():
    team()
    guild.write_evidence(entry("e-check-1", "p-patrick"))
    stored = guild.withdraw(GuildWithdrawal(evidenceId="e-check-1", by="p-eric", at=TODAY, reason="Wrong person"))
    assert stored.withdrawnBy == "p-eric" and stored.withdrawReason == "Wrong person"
    kept = [e for e in guild.read().evidence if e.id == "e-check-1"]
    assert len(kept) == 1 and kept[0].withdrawnAt == TODAY


def test_withdrawal_rules():
    team()
    guild.write_evidence(entry("e-check-1", "p-patrick"))
    refused("evidence", guild.withdraw, GuildWithdrawal(evidenceId="e-nope-1", by="p-sean", at=TODAY, reason="x y"))
    refused("authority", guild.withdraw, GuildWithdrawal(evidenceId="e-check-1", by="p-patrick", at=TODAY, reason="mine"))
    refused("note", guild.withdraw, GuildWithdrawal(evidenceId="e-check-1", by="p-sean", at=TODAY, reason=" "))
    guild.withdraw(GuildWithdrawal(evidenceId="e-check-1", by="p-sean", at=TODAY, reason="Lead correction"))
    refused("evidence", guild.withdraw, GuildWithdrawal(evidenceId="e-check-1", by="p-sean", at=TODAY, reason="again"))


# ── concurrency ────────────────────────────────────────────────────────


def test_concurrent_writes_all_land():
    team()
    errors: list[Exception] = []

    def post(i: int) -> None:
        try:
            guild.write_evidence(entry(f"e-par-{i:04d}", "p-patrick", kind="supervised", raw=f"Run {i}"))
        except Exception as e:  # pragma: no cover - the assertion below reports it
            errors.append(e)

    threads = [threading.Thread(target=post, args=(i,)) for i in range(24)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    ids = {e.id for e in guild.read().evidence}
    assert all(f"e-par-{i:04d}" in ids for i in range(24))


# ── over HTTP ──────────────────────────────────────────────────────────


def test_the_endpoints():
    client = TestClient(app)
    empty = client.get("/api/guild").json()
    assert (empty["version"], empty["people"], empty["evidence"]) == (1, [], [])
    assert empty["policy"]["criticalGate"] == "enforce", "a fresh ledger carries the default policy"

    lead = person("p-sean", "Sean Creighton", role="lead", added_by=None).model_dump()
    assert client.post("/api/guild/people", json=lead).status_code == 200
    bad = person("p-eric", "you").model_dump()
    r = client.post("/api/guild/people", json=bad)
    assert r.status_code == 422 and r.json()["detail"].startswith("name: ")
    for p in (person("p-eric", "Eric Habimana"), person("p-patrick", "Patrick Mugisha")):
        assert client.post("/api/guild/people", json=p.model_dump()).status_code == 200

    desig = entry("e-desig-eric-od", "p-eric", kind="designation", observer="p-sean", raw="Founding assessor").model_dump()
    assert client.post("/api/guild/evidence", json=desig).status_code == 200

    asked = client.post("/api/guild/check", json=entry("e-check-1", "p-patrick", skill="SK-CIP").model_dump())
    assert asked.status_code == 200 and asked.json()["ok"] is False and asked.json()["rule"] == "authority"
    assert client.post("/api/guild/check", json=entry("e-check-1", "p-patrick").model_dump()).json()["ok"] is True

    stored = client.post("/api/guild/evidence", json=entry("e-check-1", "p-patrick").model_dump())
    assert stored.status_code == 200 and stored.json()["recordedAt"]
    gone = client.post(
        "/api/guild/withdraw",
        json=GuildWithdrawal(evidenceId="e-check-1", by="p-sean", at=TODAY, reason="Test entry").model_dump(),
    )
    assert gone.status_code == 200 and gone.json()["withdrawnBy"] == "p-sean"

    ledger = client.get("/api/guild").json()
    assert [p["id"] for p in ledger["people"]] == ["p-sean", "p-eric", "p-patrick"]
    assert [e["id"] for e in ledger["evidence"]] == ["e-desig-eric-od", "e-check-1"]


# ── runs from Deposition (OF-BLD-013 §2) ───────────────────────────────


def run(eid: str, person_id: str, kind: str, observer: str | None = None, step: str = "o4", **extra) -> GuildEvidence:
    return entry(
        eid, person_id, kind=kind, observer=observer,
        source=EvidenceSource(kind="deposition", ref="PR-OD-01", stepId=step),
        raw=extra.pop("raw", f"Run dep-1: step {step}"), **extra,
    )


def qualify(person_id: str) -> None:
    """Train, supervise three times and check someone on OD750, all signed by Eric."""
    guild.write_evidence(entry(f"e-q-{person_id}-k", person_id, kind="knowledge", raw="Briefed"))
    for i in range(3):
        guild.write_evidence(entry(f"e-q-{person_id}-s{i}", person_id, kind="supervised", raw="Beside them"))
    guild.write_evidence(entry(f"e-q-{person_id}-w", person_id, kind="witnessed"))


def test_a_run_alone_needs_the_operator_to_hold_the_skill():
    team()
    why = refused("authority", guild.write_evidence, run("e-run-0001", "p-patrick", "independent"))
    assert "deviation" in why
    qualify("p-patrick")
    stored = guild.write_evidence(run("e-run-0002", "p-patrick", "independent"))
    assert stored.observerId is None and stored.source.kind == "deposition"


def test_an_assessor_holds_the_skill_they_assess():
    team()
    guild.write_evidence(run("e-run-0001", "p-eric", "independent"))


def test_the_operators_own_record_names_no_observer():
    team()
    refused("observer", guild.write_evidence, run("e-run-0001", "p-eric", "independent", observer="p-sean"))
    refused("observer", guild.write_evidence, run("e-run-0002", "p-patrick", "deviation", observer="p-eric"))


def test_a_deviation_is_kept_whoever_ran_the_step():
    team()
    stored = guild.write_evidence(run("e-run-0001", "p-patrick", "deviation", raw="Ran o4 without a cosigner"))
    assert stored.kind == "deviation"


def test_a_cosigner_has_to_hold_the_skill():
    team()
    guild.write_person(person("p-grace", "Grace Ingabire"))
    refused("authority", guild.write_evidence, run("e-run-0001", "p-patrick", "supervised", observer="p-grace"))
    qualify("p-grace")
    guild.write_evidence(run("e-run-0002", "p-patrick", "supervised", observer="p-grace"))
    refused("observer", guild.write_evidence, run("e-run-0003", "p-grace", "supervised", observer="p-grace"))


def test_a_lapsed_cosigner_does_not_hold_the_skill():
    team()
    guild.write_person(person("p-grace", "Grace Ingabire"))
    long_ago = (date.today() - timedelta(days=200)).isoformat()
    guild.write_evidence(entry("e-old-k", "p-grace", kind="knowledge", raw="Briefed", at=long_ago))
    for i in range(3):
        guild.write_evidence(entry(f"e-old-s{i}", "p-grace", kind="supervised", raw="Beside them", at=long_ago))
    guild.write_evidence(entry("e-old-w", "p-grace", kind="witnessed", at=long_ago))
    why = refused("authority", guild.write_evidence, run("e-run-0001", "p-patrick", "supervised", observer="p-grace"))
    assert "does not hold" in why


def test_a_run_names_its_step_and_the_step_needs_the_skill():
    team()
    refused("source", guild.write_evidence, entry("e-run-0001", "p-eric", kind="independent", observer=None,
                                                  source=EvidenceSource(kind="deposition", ref="PR-OD-01")))
    refused("source", guild.write_evidence, run("e-run-0002", "p-eric", "independent", step="o1"))
    refused("source", guild.write_evidence, entry("e-run-0003", "p-eric", kind="independent", observer=None))


# ── lessons from Primer (OF-BLD-013 §3.1) ──────────────────────────────


def lesson(eid: str, person_id: str, skill: str = "SK-OD", ref: str = "l6-1", **extra) -> GuildEvidence:
    return entry(
        eid, person_id, skill=skill, kind="knowledge", observer=extra.pop("observer", None),
        source=EvidenceSource(kind="lesson", ref=ref),
        raw=extra.pop("raw", f"Lesson {ref}: every checkpoint question answered correctly"), **extra,
    )


def test_the_projection_says_which_lessons_count_toward_which_skills():
    assert guild.lesson_skills("l6-1") == ["SK-OD", "SK-DCW"]
    assert guild.lesson_skills("l0-1") == []
    assert guild.lesson_skills("nope") is None


def test_a_lesson_passed_is_knowledge_with_nobody_watching():
    team()
    stored = guild.write_evidence(lesson("e-les-0001", "p-patrick"))
    assert stored.observerId is None and stored.source.kind == "lesson" and stored.recordedAt
    why = refused("observer", guild.write_evidence, lesson("e-les-0002", "p-patrick", observer="p-eric"))
    assert "training sign-off" in why


def test_a_lesson_counts_only_toward_the_skills_it_names():
    team()
    refused("source", guild.write_evidence, lesson("e-les-0001", "p-patrick", skill="SK-CIP"))
    refused("source", guild.write_evidence, lesson("e-les-0002", "p-patrick", ref="l0-1"))
    why = refused("source", guild.write_evidence, lesson("e-les-0003", "p-patrick", ref="l9-9"))
    assert "no lesson" in why


def test_a_lesson_writes_knowledge_and_nothing_else():
    team()
    passed = lesson("e-les-0001", "p-patrick")
    refused("source", guild.write_evidence, passed.model_copy(update={"kind": "supervised"}))
    refused("source", guild.write_evidence, passed.model_copy(update={"kind": "witnessed"}))
    refused("outcome", guild.write_evidence, passed.model_copy(update={"outcome": "fail"}))


def test_a_lesson_puts_someone_at_learning_and_no_further():
    team()
    guild.write_evidence(lesson("e-les-0001", "p-patrick"))
    level = lambda: guild.Competence(guild.read().evidence, guild.skills(), TODAY).level("p-patrick", "SK-OD")  # noqa: E731
    assert level() == 1
    guild.write_evidence(entry("e-brief-0001", "p-patrick", kind="knowledge", raw="Talked the steps back"))
    assert level() == 2


# ── what the review found (OF-BLD-013 §3.4) ────────────────────────────


def test_an_auditor_signs_nothing_whatever_they_held_before():
    team()
    qualify("p-patrick")
    guild.write_evidence(entry("e-desig-pat-od", "p-patrick", kind="designation", observer="p-sean", raw="Second assessor"))
    guild.write_person(person("p-patrick", "Patrick Mugisha", role="auditor", updatedBy="p-sean"))
    guild.write_person(person("p-grace", "Grace Ingabire"))
    why = refused("authority", guild.write_evidence, entry("e-aud-0001", "p-grace", observer="p-patrick"))
    assert "auditor" in why
    refused("authority", guild.write_evidence, run("e-aud-0002", "p-grace", "supervised", observer="p-patrick"))


def test_a_run_is_judged_on_the_day_it_was_run():
    team()
    guild.write_person(person("p-grace", "Grace Ingabire"))
    back = lambda n: (date.today() - timedelta(days=n)).isoformat()  # noqa: E731
    guild.write_evidence(entry("e-day-k", "p-grace", kind="knowledge", raw="Briefed", at=back(80)))
    for i in range(3):
        guild.write_evidence(entry(f"e-day-s{i}", "p-grace", kind="supervised", raw="Beside them", at=back(79 - i)))
    guild.write_evidence(entry("e-day-w", "p-grace", kind="witnessed", at=back(70)))
    # Qualified until back(10): a run alone dated today, after the window
    # closed, is refused, and the same run dated back(15), posted today, stands.
    refused("authority", guild.write_evidence, run("e-day-run2", "p-grace", "independent", at=back(0)))
    guild.write_evidence(run("e-day-run1", "p-grace", "independent", at=back(15)))
    # And a check failed after the run day does not reach back to it.
    guild.write_evidence(entry("e-day-fail", "p-grace", kind="witnessed", outcome="fail", at=back(5)))
    guild.write_evidence(run("e-day-run3", "p-grace", "independent", at=back(12)))


def test_the_sample_team_passes_the_service_rules():
    """The invented team is built in TypeScript and checked there only against
    the offline fallback. Replayed here, in ledger order, through every rule."""
    fixtures = json.loads((Path(__file__).parent / "fixtures" / "competence.json").read_text(encoding="utf-8"))
    case = next(c for c in fixtures["cases"] if c["name"] == "sample, its own day")
    for p in case["people"]:
        guild.write_person(GuildPerson.model_validate(p))
    for e in sorted(case["evidence"], key=lambda e: (e["at"][:10], e["kind"] != "designation", e["id"])):
        guild.write_evidence(GuildEvidence.model_validate(e))
    assert len(guild.read().evidence) == len(case["evidence"])


# ── the lead's policy (OF-BLD-013 §5.1) ────────────────────────────────

from openferment_core.models import GuildPolicy  # noqa: E402


def test_a_ledger_without_a_policy_reads_with_the_default():
    team()
    p = guild.read().policy
    assert (p.routineGate, p.criticalGate, p.checksPerQuarter) == ("advise", "enforce", 1)


def test_only_an_active_lead_sets_the_policy():
    team()
    refused("authority", guild.write_policy, GuildPolicy(routineGate="enforce", updatedBy="p-eric"))
    refused("authority", guild.write_policy, GuildPolicy(routineGate="enforce", updatedBy=None))
    refused("policy", guild.write_policy, GuildPolicy(checksPerQuarter=13, updatedBy="p-sean"))
    stored = guild.write_policy(GuildPolicy(routineGate="enforce", criticalGate="enforce", checksPerQuarter=2, updatedBy="p-sean"))
    assert stored.updatedAt and guild.read().policy.checksPerQuarter == 2
    assert guild.read().people and guild.read().evidence, "setting the policy keeps everything else"


def test_the_policy_endpoint():
    team()
    client = TestClient(app)
    host = {"Host": "127.0.0.1:8000"}
    r = client.post("/api/guild/policy", json={"routineGate": "advise", "criticalGate": "advise", "checksPerQuarter": 0, "updatedBy": "p-sean"}, headers=host)
    assert r.status_code == 200 and r.json()["criticalGate"] == "advise"
    r = client.post("/api/guild/policy", json={"routineGate": "advise", "criticalGate": "enforce", "checksPerQuarter": 1, "updatedBy": "p-patrick"}, headers=host)
    assert r.status_code == 422 and r.json()["detail"].startswith("authority: ")
    assert client.get("/api/guild").json()["policy"]["criticalGate"] == "advise"
