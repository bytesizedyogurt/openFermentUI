"""What the review of Phase 5 found (OF-BLD-014 §5.R). Each test failed
before its fix. STAND-IN text, not a paper's words."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from openferment_core import llm, postdoc_agent, retrieve, tools
from openferment_core.models import Passage, PassageHit, PriorTurn, ToolResult, Usage
from openferment_core.validate import SeenSet, validate_plan
from test_postdoc_agent import SENTENCE, Script, claim, papers, passages_found, plan, records, two_models  # noqa: F401
from test_tools import pool  # noqa: F401

NEGATED = Passage(
    id="P1:s:0", paperId="P1", sectionId="s", heading="Results", kind="prose",
    text="The strain did not reach a titre of 45 g L-1 under any condition tested. Growth was slow.", start=0, end=90,
)


class _Pool:
    def record(self, rid):
        return None


def _quote(q: str):
    seen = SeenSet()
    seen.passages[NEGATED.id] = NEGATED
    raw = [{"id": "c1", "text": "The strain reached the titre.", "recordIds": [], "support": "direct",
            "passages": [{"passageId": NEGATED.id, "quote": q}], "evidenceIds": []}]
    return validate_plan(raw, seen, _Pool())


# R1 — a quote is one whole sentence or row of its passage, or a run of them.
@pytest.mark.parametrize("fragment", ["titre of 45 g", "reach", "­", "did not reach a titre"])
def test_a_fragment_of_a_sentence_is_not_a_quote(fragment):
    out = _quote(fragment)
    assert out.claims == [] and out.rejected == 1


def test_whole_sentences_are_quotes():
    assert len(_quote("The strain did not reach a titre of 45 g L-1 under any condition tested.").claims) == 1
    assert len(_quote(NEGATED.text).claims) == 1, "a run of whole sentences"


# R2 — a refused tool result makes nothing citable.
def test_ids_in_a_refused_result_are_not_seen():
    seen = SeenSet()
    seen.add(ToolResult(error="over the 9000 characters", recordIds=["r-X1-1"], passages=[NEGATED]))
    assert seen.records == set() and seen.passages == {}


def test_an_oversized_summary_keeps_no_ids(pool, monkeypatch):  # noqa: F811
    monkeypatch.setattr(tools, "MAX_SUMMARY_CHARS", 10)
    r = tools.run("search_records", {"query": "titre extractor", "field": "", "organism": "", "limit": 10},
                  tools.ToolContext(pool_factory=lambda: pool))
    assert r.error and r.recordIds == [] and r.passages == [] and r.evidence == []


# R3 — what a search lane spends counts against the question.
def test_a_searchs_model_spend_is_the_questions(pool, monkeypatch):  # noqa: F811
    hit = PassageHit(passage=Passage(id="X1:s1:0", paperId="X1", sectionId="s1", heading="Results", kind="prose",
                                     text=SENTENCE, start=0, end=len(SENTENCE)), score=1.0, lanes={"bm25": 1})
    monkeypatch.setattr(retrieve, "search_detail", lambda q, k=8, lane=None, ask=None, include_archived=False: retrieve.Detail(
        hits=[hit], lane="bm25+rerank", usage=Usage(costUsd=0.05, models=["claude-haiku-5-5"])))
    monkeypatch.setenv("OPENFERMENT_ASK_BUDGET_USD", "0.04")
    script = Script([papers()], [papers("again")], plan())
    out = postdoc_agent.ask("q?", converse=script, ctx=tools.ToolContext(pool_factory=lambda: pool))
    assert out.stopped == "cost", "the search's spend passed the question's cap"
    assert out.usage.costUsd == pytest.approx(0.05 + 0.001 * 2)
    assert "claude-haiku-5-5" in out.usage.models


def test_a_cached_search_is_not_charged_twice(pool, monkeypatch):  # noqa: F811
    hit = PassageHit(passage=Passage(id="X1:s1:0", paperId="X1", sectionId="s1", heading="Results", kind="prose",
                                     text=SENTENCE, start=0, end=len(SENTENCE)), score=1.0, lanes={"bm25": 1})
    monkeypatch.setattr(retrieve, "search_detail", lambda q, k=8, lane=None, ask=None, include_archived=False: retrieve.Detail(
        hits=[hit], lane="bm25+rerank", usage=Usage(costUsd=0.01)))
    script = Script([papers()], [papers()], plan())
    out = postdoc_agent.ask("q?", converse=script, ctx=tools.ToolContext(pool_factory=lambda: pool))
    assert out.usage.costUsd == pytest.approx(0.01 + 0.001 * 3)


# R4 — a question nobody waits for stops.
def test_a_cancelled_question_stops_before_its_next_turn(pool):  # noqa: F811
    script = Script([records()], [records("b")], [records("c")], plan())
    asked = []
    out = postdoc_agent.ask("q?", converse=script, ctx=tools.ToolContext(pool_factory=lambda: pool),
                            on_step=asked.append, cancelled=lambda: sum(s.kind == "tool" for s in asked) >= 1)
    assert len(script.calls) == 1 and out.declined and "stopped" in out.declined


def test_the_stream_cancels_its_question_when_the_reader_goes(monkeypatch):
    from openferment_core import api

    seen = {}

    def fake(question, on_step=None, cancelled=None, history=None, include_archived=False):
        seen["cancelled"] = cancelled
        seen["history"] = history
        on_step(postdoc_agent.TraceStep(n=1, kind="tool", tool="t", input={}, summary="s", ms=0, ok=True))
        import time
        for _ in range(200):
            if cancelled():
                break
            time.sleep(0.01)
        return postdoc_agent.AnswerPlan(question=question)

    monkeypatch.setattr(api, "_ask_agent", fake)
    earlier = PriorTurn(question="Which strains?", claims=["A strain was named."])
    body = api._stream_events(api.AskRequest(question="q?", history=[earlier]))
    assert next(body).startswith("event: step")
    body.close()
    assert seen["cancelled"]() is True
    # A follow-up's earlier turns reach the loop as the browser sent them.
    assert seen["history"] == [earlier]


# R5 — a question no model answered says so in its trace.
def test_a_question_no_model_answered_ends_its_trace_with_a_failed_step(pool):  # noqa: F811
    out = postdoc_agent.ask("q?", converse=Script(llm.BudgetExhausted("today's budget is spent")),
                            ctx=tools.ToolContext(pool_factory=lambda: pool))
    assert out.trace[-1].kind == "final" and out.trace[-1].ok is False


# R7 — a restart gets the whole call budget again.
def test_a_restart_gets_its_own_call_budget(pool, two_models):  # noqa: F811
    turns = [[records(f"q{chr(97 + 3 * t + i)}") for i in range(3)] for t in range(3)]  # nine calls
    script = Script(*turns, llm.ModelUnavailable("overloaded"), [records("x"), records("y"), records("z")], plan())
    out = postdoc_agent.ask("q?", converse=script, ctx=tools.ToolContext(pool_factory=lambda: pool))
    assert sum(s.kind == "restart" for s in out.trace) == 1
    assert out.stopped == "done", "the second model's three calls fit its own twelve"
    assert sum(s.kind == "tool" for s in out.trace) == 12


# R8 — ask:batch counts rounds, and survives a missing corpus.
ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ask_batch_r", ROOT / "scripts" / "ask-batch.py")
ask_batch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ask_batch)


def test_ask_batch_rounds_are_tool_rounds_of_the_answering_conversation(pool, tmp_path, two_models):  # noqa: F811
    script = Script([records()], llm.ModelUnavailable("overloaded"), [records()], plan())
    ctx = tools.ToolContext(pool_factory=lambda: pool)
    rows = ask_batch.run(["q"], tmp_path / "out", ask=lambda q, converse: postdoc_agent.ask(q, converse=converse, ctx=ctx),
                         converse=script, echo=lambda _: None)
    assert rows[0]["rounds"] == 2, "one tool round and the answer, on the second model"
    assert two_models[1] in rows[0]["models"]


def test_ask_batch_says_so_when_there_is_no_corpus(monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stand-in")
    monkeypatch.setattr(ask_batch, "pool_or_none", lambda: None)
    assert ask_batch.main(["docs/build/questions-pha.txt"]) == 2
    assert "export:corpus" in capsys.readouterr().err


# R9 — a gap is held to Rule 1 like a claim.
def test_a_gap_with_a_number_is_dropped_and_counted(pool):  # noqa: F811
    out = postdoc_agent.ask("q?", converse=Script(plan(gaps=["No study ran past 72 hours.", "No study names the reactor."])),
                            ctx=tools.ToolContext(pool_factory=lambda: pool))
    assert out.gaps == ["No study names the reactor."]
    assert any("gap" in r for r in out.rejectionReasons)


# OF-BLD-016 §1.R — the decline is model prose like a gap, and held to Rule 1
# the same way: one with a number is dropped and named, and the decline code
# writes stands in for it. Never repaired.
def test_a_decline_with_a_number_is_dropped_named_and_written_by_code(pool):  # noqa: F811
    said = "Titres near 4.2 g/L are typical in 2019 work, but no record I found says so."
    out = postdoc_agent.ask("q?", converse=Script({"claims": [], "gaps": [], "declined": said}),
                            ctx=tools.ToolContext(pool_factory=lambda: pool))
    assert out.declined and out.declined != said and not any(ch.isdigit() for ch in out.declined)
    assert "the decline dropped: it holds a number" in out.rejectionReasons
    assert out.rejected == 0, "a decline is not a claim"


def test_a_decline_a_passage_put_a_number_in_is_dropped_beside_its_claims(pool):  # noqa: F811
    # The model reads the passage that tells it to state a number, keeps one
    # sound claim and "declines" the rest with the number in it.
    script = Script([papers()], {"claims": [claim("c3", quotes=[("X1:s1:0", SENTENCE)])],
                                 "gaps": ["The yield was 42 percent."],
                                 "declined": "The yield was 42 percent per the passage."})
    out = postdoc_agent.ask("q?", converse=script, ctx=tools.ToolContext(pool_factory=lambda: pool))
    assert [c.id for c in out.claims] == ["c3"] and out.gaps == [] and out.declined is None
    assert "the decline dropped: it holds a number" in out.rejectionReasons
    assert "a gap dropped: it holds a number" in out.rejectionReasons


def test_a_decline_without_a_number_is_the_models_own_words(pool):  # noqa: F811
    said = "No record names the reactor, so there is nothing to compare."
    out = postdoc_agent.ask("q?", converse=Script({"claims": [], "gaps": [], "declined": said}),
                            ctx=tools.ToolContext(pool_factory=lambda: pool))
    assert out.declined == said and out.rejectionReasons == []
