"""Intake from the two sources outside Europe PMC: OSTI reports and Saccharomyces
Genome Database strain entries (thread Q).

Offline. Fixture mode is on for every test here, so nothing reaches the
network even by accident. The report is a PDF this file writes with pypdf, a
few lines a page; the strain entry is `fixtures/sgd/S000203483.json`, trimmed
from what SGD serves.
"""
from __future__ import annotations

import html
import io
import json
import re
import shutil
from pathlib import Path

import httpx
import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from openferment_core import intake
from openferment_core.literature import collectors
from openferment_core.intake import NetworkRefused, cached, fetch_paper, split_pdf, split_sgd, status_of

FIXTURES = Path(__file__).parent / "fixtures"
SGD_ENTRY = FIXTURES / "sgd" / "S000203483.json"
OSTI_URL = "https://www.osti.gov/servlets/purl/1013269"
SGD_URL = "https://www.yeastgenome.org/backend/strain/S000203483"


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "1")
    # Persist under a temp directory so a test never writes into core/data/.
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")


def pdf(*pages: list[str]) -> bytes:
    """A PDF with a text layer, one list of lines a page; an empty list is a
    page with no text."""
    writer = PdfWriter()
    for lines in pages:
        page = writer.add_blank_page(width=612, height=792)
        if not lines:
            continue
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        shown = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
        stream = DecodedStreamObject()
        stream.set_data("\n".join(
            ["BT", "/F1 12 Tf", "14 TL", "72 720 Td", *(f"({line}) Tj T*" for line in shown), "ET"]
        ).encode("latin-1"))
        page.replace_contents(stream)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


REPORT = (
    [
        "Technical Report",
        "This report is available at no cost from the National Renewable Energy",
        "Laboratory (NREL) at www.nrel.gov/publications.",
        "Contract No. DE-AC36-08GO28308",
    ],
    [],
    ["The broth was fermen-", "ted in two stages (seed and production)."],
)


# ── a report: one section per page ─────────────────────────────────────


def test_a_report_is_one_section_per_page_in_the_words_the_library_read():
    data = pdf(*REPORT)
    r = split_pdf(data, paper_id="Q1", source_url=OSTI_URL)
    assert r.status == "complete" and r.source == "osti" and r.pmcid is None and r.bytes == len(data)
    read = [page.extract_text() for page in PdfReader(io.BytesIO(data)).pages]
    # Page two has no text and is left out; the numbering keeps to the pages.
    assert [(s.id, s.heading) for s in r.sections] == [("s1", "Page 1"), ("s3", "Page 3")]
    assert r.sections[0].text == read[0] and r.sections[1].text == read[2]
    # No reflow and no dehyphenation: the line break and the hyphen stay.
    assert "fermen-\nted" in r.sections[1].text
    # A page is never a table or a figure to anything that counts by id.
    assert not any(s.id.startswith(("t", "f")) for s in r.sections)


def test_a_report_licence_is_its_own_availability_sentence():
    r = split_pdf(pdf(*REPORT), source_url=OSTI_URL)
    assert r.license.href == "https://www.osti.gov/biblio/1013269"
    assert r.license.text == (
        "This report is available at no cost from the National Renewable Energy Laboratory (NREL) "
        "at www.nrel.gov/publications."
    )
    older = split_pdf(pdf([
        "Available electronically at http://www.osti.gov/bridge",
        "Available for a processing fee to U.S. Department of Energy",
    ]), source_url=OSTI_URL)
    assert older.license.text == "Available electronically at http://www.osti.gov/bridge"
    silent = split_pdf(pdf(["A report that says nothing of how it may be had."]), source_url=OSTI_URL)
    assert silent.license.text == "The source states no licence."


def test_a_damaged_or_textless_pdf_is_a_parse_failure():
    damaged = split_pdf(b"%PDF-1.7 and nothing a reader can use", paper_id="Q1")
    assert damaged.status == "failed:parse" and damaged.reason.startswith("the PDF did not parse")
    blank = split_pdf(pdf([], []), paper_id="Q1")
    assert blank.status == "failed:parse" and "no text layer" in blank.reason and blank.sections == []


# ── a strain entry: its description, genotype and references ───────────


def test_a_strain_entry_is_its_description_genotype_and_references():
    r = split_sgd(SGD_ENTRY.read_text(encoding="utf-8"), paper_id="Q3")
    assert r.status == "complete" and r.source == "sgd"
    assert [(s.id, s.heading) for s in r.sections] == [
        ("abstract", "Description"), ("s1", "Genotype"), ("s2", "References"),
    ]
    abstract, genotype, references = (s.text for s in r.sections)
    assert abstract.startswith("Reference Genome\nS288C is a widely used laboratory strain")
    assert "a mutated copy of HAP1, it is not a good strain" in abstract and "<" not in abstract
    assert genotype == "MATα SUC2 gal2 mal2 mel flo1 flo8-1 hap1 ho bio1 bio6"
    assert references == (
        "Mortimer RK and Johnston JR (1986) Genealogy of principal strains of the yeast genetic stock "
        "center. Genetics 113(1):35-43"
    )
    assert r.license.href == "http://creativecommons.org/licenses/by/4.0/"
    assert r.license.text == "Creative Commons License"


def test_a_strain_entry_adds_no_words_of_its_own():
    raw = SGD_ENTRY.read_text(encoding="utf-8")
    said = re.sub(r"<[^>]+>", "", html.unescape(raw))
    r = split_sgd(raw)
    for s in r.sections:
        for word in s.text.split():
            assert word in said, (s.id, word)
    # The assembly's figures, its links and its contigs are not sentences.
    everything = "\n".join(s.text for s in r.sections)
    for absent in ("12157105", "GCF_000146045.2", "Chromosome X", "atcc.org"):
        assert absent not in everything


@pytest.mark.parametrize("text", ["{not json", "[]", '{"display_name": "S288C", "paragraph": null}'])
def test_an_entry_with_nothing_to_read_is_a_parse_failure(text):
    r = split_sgd(text, paper_id="Q3")
    assert r.status == "failed:parse" and r.reason and r.source == "sgd"


# ── fetch: dispatch, cache, and the network guard ──────────────────────


@pytest.fixture
def fixture_root(monkeypatch, tmp_path):
    root = tmp_path / "fixtures"
    (root / "osti").mkdir(parents=True)
    (root / "sgd").mkdir()
    (root / "osti" / "1013269.pdf").write_bytes(pdf(*REPORT))
    shutil.copy(SGD_ENTRY, root / "sgd" / "S000203483.json")
    monkeypatch.setattr(collectors, "FIXTURE_ROOT", root)
    return root


def test_source_of_reads_the_host():
    assert intake.source_of({"sourceUrl": OSTI_URL}) == "osti"
    assert intake.source_of({"sourceUrl": SGD_URL}) == "sgd"
    assert intake.source_of({"pmcid": "PMC1"}) == "europepmc"
    assert intake.source_of({"sourceUrl": "https://example.org/osti.gov/1"}) == "europepmc"


def test_a_paper_with_a_source_address_is_fetched_there_and_cached(fixture_root):
    # It carries a DOI too, and is still not asked of Europe PMC: in fixture
    # mode that lookup would have been refused and cached as a miss.
    report = fetch_paper({"id": "Q1", "doi": "10.2172/1013269", "sourceUrl": OSTI_URL})
    assert report.status == "complete" and report.source == "osti"
    assert cached("Q1").source == "osti" and len(cached("Q1").sections) == 2
    s = status_of("Q1")
    assert s.source == "osti" and s.tables == 0 and s.license == "https://www.osti.gov/biblio/1013269"
    strain = fetch_paper({"id": "Q3", "sourceUrl": SGD_URL})
    assert strain.status == "complete" and strain.source == "sgd"
    overlay = intake.overlay_papers()
    assert overlay["Q1"].source == "osti" and overlay["Q3"].source == "sgd"
    assert overlay["Q3"].license == "http://creativecommons.org/licenses/by/4.0/"
    again = fetch_paper({"id": "Q3", "sourceUrl": SGD_URL})
    assert again.fetchedAt == strain.fetchedAt, "a cached result is returned, not re-fetched"


def test_the_batch_reaches_an_entry_with_no_identifier_but_its_address(fixture_root):
    results = intake.fetch_all([{"id": "Q3", "sourceUrl": SGD_URL}, {"id": "O4"}])
    assert [r.paperId for r in results] == ["Q3"]


def test_fixture_mode_refuses_the_network_for_both_sources(fixture_root):
    with pytest.raises(NetworkRefused):
        intake.fetch_pdf("https://www.osti.gov/servlets/purl/1")
    with pytest.raises(NetworkRefused):
        intake.fetch_sgd("https://www.yeastgenome.org/backend/strain/S000000001")
    with pytest.raises(NetworkRefused):
        intake._get(OSTI_URL, follow_redirects=True)
    # Through fetch_paper the refusal is a miss, cached as one.
    r = fetch_paper({"id": "Q9", "sourceUrl": "https://www.osti.gov/servlets/purl/1"})
    assert r.status == "failed:fetch" and "no fixture" in (r.reason or "") and cached("Q9") is not None


def test_an_outage_is_not_cached_and_a_page_in_place_of_a_pdf_is(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_FIXTURES", "0")
    request = httpx.Request("GET", OSTI_URL)
    asked: list[dict] = []

    def answer(response):
        def get(url, params=None, **kw):
            asked.append(kw)
            if isinstance(response, Exception):
                raise response
            return response
        return get

    paper = {"id": "Q1", "sourceUrl": OSTI_URL}
    monkeypatch.setattr(collectors, "_get", answer(httpx.Response(503, request=request)))
    r = fetch_paper(paper)
    assert r.status == "failed:fetch" and "503" in (r.reason or "") and cached("Q1") is None
    assert asked[-1].get("follow_redirects") is True, "the purl's redirects are followed"

    monkeypatch.setattr(collectors, "_get", answer(httpx.ConnectError("down", request=request)))
    assert fetch_paper(paper).status == "failed:fetch" and cached("Q1") is None

    page = httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>sign in</html>", request=request)
    monkeypatch.setattr(collectors, "_get", answer(page))
    r = fetch_paper(paper, force=True)
    assert r.status == "failed:fetch" and "not a PDF" in (r.reason or "") and cached("Q1") is not None

    monkeypatch.setattr(collectors, "_get", answer(httpx.Response(404, request=request)))
    assert fetch_paper(paper, force=True).status == "failed:fetch" and "404" in cached("Q1").reason

    # Served as octet-stream, a PDF is still a PDF by its first bytes.
    data = pdf(*REPORT)
    stream = httpx.Response(200, headers={"content-type": "application/octet-stream"}, content=data, request=request)
    monkeypatch.setattr(collectors, "_get", answer(stream))
    assert fetch_paper(paper, force=True).status == "complete"


def test_a_file_cached_before_the_source_field_reads_as_europe_pmc():
    intake.FULLTEXT_DIR.mkdir(parents=True)
    (intake.FULLTEXT_DIR / "B5.json").write_text(json.dumps({
        "paperId": "B5", "pmcid": "PMC8471596", "status": "complete", "fetchedAt": "2026-10-14T00:00:00+00:00",
        "sections": [{"id": "abstract", "heading": "Abstract", "text": "Words."}], "bytes": 10,
    }), encoding="utf-8")
    assert cached("B5").source == "europepmc"
    assert intake.overlay_papers()["B5"].source == "europepmc"
    assert status_of("B5").source == "europepmc"
