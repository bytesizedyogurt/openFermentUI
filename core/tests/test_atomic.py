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

from openferment_core import atomic, biorepo, db, extract, projects
from openferment_core.literature import kit
from openferment_core.models import Candidate, ExtractResponse, Quantity, ReviewDecision, Usage
from openferment_core.units import to_si


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


def _planted(n: int) -> list[str]:
    """n candidates on one document the project holds, each one a decision
    may name."""
    paper = "A1"
    db.run(kit._link(projects.current(), paper, {}, "test"))
    candidates = []
    for i in range(n):
        sv, su = to_si(i + 1, "g L⁻¹")
        candidates.append(Candidate(id=f"cl1-{paper}-{i:08x}", paperId=paper, sectionId="s1", quote=f"a titre, row {i}",
                                    field="titer_secreted", value=i + 1, unit="g L⁻¹", si=Quantity(value=sv, unit=su)))
    extract._persist(ExtractResponse(paperId=paper, extractedAt="2026-10-07T12:00:00Z", candidates=candidates,
                                     audit=[], usage=Usage(), calls=0))
    return [c.id for c in candidates]


def test_decisions_posted_together_all_survive(scratch_repo, monkeypatch):
    ids = _planted(6)
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


def test_uses_the_full_flush_where_the_platform_has_one(tmp_path, monkeypatch):
    """macOS's fsync stops at the drive's cache; F_FULLFSYNC goes through it."""
    import fcntl

    calls = []
    monkeypatch.setattr(fcntl, "F_FULLFSYNC", 51, raising=False)  # macOS's value
    monkeypatch.setattr(fcntl, "fcntl", lambda fd, op, *a: calls.append(op))
    monkeypatch.setattr(os, "fsync", lambda fd: calls.append("fsync"))
    atomic.write_text(tmp_path / "f.json", "x")
    assert calls == [51, 51], "the file, then its folder, both through F_FULLFSYNC"


def test_falls_back_to_fsync_where_the_full_flush_is_refused(tmp_path, monkeypatch):
    import fcntl

    calls = []

    def refuse(fd, op, *a):
        raise OSError("not supported here")

    monkeypatch.setattr(fcntl, "F_FULLFSYNC", 51, raising=False)
    monkeypatch.setattr(fcntl, "fcntl", refuse)
    monkeypatch.setattr(os, "fsync", lambda fd: calls.append("fsync"))
    atomic.write_text(tmp_path / "f.json", "x")
    assert calls.count("fsync") == 2 and (tmp_path / "f.json").read_text(encoding="utf-8") == "x"
