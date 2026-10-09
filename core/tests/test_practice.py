"""practice.py — scenarios drafted from the bench (OF-BLD-013 §4).

The model is replaced by a stand-in that returns a fixed draft, so every rule
is exercised offline: a good draft is kept with every value copied from the
source it cites, and a draft that states a number, cites a source it was not
given, or names no step needing the skill is refused whole. The real model is
asked in test_practice_live.py, which `pnpm test:live` runs.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest
from fastapi.testclient import TestClient

from openferment_core import llm, practice
from openferment_core.api import app
from openferment_core.models import (
    PracticeDeposition,
    PracticeDepositionEntry,
    PracticeDepositionObservation,
    PracticeDraftRequest,
    Usage,
)


@pytest.fixture(autouse=True)
def _store(monkeypatch, tmp_path):
    monkeypatch.setattr(practice, "PATH", tmp_path / "practice.json")


def run(dep_id: str = "dep-1", protocol: str = "PR-OD-01", started: str = "2026-10-01T09:00:00Z") -> PracticeDeposition:
    return PracticeDeposition(
        id=dep_id,
        protocolId=protocol,
        startedAt=started,
        entries=[
            PracticeDepositionEntry(id="ent-1", stepId="o4", at="2026-10-01T10:00:00Z", value=1.42, unit="AU", raw="one point four two", label="OD750, flask B"),
            PracticeDepositionEntry(id="ent-2", stepId="o1", at="2026-10-01T09:30:00Z", value=91.3, unit="mg", raw="ninety one point three"),
        ],
        observations=[
            PracticeDepositionObservation(id="obs-1", stepId="o4", at="2026-10-01T10:01:00Z", raw="Read it straight away, no dilution, it was off the scale I think"),
        ],
    )


GOOD: dict[str, Any] = {
    "title": "A reading off the top of the range",
    "situation": "Partway through a growth curve, flask B read [v1] on OD750. The operator noted [v2]. The protocol step is [v3].",
    "prompt": "What do you do with this sample before you record it, and why?",
    "evidence": [
        {"ref": "entry:dep-1:ent-1", "label": "The reading as recorded"},
        {"ref": "observation:dep-1:obs-1", "label": "What the operator wrote"},
        {"ref": "step:PR-OD-01:o4", "label": "Step o4 of PR-OD-01"},
    ],
    "steps": ["PR-OD-01:o4"],
    "watchFor": ["Dilutes into the same spent medium and reads again", "Says the reading stops tracking biomass above the linear range"],
}


def stand_in(data: dict[str, Any] | None, spent: float = 0.02):
    calls: list[dict[str, Any]] = []

    def ask(**kwargs):
        calls.append(kwargs)
        return llm.Result(data=copy.deepcopy(data), model="stand-in", usage=Usage(inputTokens=900, outputTokens=300, costUsd=spent, models=["stand-in"]))

    ask.calls = calls  # type: ignore[attr-defined]
    return ask


def request(**extra) -> PracticeDraftRequest:
    return PracticeDraftRequest(skillId=extra.pop("skillId", "SK-OD"), depositions=extra.pop("depositions", [run()]))


def refused(rule: str, data: dict[str, Any] | None, req: PracticeDraftRequest | None = None) -> str:
    with pytest.raises(practice.PracticeRefused) as caught:
        practice.draft(req or request(), ask=stand_in(data))
    assert caught.value.rule == rule, f"expected {rule!r}, got {caught.value.rule!r}: {caught.value.why}"
    assert practice.read().scenarios == [], "a refused draft is not kept"
    return caught.value.why


def with_(**changes) -> dict[str, Any]:
    d = copy.deepcopy(GOOD)
    d.update(changes)
    return d


# ── a good draft ───────────────────────────────────────────────────────


def test_a_good_draft_is_kept_with_every_value_copied_from_its_source():
    s = practice.draft(request(), ask=stand_in(GOOD))
    reading, said, step = s.evidence
    assert (reading.id, reading.value, reading.unit, reading.text) == ("v1", 1.42, "AU", "OD750, flask B")
    assert reading.source.kind == "entry" and reading.source.depositionId == "dep-1" and reading.source.itemId == "ent-1"
    assert said.text == "Read it straight away, no dilution, it was off the scale I think" and said.value is None
    assert step.source.kind == "step" and step.text == practice.sources_for("SK-OD", [])["step:PR-OD-01:o4"]["text"]
    assert s.depositionIds == ["dep-1"] and [x.stepId for x in s.steps] == ["o4"]
    assert s.model == "stand-in" and s.usage.costUsd == 0.02 and s.id.startswith("ps-")
    assert [x.id for x in practice.read().scenarios] == [s.id]


def test_the_model_is_given_the_sources_and_told_the_rules():
    ask = stand_in(GOOD)
    practice.draft(request(), ask=ask)
    call = ask.calls[0]  # type: ignore[attr-defined]
    assert "NEVER WRITE A NUMBER" in call["system"]
    assert "entry:dep-1:ent-1" in call["user"] and "step:PR-OD-01:o4" in call["user"]
    assert call["schema"] is practice.DRAFT_SCHEMA


def test_identifiers_with_digits_are_words():
    s = practice.draft(request(), ask=stand_in(with_(prompt="On PR-OD-01 step o4, what does OD750 need before you record it, and why?")))
    assert "OD750" in s.prompt


# ── what a draft may cite ──────────────────────────────────────────────


def test_only_steps_that_need_the_skill_and_runs_of_their_protocols_are_sources():
    newer = [run(f"dep-{i}", started=f"2026-10-0{i}T09:00:00Z") for i in range(2, 6)]
    cip = run("dep-cip", protocol="PR-CIP-01", started="2026-10-09T09:00:00Z")
    sources = practice.sources_for("SK-OD", [run(), *newer, cip])
    steps = {r for r in sources if r.startswith("step:")}
    assert "step:PR-OD-01:o4" in steps and "step:PR-OD-01:o1" not in steps
    assert not any("dep-cip" in r for r in sources), "a run of a protocol that does not need the skill"
    assert not any(":ent-2" in r for r in sources), "an entry at a step that does not need the skill"
    shown = {r.split(":")[1] for r in sources if r.startswith(("entry:", "observation:"))}
    assert shown == {"dep-5", "dep-4", "dep-3"}, "the newest runs, and no more than three"
    assert any(r.startswith("material:PR-OD-01:") for r in sources)


def test_a_source_the_model_was_not_given_refuses_the_draft():
    bad = with_(evidence=[*GOOD["evidence"][:2], {"ref": "entry:dep-9:ent-1", "label": "Another reading"}])
    assert "not a source" in refused("unresolved", bad)
    refused("unresolved", with_(evidence=[*GOOD["evidence"][:2], {"ref": "step:PR-OD-01:o1", "label": "Taring"}]))


def test_a_marker_past_the_evidence_pane_refuses_the_draft():
    why = refused("unresolved", with_(prompt="Given [v4], what do you do next, and why?"))
    assert "[v4]" in why


# ── Rule 1 ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "A reading of 1.5 on the plate reader"),
        ("situation", "Flask B read [v1], twice what it read an hour ago."),
        ("prompt", "What is the first thing you do, and why?"),
        ("watchFor", ["Dilutes the sample tenfold"]),
    ],
)
def test_a_number_the_model_wrote_refuses_the_draft(field, value):
    why = refused("quantity", with_(**{field: value}))
    assert "evidence pane" in why


def test_a_number_in_a_label_refuses_the_draft():
    labels = copy.deepcopy(GOOD["evidence"])
    labels[0]["label"] = "Reading at 10 h"
    refused("quantity", with_(evidence=labels))


# ── shape, steps, skill ────────────────────────────────────────────────


def test_shape():
    refused("shape", None)
    refused("shape", with_(title=" "))
    refused("shape", with_(evidence=[]))
    refused("shape", with_(evidence=[GOOD["evidence"][0], GOOD["evidence"][0]], situation="Flask B read [v1].", prompt="Why?"))
    refused("shape", with_(evidence=[{"ref": f"step:PR-OD-01:o{i}", "label": "x"} for i in (3, 4)] * 4))


def test_steps_must_exist_and_one_must_need_the_skill():
    refused("steps", with_(steps=["PR-OD-01:o99"]))
    refused("steps", with_(steps=["PR-OD-01:o1"]))
    refused("steps", with_(steps=[]))


def test_an_unknown_skill_is_refused_before_any_call():
    ask = stand_in(GOOD)
    with pytest.raises(practice.PracticeRefused) as caught:
        practice.draft(request(skillId="SK-NOPE"), ask=ask)
    assert caught.value.rule == "skill" and ask.calls == []  # type: ignore[attr-defined]


def test_no_answer_from_any_model_is_unavailable_not_refused():
    def down(**_):
        raise llm.ModelUnavailable("ANTHROPIC_API_KEY is not set.")

    def declined(**_):
        raise llm.ModelRefused("bio", ["claude-opus-5-5", "claude-sonnet-5-5"], Usage(costUsd=0.01))

    with pytest.raises(practice.PracticeUnavailable):
        practice.draft(request(), ask=down)
    with pytest.raises(practice.PracticeUnavailable) as caught:
        practice.draft(request(), ask=declined)
    assert caught.value.usage.costUsd == 0.01


# ── over HTTP ──────────────────────────────────────────────────────────


def test_the_endpoints(monkeypatch):
    client = TestClient(app)
    host = {"Host": "127.0.0.1:8000"}
    body = request().model_dump()
    monkeypatch.setattr(llm, "call", stand_in(GOOD))
    r = client.post("/api/practice/draft", json=body, headers=host)
    assert r.status_code == 200, r.text
    assert r.json()["evidence"][0]["value"] == 1.42
    assert [s["id"] for s in client.get("/api/practice").json()["scenarios"]] == [r.json()["id"]]

    monkeypatch.setattr(llm, "call", stand_in(with_(prompt="What is the second thing you check?")))
    r = client.post("/api/practice/draft", json=body, headers=host)
    assert r.status_code == 422 and r.json()["detail"].startswith("quantity: ")

    def down(**_):
        raise llm.ModelUnavailable("ANTHROPIC_API_KEY is not set.")

    monkeypatch.setattr(llm, "call", down)
    r = client.post("/api/practice/draft", json=body, headers=host)
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]


# ── the tutor (§4.2) ───────────────────────────────────────────────────

from datetime import date  # noqa: E402

from openferment_core import guild  # noqa: E402
from openferment_core.competence import Competence  # noqa: E402
from openferment_core.models import GuildPerson, PracticeTurnRequest  # noqa: E402


@pytest.fixture()
def team(monkeypatch, tmp_path):
    monkeypatch.setattr(guild, "PATH", tmp_path / "guild.json")
    person = lambda pid, name, role="member", by="p-sean": GuildPerson(  # noqa: E731
        id=pid, name=name, role=role, joinedAt="2026-06-01", addedBy=by, addedAt="2026-06-01T00:00:00Z"
    )
    guild.write_person(person("p-sean", "Sean Creighton", "lead", None))
    guild.write_person(person("p-olivier", "Olivier Ndayisaba"))
    guild.write_person(person("p-qa", "Client QA", "auditor"))


def reply(move: str, text: str = "Why would that change what the reading means?", **extra) -> dict[str, Any]:
    return {"move": move, "text": text, "steps": extra.pop("steps", ["PR-OD-01:o4"]), "observed": extra.pop("observed", []), **extra}


CLOSE = reply(
    "close",
    "Look again at why step o4 dilutes into spent medium.",
    observed=[
        {"text": "Saw that the reading at [v1] was above the linear range and chose to dilute.", "steps": ["PR-OD-01:o4"]},
        {"text": "Was unsure why the diluent has to be spent medium.", "steps": ["PR-OD-01:o4"]},
    ],
)


def drafted():
    return practice.draft(request(), ask=stand_in(GOOD))


def answer(sc, text: str = "Dilute it and read again", session=None, person="p-olivier", ask=None):
    return practice.turn(
        PracticeTurnRequest(scenarioId=sc.id, sessionId=session.id if session else None, personId=person, answer=text),
        ask=ask or stand_in(reply("why")),
    )


def turn_refused(rule: str, sc, data, session=None, person="p-olivier") -> str:
    with pytest.raises(practice.PracticeRefused) as caught:
        answer(sc, session=session, person=person, ask=stand_in(data))
    assert caught.value.rule == rule, f"expected {rule!r}, got {caught.value.rule!r}: {caught.value.why}"
    return caught.value.why


def test_a_turn_keeps_the_answer_and_the_reply_together(team):
    sc = drafted()
    held = answer(sc)
    assert held.id.startswith("pt-") and held.personId == "p-olivier" and held.skillId == "SK-OD"
    assert [(t.role, t.move) for t in held.turns] == [("trainee", None), ("tutor", "why")]
    assert held.turns[0].text == "Dilute it and read again" and held.closedAt is None
    assert practice.session(held.id) == held


def test_the_tutor_sees_the_scenario_the_conversation_and_what_a_sound_answer_reaches(team):
    sc = drafted()
    held = answer(sc)
    ask = stand_in(reply("change"))
    answer(sc, "Because above the range it stops tracking biomass", session=held, ask=ask)
    user = ask.calls[0]["user"]  # type: ignore[attr-defined]
    assert "Dilute it and read again" in user and "stops tracking biomass" in user
    assert "soundAnswerReaches" in user and "[v1]" in user and "NEVER WRITE A NUMBER" in ask.calls[0]["system"]  # type: ignore[attr-defined]
    assert user.startswith("Choose your move")


def test_the_last_answer_closes_the_session_and_puts_practice_on_the_ledger(team):
    sc = drafted()
    held = answer(sc)
    held = answer(sc, "Spent medium, from the same culture", session=held, ask=stand_in(reply("change")))
    why = turn_refused("move", sc, reply("next"), session=held)
    assert "did not close" in why
    assert len(practice.session(held.id).turns) == 4, "a refused reply keeps nothing, the answer included"
    ask = stand_in(CLOSE)
    held = answer(sc, "I would read it again after diluting", session=held, ask=ask)
    assert ask.calls[0]["user"].startswith("That was the trainee's last answer")  # type: ignore[attr-defined]
    assert held.closedAt and [o.text for o in held.observed][1].startswith("Was unsure")
    entry = next(e for e in guild.read().evidence if e.id == held.evidenceId)
    assert (entry.kind, entry.personId, entry.skillId, entry.observerId) == ("scenario", "p-olivier", "SK-OD", None)
    assert entry.source.kind == "scenario" and entry.source.ref == held.id and "Was unsure" in entry.raw
    level = Competence(guild.read().evidence, guild.skills(), date.today().isoformat()).level("p-olivier", "SK-OD")
    assert level == 1, "practice is Learning, and no more"
    turn_refused("closed", sc, reply("why"), session=held)


def test_a_reply_with_a_number_keeps_nothing(team):
    sc = drafted()
    turn_refused("quantity", sc, reply("why", "Would you dilute it tenfold?"))
    turn_refused("quantity", sc, reply("change", "Suppose it read 0.9 instead; what then?"))
    assert practice.read().sessions == []


def test_what_the_tutor_cites_has_to_resolve(team):
    sc = drafted()
    turn_refused("unresolved", sc, reply("why", "Why does [v7] matter here?"))
    turn_refused("steps", sc, reply("why", steps=["PR-OD-01:o99"]))


def test_closing_says_what_was_observed(team):
    sc = drafted()
    turn_refused("move", sc, reply("close", observed=[]))
    turn_refused("quantity", sc, reply("close", observed=[{"text": "Got two of the three points", "steps": []}]))
    turn_refused("move", sc, reply("guess"))
    turn_refused("move", sc, None)


def test_who_may_practise_and_on_which_session(team):
    sc = drafted()
    turn_refused("session", sc, reply("why"), person="p-qa")
    turn_refused("session", sc, reply("why"), person="p-nobody")
    held = answer(sc)
    turn_refused("session", sc, reply("why"), session=held, person=None)
    with pytest.raises(practice.PracticeRefused) as caught:
        answer(sc, " ")
    assert caught.value.rule == "answer"
    with pytest.raises(practice.PracticeRefused) as caught:
        practice.turn(PracticeTurnRequest(scenarioId="ps-nope", answer="Dilute it"), ask=stand_in(reply("why")))
    assert caught.value.rule == "scenario"


def test_a_session_nobody_is_named_on_closes_with_nothing_on_the_ledger(team):
    sc = drafted()
    held = answer(sc, person=None)
    held = answer(sc, "Spent medium", session=held, person=None, ask=stand_in(CLOSE))
    assert held.closedAt and held.personId is None and held.evidenceId is None
    assert not any(e.kind == "scenario" for e in guild.read().evidence)


def test_an_answer_that_lost_the_race_keeps_nothing(team):
    sc = drafted()
    held = answer(sc)

    def meanwhile(**kwargs):
        # Another tab answers the same session while this one waits for the tutor.
        with practice._WRITE_LOCK:
            p = practice.read()
            s = next(x for x in p.sessions if x.id == held.id)
            s.turns.append(s.turns[0])
            practice._persist(p)
        return stand_in(reply("why"))(**kwargs)

    why = turn_refused_with(sc, held, meanwhile)
    assert "first" in why


def turn_refused_with(sc, held, ask) -> str:
    with pytest.raises(practice.PracticeRefused) as caught:
        answer(sc, "Read it again", session=held, ask=ask)
    assert caught.value.rule == "session"
    return caught.value.why


def test_the_ledger_takes_practice_only_from_a_closed_session_of_that_person(team):
    from openferment_core.models import EvidenceSource, GuildEvidence

    sc = drafted()
    held = answer(sc)

    def entry(eid: str, ref: str, person: str = "p-olivier", skill: str = "SK-OD") -> GuildEvidence:
        return GuildEvidence(id=eid, personId=person, skillId=skill, kind="scenario", at=date.today().isoformat(),
                             source=EvidenceSource(kind="scenario", ref=ref), raw="Practice")

    for e, why in [(entry("e-prac-open", held.id), "still open"), (entry("e-prac-none", "pt-nope"), "not a practice session")]:
        with pytest.raises(guild.GuildRefused) as caught:
            guild.write_evidence(e)
        assert caught.value.rule == "source" and why in caught.value.why
    held = answer(sc, "Spent medium", session=held, ask=stand_in(CLOSE))
    for e in [entry("e-prac-skill", held.id, skill="SK-DCW"), entry("e-prac-who", held.id, person="p-sean")]:
        with pytest.raises(guild.GuildRefused) as caught:
            guild.write_evidence(e)
        assert caught.value.rule == "source"
    observed = entry("e-prac-obs", held.id).model_copy(update={"observerId": "p-sean"})
    with pytest.raises(guild.GuildRefused) as caught:
        guild.write_evidence(observed)
    assert caught.value.rule == "observer"


def test_the_turn_endpoint(team, monkeypatch):
    client = TestClient(app)
    host = {"Host": "127.0.0.1:8000"}
    sc = drafted()
    monkeypatch.setattr(llm, "call", stand_in(reply("why")))
    r = client.post("/api/practice/turn", json={"scenarioId": sc.id, "personId": "p-olivier", "answer": "Dilute it"}, headers=host)
    assert r.status_code == 200, r.text
    assert [t["role"] for t in r.json()["turns"]] == ["trainee", "tutor"]
    monkeypatch.setattr(llm, "call", stand_in(reply("why", "Is that the first thing you would do?")))
    r = client.post("/api/practice/turn", json={"scenarioId": sc.id, "sessionId": r.json()["id"], "personId": "p-olivier", "answer": "Yes"}, headers=host)
    assert r.status_code == 422 and r.json()["detail"].startswith("quantity: ")
