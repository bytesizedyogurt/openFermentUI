"""The one place openFerment calls a model: Opus first, Sonnet when Opus
declines or is unavailable, JSON by schema, cost from the response.

Offline: a fake client stands in for the SDK, answering `messages.stream`
the way the real one does, with a context manager whose final message has a
`model`, `stop_reason`, `stop_details`, `content` and `usage`.
"""
from __future__ import annotations

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


def test_the_real_schemas_come_out_strict():
    for schema in (postdoc.TOOL["input_schema"], extract.build_tool(["s1"], ["titer_secreted"])["input_schema"]):
        out = llm.strict_schema(schema)
        seen = []

        def walk(node):
            if isinstance(node, dict):
                if "properties" in node:
                    seen.append(node.get("additionalProperties"))
                for bad in llm._UNSUPPORTED:
                    assert bad not in node, bad
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
