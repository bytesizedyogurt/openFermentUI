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
