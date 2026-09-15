"""Intake fetch and split (OF-BLD-012 §5.1, §5.5).

Two fixtures. `structural.xml` is not a paper: a minimal JATS document that
exercises every element the parser handles, so each rule of `split_jats` is
pinned against a case a human can read in one screen. `PMC8471596.xml` is the
real B5 article as Europe PMC serves it, checked in once; its tests assert the
things §5.5 names and are skipped — with the command that fixes it — when the
file is absent.

Offline. Fixture mode is switched on for every test here so nothing can reach
the network even by accident.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from openferment_core import intake
from openferment_core.intake import (
    NetworkRefused,
    cached,
    fetch_fulltext,
    fetch_paper,
    resolve_pmcid,
    split_jats,
    status_of,
)

FIXTURES = Path(__file__).parent / "fixtures" / "jats"
STRUCTURAL = FIXTURES / "structural.xml"
REAL = FIXTURES / "PMC8471596.xml"


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    # Persist under a temp directory so a test never writes into core/data/.
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")


def _structural():
    return split_jats(STRUCTURAL.read_text(encoding="utf-8"), paper_id="X1", pmcid="structural")


# ── the structural fixture: every rule, one case each ─────────────────


def test_abstract_is_first_and_the_typed_abstract_is_ignored():
    r = _structural()
    assert r.status == "complete"
    assert r.sections[0].id == "abstract"
    assert r.sections[0].text == "The abstract comes first, whatever order the elements appear in."
    assert not any("picture of nothing" in s.text for s in r.sections)


def test_sections_are_numbered_in_document_order_with_nested_headings_prefixed():
    r = _structural()
    by_id = {s.id: s for s in r.sections}
    assert [s.id for s in r.sections if s.id.startswith("s")] == ["s1", "s2", "s3", "s4"]
    assert by_id["s1"].heading == "Introduction"
    assert by_id["s2"].heading == "Results"
    assert by_id["s3"].heading == "Results › Growth"
    # A section with no paragraphs of its own emits nothing, but its title
    # still prefixes what sits beneath it.
    assert by_id["s4"].heading == "Results › Empty › Deeper"
    assert "Empty" not in {s.heading for s in r.sections}


def test_a_parent_section_holds_only_its_own_paragraphs():
    r = _structural()
    results = next(s for s in r.sections if s.heading == "Results")
    assert results.text == "Results have a preamble of their own."
    assert "flattens" not in results.text
    assert "Placeholder A" not in results.text


def test_sup_and_sub_read_inline():
    r = _structural()
    intro = next(s for s in r.sections if s.id == "s1")
    assert "mg L-1" in intro.text
    assert "CO2" in intro.text


def test_tables_keep_their_rows():
    r = _structural()
    tables = [s for s in r.sections if s.id.startswith("t")]
    assert len(tables) == 1
    t1 = tables[0]
    assert t1.id == "t1"
    assert t1.heading == "Table 1 Placeholder rows, kept as rows."
    assert t1.text.splitlines() == [
        "Condition | Value | Unit",
        "Placeholder A | 7 | mg L-1",
        "Placeholder B | 9 | mg L-1",
    ]


def test_figure_captions_become_sections():
    r = _structural()
    figs = [s for s in r.sections if s.id.startswith("f")]
    assert [(f.id, f.heading, f.text) for f in figs] == [
        ("f1", "Figure 1", "Figure 1 A placeholder figure caption.")
    ]


def test_back_matter_is_dropped():
    r = _structural()
    everything = " ".join(s.text for s in r.sections)
    assert "Acknowledgements" not in everything
    assert "footnote" not in everything
    assert "A reference must not" not in everything


def test_the_licence_is_read():
    r = _structural()
    assert r.license is not None
    assert r.license.href == "https://creativecommons.org/licenses/by/4.0/"
    assert "placeholder licence" in (r.license.text or "")


def test_whitespace_is_collapsed_everywhere():
    r = _structural()
    for s in r.sections:
        assert "  " not in s.text and "\t" not in s.text, s.id


# ── failure is a result ────────────────────────────────────────────────


def test_malformed_xml_is_a_parse_failure_with_a_reason():
    r = split_jats("<article><body><sec>", paper_id="X1")
    assert r.status == "failed:parse"
    assert r.reason and "did not parse" in r.reason
    assert r.sections == []


def test_a_document_with_no_article_is_a_parse_failure():
    r = split_jats("<responseWrapper><error>not found</error></responseWrapper>", paper_id="X1")
    assert r.status == "failed:parse"
    assert "no <article>" in (r.reason or "")


def test_an_abstract_only_record_is_a_parse_failure_that_keeps_the_abstract():
    xml = (
        "<article><front><article-meta><abstract><p>Only this.</p></abstract>"
        "</article-meta></front></article>"
    )
    r = split_jats(xml, paper_id="X1")
    assert r.status == "failed:parse"
    assert "no <body>" in (r.reason or "")
    assert [s.id for s in r.sections] == ["abstract"]


# ── resolution and the network guard ───────────────────────────────────


def test_a_seed_pmcid_is_used_without_a_request():
    assert resolve_pmcid({"id": "B5", "pmcid": "PMC8471596", "doi": "10.x/y"}) == "PMC8471596"


def test_a_paper_with_no_identifier_resolves_to_nothing_without_a_request():
    assert resolve_pmcid({"id": "O4"}) is None


def test_fixture_mode_refuses_the_network():
    with pytest.raises(NetworkRefused):
        resolve_pmcid({"id": "H4", "doi": "10.1000/needs-a-lookup"})
    with pytest.raises(NetworkRefused):
        fetch_fulltext("PMC0000000")


# ── persistence: fetch, cache, status ──────────────────────────────────


def test_fetch_paper_persists_and_is_idempotent():
    paper = {"id": "X1", "pmcid": "structural"}
    first = fetch_paper(paper)
    assert first.status == "complete"
    path = intake.FULLTEXT_DIR / "X1.json"
    assert path.exists()
    stored = json.loads(path.read_text())
    assert stored["paperId"] == "X1" and stored["pmcid"] == "structural"
    assert stored["license"]["href"].startswith("https://creativecommons.org/")

    again = fetch_paper(paper)
    assert again.fetchedAt == first.fetchedAt, "a cached result is returned, not re-fetched"
    assert cached("X1") is not None


def test_a_miss_is_cached_as_a_miss():
    # No fixture for this PMCID, so the fetch fails — and the failure is
    # persisted, which is what stops the batch asking again next run.
    r = fetch_paper({"id": "X2", "pmcid": "PMC0000000"})
    assert r.status == "failed:fetch"
    assert r.reason and "no fixture" in r.reason
    assert cached("X2") is not None
    assert cached("X2").status == "failed:fetch"


def test_status_summarises_a_fetch():
    fetch_paper({"id": "X1", "pmcid": "structural"})
    s = status_of("X1")
    assert s is not None
    assert s.ingest == "complete" and s.textSource == "full-text"
    assert s.sections == 7  # abstract, s1–s4, t1, f1
    assert s.tables == 1
    assert s.license and "creativecommons" in s.license
    assert status_of("nope") is None


# ── the real article, when it is here ──────────────────────────────────

needs_real = pytest.mark.skipif(
    not REAL.exists(),
    reason=(
        f"{REAL.name} is not checked in. Fetch it once with: curl -sS "
        "'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8471596/fullTextXML' "
        f"-o {REAL}"
    ),
)


@needs_real
def test_b5_splits_into_many_sections_with_tables_and_a_licence():
    r = split_jats(REAL.read_text(encoding="utf-8"), paper_id="B5", pmcid="PMC8471596")
    assert r.status == "complete", r.reason
    assert r.sections[0].id == "abstract"
    assert len(r.sections) >= 10
    assert any(s.id.startswith("t") for s in r.sections), "B5 has tables; none survived"
    assert r.license is not None
    assert "creativecommons" in ((r.license.href or "") + (r.license.text or "")).lower()


# ── what JATS nests, and what a superscript means ──────────────────────

NESTED = """<?xml version="1.0" encoding="UTF-8"?>
<article xmlns:xlink="http://www.w3.org/1999/xlink">
  <front><article-meta><title-group><article-title>Nested</article-title></title-group></article-meta></front>
  <body>
    <sec><title>Results</title>
      <p>Cultures reached 2 × 10<sup>6</sup> cells mL<sup>-1</sup> and CO<sub>2</sub> rose.
        <table-wrap id="t1"><label>Table 1</label><caption><p>Rows.</p></caption>
          <table><tr><th>Condition</th><th>Value</th></tr><tr><td>A</td><td>7</td></tr></table>
        </table-wrap>
        After the table, 10<sup>-3</sup> M.</p>
    </sec>
  </body>
</article>
"""


def test_a_table_nested_in_a_paragraph_stays_out_of_the_prose():
    r = split_jats(NESTED, paper_id="X1")
    assert r.status == "complete", r.reason
    by_id = {s.id: s for s in r.sections}
    assert "Condition" not in by_id["s1"].text and "| 7" not in by_id["s1"].text
    assert by_id["t1"].text.splitlines() == ["Condition | Value", "A | 7"]
    assert by_id["s1"].text.startswith("Cultures reached") and by_id["s1"].text.endswith("M.")


def test_a_superscript_on_a_number_reads_as_a_power_of_ten():
    r = split_jats(NESTED, paper_id="X1")
    s1 = next(s for s in r.sections if s.id == "s1").text
    assert "2 × 10^6 cells mL-1" in s1, s1
    assert "CO2 rose" in s1
    assert "10^-3 M" in s1
