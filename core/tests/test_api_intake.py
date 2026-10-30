"""The Intake endpoints and the overlay (OF-BLD-012 §5.2, §2.1).

Through FastAPI's test client, in fixture mode, with the cache pointed at a
temporary directory: nothing here touches the network or `core/data/`. The
real fetch is exercised by the `live` test in test_intake_live.py.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import intake
from openferment_core.literature import collectors
from openferment_core.api import app
from openferment_core.models import Overlay

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path, test_corpus):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    # Only the structural document is a fixture here, so the fictional T5's
    # fixture-mode fetch fails as these tests expect, whatever else is saved
    # beside it.
    jats = tmp_path / "jats"
    jats.mkdir()
    shutil.copy(FIXTURES / "jats" / "structural.xml", jats / "structural.xml")
    monkeypatch.setattr(collectors, "FIXTURE_DIR", jats)
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")


@pytest.fixture
def client():
    return TestClient(app)


def test_health_still_answers(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["records"] > 0, "the test corpus holds records"


def test_status_and_overlay_are_empty_before_any_fetch(client):
    assert client.get("/api/intake/status").json() == {}
    body = client.get("/api/biorepo/overlay").json()
    overlay = Overlay.model_validate(body)
    assert overlay.papers == {} and overlay.runs == [] and overlay.candidates == []
    assert overlay.records == {}


def test_fetching_an_unknown_paper_is_a_404(client):
    r = client.post("/api/intake/NOPE/fetch")
    assert r.status_code == 404
    assert "not in the corpus" in r.json()["detail"]


def test_a_failed_fetch_is_a_200_with_a_reason_and_reaches_status_and_overlay(client):
    # T5's PMCID has no fixture, so in fixture mode the fetch fails — and the
    # failure is a result the board can render.
    r = client.post("/api/intake/T5/fetch")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed:fetch"
    assert "no fixture" in body["reason"]

    status = client.get("/api/intake/status").json()
    assert status["T5"]["ingest"] == "failed:fetch"
    assert status["T5"]["textSource"] == "curation-note"

    overlay = Overlay.model_validate(client.get("/api/biorepo/overlay").json())
    assert overlay.papers["T5"].ingest == "failed:fetch"
    assert overlay.papers["T5"].sections == []
    assert overlay.papers["T5"].reason and "no fixture" in overlay.papers["T5"].reason


def test_a_successful_fetch_puts_the_papers_words_in_the_overlay(client, monkeypatch):
    # Point T5 at the structural fixture.
    monkeypatch.setattr(intake, "resolve_pmcid", lambda paper: "structural")
    body = client.post("/api/intake/T5/fetch").json()
    assert body["status"] == "complete"
    assert body["sections"][0]["id"] == "abstract"

    overlay = Overlay.model_validate(client.get("/api/biorepo/overlay").json())
    paper = overlay.papers["T5"]
    assert paper.ingest == "complete" and paper.textSource == "full-text"
    assert [s.id for s in paper.sections][:2] == ["abstract", "s1"]
    assert paper.license and "creativecommons" in paper.license

    # Idempotent: a second call returns the cache, not a second fetch.
    again = client.post("/api/intake/T5/fetch").json()
    assert again["fetchedAt"] == body["fetchedAt"]
    forced = client.post("/api/intake/T5/fetch?force=true").json()
    assert forced["status"] == "complete"


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
    assert listed["source"] == f"project:test-project:europepmc" and listed["linkedBy"] == "A. Reader"
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
