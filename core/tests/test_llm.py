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
    plan = api.ask(AskRequest(question="what is the titre"))
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


def test_an_extraction_cached_by_an_earlier_run_is_extracted_again(monkeypatch, tmp_path):
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path)
    old = {"paperId": "B5", "run": "haiku-1", "extractedAt": "2026-09-01T00:00:00Z", "candidates": [], "dropped": []}
    (tmp_path / "B5.json").write_text(json.dumps(old))
    assert extract.cached("B5") is None, "another run's file is not this run's extraction"
    assert extract.all_cached() == []

    current = extract.ExtractResponse(paperId="B5", run=extract.RUN, extractedAt="2026-10-08T00:00:00Z")
    (tmp_path / "B5.json").write_text(current.model_dump_json())
    assert extract.cached("B5") == current and extract.all_cached() == [current]
