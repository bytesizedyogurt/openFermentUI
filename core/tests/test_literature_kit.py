"""Sci RAG Kit as openFerment runs it (ADR-002; execution prompt §8.2): one
document stored once and held by each project that collects it, every read
inside the project, the kit's settings and factories openFerment's own, and
its REST app at /rag behind its key.

Offline: the kit embeds with its deterministic local embedder here
(conftest), and a model, where one is needed, is the kit's MockLLM. Each test
stores texts of its own (`_text`): the kit's rows are committed in the
session's database, and a text another test stored would come back linked.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sci_rag.ingest.manifest import CorpusEntry
from sci_rag.llm.client import MockLLM
from sci_rag.server.errors import ApiError
from sqlalchemy import insert

from openferment_core import db, projects
from openferment_core.db import models as t
from openferment_core.literature import kit

HERE = "test-project"
THERE = "other-project"


async def _add_project(project_id: str) -> None:
    async with db.session() as s:
        await s.execute(insert(t.projects).values(id=project_id, name=project_id, created_by="test"))


@pytest.fixture(autouse=True)
def _kit(kit_database):
    pass


@pytest.fixture
def two_projects():
    db.run(_add_project(THERE))


def _text(topic: str) -> str:
    return (
        f"# {topic}\n\n## Methods\n\nThe {topic} was studied in a placeholder vessel. "
        f"Run {uuid.uuid4().hex}.\n\n## Results\n\nThe {topic} behaved as a placeholder does.\n"
    )


def _store(tmp_path, project_id: str, topic: str, text: str | None = None, collector: str = "paste") -> kit.Stored:
    path = tmp_path / f"{uuid.uuid4().hex}.md"
    path.write_text(text or _text(topic), encoding="utf-8")
    entry = CorpusEntry(path=path, title=topic, source=kit.source(project_id, collector), license_class="public")
    [stored] = kit.ingest([entry], project_id=project_id, selections=[{"collector": collector, "topic": topic}], by="test")
    return stored


def test_a_source_names_the_project_and_the_collector():
    assert kit.source("p1", "europepmc") == "project:p1:europepmc"
    with pytest.raises(ValueError):
        kit.source("p1", "somewhere")


def test_a_document_is_stored_once_and_held_by_each_project_that_collects_it(tmp_path, two_projects):
    text = _text("shared feed study")
    first = _store(tmp_path, HERE, "shared feed study", text)
    assert first.status == "ingested" and first.document_id and first.chunks >= 1
    assert _store(tmp_path, HERE, "shared feed study", text) == kit.Stored("held", first.document_id, first_detail(first))
    other = _store(tmp_path, THERE, "shared feed study", text, collector="upload")
    assert other.status == "linked" and other.document_id == first.document_id
    link = db.run(kit.linked(THERE, first.document_id))
    assert link["selection"] == {"collector": "upload", "topic": "shared feed study"} and link["created_by"] == "test"


def first_detail(stored: kit.Stored) -> str:
    return f"same content as document {stored.document_id}"


def test_a_project_sees_its_own_documents_and_those_it_shares_and_no_others(tmp_path, two_projects):
    mine = _store(tmp_path, HERE, "glucose feed")
    theirs = _store(tmp_path, THERE, "glucose feed in the other project")
    shared_text = _text("glucose feed shared")
    shared = _store(tmp_path, THERE, "glucose feed shared", shared_text)
    assert _store(tmp_path, HERE, "glucose feed shared", shared_text).status == "linked"

    seen = db.run(kit.visible(HERE))
    assert set(seen.documents) == {mine.document_id, shared.document_id}
    assert theirs.document_id in seen.excluded and kit.source(THERE, "paste") in seen.sources

    here = {item.document_id for item in kit.retrieve("glucose feed placeholder vessel", project_id=HERE, top_k=20).items}
    there = {item.document_id for item in kit.retrieve("glucose feed placeholder vessel", project_id=THERE, top_k=20).items}
    assert here == {mine.document_id, shared.document_id}
    assert there == {theirs.document_id, shared.document_id}
    assert [d.id for d, _ in kit.documents(HERE)] == [shared.document_id, mine.document_id], "newest link first"


def test_a_project_that_holds_nothing_sees_nothing(tmp_path, two_projects):
    _store(tmp_path, HERE, "a document only this project holds")
    assert db.run(kit.visible(THERE)) == kit.Visible((), (), ())
    assert kit.retrieve("a document only this project holds", project_id=THERE).items == []
    assert kit.documents(THERE) == []
    assert kit.stats(THERE)["documents"] == 0


def test_a_document_the_project_does_not_hold_is_not_found(tmp_path, two_projects):
    theirs = _store(tmp_path, THERE, "a report held elsewhere")
    with pytest.raises(ApiError) as missing:
        kit.document(theirs.document_id, project_id=HERE)
    assert missing.value.status == 404
    document, chunks = kit.document(theirs.document_id, project_id=THERE)
    assert document.title == "a report held elsewhere" and [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_stats_count_the_projects_documents(tmp_path):
    stored = _store(tmp_path, HERE, "a counted document")
    counts = kit.stats(HERE)
    assert counts["documents"] == len(db.run(kit.visible(HERE)).documents) >= 1
    assert counts["sources"] == {kit.source(HERE, "paste"): counts["documents"]}
    assert counts["chunks"] >= stored.chunks


def test_the_kits_settings_are_openferments_whatever_the_environment_says(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("SCI_RAG_EMBEDDING_DIM=1536\nSCI_RAG_API_KEYS=\nSCI_RAG_CORS_ORIGINS=*\n")
    monkeypatch.setenv("SCI_RAG_EMBEDDING_PROVIDER", "google")
    monkeypatch.setenv("SCI_RAG_LLM_PROVIDER", "anthropic")
    kit.dispose()
    try:
        s = kit.settings()
        assert (s.embedding_dim, s.embedding_provider, s.cors_origins) == (384, "local-hash", "")
        assert s.llm_provider == "google", "the shipped default: the kit never builds a model client of its own"
        assert list(__import__("json").loads(s.api_keys).values()) == [{"scopes": list(kit.RAG_SCOPES)}]
    finally:
        kit.dispose()


def test_the_kits_own_factories_answer_with_openferments_embedder_and_model(monkeypatch):
    import sci_rag.embed
    import sci_rag.llm

    mock = MockLLM(default_response="from the installed model")
    monkeypatch.setattr(kit, "_MODEL", lambda role: mock)
    kit.service()
    assert sci_rag.embed.get_embedder(None) is kit.embedder()
    assert db.run(sci_rag.llm.get_llm(None, role="extraction").generate("q")) == "from the installed model"
    with pytest.raises(kit.KitUnavailable):
        sci_rag.llm.get_llm(None, api_key_override="a key of my own")
    monkeypatch.setattr(kit, "_MODEL", None)
    with pytest.raises(kit.KitUnavailable):
        db.run(sci_rag.llm.get_llm(None).generate("q"))


def _answer(query: str, project_id: str, **kw):
    async def go():
        with projects.using(project_id):
            return [e async for e in kit.service().answer_stream(query, **kw)]

    return db.run(go())


def test_an_answer_cites_only_the_projects_documents(tmp_path, two_projects, monkeypatch):
    mine = _store(tmp_path, HERE, "xylose uptake")
    _store(tmp_path, THERE, "xylose uptake elsewhere")
    mock = MockLLM(responses=["Xylose was taken up [1]."])
    monkeypatch.setattr(kit, "_MODEL", lambda role: mock)
    events = _answer("xylose uptake placeholder", HERE, profile="interactive")
    text = "".join(e.data["text"] for e in events if e.type == "delta")
    cited = next(e.data["citations"] for e in events if e.type == "citations")
    assert text == "Xylose was taken up [1]."
    assert {c["document_id"] for c in cited} == {mine.document_id}
    assert [c["index"] for c in cited if c["cited"]] == [1]


def test_a_model_key_of_the_callers_own_is_refused():
    with pytest.raises(ApiError) as refused:
        _answer("anything", HERE, api_key_override="sk-not-ours")
    assert refused.value.status == 403


@pytest.fixture
def rag_key(monkeypatch):
    monkeypatch.setenv(kit.RAG_KEY, "a-test-key")
    kit.dispose()
    yield {"Authorization": "Bearer a-test-key"}
    monkeypatch.delenv(kit.RAG_KEY)
    kit.dispose()


def test_rag_answers_with_its_key_inside_the_named_project(tmp_path, two_projects, rag_key):
    from openferment_core.api import app

    mine = _store(tmp_path, HERE, "rag lactate")
    _store(tmp_path, THERE, "rag lactate elsewhere")
    client = TestClient(app)
    body = {"query": "rag lactate placeholder", "top_k": 20}
    assert client.post("/rag/v1/query", json=body).status_code == 401
    assert client.post("/rag/v1/query", json=body, headers={"Authorization": "Bearer wrong"}).status_code == 401
    answered = client.post("/rag/v1/query", json=body, headers=rag_key)
    assert answered.status_code == 200, answered.text
    assert {r["document_id"] for r in answered.json()["items"]} == {mine.document_id}
    listed = client.get("/rag/v1/documents", headers=rag_key).json()
    assert {d["id"] for d in listed["documents"]} == set(db.run(kit.visible(HERE)).documents)


def test_rag_refuses_a_request_that_names_no_project_and_serves_no_mcp(rag_key):
    from openferment_core.api import app

    client = TestClient(app)
    client.headers.pop(projects.HEADER)
    refused = client.post("/rag/v1/query", json={"query": "anything"}, headers=rag_key)
    assert refused.status_code == 422 and refused.json()["code"] == "project_required"
    assert TestClient(app).post("/rag/mcp/", json={}, headers=rag_key).status_code == 404


def test_rag_with_no_key_set_accepts_none(monkeypatch):
    from openferment_core.api import app

    monkeypatch.delenv(kit.RAG_KEY, raising=False)
    kit.dispose()
    client = TestClient(app)
    assert client.post("/rag/v1/query", json={"query": "anything"}).status_code == 401
    assert client.post("/rag/v1/query", json={"query": "anything"}, headers={"Authorization": "Bearer guess"}).status_code == 401


# ── extraction over the kit's passages (stage 3, step 2) ────────────────


def test_a_document_reads_as_its_passages_in_order(tmp_path):
    stored = _store(tmp_path, HERE, "passages in order")
    held = kit.passages(stored.document_id, project_id=HERE)
    assert held.document.title == "passages in order"
    assert [p["id"] for p in held.sections] == [f"p{i}" for i in range(len(held.sections))]
    assert all(not p["text"].startswith("passages in order") for p in held.sections), "the breadcrumb is not the text"
    assert {p["heading"] for p in held.sections} <= {"Methods", "Results", "passages in order"}
    assert [(d.id, [p["id"] for p in passages]) for d, _, passages in kit.held(HERE) if d.id == stored.document_id] == [
        (stored.document_id, [p["id"] for p in held.sections])
    ]


def test_extraction_anchors_in_the_kits_passages_and_witness_scores_the_reviewers_value(tmp_path, monkeypatch):
    from openferment_core import biorepo, extract, witness
    from openferment_core.models import Quantity, ReviewDecision

    sentence = "The culture reached a titre of 7 g/L of protein on day three."
    stored = _store(tmp_path, HERE, "a titre", text=f"# A titre\n\n## Results\n\n{sentence} Run {uuid.uuid4().hex}.\n")
    [where] = [p["id"] for p in kit.passages(stored.document_id, project_id=HERE).sections if sentence in p["text"]]
    raw = {"candidates": [
        {"sectionId": where, "field": "titer_secreted", "value": 7, "unit": "g/L", "quote": sentence,
         "isPrimary": True, "confidence": 0.9},
        {"sectionId": where, "field": "titer_secreted", "value": 7, "unit": "g/L",
         "quote": "a sentence the document does not hold, 7 g/L", "isPrimary": True, "confidence": 0.9},
    ]}
    monkeypatch.setattr(extract, "call_model", lambda *_: (raw, extract.Usage()))
    result = extract.extract_paper(stored.document_id)
    [candidate] = result.candidates
    assert candidate.paperId == stored.document_id and candidate.sectionId == where and result.rejected == 1

    with pytest.raises(extract.NothingToAnchor):
        extract.extract_paper("0" * 32)

    biorepo.write(ReviewDecision(
        status="verified", provenance="curated", reviewer="A. Reader", recordId=candidate.id,
        at="2026-10-30T12:00:00Z", gold=Quantity(value=7, unit="g/L"),
    ))
    assert witness.reference_records() == [{
        "id": candidate.id, "paperId": stored.document_id, "field": "titer_secreted", "value": 7.0, "unit": "g/L",
        "source": "biorepo",
    }]
    [run] = witness.runs()
    assert [(r.goldRecordId, r.outcome) for r in run.results] == [(candidate.id, "match")]


# ── search and answers over the kit (stage 3, step 3) ───────────────────


def test_search_finds_the_projects_passages_with_their_passage_ids(tmp_path, two_projects):
    mine = _store(tmp_path, HERE, "lactate search")
    _store(tmp_path, THERE, "lactate search elsewhere")
    hits, result = kit.search("lactate search placeholder vessel", project_id=HERE, top_k=10)
    assert {h.document_id for h in hits} == {mine.document_id}
    passages = {p["id"]: p["text"] for p in kit.passages(mine.document_id, project_id=HERE).sections}
    for h in hits:
        assert passages[h.passage_id] == h.text, "a hit's words are its passage's"
        assert h.citation and h.licence_class == "public"
    assert result.profile == "interactive"


def test_the_search_route_answers_in_the_named_project(tmp_path, two_projects):
    from openferment_core.api import app

    mine = _store(tmp_path, HERE, "route search")
    client = TestClient(app)
    body = client.get("/api/literature/search", params={"q": "route search placeholder"}).json()
    assert body["profile"] == "interactive" and {h["documentId"] for h in body["hits"]} == {mine.document_id}
    assert all(h["passageId"].startswith("p") for h in body["hits"])
    assert client.get("/api/literature/search", params={"q": "  "}).status_code == 422


def test_the_passage_tool_searches_the_project_through_the_kit(tmp_path):
    from openferment_core import tools

    mine = _store(tmp_path, HERE, "tool search")
    result = tools.run("search_passages", {"query": "tool search placeholder vessel", "k": 3}, tools.ToolContext())
    assert result.error is None, result.error
    assert result.summary["engine"] == "sci-rag-kit"
    assert {p.paperId for p in result.passages} == {mine.document_id}
    assert all(h["paperTitle"] == "tool search" for h in result.summary["passages"])


def test_an_answer_streams_its_words_and_citations_with_passage_ids(tmp_path, monkeypatch):
    from openferment_core.api import app

    mine = _store(tmp_path, HERE, "streamed answer")
    monkeypatch.setattr(kit, "_MODEL", lambda role: MockLLM(responses=["It was placeholder work [1]."]))
    client = TestClient(app)
    with client.stream("POST", "/api/literature/answer", json={"question": "streamed answer placeholder"}) as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        raw = "".join(r.iter_text())
    events = [(block.split("\n")[0][len("event: "):], __import__("json").loads(block.split("\n")[1][len("data: "):]))
              for block in raw.strip().split("\n\n")]
    kinds = [k for k, _ in events]
    assert kinds[-1] == "done" and "citations" in kinds
    assert "".join(d["text"] for k, d in events if k == "delta") == "It was placeholder work [1]."
    [cited] = [c for k, d in events if k == "citations" for c in d["citations"] if c["cited"]]
    assert cited["document_id"] == mine.document_id and cited["passage_id"].startswith("p")
    assert all("_" not in key[:1] for _, d in events for key in d), "nothing internal to the kit is sent"
