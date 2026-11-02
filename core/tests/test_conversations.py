"""Postdoc's conversations on the service (postdoc/conversations.py; execution prompt
§4.8; ADR-008), offline.

The model is test_postdoc_agent's scripted stand-in and the pool is test_tools'
stand-in fixture. A question asked in a conversation is kept as a turn: its
steps, its plan, who asked, each tool call with what it answered the model and
what it offered to cite, and the artifacts the calls produced; a follow-up reads
its history from what the service keeps, whatever the caller sends. A page's
write of a Live conversation lands on the same store: a turn the service lacks
is kept as the page wrote it, a turn it holds stays as it kept it, and a turn the
page wrote `running` before its ask arrived is taken over by the ask. A turn is
asked once; one nobody is answering reads `interrupted`; a conversation is never
taken back.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import api, audit, evidence_pool, llm, project_state
from openferment_core.models import ComputedBasis, Evidence, ToolResult
from openferment_core.postdoc import conversations
from test_postdoc_agent import SENTENCE, Script, claim, papers, passages_found, plan, records  # noqa: F401
from test_tools import pool  # noqa: F401


@pytest.fixture()
def client(pool, monkeypatch):  # noqa: F811
    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: pool)
    return TestClient(api.app, base_url="http://127.0.0.1")


def script_in(monkeypatch, *turns) -> Script:
    script = Script(*turns)
    monkeypatch.setattr(llm, "converse", script)
    return script


def asked(client, question, **ids):
    return client.post("/api/ask", json={"question": question, "by": "Ada Moreno", **ids}).json()


def page_turn(tid, question, status="answered", **kw):
    return {"id": tid, "question": question, "askedAt": "2026-10-30T07:00:00Z", "steps": [], "plan": None, "error": None,
            "status": status, **kw}


def page(cid, *turns):
    return {"id": cid, "title": turns[0]["question"] if turns else "", "startedAt": "2026-10-30T07:00:00Z", "turns": list(turns)}


def test_a_question_is_kept_as_a_turn_with_its_steps_its_plan_and_its_calls(client, monkeypatch):
    script_in(monkeypatch, [records()], plan(claim(records=["r-X1-1"])))
    body = asked(client, "How much PHB?", conversationId="lc-1", turnId="t-1")
    assert (body["conversationId"], body["turnId"]) == ("lc-1", "t-1")
    held = client.get("/api/conversations/lc-1").json()
    assert held["title"] == "How much PHB?" and [x["id"] for x in held["turns"]] == ["t-1"]
    (turn,) = held["turns"]
    assert (turn["status"], turn["by"], turn["question"]) == ("answered", "Ada Moreno", "How much PHB?")
    assert turn["steps"] == body["trace"] and turn["plan"]["claims"] == body["claims"]
    (call,) = client.get("/api/conversations/lc-1/turns/t-1/calls").json()
    assert (call["tool"], call["turnId"], call["by"], call["error"]) == ("search_records", "t-1", "Ada Moreno", None)
    assert "r-X1-1" in call["recordIds"] and call["input"]["query"] == "titre extractor"
    assert [c["id"] for c in client.get("/api/conversations").json()] == ["lc-1"]
    assert [(a.action, a.target) for a in audit.read() if a.action == "keep_conversations"] == [("keep_conversations", "lc-1")]


def test_a_follow_up_reads_its_history_from_the_service_whatever_the_caller_sends(client, monkeypatch):
    script_in(monkeypatch, [records()], plan(claim(records=["r-X1-1"])))
    first = asked(client, "Which polymer was reported?", conversationId="lc-1", turnId="t-1")
    assert [c["text"] for c in first["claims"]] == ["Polyhydroxybutyrate titre was reported on xylose hydrolysate."]
    script = script_in(monkeypatch, plan())
    client.post("/api/ask", json={"question": "And on glucose?", "conversationId": "lc-1", "turnId": "t-2",
                                  "history": [{"question": "a history the caller made up", "claims": [], "gaps": []}]})
    opening = str(script.calls[0]["messages"])
    assert "Which polymer was reported?" in opening and "Polyhydroxybutyrate titre was reported" in opening
    assert "a history the caller made up" not in opening
    assert [x.question for x in conversations.history("lc-1")] == ["Which polymer was reported?", "And on glucose?"]


def test_a_turn_is_asked_once_and_ids_are_the_pages_or_the_services(client, monkeypatch):
    script_in(monkeypatch, plan())
    asked(client, "How much PHB?", conversationId="lc-1", turnId="t-1")
    again = asked(client, "How much PHB, again?", conversationId="lc-1", turnId="t-1")
    assert "asked once" in again["declined"] and again.get("turnId") is None
    made = asked(client, "A question with no ids")
    assert made["conversationId"].startswith("lc-") and made["turnId"].startswith("turn-")
    assert asked(client, "q", conversationId="has space")["declined"].startswith("'has space' is not an id")


def test_a_pages_write_lands_on_the_store_and_the_services_turns_stand(client, monkeypatch):
    script_in(monkeypatch, plan())
    asked(client, "How much PHB?", conversationId="lc-1", turnId="t-1")
    failed = page_turn("t-0", "Asked while the service was away", "failed",
                       error={"message": "Postdoc service not running.", "remedy": "Start it."})
    project_state.put("conversations", "lc-1", page("lc-1", page_turn("t-1", "How much PHB?", "failed"), failed), "Ada Moreno")
    held = {x.id: x for x in conversations.get("lc-1").turns}
    assert held["t-1"].status == "answered", "the service's turn stands"
    assert held["t-0"].status == "failed" and held["t-0"].error.message == "Postdoc service not running."
    project_state.put("conversations", "lc-2", page("lc-2", page_turn("t-5", "A conversation from an older browser")),
                      "Ada Moreno")
    assert [c["id"] for c in project_state.load()["conversations"]] == ["lc-1", "lc-2"]
    with pytest.raises(project_state.StateRefused, match="belongs to conversation lc-1"):
        project_state.put("conversations", "lc-2", page("lc-2", page_turn("t-1", "moved")), "Ada Moreno")


def test_a_turn_the_page_writes_running_before_its_ask_is_taken_over_by_the_ask(client, monkeypatch):
    project_state.put("conversations", "lc-1", page("lc-1", page_turn("t-1", "How much PHB?", "running")), "Ada Moreno")
    assert conversations.get("lc-1").turns[0].status == "interrupted", "nobody is answering it yet"
    script_in(monkeypatch, plan())
    body = asked(client, "How much PHB?", conversationId="lc-1", turnId="t-1")
    assert body["turnId"] == "t-1" and conversations.get("lc-1").turns[0].status == "answered"
    assert len(conversations.get("lc-1").turns) == 1


def test_a_turn_nobody_is_answering_reads_interrupted_and_its_page_record_stands(client):
    cid, tid, seq = conversations.begin("How much PHB?", conversation_id="lc-1", turn_id="t-1", by="Ada Moreno")
    assert (cid, tid, seq) == ("lc-1", "t-1", 1) and conversations.get("lc-1").turns[0].status == "running"
    conversations._answering.discard((conversations.projects.current(), "t-1"))  # the process answering it stopped
    assert conversations.get("lc-1").turns[0].status == "interrupted"
    project_state.put("conversations", "lc-1", page("lc-1", page_turn("t-1", "How much PHB?", "stopped")), "Ada Moreno")
    assert conversations.get("lc-1").turns[0].status == "stopped"


def test_a_turn_names_the_artifacts_its_calls_produced():
    cid, tid, _ = conversations.begin("What does the run cost?", conversation_id="lc-1", turn_id="t-1", by="Ada Moreno")
    basis = ComputedBasis(tool="library.run", toolVersion="library run 2", inputs=[], artifactId="0123456789abcdef",
                          at="2026-10-30T07:00:00Z")
    result = ToolResult(summary={"price": "the solved price"}, evidence=[Evidence(
        id="ev-1", label="Minimum selling price", value=0.66, unit="USD/kg", provenance="computed", basis=basis)])
    assert conversations.called(tid, "engine_run", {"plant": "cornstover"}, result, by="Ada Moreno") == ["0123456789abcdef"]
    conversations.finish(tid, plan=None, steps=[], artifacts=["0123456789abcdef"])
    (turn,) = conversations.get(cid).turns
    assert turn.artifactIds == ["0123456789abcdef"] and turn.status == "answered"
    (call,) = conversations.calls(cid, tid)
    assert (call.tool, call.evidenceIds, call.artifactIds) == ("engine_run", ["ev-1"], ["0123456789abcdef"])


def test_the_routes_say_what_the_project_does_not_hold(client):
    assert client.get("/api/conversations").json() == []
    assert client.get("/api/conversations/lc-none").status_code == 404
    conversations.begin("q", conversation_id="lc-1", turn_id="t-1")
    assert client.get("/api/conversations/lc-1/turns/t-none/calls").status_code == 404
