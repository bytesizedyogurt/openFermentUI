"""Postdoc's evaluation set (postdoc/evaluate.py; execution prompt §10 stage
6.4), offline.

The worker is test_tools_study's priced STAND-IN and the model the
evaluation's own (`evaluate.StandIn`). The default questions are kept in the
project once; a run asks each through the loop as a turn of a conversation,
the follow-up in the conversation of the question it follows, reading its
history from the service; each is scored on the tools it reached, what its
claims cite, its labelled estimate and the claims dropped for a number, and
kept. The stand-in is named wherever a model is: the estimate it types, the
scenario it keeps.
"""
from __future__ import annotations

import json

import pytest

from openferment_core import api, evidence_pool
from openferment_core.engine import library, simulator
from openferment_core.models import AnswerPlan, Claim, ClaimValue, Origin, Quantity, TraceStep
from openferment_core.postdoc import conversations, evaluate
from openferment_core.studies import scenarios
from test_tools import pool  # noqa: F401
from test_tools_study import Priced


@pytest.fixture
def worker(monkeypatch, pool):  # noqa: F811
    monkeypatch.setattr(simulator, "call", Priced())
    monkeypatch.setattr(library, "_PARAMETERS", {})
    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: pool)


def test_the_default_questions_are_kept_once():
    assert evaluate.seed() == ["eq-price", "eq-dearer"] and evaluate.seed() == []
    assert [q.id for q in evaluate.questions()] == ["eq-price", "eq-dearer"]
    assert evaluate.questions()[1].follows == "eq-price"


def test_an_offline_run_asks_scores_and_keeps_each_question(worker):
    evaluate.seed()
    found, standins = evaluate.run(api._answer)
    price, dearer = found
    assert (price.mode, price.models, price.scores.model_dump()) == (
        "offline", [evaluate.STANDIN], {"tools": 1.0, "citations": 1.0, "estimates": 1.0, "bareNumbers": 1.0})
    assert dearer.scores.model_dump() == {"tools": 1.0, "citations": 1.0, "estimates": 1.0, "bareNumbers": 0.0}
    assert (dearer.droppedForNumbers, dearer.rejected, dearer.claims) == (1, 1, 1)
    assert dearer.conversationId == price.conversationId, "the follow-up is asked in the conversation it follows"
    assert "What selling price does the library's sugarcane plant solve" in str(standins["eq-dearer"].seen[0])
    held = conversations.get(price.conversationId)
    assert [x.status for x in held.turns] == ["answered", "answered"] and held.turns[1].by == evaluate.BY
    (scenario,) = scenarios.listed()
    (value,) = scenario.values
    assert (value.quantity.origin.kind, value.quantity.origin.by) == ("model-estimate", evaluate.STANDIN)
    assert [r.id for r in evaluate.runs()] == [r.id for r in found]
    report = evaluate.report(found)
    assert report["mean"] == {"tools": 1.0, "citations": 1.0, "estimates": 1.0, "bareNumbers": 0.5}


def _plan(*claims, rejected=(), tools=()):
    return AnswerPlan(question="q", claims=list(claims), rejected=len(rejected), rejectionReasons=list(rejected),
                      trace=[TraceStep(n=i, kind="tool", tool=t, summary="", ms=0, ok=True) for i, t in enumerate(tools)])


def test_the_scores_are_computed_from_the_plan():
    q = evaluate.EvalQuestion(id="q", question="q", tools=[["engine_run", "engine_report"], ["study_scenario"]],
                              cites=["evidence"], estimate=True)
    estimate = ClaimValue(label="a price", quantity=Quantity(value=1.0, unit="USD/kg", origin=Origin(
        kind="model-estimate", by=evaluate.STANDIN, at="2026-10-30")))
    good = Claim(id="c1", text="t", evidenceIds=["e1"], provenance="assumed", values=[estimate])
    bare = Claim(id="c2", text="t", recordIds=["r1"], provenance="curated")
    s = evaluate.score(q, _plan(good, bare, tools=["engine_report"], rejected=["c3: claim text contains a number ('2')"]))
    assert s.model_dump() == {"tools": 0.5, "citations": 0.5, "estimates": 1.0, "bareNumbers": 0.0}
    plain = evaluate.EvalQuestion(id="p", question="p", tools=[], cites=[], estimate=False)
    assert evaluate.score(plain, _plan(good)).estimates == 0.0, "an estimate where none was asked for"
    assert evaluate.score(plain, _plan()).model_dump() == {"tools": 1.0, "citations": 0.0, "estimates": 1.0,
                                                          "bareNumbers": 1.0}


# ── alpha 2.1 stage C: the owner's twelve, tags and the judge ──────────


def test_the_owners_twelve_and_the_bases_two_are_a_suite_of_their_own():
    made = evaluate.seed(suite=evaluate.ETHANOL)
    assert made == [f"eq-eth-{n:02d}" for n in range(1, 15)] and evaluate.seed(suite=evaluate.ETHANOL) == []
    held = {q.id: q for q in evaluate.questions(evaluate.ETHANOL)}
    assert (held["eq-eth-07"].follows, held["eq-eth-08"].follows) == ("eq-eth-06", "eq-eth-05")
    assert all(q.expects and q.suite == evaluate.ETHANOL for q in held.values())
    assert evaluate.questions(evaluate.DEFAULT) == [], "a suite is seeded on its own"
    assert held["eq-eth-05"].estimate is True and held["eq-eth-07"].estimate is False and held["eq-eth-01"].estimate is None
    with pytest.raises(ValueError, match="no suite"):
        evaluate.seed(suite="nonesuch")


# ── alpha 2.2 stage C: the base's two (the prompt's §5, questions 13 and 14) ──


def _core_engines() -> set[str]:
    """The engines core/pyproject.toml registers in the group `openferment.engines`."""
    import tomllib
    from pathlib import Path

    project = tomllib.loads((Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8"))
    return set(project["project"]["entry-points"]["openferment.engines"])


def test_question_13_expects_the_engine_reads_and_every_engine_the_core_registers():
    q = {q.id: q for q in evaluate.ETHANOL_QUESTIONS}["eq-eth-13"]
    assert q.question == ("Which engines are registered here, what does each take and give, and which of this "
                          "project's runs came from each?"), "the prompt's words"
    assert _core_engines() <= set(evaluate.ENGINES_EXPECTED), "every engine the core registers is one it expects"
    assert all(name in q.expects for name in evaluate.ENGINES_EXPECTED) and "one table" in q.expects
    assert q.tools[:2] == [["engine_plants"], ["engine_parameters"]] and "engine_report" in q.tools[2]
    assert set(q.cites) == {"evidence", "row"} and q.estimate is False and q.follows is None


def test_question_13_seeded_expects_every_engine_the_registry_holds_the_cores_three_among_them(monkeypatch):
    """alpha 2.2 D0.12: an engine installed beside the core is expected
    beside the core's three when the suite is seeded; the code names the
    core's three alone."""
    from importlib.metadata import EntryPoint

    from openferment_core.engine import registry

    points = [EntryPoint(name=n, value=v, group=registry.GROUP) for n, v in (
        ("biosteam", "openferment_core.engine.biosteam:ENGINE"), ("sample", "openferment_core.engine.sample:SAMPLE"))]
    monkeypatch.setattr(registry, "entry_points", lambda: points)
    registry.reset()
    try:
        assert evaluate.engines_here() == ("biosteam", "kinetics", "sample", "train")
        evaluate.seed(suite=evaluate.ETHANOL)
        held = {q.id: q for q in evaluate.questions(evaluate.ETHANOL)}["eq-eth-13"]
        assert "Names each engine registered here (biosteam, kinetics, sample and train)" in held.expects
        code = {q.id: q for q in evaluate.ETHANOL_QUESTIONS}["eq-eth-13"]
        assert "Names each engine registered here (biosteam, kinetics and train)" in code.expects
        assert held.expects.replace("sample and train", "train").replace("kinetics, train", "kinetics and train") == \
            code.expects, "the seed changes the names alone"
        assert {q.id: q.expects for q in evaluate.questions(evaluate.ETHANOL) if q.id != "eq-eth-13"} == {
            q.id: q.expects for q in evaluate.ETHANOL_QUESTIONS if q.id != "eq-eth-13"}
    finally:
        registry.reset()


def test_question_14_expects_a_measurement_origin_a_provenance_with_its_reason_and_a_comparison():
    q = {q.id: q for q in evaluate.ETHANOL_QUESTIONS}["eq-eth-14"]
    assert q.question == ("Take the ethanol yield measured in this project's most recent deposition, set it as the "
                          "glucose-only scenario's yield, run it, and say what changed and what the value rests on."), \
        "the prompt's words"
    assert q.tools == [["runbooks_read"], ["study_scenario"], ["engine_run"], ["study_compare"]]
    assert all(w in q.expects for w in ("origin measurement", "reading's id", "measured", "assumed with the reason",
                                        "comparison"))
    assert q.follows == "eq-eth-05", "asked in the conversation that proposed the glucose-only scenario"
    assert q.estimate is None, "the glucose-only scenario's own estimates may stand, each labelled"
    assert set(q.cites) == {"evidence", "row"}


def test_every_question_names_tools_the_registry_holds_and_words_alone():
    from openferment_core import tools

    for q in (*evaluate.DEFAULT_QUESTIONS, *evaluate.ETHANOL_QUESTIONS):
        assert all(name in tools.WHITELIST for group in q.tools for name in group), q.id
    for q in evaluate.ETHANOL_QUESTIONS[12:]:
        assert not any(ch.isdigit() for ch in q.question + q.expects), f"{q.id}: words only, no values"


def test_an_estimate_a_question_allows_is_held_to_its_label():
    may = evaluate.EvalQuestion(id="m", question="m", estimate=None)
    estimate = ClaimValue(label="a share", quantity=Quantity(value=0.5, unit="", origin=Origin(
        kind="model-estimate", by=evaluate.STANDIN, at="2026-11-02")))
    labelled = Claim(id="c1", text="t", evidenceIds=["e1"], provenance="assumed", values=[estimate])
    unlabelled = Claim(id="c2", text="t", evidenceIds=["e1"], provenance="computed", values=[estimate])
    assert evaluate.score(may, _plan(labelled)).estimates == 1.0
    assert evaluate.score(may, _plan()).estimates == 1.0, "none stated, none needed"
    assert evaluate.score(may, _plan(unlabelled)).estimates == 0.0, "stated and not labelled"


class _Judge:
    """A stand-in for `llm.call` on the judge route: what it was handed, and a judgement."""

    def __init__(self, data, model="judge-standin", stop="end_turn"):
        self.data, self.model, self.stop, self.asked = data, model, stop, []

    def __call__(self, **kw):
        from openferment_core import llm
        from openferment_core.models import Usage

        self.asked.append(kw)
        return llm.Result(data=self.data, model=self.model, usage=Usage(costUsd=0.0123, models=[self.model]),
                          stop_reason=self.stop)


def _cited_plan():
    from openferment_core.models import Evidence, Passage, PassageRef
    from openferment_core.models import ComputedBasis

    basis = ComputedBasis(tool="t", toolVersion="1", artifactId="a1", at="2026-11-02", inputs=[])
    ev = Evidence(id="a1:price.solvedPrice", label="the solved price", value=0.66, unit="USD/kg",
                  provenance="computed", basis=basis)
    passage = Passage(id="P1:s1:0", paperId="P1", sectionId="s1", heading="Results", kind="prose",
                      text="The titre reached its peak after two days. More words follow.", start=0, end=60)
    claim = Claim(id="c1", text="The plant solves a selling price.", evidenceIds=[ev.id], recordIds=["r1"],
                  passages=[PassageRef(passageId=passage.id, quote="The titre reached its peak after two days.")],
                  provenance="computed", values=[ClaimValue(label="the price", quantity=Quantity(
                      value=0.66, unit="USD/kg", origin=Origin(kind="artifact", ref="a1")), source=ev.id)])
    return AnswerPlan(question="q", claims=[claim], evidence=[ev], passages=[passage], gaps=["a gap in words"],
                      trace=[TraceStep(n=1, kind="tool", tool="engine_run", summary="", ms=0, ok=True),
                             TraceStep(n=2, kind="tool", tool="draft_runbook", summary="", ms=0, ok=False)])


def test_the_judge_reads_each_claim_with_what_it_cites_and_its_judgement_is_labelled():
    q = evaluate.EvalQuestion(id="q", question="What does the plant solve?", expects="A price, cited.")
    call = _Judge({"answers": 1.4, "grounded": 0.8, "labelled": "1", "coverage": -0.2,
                   "errors": ["c1: the unit is per gallon"], "note": "Mostly sound."})
    record = {"r1": {"paperId": "P1", "fieldLabel": "Ethanol titre", "value": 21.0, "unit": "g/L",
                     "quote": "a titre of 21 g/L"}}.get
    got = evaluate.judge(q, _cited_plan(), call=call, record=record, paper=lambda pid: {"title": "A paper on titres"})
    (asked,) = call.asked
    assert (asked["family"], asked["schema"], asked["system"]) == ("judge", evaluate.JUDGE_SCHEMA, evaluate.JUDGE_SYSTEM)
    seen = json.loads(asked["user"])
    (c,) = seen["claims"]
    assert (seen["question"], seen["aGoodAnswer"], seen["documents"]) == ("What does the plant solve?", "A price, cited.",
                                                                          {"P1": "A paper on titres"})
    assert c["evidence"] == [{"id": "a1:price.solvedPrice", "label": "the solved price", "value": 0.66, "unit": "USD/kg"}]
    assert c["records"][0]["quote"] == "a titre of 21 g/L" and c["passages"][0]["context"].startswith("The titre")
    assert c["values"][0]["origin"] == "artifact" and seen["toolsCalled"] == ["engine_run", "draft_runbook (refused)"]
    assert (got.model, got.answers, got.grounded, got.labelled, got.coverage) == ("judge-standin", 1.0, 0.8, 1.0, 0.0)
    assert got.errors == ["c1: the unit is per gallon"] and got.costUsd == 0.0123
    cut = evaluate.judge(q, _cited_plan(), call=_Judge(None, stop="max_tokens"), record=record, paper=lambda _: None)
    assert "ran out of room" in cut.declined and cut.answers is None


def test_a_judge_that_declines_leaves_no_score_and_says_why(worker):
    from openferment_core import llm
    from openferment_core.models import Usage

    def refuses(**kw):
        raise llm.ModelRefused("bio", ["claude-opus-5-5"], Usage(costUsd=0.002))

    q = evaluate.EvalQuestion(id="q", question="q")
    got = evaluate.judge(q, _cited_plan(), call=refuses, record=lambda _: None, paper=lambda _: None)
    assert (got.model, got.answers, got.costUsd) == ("claude-opus-5-5", None, 0.002) and "bio" in got.declined
    evaluate.seed()

    def half(q, plan):
        return evaluate.Judgement(model="claude-opus-5-5", answers=0.5, grounded=0.5, labelled=0.5, coverage=0.5)

    found, _ = evaluate.run(api._answer, tag="t", judged=True,
                            judge_with=lambda q, plan: got if q.id == "eq-dearer" else half(q, plan))
    judged = evaluate.summary(evaluate.DEFAULT)["t"]["judges"]["claude-opus-5-5"]
    assert (judged["answers"], judged["answers judged"], judged["declined"]) == (0.5, 1, ["eq-dearer"])


def test_a_run_is_tagged_timed_judged_and_judged_again(worker):
    evaluate.seed()
    with pytest.raises(ValueError, match="offline run is not judged"):
        evaluate.run(api._answer, judged=True)

    def first(q, plan):
        return evaluate.Judgement(model="judge-one", answers=1.0, grounded=1.0, labelled=1.0, coverage=0.5)

    def second(q, plan):
        assert plan.claims is not None, "the answer as it was kept"
        return evaluate.Judgement(model="judge-two", answers=0.5, grounded=1.0, labelled=1.0, coverage=0.5)

    found, _ = evaluate.run(api._answer, tag="stand-in table", judged=True, judge_with=first)
    assert all(r.tag == "stand-in table" and r.seconds is not None and [j.model for j in r.judged] == ["judge-one"]
               for r in found)
    again = evaluate.judge_kept(evaluate.DEFAULT, "stand-in table", judge_with=second)
    assert [[j.model for j in r.judged] for r in again] == [["judge-one", "judge-two"]] * 2
    s = evaluate.summary(evaluate.DEFAULT)["stand-in table"]
    assert s["questions"] == 2 and s["code"]["tools"] == 1.0 and s["droppedForNumbers"] == 1
    assert s["judges"]["judge-one"]["coverage"] == 0.5 and s["judges"]["judge-two"]["answers"] == 0.5
