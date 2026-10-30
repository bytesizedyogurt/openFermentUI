"""pureOS proposes a train by rules that each name the property they read
(OF-BLD-020 §7.2, D12, D13, E.4‴).

Offline, thermosteam's answer is a STAND-IN in the worker's shape with
invented numbers (the boiling points and the azeotrope a test names), and
Biopython's ProtParam runs for real on one published chain, cited by its
accession, carried by a STAND-IN product in this file's own products catalogue
and never in the repository's. The one `sim` test asks the real worker. Nothing
here reads a key or the network.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, intake, proforma, protparam, pureos, thermo, tools
from openferment_core.models import Artifact, TrainProposal
from openferment_core.pureos import proposer, train_spec
from openferment_core.workers import WorkerError

CORE = Path(__file__).resolve().parent.parent
STANDIN = "STAND-IN for a test: thermosteam's answer in its shape, every number invented"

# Human insulin's B chain: UniProt P01308 (INS_HUMAN), residues 25–54 of the
# preproinsulin, the mature chain after the signal peptide (as test_protparam
# cites it). A STAND-IN product carries it here, in this test's seed alone.
INSULIN_B = "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"
INSULIN_B_SOURCE = "UniProt P01308 (INS_HUMAN), residues 25–54: the insulin B chain"


class VolatilityStandIn:
    """The worker's `volatility` op in its shape: `lighter` names which
    chemical boils first, `none` the chemicals with no azeotrope, `unsaid` the
    ones whose answer cannot say, `refuse` those the library lacks."""

    def __init__(self, heavier=(), none=(), unsaid=(), refuse=(), library=STANDIN):
        self.calls: list[dict] = []
        self.heavier, self.none, self.unsaid, self.refuse = set(heavier), set(none), set(unsaid), set(refuse)
        self.library = library

    def __call__(self, op, args):
        assert op == "volatility", op
        self.calls.append(args)
        chem = args["chemical"]
        if chem in self.refuse:
            raise WorkerError(f"Refused: thermosteam's chemical library has no chemical named {chem}")
        if chem == "boom":
            raise WorkerError("RuntimeError: something else went wrong")
        found = None if chem in self.unsaid else chem not in self.none
        return {"library": self.library, "chemical": chem, "partner": args["partner"], "P": 101325.0,
                "PSource": thermo.LIBRARY_DEFAULT, "boilingPoint": 351.0, "partnerBoilingPoint": 373.0,
                "lighter": args["partner"] if chem in self.heavier else chem, "azeotrope": found,
                "azeotropeMoleFraction": 0.9 if found else None, "azeotropeMassFraction": 0.95 if found else None,
                "azeotropeT": 350.0 if found else None, "searched": {"of": chem, "from": 0.1, "to": 0.9, "points": 9},
                "units": {"boilingPoint": "K"}, "how": STANDIN, "notes": []}


# A products catalogue and the strains on file, in the corpus's shape: STAND-IN
# entries beside real ids, so each rule is reached.
MOLECULES = [
    {"id": "insulin-b-chain", "name": "Insulin B chain (STAND-IN)", "category": "therapeutic_protein",
     "location": "secreted"},
    {"id": "insulin-b-inside", "name": "Insulin B chain held in the cells (STAND-IN)", "category": "therapeutic_protein",
     "location": "intracellular"},
    {"id": "protein-no-chain", "name": "A secreted protein with no chain (STAND-IN)", "category": "food_protein",
     "location": "secreted"},
    {"id": "taq-dna-polymerase", "name": "Taq DNA polymerase", "category": "molecular_biology_enzyme"},
    {"id": "valencene", "name": "Valencene", "category": "terpene"},
    {"id": "granules", "name": "A stored polymer (STAND-IN)", "category": "biopolymer",
     "location": "intracellular"},
    {"id": "secreted-polymer", "name": "A secreted polymer (STAND-IN)", "category": "biopolymer",
     "location": "secreted"},
    {"id": "odd-category", "name": "A category no rule reads (STAND-IN)", "category": "a word of its own"},
]
HOSTS = [
    {"id": "s-cerevisiae-s288c", "name": "Saccharomyces cerevisiae S288C"},
    {"id": "ecoli", "name": "Escherichia coli expression strains"},
]
SEQUENCES = [
    {"id": "insulin-b-chain", "name": "Insulin B chain", "sequence": INSULIN_B, "sequenceSource": INSULIN_B_SOURCE},
    {"id": "insulin-b-inside", "name": "Insulin B chain", "sequence": INSULIN_B, "sequenceSource": INSULIN_B_SOURCE},
    {"id": "protein-no-chain", "name": "A secreted protein with no chain"},
    {"id": "taq-dna-polymerase", "name": "Taq DNA polymerase"},
]
YEAST = "s-cerevisiae-s288c"


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def seed(monkeypatch):
    monkeypatch.setattr(proposer, "_catalogue", lambda: SimpleNamespace(products=MOLECULES, strains=HOSTS))
    monkeypatch.setattr(protparam, "products", lambda: SEQUENCES)
    monkeypatch.setattr(thermo, "CHEMICALS", {**thermo.CHEMICALS, "methanol-product": "Methanol",
                                              "heavy-product": "Glycerol", "unsaid-product": "Unsaid",
                                              "odd-product": "boom", "unobtainium-product": "Unobtainium"})


@pytest.fixture()
def worker(monkeypatch):
    w = VolatilityStandIn(heavier={"Glycerol"}, none={"Methanol"}, unsaid={"Unsaid"}, refuse={"Unobtainium"})
    monkeypatch.setattr(proforma, "call", w)
    return w


def _units(p: TrainProposal) -> list[tuple[str, str]]:
    return [(u.id, u.type) for u in p.train.units] if p.train else []


def _no_value(p: TrainProposal) -> None:
    """D12: a proposal types no value: no parameter, record or inlet value,
    and no reason's words hold a number."""
    assert p.train is not None
    assert p.train.inlet.params == {}
    for u in p.train.units:
        assert u.params == {} and u.records == {} and u.readFrom is None, u
    for r in p.reasons:
        assert not re.search(r"\d", r.words), r.words


# ── a small molecule: thermosteam's boiling points and azeotrope ─────────


def test_ethanol_proposes_distillation_then_a_sieve_because_thermosteam_finds_the_azeotrope(store, seed, worker):
    p = pureos.propose("ethanol", YEAST)
    [vol] = [a for a in artifacts.all_artifacts() if a.tool == "volatility"]
    assert _units(p) == [("D1", "distillation"), ("MS1", "molecular-sieve")]
    assert [(r.unitId, r.rule, r.property, r.artifactId) for r in p.reasons] == [
        ("D1", "volatile-separate", "boilingPoint", vol.id), ("MS1", "azeotrope-dehydrate", "azeotrope", vol.id)]
    assert "below Water's" in p.reasons[0].words and "minimum-boiling azeotrope of Ethanol and Water" in p.reasons[1].words
    assert p.productClass == "small molecule" and p.program == "yeast" and p.artifacts == [vol.id]
    assert p.train.product == "ethanol" and p.train.program == "yeast" and p.train.inlet.kind == "typed"
    assert p.missing == [] and pureos.validate(p.train) == []
    _no_value(p)
    # Asked by the library's own names, the pressure the library's default.
    assert worker.calls == [{"chemical": "Ethanol", "partner": "Water", "P": None}]
    # Kept: nothing but the property artifact.
    assert [a.tool for a in artifacts.all_artifacts()] == ["volatility"]
    # Asked again, the stored answer is read: the worker is not asked twice.
    assert pureos.propose("ethanol", YEAST).model_dump() == p.model_dump() and len(worker.calls) == 1


def test_no_azeotrope_found_proposes_the_column_alone_and_says_why(store, seed, worker):
    p = pureos.propose("methanol-product", YEAST)
    assert _units(p) == [("D1", "distillation")]
    assert any("no minimum-boiling azeotrope of Methanol and Water" in n for n in p.notes)
    assert pureos.validate(p.train) == []


def test_an_azeotrope_the_library_cannot_say_is_named_missing(store, seed, worker):
    p = pureos.propose("unsaid-product", YEAST)
    assert _units(p) == [("D1", "distillation")]
    assert [m.property for m in p.missing] == ["azeotrope"]


def test_a_small_molecule_heavier_than_water_is_extracted_and_the_reason_names_the_other_step(store, seed, worker):
    p = pureos.propose("heavy-product", YEAST)
    assert _units(p) == [("X1", "lle")]
    [r] = p.reasons
    assert (r.rule, r.property) == ("nonvolatile-extract", "boilingPoint") and "crystallisation" in r.words
    assert "above Water's" in r.words
    _no_value(p)


def test_a_chemical_the_library_lacks_is_refused_and_a_dead_worker_is_its_own_error(store, seed, worker):
    with pytest.raises(pureos.ProposeRefused, match="no chemical named Unobtainium"):
        pureos.propose("unobtainium-product", YEAST)
    with pytest.raises(WorkerError, match="something else"):
        pureos.propose("odd-product", YEAST)
    assert artifacts.all_artifacts() == []


# ── a protein: ProtParam on a cited chain, where the seed says it is ─────


def test_a_secreted_protein_proposes_clarify_uf_and_chromatography_keyed_on_pi(store, seed, worker):
    p = pureos.propose("insulin-b-chain", YEAST)
    [pp] = [a for a in artifacts.all_artifacts() if a.tool == "protparam"]
    assert _units(p) == [("C1", "centrifugation"), ("UF1", "uf-df"), ("CH1", "chromatography"),
                         ("CH2", "chromatography"), ("SD1", "spray-dry")]
    assert [(r.rule, r.property, r.artifactId) for r in p.reasons] == [
        ("secreted-clarify", "location", None), ("protein-concentrate", "molecularWeight", pp.id),
        ("protein-capture", "isoelectricPoint", pp.id), ("protein-polish", "molecularWeight", pp.id),
        ("protein-formulate", "class", None)]
    # The capture's mode waits: no inlet carries a pH, and the reason says so.
    capture = p.reasons[2]
    assert "carries no pH" in capture.words and "mode waits" in capture.words
    assert p.train.units[2].params == {}
    # The isoelectric point read is the library's own, kept as the artifact.
    from Bio.SeqUtils.ProtParam import ProteinAnalysis

    assert protparam.output_of(pp).isoelectricPoint == ProteinAnalysis(INSULIN_B).isoelectric_point()
    assert p.productClass == "protein" and p.artifacts == [pp.id] and worker.calls == []
    assert pureos.validate(p.train) == []
    _no_value(p)


def test_an_intracellular_protein_is_harvested_disrupted_and_clarified_first(store, seed, worker):
    p = pureos.propose("insulin-b-inside", YEAST)
    assert _units(p) == [("C1", "centrifugation"), ("H1", "cell-disruption"), ("C2", "centrifugation"),
                         ("UF1", "uf-df"), ("CH1", "chromatography"), ("CH2", "chromatography"), ("SD1", "spray-dry")]
    # The harvest sends the cells on: a word, the catalogue's own outlet names.
    assert p.train.units[0].outlets == {"cake": "onward", "liquid": "waste"}
    assert p.train.units[2].outlets == {}
    assert [r.rule for r in p.reasons][:3] == ["intracellular-harvest", "intracellular-disrupt", "disrupted-clarify"]
    assert pureos.validate(p.train) == []
    _no_value(p)


def test_an_intracellular_polymer_is_harvested_digested_washed_and_dried(store, seed, worker):
    p = pureos.propose("granules", YEAST)
    assert _units(p) == [("C1", "centrifugation"), ("H1", "cell-disruption"), ("C2", "centrifugation"),
                         ("DD1", "drying-drum")]
    assert [u.outlets for u in p.train.units] == [{"cake": "onward", "liquid": "waste"}, {},
                                                   {"cake": "onward", "liquid": "waste"}, {}]
    assert p.artifacts == [] and pureos.validate(p.train) == []
    _no_value(p)


# ── nothing proposed: the missing property named ─────────────────────────


@pytest.mark.parametrize("product, host, missing", [
    # No sequence and no thermodynamics: the seed says neither where it is nor its chain.
    ("taq-dna-polymerase", "ecoli", ["location", "sequence"]),
    ("protein-no-chain", YEAST, ["sequence"]),
    ("valencene", YEAST, ["volatility"]),
    ("secreted-polymer", YEAST, ["location"]),
    ("odd-category", YEAST, ["class"]),
])
def test_a_product_whose_deciding_property_is_missing_proposes_nothing_and_names_it(store, seed, worker, product,
                                                                                    host, missing):
    p = pureos.propose(product, host)
    assert p.train is None and p.reasons == [] and [m.property for m in p.missing] == missing
    assert all(m.why for m in p.missing) and any("Nothing is proposed" in n for n in p.notes)
    assert worker.calls == [] and artifacts.all_artifacts() == []


def test_the_missing_words_are_the_property_functions_own(store, seed, worker):
    p = pureos.propose("taq-dna-polymerase", "ecoli")
    why = {m.property: m.why for m in p.missing}
    assert "carries no sequence" in why["sequence"] and "secreted or stays in the cells" in why["location"]
    assert "names no chemical of thermosteam's library" in pureos.propose("valencene", YEAST).missing[0].why
    # Neither names a chemical set: the one pureOS holds, said so.
    assert p.program == "yeast" and any("built on the one it holds, yeast" in n for n in p.notes)


@pytest.mark.parametrize("product", ["ethanol", "methanol-product", "heavy-product", "insulin-b-chain",
                                     "insulin-b-inside", "granules"])
def test_every_proposal_validates_and_carries_no_parameter_value(store, seed, worker, product):
    p = pureos.propose(product, YEAST)
    assert pureos.validate(p.train) == [] and pureos.validation(p.train).ok
    assert len(p.reasons) == len(p.train.units) and [r.unitId for r in p.reasons] == [u.id for u in p.train.units]
    _no_value(p)


# ── what is refused ──────────────────────────────────────────────────────


def test_an_unknown_product_is_unknown_and_an_unknown_host_refused(store, seed, worker):
    with pytest.raises(pureos.ProposeUnknown, match="no product 'nonesuch'"):
        pureos.propose("nonesuch", YEAST)
    with pytest.raises(pureos.ProposeRefused, match="no host 'nobody'"):
        pureos.propose("ethanol", "nobody")
    for product, host in (("", YEAST), ("ethanol", "")):
        with pytest.raises(pureos.ProposeRefused):
            pureos.propose(product, host)


def _kept(store: Path, aid: str, tool: str, output: dict) -> Artifact:
    art = Artifact(id=aid, tool=tool, toolVersion="a test's", inputs=[], output=output, outputHash="0",
                   provenance="demo", createdAt="2026-10-21T00:00:00Z", durationMs=0)
    from standins import plant_artifact

    return plant_artifact(art)


def test_an_inlet_names_a_kept_simulation_or_a_runs_stream(store, seed, worker, monkeypatch):
    sim = _kept(store, "0123456789abcdef", "fermos.simulation", {"family": "batch_v1", "product": "ethanol"})
    p = pureos.propose("ethanol", YEAST, sim.id)
    assert p.train.inlet.kind == "simulation" and p.train.inlet.ref == sim.id and p.train.inlet.params == {}
    assert pureos.validate(p.train) == []
    run = _kept(store, "fedcba9876543210", "proforma.run", {})
    monkeypatch.setattr(proforma, "tables_of", lambda art: SimpleNamespace(streams=[SimpleNamespace(id="beer")]))
    p = pureos.propose("ethanol", YEAST, f"{run.id}/beer")
    assert (p.train.inlet.kind, p.train.inlet.ref, p.train.inlet.streamId) == ("run-stream", run.id, "beer")
    assert pureos.validate(p.train) == []
    other = _kept(store, "00000000000000aa", "fermos.simulation", {"family": "batch_v1", "product": "glycerol"})
    fit = _kept(store, "00000000000000bb", "kinetic_fit", {})
    for ref, words in (("not-an-id", "is neither"), ("abcdefabcdefabcd", "no kept artifact"),
                       (other.id, "makes glycerol"), (run.id, "name the stream"), (f"{run.id}/mash", "no stream mash"),
                       (f"{sim.id}/beer", "by its id alone"), (fit.id, "kinetic_fit artifact")):
        with pytest.raises(pureos.ProposeRefused, match=words):
            pureos.propose("ethanol", YEAST, ref)


def test_capture_compares_two_read_numbers_and_waits_with_no_ph():
    assert proposer.capture_mode(5.0, None)[0] is None
    assert "carries no pH" in proposer.capture_mode(5.0, None)[1]
    mode, why = proposer.capture_mode(6.0, 5.0)
    assert mode == "iex" and "cation exchanger" in why
    mode, why = proposer.capture_mode(5.0, 6.0)
    assert mode == "iex" and "anion exchanger" in why
    assert proposer.capture_mode(5.0, 5.0)[0] is None


def test_the_proposer_holds_no_number():
    """Rule 1: no numeric literal in proposer.py, so no threshold of its own."""
    tree = ast.parse((CORE / "openferment_core" / "pureos" / "proposer.py").read_text(encoding="utf-8"))
    found = [(n.lineno, n.value) for n in ast.walk(tree)
             if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]
    assert found == []


def test_every_rule_names_a_unit_type_of_the_catalogue():
    from openferment_core.pureos import catalogue

    assert {r.unit for r in proposer.RULES.values()} <= set(catalogue.ids())
    assert set(proposer.PREFIX) <= set(catalogue.ids())


# ── the endpoint ─────────────────────────────────────────────────────────


@pytest.fixture()
def client(store, seed, worker):
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


def test_post_proposes_and_says_what_is_unknown_refused_or_cannot_be_asked(client, worker, store):
    r = client.post("/api/pureos/propose", json={"product": "ethanol", "host": YEAST})
    assert r.status_code == 200
    p = TrainProposal.model_validate(r.json())
    assert [u.type for u in p.train.units] == ["distillation", "molecular-sieve"]
    r = client.post("/api/pureos/propose", json={"product": "taq-dna-polymerase", "host": "ecoli"})
    assert r.status_code == 200 and r.json()["train"] is None
    assert client.post("/api/pureos/propose", json={"product": "nonesuch", "host": YEAST}).status_code == 404
    r = client.post("/api/pureos/propose", json={"product": "ethanol", "host": "nobody"})
    assert r.status_code == 422 and "no host 'nobody'" in r.json()["detail"]
    r = client.post("/api/pureos/propose", json={"product": "odd-product", "host": YEAST})
    assert r.status_code == 503 and "where thermosteam runs" in r.json()["detail"]
    # Ids and words: a number, or a field the request does not take, is refused.
    assert client.post("/api/pureos/propose", json={"product": "ethanol", "host": YEAST, "P": 5}).status_code == 422
    assert client.post("/api/pureos/propose", json={"product": "ethanol", "host": YEAST, "pH": 7}).status_code == 422
    assert {a.tool for a in artifacts.all_artifacts()} == {"volatility"}


def test_a_damaged_property_answer_is_a_409_in_words(client, store):
    from standins import plant_damaged

    art = thermo.volatility("ethanol")
    plant_damaged(art.id)
    r = client.post("/api/pureos/propose", json={"product": "ethanol", "host": YEAST})
    assert r.status_code == 409 and f"{art.id} is damaged on disk" in r.json()["detail"]


def test_with_no_strain_on_file_the_endpoint_refuses_in_words(store, worker):
    # The catalogues are empty until a project's documents bring entries (alpha 2.0, ADR-010).
    from openferment_core import api

    r = TestClient(api.app, base_url="http://127.0.0.1").post("/api/pureos/propose",
                                                              json={"product": "ethanol", "host": YEAST})
    assert r.status_code == 422 and f"there is no host {YEAST!r} among the strains on file" in r.json()["detail"]


# ── the tool ─────────────────────────────────────────────────────────────


def _numbers(value) -> list:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return []
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, dict):
        return [n for v in value.values() for n in _numbers(v)]
    return [n for v in value for n in _numbers(v)]


def test_the_tool_is_a_loose_read_whose_schema_takes_no_number():
    tool = tools.REGISTRY["pureos_propose"]
    assert tool.strict is False
    schema = json.dumps(tool.info().inputSchema)
    assert '"number"' not in schema and '"integer"' not in schema
    assert set(tool.info().inputSchema["properties"]) == {"product", "host", "inletRef"}


def test_the_tool_returns_the_proposal_as_data_its_summary_in_words_and_the_properties_as_evidence(store, seed, worker):
    r = tools.run("pureos_propose", {"product": "ethanol", "host": YEAST, "inletRef": ""})
    assert r.error is None
    [vol] = [a for a in artifacts.all_artifacts() if a.tool == "volatility"]
    assert [(u["unitId"], u["type"], u["rule"], u["property"], u["artifactId"]) for u in r.summary["units"]] == [
        ("D1", "distillation", "volatile-separate", "boilingPoint", vol.id),
        ("MS1", "molecular-sieve", "azeotrope-dehydrate", "azeotrope", vol.id)]
    # No number in the summary: the values are in the evidence, read from the artifact.
    assert _numbers(r.summary) == []
    assert [e.id for e in r.evidence] == [e.id for e in thermo.volatility_evidence(vol)] == r.summary["propertyEvidence"]
    assert TrainProposal.model_validate(r.data).train.units[0].type == "distillation"
    protein = tools.run("pureos_propose", {"product": "insulin-b-chain", "host": YEAST, "inletRef": ""})
    [pp] = [a for a in artifacts.all_artifacts() if a.tool == "protparam"]
    assert [e.id for e in protein.evidence] == [e.id for e in protparam.evidence_of(pp)]
    assert _numbers(protein.summary) == []
    nothing = tools.run("pureos_propose", {"product": "taq-dna-polymerase", "host": "ecoli", "inletRef": ""})
    assert nothing.summary["proposed"] is False and [m["property"] for m in nothing.summary["missing"]] == [
        "location", "sequence"] and nothing.evidence == []


def test_the_tool_refuses_a_number_and_an_unknown_product(store, seed, worker):
    assert "a number was typed" in tools.run("pureos_propose", {"product": "ethanol", "host": YEAST, "inletRef": 5}).error
    assert "pureos_propose refused: there is no product" in tools.run(
        "pureos_propose", {"product": "nonesuch", "host": YEAST}).error
    assert "could not ask thermosteam" in tools.run("pureos_propose", {"product": "odd-product", "host": YEAST}).error


def test_a_claim_may_cite_a_property_the_tool_returned(store, seed, worker):
    from openferment_core.validate import SeenSet

    r = tools.run("pureos_propose", {"product": "ethanol", "host": YEAST})
    seen = SeenSet()
    seen.add(r)
    assert all(e.id in seen.evidence for e in r.evidence) and r.evidence


def test_a_claim_that_copies_a_property_label_word_for_word_is_kept(store, seed, monkeypatch):
    """OF-BLD-020 §7.R, finding 33: every property the tool returns is labelled
    in words a claim may copy, so validate's digit rule keeps such a claim
    (thermosteam's answer here carries the real worker's library words, its
    name and version, and ProtParam's is Biopython's own)."""
    from importlib.metadata import version
    from openferment_core.validate import SeenSet, validate_plan

    monkeypatch.setattr(proforma, "call", VolatilityStandIn(library=f"thermosteam {version('thermosteam')}"))
    seen, evidence = SeenSet(), []
    for product in ("ethanol", "insulin-b-chain"):
        r = tools.run("pureos_propose", {"product": product, "host": YEAST})
        assert r.error is None and r.evidence, r.error
        seen.add(r)
        evidence += r.evidence
    assert {e.basis.tool for e in evidence} == {"volatility", "protparam"}
    claims = [{"id": f"c{n}", "text": e.label, "recordIds": [], "support": "direct", "passages": [],
               "evidenceIds": [e.id], "moduleRefs": []} for n, e in enumerate(evidence, start=1)]
    out = validate_plan(claims, seen, SimpleNamespace(record=lambda rid: None))
    assert out.reasons == [] and [c.text for c in out.claims] == [e.label for e in evidence]


# ── the real worker ──────────────────────────────────────────────────────


@pytest.mark.sim
def test_ethanol_through_the_real_worker_is_distilled_then_sieved(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(proposer, "_catalogue", lambda: SimpleNamespace(products=[], strains=HOSTS))
    proforma.start(background=False)
    p = pureos.propose("ethanol", YEAST)
    [vol] = [a for a in artifacts.all_artifacts() if a.tool == "volatility"]
    o = thermo.volatility_of(vol)
    # Because thermosteam's own answer says so: ethanol boils before water, and
    # the pair has a minimum-boiling azeotrope.
    assert o.lighter == "Ethanol" and o.azeotrope is True
    assert [u.type for u in p.train.units] == ["distillation", "molecular-sieve"]
    assert [(r.property, r.artifactId) for r in p.reasons] == [("boilingPoint", vol.id), ("azeotrope", vol.id)]
    assert pureos.validate(p.train) == [] and [a.tool for a in artifacts.all_artifacts()] == ["volatility"]
    _no_value(p)
