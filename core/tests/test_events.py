"""A project's event stream (events.py; execution prompt §7.3 item 2, §4.8), offline.

An event is said in one project and read there alone, and nothing is said where
no project is open. A page that reconnects with the last id it read is sent what
it missed, then what happens, then a comment while nothing does; a page that
names no event is sent what happens from when it opens; an event said while a
page opens its stream is sent once; a page that falls behind is closed and reads
the rest when it reconnects. `GET /api/events` is that stream for the request's
project. A question says its turn, each step, each tool call and what it answered,
then its plan or its decline; an engine run (test_runs' stand-in worker) says its
job queued, running and done or failed in the plant's words, and the artifact it
kept; a run answered from its row says nothing.
"""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from conftest import TEST_PROJECT
from openferment_core import api, events, evidence_pool, llm, projects
from openferment_core.engine import library, runs, simulator
from test_postdoc_agent import Script, claim, passages_found, plan, records  # noqa: F401
from test_runs import StandIn, worker  # noqa: F401
from test_tools import pool  # noqa: F401

BEAT = ": keepalive\n\n"


@pytest.fixture()
def client():
    return TestClient(api.app, base_url="http://127.0.0.1")


def said(body: str) -> list[dict]:
    """The events of a server-sent body, each its id, its type and its data; comments left out."""
    out = []
    for block in body.split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if line and not line.startswith(":"))
        if fields:
            out.append({"id": int(fields["id"]), "event": fields["event"], "data": json.loads(fields["data"])["data"]})
    return out


def ending(monkeypatch, passes: int) -> None:
    """`GET /api/events` ends after `passes` passes of its loop, as a page that closes it."""
    original = events.stream

    def stream(project, after=None, **_):
        left = iter(range(passes))
        return original(project, after, heartbeat_s=0.001, until=lambda: next(left, None) is None)

    monkeypatch.setattr(events, "stream", stream)


def test_an_event_is_said_in_its_project_and_read_there_alone():
    start = events.newest()
    here = events.publish("tool.call", {"tool": "search_records"})
    events.publish("tool.call", {"tool": "search_records"}, project="another-project")
    assert [e.id for e in events.recent(TEST_PROJECT, start)] == [here.id]
    assert (here.project, here.type, here.data) == (TEST_PROJECT, "tool.call", {"tool": "search_records"})
    assert events.newest() == here.id + 1
    with projects.using(None):
        assert events.publish("tool.call", {}) is None, "a command acting in no project says nothing"
    with pytest.raises(ValueError, match="not an event type"):
        events.publish("tool.made-up", {})


def test_a_page_is_sent_what_it_missed_then_what_happens_then_a_keepalive():
    start = events.newest()
    missed = events.publish("job.queued", {"id": "r1"})

    async def page():
        s = events.stream(TEST_PROJECT, start, heartbeat_s=0.01)
        first = await anext(s)
        events.publish("job.done", {"id": "r1"}, project="another-project")
        live = events.publish("job.running", {"id": "r1"})
        out = [first, await anext(s), await anext(s)]
        await s.aclose()
        return out, live

    (first, second, beat), live = asyncio.run(page())
    assert (first, second, beat) == (events.sse(missed), events.sse(live), BEAT)
    assert all(owner != TEST_PROJECT for owner, _ in events._readers.values()), "a page gone is sent nothing more"


def test_a_page_that_names_no_event_is_sent_what_happens_from_when_it_opens():
    events.publish("job.queued", {"id": "before the page"})

    async def page():
        s = events.stream(TEST_PROJECT, heartbeat_s=0.01)
        beat = await anext(s)
        live = events.publish("job.running", {"id": "after it opened"})
        sent = await anext(s)
        await s.aclose()
        return beat, sent, live

    beat, sent, live = asyncio.run(page())
    assert (beat, sent) == (BEAT, events.sse(live))


def test_an_event_said_while_a_page_opens_its_stream_is_sent_once(monkeypatch):
    start = events.newest()
    kept = events.recent

    def racing(project, after=0):
        events.publish("artifact.kept", {"id": "a1"})  # in the page's inbox and among the kept both
        return kept(project, after)

    monkeypatch.setattr(events, "recent", racing)

    async def page():
        s = events.stream(TEST_PROJECT, start, heartbeat_s=0.01)
        out = [await anext(s), await anext(s)]
        await s.aclose()
        return out

    sent, beat = asyncio.run(page())
    assert said(sent)[0]["data"] == {"id": "a1"} and beat == BEAT


def test_a_page_that_falls_behind_is_closed_and_reads_the_rest_when_it_reconnects(monkeypatch):
    monkeypatch.setattr(events, "BEHIND", 2)

    async def page():
        s = events.stream(TEST_PROJECT, heartbeat_s=0.01)
        await anext(s)  # open, nothing yet
        sent = [events.publish("turn.delta", {"n": n}) for n in range(3)]
        read = [x async for x in s]
        again = events.stream(TEST_PROJECT, sent[1].id, heartbeat_s=0.01)
        rest = await anext(again)
        await again.aclose()
        return sent, read, rest

    sent, read, rest = asyncio.run(page())
    assert read == [events.sse(sent[0]), events.sse(sent[1])], "two read, then the stream ends"
    assert rest == events.sse(sent[2])


def test_the_route_streams_the_projects_events_and_resumes_after_the_last_a_page_read(client, monkeypatch):
    ending(monkeypatch, passes=3)
    start = events.newest()
    one = events.publish("job.queued", {"id": "r1"})
    two = events.publish("job.done", {"id": "r1"})
    events.publish("job.done", {"id": "r2"}, project="another-project")
    got = client.get("/api/events", params={"after": start})
    assert got.headers["content-type"].startswith("text/event-stream") and got.headers["cache-control"] == "no-cache"
    assert [(e["id"], e["event"], e["data"]) for e in said(got.text)] == [
        (one.id, "job.queued", {"id": "r1"}), (two.id, "job.done", {"id": "r1"})]
    assert BEAT in got.text
    resumed = client.get("/api/events", headers={"Last-Event-ID": str(one.id)})
    assert [e["id"] for e in said(resumed.text)] == [two.id]
    named = client.get("/api/events", params={"after": start, "project": TEST_PROJECT}, headers={projects.HEADER: ""})
    assert [e["id"] for e in said(named.text)] == [one.id, two.id], "an EventSource names its project in the address"
    assert said(client.get("/api/events").text) == [], "a page that names no event is sent what happens from now"


def test_a_question_says_its_turn_each_step_each_call_and_its_plan(client, pool, monkeypatch):  # noqa: F811
    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: pool)
    monkeypatch.setattr(llm, "converse", Script([records()], plan(claim(records=["r-X1-1"]))))
    start = events.newest()
    body = client.post("/api/ask", json={"question": "How much PHB?", "conversationId": "lc-1", "turnId": "t-1",
                                         "by": "Ada Moreno"}).json()
    sent = events.recent(TEST_PROJECT, start)
    types = [e.type for e in sent]
    assert types[0] == "turn.started" and types[-1] == "turn.plan"
    assert types.index("tool.call") < types.index("tool.result")
    assert types.count("turn.delta") == len(body["trace"])
    assert all((e.data["conversationId"], e.data["turnId"]) == ("lc-1", "t-1") for e in sent)
    started, result = sent[0].data, next(e.data for e in sent if e.type == "tool.result")
    assert (started["seq"], started["question"], started["by"]) == (1, "How much PHB?", "Ada Moreno")
    assert (result["tool"], result["ok"], result["error"]) == ("search_records", True, None)
    assert sent[-1].data["plan"]["claims"] == body["claims"]

    monkeypatch.setattr(llm, "converse", Script({"claims": [], "gaps": [], "declined": "The corpus holds nothing on this."}))
    start = events.newest()
    client.post("/api/ask", json={"question": "And on glucose?", "conversationId": "lc-1", "turnId": "t-2"})
    assert [e.type for e in events.recent(TEST_PROJECT, start)][-1] == "turn.decline"


def test_an_engine_run_says_its_job_and_the_artifact_it_kept(worker):  # noqa: F811
    start = events.newest()
    rep = runs.run("sugarcane", by="Ada Moreno")
    sent = events.recent(TEST_PROJECT, start)
    assert [(e.type, e.data["id"]) for e in sent] == [
        ("job.queued", rep.run.id), ("job.running", rep.run.id), ("artifact.kept", rep.run.artifactId),
        ("job.done", rep.run.id)]
    job = sent[0].data
    assert (job["kind"], job["plant"], job["configuration"], job["scenarioId"], job["by"]) == (
        "engine.run", "sugarcane", None, None, "Ada Moreno")
    kept, done = sent[2].data, sent[3].data
    assert (kept["tool"], kept["provenance"]) == (library.LIBRARY_RUN, rep.artifact.provenance)
    assert (done["status"], done["provenance"], done["artifactId"], done["sffRecordId"]) == (
        "done", rep.run.provenance, rep.run.artifactId, rep.run.sff.recordId)
    start = events.newest()
    runs.run("sugarcane", by="Ada Moreno")
    assert events.recent(TEST_PROJECT, start) == [], "a run answered from its row is no job"


def test_a_run_the_plant_refuses_says_its_job_failed_in_the_plants_words(monkeypatch):
    monkeypatch.setattr(simulator, "call", StandIn(refuse="infeasible here (BioSTEAM's InfeasibleRegion): M207 NH3 over 100 %"))
    start = events.newest()
    with pytest.raises(library.LibraryRefused):
        runs.run("sugarcane", by="Ada Moreno")
    *_, failed = events.recent(TEST_PROJECT, start)
    assert (failed.type, failed.data["status"]) == ("job.failed", "refused") and "M207" in failed.data["words"]
