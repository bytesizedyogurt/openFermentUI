"""`POST /api/ask` and `POST /api/ask/stream` (OF-BLD-014 §5.3), offline.

The model is test_postdoc_agent's scripted stand-in and the pool is
test_tools' stand-in fixture.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, evidence_pool, llm
from test_postdoc_agent import SENTENCE, Script, claim, papers, passages_found, plan, records  # noqa: F401
from test_tools import pool  # noqa: F401


@pytest.fixture()
def client(pool, monkeypatch):  # noqa: F811
    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: pool)
    return TestClient(api.app, base_url="http://127.0.0.1")


def script_in(monkeypatch, *turns) -> Script:
    script = Script(*turns)
    monkeypatch.setattr(llm, "converse", script)
    return script


def events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_ask_runs_the_loop_by_default(client, monkeypatch):
    script = script_in(monkeypatch, [records()], plan(claim(records=["r-X1-1"])))
    body = client.post("/api/ask", json={"question": "How much PHB?"}).json()
    assert len(script.calls) == 2
    assert [c["recordIds"] for c in body["claims"]] == [["r-X1-1"]]
    assert [s["kind"] for s in body["trace"]] == ["coverage", "tool", "final"] and body["stopped"] == "done"


def test_single_mode_is_one_call_with_no_tools(client, monkeypatch):
    monkeypatch.setattr(llm, "converse", lambda **kw: pytest.fail("single mode called the loop"))
    seen = []

    def one_call(question, records, corpus):
        seen.append(question)
        return {"claims": [], "gaps": [], "declined": "nothing in the stand-in"}, llm.Usage()

    monkeypatch.setattr(api, "ask_model", one_call)
    monkeypatch.setattr(api, "load_corpus", lambda: evidence_pool.load().corpus)
    body = client.post("/api/ask", json={"question": "How much PHB?", "mode": "single"}).json()
    assert seen == ["How much PHB?"] and body["trace"] == [] and body["declined"] == "nothing in the stand-in"
    assert client.post("/api/ask", json={"question": "q", "mode": "loop"}).status_code == 422


def test_a_missing_corpus_declines_in_words(monkeypatch):
    def missing(include_archived=False):
        raise FileNotFoundError("no corpus.json")

    monkeypatch.setattr(evidence_pool, "load", missing)
    body = TestClient(api.app, base_url="http://127.0.0.1").post("/api/ask", json={"question": "q"}).json()
    assert body["declined"] == api.CORPUS_MISSING


def test_the_stream_sends_each_step_then_the_plan(client, monkeypatch):
    script_in(monkeypatch, [records()], [papers()], plan(claim(records=["r-X1-1"], quotes=[("X1:s1:0", SENTENCE)])))
    r = client.post("/api/ask/stream", json={"question": "How much PHB from xylose?"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    got = events(r.text)
    assert [e for e, _ in got] == ["step", "step", "step", "step", "plan"]
    assert [d["n"] for _, d in got[:4]] == [1, 2, 3, 4] and got[0][1]["kind"] == "coverage" and got[3][1]["kind"] == "final"
    final = got[-1][1]
    assert final["trace"] == [d for _, d in got[:4]], "the plan's trace is the steps that streamed"
    assert [p["id"] for p in final["passages"]] == ["X1:s1:0"]


def test_a_declined_plan_is_a_plan_event(client, monkeypatch):
    script_in(monkeypatch, llm.BudgetExhausted("today's budget is spent"))
    got = events(client.post("/api/ask/stream", json={"question": "q?"}).text)
    assert [e for e, _ in got] == ["step", "step", "plan"] and "budget" in got[2][1]["declined"]
    assert got[0][1]["kind"] == "coverage" and got[1][1]["kind"] == "final" and got[1][1]["ok"] is False


def test_a_failure_in_the_service_is_an_error_event(client, monkeypatch):
    def broken(*a, **kw):
        raise RuntimeError("stand-in fault")

    monkeypatch.setattr(api.postdoc_agent, "ask", broken)
    got = events(client.post("/api/ask/stream", json={"question": "q?"}).text)
    assert [e for e, _ in got] == ["error"] and "RuntimeError" in got[0][1]["message"]


def test_the_guard_covers_the_stream(client):
    r = client.post("/api/ask/stream", json={"question": "q?"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403



def test_single_mode_holds_its_gaps_and_its_decline_to_rule_one(client, monkeypatch):
    """OF-BLD-016 §1.R: the one-call path drops a gap or a decline holding a
    number and names it, as the loop does; the code-written decline stands in."""
    said = "Titres near 4.2 g/L are typical."

    def one_call(question, records, corpus):
        return {"claims": [], "gaps": ["No study ran past 72 hours.", "No study names the reactor."], "declined": said}, llm.Usage()

    monkeypatch.setattr(api, "ask_model", one_call)
    monkeypatch.setattr(api, "load_corpus", lambda: evidence_pool.load().corpus)
    body = client.post("/api/ask", json={"question": "How much PHB?", "mode": "single"}).json()
    assert body["gaps"] == ["No study names the reactor."]
    assert body["declined"] and body["declined"] != said and not any(ch.isdigit() for ch in body["declined"])
    assert "a gap dropped: it holds a number" in body["rejectionReasons"]
    assert "the decline dropped: it holds a number" in body["rejectionReasons"]
