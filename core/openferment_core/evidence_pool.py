"""What Postdoc may cite: one view over every record it can see (OF-BLD-014 §3.4).

- the records in the corpus (empty since alpha 2.0 deleted the seed it was
  projected from; a project's records arrive through Intake, extraction and
  review, PostgreSQL from stage 2);
- plus the extractor's current anchored candidates that no decision rejected,
  each marked `unverified`.

Until now Postdoc could not see a candidate until a reviewer verified it,
which would hide all of thread P: its papers have no curated record. A
candidate is shown as what it is, `unverified`, and a claim resting on it is
worth that much (`weakest_provenance`).

A record a reviewer rejected is never in the pool: not a rejected seed
record, and not a candidate whose decision rejects it. `Corpus.search`, which
the flow test uses, is left as it was.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from rank_bm25 import BM25Okapi

from . import biorepo, extract
from .corpus import MIN_QUERY_TOKENS_FOR_COVERAGE, Corpus, _document, load_corpus, tokenize
from .models import Candidate, ReviewDecision

# The most records one search returns (§3.4).
MAX_LIMIT = 10


def _field_labels(corpus_json_ontology: Iterable[dict[str, Any]] | None) -> dict[str, str]:
    return {f["id"]: f.get("name", f["id"]) for f in corpus_json_ontology or []}


def candidate_record(c: Candidate, labels: dict[str, str]) -> dict[str, Any]:
    """A candidate in the shape of a `corpus.json` record, marked unverified.

    `organism` is a strain id exactly when anchoring resolved the paper's
    wording to one, and then `organismText` keeps the wording (§2.1); a
    wording that resolved to nothing stays words and names no strain."""
    resolved = c.organismText is not None
    return {
        "id": c.id,
        "paperId": c.paperId,
        "sectionId": c.sectionId,
        "field": c.field,
        "fieldLabel": labels.get(c.field, c.field),
        "value": c.value,
        "unit": c.unit,
        "quote": c.quote,
        "strainId": c.organism if resolved else None,
        "organismText": c.organismText if resolved else c.organism,
        "carbonSource": c.carbonSource,
        "conditions": None,
        "provenance": "unverified",
        "status": "unverified",
        "primary": c.isPrimary,
        "citesRecordId": c.citesRecordId,
        "range": c.range.model_dump() if c.range else None,
        "source": "candidate",
    }


@dataclass
class EvidencePool:
    corpus: Corpus
    records: list[dict[str, Any]]
    records_by_id: dict[str, dict[str, Any]] = field(init=False)
    _order: list[str] = field(init=False, repr=False)
    _bm25: BM25Okapi | None = field(init=False, repr=False)
    _tokens: dict[str, frozenset[str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.records_by_id = {r["id"]: r for r in self.records}
        self._order = [r["id"] for r in self.records]
        docs = [tokenize(_document(r, self.corpus.papers_by_id)) for r in self.records]
        self._bm25 = BM25Okapi(docs) if docs else None
        self._tokens = {rid: frozenset(d) for rid, d in zip(self._order, docs)}

    def paper(self, paper_id: str) -> dict[str, Any] | None:
        return self.corpus.paper(paper_id)

    def record(self, record_id: str) -> dict[str, Any] | None:
        return self.records_by_id.get(record_id)

    def search(self, query: str, field: str = "", organism: str = "", limit: int = MAX_LIMIT) -> list[dict[str, Any]]:
        """BM25 over the pool, with an exact field id and an exact strain id
        as optional filters (an empty string filters nothing). At most
        `MAX_LIMIT` records. A query with no words returns the filtered
        records in pool order; zero-scoring records are never returned, and
        a long query whose best hit rests on one word returns nothing, as in
        `Corpus.search`."""
        limit = max(0, min(int(limit), MAX_LIMIT))
        if limit == 0:
            return []

        def keep(rid: str) -> bool:
            r = self.records_by_id[rid]
            return (not field or r.get("field") == field) and (not organism or r.get("strainId") == organism)

        tokens = tokenize(query)
        if not tokens:
            return [self.records_by_id[rid] for rid in self._order if keep(rid)][:limit]
        if self._bm25 is None:
            return []
        unique = set(tokens)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            ((n, rid, s) for n, (rid, s) in enumerate(zip(self._order, scores)) if keep(rid)),
            key=lambda x: (-x[2], x[0]),
        )
        hits = []
        for _, rid, score in ranked[:limit]:
            if score <= 0:
                break
            hits.append(self.records_by_id[rid] | {"score": round(float(score), 4), "matchedTerms": sorted(unique & self._tokens[rid])})
        if hits and len(unique) >= MIN_QUERY_TOKENS_FOR_COVERAGE and len(hits[0]["matchedTerms"]) < 2:
            return []
        return hits


def build(
    corpus: Corpus,
    candidates: Iterable[Candidate],
    decisions: dict[str, ReviewDecision],
    ontology: Iterable[dict[str, Any]] | None = None,
) -> EvidencePool:
    """The pool from its parts, so a test can hand it a fixture."""

    # A rejection counts from either side: the projection's status, or a
    # decision made since `corpus.json` was last exported (§3.R).
    rejected_ids = {rid for rid, d in decisions.items() if d.status == "rejected"} | {
        r["id"] for r in corpus.records if r.get("status") == "rejected"
    }
    kept = [r for r in corpus.records if r["id"] not in rejected_ids]
    seen = {r["id"] for r in kept}
    records = list(kept)
    labels = _field_labels(ontology)
    for c in candidates:
        if c.id in seen or c.id in rejected_ids or c.status == "rejected":
            continue
        seen.add(c.id)
        records.append(candidate_record(c, labels))
    return EvidencePool(corpus=corpus, records=records)


def load() -> EvidencePool:
    """The pool as this checkout holds it now: `corpus.json`, the cached
    extractions of the current run, and the committed decisions."""
    from . import units

    corpus = load_corpus()
    ontology = list(units.tables()["ontology"].values())
    candidates = [c for r in extract.all_cached() for c in r.candidates]
    return build(corpus, candidates, biorepo.decisions(), ontology)
