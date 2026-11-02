"""The stage 3 gate over Sci RAG Kit's demo corpus (execution prompt §10 stage 3).

Marked `lit`: the five demo documents (core/tests/fixtures/kit-demo/, CC0,
fictional) are embedded with FastEmbed's model, as the service embeds, and
held by a project; a second project holds two of them. Over them: the corpus
is stored once and linked by each project, a search finds the passage that
answers each of the kit's seed questions with its citation, an answer cites
the document its evidence stands in, an extraction anchors in a demo
document's passage and a reviewer's decision on it is accepted, and each
project sees its own documents alone.

The model is the kit's MockLLM where one is asked: no key, no spend. The kit's
rows are committed in the session's database, so the corpus is embedded
once and every later test links what is there.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sci_rag.ingest.manifest import CorpusEntry
from sci_rag.llm.client import MockLLM
from sqlalchemy import insert

from openferment_core import biorepo, db, extract, projects, witness
from openferment_core.db import models as t
from openferment_core.literature import EMBEDDING_DIM, EMBEDDING_MODEL, kit
from openferment_core.models import Quantity, ReviewDecision

pytestmark = pytest.mark.lit

DEMO = Path(__file__).parent / "fixtures" / "kit-demo"
HERE = "test-project"
THERE = "other-project"
# The second project holds these two alone.
THEIRS = ("Small-Scale Gasification of Walnut Shells and Orchard Chips",
          "Anaerobic Digestion of Crop Residues: A Working Primer")


def _manifest() -> list[dict]:
    return [json.loads(line) for line in (DEMO / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def _questions() -> list[dict]:
    return [json.loads(line) for line in (DEMO / "eval_seed_questions.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def _hold(project_id: str, rows: list[dict]) -> dict[str, kit.Stored]:
    entries = [CorpusEntry(**{**row, "path": DEMO / row["path"], "source": kit.source(project_id, "upload")}) for row in rows]
    stored = kit.ingest(entries, project_id=project_id, selections=[{"collector": "upload", "title": r["title"]} for r in rows],
                        by="the demo")
    return {row["title"]: s for row, s in zip(rows, stored, strict=True)}


@pytest.fixture
def demo(kit_database) -> dict[str, dict[str, kit.Stored]]:
    async def other() -> None:
        async with db.session() as s:
            await s.execute(insert(t.projects).values(id=THERE, name=THERE, created_by="test"))

    db.run(other())
    rows = _manifest()
    return {HERE: _hold(HERE, rows), THERE: _hold(THERE, [r for r in rows if r["title"] in THEIRS])}


def test_the_corpus_is_embedded_once_and_held_by_each_project_that_collects_it(demo):
    mine, theirs = demo[HERE], demo[THERE]
    assert len(mine) == 5 and all(s.status in ("ingested", "linked") and s.document_id for s in mine.values())
    assert all(theirs[title].status == "linked" and theirs[title].document_id == mine[title].document_id for title in THEIRS)
    counts = kit.stats(HERE)
    assert counts["documents"] == 5 and counts["chunks"] >= 5
    assert counts["embedding_versions"] == {f"fastembed:{EMBEDDING_MODEL}@{EMBEDDING_DIM}": counts["chunks"]}


def test_a_search_finds_the_passage_that_answers_each_seed_question_with_its_citation(demo):
    asked = [q for q in _questions() if "unanswerable" not in q["tags"]]
    found = 0
    for q in asked:
        hits, _ = kit.search(q["question"], project_id=HERE, top_k=5)
        assert hits and all(h.citation and h.passage_id.startswith("p") for h in hits), q["id"]
        titles = [h.title for h in hits]
        phrases = [p.lower() for p in q["evidence_phrases"]]
        found += any(t in q["reference_titles"] and any(p in h.text.lower() for p in phrases)
                     for t, h in zip(titles, hits, strict=True))
    assert found / len(asked) >= 0.8, f"{found} of {len(asked)} seed questions answered in the top five"


def test_an_answer_cites_the_document_its_evidence_stands_in(demo, monkeypatch):
    monkeypatch.setattr(kit, "_MODEL", lambda role: MockLLM(responses=["About 302,000 dry tons were generated [1]."]))
    events = list(kit.answer("How much rice straw was generated in the Colusa Basin in 2023?", project_id=HERE))
    assert events[-1]["type"] == "done"
    [cited] = [c for e in events if e["type"] == "citations" for c in e["citations"] if c["cited"]]
    assert cited["document_id"] == demo[HERE]["Colusa Basin Rice Straw Resource Assessment 2023"].document_id
    passages = {p["id"]: p["text"] for p in kit.passages(cited["document_id"], project_id=HERE).sections}
    assert "302,000 dry tons" in passages[cited["passage_id"]]


def test_an_extraction_anchors_in_a_demo_passage_and_a_decision_on_it_is_accepted(demo, monkeypatch):
    document_id = demo[HERE]["Demo Region Policy Landscape for Agricultural Residue Utilization"].document_id
    [where] = [p["id"] for p in kit.passages(document_id, project_id=HERE).sections
               if "target decision time of 120 days" in p["text"]]
    quote = "a target decision time of 120 days"
    raw = {"candidates": [{"sectionId": where, "field": "time_to_colony", "value": 120, "unit": "d", "quote": quote,
                           "isPrimary": True, "confidence": 0.9}]}
    monkeypatch.setattr(extract, "call_model", lambda *_: (raw, extract.Usage()))
    [candidate] = extract.extract_paper(document_id, force=True).candidates
    assert (candidate.paperId, candidate.sectionId, candidate.quote) == (document_id, where, quote)

    biorepo.write(ReviewDecision(status="verified", provenance="curated", reviewer="A. Reader", recordId=candidate.id,
                                 at="2026-10-30T12:00:00Z", gold=Quantity(value=120, unit="d")))
    assert candidate.id in biorepo.decisions()
    [run] = witness.runs()
    assert (candidate.id, "match") in [(r.goldRecordId, r.outcome) for r in run.results]


def test_each_project_sees_its_own_documents_alone(demo):
    theirs = {demo[THERE][title].document_id for title in THEIRS}
    rice = "How much rice straw was generated in the Colusa Basin in 2023?"
    here = {h.document_id for h in kit.search(rice, project_id=HERE, top_k=10)[0]}
    there = {h.document_id for h in kit.search(rice, project_id=THERE, top_k=10)[0]}
    assert demo[HERE]["Colusa Basin Rice Straw Resource Assessment 2023"].document_id in here
    assert there and there <= theirs
    assert {d.id for d, _ in kit.documents(THERE)} == theirs
    with projects.using(THERE):
        assert kit.stats(THERE)["documents"] == 2
