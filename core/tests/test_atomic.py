"""Files the service keeps land whole, and decisions do not erase each other
(OF-BLD-012 §B.8).

`atomic.write_text` replaces a file in one rename, so a failure part-way
leaves the old file as it was. `biorepo.write` holds one lock across its
read-modify-write, so two decisions posted at once both survive: the test
slows `read` down to make the two writes overlap, which they would on a
thread pool given enough reviewers or tabs.
"""
from __future__ import annotations

import os
import threading
import time

import pytest

from openferment_core import atomic, biorepo, extract, intake
from openferment_core.corpus import load_corpus
from openferment_core.models import ReviewDecision


def test_replaces_the_whole_file(tmp_path):
    path = tmp_path / "f.json"
    atomic.write_text(path, "old\n")
    atomic.write_text(path, "new\n")
    assert path.read_text(encoding="utf-8") == "new\n"


def test_creates_the_folder(tmp_path):
    path = tmp_path / "a" / "b" / "f.json"
    atomic.write_text(path, "x")
    assert path.read_text(encoding="utf-8") == "x"


def test_a_failed_write_leaves_the_old_file_and_nothing_beside_it(tmp_path, monkeypatch):
    path = tmp_path / "biorepo.json"
    atomic.write_text(path, '{"decisions": "the old ones"}\n')

    def boom(*_):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        atomic.write_text(path, '{"decisions": "half of the new')
    assert path.read_text(encoding="utf-8") == '{"decisions": "the old ones"}\n'
    assert [p.name for p in tmp_path.iterdir()] == ["biorepo.json"]


def test_keeps_the_permissions_of_the_file_it_replaces(tmp_path):
    path = tmp_path / "f.json"
    path.write_text("old", encoding="utf-8")
    os.chmod(path, 0o640)
    atomic.write_text(path, "new")
    assert path.stat().st_mode & 0o777 == 0o640


def test_a_new_file_is_readable_by_others(tmp_path):
    path = tmp_path / "f.json"
    atomic.write_text(path, "new")
    assert path.stat().st_mode & 0o777 == 0o644


@pytest.fixture
def scratch_repo(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(biorepo, "PATH", tmp_path / "biorepo.json")


def _identified_seed_records(n: int) -> list[str]:
    corpus = load_corpus()
    out = []
    for r in corpus.records:
        p = corpus.paper(r["paperId"]) or {}
        if p.get("pmcid") or p.get("doi") or p.get("pmid"):
            out.append(r["id"])
        if len(out) == n:
            return out
    pytest.skip(f"fewer than {n} seed records on identified papers")


def test_decisions_posted_together_all_survive(scratch_repo, monkeypatch):
    ids = _identified_seed_records(6)
    real_read = biorepo.read

    def slow_read():
        repo = real_read()
        time.sleep(0.05)  # long enough for every thread to read before any writes
        return repo

    monkeypatch.setattr(biorepo, "read", slow_read)

    def decide(record_id: str) -> None:
        biorepo.write(ReviewDecision(
            status="rejected", provenance="curated", reviewer="sean",
            recordId=record_id, at="2026-10-07T12:00:00Z",
        ))

    threads = [threading.Thread(target=decide, args=(rid,)) for rid in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(real_read().decisions) == sorted(ids)
