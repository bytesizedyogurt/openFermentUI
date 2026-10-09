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
