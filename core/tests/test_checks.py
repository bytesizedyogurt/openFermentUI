"""checks.py — proposals, the queue, and a run at the bench (OF-BLD-013 §5.2).

The ranking first: every pair and every proposal the TypeScript reference
made on the fixture's ledgers has to come out the same here. Then each rule
of the queue, presented with the write it should refuse, and a run that puts
witnessed entries on the ledger with the check as their source.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import checks, guild, practice
from openferment_core.api import app
from openferment_core.competence import Competence
from openferment_core.models import (
    CheckDismiss,
    CheckNote,
    CheckRecord,
    CheckRequest,
    CheckResult,
    CheckSchedule,
    EvidenceSource,
    Guild,
    GuildEvidence,
    GuildPerson,
    GuildPolicy,
)

FIXTURE = Path(__file__).parent / "fixtures" / "competence.json"
TODAY = date.today().isoformat()


@pytest.fixture(autouse=True)
def _files(monkeypatch, tmp_path):
    monkeypatch.setattr(guild, "PATH", tmp_path / "guild.json")
    monkeypatch.setattr(checks, "PATH", tmp_path / "checks.json")
    monkeypatch.setattr(practice, "PATH", tmp_path / "practice.json")


# ── the ranking, against the reference ─────────────────────────────────


def _cases():
    data = json.loads(FIXTURE.read_text())
    skills = {s["id"]: s for s in data["skills"]}
    for case in data["cases"]:
        ledger = Guild(
            people=[GuildPerson(**p) for p in case["people"]],
            evidence=[GuildEvidence(**e) for e in case["evidence"]],
            policy=GuildPolicy(**case["policy"]) if case.get("policy") else GuildPolicy(),
        )
        yield case, ledger, skills


def test_every_pair_and_proposal_matches_the_reference():
    compared = 0
    for case, ledger, skills in _cases():
        pairs = checks.rank_pairs(ledger, skills, case["today"])
        assert pairs == case["pairs"], f"{case['name']}: pairs differ"
        assert checks.propose_from(ledger, skills, case["today"]) == case["proposals"], f"{case['name']}: proposals differ"
        compared += len(pairs)
    assert compared > 50


def test_a_covered_pair_is_not_proposed_again():
    case, ledger, skills = next(_cases())
    first = checks.propose_from(ledger, skills, case["today"])
    cover = {f"{p['personId']}|{s}" for p in first for s in p["skillIds"]}
    again = checks.propose_from(ledger, skills, case["today"], cover)
    assert not {f"{p['personId']}|{s}" for p in again for s in p["skillIds"]} & cover


# ── the queue ──────────────────────────────────────────────────────────


def person(pid: str, name: str, role: str = "member", added_by: str | None = "p-sean") -> GuildPerson:
    return GuildPerson(id=pid, name=name, role=role, joinedAt="2026-01-01", addedBy=added_by, addedAt="2026-01-01T00:00:00Z")


def entry(eid: str, pid: str, kind: str, at: str, skill: str = "SK-OD", observer: str | None = "p-eric", **extra) -> GuildEvidence:
    source = extra.pop("source", None) or EvidenceSource(kind="lead" if kind == "designation" else "signoff", ref="PR-OD-01")
    return GuildEvidence(id=eid, personId=pid, skillId=skill, kind=kind, at=at, observerId=observer, source=source, raw="seen", **extra)


@pytest.fixture()
def team():
    """Sean leads; Eric assesses OD750; Patrick has done his supervised runs."""
    guild.write_person(person("p-sean", "Sean Creighton", "lead", None))
    guild.write_person(person("p-eric", "Eric Habimana"))
    guild.write_person(person("p-patrick", "Patrick Mugisha"))
    guild.write_person(person("p-qa", "Client QA", "auditor"))
    day = (date.today() - timedelta(days=20)).isoformat()
    guild.write_evidence(entry("e-desig-eric", "p-eric", "designation", day, observer="p-sean"))
    guild.write_evidence(entry("e-pat-k", "p-patrick", "knowledge", day))
    for i in range(3):
        guild.write_evidence(entry(f"e-pat-s{i}", "p-patrick", "supervised", day))


def refused(rule: str, fn, *args) -> str:
    with pytest.raises(checks.CheckRefused) as caught:
        fn(*args)
    assert caught.value.rule == rule, f"expected {rule!r}, got {caught.value.rule!r}: {caught.value.why}"
    return caught.value.why


def all_ok(check_id: str, by: str = "p-eric", meets=lambda i: True, note: str = "Read every sample after inverting it") -> CheckRecord:
    n = len(guild.skills()["SK-OD"]["mastery"])
    return CheckRecord(
        by=by,
        at=TODAY,
        results=[CheckResult(skillId="SK-OD", criterion=i, meets=meets(i), note="") for i in range(n)],
        notes=[CheckNote(skillId="SK-OD", text=note)],
    )


def test_the_nightly_ranking_proposes_and_never_twice(team):
    made = checks.propose(None)
    assert [(c.personId, c.skillIds, c.state) for c in made] == [("p-patrick", ["SK-OD"], "proposed")]
    assert made[0].reasons[0].kind == "ready" and made[0].proposedBy is None
    assert checks.propose(None) == [], "an open check covers the pair"
    assert checks.main(["propose"]) == 0


def test_who_may_run_the_ranking(team):
    refused("authority", checks.propose, "p-patrick")
    refused("authority", checks.propose, "p-qa")
    assert checks.propose("p-sean") and True


def test_asking_for_a_check(team):
    made = checks.request(CheckRequest(personId="p-patrick", skillIds=["SK-OD"], by="p-patrick"))
    assert made.reasons[0].kind == "requested" and "the person themselves" in made.reasons[0].text
    refused("duplicate", checks.request, CheckRequest(personId="p-patrick", skillIds=["SK-OD"], by="p-patrick"))
    refused("authority", checks.request, CheckRequest(personId="p-patrick", skillIds=["SK-DCW"], by="p-sean"))
    refused("skill", checks.request, CheckRequest(personId="p-patrick", skillIds=["SK-NOPE"], by="p-patrick"))
    refused("person", checks.request, CheckRequest(personId="p-qa", skillIds=["SK-OD"], by="p-eric"))
    assert checks.propose(None) == [], "a check asked for covers the pair the ranking would propose"


def test_scheduling_and_dismissing(team):
    (c,) = checks.propose(None)
    refused("authority", checks.schedule, c.id, CheckSchedule(by="p-patrick", scheduledFor=TODAY))
    refused("authority", checks.schedule, c.id, CheckSchedule(by="p-sean", scheduledFor=TODAY))
    refused("date", checks.schedule, c.id, CheckSchedule(by="p-eric", scheduledFor="soon"))
    s = checks.schedule(c.id, CheckSchedule(by="p-eric", scheduledFor=TODAY))
    assert (s.state, s.assessorId, s.scheduledFor) == ("scheduled", "p-eric", TODAY)
    refused("note", checks.dismiss, c.id, CheckDismiss(by="p-eric", reason=" "))
    refused("authority", checks.dismiss, c.id, CheckDismiss(by="p-patrick", reason="Not now"))
    d = checks.dismiss(c.id, CheckDismiss(by="p-sean", reason="Checked him on Monday on paper"))
    assert d.state == "dismissed" and d.dismissedBy == "p-sean" and d.closedAt
    refused("state", checks.schedule, c.id, CheckSchedule(by="p-eric", scheduledFor=TODAY))
    refused("check", checks.dismiss, "ck-nope", CheckDismiss(by="p-sean", reason="x y"))


def test_a_run_calls_every_criterion_and_says_what_was_seen(team):
    (c,) = checks.propose(None)
    good = all_ok(c.id)
    refused("authority", checks.record, c.id, all_ok(c.id, by="p-sean"))
    refused("results", checks.record, c.id, good.model_copy(update={"results": good.results[:-1]}))
    refused("results", checks.record, c.id, good.model_copy(update={"results": [*good.results, good.results[0]]}))
    bad = good.model_copy(update={"results": [*good.results[:-1], CheckResult(skillId="SK-OD", criterion=99, meets=True)]})
    refused("results", checks.record, c.id, bad)
    refused("note", checks.record, c.id, all_ok(c.id, note=" "))
    refused("date", checks.record, c.id, good.model_copy(update={"at": (date.today() + timedelta(days=5)).isoformat()}))
    assert guild.read().evidence[-1].kind == "supervised", "nothing refused reached the ledger"

    done = checks.record(c.id, good)
    (e,) = [x for x in guild.read().evidence if x.id in done.evidenceIds]
    assert (e.kind, e.outcome, e.observerId, e.source.kind, e.source.ref) == ("witnessed", "pass", "p-eric", "check", c.id)
    assert e.raw == "Read every sample after inverting it"
    assert done.state == "done" and len(done.results) == len(good.results)
    level = Competence(guild.read().evidence, guild.skills(), TODAY).level("p-patrick", "SK-OD")
    assert level == 3, "a passed check on a ready trainee qualifies them"
    refused("state", checks.record, c.id, good)


def test_one_criterion_needing_work_fails_the_skill(team):
    (c,) = checks.propose(None)
    done = checks.record(c.id, all_ok(c.id, meets=lambda i: i != 1))
    (e,) = [x for x in guild.read().evidence if x.id in done.evidenceIds]
    assert e.outcome == "fail"


def test_the_ledger_takes_a_witnessed_entry_from_an_open_check_of_that_person_only(team):
    (c,) = checks.propose(None)
    src = EvidenceSource(kind="check", ref=c.id)

    def write(eid, **kw):
        return guild.write_evidence(entry(eid, kw.pop("pid", "p-patrick"), "witnessed", TODAY, source=kw.pop("source", src), **kw))

    for kw, rule in [
        ({"source": EvidenceSource(kind="check", ref="ck-nope")}, "source"),
        ({"pid": "p-sean"}, "source"),
        ({"skill": "SK-DCW"}, "source"),
        ({"observer": "p-sean"}, "authority"),
    ]:
        with pytest.raises(guild.GuildRefused) as caught:
            write(f"e-try-{rule}-{len(kw)}{list(kw)[0]}", **kw)
        assert caught.value.rule == rule, (kw, caught.value)
    write("e-direct-1")
    with pytest.raises(guild.GuildRefused) as caught:
        write("e-direct-2")
    assert caught.value.rule == "duplicate"


def test_the_endpoints(team):
    client = TestClient(app)
    host = {"Host": "127.0.0.1:8000"}
    r = client.post("/api/guild/checks/propose", json={"by": "p-eric"}, headers=host)
    assert r.status_code == 200 and len(r.json()) == 1
    cid = r.json()[0]["id"]
    r = client.post(f"/api/guild/checks/{cid}/schedule", json={"by": "p-patrick", "scheduledFor": TODAY}, headers=host)
    assert r.status_code == 422 and r.json()["detail"].startswith("authority: ")
    r = client.post(f"/api/guild/checks/{cid}/record", json=all_ok(cid).model_dump(), headers=host)
    assert r.status_code == 200 and r.json()["state"] == "done"
    assert [c["state"] for c in client.get("/api/guild/checks").json()["checks"]] == ["done"]


# ── briefs (§5.3) ──────────────────────────────────────────────────────

import copy  # noqa: E402
from typing import Any  # noqa: E402

from openferment_core import llm  # noqa: E402
from openferment_core.models import Usage  # noqa: E402

BRIEF: dict[str, Any] = {
    "steps": ["PR-OD-01:o3", "PR-OD-01:o4"],
    "criteria": [{"skillId": "SK-OD", "index": 0}, {"skillId": "SK-OD", "index": 2}],
    "questions": ["Before reading, what do you do with the sample, and why?", "What do you blank against on this protocol?"],
}


def stand_in(data, calls=None):
    def ask(**kw):
        if calls is not None:
            calls.append(kw)
        return llm.Result(data=copy.deepcopy(data), model="stand-in", usage=Usage(costUsd=0.01, models=["stand-in"]))

    return ask


def test_a_brief_is_kept_on_the_check_and_names_nobody(team):
    (c,) = checks.propose(None)
    calls: list = []
    made = checks.brief(c.id, "p-eric", ask=stand_in(BRIEF, calls))
    assert made.brief and [s.stepId for s in made.brief.steps] == ["o3", "o4"] and made.brief.criteria[1].index == 2
    assert checks.get(c.id).brief == made.brief and made.brief.usage.costUsd == 0.01
    user = calls[0]["user"]
    assert "Patrick" not in user and "p-patrick" not in user, "the model is never told who is checked"
    assert "NEVER WRITE A NUMBER" in calls[0]["system"]


@pytest.mark.parametrize(
    "change",
    [
        {"questions": ["Read it again twice?"]},
        {"questions": ["What if it reads pH7?"]},
        {"questions": ["Given [v1], what next?"]},
        {"steps": ["PR-OD-01:o99"]},
        {"steps": ["PR-OD-01:o1"]},
        {"criteria": [{"skillId": "SK-OD", "index": 99}]},
        {"criteria": [{"skillId": "SK-DCW", "index": 0}]},
        {"criteria": []},
        {"questions": []},
    ],
)
def test_a_brief_that_breaks_a_rule_is_refused_whole(team, change):
    (c,) = checks.propose(None)
    with pytest.raises(checks.CheckRefused) as caught:
        checks.brief(c.id, "p-eric", ask=stand_in({**BRIEF, **change}))
    assert caught.value.rule == "brief"
    assert checks.get(c.id).brief is None
    for said in ("twice", "pH7", "o99", "99"):
        assert said not in caught.value.why, "a refusal never repeats what the model wrote"


def test_who_may_ask_for_a_brief_and_when(team):
    (c,) = checks.propose(None)
    refused("authority", lambda: checks.brief(c.id, "p-patrick", ask=stand_in(BRIEF)))
    checks.dismiss(c.id, CheckDismiss(by="p-sean", reason="Seen on Monday"))
    refused("state", lambda: checks.brief(c.id, "p-eric", ask=stand_in(BRIEF)))


def test_no_model_is_unavailable_and_the_nightly_job_waits_without_a_key(team, monkeypatch, capsys):
    (c,) = checks.propose(None)

    def down(**_):
        raise llm.ModelUnavailable("ANTHROPIC_API_KEY is not set.")

    with pytest.raises(checks.BriefUnavailable):
        checks.brief(c.id, "p-eric", ask=down)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert checks.main(["brief", "--missing"]) == 0
    assert "wait" in capsys.readouterr().out
    client = TestClient(app)
    monkeypatch.setattr(llm, "call", down)
    r = client.post(f"/api/guild/checks/{c.id}/brief", json={"by": "p-eric"}, headers={"Host": "127.0.0.1:8000"})
    assert r.status_code == 503
    monkeypatch.setattr(llm, "call", stand_in(BRIEF))
    r = client.post(f"/api/guild/checks/{c.id}/brief", json={"by": "p-eric"}, headers={"Host": "127.0.0.1:8000"})
    assert r.status_code == 200 and r.json()["brief"]["questions"]
