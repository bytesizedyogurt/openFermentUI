"""Practice against the real model (OF-BLD-013 §4).

Marked `live`: needs a key and spends money, one draft call per test.
Excluded from `pnpm verify`; run with `pnpm test:live`. Prints what each call
cost, so the price of a practice scenario is a number somebody has seen.
"""
from __future__ import annotations

import os

import pytest

from openferment_core import practice
from openferment_core.models import (
    PracticeDeposition,
    PracticeDepositionEntry,
    PracticeDepositionObservation,
    PracticeDraftRequest,
    PracticeTurnRequest,
)

pytestmark = pytest.mark.live

needs_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live tests need ANTHROPIC_API_KEY in core/.env",
)


@pytest.fixture(autouse=True)
def _store(monkeypatch, tmp_path):
    monkeypatch.setattr(practice, "PATH", tmp_path / "practice.json")


def bench_run() -> PracticeDeposition:
    """A run as an operator might have recorded it: one reading above the
    linear range, and a note saying it was read without dilution."""
    return PracticeDeposition(
        id="dep-live",
        protocolId="PR-OD-01",
        startedAt="2026-10-01T09:00:00Z",
        entries=[PracticeDepositionEntry(id="ent-1", stepId="o4", at="2026-10-01T10:00:00Z", value=1.42, unit="AU", raw="one point four two", label="OD750, flask B")],
        observations=[PracticeDepositionObservation(id="obs-1", stepId="o4", at="2026-10-01T10:01:00Z", raw="Read it straight away, no dilution, it was off the scale I think")],
    )


@needs_key
def test_a_real_draft_passes_every_rule():
    try:
        s = practice.draft(PracticeDraftRequest(skillId="SK-OD", depositions=[bench_run()]))
    except practice.PracticeRefused as e:
        pytest.fail(f"the model's draft was refused on {e.rule}: {e.why} (${e.usage.costUsd:.4f} spent)")
    print(f"\n{s.id}: {s.title!r}, {len(s.evidence)} values, {s.model}, ${s.usage.costUsd:.4f}")
    print(f"  situation: {s.situation}\n  prompt: {s.prompt}")
    assert s.evidence and all(v.label for v in s.evidence)
    assert any(st.stepId in {"o3", "o4", "s7", "s8", "s12"} for st in s.steps)


@needs_key
def test_a_real_tutor_questions_and_then_closes():
    """Three answers, as a trainee who is half right might give them. The tutor
    has to stay clear of numbers throughout and close on the last."""
    s = practice.draft(PracticeDraftRequest(skillId="SK-OD", depositions=[bench_run()]))
    answers = [
        "I would record it as it is and add a note that it looked high.",
        "Because the reading was what the instrument showed, so it is the measurement.",
        "Maybe dilute it first so it is in the range, then read again.",
    ]
    held = None
    for a in answers:
        try:
            held = practice.turn(PracticeTurnRequest(scenarioId=s.id, sessionId=held.id if held else None, answer=a))
        except practice.PracticeRefused as e:
            pytest.fail(f"the tutor's reply was refused on {e.rule}: {e.why}")
        print(f"\n  trainee: {a}\n  tutor ({held.turns[-1].move}): {held.turns[-1].text}")
    assert held is not None and held.closedAt and held.observed
    for o in held.observed:
        print(f"  observed: {o.text}")
    print(f"  session {held.id}: ${held.usage.costUsd:.4f} for the tutor, ${s.usage.costUsd:.4f} for the draft")
