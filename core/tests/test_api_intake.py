"""The Intake endpoints and the overlay (OF-BLD-012 §5.2, §2.1; ADR-002).

Through FastAPI's test client, in fixture mode: nothing here touches the
network. A document is collected into the project's literature in Sci RAG
Kit, and the overlay carries it as a paper. The real fetch is exercised by the
`live` test in test_intake_live.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core.literature import collectors
from openferment_core.api import app
from openferment_core.models import Overlay

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")


@pytest.fixture
def client():
    return TestClient(app)


def test_health_still_answers(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["service"] == "openferment-core"


def test_the_overlay_holds_no_paper_before_anything_is_collected(client, kit_database):
    body = client.get("/api/biorepo/overlay").json()
    overlay = Overlay.model_validate(body)
    assert overlay.papers == {} and overlay.runs == [] and overlay.candidates == []
    assert overlay.records == {}


def test_the_corpus_fetch_routes_are_gone(client):
    assert client.post("/api/intake/T5/fetch").status_code in (404, 405)
    assert client.get("/api/intake/status").status_code in (404, 405)


# ── collection into Sci RAG Kit (ADR-002) ──────────────────────────────


@pytest.fixture
def kit_client(kit_database, monkeypatch, tmp_path):
    """The structural fixture under a PMCID of this test's own, with a
    sentence of this test's own: the kit's rows are committed in the
    session's database, and a text another test stored would come back linked."""
    import uuid

    pmcid = f"PMC{uuid.uuid4().int % 10**9}"
    jats = tmp_path / "jats-own"
    jats.mkdir()
    xml = (FIXTURES / "jats" / "structural.xml").read_text(encoding="utf-8")
    (jats / f"{pmcid}.xml").write_text(
        xml.replace("<body>", f"<body><p>Collected under {pmcid}.</p>", 1), encoding="utf-8"
    )
    monkeypatch.setattr(collectors, "FIXTURE_DIR", jats)
    return TestClient(app), pmcid


def test_a_paper_collected_by_its_pmcid_is_stored_once_and_listed(kit_client):
    client, pmcid = kit_client
    first = client.post("/api/intake/collect", json={"identifier": pmcid, "by": "A. Reader", "reason": "feed rates"})
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "ingested" and body["collector"] == "europepmc" and body["identifier"] == pmcid
    assert body["title"] == "A structural fixture for the Intake parser"
    assert body["licenceClass"] == "open_commercial" and body["tables"] >= 1 and body["chunks"] >= 1

    again = client.post("/api/intake/collect", json={"identifier": pmcid, "by": "A. Reader"}).json()
    assert again["status"] == "held" and again["documentId"] == body["documentId"]

    [listed] = client.get("/api/literature/documents").json()
    assert listed["documentId"] == body["documentId"] and listed["collector"] == "europepmc"
    assert listed["source"] == "project:test-project:europepmc" and listed["linkedBy"] == "A. Reader"
    assert listed["selection"]["reason"] == "feed rates" and listed["selection"]["pmcid"] == pmcid
    assert listed["sourceRef"] == f"https://europepmc.org/article/PMC/{pmcid}"
    stats = client.get("/api/literature/stats").json()
    assert stats["documents"] == 1 and stats["chunks"] == body["chunks"]


def test_a_paper_not_collected_is_a_200_with_the_reason(kit_client):
    client, _ = kit_client
    body = client.post("/api/intake/collect", json={"identifier": "PMC1", "by": "A. Reader"}).json()
    assert body["status"] == "failed" and "no fixture" in body["reason"] and body["documentId"] is None
    body = client.post("/api/intake/collect", json={"identifier": "4242", "by": "A. Reader"}).json()
    assert body["status"] == "failed" and "PMID:4242 or OSTI:4242" in body["reason"]
    assert client.get("/api/literature/documents").json() == []
    assert client.post("/api/intake/collect", json={"identifier": "PMC1"}).status_code == 422, "who asked is required"


def test_an_upload_and_a_paste_are_stored_with_the_class_the_person_chose(kit_client):
    import uuid

    client, _ = kit_client
    words = f"# Bench notes\n\nThe feed ran at a placeholder rate. {uuid.uuid4().hex}\n"
    up = client.post(
        "/api/intake/upload",
        files={"file": ("bench notes.md", words.encode(), "text/markdown")},
        data={"by": "A. Reader", "licenceClass": "restricted", "title": "Bench notes"},
    ).json()
    assert up["status"] == "ingested" and up["collector"] == "upload" and up["licenceClass"] == "restricted"

    pasted = client.post("/api/intake/paste", json={
        "title": "Pasted methods", "text": f"Grown in a placeholder medium. {uuid.uuid4().hex}", "by": "A. Reader",
        "licenceClass": "public",
    }).json()
    assert pasted["status"] == "ingested" and pasted["collector"] == "paste" and pasted["licenceClass"] == "public"

    listed = {d["documentId"]: d for d in client.get("/api/literature/documents").json()}
    assert listed[up["documentId"]]["sourceRef"] == "upload:bench notes.md"
    assert listed[pasted["documentId"]]["sourceRef"] == "paste:Pasted methods"
    assert listed[up["documentId"]]["licenceClass"] == "restricted"

    refused = client.post(
        "/api/intake/upload", files={"file": ("notes.docx", b"x", "application/octet-stream")}, data={"by": "A. Reader"},
    ).json()
    assert refused["status"] == "failed" and "is not one of" in refused["reason"]


def test_collection_names_its_project(kit_client):
    from openferment_core import projects

    client, pmcid = kit_client
    client.headers.pop(projects.HEADER)
    assert client.post("/api/intake/collect", json={"identifier": pmcid, "by": "A. Reader"}).status_code == 422
    assert client.get("/api/literature/documents").status_code == 422


def test_the_overlay_carries_a_collected_document_as_a_paper(kit_client):
    client, pmcid = kit_client
    body = client.post("/api/intake/collect", json={"identifier": pmcid, "by": "A. Reader"}).json()
    overlay = Overlay.model_validate(client.get("/api/biorepo/overlay").json())
    paper = overlay.papers[body["documentId"]]
    assert paper.ingest == "complete" and paper.textSource == "full-text" and paper.source == "europepmc"
    assert paper.title == "A structural fixture for the Intake parser" and paper.pmcid == pmcid
    assert paper.licenceClass == "open_commercial" and paper.license == "https://creativecommons.org/licenses/by/4.0/"
    assert [s.id for s in paper.sections] == [f"p{i}" for i in range(len(paper.sections))]
    assert any("| Placeholder A | 7 | mg L-1 |" in s.text for s in paper.sections), "the table keeps its rows"
