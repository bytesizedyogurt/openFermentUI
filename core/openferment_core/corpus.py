"""Corpus loading and retrieval (OF-BLD-007 §4, §10.3).

Retrieval quality decides answer quality. A model given the wrong thirty
records will write a confident, well-cited, wrong answer — the citations will
resolve, the validator will pass it, and it will still be wrong. So this is
tested standalone before a single token is spent.

BM25 over records rather than over papers. The unit of evidence in this system
is the extraction record: a value, its unit, the quote it came from, and what
is known about the conditions. A paper-level hit would hand the model 132
sections and ask it to find the number, which is the job the extraction
pipeline already did.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

DATA = Path(__file__).parent / "data" / "corpus.json"

# Words that carry no retrieval signal in a corpus where every document is
# about fermentation. Kept small on purpose: an aggressive stop list throws
# away the terms that separate two similar questions.
STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "has", "have", "how", "in", "is", "it", "its", "of", "on", "or",
    "that", "the", "there", "to", "was", "were", "what", "when", "which", "who",
    "why", "with", "you", "your", "any", "been", "much", "many",
}


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, stop words dropped, short tokens kept.

    Short tokens are kept deliberately: 'pH', 'OD', 'C1' and strain
    designations like 'cw15' are two to four characters and are exactly the
    terms that distinguish one record from another here.
    """
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


# A question this long or longer must find a record matching more than one of
# its terms, or the corpus is judged not to cover it. See `search`.
MIN_QUERY_TOKENS_FOR_COVERAGE = 3


@dataclass(frozen=True)
class Corpus:
    papers: list[dict[str, Any]]
    records: list[dict[str, Any]]
    papers_by_id: dict[str, dict[str, Any]]
    records_by_id: dict[str, dict[str, Any]]
    _bm25: BM25Okapi
    _order: list[str]
    _tokens: dict[str, frozenset[str]]

    def search(self, question: str, limit: int = 30) -> list[dict[str, Any]]:
        """The `limit` best-scoring records for a question, or nothing.

        Two things are dropped rather than returned.

        Zero-scoring records, obviously — handing the model filler to reach a
        round number is how a question the corpus cannot answer gets answered
        anyway, and "nothing matched" has to stay visible.

        And, less obviously, the whole result set when its BEST hit rests on a
        single query term. In a corpus this small almost every token is rare —
        'achieved' and 'mixotrophic' both appear in exactly one record — so IDF
        cannot tell a generic verb from a discriminative one, and BM25 will
        happily return a casein kinase record for a question about brazzein
        because both contain the word "achieved". A lone one-word hit is not
        weak evidence; it is a coincidence, and the model would cite it. The
        rule applies only to questions long enough for the coverage test to
        mean something: a two-word question legitimately matches on one term.
        """
        tokens = tokenize(question)
        if not tokens:
            return []
        unique = set(tokens)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(zip(self._order, scores), key=lambda x: -x[1])

        hits = []
        for rid, score in ranked[:limit]:
            if score <= 0:
                break
            matched = sorted(unique & self._tokens[rid])
            hits.append(
                self.records_by_id[rid]
                | {"score": round(float(score), 4), "matchedTerms": matched}
            )

        if (
            hits
            and len(unique) >= MIN_QUERY_TOKENS_FOR_COVERAGE
            and len(hits[0]["matchedTerms"]) < 2
        ):
            return []
        return hits

    def paper(self, paper_id: str) -> dict[str, Any] | None:
        return self.papers_by_id.get(paper_id)

    def record(self, record_id: str) -> dict[str, Any] | None:
        return self.records_by_id.get(record_id)


def _document(record: dict[str, Any], papers_by_id: dict[str, Any]) -> str:
    """The searchable text for one record.

    The quote and the field label do most of the work. The paper title and the
    section heading are included because a question often names the subject
    ("Chlamydomonas", "brazzein") in words that appear in the title and nowhere
    in the extracted quote. The numeric value is deliberately NOT indexed:
    matching on digits retrieves records that share a magnitude rather than a
    meaning.
    """
    paper = papers_by_id.get(record["paperId"], {})
    section = next(
        (s for s in paper.get("sections", []) if s["id"] == record.get("sectionId")),
        {},
    )
    return " ".join(
        str(part)
        for part in (
            record.get("fieldLabel", ""),
            record.get("field", ""),
            record.get("unit", ""),
            record.get("quote", ""),
            record.get("strainId") or "",
            record.get("conditions") or "",
            paper.get("title", ""),
            section.get("heading", ""),
        )
        if part
    )


@lru_cache(maxsize=1)
def load_corpus(path: str | None = None) -> Corpus:
    """Load and index. Cached — the index is built once per process.

    Raises rather than returning an empty corpus when the file is missing. A
    service that answers questions from nothing is worse than one that refuses
    to start: the first is a wrong answer, the second is a message telling you
    to run `pnpm export:corpus`.
    """
    target = Path(path) if path else DATA
    if not target.exists():
        raise FileNotFoundError(
            f"{target} not found. Generate it with `pnpm export:corpus` from the "
            "repository root — the corpus lives in TypeScript and this is a "
            "projection of it."
        )
    raw = json.loads(target.read_text())
    papers = raw["papers"]
    records = raw["records"]
    papers_by_id = {p["id"]: p for p in papers}
    records_by_id = {r["id"]: r for r in records}

    order = [r["id"] for r in records]
    docs = [tokenize(_document(r, papers_by_id)) for r in records]
    return Corpus(
        papers=papers,
        records=records,
        papers_by_id=papers_by_id,
        records_by_id=records_by_id,
        _bm25=BM25Okapi(docs),
        _order=order,
        _tokens={rid: frozenset(doc) for rid, doc in zip(order, docs)},
    )
