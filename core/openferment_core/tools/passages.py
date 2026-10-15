"""`search_passages`: the papers' own words, found for a question (OF-BLD-014 §5.2).

Wraps `retrieve.search` on the lane the scorecard chose. The summary gives each
hit's passage id, paper title, year, section heading and text, the text cut to
`TEXT_CHARS`, so the model reads sentences it may then quote by passage id;
the passages themselves travel in `ToolResult.passages`, which is what a quote
is checked against.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .. import retrieve
from ..models import ToolResult
from . import Tool, ToolContext, register

# At most this many passages per search, each cut to this many characters in
# the summary: six full hits stay under the 9,000 characters a summary may
# hold. Conventions (E.1).
MAX_K = 6
TEXT_CHARS = 900


class SearchPassagesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(description="Words to search the papers' text for.")
    k: int = Field(description=f"How many passages to return, at most {MAX_K}.")


def _paper_meta(ctx: ToolContext, paper_id: str) -> dict:
    try:
        return ctx.pool.paper(paper_id) or {}
    except FileNotFoundError:
        return {}


def _run(inp: SearchPassagesInput, ctx: ToolContext) -> ToolResult:
    k = max(1, min(inp.k, MAX_K))
    try:
        detail = retrieve.search_detail(inp.query, k=k)
    except retrieve.LaneUnavailable as e:
        return ToolResult(error=f"The papers cannot be searched here: {e}")
    hits = []
    for h in detail.hits:
        p = h.passage
        meta = _paper_meta(ctx, p.paperId)
        text = p.text if len(p.text) <= TEXT_CHARS else p.text[:TEXT_CHARS].rsplit(" ", 1)[0] + " …"
        hits.append(
            {
                "passageId": p.id,
                "paperId": p.paperId,
                "paperTitle": (meta.get("title") or "")[:160],
                "year": meta.get("year"),
                "heading": p.heading[:120],
                "text": text,
            }
        )
    summary = {"query": inp.query, "lane": detail.lane, "count": len(hits), "passages": hits}
    if detail.note:
        summary["note"] = detail.note
    return ToolResult(summary=summary, passages=[h.passage for h in detail.hits], recordIds=[])


TOOL = register(
    Tool(
        name="search_passages",
        description=(
            "Search the full text of the fetched papers for passages that bear on a question. Returns up to six "
            "passages, best first, each with its passage id, paper, year, section heading and text. Quote a "
            "sentence from a passage by its passage id, copied exactly; a quote not in its passage discards the "
            "claim. Use it when a claim needs the context a record does not hold."
        ),
        input_model=SearchPassagesInput,
        run=_run,
    )
)
