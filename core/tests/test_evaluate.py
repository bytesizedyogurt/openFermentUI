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
    assert held["eq-eth-04"].follows == "eq-eth-03", "that plant, the one question 3 asks of, in its conversation"
    assert {q.id: q.follows for q in held.values() if q.follows} == {
        "eq-eth-04": "eq-eth-03", "eq-eth-07": "eq-eth-06", "eq-eth-08": "eq-eth-05", "eq-eth-14": "eq-eth-05"}
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
    assert got.tried == ["claude-opus-5-5"], "the models the refusal names"
    evaluate.seed()

    def half(q, plan):
        return evaluate.Judgement(model="claude-opus-5-5", answers=0.5, grounded=0.5, labelled=0.5, coverage=0.5)

    found, _ = evaluate.run(api._answer, tag="t", judged=True,
                            judge_with=lambda q, plan: got if q.id == "eq-dearer" else half(q, plan))
    judged = evaluate.summary(evaluate.DEFAULT)["tags"]["t"]["judges"]["claude-opus-5-5"]
    assert (judged["answers"], judged["answersJudged"], judged["declined"]) == (0.5, 1, ["eq-dearer"])


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
    s = evaluate.summary(evaluate.DEFAULT)["tags"]["stand-in table"]
    assert s["questions"] == 2 and s["code"]["tools"] == 1.0 and s["claims"]["droppedForNumbers"] == 1
    assert s["judges"]["judge-one"]["coverage"] == 0.5 and s["judges"]["judge-two"]["answers"] == 0.5


# ── alpha 2.2 F.2a: what the model comparison reads ─────────────────────

OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"


def test_a_run_keeps_its_first_steps_its_stop_its_restarts_and_its_drop_reasons(worker):
    evaluate.seed()
    found, _ = evaluate.run(api._answer)
    price, dearer = found
    for r in found:
        assert 0 <= r.firstStepSeconds <= r.firstModelSeconds <= r.seconds, r.questionId
        assert (r.stopped, r.restarts) == ("done", []), r.questionId
    (turn,) = [t for t in conversations.get(price.conversationId).turns if t.id == price.turnId]
    assert [s.kind for s in turn.plan.trace][:2] == ["coverage", "tool"], "the code's sweep first, the model's call next"
    assert price.dropReasons == []
    (reason,) = dearer.dropReasons
    assert "contains a number" in reason and evaluate.drop_kind(reason) == "a number in a claim's words"
    kept = {r.id: r for r in evaluate.runs()}[dearer.id]
    assert (kept.dropReasons, kept.firstModelSeconds, kept.stopped) == (dearer.dropReasons, dearer.firstModelSeconds,
                                                                      "done"), "kept as the run made it"


def test_a_run_keeps_the_restarts_and_the_stop_its_answer_gave():
    """The answer path hands the run each step as it completes; a restart
    step's words and the plan's stop are kept on the run."""
    from openferment_core.models import Usage

    evaluate.seed()
    restart = "model-a declined; asked again on model-b"

    def answer(request, *, converse=None, on_step=None):
        steps = [TraceStep(n=1, kind="coverage", summary="swept", ms=0, ok=True),
                 TraceStep(n=2, kind="restart", summary=restart, ms=0, ok=False),
                 TraceStep(n=3, kind="final", summary="Answered", ms=0, ok=True)]
        for s in steps:
            on_step(s)
        return AnswerPlan(question=request.question, trace=steps, stopped="calls", conversationId=request.conversationId,
                          turnId=request.turnId, usage=Usage(models=["model-b"], costUsd=0.01),
                          rejectionReasons=["a gap dropped: it holds a number"])

    found, _ = evaluate.run(answer, live=True, tag="restarted")
    assert [(r.restarts, r.stopped, r.models) for r in found] == [([restart], "calls", ["model-b"])] * 2
    assert all(r.firstStepSeconds <= r.firstModelSeconds <= r.seconds for r in found)
    assert all(evaluate.drop_kind(x) == "a number in a gap or the decline" for r in found for x in r.dropReasons)


def test_the_drop_kinds_read_the_validators_own_words():
    """Each kind of drop counted by the words the validator writes, read
    from the validator itself so a change to its words is seen here."""
    from openferment_core import postdoc_agent
    from openferment_core.models import Passage
    from openferment_core.validate import SeenSet, validate_plan

    class NoRecords:
        def record(self, record_id):
            return None

    seen = SeenSet()
    seen.passages["P1:s1:0"] = Passage(id="P1:s1:0", paperId="P1", sectionId="s1", heading="h", kind="prose",
                                       text="One sentence stands here.", start=0, end=25)
    seen.runs["a9"] = "fermos/vessel/a9"

    def claim(cid, text="It says a thing.", **kw):
        return {"id": cid, "text": text, "recordIds": [], "paperIds": [], "support": "direct", "passages": [],
                "evidenceIds": [], "moduleRefs": [], "values": [], **kw}

    out = validate_plan([
        claim("c1", "The run gives 2 of them."),
        claim("c2", recordIds=["r-none"]),
        claim("c3", evidenceIds=["a1:price"]),
        claim("c4", evidenceIds=["a9"]),
        claim("c5", passages=[{"passageId": "P1:s1:0", "quote": ""}]),
        claim("c6", values=[{"label": "a value", "evidenceId": "", "recordId": "", "estimate": None}]),
        claim("c7"),
        claim("c8", ""),
        "not a claim at all",
    ], seen, NoRecords())
    reasons = list(out.reasons)
    postdoc_agent.held_to_rule_one(["a gap of 3 parts"], "declined for 2 reasons", reasons)
    assert [evaluate.drop_kind(r) for r in reasons] == [
        "a number in a claim's words", "a citation no tool returned", "a citation no tool returned",
        "a row cited as evidence", "a quote", "a typed value", "a claim citing nothing", "an empty claim",
        "an empty claim", "a number in a gap or the decline", "a number in a gap or the decline"], reasons
    assert evaluate.drop_kind("words of no rule") == evaluate.OTHER_DROP


def _keep(question_id, tag="t", **fields):
    """A run kept with known values (placeholders) through the store a run is kept in."""
    import uuid

    from openferment_core import db, projects

    run = evaluate.EvalRun(**{
        "id": f"er-{uuid.uuid4().hex[:12]}", "questionId": question_id, "question": "q", "mode": "live",
        "models": ["model-a"], "scores": evaluate.EvalScores(tools=1.0, citations=1.0, estimates=1.0, bareNumbers=1.0),
        "droppedForNumbers": 0, "claims": 0, "rejected": 0, "toolsCalled": [], "costUsd": 0.0,
        "at": "2026-11-05T00:00:00Z", "by": evaluate.BY, "suite": evaluate.ETHANOL, "tag": tag, **fields})
    db.run(evaluate._keep(projects.current(), run))
    return run


def _judged(model, score=None, *, tried=None, route=None, declined=None, cost=0.0):
    return evaluate.Judgement(model=model, answers=score, grounded=score, labelled=score, coverage=score,
                              declined=declined, costUsd=cost, tried=tried if tried is not None else [model],
                              route=route if route is not None else [model])


def test_summary_sets_medians_tool_calls_dropped_claims_and_cost_per_question():
    evaluate.seed(suite=evaluate.ETHANOL)
    _keep("eq-eth-01", costUsd=5.0, seconds=99.0, toolsCalled=["a"] * 20)  # superseded by the newer run below
    _keep("eq-eth-01", seconds=10.0, firstStepSeconds=0.2, firstModelSeconds=1.0, toolsCalled=["a"] * 3, claims=2,
          rejected=1, droppedForNumbers=1, dropReasons=["c3: claim text contains a number ('2') — values come from "
                                                        "the record"], stopped="done", costUsd=0.1)
    _keep("eq-eth-02", seconds=30.0, firstStepSeconds=0.4, firstModelSeconds=3.0, toolsCalled=["a"] * 5, claims=4,
          rejected=2, dropReasons=["c1: cites what no tool returned in this run: P9:s1:0",
                                   "a gap dropped: it holds a number"], stopped="calls",
          restarts=["model-a declined; asked again on model-b"], costUsd=0.2,
          judged=[_judged("judge-a", 0.5, cost=0.05)])
    _keep("eq-eth-03", seconds=20.0, firstStepSeconds=0.3, firstModelSeconds=2.0, toolsCalled=["a"] * 10,
          stopped="time", costUsd=0.6, declined="Postdoc wrote no claim it could support.")
    _keep("eq-eth-01", tag="other", costUsd=1.0)
    out = evaluate.summary(evaluate.ETHANOL)
    assert (out["suite"], sorted(out["tags"])) == (evaluate.ETHANOL, ["other", "t"])
    s = out["tags"]["t"]
    assert s["questions"] == 3 and s["toolCalls"] == {"mean": 6.0, "median": 5}
    assert s["seconds"] == {"firstStep": 0.3, "firstModelStep": 2.0, "answer": 20.0}
    assert s["claims"] == {"kept": 6, "dropped": 3, "droppedForNumbers": 1, "dropReasons": {
        "a number in a claim's words": 1, "a number in a gap or the decline": 1, "a citation no tool returned": 1}}
    assert s["stops"] == {"done": 1, "rounds": 0, "calls": 1, "cost": 0, "time": 1}
    assert s["declined"] == ["eq-eth-03"] and s["restarts"] == {"eq-eth-02": ["model-a declined; asked again on model-b"]}
    assert s["cost"] == {"perQuestion": {"mean": 0.3, "median": 0.2}, "answersUsd": 0.9, "judgesUsd": 0.05,
                         "totalUsd": 0.95}
    assert out["tags"]["other"]["cost"]["answersUsd"] == 1.0 and out["tags"]["other"]["seconds"]["answer"] is None


def _two_judges():
    """Two tags judged by two judge models: on `t` Opus once and Sonnet twice
    on one answer; on `u` Opus declining one answer and passing another on to
    Sonnet on the Opus-then-Sonnet route."""
    evaluate.seed(suite=evaluate.ETHANOL)
    _keep("eq-eth-01", judged=[_judged(OPUS, 0.8, cost=0.05), _judged(SONNET, 0.6, cost=0.02),
                               _judged(SONNET, 0.7, cost=0.03)], toolsCalled=["engine_run"], claims=3, costUsd=0.4)
    _keep("eq-eth-01", tag="u", judged=[
        _judged(OPUS, declined="declined by the safety classifier (bio) on claude-opus-5-5", cost=0.002),
        _judged(SONNET, 0.5, cost=0.03)])
    _keep("eq-eth-02", tag="u", judged=[_judged(SONNET, 0.9, tried=[OPUS, SONNET], route=[OPUS, SONNET], cost=0.04)])


def test_summary_counts_a_judge_once_a_run_and_says_how_far_the_judges_disagree():
    _two_judges()
    out = evaluate.summary(evaluate.ETHANOL)
    t, u = out["tags"]["t"], out["tags"]["u"]
    assert (t["judges"][OPUS]["answers"], t["judges"][SONNET]["answers"]) == (0.8, 0.7), "Sonnet's newest judgement"
    assert t["judges"][SONNET]["answersJudged"] == 1 and t["judges"][SONNET]["costUsd"] == 0.05, "both judgements paid"
    (pair,) = t["judgesDisagree"]
    assert pair == {"judges": [OPUS, SONNET], "answers": 0.1, "grounded": 0.1, "labelled": 0.1, "coverage": 0.1,
                    "pairs": 1, "unpaired": 0}
    assert u["judges"][OPUS] == {"answers": None, "grounded": None, "labelled": None, "coverage": None,
                                 "answersJudged": 0, "declined": ["eq-eth-01", "eq-eth-02"], "costUsd": 0.002}
    assert (u["judges"][SONNET]["answers"], u["judges"][SONNET]["answersJudged"]) == (0.7, 2)
    assert u["judgeRoutes"] == {OPUS: {"judgements": 1, "fellBack": 0, "declined": 1},
                                SONNET: {"judgements": 1, "fellBack": 0, "declined": 0},
                                f"{OPUS} then {SONNET}": {"judgements": 1, "fellBack": 1, "declined": 0}}
    assert [(p["pairs"], p["unpaired"], p["answers"]) for p in u["judgesDisagree"]] == [(0, 2, None)]
    (pooled,) = out["judgesDisagree"]
    assert (pooled["judges"], pooled["pairs"], pooled["unpaired"], pooled["answers"]) == ([OPUS, SONNET], 1, 2, 0.1)
    assert t["cost"]["judgesUsd"] == 0.1 and u["cost"]["judgesUsd"] == 0.072


def test_a_judgement_names_its_route_and_the_models_it_tried(monkeypatch):
    from openferment_core import llm
    from openferment_core.models import Usage

    monkeypatch.setenv(llm.ROUTES_SETTING, json.dumps({"judge": {"models": [OPUS, SONNET], "effort": "max"}}))
    q = evaluate.EvalQuestion(id="q", question="q", expects="e")
    scores = {"answers": 0.9, "grounded": 0.8, "labelled": 1.0, "coverage": 0.7, "errors": [], "note": "Sound."}

    def after_opus(**kw):
        return llm.Result(data=scores, model=SONNET, usage=Usage(costUsd=0.04, models=[OPUS, SONNET]),
                          stop_reason="end_turn", fell_back=True, tried=[OPUS, SONNET])

    got = evaluate.judge(q, _cited_plan(), call=after_opus, record=lambda _: None, paper=lambda _: None)
    assert (got.model, got.tried, got.route, got.answers, got.declined) == (SONNET, [OPUS, SONNET], [OPUS, SONNET], 0.9,
                                                                           None)
    served = got.model_copy(update={"model": f"{SONNET}-served"})
    assert evaluate._took_part(served) == [OPUS, f"{SONNET}-served"], "the last model tried, by the id it was served as"
    assert evaluate._fell_back(served) and evaluate._charged(served) == f"{SONNET}-served"

    def both_decline(**kw):
        raise llm.ModelRefused("bio", [OPUS, SONNET], Usage(costUsd=0.003))

    none = evaluate.judge(q, _cited_plan(), call=both_decline, record=lambda _: None, paper=lambda _: None)
    assert (none.tried, none.route, none.answers, none.costUsd) == ([OPUS, SONNET], [OPUS, SONNET], None, 0.003)
    assert "bio" in none.declined

    def unavailable(**kw):
        raise llm.ModelUnavailable("ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service.")

    with pytest.raises(llm.ModelUnavailable, match="ANTHROPIC_API_KEY is not set"):
        evaluate.judge(q, _cited_plan(), call=unavailable, record=lambda _: None, paper=lambda _: None)


def test_rows_give_each_newest_run_with_each_judges_scores():
    _two_judges()
    rows = {(r["tag"], r["questionId"]): r for r in evaluate.rows(evaluate.ETHANOL)}
    assert list(rows) == [("t", "eq-eth-01"), ("u", "eq-eth-01"), ("u", "eq-eth-02")]
    first = rows[("t", "eq-eth-01")]
    assert (first["models"], first["toolCalls"], first["claims"], first["dropped"], first["costUsd"]) == (
        ["model-a"], 1, 3, 0, 0.4)
    assert set(first) >= {"stopped", "restarts", "seconds", "firstStepSeconds", "firstModelSeconds", "scores", "declined"}
    assert first["judges"] == {
        OPUS: {"answers": 0.8, "grounded": 0.8, "labelled": 0.8, "coverage": 0.8, "declined": None, "costUsd": 0.05},
        SONNET: {"answers": 0.7, "grounded": 0.7, "labelled": 0.7, "coverage": 0.7, "declined": None, "costUsd": 0.05}}
    passed = rows[("u", "eq-eth-02")]["judges"]
    assert passed[OPUS] == {"answers": None, "grounded": None, "labelled": None, "coverage": None,
                            "declined": f"{SONNET} gave the judgement, after {OPUS}", "costUsd": 0.0}
    assert (passed[SONNET]["answers"], passed[SONNET]["costUsd"]) == (0.9, 0.04)
    assert "bio" in rows[("u", "eq-eth-01")]["judges"][OPUS]["declined"]


def test_only_asks_the_questions_named_and_a_follow_up_in_its_questions_conversation(worker):
    evaluate.seed()
    (price, _dearer), _ = evaluate.run(api._answer, tag="t")
    again, standins = evaluate.run(api._answer, tag="t", only=["eq-dearer"])
    (dearer,) = again
    assert dearer.questionId == "eq-dearer" and dearer.conversationId == price.conversationId
    assert "What selling price does the library's sugarcane plant solve" in str(standins["eq-dearer"].seen[0])
    assert [r.id for r in evaluate.newest(evaluate.DEFAULT, "t")] == [price.id, dearer.id]
    with pytest.raises(evaluate.Refused, match="the tag 'other' holds no run of eq-price"):
        evaluate.run(api._answer, tag="other", only=["eq-dearer"])
    with pytest.raises(evaluate.Refused, match="holds no question nonesuch; it holds eq-price, eq-dearer"):
        evaluate.run(api._answer, tag="t", only=["nonesuch"])
    with pytest.raises(evaluate.Refused, match="no question is named"):
        evaluate.run(api._answer, tag="t", only=[])
    assert len(evaluate.runs()) == 3, "a refusal asks nothing"
    both, _ = evaluate.run(api._answer, tag="other", only=["eq-price", "eq-dearer"])
    assert both[1].conversationId == both[0].conversationId != price.conversationId


def _unavailable(**kw):
    from openferment_core import llm

    raise llm.ModelUnavailable("ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service.")


def _judging(q, plan):
    return evaluate.judge(q, plan, record=lambda _: None, paper=lambda _: None, call=_unavailable)


def test_a_judge_pass_stops_in_words_when_no_judge_model_answers(worker):
    evaluate.seed()
    evaluate.run(api._answer, tag="t")

    def first_alone(q, plan):
        if q.id == "eq-dearer":
            return _judging(q, plan)
        return evaluate.Judgement(model="judge-one", answers=1.0, grounded=1.0, labelled=1.0, coverage=1.0)

    with pytest.raises(evaluate.JudgeUnavailable) as stop:
        evaluate.judge_kept(evaluate.DEFAULT, "t", judge_with=first_alone)
    words = str(stop.value)
    assert "stopped at eq-dearer" in words and "ANTHROPIC_API_KEY is not set" in words
    assert "judged 1 run before it" in words and "pnpm eval judge --suite default --tag t --only eq-dearer" in words
    assert [r.questionId for r in stop.value.done] == ["eq-price"]
    held = {r.questionId: r for r in evaluate.newest(evaluate.DEFAULT, "t")}
    assert ([j.model for j in held["eq-price"].judged], held["eq-dearer"].judged) == (["judge-one"], []), \
        "the run it stopped at keeps no judgement, and none names the missing key"
    with pytest.raises(evaluate.Refused, match="no question nonesuch"):
        evaluate.judge_kept(evaluate.DEFAULT, "t", judge_with=first_alone, only=["nonesuch"])
    assert [r.questionId for r in evaluate.judge_kept(evaluate.DEFAULT, "t", judge_with=first_alone,
                                                      only=["eq-price"])] == ["eq-price"]


def test_a_judged_run_stops_at_the_answer_no_judge_could_read(worker):
    evaluate.seed()
    with pytest.raises(evaluate.JudgeUnavailable) as stop:
        evaluate.run(api._answer, tag="u", judged=True, judge_with=_judging)
    (kept,) = stop.value.done
    assert (kept.questionId, kept.judged) == ("eq-price", [])
    assert [(r.questionId, r.judged) for r in evaluate.runs()] == [("eq-price", [])], "the answer kept, unjudged"
    words = str(stop.value)
    assert "stopped at eq-price" in words and "ANTHROPIC_API_KEY is not set" in words
    assert "pnpm eval judge --suite default --tag u --only eq-price" in words
    assert "pnpm eval run --suite default --tag u --judge --only eq-dearer" in words


def test_the_command_asks_only_the_questions_named_and_adds_the_rows(worker, capsys):
    from openferment_core import evaluation

    evaluate.seed()
    assert evaluation.main(["run", "--tag", "t"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert [r["questionId"] for r in first["runs"]] == ["eq-price", "eq-dearer"] and first["stopped"] is None
    assert evaluation.main(["run", "--tag", "t", "--only", "eq-dearer"]) == 0
    again = json.loads(capsys.readouterr().out)
    assert [r["questionId"] for r in again["runs"]] == ["eq-dearer"] and again["followUps"] == {"eq-dearer": True}
    assert again["runs"][0]["conversationId"] == first["runs"][0]["conversationId"]
    assert evaluation.main(["run", "--only", "nonesuch"]) == 2
    assert "holds no question nonesuch" in capsys.readouterr().err
    assert evaluation.main(["summary", "--rows"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert set(out) == {"suite", "tags", "judgesDisagree", "rows"}
    assert [(r["tag"], r["questionId"]) for r in out["rows"]] == [("t", "eq-price"), ("t", "eq-dearer")]
    assert out["tags"]["t"]["questions"] == 2


def test_the_judge_command_stops_in_words_and_exits_one(worker, capsys, monkeypatch):
    from openferment_core import evaluation

    evaluate.seed()
    evaluate.run(api._answer, tag="t")
    monkeypatch.setattr(evaluation, "_judge_with", lambda: _judging)
    assert evaluation.main(["judge", "--tag", "t"]) == 1
    seen = capsys.readouterr()
    out = json.loads(seen.out)
    assert out["judged"] == [] and "ANTHROPIC_API_KEY is not set" in out["stopped"] and "stopped at eq-price" in seen.err
    assert all(r.judged == [] for r in evaluate.runs())


def test_the_judge_command_reads_core_env_as_the_run_command_does():
    """The judge branch imports the service module before it judges, whose
    import loads core/.env (api.py, override=False), as the run branch's
    import does: the key, the routes and the budgets a judge's call reads.
    In a process of its own, so the import is seen happening."""
    import os
    import subprocess
    import sys

    script = (
        "import sys\n"
        "from openferment_core import evaluation\n"
        "from openferment_core.postdoc import evaluate\n"
        "before = 'openferment_core.api' in sys.modules\n"
        "seen = []\n"
        "evaluation._judge_with = lambda: seen.append('openferment_core.api' in sys.modules)\n"
        "evaluate.judge_kept = lambda *a, **k: []\n"
        "code = evaluation.main(['judge'])\n"
        "print(before, seen, code)\n"
    )
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=300,
                          env=dict(os.environ))
    assert done.returncode == 0, done.stderr[-2000:]
    assert done.stdout.split()[-3:] == ["False", "[True]", "0"], done.stdout
