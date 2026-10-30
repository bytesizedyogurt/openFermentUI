"""The collectors (ADR-002; execution prompt §8.2): an identifier, a file or
pasted text, as a document for Sci RAG Kit with its citation and licence.

Offline: fixture mode refuses the network, and Europe PMC's answers are
fixtures or stand-ins. The parsers' own rules are tested in test_intake.py
and test_intake_sources.py.
"""
from __future__ import annotations

import io
import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfWriter

from openferment_core.literature import collectors
from openferment_core.literature.collectors import Citation, NotCollected, licence_class
from openferment_core.models import FetchedSection, FetchLicense

FIXTURES = Path(__file__).parent / "fixtures"

FRONT = """<article><front>
  <journal-meta><journal-title-group><journal-title>Journal of Placeholders</journal-title></journal-title-group></journal-meta>
  <article-meta>
    <article-id pub-id-type="pmcid">PMC0000001</article-id>
    <article-id pub-id-type="doi">10.0000/placeholder.1</article-id>
    <title-group><article-title>A <italic>placeholder</italic> article</article-title></title-group>
    <contrib-group>
      <contrib contrib-type="author"><name><surname>Doe</surname><given-names>Jane</given-names></name></contrib>
      <contrib contrib-type="author"><collab>The Placeholder Consortium</collab></contrib>
      <contrib contrib-type="editor"><name><surname>Roe</surname><given-names>Richard</given-names></name></contrib>
    </contrib-group>
    <pub-date pub-type="epub"><day>2</day><month>3</month><year>2021</year></pub-date>
  </article-meta></front><body><sec><title>Methods</title><p>Grown at 30 C.</p></sec></body></article>"""


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")


def test_the_front_matter_gives_the_citation():
    found = collectors.jats_citation(FRONT)
    assert found == Citation(
        title="A placeholder article",
        authors=["Jane Doe", "The Placeholder Consortium"],
        year=2021,
        doi="10.0000/placeholder.1",
        journal="Journal of Placeholders",
        pmcid="PMC0000001",
    )
    assert collectors.jats_citation("<not xml") == Citation()


@pytest.mark.parametrize(
    ("href", "text", "expected"),
    [
        ("https://creativecommons.org/licenses/by/4.0/", None, "open_commercial"),
        ("http://creativecommons.org/licenses/by-sa/4.0/", None, "open_commercial"),
        ("https://creativecommons.org/licenses/by-nc/4.0/", None, "open_noncommercial"),
        ("https://creativecommons.org/licenses/by-nc-nd/4.0/", None, "open_noncommercial"),
        ("https://creativecommons.org/licenses/by-nd/4.0/", None, "unknown"),
        ("https://creativecommons.org/publicdomain/zero/1.0/", None, "public"),
        (None, "This article is distributed under the Creative Commons Attribution License.", "open_commercial"),
        (None, "Creative Commons Attribution-NonCommercial 4.0 International", "open_noncommercial"),
        (None, "Creative Commons Attribution-NoDerivatives", "unknown"),
        (None, "CC BY 4.0", "open_commercial"),
        (None, "CC BY-NC-SA 4.0", "open_noncommercial"),
        (None, "CC0", "public"),
        (None, "Creative Commons License", "unknown"),
        (None, "This report is available at no cost from NREL.", "unknown"),
        (None, "© The authors. All rights reserved.", "unknown"),
    ],
)
def test_a_licence_maps_to_the_kits_class_and_fails_closed(href, text, expected):
    assert licence_class(FetchLicense(href=href, text=text)) == expected
    assert licence_class(None) == "unknown"


def test_the_markdown_keeps_each_section_under_its_heading_and_a_table_as_rows():
    sections = [
        FetchedSection(id="abstract", heading="Abstract", text="What was done."),
        FetchedSection(id="s1", heading="Results › Growth", text="It grew."),
        FetchedSection(id="t1", heading="Table 1 Rates", text="Strain | Rate\nA | 7\n\nA note under the table."),
    ]
    assert collectors.markdown("A title", sections) == (
        "# A title\n\n## Abstract\n\nWhat was done.\n\n## Results › Growth\n\nIt grew.\n\n"
        "## Table 1 Rates\n\n| Strain | Rate |\n| A | 7 |\n| A note under the table. |\n"
    )


@pytest.mark.parametrize(
    ("identifier", "collector"),
    [
        ("PMC1234567", "europepmc"),
        ("10.1000/x.1", "europepmc"),
        ("https://doi.org/10.1000/x.1", "europepmc"),
        ("PMID:12345", "europepmc"),
        ("OSTI:1013269", "osti"),
        ("https://www.osti.gov/biblio/1013269", "osti"),
        ("https://www.yeastgenome.org/backend/strain/S000203483", "sgd"),
    ],
)
def test_an_identifier_goes_to_the_collector_that_serves_it(monkeypatch, identifier, collector):
    called: list[str] = []
    for name in ("europepmc", "osti", "sgd"):
        monkeypatch.setattr(collectors, name, lambda asked, name=name: called.append(name))
    collectors.by_identifier(identifier)
    assert called == [collector]


@pytest.mark.parametrize("identifier", ["", "   ", "12345"])
def test_an_identifier_that_names_nothing_or_two_things_is_refused(identifier):
    with pytest.raises(NotCollected) as refused:
        collectors.by_identifier(identifier)
    assert "PMID:12345 or OSTI:12345" in str(refused.value) or "no identifier" in str(refused.value)


def test_a_pmcid_is_fetched_split_and_cited(monkeypatch, tmp_path):
    jats = tmp_path / "jats"
    jats.mkdir()
    shutil.copy(FIXTURES / "jats" / "structural.xml", jats / "PMC0000002.xml")
    monkeypatch.setattr(collectors, "FIXTURE_DIR", jats)
    found = collectors.europepmc("pmc0000002")
    assert found.collector == "europepmc" and found.identifier == "pmc0000002"
    assert found.citation.title == "A structural fixture for the Intake parser"
    assert found.citation.pmcid == "PMC0000002"
    assert found.licence_class == "open_commercial"
    assert found.url == "https://europepmc.org/article/PMC/PMC0000002"
    assert found.text.startswith("# A structural fixture for the Intake parser\n\n## Abstract\n")
    assert found.tables >= 1 and "| Placeholder A | 7 | mg L-1 |" in found.text
    assert found.selection("for the feed study")["reason"] == "for the feed study"


def test_a_pmcid_with_no_text_says_why(monkeypatch, tmp_path):
    monkeypatch.setattr(collectors, "FIXTURE_DIR", tmp_path)
    with pytest.raises(NotCollected) as refused:
        collectors.europepmc("PMC0000003")
    assert "no fixture" in str(refused.value) and not refused.value.transient


def test_a_doi_is_looked_up_and_a_lookup_outage_is_transient(monkeypatch):
    import httpx

    monkeypatch.setenv("OPENFERMENT_FIXTURES", "0")
    request = httpx.Request("GET", "https://www.ebi.ac.uk/europepmc/webservices/rest/search")
    monkeypatch.setattr(collectors, "_get", lambda *a, **k: httpx.Response(503, request=request))
    with pytest.raises(NotCollected) as refused:
        collectors.europepmc("10.1000/x.1")
    assert refused.value.transient

    empty = httpx.Response(200, json={"resultList": {"result": [{"pmcid": "PMC9", "isOpenAccess": "N"}]}}, request=request)
    monkeypatch.setattr(collectors, "_get", lambda *a, **k: empty)
    with pytest.raises(NotCollected) as refused:
        collectors.europepmc("10.1000/x.1")
    assert "no open-access full text for 10.1000/x.1" in str(refused.value)


def _pdf(*pages: str) -> bytes:
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    for words in pages:
        page = writer.add_blank_page(width=612, height=792)
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({words}) Tj ET".encode())
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
        })
        page[NameObject("/Contents")] = writer._add_object(stream)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_an_osti_report_is_its_pdf_a_page_a_section_with_its_record(monkeypatch, tmp_path):
    (tmp_path / "osti").mkdir()
    (tmp_path / "osti" / "1013269.pdf").write_bytes(_pdf("A placeholder report.", "Its second page."))
    (tmp_path / "osti" / "1013269.json").write_text(json.dumps([{
        "title": "A placeholder report", "authors": ["Doe, Jane [Placeholder Lab]"],
        "publication_date": "2011-04-01T00:00:00Z", "doi": "10.2172/1013269",
    }]))
    monkeypatch.setattr(collectors, "FIXTURE_ROOT", tmp_path)
    found = collectors.osti("OSTI:1013269")
    assert found.citation == Citation(title="A placeholder report", authors=["Doe, Jane"], year=2011, doi="10.2172/1013269")
    assert found.url == "https://www.osti.gov/biblio/1013269" and found.sections == 2
    assert "## Page 1\n\nA placeholder report." in found.text and "## Page 2\n\nIts second page." in found.text
    assert found.licence_class == "unknown"


def test_an_sgd_entry_is_its_own_words_under_its_name(monkeypatch, tmp_path):
    (tmp_path / "sgd").mkdir()
    shutil.copy(FIXTURES / "sgd" / "S000203483.json", tmp_path / "sgd" / "S000203483.json")
    monkeypatch.setattr(collectors, "FIXTURE_ROOT", tmp_path)
    found = collectors.sgd("https://www.yeastgenome.org/backend/strain/S000203483")
    assert found.collector == "sgd" and found.licence_class == "open_commercial"
    assert found.citation.title.endswith("(Saccharomyces Genome Database)")
    assert found.text.startswith("# ") and "## Description" in found.text
    with pytest.raises(NotCollected):
        collectors.sgd("https://example.org/strain/S1")


def test_an_upload_is_split_by_its_kind_or_passed_as_it_is():
    pdf = collectors.uploaded("A report.pdf", _pdf("Page one words."), licence_class="restricted")
    assert pdf.collector == "upload" and pdf.citation.title == "A report" and pdf.licence_class == "restricted"
    assert "## Page 1\n\nPage one words." in pdf.text and not pdf.data

    jats = collectors.uploaded("paper.xml", FRONT.encode())
    assert jats.citation.title == "A placeholder article" and "## Methods\n\nGrown at 30 C." in jats.text

    notes = collectors.uploaded("notes.md", b"# Notes\n\nWords.", title="Bench notes", licence="Mine to share")
    assert notes.data == b"# Notes\n\nWords." and notes.suffix == ".md" and notes.citation.title == "Bench notes"
    assert notes.licence == FetchLicense(text="Mine to share") and notes.licence_class == "unknown"


@pytest.mark.parametrize(
    ("name", "data", "chosen", "why"),
    [
        ("a.docx", b"x", "", "is not one of"),
        ("a.txt", b"", "", "is empty"),
        ("a.txt", b"x", "everyone's", "is not a licence class"),
    ],
)
def test_an_upload_it_cannot_take_is_refused_in_words(name, data, chosen, why):
    with pytest.raises(NotCollected) as refused:
        collectors.uploaded(name, data, licence_class=chosen)
    assert why in str(refused.value)


def test_pasted_text_is_kept_under_its_title():
    found = collectors.pasted("Feed notes", "  The feed ran at 2 g/h.  ", url="https://example.org/n", licence_class="public")
    assert found.text == "# Feed notes\n\nThe feed ran at 2 g/h.\n"
    assert found.url == "https://example.org/n" and found.licence_class == "public"
    with pytest.raises(NotCollected):
        collectors.pasted("", "words")
    with pytest.raises(NotCollected):
        collectors.pasted("A title", "   ")


def test_a_collected_document_is_written_under_a_safe_name(tmp_path):
    found = collectors.pasted("../A title: with/slashes", "Words.")
    path = found.write(tmp_path)
    assert path.parent == tmp_path and path.name == "A-title-with-slashes.md"
    assert path.read_text() == found.text


def test_an_upload_keeps_the_title_it_gives_itself():
    md = collectors.uploaded("notes-2023.md", b"Some words first.\n\n# Feed Trials of 2023\n\nWords.")
    assert md.citation.title == "Feed Trials of 2023"
    page = collectors.uploaded("page.html", b"<html><head><title>A <b>Report</b></title></head><body>x</body></html>")
    assert page.citation.title == "A Report"
    plain = collectors.uploaded("plain.txt", b"no title here")
    assert plain.citation.title == "plain"
    assert collectors.uploaded("notes.md", b"# Own", title="Given").citation.title == "Given"
