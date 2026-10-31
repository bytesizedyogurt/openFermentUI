"""What Postdoc may cite: one view over every record the project holds (OF-BLD-014 §3.4).

The pool is the project's candidates, read from PostgreSQL: the extractor's
current ones and the copies kept with standing decisions (biorepo.py). A
candidate nobody has decided is in the pool as what it is, `unverified`, and a
claim resting on it is worth that much (`weakest_provenance`). One a reviewer
decided is in it as the decision left it: the class `biorepo.provenance_of`
computes from the decision, the value a correction typed, and the sentence a
promotion re-anchored to. A record a reviewer rejected is never in the pool.

Search ranks the pool's records with BM25, in memory, for one question at a
time: a project's records are few, and the rules below (the coverage rule,
the filters, the cap) are tested on their own.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from rank_bm25 import BM25Okapi

from . import biorepo, extract, projects
from .models import Candidate, ReviewDecision

# The most records one search returns (§3.4).
MAX_LIMIT = 10

# A question this long or longer must find a record matching more than one of
# its terms, or the pool is judged not to cover it. See `EvidencePool.search`.
MIN_QUERY_TOKENS_FOR_COVERAGE = 3

# Words that carry no retrieval signal where every record is about
# fermentation. Kept small on purpose: an aggressive stop list throws away the
# terms that separate two similar questions.
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
    terms that distinguish one record from another.
    """
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def _document(record: dict[str, Any], papers_by_id: dict[str, Any]) -> str:
    """The searchable text for one record.

    The quote and the field label do most of the work. The paper's title and
    the section heading are included because a question often names the
    subject in words that appear in the title and nowhere in the quote. The
    numeric value is deliberately NOT indexed: matching on digits retrieves
    records that share a magnitude rather than a meaning.
    """
    paper = papers_by_id.get(record["paperId"], {})
    section = next((s for s in paper.get("sections", []) if s["id"] == record.get("sectionId")), {})
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


def _field_labels(ontology: Iterable[dict[str, Any]] | None) -> dict[str, str]:
    return {f["id"]: f.get("name", f["id"]) for f in ontology or []}


def candidate_record(c: Candidate, labels: dict[str, str], decision: ReviewDecision | None = None) -> dict[str, Any]:
    """A candidate as a record the pool holds: as the extractor wrote it,
    `unverified`, until a reviewer's decision stands on it, and then as the
    decision left it.

    `organism` is a strain id exactly when anchoring resolved the paper's
    wording to one, and then `organismText` keeps the wording (§2.1); a
    wording that resolved to nothing stays words and names no strain."""
    resolved = c.organismText is not None
    value, unit, quote, section_id = c.value, c.unit, c.quote, c.sectionId
    status, provenance = "unverified", "unverified"
    if decision is not None:
        status, provenance = decision.status, biorepo.provenance_of(decision)
        if decision.corrected is not None:
            value, unit = decision.corrected.value, decision.corrected.unit
        quote, section_id = decision.quote or quote, decision.sectionId or section_id
    return {
        "id": c.id,
        "paperId": c.paperId,
        "sectionId": section_id,
        "field": c.field,
        "fieldLabel": labels.get(c.field, c.field),
        "value": value,
        "unit": unit,
        "quote": quote,
        "strainId": c.organism if resolved else None,
        "organismText": c.organismText if resolved else c.organism,
        "carbonSource": c.carbonSource,
        "conditions": None,
        "provenance": provenance,
        "status": status,
        "primary": c.isPrimary,
        "citesRecordId": c.citesRecordId,
        "range": c.range.model_dump() if c.range else None,
        "source": "candidate",
    }


@dataclass
class EvidencePool:
    records: list[dict[str, Any]]
    papers_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    records_by_id: dict[str, dict[str, Any]] = field(init=False)
    _order: list[str] = field(init=False, repr=False)
    _bm25: BM25Okapi | None = field(init=False, repr=False)
    _tokens: dict[str, frozenset[str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.records_by_id = {r["id"]: r for r in self.records}
        self._order = [r["id"] for r in self.records]
        docs = [tokenize(_document(r, self.papers_by_id)) for r in self.records]
        self._bm25 = BM25Okapi(docs) if docs else None
        self._tokens = {rid: frozenset(d) for rid, d in zip(self._order, docs)}

    def paper(self, paper_id: str) -> dict[str, Any] | None:
        return self.papers_by_id.get(paper_id)

    def record(self, record_id: str) -> dict[str, Any] | None:
        return self.records_by_id.get(record_id)

    def search(self, query: str, field: str = "", organism: str = "", limit: int = MAX_LIMIT) -> list[dict[str, Any]]:
        """BM25 over the pool, with an exact field id and an exact strain id
        as optional filters (an empty string filters nothing). At most
        `MAX_LIMIT` records. A query with no words returns the filtered
        records in pool order.

        Two things are dropped rather than returned. Zero-scoring records:
        handing the model filler to reach a round number is how a question
        the pool cannot answer gets answered anyway, and "nothing matched"
        has to stay visible. And the whole result set when a question of
        `MIN_QUERY_TOKENS_FOR_COVERAGE` terms or more has a best hit resting
        on a single one: in a pool this small almost every token is rare, so
        IDF cannot tell a generic verb from a discriminative one, and a lone
        one-word hit is a coincidence the model would cite."""
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
    candidates: Iterable[Candidate],
    decisions: dict[str, ReviewDecision],
    ontology: Iterable[dict[str, Any]] | None = None,
    *,
    records: Iterable[dict[str, Any]] = (),
    papers: Iterable[dict[str, Any]] = (),
) -> EvidencePool:
    """The pool from its parts, so a test can hand it a fixture: the
    candidates, the decisions that stand on them, and, for a test, records
    already in a record's shape and the papers they are on."""
    rejected = {rid for rid, d in decisions.items() if d.status == "rejected"}
    fixed = [r for r in records if r["id"] not in rejected and r.get("status") != "rejected"]
    seen = {r["id"] for r in fixed}
    out = list(fixed)
    labels = _field_labels(ontology)
    for c in candidates:
        if c.id in seen or c.id in rejected or c.status == "rejected":
            continue
        seen.add(c.id)
        out.append(candidate_record(c, labels, decisions.get(c.id)))
    return EvidencePool(records=out, papers_by_id={p["id"]: p for p in papers})


def load() -> EvidencePool:
    """The pool as the project holds it now: the extractor's current
    candidates, the copies kept with standing decisions, the decisions, and
    the titles of the documents the project holds."""
    from . import units
    from .literature import kit

    ontology = list(units.tables()["ontology"].values())
    repo = biorepo.read()
    current = [c for r in extract.all_cached() for c in r.candidates]
    held = {c.id for c in current}
    kept = [c for c in repo.records if c.id not in held]
    papers = [{"id": d.id, "title": d.title, "year": d.publication_year, "textSource": "full-text"}
              for d, _ in kit.documents(projects.current())]
    return build(current + kept, repo.decisions, ontology, papers=papers)
