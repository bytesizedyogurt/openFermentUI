"""The open web (ADR-015), offline: `llm.web_search` against a stand-in client,
the `web_search` tool, a claim that cites a page, and Postdoc's loop.

Every page here is a STAND-IN: an address under example.org and words written
for the test. The real tool is Anthropic's, asked by `pnpm test:live`.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from openferment_core import llm, postdoc_agent, tools
from openferment_core.models import ToolResult, Usage, WebSource
from openferment_core.tools import web as web_tool
from openferment_core.validate import SeenSet, validate_plan
from test_postdoc_agent import Script, claim, plan
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)

URL = "https://example.org/stand-in/feedstock-report"
PAGE = WebSource(id=web_tool.page_id(URL), url=URL, title="A stand-in feedstock report", query="stand-in")


def message(*, stop="end_turn", text="A stand-in report.", urls=(URL,), searches=1, model=llm.DEFAULT_INDEX,
            error=None):
    content = [SimpleNamespace(type="server_tool_use", id="srvtoolu_1", name="web_search", input={"query": "q"})]
    if error:
        content.append(SimpleNamespace(type="web_search_tool_result", tool_use_id="srvtoolu_1",
                                       content=SimpleNamespace(type="web_search_tool_result_error", error_code=error)))
    else:
        content.append(SimpleNamespace(type="web_search_tool_result", tool_use_id="srvtoolu_1", content=[
            SimpleNamespace(type="web_search_result", url=u, title=f"Title of {u}", page_age="a stand-in age",
                            encrypted_content="…") for u in urls]))
    if text:
        content.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(model=model, stop_reason=stop, stop_details=None, content=content,
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=100,
                                                 server_tool_use=SimpleNamespace(web_search_requests=searches)))


class Client:
    """Answers each request with the next message of its script, and keeps the requests."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests: list[dict] = []
        self.messages = self

    def stream(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        outcome = self.answers.pop(0)

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


@pytest.fixture(autouse=True)
def _web_setting(monkeypatch):
    monkeypatch.delenv(llm.WEB_SETTING, raising=False)
    monkeypatch.delenv("OPENFERMENT_FIXTURES", raising=False)


# ── the setting ────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw, n", [("", llm.DEFAULT_WEB_SEARCHES), ("on", llm.DEFAULT_WEB_SEARCHES), ("5", 5),
                                    ("99", llm.MAX_WEB_SEARCHES), ("0", 0), ("off", 0), ("-2", 0), ("many", 0)])
def test_the_setting_is_a_count_and_anything_else_is_off(monkeypatch, raw, n):
    monkeypatch.setenv(llm.WEB_SETTING, raw)
    assert llm.web_searches() == n


# ── the call ───────────────────────────────────────────────────────────


def test_one_look_is_one_request_with_the_web_tool_and_no_answer_schema():
    client = Client(message(urls=(URL, URL, "https://example.org/stand-in/second", "ftp://example.org/not-a-page"),
                            searches=2))
    found = llm.web_search("stand-in question", client_factory=lambda: client)
    (request,) = client.requests
    assert request["model"] == llm.DEFAULT_INDEX
    assert request["tools"] == [{"type": llm.WEB_TOOL_TYPE, "name": "web_search", "max_uses": llm.DEFAULT_WEB_SEARCHES}]
    # The API refuses citations beside an answer schema, and a search's answer cites.
    assert "format" not in request["output_config"]
    assert [p.url for p in found.pages] == [URL, "https://example.org/stand-in/second"]
    assert found.text == "A stand-in report." and found.searches == 2
    tokens = llm.cost_usd(llm.DEFAULT_INDEX, 1000, 100)
    assert found.usage.costUsd == pytest.approx(tokens + 2 * llm.WEB_SEARCH_USD)


def test_a_paused_turn_is_asked_to_go_on_with_its_own_blocks():
    client = Client(message(stop="pause_turn", text="", searches=1), message(text="The rest.", urls=(), searches=0))
    found = llm.web_search("stand-in question", client_factory=lambda: client)
    assert len(client.requests) == 2
    again = client.requests[1]["messages"]
    assert [m["role"] for m in again] == ["user", "assistant"]
    assert [b["type"] for b in again[1]["content"]] == ["server_tool_use", "web_search_tool_result"]
    assert found.text == "The rest." and [p.url for p in found.pages] == [URL] and found.searches == 1


def test_a_search_the_api_could_not_run_is_said_in_words():
    client = Client(message(error="too_many_requests", text="I could not search."))
    with pytest.raises(llm.ModelUnavailable, match="too_many_requests"):
        llm.web_search("stand-in question", client_factory=lambda: client)


def test_the_web_turned_off_calls_nothing(monkeypatch):
    monkeypatch.setenv(llm.WEB_SETTING, "0")
    client = Client()
    with pytest.raises(llm.ModelUnavailable, match="off"):
        llm.web_search("stand-in question", client_factory=lambda: client)
    assert client.requests == []


# ── the tool ───────────────────────────────────────────────────────────


def found(pages=((URL, "A stand-in feedstock report"),), text="The report, in the model's words."):
    return llm.WebFound(text=text, pages=[llm.WebPage(url=u, title=t) for u, t in pages], searches=1,
                        usage=Usage(costUsd=0.02, models=[llm.DEFAULT_INDEX]), model=llm.DEFAULT_INDEX)


def test_the_tool_returns_a_report_and_pages_a_claim_may_cite(monkeypatch):
    asked: list[str] = []
    monkeypatch.setattr(llm, "web_search", lambda q: asked.append(q) or found())
    r = tools.run("web_search", {"query": "  stand-in   question "})
    assert r.error is None and asked == ["stand-in question"]
    assert [w.id for w in r.web] == [PAGE.id] and r.summary["pages"][0]["url"] == URL
    assert r.summary["report"] == "The report, in the model's words." and r.usage.costUsd == 0.02
    assert not r.evidence and not r.recordIds and not r.passages


def test_the_tool_refuses_in_words_and_calls_nothing(monkeypatch):
    def never(q):
        raise AssertionError("no search is made")

    monkeypatch.setattr(llm, "web_search", never)
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    assert "network is refused" in tools.run("web_search", {"query": "stand-in question"}).error
    monkeypatch.delenv("OPENFERMENT_FIXTURES")
    monkeypatch.setenv(llm.WEB_SETTING, "off")
    assert "is off" in tools.run("web_search", {"query": "stand-in question"}).error


def test_an_outage_is_the_tools_refusal_with_what_it_spent(monkeypatch):
    def down(q):
        raise llm.ModelUnavailable("the web search could not run (unavailable)", Usage(costUsd=0.01))

    monkeypatch.setattr(llm, "web_search", down)
    r = tools.run("web_search", {"query": "stand-in question"})
    assert r.error.startswith("web_search refused:") and r.usage.costUsd == 0.01 and not r.web


def test_a_search_with_no_page_gives_nothing_to_cite(monkeypatch):
    monkeypatch.setattr(llm, "web_search", lambda q: found(pages=()))
    r = tools.run("web_search", {"query": "stand-in question"})
    assert r.error is None and r.web == [] and "report" not in r.summary


# ── a claim that cites a page ──────────────────────────────────────────


class _NoRecords:
    def record(self, rid):
        return None


def seen_with(*pages):
    seen = SeenSet()
    seen.add(ToolResult(web=list(pages)))
    return seen


def web_claim(*ids, **kw):
    return {**claim(text="A feedstock price was reported for the region.", **kw), "webIds": list(ids)}


def test_a_claim_resting_on_a_page_is_kept_unverified():
    out = validate_plan([web_claim(PAGE.id)], seen_with(PAGE), _NoRecords())
    (kept,) = out.claims
    assert kept.webIds == [PAGE.id] and kept.provenance == "unverified" and out.rejected == 0


def test_a_page_no_search_returned_in_this_run_is_not_citable():
    out = validate_plan([web_claim("web:000000000000")], seen_with(PAGE), _NoRecords())
    assert out.claims == [] and "no tool returned" in out.reasons[0]


def test_a_refused_search_teaches_the_run_nothing():
    seen = SeenSet()
    seen.add(ToolResult(web=[PAGE], error="web_search refused: stand-in"))
    assert seen.web == {}


def test_a_number_read_off_a_report_is_the_models_estimate():
    raw = {**web_claim(PAGE.id), "values": [{"label": "the feedstock's price", "evidenceId": "", "recordId": "",
                                           "estimate": {"value": 1.0, "unit": "USD/kg", "low": None, "high": None,
                                                        "basis": "read from the stand-in feedstock report"}}]}
    out = validate_plan([raw], seen_with(PAGE), _NoRecords(), model="stand-in-model")
    (kept,) = out.claims
    assert kept.provenance == "assumed" and kept.values[0].quantity.origin.kind == "model-estimate"


# ── Postdoc's loop ─────────────────────────────────────────────────────


def test_postdoc_searches_the_web_and_its_plan_carries_the_page(pool, monkeypatch):  # noqa: F811
    monkeypatch.setattr(llm, "web_search", lambda q: found())
    script = Script([("web_search", {"query": "stand-in question"})], plan(web_claim(PAGE.id)))
    ctx = tools.ToolContext(pool_factory=lambda: pool)
    answer = postdoc_agent.ask("What does corn stover cost?", converse=script, ctx=ctx)
    assert [w.url for w in answer.web] == [URL]
    assert answer.claims[0].webIds == [PAGE.id] and answer.claims[0].provenance == "unverified"
    line = next(s.summary for s in answer.trace if s.tool == "web_search")
    assert line == 'Searched the web for "stand-in question" · 1 page'
    # What the search spent is charged to the question that asked.
    assert answer.usage.costUsd == pytest.approx(0.02 + 2 * 0.001)
    # The page's text never enters the conversation: the model reads the report and the ids.
    result = script.calls[1]["messages"][-1]["content"][0]["content"]
    assert PAGE.id in result and "encrypted_content" not in result


def test_the_plan_schema_asks_every_claim_for_its_pages():
    claim_schema = postdoc_agent.PLAN_SCHEMA["properties"]["claims"]["items"]
    assert "webIds" in claim_schema["required"] and claim_schema["properties"]["webIds"]["type"] == "array"
