"""The authored flows as acceptance criteria (OF-BLD-007 §9).

REQUIRES AN API KEY AND SPENDS MONEY. Marked `live` and excluded from
`pnpm verify`, which must stay runnable offline with no key. Run with
`pnpm test:live`.

Thirteen conversations were written by hand: a question, and an answer citing
the records that answer it. Under the scripted path they were a parallel
implementation — content that looked like the system working. Here they become
the thing the real pipeline is graded against, which is the payoff of the
inversion in §1.

WHAT IS ASSERTED, AND WHY IT IS NOT SET EQUALITY. The specification says the
plan should cite "the same records". Exact set equality is the wrong test and
would fail for the wrong reason: the authored answer for F1 cites seventeen
records because it draws a cross-host table, while the same question asked once
retrieves thirty records and may be answered correctly with three of them. Both
are right. What is NOT right is citing none of them — that means the model
answered a different question, or answered from outside the evidence.

So the floor is overlap ≥ 1, and every run prints the full overlap per flow, so
a drop from "twelve of seventeen" to "one of seventeen" is visible as drift even
though both pass. A threshold that hides its own margin is a threshold that
stops meaning anything.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from openferment_core import postdoc_agent, tools

FIXTURES = Path(__file__).parent / "fixtures" / "flows.json"

pytestmark = pytest.mark.live

needs_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live tests need ANTHROPIC_API_KEY in core/.env",
)


def load_fixtures() -> list[dict]:
    if not FIXTURES.exists():
        pytest.skip(f"{FIXTURES} not generated — run `pnpm export:fixtures`")
    return json.loads(FIXTURES.read_text())


def gradable() -> list[dict]:
    """Flows whose authored answer cites at least one resolvable record.

    F12 (regulatory status) cites only papers — there is no numeric record
    behind a regulatory status, which is correct — so it has nothing to grade a
    citation overlap against and is exercised by the smoke test below instead.
    """
    return [f for f in load_fixtures() if f["recordIds"]]


def run_pipeline(question: str, monkeypatch) -> tuple:
    """The real thing, as `/api/ask` runs it by default since OF-BLD-014
    §5.3: the bounded loop over the evidence pool. Every record a tool
    returned is kept, so retrieval is graded apart from the model."""
    returned: set[str] = set()
    real = tools.run

    def spy(name, raw, ctx):
        result = real(name, raw, ctx)
        returned.update(result.recordIds)
        return result

    monkeypatch.setattr(tools, "run", spy)
    plan = postdoc_agent.ask(question)
    return plan, returned


@needs_key
@pytest.mark.parametrize("fixture", gradable(), ids=lambda f: f["id"])
def test_the_plan_cites_what_a_human_said_it_should(fixture, capsys, monkeypatch):
    expected = set(fixture["recordIds"])
    plan, returned = run_pipeline(fixture["question"], monkeypatch)

    cited = {rid for claim in plan.claims for rid in claim.recordIds}
    overlap = cited & expected
    retrievable = expected & returned

    with capsys.disabled():
        print(
            f"\n  {fixture['id']:<9} cited {len(cited):>2} · "
            f"authored {len(expected):>2} · overlap {len(overlap):>2} "
            f"({len(retrievable)} of the authored records were even retrieved) · "
            f"{plan.rejected} rejected · {sum(1 for t in plan.trace if t.kind == 'tool')} tool calls · "
            f"stopped {plan.stopped} · ${plan.usage.costUsd:.4f}"
        )
        if plan.rejected:
            for reason in plan.rejectionReasons:
                print(f"      dropped — {reason}")

    # Retrieval is graded separately and honestly: if BM25 never surfaced any of
    # the authored records, the model could not have cited them, and failing it
    # for that would blame the wrong component.
    assert retrievable, (
        f"{fixture['id']}: no tool returned ANY of the {len(expected)} authored "
        f"records for {fixture['question']!r} — this is a retrieval failure, not a "
        "model failure"
    )

    assert not (plan.claims == [] and not plan.declined), (
        f"{fixture['id']}: no claims and no reason given"
    )

    assert overlap, (
        f"{fixture['id']}: cited {sorted(cited) or 'nothing'} but a human said the "
        f"answer is in {sorted(expected)}; {len(retrievable)} of those were retrieved. "
        "Citing none of them means a different question got answered."
    )


@needs_key
@pytest.mark.parametrize("fixture", load_fixtures(), ids=lambda f: f["id"])
def test_every_flow_produces_a_usable_plan(fixture, monkeypatch):
    """Rule 1 and the citation rules hold on real model output, on every flow.

    The offline tests pin the validator against hand-written plans. This pins it
    against what the model actually emits, which is the only place the two can
    disagree.
    """
    plan, _returned = run_pipeline(fixture["question"], monkeypatch)

    assert plan.claims or plan.declined, (
        f"{fixture['id']}: neither claims nor a decline — a blank answer"
    )

    for claim in plan.claims:
        # Belt and braces: the validator already enforced this, and the point of
        # asserting it again here is that this is REAL model output rather than
        # a fixture, so a regression in the validator shows up as a test failure
        # rather than as a number quietly reaching a screen.
        from openferment_core.validate import find_number

        assert find_number(claim.text) is None, (
            f"{fixture['id']}: a number survived validation in {claim.text!r}"
        )
        assert claim.recordIds or claim.passages or claim.evidenceIds or claim.support == "unsupported"
        assert claim.provenance, "every claim carries a computed provenance"


@needs_key
def test_an_out_of_corpus_question_declines(monkeypatch):
    """The honest failure, end to end and for real.

    Nothing in a fermentation corpus bears on lattice QCD. Retrieval returns
    nothing, the model is told so, and the only correct outcome is a decline
    with no claims. A confident answer here would mean the model is drawing on
    training rather than on evidence, which is the failure this whole
    architecture exists to prevent.
    """
    plan, _returned = run_pipeline(
        "What is the lattice spacing in quantum chromodynamics simulations?", monkeypatch
    )
    assert plan.claims == [] or all(c.support == "unsupported" for c in plan.claims), (
        f"claimed something from an empty corpus: {[c.text for c in plan.claims]}"
    )
    assert plan.declined


@needs_key
def test_a_number_in_the_answer_is_dropped_not_shown(monkeypatch):
    """The rail, on live output.

    Asked in a way that invites a quantity. Whatever the model does, no number
    reaches a claim: either it follows the instruction, or the validator drops
    the claim and counts it. There is no third outcome, and this test would fail
    if one appeared.
    """
    plan, _returned = run_pipeline(
        "Exactly what titre in grams per litre was reached, as a number?", monkeypatch
    )
    from openferment_core.validate import find_number

    offenders = [c.text for c in plan.claims if find_number(c.text)]
    assert not offenders, f"a number reached a claim: {offenders}"


def test_the_pipeline_reports_a_missing_key_rather_than_crashing():
    """Runs without a key, on purpose — the one live-file test that always runs.

    A missing key must produce a message a person can act on, not a traceback.
    """
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        plan = postdoc_agent.ask("anything")
        assert plan.claims == [] and "core/.env" in (plan.declined or "")
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved
