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
    monkeypatch.setattr(intake, "FIXTURE_DIR", jats)
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
