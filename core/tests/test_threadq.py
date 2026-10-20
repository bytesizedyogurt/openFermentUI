"""Thread Q, proposed by a rule and written on a person's approval, with the
sources outside Europe PMC a person named in its include file.

Offline. OSTI's records API and SGD's strain backend are stood in for by
`intake._get` answering from what this file holds: an OSTI record cut down
from the real one, and `fixtures/sgd/S000203483.json`. Thread P's own tests
are in test_threadp.py and run unchanged.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from openferment_core import intake, threadp
from openferment_core.threadp import THREAD_P, THREAD_Q

ROOT = Path(__file__).resolve().parents[2]
SGD_ENTRY = Path(__file__).parent / "fixtures" / "sgd" / "S000203483.json"
OSTI_URL = "https://www.osti.gov/servlets/purl/1013269"
SGD_URL = "https://www.yeastgenome.org/backend/strain/S000203483"

# What OSTI's records API answered for 1013269 on 2026-10-20, cut to the
# fields lookup reads and two of the twelve authors, with a third written as
# OSTI writes the authors of 1129271: an affiliation, and here an ORCID, after
# the name.
OSTI_RECORD = [{
    "osti_id": "1013269",
    "title": "Process Design and Economics for Biochemical Conversion of Lignocellulosic Biomass to Ethanol: "
             "Dilute-Acid Pretreatment and Enzymatic Hydrolysis of Corn Stover",
    "authors": [
        "Humbird, D", "Davis, R",
        "Tao, Ling [National Renewable Energy Laboratory (NREL), Golden, CO (United States)] (ORCID:0000000000000000)",
    ],
    "publication_date": "2011-03-01T00:00:00Z",
    "report_number": "NREL/TP-5100-47764",
    "doi": "10.2172/1013269",
    "product_type": "Technical Report",
    "links": [
        {"rel": "citation", "href": "https://www.osti.gov/biblio/1013269"},
        {"rel": "fulltext", "href": "https://www.osti.gov/servlets/purl/1013269"},
    ],
}]


@pytest.fixture
def sources(monkeypatch):
    """`intake._get` answering as OSTI and SGD do, and recording what it was asked."""
    asked: list[tuple[str, dict]] = []

    def get(url, params=None, **kw):
        asked.append((url, kw))
        request = httpx.Request("GET", url)
        if url == f"{threadp.OSTI_API}/1013269":
            return httpx.Response(200, json=OSTI_RECORD, request=request)
        if url == SGD_URL:
            return httpx.Response(200, text=SGD_ENTRY.read_text(encoding="utf-8"), request=request)
        return httpx.Response(404, request=request)

    monkeypatch.setattr(intake, "_get", get)
    return asked


def named_rows():
    return [threadp.lookup("osti:1013269", THREAD_Q), threadp.lookup("sgd:S000203483", THREAD_Q)]


# ── the rule ───────────────────────────────────────────────────────────


def test_the_rule_is_the_one_sean_set():
    assert THREAD_Q.query == (
        'TITLE_ABS:("Saccharomyces cerevisiae" OR "S. cerevisiae" OR yeast) AND '
        'TITLE_ABS:(ethanol OR bioethanol OR "alcoholic fermentation") AND '
        'TITLE_ABS:(Monod OR Luedeking OR "kinetic model" OR "kinetic models" OR "kinetic modeling" OR '
        '"kinetic modelling" OR "kinetic parameters" OR "unstructured model" OR "ethanol inhibition" OR '
        '"product inhibition" OR "substrate inhibition" OR "maximum specific growth rate" OR '
        '"growth kinetics" OR "fermentation kinetics") AND TITLE_ABS:(glucose OR batch) AND '
        "OPEN_ACCESS:y AND HAS_FT:y"
    )
    assert (THREAD_Q.min_year, THREAD_Q.propose_research, THREAD_Q.propose_reviews) == (2005, 20, 3)
    assert THREAD_Q.letter == "Q" and THREAD_Q.named_sources and not THREAD_P.named_sources
    hit = {"pmcid": "PMC1", "isOpenAccess": "Y", "pubYear": "2005", "license": "cc by"}
    assert threadp.eligible(hit, THREAD_Q) and not threadp.eligible(dict(hit, pubYear="2004"), THREAD_Q)
    assert not threadp.eligible(hit, THREAD_P), "thread P's year still holds for thread P"
    assert not threadp.eligible(dict(hit, license="other"), THREAD_Q)


def test_the_include_file_names_the_four_sources_sean_named_then_the_papers_he_approved():
    ids = threadp.read_includes(rule=THREAD_Q)
    assert ids[:4] == ["osti:1013269", "osti:1129271", "sgd:S000203483", "sgd:S000203459"]
    # The papers Sean Creighton approved on 2026-10-20: PMCIDs, each once.
    papers = ids[4:]
    assert len(papers) == 18 and len(set(papers)) == 18
    assert all(p.startswith("PMC") and p[3:].isdigit() for p in papers)


def test_the_committed_seed_file_reads_as_apply_wrote_it():
    assert threadp.render(threadp.read_seed(rule=THREAD_Q), rule=THREAD_Q) == THREAD_Q.seed_file.read_text(encoding="utf-8")


def test_the_committed_seed_file_holds_only_what_apply_writes():
    assert threadp.seed_problems(threadp.read_seed(rule=THREAD_Q), THREAD_Q) == []


# ── lookup at the source ───────────────────────────────────────────────


def test_a_report_is_looked_up_on_osti(sources):
    row = threadp.lookup("osti:1013269", THREAD_Q)
    assert isinstance(row, threadp.Row) and row.verdict == "INCLUDE"
    assert row.doi == "10.2172/1013269" and row.year == 2011 and row.journal == "NREL/TP-5100-47764"
    assert row.authors == ["Humbird, D", "Davis, R", "Tao, Ling"] and row.firstAuthor == "Humbird, D"
    assert row.title.startswith("Process Design and Economics") and row.openAccess
    assert row.sourceUrl == OSTI_URL and row.pmcid == "" and row.pmid == ""
    assert sources[-1][1]["headers"] == {"Accept": "application/json"}


def test_a_strain_entry_is_looked_up_on_sgd(sources):
    row = threadp.lookup("sgd:S000203483", THREAD_Q)
    assert row.title == "Saccharomyces Genome Database strain entry: S288C"
    assert row.journal == "Saccharomyces Genome Database" and row.sourceUrl == SGD_URL
    assert (row.pmcid, row.doi, row.pmid, row.authors, row.year) == ("", "", "", [], None)


def test_a_named_source_with_no_record_stops_the_run(sources):
    with pytest.raises(threadp.LookupFailed, match="404"):
        threadp.lookup("osti:999", THREAD_Q)
    asked = len(sources)
    for bad in ("osti:12a", "sgd:S1", "sgd:YAL001C"):
        with pytest.raises(threadp.LookupFailed):
            threadp.lookup(bad, THREAD_Q)
    assert len(sources) == asked, "a malformed id is refused without a request"
    with pytest.raises(threadp.LookupFailed, match="thread P"):
        threadp.lookup("osti:1013269", THREAD_P)


# ── apply ──────────────────────────────────────────────────────────────


def test_apply_writes_a_named_source_with_its_address(tmp_path, sources):
    seed = tmp_path / "threadQ.ts"
    rows = threadp.propose([], named_rows(), rule=THREAD_Q)
    # The address survives the proposal file a person edits.
    again = threadp.from_tsv(threadp.to_tsv(rows))
    assert [threadp.as_dict(r) for r in again] == [threadp.as_dict(r) for r in rows]
    added = threadp.apply(again, "Sean Creighton", seed=seed, on="2026-10-20", rule=THREAD_Q)
    assert len(added) == 2
    entries = threadp.read_seed(seed, THREAD_Q)
    report, strain = (e.paper for e in entries)
    assert (report["id"], strain["id"]) == ("Q1", "Q2")
    assert report["sourceType"] == "industry-report" and report["venue"] == "NREL/TP-5100-47764"
    assert report["doi"] == "10.2172/1013269" and report["sourceUrl"] == OSTI_URL and report["year"] == 2011
    assert report["thread"] == "Q" and report["openAccess"] is True and "pmcid" not in report
    assert report["abstract"].startswith("Catalogued on 2026-10-20 by the thread Q selection rule")
    assert strain["sourceType"] == "database-entry" and strain["venue"] == "Saccharomyces Genome Database"
    assert strain["sourceUrl"] == SGD_URL and not ({"doi", "pmcid", "pmid"} & set(strain))
    assert strain["authors"] == [] and strain["verifyNeeded"] is True
    assert all(p["organisms"] == [] and p["topics"] == [] and "license" not in p for p in (report, strain))
    assert threadp.seed_problems(entries, THREAD_Q) == []
    assert threadp.render(entries, rule=THREAD_Q) == seed.read_text(encoding="utf-8")
    assert "export const THREAD_Q_PAPERS: Paper[] = [" in seed.read_text(encoding="utf-8")


def test_a_second_apply_keeps_every_id_by_address(tmp_path, sources):
    seed = tmp_path / "threadQ.ts"
    threadp.apply(threadp.propose([], named_rows()[1:], rule=THREAD_Q), "Sean Creighton", seed=seed,
                  on="2026-10-20", rule=THREAD_Q)
    seeded = threadp.seeded_ids(threadp.read_seed(seed, THREAD_Q))
    rows = threadp.propose([], named_rows(), seeded, THREAD_Q)
    assert [r.id for r in rows] == ["", "Q1"]
    threadp.apply(rows, "Sean Creighton", seed=seed, on="2026-10-21", rule=THREAD_Q)
    papers = {e.paper["id"]: e.paper.get("sourceUrl") for e in threadp.read_seed(seed, THREAD_Q)}
    assert papers == {"Q1": SGD_URL, "Q2": OSTI_URL}


@pytest.mark.parametrize("name", ["", " ", "x", "you", "Reviewer", "test", "Sean\nX = 1;"])
def test_apply_refuses_a_name_biorepo_would_refuse(tmp_path, sources, name):
    with pytest.raises(threadp.ThreadRefused):
        threadp.apply(threadp.propose([], named_rows(), rule=THREAD_Q), name, seed=tmp_path / "t.ts", rule=THREAD_Q)
    assert not (tmp_path / "t.ts").exists()


def test_apply_refuses_an_address_it_does_not_write(tmp_path):
    elsewhere = threadp.Row(verdict="INCLUDE", title="Elsewhere", sourceUrl="https://example.org/report.pdf")
    with pytest.raises(threadp.ThreadRefused, match="Intake reads no other source"):
        threadp.apply([elsewhere], "Sean Creighton", seed=tmp_path / "q.ts", rule=THREAD_Q)
    nothing = threadp.Row(verdict="INCLUDE", title="Nothing")
    with pytest.raises(threadp.ThreadRefused, match="source address"):
        threadp.apply([nothing], "Sean Creighton", seed=tmp_path / "q.ts", rule=THREAD_Q)
    assert not (tmp_path / "q.ts").exists()


def test_thread_p_takes_no_address_and_keeps_its_rule(tmp_path):
    with_url = threadp.Row(verdict="INCLUDE", doi="10.2172/1013269", title="A report", sourceUrl=OSTI_URL)
    with pytest.raises(threadp.ThreadRefused, match="by PMCID, DOI or PMID"):
        threadp.apply([with_url], "Sean Creighton", seed=tmp_path / "p.ts")
    bare = threadp.Row(verdict="INCLUDE", title="Bare")
    with pytest.raises(threadp.ThreadRefused, match="names no PMCID, DOI or PMID$"):
        threadp.apply([bare], "Sean Creighton", seed=tmp_path / "p.ts")
    # A proposal file written before the column existed still reads.
    old = "verdict\tid\tpmcid\tdoi\nAPPROVED\t\tPMC1\t10.0000/x\n"
    assert threadp.from_tsv(old)[0].sourceUrl == ""
    # And thread P's seed is still thread P's, read as P.
    assert threadp.seed_problems(threadp.read_seed()) == []
    assert threadp.read_seed(THREAD_Q.seed_file, THREAD_P) == []


def test_a_hand_edited_entry_is_named(tmp_path, sources):
    seed = tmp_path / "t.ts"
    threadp.apply(threadp.propose([], named_rows(), rule=THREAD_Q), "Sean Creighton", seed=seed,
                  on="2026-10-20", rule=THREAD_Q)
    text = seed.read_text(encoding="utf-8")
    for before, after in [
        ('"sourceType": "industry-report"', '"sourceType": "journal-article"'),
        ('"sourceType": "database-entry"', '"sourceType": "industry-report"'),
        (f'"sourceUrl": "{OSTI_URL}"', '"sourceUrl": "https://example.org/report.pdf"'),
        ('"thread": "Q"', '"thread": "P"'),
        ('"organisms": []', '"organisms": ["s-cerevisiae"]'),
        ('No curator has read this entry.', 'A curator read this entry.'),
    ]:
        assert before in text, before
        seed.write_text(text.replace(before, after, 1), encoding="utf-8")
        assert threadp.seed_problems(threadp.read_seed(seed, THREAD_Q), THREAD_Q), after
    with pytest.raises(threadp.ThreadRefused):
        threadp.apply(threadp.propose([], named_rows(), rule=THREAD_Q), "Sean Creighton", seed=seed, rule=THREAD_Q)


TSC = ROOT / "node_modules" / ".bin" / "tsc"


@pytest.mark.skipif(not TSC.exists() or shutil.which("node") is None, reason="needs node_modules")
def test_the_written_file_compiles(tmp_path, sources):
    seed = tmp_path / "threadQ.ts"
    threadp.apply(threadp.propose([], named_rows(), rule=THREAD_Q), "Sean Creighton", seed=seed,
                  types_import=str(ROOT / "src" / "data" / "types"), rule=THREAD_Q)
    out = subprocess.run(
        [str(TSC), "--noEmit", "--strict", "--skipLibCheck", "--target", "es2020",
         "--module", "esnext", "--moduleResolution", "bundler", str(seed)],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stdout + out.stderr


def test_the_script_takes_the_thread():
    script = ROOT / "scripts" / "thread-p.py"
    out = subprocess.run(
        [sys.executable, str(script), "--thread", "R"], capture_output=True, text=True, timeout=60,
        cwd=ROOT / "core",
    )
    assert out.returncode != 0 and "invalid choice" in out.stderr
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["scripts"]
    assert package["thread:propose:q"].endswith("thread-p.py --thread Q")
    assert package["thread:apply:q"].endswith("thread-p.py --thread Q --apply")
