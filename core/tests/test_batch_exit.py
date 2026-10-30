"""A failed night exits non-zero (OF-BLD-012 §B.8).

`extract --all` is what the nightly job runs, over every document the
project holds (ADR-002). Before this, it always exited 0, so a revoked key or
an outage read as a clean night in the log. Now a document that could not be
extracted makes the batch exit 1.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from openferment_core import extract
from openferment_core.models import ExtractResponse


def _one_held_document(monkeypatch):
    monkeypatch.setattr(extract.kit, "documents", lambda project_id: [(SimpleNamespace(id="B5"), {})])


@pytest.mark.parametrize("error", [extract.ExtractUnavailable("no key"), extract.ExtractTruncated("too long")])
def test_a_document_that_could_not_be_extracted_exits_one(monkeypatch, capsys, error):
    _one_held_document(monkeypatch)

    def boom(paper_id, force=False):
        raise error

    monkeypatch.setattr(extract, "extract_paper", boom)
    assert extract.main(["--all"]) == 1
    assert "1 not extracted: B5" in capsys.readouterr().out


def test_a_clean_extraction_exits_zero(monkeypatch):
    _one_held_document(monkeypatch)
    monkeypatch.setattr(
        extract, "extract_paper",
        lambda paper_id, force=False: ExtractResponse(paperId=paper_id, extractedAt="2026-10-08T03:00:00Z"),
    )
    assert extract.main(["--all"]) == 0


def test_a_project_holding_nothing_is_a_clean_night():
    assert extract.main(["--all"]) == 0
