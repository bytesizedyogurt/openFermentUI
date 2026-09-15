"""The Intake endpoints and the overlay (OF-BLD-012 §5.2, §2.1).

Through FastAPI's test client, in fixture mode, with the cache pointed at a
temporary directory: nothing here touches the network or `core/data/`. The
real fetch is exercised by the `live` test in test_intake_live.py.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import biorepo, extract, intake
from openferment_core.api import app
from openferment_core.models import Overlay

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    # Only the structural document is a fixture here. A real PMC8471596.xml
    # saved beside it (test_intake's skip message asks for one) must not turn
    # B5's fixture-mode fetch from the failure these tests expect into a
    # success.
    jats = tmp_path / "jats"
    jats.mkdir()
    shutil.copy(FIXTURES / "jats" / "structural.xml", jats / "structural.xml")
    monkeypatch.setattr(intake, "FIXTURE_DIR", jats)
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(biorepo, "PATH", tmp_path / "biorepo.json")


@pytest.fixture
def client():
    return TestClient(app)


def test_health_still_answers(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["records"] > 0


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
    # B5's real PMCID has no fixture, so in fixture mode the fetch fails —
    # and the failure is a result the board can render, not an error.
    r = client.post("/api/intake/B5/fetch")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed:fetch"
    assert "no fixture" in body["reason"]

    status = client.get("/api/intake/status").json()
    assert status["B5"]["ingest"] == "failed:fetch"
    assert status["B5"]["textSource"] == "curation-note"

    overlay = Overlay.model_validate(client.get("/api/biorepo/overlay").json())
    assert overlay.papers["B5"].ingest == "failed:fetch"
    assert overlay.papers["B5"].sections == []
    assert overlay.papers["B5"].reason and "no fixture" in overlay.papers["B5"].reason


def test_a_successful_fetch_puts_the_papers_words_in_the_overlay(client, monkeypatch):
    # Point B5 at the structural fixture instead of its real PMCID.
    monkeypatch.setattr(intake, "resolve_pmcid", lambda paper: "structural")
    body = client.post("/api/intake/B5/fetch").json()
    assert body["status"] == "complete"
    assert body["sections"][0]["id"] == "abstract"

    overlay = Overlay.model_validate(client.get("/api/biorepo/overlay").json())
    paper = overlay.papers["B5"]
    assert paper.ingest == "complete" and paper.textSource == "full-text"
    assert [s.id for s in paper.sections][:2] == ["abstract", "s1"]
    assert paper.license and "creativecommons" in paper.license

    # Idempotent: a second call returns the cache, not a second fetch.
    again = client.post("/api/intake/B5/fetch").json()
    assert again["fetchedAt"] == body["fetchedAt"]
    forced = client.post("/api/intake/B5/fetch?force=true").json()
    assert forced["status"] == "complete"


def test_the_smoke_overlay_fixture_matches_the_overlay_shape():
    """scripts/smoke.mjs serves this file as the overlay. It is committed, so
    it can drift from the model; this ties it to the shape the browser reads.

    Regenerate with `pnpm demo:fixtures` (core/openferment_core/demo.py)."""
    raw = json.loads((FIXTURES / "overlay-smoke.json").read_text(encoding="utf-8"))
    overlay = Overlay.model_validate(raw)
    assert "B5" in overlay.papers
    assert overlay.papers["B5"].textSource == "full-text"
    assert overlay.papers["B5"].sections[0].id == "abstract"
    assert "not the paper" in raw["_note"]
    # §6.4 — the run Witness scores in the smoke test: match_run's own output
    # over B5's three curated records and the two candidates below.
    assert [r.run for r in overlay.runs] == ["haiku-1"]
    # One candidate scores one record: the colony-time candidate is spent
    # on r-B5-1 as a mismatch; its siblings are misses, not mismatches.
    assert [r.outcome for r in overlay.runs[0].results] == ["value_mismatch", "miss", "miss"]
    assert overlay.runs[0].falsePositives == []
    # §7.3 — two anchored candidates: a titre the seed has no B5 record for
    # (a new record, so Guild queues it) and the same row read as a colony
    # time (matching r-B5-*'s field, so it sits beside those cards).
    assert [(c.id, c.field) for c in overlay.candidates] == [
        ("hk1-B5-a07dd73c", "titer_secreted"),
        ("hk1-B5-95f64ef4", "time_to_colony"),
    ]
    assert all(c.extractorRun == "haiku-1" and c.status == "unverified" for c in overlay.candidates)
