"""The per-request key override (owner question 10, 2 November 2026; ADR-008).

A request may name its own Anthropic key in `X-OpenFerment-Key`: its model
calls, openFerment's and the kit's, run on it in place of core/.env's, and a
request that names none runs on core/.env's. The key is never stored, logged
or echoed: the audit row says an override was used, and nothing else of it is
kept. The negative test: a request on an override, then the key looked for in
every log line, every response and every row of every table of both schemas.

The Anthropic client is a stand-in that keeps the key it was built with and
answers each message with an empty plan, so the real call path runs to it.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from openferment_core import api, audit, db, evidence_pool, guard, llm
from test_tools import pool  # noqa: F401

OVERRIDE = "sk-ant-api03-OVERRIDE-negative-test-0123456789abcdef"
ENV_KEY = "sk-ant-api03-core-env-key-of-the-test"


class Made:
    """The keys every stand-in client was built with, in order."""

    keys: list[str] = []


class _Stream:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        plan = {"claims": [], "gaps": [], "declined": None}
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(plan))], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0,
                                                     cache_creation_input_tokens=0), model=llm.DEFAULT_PRIMARY)


class StandInAnthropic:
    def __init__(self, **kw):
        Made.keys.append(kw.get("api_key"))
        self.messages = self

    def stream(self, **request):
        return _Stream()


@pytest.fixture()
def client(pool, monkeypatch):  # noqa: F811
    Made.keys = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", ENV_KEY)
    monkeypatch.setattr(llm, "make_client", lambda **kw: StandInAnthropic(**kw))
    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: pool)
    return TestClient(api.app, base_url="http://127.0.0.1")


async def _rows_holding(needle: str) -> list[str]:
    """Every table of both schemas whose rows, read as text, hold `needle`."""
    found = []
    async with db.session() as s:
        tables = (await s.execute(text(
            "select table_schema, table_name from information_schema.tables "
            "where table_schema in ('openferment', 'sci_rag') and table_type = 'BASE TABLE'"))).all()
        for schema, name in tables:
            hits = (await s.execute(text(
                f'select count(*) from "{schema}"."{name}" as r where cast(r as text) like :n'), {"n": f"%{needle}%"})
            ).scalar_one()
            if hits:
                found.append(f"{schema}.{name}")
    return found


def test_a_named_key_serves_the_requests_calls_and_appears_nowhere(client, caplog):
    caplog.set_level(logging.DEBUG)
    named = client.post("/api/ask", json={"question": "What does the plant solve?"}, headers={llm.KEY_HEADER: OVERRIDE})
    assert named.status_code == 200, named.text
    assert Made.keys and set(Made.keys) == {OVERRIDE}, "every call of the request ran on the key it named"

    Made.keys = []
    plain = client.post("/api/ask", json={"question": "And on core/.env's key?"})
    assert plain.status_code == 200 and set(Made.keys) == {ENV_KEY}, "a request that names none runs on core/.env's"

    # The audit row says an override was used, and holds nothing of the key.
    lines = [a for a in audit.read() if a.action == "key_override"]
    assert len(lines) == 1 and lines[0].detail == {"override": True} and lines[0].target == "POST /api/ask"

    # Nowhere: no log line, no response (body or headers), no row of any table.
    assert not [r.getMessage() for r in caplog.records if OVERRIDE in r.getMessage()]
    for r in (named, plain):
        assert OVERRIDE not in r.text and OVERRIDE not in json.dumps(dict(r.headers))
    assert db.run(_rows_holding(OVERRIDE)) == []
    assert db.run(_rows_holding("OVERRIDE-negative-test")) == [], "nor a piece of it"


def test_the_kits_calls_and_the_requests_threads_reach_the_named_key(monkeypatch):
    Made.keys = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", ENV_KEY)
    monkeypatch.setattr(llm, "make_client", lambda **kw: StandInAnthropic(**kw))
    with llm.request_key(OVERRIDE):
        assert llm.key_named()
        # The kit calls `llm.call` on asyncio's worker thread, which copies the context.
        asyncio.run(asyncio.to_thread(llm._default_client))
        # A thread the request starts as the ask stream does.
        t = threading.Thread(target=contextvars.copy_context().run, args=(llm._default_client,))
        t.start()
        t.join()
    llm._default_client()
    assert Made.keys == [OVERRIDE, OVERRIDE, ENV_KEY] and not llm.key_named()


def test_a_key_is_refused_from_the_public_internet_and_never_repeated(client):
    r = client.post("/api/ask", json={"question": "q"}, headers={llm.KEY_HEADER: OVERRIDE, guard.FUNNEL: "1"})
    assert r.status_code == 403 and "Funnel" in r.json()["detail"] and OVERRIDE not in r.text
    assert Made.keys == [], "no call was made"
    hostile = client.post("/api/ask", json={"question": "q"}, headers={llm.KEY_HEADER: OVERRIDE, "host": "evil.example"})
    assert hostile.status_code == 403 and OVERRIDE not in hostile.text
    empty = client.post("/api/ask", json={"question": "q"}, headers={llm.KEY_HEADER: "  "})
    assert empty.status_code == 422 and "names no key" in empty.json()["detail"]


def test_a_rejected_named_key_is_said_to_be_the_requests():
    import anthropic
    import httpx

    def refuse(**kw):
        class C:
            messages = None

            def __init__(self):
                self.messages = self

            def stream(self, **request):
                raise anthropic.AuthenticationError(
                    "invalid x-api-key", response=httpx.Response(401, request=httpx.Request("POST", "https://x")),
                    body=None)

        return C()

    with llm.request_key(OVERRIDE), pytest.raises(llm.ModelUnavailable) as e:
        llm.call(system="", user="q", schema=None, max_tokens=10, client_factory=refuse, family="explain")
    assert "the key this request named" in str(e.value) and OVERRIDE not in str(e.value)
