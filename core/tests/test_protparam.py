"""A protein product's properties from its sequence (OF-BLD-020 §7.1, D12).

Biopython's ProtParam is called in the service itself, so these tests run it
for real: every expected number is the library's own, called here beside the
code under test, and none is typed. The one sequence below is a published
chain, cited by its accession. Nothing here reads a key or the network.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, intake, protparam
from openferment_core.models import BasisSource, ProtParam

CORE = Path(__file__).resolve().parent.parent

# Human insulin's B chain: UniProt P01308 (INS_HUMAN), residues 25–54 of the
# preproinsulin, the mature chain after the signal peptide. Thirty residues,
# with two cysteines and two tyrosines and no tryptophan.
INSULIN_B = "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"
INSULIN_B_SOURCE = "UniProt P01308 (INS_HUMAN), residues 25–54: the insulin B chain"
SOURCE = BasisSource(kind="convention", note=INSULIN_B_SOURCE)


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def seed(monkeypatch):
    """A products catalogue as the corpus carries it, with one entry holding
    the cited chain and others that do not, or hold what ProtParam cannot read."""
    entries = [
        {"id": "insulin-b-chain", "name": "Insulin B chain", "sequence": INSULIN_B, "sequenceSource": INSULIN_B_SOURCE},
        {"id": "taq-dna-polymerase", "name": "Taq DNA polymerase"},
        {"id": "nameless-source", "name": "A chain read from nowhere", "sequence": INSULIN_B, "sequenceSource": None},
        {"id": "with-an-x", "name": "A chain with an unknown residue", "sequence": "FVNQXLCG", "sequenceSource": "a test's words"},
    ]
    monkeypatch.setattr(protparam, "products", lambda: entries)
    return entries


def _library(seq: str):
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    return ProteinAnalysis(seq)


# ── every number is the library's ─────────────────────────────────────────


def test_a_published_chain_gives_exactly_what_protparam_gives(store):
    art = protparam.protparam(INSULIN_B, source=SOURCE)
    o = protparam.output_of(art)
    pa = _library(INSULIN_B)
    reduced, cystines = pa.molar_extinction_coefficient()
    assert o.molecularWeight == pa.molecular_weight()
    assert o.isoelectricPoint == pa.isoelectric_point()
    assert (o.extinctionReduced, o.extinctionCystines) == (reduced, cystines)
    assert o.gravy == pa.gravy()
    assert o.length == len(INSULIN_B) and o.sequenceSource == INSULIN_B_SOURCE
    assert o.units["molecularWeight"] == "Da" and o.units["extinctionReduced"] == "M⁻¹ cm⁻¹"
    assert set(o.how) == set(protparam.UNITS)


def test_the_basis_names_the_library_its_settings_and_the_source(store):
    from importlib.metadata import version

    art = protparam.protparam(INSULIN_B, source=SOURCE)
    v = version("biopython")
    assert art.tool == "protparam" and art.toolVersion == f"protparam 1 · biopython {v}"
    named = {i.name: i for i in art.inputs}
    assert named["sequence"].value == INSULIN_B and named["sequence"].source.note == INSULIN_B_SOURCE
    assert named["library"].value == f"Biopython {v}" and named["library"].source.kind == "model"
    assert named["library"].source.id == f"biopython@{v}"
    # The settings are the library's own defaults, read from its signatures.
    import inspect

    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    assert named["monoisotopic"].value == str(inspect.signature(ProteinAnalysis.__init__).parameters["monoisotopic"].default)
    assert named["hydropathy scale"].value == inspect.signature(ProteinAnalysis.gravy).parameters["scale"].default
    assert {i.source.kind for i in art.inputs} == {"convention", "model"}
    assert art.provenance == "computed"


def test_a_second_call_returns_the_stored_answer_and_a_replay_agrees(store, monkeypatch):
    first = protparam.protparam(INSULIN_B, source=SOURCE)
    reg = artifacts.registered(protparam.TOOL)
    calls = []
    monkeypatch.setattr(artifacts, "_REGISTRY", {**artifacts._REGISTRY, protparam.TOOL: artifacts.Registered(
        reg.tool, reg.version, lambda i, s: calls.append(1) or reg.fn(i, s))})
    again = protparam.protparam(INSULIN_B, source=SOURCE)
    assert again.id == first.id and again.createdAt == first.createdAt and calls == []
    assert artifacts.replay(first.id).identical


def test_a_records_sequence_takes_the_records_provenance(store):
    record = {"id": "r-seq-1", "provenance": "unverified"}
    art = protparam.protparam(INSULIN_B, source=BasisSource(kind="record", id="r-seq-1"),
                              records_by_id={"r-seq-1": record})
    assert art.provenance == "unverified"
    o = protparam.output_of(art)
    assert o.subject == "the sequence of record r-seq-1" and o.sequenceSource == "record r-seq-1"


# ── refused whole, in words ──────────────────────────────────────────────


@pytest.mark.parametrize("seq, words", [
    ("FVNQXLCGB", "'X' at 5; 'B' at 9"),
    ("XXFVX", "'X' at 1, 2, 5"),
    ("FVNQ HL", "' ' at 5"),
    ("fvnq", "'f' at 1; 'v' at 2; 'n' at 3; 'q' at 4"),
    ("", "the sequence is empty"),
])
def test_a_letter_outside_the_twenty_or_nothing_is_refused_naming_where(store, seq, words):
    with pytest.raises(protparam.ProtParamRefused, match=words):
        protparam.protparam(seq, source=SOURCE)
    assert artifacts.all_artifacts() == []


def test_a_long_run_of_one_letter_names_its_first_positions_and_counts_the_rest():
    with pytest.raises(protparam.ProtParamRefused) as e:
        protparam.check("Z" * (protparam.SHOWN_POSITIONS + 3))
    assert f"{protparam.SHOWN_POSITIONS} and 3 more" in str(e.value)


def test_the_twenty_are_the_librarys_own():
    from Bio.Data.IUPACData import protein_letters

    assert protparam.standard_letters() == protein_letters
    assert protparam.check(protein_letters) == protein_letters


# ── a product entry's own sequence ───────────────────────────────────────


def test_a_product_entrys_sequence_is_computed_with_its_source_named(store, seed):
    art = protparam.of_product("insulin-b-chain")
    named = {i.name: i for i in art.inputs}
    assert named["product"].value == "insulin-b-chain" and named["sequence"].source.kind == "convention"
    assert INSULIN_B_SOURCE in named["sequence"].source.note and "insulin-b-chain" in named["sequence"].source.note
    o = protparam.output_of(art)
    assert o.product == "insulin-b-chain" and o.subject == "the sequence of product insulin-b-chain"
    assert o.isoelectricPoint == _library(INSULIN_B).isoelectric_point() and art.provenance == "computed"
    assert protparam.stored("insulin-b-chain").id == art.id


@pytest.mark.parametrize("product, err, words", [
    ("taq-dna-polymerase", protparam.ProtParamMissing, "taq-dna-polymerase's entry carries no sequence"),
    ("nonesuch", protparam.ProtParamMissing, "there is no product 'nonesuch'"),
    ("nameless-source", protparam.ProtParamRefused, "names no source"),
    ("with-an-x", protparam.ProtParamRefused, "'X' at 5"),
    ("", protparam.ProtParamRefused, "by its id"),
])
def test_a_product_with_no_sequence_is_missing_and_a_bad_one_refused(store, seed, product, err, words):
    with pytest.raises(err, match=words):
        protparam.of_product(product)
    with pytest.raises(err, match=words):
        protparam.stored(product)
    assert artifacts.all_artifacts() == []


def test_evidence_is_one_value_a_property_with_the_artifacts_basis(store):
    art = protparam.protparam(INSULIN_B, source=SOURCE)
    ev = protparam.evidence_of(art)
    assert [e.id for e in ev] == [f"{art.id}:{k}" for k, _ in protparam.PROPERTIES]
    assert all(e.basis.artifactId == art.id and e.provenance == "computed" for e in ev)
    assert ev[0].unit == "Da" and ev[0].value == _library(INSULIN_B).molecular_weight()
    # A label is built by code and carries no digit at all: not the answer's
    # numbers, and not the library's version (OF-BLD-020 §7.R, finding 33).
    assert all(not any(ch.isdigit() for ch in e.label) for e in ev), [e.label for e in ev]


def test_a_label_names_the_library_and_never_its_version_so_a_claim_may_copy_it(store, seed):
    """OF-BLD-020 §7.R, finding 33: a claim that copies a property's label word
    for word is not dropped by the digit rule. The library is named; its
    version is the basis's `library` input, which the evidence carries."""
    from importlib.metadata import version

    from openferment_core.validate import find_number

    record = {"id": "r-seq-1", "provenance": "unverified"}
    answers = [protparam.protparam(INSULIN_B, source=SOURCE), protparam.of_product("insulin-b-chain"),
               protparam.protparam(INSULIN_B, source=BasisSource(kind="record", id="r-seq-1"),
                                   records_by_id={"r-seq-1": record})]
    for art in answers:
        for e in protparam.evidence_of(art):
            assert find_number(e.label) is None, e.label
            assert e.label.endswith(", as Biopython's ProtParam computes it"), e.label
            assert {i.name: i.value for i in e.basis.inputs}["library"] == f"Biopython {version('biopython')}"


# ── the endpoints ────────────────────────────────────────────────────────


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


def test_post_computes_get_reads_and_neither_takes_a_sequence(store, seed, client):
    assert client.get("/api/protparam", params={"product": "insulin-b-chain"}).json() == {"artifact": None}
    made = client.post("/api/protparam", json={"product": "insulin-b-chain"})
    assert made.status_code == 200 and made.json()["tool"] == "protparam"
    ProtParam.model_validate(made.json()["output"])
    kept = client.get("/api/protparam", params={"product": "insulin-b-chain"}).json()["artifact"]
    assert kept["id"] == made.json()["id"]
    assert client.post("/api/protparam", json={"product": "insulin-b-chain", "sequence": INSULIN_B}).status_code == 422
    assert client.post("/api/protparam", json={"sequence": INSULIN_B}).status_code == 422


@pytest.mark.parametrize("product, status, words", [
    ("taq-dna-polymerase", 404, "carries no sequence"),
    ("nonesuch", 404, "there is no product"),
    ("with-an-x", 422, "'X' at 5"),
    ("", 422, "by its id"),
])
def test_the_endpoints_say_what_is_missing_and_what_is_refused(store, seed, client, product, status, words):
    for r in (client.post("/api/protparam", json={"product": product}),
              client.get("/api/protparam", params={"product": product})):
        assert r.status_code == status and words in r.json()["detail"], r.text


def test_a_damaged_answer_is_a_409_in_words(store, seed, client):
    from standins import plant_damaged

    art = protparam.of_product("insulin-b-chain")
    plant_damaged(art.id)
    for r in (client.get("/api/protparam", params={"product": "insulin-b-chain"}),
              client.post("/api/protparam", json={"product": "insulin-b-chain"})):
        assert r.status_code == 409 and f"{art.id} is damaged on disk" in r.json()["detail"], r.text


def test_both_tools_are_registered_when_the_service_starts_and_biopython_waits():
    code = ("import sys\nfrom openferment_core import api, artifacts\n"
            "assert 'Bio' not in sys.modules, 'the service imports Biopython at start'\n"
            "print(artifacts.registered('protparam').version)\nprint(artifacts.registered('volatility').version)\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(CORE), timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    lines = out.stdout.strip().splitlines()
    assert lines[-2].startswith("protparam 1 · biopython ") and lines[-1].startswith("thermo volatility 1 · thermosteam ")


def test_no_product_is_catalogued_and_a_product_it_lacks_is_missing_in_words():
    """No store holds a product catalogue yet, so the service ships none: a
    product's properties are missing, said in words, and nothing is
    computed."""
    assert protparam.products() == []
    with pytest.raises(protparam.ProtParamMissing, match="there is no product 'insulin-b-chain' in the products catalogue"):
        protparam.of_product("insulin-b-chain")
