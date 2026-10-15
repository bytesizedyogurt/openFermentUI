"""A reader that grades passages (OF-BLD-014 §4.2, the `+rerank` lanes).

The top passages go to a small model, which grades each from 0 to 3 for how
well it answers the question and copies out the sentence that answers it.
The copy is checked: it must be one whole sentence (or table row) of its
passage, or a run of them, word for word after `normalize_text`. A sentence that fails sets that passage's grade to 0 and
is counted, never repaired. The order is grade, then fused rank. One
`index`-role call per question and passage set, cached on disk.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import helper_cache, llm
from .models import Passage, Usage
from .validate import normalize_text

PROMPT_VERSION = "rerank-1"
# How many passages the reader is shown: a convention (§4.2).
TOP = 30

SYSTEM = (
    "You grade passages from research papers against a question. For each passage give a grade: "
    "3 answers the question directly, 2 answers part of it, 1 is on the topic and answers nothing, "
    "0 is off the topic. For a grade of 1 or more, copy the one sentence of the passage that best "
    "answers the question, exactly as it is written, character for character; for 0, copy nothing. "
    "Grade every passage, by its id."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "grades": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "passageId": {"type": "string"},
                    "grade": {"type": "integer", "enum": [0, 1, 2, 3]},
                    "sentence": {"type": "string", "description": "Copied exactly from the passage; empty for grade 0."},
                },
                "required": ["passageId", "grade", "sentence"],
            },
        }
    },
    "required": ["grades"],
}

Ask = Callable[..., llm.Result]


@dataclass
class Graded:
    grades: dict[str, int] = field(default_factory=dict)
    sentences: dict[str, str] = field(default_factory=dict)
    # Sentences the reader made up or altered: grade set to 0, counted.
    unverified: int = 0
    usage: Usage = field(default_factory=Usage)


def units_of(passage: Passage) -> set[str]:
    """What the reader may copy, normalised: each whole sentence of the
    passage, and each whole line (a table row is a unit of its own)."""
    from .passages import sentence_spans

    out: set[str] = set()
    for line in passage.text.split("\n"):
        if line.strip():
            out.add(normalize_text(line))
            for s, e in sentence_spans(line):
                if line[s:e].strip():
                    out.add(normalize_text(line[s:e]))
    return out


def is_whole_sentence(sentence: str, passage: Passage) -> bool:
    """The copy is one sentence or row of the passage, or a run of them, word
    for word after `normalize_text`. A fragment is not (§4.R: "c" passed)."""
    norm = normalize_text(sentence)
    if not norm or norm not in normalize_text(passage.text):
        return False
    units = units_of(passage)
    if norm in units:
        return True
    # A run of whole sentences: it starts with one and ends with one.
    return any(norm.startswith(u) for u in units) and any(norm.endswith(u) for u in units)


def check(raw: Any, by_id: dict[str, Passage]) -> Graded:
    """The model's grades, held to the passages. Anything that is not a
    passage it was shown is ignored; a sentence not in its passage zeroes it."""
    out = Graded()
    for g in raw if isinstance(raw, list) else []:
        if not isinstance(g, dict):
            continue
        pid = str(g.get("passageId", ""))
        if pid not in by_id or pid in out.grades:
            continue
        try:
            grade = max(0, min(3, int(g.get("grade", 0))))
        except (TypeError, ValueError):
            grade = 0
        sentence = str(g.get("sentence") or "").strip()
        if grade > 0:
            if not is_whole_sentence(sentence, by_id[pid]):
                out.unverified += 1
                grade = 0
                sentence = ""
        else:
            sentence = ""
        out.grades[pid] = grade
        if sentence:
            out.sentences[pid] = sentence
    return out


def grade(question: str, passages: list[Passage], *, ask: Ask | None = None) -> Graded:
    shown = passages[:TOP]
    by_id = {p.id: p for p in shown}
    k = helper_cache.key("rerank", PROMPT_VERSION, {"question": question, "passages": [[p.id, p.text] for p in shown]})
    hit = helper_cache.get("rerank", k)
    if hit is not None:
        cached = check(hit.get("grades"), by_id)
        return Graded(cached.grades, cached.sentences, int(hit.get("unverified", cached.unverified)))
    user = f"Question: {question}\n\nPassages:\n" + "\n\n".join(f"[{p.id}]\n{p.text}" for p in shown)
    result = (ask or llm.call)(
        system=SYSTEM,
        user=user,
        schema=SCHEMA,
        max_tokens=8000,
        label="rerank: ",
        role="index",
    )
    raw = (result.data or {}).get("grades", [])
    graded = check(raw, by_id)
    graded.usage = result.usage
    helper_cache.put("rerank", k, {"grades": raw, "unverified": graded.unverified})
    return graded
