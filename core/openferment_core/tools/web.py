"""The open web, for Postdoc (ADR-015): `web_search`.

One call is one look at the web: `llm.web_search` sends the query to a model
with Anthropic's web search tool in a request of its own, the API runs the
searches, and what comes back is that model's report in its own words and
the pages the searches returned. The conversation that asked never carries a
page's text, so a page cannot steer it, and the request that plans an answer
keeps its schema.

WHAT A PAGE IS WORTH. A page is a pointer, held by nobody here: a claim cites
it by its id (`web:<hash of its url>`, `Claim.webIds`) and is `unverified` for
it, and a number read off a report is the answering model's estimate, typed
and labelled as every estimate is (ADR-006). The way from a page to evidence
is Intake: a paper or a report the search finds enters the project through
`intake_write` fetch by its identifier, and its own sentences are quoted from
there.

WHEN IT REFUSES, in words: the web turned off (`OPENFERMENT_WEB_SEARCH`), the
network refused for this process (`OPENFERMENT_FIXTURES`, which the offline
suites and the proof set), no key, the day's cap, or the API's own refusal
(web search switched off for the organisation in the Anthropic Console is one).
"""
from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field

from ..models import ToolResult, WebSource
from . import Tool, ToolContext, register

# How much of the report a model reads, and how many pages it may cite.
REPORT_CHARS = 5000
MAX_PAGES = 12


class WebSearchInput(BaseModel):
    query: str = Field(min_length=3, max_length=400,
                       description="What to look up, in words: the thing, the place or year when they matter, and the "
                                   "kind of source wanted.")


def page_id(url: str) -> str:
    return "web:" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def _web_search(inp: WebSearchInput, ctx: ToolContext) -> ToolResult:
    from .. import llm
    from ..literature import collectors

    if collectors.fixtures_only():
        return ToolResult(error="web_search refused: the network is refused for this process (OPENFERMENT_FIXTURES)")
    if llm.web_searches() <= 0:
        return ToolResult(error=f"web_search refused: the open web is off on this installation ({llm.WEB_SETTING} "
                                "in core/.env)")
    query = " ".join(inp.query.split())
    try:
        found = llm.web_search(query)
    except llm.ModelRefused as e:
        return ToolResult(error=f"web_search refused: the model declined the search ({e})",
                          usage=getattr(e, "usage", None) or ToolResult().usage)
    except llm.ModelUnavailable as e:
        return ToolResult(error=f"web_search refused: {e}", usage=getattr(e, "usage", None) or ToolResult().usage)
    pages = [WebSource(id=page_id(p.url), url=p.url, title=p.title, pageAge=p.page_age, query=query)
             for p in found.pages[:MAX_PAGES]]
    if not pages:
        return ToolResult(summary={"query": query, "searches": found.searches, "pages": [],
                                   "note": "The search returned no page. Nothing here is citable."},
                          usage=found.usage)
    report = found.text if len(found.text) <= REPORT_CHARS else found.text[: REPORT_CHARS - 1].rstrip() + "…"
    return ToolResult(
        summary={
            "query": query,
            "searches": found.searches,
            "report": report,
            "pages": [{"id": w.id, "title": w.title, "url": w.url, **({"age": w.pageAge} if w.pageAge else {})}
                      for w in pages],
            "note": ("The report is another model's reading of these pages, and the pages are held by nobody here. "
                     "Cite a page by its id in webIds; a claim that does is unverified. A number from the report is "
                     "your estimate, with the page named in its basis. To make a paper or a report evidence, bring "
                     "it into the project with intake_write fetch and quote it from there."),
        },
        web=pages,
        usage=found.usage,
    )


register(Tool(
    name="web_search",
    description=(
        "Look something up on the open web: current prices, statistics, news, a paper or a report the project does "
        "not hold, or the identifier of one to bring in. Returns a short report in words of what the pages say and "
        "the pages themselves, each with an id a claim may cite in webIds. The pages are held by nobody here, so a "
        "claim resting on one is unverified and a number from the report is your estimate. Search the project's own "
        "records and documents first; use this for what they do not hold."
    ),
    input_model=WebSearchInput,
    run=_web_search,
    strict=False,
))
