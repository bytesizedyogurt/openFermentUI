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

from openferment_core.corpus import load_corpus
from openferment_core.postdoc import PostdocUnavailable, ask_model
from openferment_core.validate import decline_reason, validate_claims

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


def run_pipeline(question: str) -> tuple:
    """The real thing: retrieve, ask, validate. Same path as /api/ask."""
    corpus = load_corpus()
    records = corpus.search(question, limit=30)
    raw, usage = ask_model(question, records, corpus)
    result = validate_claims(raw.get("claims") or [], corpus.records_by_id, corpus.papers_by_id)
    return result, raw, usage, records


@needs_key
@pytest.mark.parametrize("fixture", gradable(), ids=lambda f: f["id"])
def test_the_plan_cites_what_a_human_said_it_should(fixture, capsys):
    expected = set(fixture["recordIds"])
    result, raw, usage, retrieved = run_pipeline(fixture["question"])

    cited = {rid for claim in result.claims for rid in claim.recordIds}
    overlap = cited & expected
    retrievable = expected & {r["id"] for r in retrieved}

    with capsys.disabled():
        print(
            f"\n  {fixture['id']:<9} cited {len(cited):>2} · "
            f"authored {len(expected):>2} · overlap {len(overlap):>2} "
            f"({len(retrievable)} of the authored records were even retrieved) · "
            f"{result.rejected} rejected · ${usage.costUsd:.4f}"
        )
        if result.rejected:
            for reason in result.reasons:
                print(f"      dropped — {reason}")

    # Retrieval is graded separately and honestly: if BM25 never surfaced any of
    # the authored records, the model could not have cited them, and failing it
    # for that would blame the wrong component.
    assert retrievable, (
        f"{fixture['id']}: retrieval surfaced NONE of the {len(expected)} authored "
        f"records for {fixture['question']!r} — this is a retrieval failure, not a "
        "model failure"
    )

    assert not (result.claims == [] and not raw.get("declined")), (
        f"{fixture['id']}: no claims and no reason given"
    )

    assert overlap, (
        f"{fixture['id']}: cited {sorted(cited) or 'nothing'} but a human said the "
        f"answer is in {sorted(expected)}; {len(retrievable)} of those were retrieved. "
        "Citing none of them means a different question got answered."
    )


@needs_key
@pytest.mark.parametrize("fixture", load_fixtures(), ids=lambda f: f["id"])
def test_every_flow_produces_a_usable_plan(fixture):
    """Rule 1 and the citation rules hold on real model output, on every flow.

    The offline tests pin the validator against hand-written plans. This pins it
    against what the model actually emits, which is the only place the two can
    disagree.
    """
    result, raw, _usage, _retrieved = run_pipeline(fixture["question"])

    assert result.claims or decline_reason(result, raw.get("declined")), (
        f"{fixture['id']}: neither claims nor a decline — a blank answer"
    )

    for claim in result.claims:
        # Belt and braces: the validator already enforced this, and the point of
        # asserting it again here is that this is REAL model output rather than
        # a fixture, so a regression in the validator shows up as a test failure
        # rather than as a number quietly reaching a screen.
        from openferment_core.validate import find_number

        assert find_number(claim.text) is None, (
            f"{fixture['id']}: a number survived validation in {claim.text!r}"
        )
        assert claim.recordIds or claim.support == "unsupported"
        assert claim.provenance, "every claim carries a computed provenance"


@needs_key
def test_an_out_of_corpus_question_declines():
    """The honest failure, end to end and for real.

    Nothing in a fermentation corpus bears on lattice QCD. Retrieval returns
    nothing, the model is told so, and the only correct outcome is a decline
    with no claims. A confident answer here would mean the model is drawing on
    training rather than on evidence, which is the failure this whole
    architecture exists to prevent.
    """
    result, raw, _usage, retrieved = run_pipeline(
        "What is the lattice spacing in quantum chromodynamics simulations?"
    )
    assert retrieved == [], "retrieval should surface nothing for an out-of-corpus question"
    assert result.claims == [] or all(c.support == "unsupported" for c in result.claims), (
        f"claimed something from an empty corpus: {[c.text for c in result.claims]}"
    )
    assert decline_reason(result, raw.get("declined"))


@needs_key
def test_a_number_in_the_answer_is_dropped_not_shown():
    """The rail, on live output.

    Asked in a way that invites a quantity. Whatever the model does, no number
    reaches a claim: either it follows the instruction, or the validator drops
    the claim and counts it. There is no third outcome, and this test would fail
    if one appeared.
    """
    result, _raw, _usage, _retrieved = run_pipeline(
        "Exactly what titre in grams per litre was reached, as a number?"
    )
    from openferment_core.validate import find_number

    offenders = [c.text for c in result.claims if find_number(c.text)]
    assert not offenders, f"a number reached a claim: {offenders}"


def test_the_pipeline_reports_a_missing_key_rather_than_crashing():
    """Runs without a key, on purpose — the one live-file test that always runs.

    A missing key must produce a message a person can act on, not a traceback.
    """
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        corpus = load_corpus()
        with pytest.raises(PostdocUnavailable) as excinfo:
            ask_model("anything", [], corpus)
        assert "core/.env" in str(excinfo.value)
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved
