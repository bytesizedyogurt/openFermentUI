"""SFF flowsheet records (ADR-003; execution prompt §8.3), offline.

The graph is read from a small SFF document written here; the toolkit's
verdicts come from a STAND-IN for the Proforma worker's SFF ops, which
answers in the toolkit's shape and counts its calls; the reference corpus
is a manifest of one small file, served by a stand-in for GitHub. The real
toolkit, a real export and the real reference files are the `sim` tests in
test_sff_sim.py.
"""
from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core.api import app
from openferment_core.engine import sff, simulator
from openferment_core.models import Artifact

CORE = Path(__file__).resolve().parent.parent
PROJECT = "test-project"


def small_doc(**metadata) -> dict:
    """A plant of four units: a feed into M1, M1 to R1, R1 to S1, a recycle
    from S1 back to M1, a product out of S1, a vent out of R1, a stream to a
    unit the file does not list, and one that touches no unit."""
    return {
        "metadata": {"sff_version": "0.2.4", "TEA_currency": "USD", "TEA_year": 2018,
                     "process_simulator": {"name": "BioSTEAM", "version": "2.54.0"},
                     "feedstocks": [{"display_name": "Corn stover", "stream_id": "feed"}],
                     "products": [{"display_name": "Ethanol", "stream_id": "ethanol"}], **metadata},
        "quantity_units_global": {"mass_flow": {"aliases": ["total_mass_flow"], "quantity_units": "kg/hr"},
                                  "price": {"aliases": ["price"], "quantity_units": "USD/kg"}},
        "units": [
            {"id": "M1", "unit_type": "Mixer", "design_simulation_method": "Mixer on https://example.org/m"},
            {"id": "R1", "unit_type": "Fermentation", "design_simulation_method": "SimultaneousSaccharification on x"},
            {"id": "S1", "unit_type": "Splitter"},
            {"id": "P1", "unit_type": "Pump"},
        ],
        "streams": [
            {"id": "feed", "source_unit_id": "None", "sink_unit_id": "M1", "price": 0.05,
             "stream_properties": {"total_mass_flow": 1000.0}},
            {"id": "s1", "source_unit_id": "M1", "sink_unit_id": "R1", "stream_properties": {"total_mass_flow": 1200.0}},
            {"id": "s2", "source_unit_id": "R1", "sink_unit_id": "S1", "stream_properties": {"total_mass_flow": 1150.0}},
            {"id": "recycle", "source_unit_id": "S1", "sink_unit_id": "M1",
             "stream_properties": {"total_mass_flow": 200.0}},
            {"id": "ethanol", "source_unit_id": "S1", "sink_unit_id": "None", "price": 0.7,
             "stream_properties": {"total_mass_flow": 950.0}},
            {"id": "vent", "source_unit_id": "R1", "sink_unit_id": "None", "stream_properties": {"total_mass_flow": 50.0}},
            {"id": "lost", "source_unit_id": "S1", "sink_unit_id": "X9", "stream_properties": {"total_mass_flow": 1.0}},
            {"id": "idle", "source_unit_id": "None", "sink_unit_id": "None", "stream_properties": {"total_mass_flow": 0.0}},
        ],
        "chemicals": [],
        "utilities": {},
    }


def as_bytes(doc: dict) -> bytes:
    return json.dumps(doc, indent=1).encode("utf-8")


# ── the graph ──────────────────────────────────────────────────────────


def test_a_file_draws_its_units_as_nodes_and_its_streams_as_edges_and_boundaries():
    g = sff.graph(small_doc())
    assert [n.id for n in g.nodes] == ["M1", "R1", "S1", "P1"]
    assert {(e.source, e.sink) for e in g.edges} == {("M1", "R1"), ("R1", "S1"), ("S1", "M1")}
    assert [(f.id, f.unit, f.name, f.massFlow, f.price) for f in g.feeds] == [("feed", "M1", "Corn stover", 1000.0, 0.05)]
    assert [(p.id, p.unit, p.name) for p in g.products] == [("ethanol", "S1", "Ethanol"), ("vent", "R1", None)]
    assert g.dangling == ["lost"], "a stream into a unit the file does not list is counted, never drawn"
    assert "idle" not in {e.id for e in g.edges} | {b.id for b in g.feeds + g.products}


def test_ranks_run_left_to_right_from_the_feeds_and_a_recycle_does_not_push_them_round():
    ranks = {n.id: n.rank for n in sff.graph(small_doc()).nodes}
    assert ranks == {"M1": 0, "R1": 1, "S1": 2, "P1": 0}


def test_a_unit_names_the_class_the_toolkit_says_simulated_it():
    nodes = {n.id: n for n in sff.graph(small_doc()).nodes}
    assert (nodes["M1"].type, nodes["M1"].method) == ("Mixer", "Mixer")
    assert nodes["R1"].method == "SimultaneousSaccharification"
    assert nodes["S1"].method is None


def test_the_inline_style_of_older_files_reads_the_same_and_another_unit_is_left_out():
    doc = small_doc()
    doc.pop("quantity_units_global")
    doc["streams"][0]["stream_properties"]["total_mass_flow"] = {"value": 1000.0, "units": "kg/h"}
    doc["streams"][0]["price"] = {"value": 0.05, "units": "$/kg"}
    doc["streams"][1]["stream_properties"]["total_mass_flow"] = {"value": 2.0, "units": "lb/s"}
    g = sff.graph(doc)
    assert (g.feeds[0].massFlow, g.feeds[0].price) == (1000.0, 0.05)
    assert next(e for e in g.edges if e.id == "s1").massFlow is None, "a flow in another unit is not converted here"


def test_a_title_is_the_files_own_else_its_feedstocks_and_products_else_the_fallback():
    assert sff.title_of(small_doc(process_title="Stover to ethanol"), "x") == "Stover to ethanol"
    assert sff.title_of(small_doc(), "x") == "Corn stover → Ethanol"
    assert sff.title_of({"metadata": {}}, "fallback") == "fallback"


@pytest.mark.parametrize("data, said", [
    (b"\xff\xfe\x00", "not UTF-8"),
    (b"{not json", "not JSON"),
    (b"[1, 2]", "not an SFF flowsheet"),
    (json.dumps({"units": []}).encode(), "not an SFF flowsheet"),
])
def test_what_is_not_an_sff_file_is_refused_in_words(data, said):
    with pytest.raises(sff.SFFRefused, match=said):
        sff.parsed(data, "upload.json")


def test_a_file_past_the_size_an_import_takes_is_refused(monkeypatch):
    monkeypatch.setattr(sff, "MAX_FILE", 10)
    with pytest.raises(sff.SFFRefused, match="larger than"):
        sff.parsed(as_bytes(small_doc()), "big.json")


# ── the manifest of the reference corpus ───────────────────────────────


def test_the_manifest_names_the_reference_corpus_at_the_commit_the_ledger_records():
    m = sff.manifest()
    ledger = tomllib.loads((CORE / "licences.toml").read_text(encoding="utf-8"))["vendored"]["pisces_sff"]
    shipped = json.loads((CORE / "vendor" / "pisces_sff" / "schema" / "sff_schema.json").read_text(encoding="utf-8"))
    assert m.revision == ledger["revision"] and m.schema == ledger["schema"] == shipped["version"]
    assert m.licence == ledger["licence"] == "MIT"
    ids = [f.id for f in m.flowsheets]
    assert len(ids) == len(set(ids)) == 18, "eighteen exported flowsheets at the pinned commit (ADR-003, Evidence)"
    for f in (*m.flowsheets, m.registry):
        assert len(f.sha256) == 64 and int(f.sha256, 16) >= 0 and f.bytes > 0
    assert all(f.path.startswith("pisces_sff/export/exported_flowsheets/") and f.title for f in m.flowsheets)
    assert m.registry.path == "pisces_sff/export/models/all_models.yaml"
    assert m.url(m.flowsheets[0].path).startswith(f"https://raw.githubusercontent.com/sustainability-software-lab/"
                                                  f"pisces-standard-flowsheet-format/{m.revision}/")


def test_the_corpus_is_never_committed():
    assert not (CORE / "vendor" / "pisces_sff" / "export" / "exported_flowsheets").exists()
    assert not (CORE / "vendor" / "pisces_sff" / "export" / "models").exists()
    assert (CORE / "vendor" / "pisces_sff" / "LICENSE").is_file()


# ── a corpus of one small file, served by a stand-in for GitHub ─────────


@pytest.fixture
def corpus(monkeypatch, tmp_path):
    data = as_bytes(small_doc(process_title="The small plant"))
    sha = hashlib.sha256(data).hexdigest()
    one = sff.LibraryFile(id="SF_BST_99", path="pisces_sff/export/exported_flowsheets/x/SF_BST_99.json", sha256=sha,
                          bytes=len(data), title="The small plant", sffVersion="0.2.4")
    reg = sff.LibraryFile(id="all_models", path="pisces_sff/export/models/all_models.yaml",
                          sha256=hashlib.sha256(b"models: {}\n").hexdigest(), bytes=11)
    m = sff.Manifest(repository=sff.REPOSITORY, revision="0" * 40, schema="0.2.4", licence="MIT", registry=reg,
                     flowsheets=(one,))
    monkeypatch.setattr(sff, "manifest", lambda: m)
    monkeypatch.setenv("OPENFERMENT_SFF_LIBRARY", str(tmp_path / "library"))
    served: list[str] = []

    def github(url: str) -> bytes:
        served.append(url)
        return data

    return {"file": one, "data": data, "get": github, "served": served, "manifest": m}


def test_a_reference_file_is_fetched_once_and_kept_when_it_hashes_as_pinned(corpus):
    path = sff.fetch("SF_BST_99", get=corpus["get"])
    assert path.read_bytes() == corpus["data"] and len(corpus["served"]) == 1
    assert sff.fetch("SF_BST_99", get=corpus["get"]) == path and len(corpus["served"]) == 1
    assert [e.fetched for e in sff.library()] == [True]


def test_a_reference_file_that_does_not_hash_as_pinned_is_set_aside_and_refused(corpus):
    with pytest.raises(sff.LibraryUnavailable, match="not the pinned"):
        sff.fetch("SF_BST_99", get=lambda url: b"{}")
    path = sff.local(corpus["file"])
    assert not path.exists() and path.with_name(path.name + ".mismatch").read_bytes() == b"{}"
    assert [e.fetched for e in sff.library()] == [False]


def test_the_library_lists_what_the_manifest_names_and_fetches_nothing(corpus):
    [entry] = sff.library()
    assert (entry.id, entry.title, entry.fetched, entry.sha256) == ("SF_BST_99", "The small plant", False,
                                                                   corpus["file"].sha256)
    assert corpus["served"] == []
    with pytest.raises(sff.FlowsheetNotFound):
        sff.fetch("SF_BST_42", get=corpus["get"])


# ── records, with the worker stood in ───────────────────────────────────


VALIDATION = {"valid": False, "schemaVersion": "0.2.4", "summary": {"error": {"pass": 30, "fail": 1}},
              "findings": [{"checkId": "STR-01", "severity": "error", "status": "fail",
                            "message": "stream lost names a unit the file does not list", "path": "streams[lost]"}]}
COMPLETENESS = {"score": 0.5, "representableScore": 0.6, "categories": {"topology": 0.9}, "criticalities": {},
                "criteria": [{"id": "CMP-TOP-01", "category": "topology", "criticality": "essential", "weight": 4,
                              "representable": True, "status": "scored", "score": 0.9, "message": "m",
                              "missing": []}],
                "sffVersion": "0.2.4", "recipe": {"present": False}, "report": "SFF completeness report"}
TAGS = {"reproducible": {"earned": None, "declared": False, "blocking": ["no reproducibility recipe"]}}


class StandInToolkit:
    """A STAND-IN for the Proforma worker's SFF ops: the toolkit's shapes,
    fixed verdicts, and every op it was asked counted. `sff_export` writes
    the small plant, with the metadata block it was given, where it is told."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, op: str, args: dict):
        self.calls.append((op, args))
        path = Path(args["path"])
        if op == "sff_validate":
            return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **VALIDATION}
        if op == "sff_score":
            return {"path": str(path), "sha256": "x", "completeness": COMPLETENESS, "tags": TAGS}
        if op == "sff_export":
            doc = small_doc(process_title=args.get("title") or "")
            doc["metadata"]["openferment"] = args["metadata"]
            path.write_bytes(as_bytes(doc))
            return {"path": str(path), "sha256": "x", "bytes": path.stat().st_size, "validation": VALIDATION,
                    "completeness": COMPLETENESS, "tags": TAGS, "toolkit": "pisces_sff 0.2.4",
                    "simulator": "BioSTEAM 2.54.0"}
        raise AssertionError(f"the stand-in has no op {op}")

    def ops(self) -> list[str]:
        return [op for op, _ in self.calls]


@pytest.fixture
def toolkit(monkeypatch):
    stand_in = StandInToolkit()
    monkeypatch.setattr(simulator, "call", stand_in)
    return stand_in


def test_an_imported_file_is_checked_drawn_and_kept_with_its_findings(toolkit):
    data = as_bytes(small_doc())
    record = sff.import_sff(data, "small.sff.json", project_id=PROJECT, by="A. Reader")
    assert toolkit.ops() == ["sff_validate", "sff_score"]
    assert (record.origin, record.title, record.libraryId) == ("imported", "Corn stover → Ethanol", None)
    assert record.id == f"sff-{hashlib.sha256(data).hexdigest()[:16]}" and record.sha256 == hashlib.sha256(data).hexdigest()
    assert record.validation.valid is False and record.validation.findings[0].checkId == "STR-01"
    assert record.completeness.score == 0.5 and record.tags["reproducible"].earned is None
    assert (record.units, record.streams, record.sffVersion, record.simulator) == (4, 8, "0.2.4", "BioSTEAM 2.54.0")
    assert record.source == "the file small.sff.json, imported" and record.createdBy == "A. Reader"
    assert len(record.graph.nodes) == 4

    held = sff.get(record.id, project_id=PROJECT)
    assert held.model_dump() == record.model_dump()
    assert sff.document(record.id, project_id=PROJECT).encode("utf-8") == data, "the file is held byte for byte"
    [listed] = sff.listed(project_id=PROJECT)
    assert listed.id == record.id and listed.graph is None


def test_the_same_file_kept_again_is_the_record_already_held(toolkit):
    data = as_bytes(small_doc())
    first = sff.import_sff(data, "a.json", project_id=PROJECT, by="A. Reader")
    again = sff.import_sff(data, "b.json", project_id=PROJECT, by="B. Reader")
    assert again.model_dump() == first.model_dump() and toolkit.ops() == ["sff_validate", "sff_score"]


def test_a_file_that_is_a_reference_flowsheet_is_known_by_its_hash_whichever_door(toolkit, corpus):
    record = sff.import_sff(corpus["data"], "renamed.json", project_id=PROJECT, by="A. Reader")
    assert (record.origin, record.libraryId, record.title) == ("library", "SF_BST_99", "The small plant")
    assert record.source.startswith("the PISCES SFF reference flowsheet SF_BST_99")


def test_a_reference_flowsheet_kept_in_the_project_is_fetched_checked_once_and_drawn(toolkit, corpus):
    record = sff.import_library("SF_BST_99", project_id=PROJECT, by="A. Reader", get=corpus["get"])
    assert record.origin == "library" and len(corpus["served"]) == 1
    assert toolkit.ops() == ["sff_validate", "sff_score"]
    loaded = sff.library_flowsheet("SF_BST_99", get=corpus["get"])
    assert toolkit.ops() == ["sff_validate", "sff_score"], "the verdict on a fetched file is kept beside it"
    assert (loaded.origin, loaded.libraryId, loaded.validation.valid) == ("library", "SF_BST_99", False)
    with pytest.raises(sff.SFFRefused, match="registry"):
        sff.import_library("all_models", project_id=PROJECT, by="A. Reader", get=corpus["get"])


def test_a_runs_export_carries_openferments_block_and_is_kept_as_the_runs(toolkit):
    record = sff.export({"flowsheet": "cornstover_benchmark"}, project_id=PROJECT, run_artifact_id="0123456789abcdef",
                        by="A. Reader", title="Corn stover ethanol")
    [(op, args)] = toolkit.calls
    assert op == "sff_export" and args["flowsheet"] == "cornstover_benchmark" and args["title"] == "Corn stover ethanol"
    assert (record.id, record.origin, record.runArtifactId) == ("run-0123456789abcdef", "run", "0123456789abcdef")
    assert record.title == "Corn stover ethanol" and record.source == "exported from run 0123456789abcdef of cornstover_benchmark"
    held = json.loads(sff.document(record.id, project_id=PROJECT))
    assert held["metadata"]["openferment"] == {"project_id": PROJECT, "run_artifact_id": "0123456789abcdef",
                                               "origin": "run", "flowsheet": "cornstover_benchmark"}
    again = sff.export({"flowsheet": "cornstover_benchmark"}, project_id=PROJECT, run_artifact_id="0123456789abcdef",
                       by="A. Reader")
    assert again.id == record.id and len(sff.listed(project_id=PROJECT)) == 1, "a run exported twice is one record"


def test_an_export_names_its_flowsheet(toolkit):
    with pytest.raises(sff.SFFRefused, match="names the flowsheet"):
        sff.export({}, project_id=PROJECT, run_artifact_id="0123456789abcdef", by="A. Reader")
    assert toolkit.calls == []


def test_a_project_sees_its_own_records_alone(toolkit):
    from sqlalchemy import insert

    from openferment_core import db
    from openferment_core.db import models as t

    async def other() -> None:
        async with db.session() as s:
            await s.execute(insert(t.projects).values(id="other", name="Other", created_by="test"))

    db.run(other())
    record = sff.import_sff(as_bytes(small_doc()), "a.json", project_id=PROJECT, by="A. Reader")
    assert sff.listed(project_id="other") == []
    with pytest.raises(sff.FlowsheetNotFound):
        sff.get(record.id, project_id="other")


# ── the routes ─────────────────────────────────────────────────────────


def test_the_routes_import_list_read_and_serve_the_file(toolkit):
    client = TestClient(app)
    data = as_bytes(small_doc())
    made = client.post("/api/flowsheets/import", files={"file": ("small.json", data, "application/json")},
                       data={"by": "A. Reader"})
    assert made.status_code == 200, made.text
    rid = made.json()["id"]
    assert [r["id"] for r in client.get("/api/flowsheets").json()] == [rid]
    assert client.get("/api/flowsheets").json()[0]["graph"] is None
    assert len(client.get(f"/api/flowsheets/{rid}").json()["graph"]["nodes"]) == 4
    served = client.get(f"/api/flowsheets/{rid}/file")
    assert served.status_code == 200 and served.content == data
    assert client.get("/api/flowsheets/sff-0000000000000000").status_code == 404
    assert client.get("/api/flowsheets/sff-0000000000000000/file").status_code == 404


def test_the_routes_refuse_what_is_not_an_sff_file_and_what_is_not_a_run(toolkit):
    client = TestClient(app)
    bad = client.post("/api/flowsheets/import", files={"file": ("x.json", b"[]", "application/json")},
                      data={"by": "A. Reader"})
    assert bad.status_code == 422 and "not an SFF flowsheet" in bad.json()["detail"]
    missing = client.post("/api/flowsheets/export", json={"artifactId": "0123456789abcdef", "by": "A. Reader"})
    assert missing.status_code == 404
    assert toolkit.calls == []


def test_the_library_route_lists_the_manifest_and_fetches_nothing(corpus):
    body = TestClient(app).get("/api/flowsheets/library").json()
    assert [(e["id"], e["fetched"]) for e in body] == [("SF_BST_99", False)] and corpus["served"] == []


def test_a_run_exports_from_its_basis_alone():
    from openferment_core import proforma
    from openferment_core.models import BasisInput, BasisSource

    def art(tool: str, inputs: list[BasisInput]) -> Artifact:
        return Artifact(id="0123456789abcdef", tool=tool, toolVersion="v", inputs=inputs, output={}, outputHash="h",
                        provenance="computed", createdAt="2026-10-30T00:00:00Z", durationMs=0)

    model = BasisSource(kind="model", id="biorefineries@2.35.1")
    ref = art(proforma.REFERENCE, [BasisInput(name="flowsheet", value="corn_drygrind", unit="", source=model)])
    assert proforma.plant_of(ref) == {"flowsheet": "corn_drygrind"}
    assert proforma.plant_of(art(proforma.BENCHMARK, [])) == {"flowsheet": "cornstover_benchmark"}
    with pytest.raises(proforma.ScenarioRefused, match="not a run of a flowsheet"):
        proforma.plant_of(art("thermo.props", []))
