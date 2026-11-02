"""Sentences, and whether a quote is whole ones of its passage.

A quote is held to the passage it cites: one whole sentence or table row of
the passage, or a run of them, word for word after `normalize_text`. A
fragment can lift a number out of its negation, so a fragment is refused
(OF-BLD-014 §4.R, kept by alpha 2.0 ADR-006). The splitter and the check moved
here from the retired retrieval stack (`passages.py`, `rerank.py`) when Sci RAG
Kit became the literature layer (ADR-002); the kit's chunks are the passages.
"""
from __future__ import annotations

import re
from typing import Protocol

from .validate import normalize_text

# A sentence ends at . ! or ? followed by space and a capital letter, a digit
# or an opening bracket, unless the word before the stop is a single capital
# (E. coli, P. putida) or a common abbreviation.
_END = re.compile(r"(?<=[.!?])[)\]\"'’”]*\s+(?=[A-Z0-9(\[])")
_ABBREV = re.compile(
    r"(?:\b[A-Z]|\bet al|\be\.g|\bi\.e|\bFig|\bFigs|\bEq|\bRef|\bNo|\bapprox|\bca|\bvs|\bsp|\bspp|\bcf|\bSupp|\bTab)\.$"
)


class HasText(Protocol):
    text: str


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Spans that cover `text` end to end, one per sentence; trailing space
    belongs to the sentence before it."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _END.finditer(text):
        head = text[start : m.start()].rstrip()
        if _ABBREV.search(head):
            continue
        spans.append((start, m.end()))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def quote_units(passage: HasText) -> set[str]:
    """What a quote may copy, normalised: each whole sentence of the passage,
    and each whole line (a table row is a unit of its own)."""
    out: set[str] = set()
    for line in passage.text.split("\n"):
        if line.strip():
            out.add(normalize_text(line))
            for s, e in sentence_spans(line):
                if line[s:e].strip():
                    out.add(normalize_text(line[s:e]))
    return out


def is_whole_sentence(sentence: str, passage: HasText) -> bool:
    """The copy is one sentence or row of the passage, or a run of them, word
    for word after `normalize_text`. A fragment is not."""
    norm = normalize_text(sentence)
    if not norm or norm not in normalize_text(passage.text):
        return False
    units = quote_units(passage)
    if norm in units:
        return True
    # A run of whole sentences: it starts with one and ends with one.
    return any(norm.startswith(u) for u in units) and any(norm.endswith(u) for u in units)
