"""`search_passages`: the papers' own words, found for a question.

The literature layer answers it through one seam, `search` (ADR-002): Sci RAG
Kit's retrieval once stage 3 wires it. Until then no literature index exists
here and the tool says so in words. The summary gives each hit's passage id,
paper title, year, section heading and text, the text cut to `TEXT_CHARS`, so
the model reads sentences it may then quote by passage id; the passages
themselves travel in `ToolResult.passages`, which is what a quote is checked
against (`quotes.is_whole_sentence`).
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from ..models import Passage, ToolResult, Usage
from . import Tool, ToolContext, register

# At most this many passages per search, each cut to this many characters in
# the summary: six full hits stay under the 9,000 characters a summary may
# hold. Conventions (E.1).
MAX_K = 6
TEXT_CHARS = 900


class LiteratureUnavailable(RuntimeError):
    """No literature index answers here; the message says why in words."""


@dataclass
class Found:
    """What a search returned: the passages, best first, the engine that
    found them, what it spent on a model (if anything) and a note."""

    passages: list[Passage]
    engine: str
    usage: Usage | None = None
    note: str | None = None


def search(query: str, k: int) -> Found:
    """The literature layer's answer to a question. Stage 3 replaces this body
    with Sci RAG Kit's retrieval over the project's documents."""
    raise LiteratureUnavailable(
        "no literature index exists yet: documents enter through Intake into Sci RAG Kit "
        "(alpha 2.0 stage 3), and search reads them there."
    )


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
        found = search(inp.query, k)
    except LiteratureUnavailable as e:
        return ToolResult(error=f"The papers cannot be searched here: {e}")
    hits = []
    for p in found.passages[:k]:
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
    summary = {"query": inp.query, "engine": found.engine, "count": len(hits), "passages": hits}
    if found.note:
        summary["note"] = found.note
    return ToolResult(summary=summary, passages=list(found.passages[:k]), recordIds=[], usage=found.usage or Usage())


TOOL = register(
    Tool(
        name="search_passages",
        description=(
            "Search the full text of the project's documents for passages that bear on a question. Returns up to "
            "six passages, best first, each with its passage id, paper, year, section heading and text. Quote a "
            "sentence from a passage by its passage id, copied exactly; a quote not in its passage discards the "
            "claim. Use it when a claim needs the context a record does not hold."
        ),
        input_model=SearchPassagesInput,
        run=_run,
    )
)
