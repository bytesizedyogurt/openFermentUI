"""The one place openFerment calls a model: Opus first, Sonnet when Opus
declines or is unavailable, JSON by schema, cost from the response.

Offline: a fake client stands in for the SDK, answering `messages.stream`
the way the real one does, with a context manager whose final message has a
`model`, `stop_reason`, `stop_details`, `content` and `usage`.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import anthropic
import pytest

from openferment_core import extract, llm, postdoc
from openferment_core.models import Usage

OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
URL = "https://api.anthropic.com/v1/messages"
SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "string"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "range": {
                        "type": "object",
                        "properties": {"low": {"type": "number"}, "high": {"type": "number"}},
                        "required": ["low", "high"],
                    },
                },
                "required": ["value"],
            },
        }
    },
    "required": ["candidates"],
}


def _http():
    try:
        import httpx2 as h
    except ImportError:  # pragma: no cover
        import httpx as h
    return h


def status_error(cls, code):
    h = _http()
    return cls(f"status {code}", response=h.Response(code, request=h.Request("POST", URL)), body=None)


def answer(model, text='{"candidates": []}', stop="end_turn", tin=1000, tout=500, category=None, thinking=True):
    content = [SimpleNamespace(type="thinking", thinking="")] if thinking else []
    if text is not None:
        content.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(
        model=model,
        stop_reason=stop,
        stop_details=SimpleNamespace(category=category) if stop == "refusal" else None,
        content=content if stop != "refusal" else [],
        usage=SimpleNamespace(input_tokens=tin, output_tokens=tout),
    )


class FakeClient:
    """`script` maps a model id to the message it answers, or to the error
    opening its stream raises. Every request is kept for inspection."""

    def __init__(self, script):
        self.script = script
        self.requests: list[dict] = []
        self.messages = self

    def stream(self, **kwargs):
        self.requests.append(kwargs)
        outcome = self.script[kwargs["model"]]
        client = self

        class Stream:
            def __enter__(self_inner):
                if isinstance(outcome, Exception):
                    raise outcome
                return self_inner

            def __exit__(self_inner, *exc):
                return False

            def get_final_message(self_inner):
                return outcome

        return Stream()

    @property
    def asked(self):
        return [r["model"] for r in self.requests]


@pytest.fixture(autouse=True)
def _default_chain(monkeypatch):
    for name in ("OPENFERMENT_MODEL", "OPENFERMENT_FALLBACK_MODEL", "OPENFERMENT_EFFORT"):
        monkeypatch.delenv(name, raising=False)


def run(client, schema=SCHEMA, max_tokens=4000):
    return llm.call(system="s", user="u", schema=schema, max_tokens=max_tokens, client_factory=lambda: client)


# ── the schema ─────────────────────────────────────────────────────────


def test_strict_schema_closes_every_object_and_moves_what_the_api_rejects():
    out = llm.strict_schema(SCHEMA)
    item = out["properties"]["candidates"]["items"]
    assert out["additionalProperties"] is False
    assert item["additionalProperties"] is False
    assert item["properties"]["range"]["additionalProperties"] is False
    confidence = item["properties"]["confidence"]
    assert "minimum" not in confidence and "maximum" not in confidence
    assert "minimum 0" in confidence["description"] and "maximum 1" in confidence["description"]
    assert item["properties"]["value"] == {"type": ["number", "string"]}, "a union type is accepted as it is"
    assert "additionalProperties" not in SCHEMA, "the caller's schema is left untouched"


# Written out from the structured-outputs docs
# (platform.claude.com/docs/en/build-with-claude/structured-outputs, read
# 2026-10-08), and kept apart from llm._UNSUPPORTED on purpose: a keyword
# dropped from that list must fail here.
DOCS_REJECT = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength"}


def test_the_real_schemas_come_out_strict():
    for schema in (postdoc.TOOL["input_schema"], extract.build_tool(["s1"], ["titer_secreted"])["input_schema"]):
        out = llm.strict_schema(schema)
        seen = []

        def walk(node):
            if isinstance(node, dict):
                if "properties" in node or node.get("type") == "object":
                    seen.append(node.get("additionalProperties"))
                for bad in DOCS_REJECT:
                    assert bad not in node, bad
                assert node.get("minItems", 0) <= 1, "minItems above 1 is rejected"
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(out)
        assert seen and all(v is False for v in seen)


# ── answers ────────────────────────────────────────────────────────────


def test_opus_answers_as_json_by_schema():
    client = FakeClient({OPUS: answer(OPUS, '{"candidates": [{"value": 4.2}]}')})
    result = run(client)
    assert result.data == {"candidates": [{"value": 4.2}]}
    assert result.model == OPUS and not result.fell_back and client.asked == [OPUS]
    request = client.requests[0]
    assert "tool_choice" not in request and "tools" not in request, "forced tool use is a 400 on these models"
    assert request["output_config"]["effort"] == "medium"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert request["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_cost_is_read_from_the_response_at_the_answering_models_price():
    result = run(FakeClient({OPUS: answer(OPUS, tin=100_000, tout=10_000)}))
    assert result.usage.inputTokens == 100_000 and result.usage.outputTokens == 10_000
    assert result.usage.costUsd == pytest.approx(100_000 / 1e6 * 4 + 10_000 / 1e6 * 20)
    assert result.usage.models == [OPUS]


def test_a_refusal_on_opus_is_answered_by_sonnet_and_both_are_paid_for():
    client = FakeClient({
        OPUS: answer(OPUS, stop="refusal", category="bio", tin=2000, tout=0),
        SONNET: answer(SONNET, '{"candidates": [{"value": 7}]}', tin=2000, tout=800),
    })
    result = run(client)
    assert client.asked == [OPUS, SONNET]
    assert result.model == SONNET and result.fell_back and result.data["candidates"][0]["value"] == 7
    assert result.usage.models == [OPUS, SONNET]
    assert result.usage.costUsd == pytest.approx(2000 / 1e6 * 4 + 2000 / 1e6 * 2 + 800 / 1e6 * 10)


def test_refused_by_both_raises_with_the_category():
    client = FakeClient({
        OPUS: answer(OPUS, stop="refusal", category="bio"),
        SONNET: answer(SONNET, stop="refusal", category="bio"),
    })
    with pytest.raises(llm.ModelRefused) as e:
        run(client)
    assert e.value.category == "bio" and e.value.models == [OPUS, SONNET]
    assert e.value.usage.models == [OPUS, SONNET] and e.value.usage.costUsd > 0


@pytest.mark.parametrize(("category", "billed"), [
    ("bio", True), ("frontier_llm", True), ("reasoning_extraction", True),
    ("cyber", False), ("general_harms", False), (None, False),
])
def test_a_refusal_before_any_output_is_billed_only_in_the_categories_anthropic_bills(category, billed):
    response = answer(OPUS, stop="refusal", category=category, tin=50_000, tout=0)
    used = llm.usage_of(response)
    assert used.inputTokens == 50_000 and used.models == [OPUS], "the tokens are counted either way"
    assert used.costUsd == (pytest.approx(50_000 / 1e6 * 4) if billed else 0.0)


def test_a_refusal_after_output_began_is_billed_whatever_the_category():
    used = llm.usage_of(answer(OPUS, stop="refusal", category="cyber", tin=1000, tout=300))
    assert used.costUsd == pytest.approx(1000 / 1e6 * 4 + 300 / 1e6 * 20)


def test_a_reasoning_extraction_refusal_is_not_sent_on_to_sonnet():
    client = FakeClient({OPUS: answer(OPUS, stop="refusal", category="reasoning_extraction"), SONNET: answer(SONNET)})
    with pytest.raises(llm.ModelRefused) as e:
        run(client)
    assert client.asked == [OPUS] and e.value.category == "reasoning_extraction"


def test_what_was_spent_before_an_outage_travels_with_the_failure():
    client = FakeClient({
        OPUS: answer(OPUS, stop="refusal", category="bio", tin=3000, tout=0),
        SONNET: status_error(anthropic.APIStatusError, 529),
    })
    with pytest.raises(llm.ModelUnavailable) as e:
        run(client)
    assert client.asked == [OPUS, SONNET]
    assert e.value.usage.models == [OPUS] and e.value.usage.costUsd == pytest.approx(3000 / 1e6 * 4)


@pytest.mark.parametrize(
    "error",
    [
        lambda: status_error(anthropic.NotFoundError, 404),
        lambda: status_error(anthropic.PermissionDeniedError, 403),
        lambda: status_error(anthropic.RateLimitError, 429),
        lambda: status_error(anthropic.InternalServerError, 500),
        lambda: status_error(anthropic.APIStatusError, 529),
    ],
)
def test_opus_unavailable_falls_back_to_sonnet(error):
    client = FakeClient({OPUS: error(), SONNET: answer(SONNET)})
    result = run(client)
    assert client.asked == [OPUS, SONNET] and result.model == SONNET and result.fell_back


def test_both_unavailable_is_unavailable():
    client = FakeClient({OPUS: status_error(anthropic.NotFoundError, 404),
                         SONNET: status_error(anthropic.APIStatusError, 529)})
    with pytest.raises(llm.ModelUnavailable):
        run(client)


@pytest.mark.parametrize(
    ("error", "says"),
    [
        (lambda: status_error(anthropic.AuthenticationError, 401), "rejected the key"),
        (lambda: status_error(anthropic.BadRequestError, 400), "malformed"),
        (lambda: anthropic.APIConnectionError(request=_http().Request("POST", URL)), "Could not reach"),
    ],
)
def test_what_another_model_would_also_fail_does_not_fall_back(error, says):
    client = FakeClient({OPUS: error(), SONNET: answer(SONNET)})
    with pytest.raises(llm.ModelUnavailable) as e:
        run(client)
    assert client.asked == [OPUS] and says in str(e.value)


def test_a_response_cut_off_is_reported_as_truncated_on_the_same_model():
    client = FakeClient({OPUS: answer(OPUS, '{"candidates": [{"val', stop="max_tokens")})
    result = run(client)
    assert result.truncated and result.data is None and client.asked == [OPUS]


def test_text_that_is_not_json_is_no_data():
    assert run(FakeClient({OPUS: answer(OPUS, "Here are the candidates: none.")})).data is None


def test_the_models_come_from_the_environment_at_call_time(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_MODEL", SONNET)
    monkeypatch.setenv("OPENFERMENT_FALLBACK_MODEL", SONNET)
    monkeypatch.setenv("OPENFERMENT_EFFORT", "high")
    client = FakeClient({SONNET: answer(SONNET, stop="refusal", category="bio")})
    with pytest.raises(llm.ModelRefused):
        run(client)
    assert client.asked == [SONNET], "one model named twice is asked once"
    assert client.requests[0]["output_config"]["effort"] == "high"


def test_the_fallback_can_name_several_models_tried_in_order(monkeypatch):
    third = "claude-opus-4-8"
    monkeypatch.setenv("OPENFERMENT_FALLBACK_MODEL", f"{SONNET}, {third}")
    assert llm.chain() == [OPUS, SONNET, third]
    client = FakeClient({
        OPUS: answer(OPUS, stop="refusal", category="bio"),
        SONNET: answer(SONNET, stop="refusal", category="bio"),
        third: answer(third, '{"candidates": [{"value": 3}]}'),
    })
    result = run(client)
    assert client.asked == [OPUS, SONNET, third] and result.model == third
    assert result.usage.models == [OPUS, SONNET, third]


def test_no_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.ModelUnavailable) as e:
        llm.call(system="s", user="u", schema=SCHEMA, max_tokens=10)
    assert "ANTHROPIC_API_KEY" in str(e.value)


# ── the two callers ────────────────────────────────────────────────────


def test_postdoc_turns_a_refusal_into_a_declined_plan_it_still_pays_for(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    spent = Usage(inputTokens=10, outputTokens=0, costUsd=0.01, models=[OPUS, SONNET])

    def refused(**_):
        raise llm.ModelRefused("bio", [OPUS, SONNET], spent)

    monkeypatch.setattr(llm, "call", refused)
    raw, usage = postdoc.ask_model("what is the titre", [], corpus=None)
    assert raw["claims"] == [] and "declined" in raw["declined"] and "bio" in raw["declined"]
    assert usage == spent


def test_postdoc_reports_an_unavailable_model_as_the_service_being_unavailable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")

    def down(**_):
        raise llm.ModelUnavailable("claude-opus-5-5 answered 529")

    monkeypatch.setattr(llm, "call", down)
    with pytest.raises(postdoc.PostdocUnavailable, match="529"):
        postdoc.ask_model("q", [], corpus=None)


def test_a_plan_that_failed_after_a_billed_refusal_still_shows_the_cost(monkeypatch):
    from openferment_core import api
    from openferment_core.models import AskRequest

    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    spent = Usage(inputTokens=3000, outputTokens=0, costUsd=0.012, models=[OPUS])

    def down(**_):
        raise llm.ModelUnavailable("claude-sonnet-5-5 answered 529", spent)

    monkeypatch.setattr(llm, "call", down)
    with pytest.raises(postdoc.PostdocUnavailable) as e:
        postdoc.ask_model("q", [], corpus=None)
    assert e.value.usage == spent

    monkeypatch.setattr(api, "load_corpus", lambda: SimpleNamespace(search=lambda q, limit: []))
    plan = api.ask(AskRequest(question="what is the titre", mode="single"))
    assert "529" in plan.declined and plan.usage == spent


def test_extract_names_what_was_spent_before_an_outage(monkeypatch):
    def down(**_):
        raise llm.ModelUnavailable("claude-sonnet-5-5 answered 529", Usage(costUsd=0.25, models=[OPUS]))

    monkeypatch.setattr(llm, "call", down)
    with pytest.raises(extract.ExtractUnavailable, match=r"529 \(\$0\.2500 spent first\)"):
        extract.call_model("B5", "text", extract.build_tool(["s1"], ["titer_secreted"]))


def test_extract_reports_a_refused_paper_as_not_extracted(monkeypatch):
    def refused(**_):
        raise llm.ModelRefused("bio", [OPUS, SONNET], Usage())

    monkeypatch.setattr(llm, "call", refused)
    with pytest.raises(extract.ExtractUnavailable, match="B5 declined"):
        extract.call_model("B5", "text", extract.build_tool(["s1"], ["titer_secreted"]))


def test_extract_passes_truncation_on_for_the_split(monkeypatch):
    cut = llm.Result(data=None, model=OPUS, usage=Usage(outputTokens=32_000, models=[OPUS]), stop_reason="max_tokens")
    monkeypatch.setattr(llm, "call", lambda **_: cut)
    raw, usage = extract.call_model("B5", "text", extract.build_tool(["s1"], ["titer_secreted"]))
    assert raw["truncated"] is True and usage.models == [OPUS]


# ── through the real SDK ───────────────────────────────────────────────
#
# The fakes above answer `messages.stream` the way this module expects. These
# put the real anthropic client in front of a transport that replays the
# event stream the API sends, so the request the SDK actually builds and the
# errors it actually raises are what is tested.


def _sse(events):
    return b"".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n".encode() for e in events)


def _events(model, text='{"candidates": []}', stop="end_turn", tin=1000, tout=500, category=None):
    events = [{"type": "message_start", "message": {
        "id": "msg_1", "type": "message", "role": "assistant", "model": model, "content": [],
        "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": tin, "output_tokens": 1}}}]
    if text is not None:
        events += [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
            {"type": "content_block_stop", "index": 0},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": text}},
            {"type": "content_block_stop", "index": 1},
        ]
    details = {"type": "refusal", "category": category, "explanation": None} if stop == "refusal" else None
    events += [
        {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None, "stop_details": details},
         "usage": {"output_tokens": tout}},
        {"type": "message_stop"},
    ]
    return events


class _Dropped(_http().SyncByteStream):
    """A response body that sends its first events and then loses the
    connection, the way a stream cut mid-answer arrives. (It must be a
    SyncByteStream: anything else trips an assertion inside the transport,
    which the SDK reports as a connection error and so tests nothing.)"""

    def __init__(self, head: bytes):
        self.head = head

    def __iter__(self):
        yield self.head
        raise _http().RemoteProtocolError("peer closed connection without sending complete message body")

    def close(self):
        pass


def sdk(script):
    """A real client whose every request is answered from `script`, keyed by
    model: a list of events, a status code, or "drop" for a stream that opens
    and then breaks. Returns the client and the request bodies it sent."""
    h = _http()
    sent: list[dict] = []

    def handle(request):
        body = json.loads(request.content)
        sent.append(body)
        outcome = script[body["model"]]
        if isinstance(outcome, int):
            return h.Response(outcome, json={"type": "error", "error": {"type": "overloaded_error", "message": "x"}})
        stream = {"content-type": "text/event-stream"}
        if outcome == "drop":
            return h.Response(200, headers=stream, stream=_Dropped(_sse(_events(body["model"])[:1])))
        return h.Response(200, headers=stream, content=_sse(outcome))

    client = anthropic.Anthropic(api_key="x", max_retries=0, http_client=h.Client(transport=h.MockTransport(handle)))
    return client, sent


def test_the_request_the_sdk_sends_is_the_one_these_models_accept():
    client, sent = sdk({OPUS: _events(OPUS, '{"candidates": [{"value": 4.2}]}', tin=2000, tout=900)})
    result = run(client)
    assert result.data == {"candidates": [{"value": 4.2}]} and result.model == OPUS
    assert result.usage.inputTokens == 2000 and result.usage.outputTokens == 900
    body = sent[0]
    # Exactly these keys: no tools or tool_choice (forced tool use is a 400),
    # no thinking (adaptive thinking is always on, and disabling it is a 400),
    # no temperature or top_p (a non-default value is a 400 on Sonnet 5.5).
    assert sorted(body) == ["max_tokens", "messages", "model", "output_config", "stream", "system"]
    assert body["stream"] is True
    assert body["output_config"]["effort"] == "medium"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_a_refusal_through_the_sdk_moves_to_sonnet():
    client, sent = sdk({
        OPUS: _events(OPUS, None, stop="refusal", category="bio", tin=2000, tout=0),
        SONNET: _events(SONNET, '{"candidates": [{"value": 7}]}'),
    })
    result = run(client)
    assert [b["model"] for b in sent] == [OPUS, SONNET]
    assert result.model == SONNET and result.fell_back and result.data["candidates"][0]["value"] == 7
    assert result.usage.models == [OPUS, SONNET]


@pytest.mark.parametrize("opus", [529, 404, "drop", "error-event"])
def test_opus_failing_through_the_sdk_moves_to_sonnet(opus):
    if opus == "error-event":
        opus = _events(OPUS)[:1] + [{"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}]
    client, sent = sdk({OPUS: opus, SONNET: _events(SONNET)})
    result = run(client)
    assert [b["model"] for b in sent] == [OPUS, SONNET] and result.model == SONNET


@pytest.mark.parametrize(("sonnet", "says"), [
    ("drop", "stream failed (RemoteProtocolError)"),
    ("error-event", "stream failed (overloaded_error)"),
    (529, "answered 529"),
])
def test_the_last_model_failing_mid_stream_is_unavailable_and_says_how(sonnet, says):
    if sonnet == "error-event":
        sonnet = _events(SONNET)[:1] + [{"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}]
    client, _ = sdk({OPUS: 404, SONNET: sonnet})
    with pytest.raises(llm.ModelUnavailable) as e:
        run(client)
    assert says in str(e.value)


def test_a_rejected_key_through_the_sdk_does_not_fall_back():
    client, sent = sdk({OPUS: 401, SONNET: _events(SONNET)})
    with pytest.raises(llm.ModelUnavailable, match="rejected the key"):
        run(client)
    assert [b["model"] for b in sent] == [OPUS]


# ── a cache from before the move ───────────────────────────────────────


def test_an_extraction_kept_by_an_earlier_run_is_extracted_again():
    from sqlalchemy import delete, insert

    from openferment_core import db, projects
    from openferment_core.db import models as t

    def keep(body: dict) -> None:
        async def put() -> None:
            async with db.session() as s:
                await s.execute(delete(t.candidates))
                await s.execute(insert(t.candidates).values(project_id=projects.current(), document_id="B5",
                                                            source=extract.MODEL, body=body, created_by="test"))

        db.run(put())

    keep({"paperId": "B5", "run": "haiku-1", "extractedAt": "2026-09-01T00:00:00Z", "candidates": [], "dropped": []})
    assert extract.cached("B5") is None, "another run's row is not this run's extraction"
    assert extract.all_cached() == []

    current = extract.ExtractResponse(paperId="B5", run=extract.RUN, extractedAt="2026-10-08T00:00:00Z")
    keep(current.model_dump(mode="json"))
    assert extract.cached("B5") == current and extract.all_cached() == [current]


# ── OF-BLD-014 §3.3: cached tokens, roles, tool turns, the daily cap ────

HAIKU = "claude-haiku-5-5"


def test_cost_with_cached_tokens_matches_the_arithmetic_by_hand():
    # Opus 5.5: $4 in, $20 out; a cache write 1.25x input, a read 0.05x.
    # 1000*4 + 400*4*1.25 + 2000*4*0.05 + 500*20 = 16,400 per million.
    assert llm.cost_usd(OPUS, 1000, 500, cache_read_tokens=2000, cache_write_tokens=400) == 0.0164
    # Sonnet 5.5 reads at 0.05x of $2: a million read tokens cost $0.10.
    assert llm.cost_usd(SONNET, 0, 0, cache_read_tokens=1_000_000) == 0.1
    # Haiku 5.5 reads at 0.1x. A prompt of 60,000 tokens is the short tier:
    # 10000*0.10 + 50000*0.10*0.1 + 1000*0.50 = 2,000 per million.
    assert llm.cost_usd(HAIKU, 10_000, 1000, cache_read_tokens=50_000) == 0.002
    # 105,000 prompt tokens, cache reads included, is the long tier for the
    # whole request: 10000*0.50 + 95000*0.50*0.1 + 1000*2.50 = 12,250.
    assert llm.cost_usd(HAIKU, 10_000, 1000, cache_read_tokens=95_000) == 0.01225
    # Without cached tokens nothing changed.
    assert llm.cost_usd(OPUS, 1000, 500) == 0.014


def test_usage_reads_cached_tokens_from_the_response_and_add_sums_them():
    response = answer(OPUS, tin=1000, tout=500)
    response.usage.cache_read_input_tokens = 2000
    response.usage.cache_creation_input_tokens = 400
    used = llm.usage_of(response)
    assert (used.cacheReadTokens, used.cacheWriteTokens, used.costUsd) == (2000, 400, 0.0164)
    both = llm.add(used, used)
    assert (both.cacheReadTokens, both.cacheWriteTokens, both.inputTokens) == (4000, 800, 2000)


def test_a_response_without_cache_fields_reads_as_none_cached():
    used = llm.usage_of(answer(OPUS))
    assert (used.cacheReadTokens, used.cacheWriteTokens) == (0, 0)


def test_haiku_5_5_has_both_tiers_on_file():
    assert llm.PRICES[HAIKU] == (0.10, 0.50)
    assert llm.LONG_PROMPT_PRICES[HAIKU] == (100_000, (0.50, 2.50))


def test_the_roles_name_their_chains(monkeypatch):
    assert llm.chain() == llm.chain("answer") == [OPUS, SONNET]
    assert llm.chain("index") == [HAIKU, OPUS, SONNET]
    monkeypatch.setenv("OPENFERMENT_INDEX_MODEL", SONNET)
    assert llm.chain("index") == [SONNET, OPUS], "no model twice"
    with pytest.raises(ValueError):
        llm.chain("other")


def test_an_index_call_starts_on_the_index_model():
    client = FakeClient({HAIKU: answer(HAIKU)})
    result = llm.call(system="s", user="u", schema=SCHEMA, max_tokens=100, client_factory=lambda: client, role="index")
    assert client.asked == [HAIKU] and result.model == HAIKU


TOOLS = [{"name": "search_records", "description": "d", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}]


def _turn(content, stop="end_turn", model=OPUS, tin=100, tout=50, category=None):
    return SimpleNamespace(
        model=model,
        stop_reason=stop,
        stop_details=SimpleNamespace(category=category) if stop == "refusal" else None,
        content=content,
        usage=SimpleNamespace(input_tokens=tin, output_tokens=tout, cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


def _converse(ask, **kw):
    args = dict(system="s", messages=[{"role": "user", "content": "q"}], tools=TOOLS, schema=SCHEMA, max_tokens=500, model=OPUS, ask=ask)
    args.update(kw)
    return llm.converse(**args)


def test_converse_never_sends_a_forced_tool_choice():
    sent = []
    for forced in ("any", "tool"):
        with pytest.raises(ValueError):
            _converse(lambda r: sent.append(r), tool_choice=forced)
    assert sent == [], "a forced choice is refused before anything is sent"
    for choice in llm.TOOL_CHOICES:
        _converse(lambda r: sent.append(r) or _turn([SimpleNamespace(type="text", text='{"candidates": []}')]), tool_choice=choice)
    assert [r["tool_choice"] for r in sent] == [{"type": "auto"}, {"type": "none"}]
    for r in sent:
        assert r["tool_choice"]["type"] not in ("any", "tool")


def test_converse_builds_strict_tools_the_plan_schema_and_top_level_caching():
    sent = []
    _converse(lambda r: sent.append(r) or _turn([SimpleNamespace(type="text", text='{"candidates": []}')]))
    r = sent[0]
    assert r["cache_control"] == {"type": "ephemeral"}
    assert r["tools"][0]["strict"] is True
    assert r["tools"][0]["input_schema"]["additionalProperties"] is False
    assert r["output_config"]["format"]["type"] == "json_schema"
    assert r["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert r["model"] == OPUS


def test_converse_returns_tool_calls_and_keeps_every_block_as_returned():
    blocks = [
        SimpleNamespace(type="thinking", thinking="…", signature="sig"),
        SimpleNamespace(type="tool_use", id="tu_1", name="search_records", input={"query": "PHB"}),
    ]
    turn = _converse(lambda r: _turn(blocks, stop="tool_use"))
    assert [(c.id, c.name, c.input) for c in turn.toolCalls] == [("tu_1", "search_records", {"query": "PHB"})]
    assert turn.data is None and turn.stopReason == "tool_use"
    assert turn.content[0] == {"type": "thinking", "thinking": "…", "signature": "sig"}
    assert turn.content[1]["type"] == "tool_use"


def test_converse_parses_the_final_answer_when_no_tool_was_called():
    turn = _converse(lambda r: _turn([SimpleNamespace(type="text", text='{"candidates": [{"value": "x"}]}')]))
    assert turn.data == {"candidates": [{"value": "x"}]} and turn.toolCalls == []
    assert turn.usage.costUsd == llm.cost_usd(OPUS, 100, 50)


def test_a_refusal_inside_a_conversation_is_model_refused_with_what_was_spent():
    with pytest.raises(llm.ModelRefused) as e:
        _converse(lambda r: _turn([], stop="refusal", tin=300, tout=0, category="bio"))
    assert e.value.category == "bio"
    assert e.value.usage.inputTokens == 300 and e.value.usage.costUsd == llm.cost_usd(OPUS, 300, 0)


def test_converse_falls_back_nowhere():
    asked = []

    def ask(r):
        asked.append(r["model"])
        raise status_error(anthropic.NotFoundError, 404)

    with pytest.raises(llm.ModelUnavailable):
        _converse(ask)
    assert asked == [OPUS]


def test_the_daily_cap_refuses_the_call_that_would_pass_it_and_allows_the_one_before(monkeypatch):
    from openferment_core import spend

    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "1.00")
    monkeypatch.setattr(llm, "worst_case_usd", lambda *a, **k: 0.10)
    spend.charge("answer", 0.85)
    client = FakeClient({OPUS: answer(OPUS, tin=1000, tout=500)})
    run(client)  # 0.85 + 0.10 stays within the cap
    assert client.asked == [OPUS]
    assert spend.total_today() == round(0.85 + llm.cost_usd(OPUS, 1000, 500), 6), "the response was charged"
    spend.charge("answer", 0.10)  # 0.964: the next worst case would pass 1.00
    with pytest.raises(llm.BudgetExhausted) as e:
        run(client)
    assert client.asked == [OPUS], "the refused call was never sent"
    assert "OPENFERMENT_DAILY_BUDGET_USD" in str(e.value) and "$0.96" in str(e.value)
    assert isinstance(e.value, llm.ModelUnavailable), "every caller that reports an outage reports this"
    with pytest.raises(llm.BudgetExhausted):
        _converse(lambda r: pytest.fail("sent past the cap"))


def test_the_worst_case_grows_with_what_a_call_allows():
    small = llm.worst_case_usd(OPUS, {"messages": "x"}, 100)
    assert llm.worst_case_usd(OPUS, {"messages": "x"}, 10_000) > small
    assert llm.worst_case_usd(OPUS, {"messages": "x" * 10_000}, 100) > small


def test_every_response_is_charged_to_its_role():
    from openferment_core import spend

    client = FakeClient({HAIKU: answer(HAIKU, tin=1000, tout=500)})
    llm.call(system="s", user="u", schema=SCHEMA, max_tokens=100, client_factory=lambda: client, role="index")
    assert spend.state()["byRole"]["index"] == llm.cost_usd(HAIKU, 1000, 500)
    assert spend.state()["byRole"]["answer"] == 0.0


# ── the routing table (execution prompt §4.8; ADR-008; alpha 2.0 stage 6.3) ──


def test_the_routing_table_names_each_familys_models_and_effort(monkeypatch):
    table = llm.routes()
    assert set(table) == set(llm.FAMILIES) == {"plan", "explain", "extract", "index", "judge"}
    assert table == llm.ROUTES, "with core/.env silent, the table is ROUTES"
    assert table["plan"].models == (OPUS, SONNET) and table["index"].models == (HAIKU, OPUS, SONNET)
    assert {f: llm.SPEND_ROLES[f] for f in llm.FAMILIES} == {"plan": "answer", "explain": "answer", "extract": "answer",
                                                            "index": "index", "judge": "answer"}
    monkeypatch.setenv("OPENFERMENT_ROUTES", json.dumps({"judge": {"models": [f"anthropic:{SONNET}"], "effort": "low"},
                                                         "index": {"effort": "high"}}))
    table = llm.routes()
    assert table["judge"] == llm.Route((f"anthropic:{SONNET}",), "low")
    assert table["index"] == llm.Route((HAIKU, OPUS, SONNET), "high") and table["plan"] == llm.ROUTES["plan"]
    assert llm.chain("judge") == [f"anthropic:{SONNET}"] and llm.chain("answer") == llm.chain("plan")


@pytest.mark.parametrize("raw, says", [
    ("not json", "is not JSON"),
    ('["plan"]', "an object of family to route"),
    ('{"answer": {}}', "names 'answer'"),
    ('{"plan": {"models": []}}', "a list of model specs"),
    ('{"plan": {"models": ["nonesuch:model"]}}', "names the provider 'nonesuch'"),
    ('{"plan": {"models": ["anthropic:"]}}', "names a provider and no model"),
    ('{"plan": {"effort": "huge"}}', "effort is one of"),
    ('{"plan": {"temperature": 1}}', "an object of models and effort"),
])
def test_a_routing_table_that_cannot_route_says_why(monkeypatch, raw, says):
    monkeypatch.setenv("OPENFERMENT_ROUTES", raw)
    with pytest.raises(llm.RoutesInvalid, match=says):
        llm.routes()


def test_a_spec_is_the_kits_provider_and_model_and_a_bare_id_is_anthropics():
    assert llm.spec(OPUS) == ("anthropic", OPUS) and llm.spec(f"anthropic:{OPUS}") == ("anthropic", OPUS)
    assert llm.spec("openai-compatible:qwen3-32b") == ("openai-compatible", "qwen3-32b")


def test_a_call_runs_at_its_familys_effort_on_its_anthropic_spec_and_passes_over_a_provider_that_waits(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_ROUTES", json.dumps(
        {"extract": {"models": ["openai-compatible:qwen3-32b", f"anthropic:{SONNET}"], "effort": "high"}}))
    client = FakeClient({SONNET: answer(SONNET)})
    result = llm.call(system="s", user="u", schema=SCHEMA, max_tokens=100, client_factory=lambda: client,
                      family="extract")
    assert result.model == SONNET and result.tried == [SONNET] and client.asked == [SONNET]
    assert client.requests[0]["output_config"]["effort"] == "high"
    monkeypatch.setenv("OPENFERMENT_ROUTES", json.dumps({"extract": {"models": ["openai-compatible:qwen3-32b"]}}))
    with pytest.raises(llm.ModelUnavailable, match="waits for the owner"):
        llm.call(system="s", user="u", schema=SCHEMA, max_tokens=100, client_factory=lambda: FakeClient({}),
                 family="extract")


def test_a_turn_on_a_provider_that_waits_is_unavailable_in_words():
    with pytest.raises(llm.ModelUnavailable, match="waits for the owner"):
        llm.converse(system="s", messages=[{"role": "user", "content": "q"}], tools=[], schema=None, max_tokens=10,
                     model="openai-compatible:qwen3-32b", ask=lambda request: None)


def test_a_grammar_too_large_sends_the_tools_loose_and_is_remembered(monkeypatch):
    """The API compiles one grammar for the answer schema and every strict
    tool and refuses one too large (measured 2026-10-30 on Postdoc's plan
    schema beside seven strict tools): the request goes again with its tools
    loose and its answer schema strict, and the next turn goes loose at once."""
    import anthropic
    import httpx

    monkeypatch.setattr(llm, "_TOO_LARGE", set())
    refusal = anthropic.BadRequestError(
        message="The compiled grammar is too large, which would cause performance issues.",
        response=httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")), body=None)
    sent = []

    def ask(request):
        sent.append([t["strict"] for t in request["tools"]])
        if len(sent) == 1:
            raise refusal
        return _turn([SimpleNamespace(type="text", text='{"candidates": []}')])

    assert _converse(ask).data == {"candidates": []}
    _converse(ask)
    assert sent == [[True], [False], [False]]


def test_any_other_malformed_request_is_unavailable_as_before():
    import anthropic
    import httpx

    refusal = anthropic.BadRequestError(message="messages: at least one message is required",
                                        response=httpx.Response(400, request=httpx.Request("POST", "https://x")), body=None)
    sent = []

    def ask(request):
        sent.append(request)
        raise refusal

    with pytest.raises(llm.ModelUnavailable) as e:
        _converse(ask)
    assert not isinstance(e.value, llm.GrammarTooLarge) and len(sent) == 1
