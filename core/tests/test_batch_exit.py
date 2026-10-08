"""A failed night exits non-zero (OF-BLD-012 §B.8).

`intake --all` and `extract --all` are what the nightly job runs. Before
this, both always exited 0, so a revoked key or an outage read as a clean
night in the log. Now an unreached paper (an outage, which is not cached) or
a paper that could not be extracted makes the batch exit 1. A miss (no
open-access text) is an answer, cached, and not a failure.
"""
from __future__ import annotations

import pytest

from openferment_core import extract, intake
from openferment_core.models import ExtractResponse, FetchResult, IntakeStatus


@pytest.fixture(autouse=True)
def _scratch(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")


def result(paper_id: str, status: str = "failed:fetch") -> FetchResult:
    return FetchResult(paperId=paper_id, status=status, fetchedAt="2026-10-08T03:00:00Z", reason="r")


def test_misses_are_answers_and_exit_zero(monkeypatch):
    def fetch_all(papers, force=False):
        return [intake._persist(result("A1")), intake._persist(result("A2"))]

    monkeypatch.setattr(intake, "fetch_all", fetch_all)
    assert intake.main(["--all"]) == 0


def test_an_unreached_paper_exits_one(monkeypatch, capsys):
    def fetch_all(papers, force=False):
        return [intake._persist(result("A1")), result("A2")]  # A2: an outage, not cached

    monkeypatch.setattr(intake, "fetch_all", fetch_all)
    assert intake.main(["--all"]) == 1
    assert "1 not reached" in capsys.readouterr().out


def test_an_outage_on_a_paper_cached_before_still_counts(monkeypatch):
    intake._persist(result("A1", "complete"))

    def fetch_all(papers, force=False):
        return [result("A1")]  # --force, and the network failed this time

    monkeypatch.setattr(intake, "fetch_all", fetch_all)
    assert intake.main(["--all", "--force"]) == 1


def _one_fetched_paper(monkeypatch):
    status = IntakeStatus(paperId="B5", ingest="complete", textSource="full-text")
    monkeypatch.setattr(intake, "all_statuses", lambda: {"B5": status})


@pytest.mark.parametrize("error", [extract.ExtractUnavailable("no key"), extract.ExtractTruncated("too long")])
def test_a_paper_that_could_not_be_extracted_exits_one(monkeypatch, capsys, error):
    _one_fetched_paper(monkeypatch)

    def boom(paper_id, force=False):
        raise error

    monkeypatch.setattr(extract, "extract_paper", boom)
    assert extract.main(["--all"]) == 1
    assert "1 not extracted: B5" in capsys.readouterr().out


def test_a_clean_extraction_exits_zero(monkeypatch):
    _one_fetched_paper(monkeypatch)
    monkeypatch.setattr(
        extract, "extract_paper",
        lambda paper_id, force=False: ExtractResponse(paperId=paper_id, extractedAt="2026-10-08T03:00:00Z"),
    )
    assert extract.main(["--all"]) == 0


def test_nothing_fetched_is_a_clean_night():
    assert extract.main(["--all"]) == 0
