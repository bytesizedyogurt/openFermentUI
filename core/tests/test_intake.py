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
        After the table, 10<sup>-3</sup> M. The 2<sup>nd</sup> run<sup>a</sup> and Fig. 3<sup>†</sup> agree.</p>
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
    assert by_id["s1"].text.startswith("Cultures reached") and by_id["s1"].text.endswith("agree.")


def test_a_superscript_on_a_number_reads_as_a_power_of_ten():
    r = split_jats(NESTED, paper_id="X1")
    s1 = next(s for s in r.sections if s.id == "s1").text
    assert "2 × 10^6 cells mL-1" in s1, s1
    assert "CO2 rose" in s1
    assert "10^-3 M" in s1


def test_a_superscript_that_is_not_a_number_is_not_a_power():
    # An ordinal, a footnote letter or a dagger after a digit is read inline,
    # not as an exponent: '2nd', '3†' — a caret would invent a power of ten
    # the paper never wrote, and normalize_text would then fold it as one.
    r = split_jats(NESTED, paper_id="X1")
    s1 = next(s for s in r.sections if s.id == "s1").text
    assert "The 2nd runa and Fig. 3† agree." in s1, s1
    assert "2^nd" not in s1 and "3^†" not in s1


def test_a_linked_citation_is_dropped_and_an_unlinked_superscript_on_a_number_is_a_power():
    # Europe PMC links every citation: of the first 31 real fetches
    # (OF-BLD-014 §1.5) all 163 superscript citations hold an <xref
    # ref-type="bibr">. So a linked mark goes wherever it sits, after a word
    # or after a number, and an unlinked numeric superscript on a number is a
    # power: C6 wrote 2<sup>4</sup>–2<sup>6</sup>, which the earlier rule read
    # as '2–2'. A run of unlinked numbers is still citations.
    xml = NESTED.replace(
        "After the table, 10<sup>-3</sup> M.",
        'Titres reached 4.2<sup><xref ref-type="bibr" rid="B12">12</xref></sup> g/L, as growth'
        '<sup><xref ref-type="bibr" rid="B3">3</xref></sup> and yield<xref ref-type="bibr" rid="B4"><sup>4</sup></xref> '
        "did previously<sup>13,14</sup>; half were 16–64 (i.e. 2<sup>4</sup>–2<sup>6</sup>) times higher. "
        "After the table, 10<sup>-3</sup> M.",
    )
    s1 = next(s for s in split_jats(xml, paper_id="X1").sections if s.id == "s1").text
    assert "Titres reached 4.2 g/L, as growth and yield did previously;" in s1, s1
    assert "16–64 (i.e. 2^4–2^6) times higher" in s1, s1
    assert "2 × 10^6 cells mL-1" in s1 and "10^-3 M" in s1, "a superscript on a ten is still a power"


# ── what the first real fetch taught (OF-BLD-014 §1.5, docs/build/JATS-AUDIT.md) ──


def _doc(body: str, *, front: str = "", after_body: str = "") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML"
         xmlns:ali="http://www.niso.org/schemas/ali/1.0/">
  <front><article-meta><title-group><article-title>Case</article-title></title-group>{front}</article-meta></front>
  <body>{body}</body>{after_body}
</article>"""


def _sections(xml: str) -> dict[str, str]:
    r = split_jats(xml, paper_id="X1")
    assert r.status == "complete", r.reason
    return {s.id: s.text for s in r.sections}


def _table(rows: str, foot: str = "", caption: str = "<label>Table 1</label><caption><p>Cells.</p></caption>") -> str:
    return _doc(f"<sec><title>Results</title><p>See Table 1.</p>"
                f"<table-wrap id='tw1'>{caption}<table>{rows}</table>{foot}</table-wrap></sec>")


def test_an_empty_cell_keeps_its_column():
    # C2, H1, N4, O3, O5: an empty stub corner moved every header one column left.
    t1 = _sections(_table("<tr><th/><th>UVM4</th><th>cw15</th></tr>"
                          "<tr><td>titre</td><td>30.9</td><td>12</td></tr>"
                          "<tr><td>yield</td><td/><td>4</td></tr>"))["t1"].splitlines()
    assert t1 == [" | UVM4 | cw15", "titre | 30.9 | 12", "yield |  | 4"], t1


def test_a_cell_that_spans_rows_is_repeated_in_each():
    # F4: 'Fat' spanned thirteen rows and named the first alone.
    t1 = _sections(_table("<tr><td rowspan='2'>Fat</td><td>AA</td><td>1.2</td></tr>"
                          "<tr><td>AB</td><td>1.4</td></tr>"))["t1"].splitlines()
    assert t1 == ["Fat | AA | 1.2", "Fat | AB | 1.4"], t1


def test_a_header_that_spans_columns_stands_over_each():
    # L7, N3, O3: two-row headers sat over the wrong columns.
    t1 = _sections(_table("<tr><th rowspan='2'>Strain</th><th colspan='2'>Titre</th></tr>"
                          "<tr><th>day 3</th><th>day 7</th></tr>"
                          "<tr><td>cw15</td><td>4</td><td>9</td></tr>"
                          "<tr><td colspan='3'>Grown at 25 °C</td></tr>"))["t1"].splitlines()
    assert t1 == ["Strain | Titre | Titre", "Strain | day 3 | day 7", "cw15 | 4 | 9", "Grown at 25 °C |  |"], t1


def test_table_footnotes_are_kept_and_a_numeric_mark_leaves_its_number_alone():
    # B5: '221<sup>1</sup>' is 221 with footnote 1. I6: '0.5' plus the mark
    # '1.' read as '0.51'. Eight papers lost the footnotes that give units.
    xml = _table("<tr><th>Gene</th><th>Length (bp)</th></tr><tr><td>RPS29</td><td>221<sup>1</sup></td></tr>"
                 "<tr><td>PSAD</td><td>336<xref ref-type='table-fn' rid='n2'><sup>2</sup></xref></td></tr>"
                 "<tr><td>RBCS2</td><td>7.2<xref ref-type='table-fn' rid='n3'><sup>a</sup></xref></td></tr>",
                 foot="<table-wrap-foot><fn id='n1'><label>1</label><p>Length in the gene model.</p></fn>"
                      "<fn id='n2'><label>2.</label><p>Length used.</p></fn>"
                      "<fn id='n3'><p><sup>a</sup> Mean of three.</p></fn></table-wrap-foot>",
                 caption="<label>Table 1</label><caption><p>Micelles with α ∼ 0.5"
                         "<xref ref-type='table-fn' rid='n1'><sup>1.</sup></xref></p></caption>")
    r = split_jats(xml, paper_id="X1")
    t1 = next(s for s in r.sections if s.id == "t1")
    assert t1.heading == "Table 1 Micelles with α ∼ 0.5", t1.heading
    assert t1.text.splitlines() == ["Gene | Length (bp)", "RPS29 | 221", "PSAD | 336", "RBCS2 | 7.2a",
                                    "1 Length in the gene model.", "2. Length used.", "a Mean of three."], t1.text


def test_an_exponent_with_a_space_inside_is_still_a_power():
    # E6: 10<sup>− 15</sup> read '10− 15'. H10: a thin space after the minus.
    s1 = _sections(_doc("<sec><title>R</title><p>p-value &lt;10<sup>− 15</sup> and 4 × 10<sup>− "
                        "5</sup> % biotin; mg L<sup>−1</sup> and [α-<sup>32</sup>P]dCTP.</p></sec>"))["s1"]
    assert "p-value <10^−15 and 4 × 10^−5 % biotin; mg L−1 and [α-32P]dCTP." in s1, s1


def test_tables_and_figures_in_floats_group_are_read():
    # C9, A6, F1: MDPI keeps every table and figure in <floats-group>.
    xml = _doc("<sec><title>R</title><p>See Table 1 and Figure 1.</p></sec>",
               after_body="<floats-group><table-wrap id='t'><label>Table 1</label><caption><p>Primers.</p></caption>"
                          "<table><tr><th>Primer</th><th>bp</th></tr><tr><td>F1</td><td>212</td></tr></table>"
                          "</table-wrap><fig id='f'><label>Figure 1</label><caption><p>Growth.</p></caption></fig>"
                          "</floats-group>")
    sections = _sections(xml)
    assert sections["t1"].splitlines() == ["Primer | bp", "F1 | 212"] and sections["f1"] == "Figure 1 Growth."


def test_back_matter_inside_the_body_is_dropped():
    # Nine papers: Europe PMC serves acknowledgements, footnotes and the
    # statements after them as <sec sec-type=...> inside <body>.
    xml = _doc("<sec><title>Results</title><p>Titres rose.</p></sec>"
               "<sec sec-type='ack'><title>Acknowledgements</title><p>We thank grant 12345.</p></sec>"
               "<sec sec-type='data-availability-statement'><title>Data</title><p>On request.</p></sec>"
               "<sec sec-type='COI-statement'><title>Conflicts</title><p>None.</p></sec>"
               "<sec sec-type='fn-group'><title>Footnotes</title><sec><title>Funding</title><p>EU 777.</p></sec></sec>")
    text = " ".join(_sections(xml).values())
    assert "Titres rose." in text
    for gone in ("12345", "On request", "None.", "EU 777"):
        assert gone not in text, gone


def test_a_line_break_in_a_cell_separates_its_words():
    # G6: 'alters<break/>17%' read 'alters17%', which parse_numbers took for an identifier.
    t1 = _sections(_table("<tr><th>Effect</th></tr><tr><td>alters<break/>17% of sites</td></tr>"))["t1"]
    assert "alters 17% of sites" in t1, t1


def test_mathml_reads_as_a_line():
    # I6: 3/5 flattened to '35'; R_coat^5 to 'Rcoat5'.
    s1 = _sections(_doc("<sec><title>M</title><p>Use <inline-formula><mml:math><mml:mfrac><mml:mn>3</mml:mn>"
                        "<mml:mn>5</mml:mn></mml:mfrac></mml:math></inline-formula> of "
                        "<inline-formula><alternatives><tex-math>R_{coat}^5</tex-math><mml:math><mml:msubsup>"
                        "<mml:mi>R</mml:mi><mml:mi>coat</mml:mi><mml:mn>5</mml:mn></mml:msubsup></mml:math>"
                        "</alternatives></inline-formula> here.</p></sec>"))["s1"]
    assert "Use 3/5 of Rcoat^5 here." in s1, s1


def test_a_table_given_as_an_image_keeps_its_caption():
    # D2: an image-only table left its caption nowhere.
    sections = _sections(_table("", caption="<label>Table 1</label><caption><p>Strains used.</p></caption><graphic/>"))
    assert sections["t1"] == "Table 1 Strains used."


def test_a_licence_url_in_ali_license_ref_is_the_href():
    # G6, N4: the URL sat in <ali:license_ref> and was glued to the sentence.
    front = ("<permissions><license><ali:license_ref>https://creativecommons.org/licenses/by/4.0/</ali:license_ref>"
             "<license-p>This is an open access article.</license-p></license></permissions>")
    r = split_jats(_doc("<sec><title>R</title><p>Text.</p></sec>", front=front), paper_id="X1")
    assert r.license.href == "https://creativecommons.org/licenses/by/4.0/"
    assert r.license.text == "This is an open access article."


def test_a_structured_abstract_keeps_its_headings_apart():
    # O5: 'Background' ran into 'The study'.
    front = "<abstract><sec><title>Background</title><p>The study.</p></sec><sec><title>Results</title><p>It grew.</p></sec></abstract>"
    abstract = _sections(_doc("<sec><title>R</title><p>Text.</p></sec>", front=front))["abstract"]
    assert abstract == "Background The study. Results It grew.", abstract


# ── §6.9 — an outage is not a miss ──────────────────────────────────────


def test_a_transient_failure_is_not_cached_as_a_miss(monkeypatch):
    # A timeout or a 5xx is the network's condition, not the paper's. Cached
    # as failed:fetch it read exactly like "no open-access text", and the
    # batch never asked again without --force; the board showed every paper
    # a brief outage touched as halted.
    import httpx

    request = httpx.Request("GET", "https://www.ebi.ac.uk/europepmc/x")

    def slow(pmcid):
        raise httpx.ReadTimeout("slow", request=request)

    monkeypatch.setattr(intake, "fetch_fulltext", slow)
    r = fetch_paper({"id": "X3", "pmcid": "PMC1"})
    assert r.status == "failed:fetch" and "slow" in (r.reason or "")
    assert cached("X3") is None, "not persisted: the next run asks again"

    def down(pmcid):
        raise intake.Transient("Europe PMC returned 503 for PMC1")

    monkeypatch.setattr(intake, "fetch_fulltext", down)
    r = fetch_paper({"id": "X3", "pmcid": "PMC1"})
    assert r.status == "failed:fetch" and "503" in (r.reason or "")
    assert cached("X3") is None

    # A definitive answer — a 404, a document with nothing in it — IS cached.
    def gone(pmcid):
        raise httpx.HTTPStatusError(
            "Europe PMC returned 404 for PMC1", request=request, response=httpx.Response(404, request=request)
        )

    monkeypatch.setattr(intake, "fetch_fulltext", gone)
    r = fetch_paper({"id": "X3", "pmcid": "PMC1"})
    assert r.status == "failed:fetch" and cached("X3") is not None


def test_a_5xx_from_the_lookup_is_transient_too(monkeypatch):
    # A DOI-only paper resolves through a search; a 503 there is not "no
    # open-access full text", which is what a None answer means.
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "0")
    import httpx

    request = httpx.Request("GET", "https://www.ebi.ac.uk/europepmc/search")
    monkeypatch.setattr(intake, "_get", lambda *a, **k: httpx.Response(503, request=request))
    with pytest.raises(intake.Transient):
        intake.resolve_pmcid({"id": "X4", "doi": "10.1/x"})
    r = fetch_paper({"id": "X4", "doi": "10.1/x"})
    assert r.status == "failed:fetch" and cached("X4") is None
