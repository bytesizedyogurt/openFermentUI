"""Thread P, proposed by a rule and written on a person's approval
(OF-BLD-014 §2.3).

Offline. The search response is `fixtures/europepmc/search-pha.json`, a
structural stand-in with invented papers; the one test that asks Europe PMC
is marked live.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from openferment_core import threadp

FIXTURE = Path(__file__).parent / "fixtures" / "europepmc" / "search-pha.json"
ROOT = Path(__file__).resolve().parents[2]


def results() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["resultList"]["result"]


def by_doi(rows):
    return {r.doi: r for r in rows}


# ── propose ────────────────────────────────────────────────────────────


def test_the_fixture_says_what_it_is():
    assert "STAND-IN" in json.loads(FIXTURE.read_text(encoding="utf-8"))["_fixture"]


def test_the_filters_drop_what_the_rule_excludes():
    rows = by_doi(threadp.propose(results()))
    # 43 published before MIN_YEAR, 44 no licence, 45 a licence that is not cc,
    # 46 not open access, 47 no PMCID.
    for n in (43, 44, 45, 46, 47):
        assert f"10.0000/stand-in.{n}" not in rows
    assert len(rows) == 43


def test_the_most_cited_thirty_research_articles_and_five_reviews_are_proposed():
    rows = threadp.propose(results())
    proposed = [r for r in rows if r.verdict == "PROPOSE"]
    assert sum(1 for r in proposed if r.publicationType != "review") == 30
    assert sum(1 for r in proposed if r.publicationType == "review") == 5
    d = by_doi(rows)
    # 48 has the most citations and comes first; 30 to 34 fall outside the thirty.
    assert rows[0].doi == "10.0000/stand-in.48" and rows[0].verdict == "PROPOSE"
    assert d["10.0000/stand-in.29"].verdict == "PROPOSE"
    assert all(d[f"10.0000/stand-in.{n}"].verdict == "REVIEW" for n in range(30, 35))
    assert all(d[f"10.0000/stand-in.{n}"].verdict == "PROPOSE" for n in range(35, 40))
    assert d["10.0000/stand-in.40"].verdict == "REVIEW"
    # An editorial is neither a research article nor a review.
    assert d["10.0000/stand-in.42"].verdict == "REVIEW"


def test_a_row_holds_what_europe_pmc_returned_as_words():
    row = by_doi(threadp.propose(results()))["10.0000/stand-in.1"]
    assert row.title == "Stand-in research article 1"  # tags and the closing stop removed
    assert row.authors == ["Author1 A", "Second B"] and row.firstAuthor == "Author1 A"
    assert row.journal == "Journal of Stand-ins" and row.year == 2018 and row.licence == "cc by"


def test_a_result_missing_a_named_field_stops_the_run():
    broken = [dict(results()[0])]
    del broken[0]["citedByCount"]
    with pytest.raises(threadp.MissingKeys, match="citedByCount"):
        threadp.propose(broken)


def test_an_include_is_included_whatever_the_rule_says():
    old = next(r for r in results() if r["doi"].endswith(".43"))  # before MIN_YEAR
    rows = threadp.propose(results(), [old, "10.0000/no-open-text"])
    d = by_doi(rows)
    assert d["10.0000/stand-in.43"].verdict == "INCLUDE"
    assert d["10.0000/no-open-text"].verdict == "INCLUDE" and d["10.0000/no-open-text"].pmcid == ""


def test_the_proposal_survives_its_own_file():
    rows = threadp.propose(results())
    again = threadp.from_tsv(threadp.to_tsv(rows))
    assert [threadp.as_dict(r) for r in again] == [threadp.as_dict(r) for r in rows]


def test_the_include_file_ignores_comments(tmp_path):
    f = tmp_path / "inc.txt"
    f.write_text("# a comment\nPMC123  # trailing\n\n10.1/x\n", encoding="utf-8")
    assert threadp.read_includes(f) == ["PMC123", "10.1/x"]


# ── apply ──────────────────────────────────────────────────────────────


def approve(rows, *dois):
    for r in rows:
        if r.doi in dois:
            r.verdict = "APPROVED"
    return rows


def test_apply_writes_approved_and_included_rows_and_nothing_proposed(tmp_path):
    seed = tmp_path / "threadP.ts"
    rows = approve(threadp.propose(results(), ["10.0000/no-open-text"]), "10.0000/stand-in.2", "10.0000/stand-in.1")
    added = threadp.apply(rows, "Sean Creighton", seed=seed, on="2026-10-15")
    assert len(added) == 3
    entries = threadp.read_seed(seed)
    assert [e.paper["id"] for e in entries] == ["P1", "P2", "P3"]
    # File order: the include first, then the approved rows as the file lists them.
    assert entries[0].paper.get("doi") == "10.0000/no-open-text" and entries[0].paper["openAccess"] is False
    assert entries[0].verdict == "INCLUDE" and entries[1].verdict == "APPROVED"
    assert all(e.approvedBy == "Sean Creighton" and e.approvedOn == "2026-10-15" for e in entries)
    p = entries[1].paper
    assert p["thread"] == "P" and p["organisms"] == [] and p["topics"] == [] and p["ingest"] == "catalogued"
    assert p["textSource"] == "curation-note" and "license" not in p
    assert p["abstract"].startswith("Catalogued on 2026-10-15 by the thread P selection rule")
    assert p["sections"][0]["text"] == p["abstract"]


def test_a_second_apply_keeps_every_id(tmp_path):
    seed = tmp_path / "threadP.ts"
    threadp.apply(approve(threadp.propose(results()), "10.0000/stand-in.5", "10.0000/stand-in.9"),
                  "Sean Creighton", seed=seed, on="2026-10-15")
    first = {e.paper["doi"]: e.paper["id"] for e in threadp.read_seed(seed)}
    seeded = threadp.seeded_ids(threadp.read_seed(seed))
    rows = threadp.propose(results(), seeded=seeded)
    assert by_doi(rows)["10.0000/stand-in.9"].id == first["10.0000/stand-in.9"]
    threadp.apply(approve(rows, "10.0000/stand-in.3", "10.0000/stand-in.9"), "Sean Creighton", seed=seed, on="2026-10-16")
    after = {e.paper["doi"]: e.paper["id"] for e in threadp.read_seed(seed)}
    assert {k: after[k] for k in first} == first
    assert after["10.0000/stand-in.3"] == "P3"


@pytest.mark.parametrize("name", ["", " ", "x", "you", "Reviewer", "test"])
def test_apply_refuses_a_name_biorepo_would_refuse(tmp_path, name):
    rows = approve(threadp.propose(results()), "10.0000/stand-in.1")
    with pytest.raises(threadp.ThreadPRefused):
        threadp.apply(rows, name, seed=tmp_path / "t.ts")
    assert not (tmp_path / "t.ts").exists()


def test_apply_refuses_an_approved_row_with_no_pmcid(tmp_path):
    row = threadp.Row(verdict="APPROVED", doi="10.0000/closed", title="A closed paper")
    with pytest.raises(threadp.ThreadPRefused, match="no PMCID"):
        threadp.apply([row], "Sean Creighton", seed=tmp_path / "t.ts")


def test_proposed_and_review_rows_are_never_written(tmp_path):
    seed = tmp_path / "t.ts"
    assert threadp.apply(threadp.propose(results()), "Sean Creighton", seed=seed) == []
    assert threadp.read_seed(seed) == []


TSC = ROOT / "node_modules" / ".bin" / "tsc"


@pytest.mark.skipif(not TSC.exists() or shutil.which("node") is None, reason="needs node_modules")
def test_the_written_file_compiles(tmp_path):
    seed = tmp_path / "threadP.ts"
    rows = approve(threadp.propose(results(), ["10.0000/no-open-text"]), "10.0000/stand-in.36", "10.0000/stand-in.1")
    threadp.apply(rows, "Sean Creighton", seed=seed, types_import=str(ROOT / "src" / "data" / "types"))
    out = subprocess.run(
        [str(TSC), "--noEmit", "--strict", "--skipLibCheck", "--target", "es2020",
         "--module", "esnext", "--moduleResolution", "bundler", str(seed)],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stdout + out.stderr


def test_the_committed_seed_file_reads_as_apply_wrote_it():
    """Re-rendering what threadP.ts holds reproduces it byte for byte, so a
    hand edit to the paper list, or a record typed into it, fails here."""
    assert threadp.render(threadp.read_seed()) == threadp.SEED_FILE.read_text(encoding="utf-8")


@pytest.mark.live
def test_europe_pmc_returns_the_fields_the_rule_reads():
    found = threadp.search()
    assert found
    threadp.check_keys(found[0])
