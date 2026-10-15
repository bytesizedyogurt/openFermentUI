"""Other phrasings of a question (OF-BLD-014 §4.2, the `bm25+expand` lane).

A small model writes up to three other ways to ask the question; each is
searched, and the rankings are fused. The phrasings are search terms, never
shown as an answer. One `index`-role call per question, cached on disk.
"""
from __future__ import annotations

from typing import Any, Callable

from . import helper_cache, llm
from .models import Usage

PROMPT_VERSION = "expand-1"
MAX_PHRASINGS = 3

SYSTEM = (
    "You rewrite a question about bioprocess research papers into other phrasings a keyword search "
    "would match: synonyms, the full names of abbreviations, the organism's other names, the measurement's "
    "other names. Keep each phrasing a question or a short noun phrase. Add no number that the question "
    "does not contain, and no fact the question does not ask about."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "phrasings": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": MAX_PHRASINGS,
            "description": f"Up to {MAX_PHRASINGS} other phrasings of the question.",
        }
    },
    "required": ["phrasings"],
}

Ask = Callable[..., llm.Result]


def phrasings(question: str, *, ask: Ask | None = None) -> tuple[list[str], Usage]:
    """Up to three other phrasings, and what they cost (nothing when cached)."""
    k = helper_cache.key("expand", PROMPT_VERSION, {"question": question})
    hit = helper_cache.get("expand", k)
    if hit is not None:
        return [str(p) for p in hit.get("phrasings", [])][:MAX_PHRASINGS], Usage()
    result = (ask or llm.call)(
        system=SYSTEM,
        user=f"Question: {question}",
        schema=SCHEMA,
        max_tokens=1000,
        label="expand: ",
        role="index",
    )
    raw: Any = (result.data or {}).get("phrasings", [])
    seen = {question.strip().lower()}
    out: list[str] = []
    for p in raw if isinstance(raw, list) else []:
        text = str(p).strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    out = out[:MAX_PHRASINGS]
    helper_cache.put("expand", k, {"phrasings": out})
    return out, result.usage
