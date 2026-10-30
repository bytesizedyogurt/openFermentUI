"""SFF with the real toolkit in the real worker (ADR-003; the stage 4 gate).

Marked `sim`: the Proforma worker loads BioSTEAM and the vendored toolkit.
A reference run and a shelf run are each exported as SFF, validated and
scored by the toolkit, and describe the base case their run read; the
toolkit checks a file on its own as it checked the export; and reference
flowsheets fetched from the pinned commit (once, from GitHub, into a
directory of this test session's own) import and draw, the one that fails
validation under the schema the toolkit ships kept with its findings.
"""
from __future__ import annotations

import json

import pytest

from openferment_core import proforma
from openferment_core.engine import sff
from openferment_core.models import InputAssumption

pytestmark = pytest.mark.sim

PROJECT = "test-project"
ETHANOL = {"feed_glucose_conc": 100.0, "titre": 45.0, "yield": 0.45, "productivity": 2.0, "plant_scale": 100000.0,
           "glucose_price": 0.4}


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()


@pytest.fixture(scope="module")
def library_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("sff-library")


@pytest.fixture
def library(library_dir, monkeypatch):
    monkeypatch.setenv("OPENFERMENT_SFF_LIBRARY", str(library_dir))
    return library_dir


def _row(art, stream_id: str) -> dict:
    return next(s for s in art.output["streams"] if s["id"] == stream_id)


def test_a_reference_runs_export_validates_scores_and_is_the_base_case_its_run_read(warm):
    art = proforma.run_reference("cornstover_benchmark")
    record = sff.export(proforma.plant_of(art), project_id=PROJECT, run_artifact_id=art.id, by="openFerment test")
    assert record.validation.valid, record.validation.findings
    assert record.validation.schemaVersion == "0.2.4" and record.sffVersion == "0.2.4"
    assert not [f for f in record.validation.findings if f.severity == "error" and f.status == "fail"]
    c = record.completeness
    assert 0.5 < c.score < 1 and c.representableScore >= c.score and c.criteria and c.report.startswith("SFF completeness")
    assert set(record.tags) >= {"exported-from-simulator", "reproducible"} and record.tags["reproducible"].earned is None
    assert record.simulator.startswith("BioSTEAM ") and record.origin == "run" and record.runArtifactId == art.id

    g = record.graph
    assert len(g.nodes) == record.units and g.dangling == []
    assert ("cornstover", "Corn stover") in [(f.id, f.name) for f in g.feeds]
    [ethanol] = [p for p in g.products if p.id == "ethanol"]
    assert ethanol.name == "Ethanol"
    # The file describes the plant the run read: the product's flow is the
    # run's own row, to the ten digits the run keeps.
    assert ethanol.massFlow == pytest.approx(_row(art, "ethanol")["massFlow"], rel=1e-9)

    held = json.loads(sff.document(record.id, project_id=PROJECT))
    assert held["metadata"]["openferment"] == {"project_id": PROJECT, "run_artifact_id": art.id, "origin": "run",
                                               "flowsheet": "cornstover_benchmark"}


def test_a_shelf_runs_export_is_its_base_case_with_its_solved_price_on_the_product(warm):
    a = [InputAssumption(key=k, value=v, low=v, high=v, by="openFerment test fixture", at="2026-10-30")
         for k, v in ETHANOL.items()]
    art = proforma.run_flowsheet("ethanol_glucose_v0", a, samples=4, seed=1)
    assert art.output["baseInfeasible"] is None
    record = sff.export(proforma.plant_of(art), project_id=PROJECT, run_artifact_id=art.id, by="openFerment test",
                        title="Glucose to ethanol, a shelf run")
    assert record.validation.valid, record.validation.findings
    assert record.title == "Glucose to ethanol, a shelf run" and 0 < record.completeness.score < 1
    [product] = [p for p in record.graph.products if p.id == "ethanol"]
    run_row = _row(art, "ethanol")
    assert product.massFlow == pytest.approx(run_row["massFlow"], rel=1e-9)
    assert product.price == pytest.approx(art.output["basePrice"], rel=1e-9), "the price the run solved"


def test_the_worker_checks_a_file_on_its_own_as_it_checked_the_export(warm, tmp_path):
    art = proforma.run_reference("cornstover_benchmark")
    record = sff.export(proforma.plant_of(art), project_id=PROJECT, run_artifact_id=art.id, by="openFerment test")
    path = tmp_path / "held.json"
    path.write_text(sff.document(record.id, project_id=PROJECT), encoding="utf-8")
    v = proforma.call("sff_validate", {"path": str(path)})
    s = proforma.call("sff_score", {"path": str(path)})
    assert v["sha256"] == record.sha256 and v["valid"] == record.validation.valid
    assert v["summary"] == record.validation.summary
    assert s["completeness"]["score"] == pytest.approx(record.completeness.score, rel=1e-12)
    with pytest.raises(Exception, match="no SFF file"):
        proforma.call("sff_validate", {"path": str(tmp_path / "absent.json")})


def test_a_reference_flowsheet_from_the_pinned_commit_imports_and_draws(warm, library):
    record = sff.import_library("SF_BST_01", project_id=PROJECT, by="openFerment test")
    m = sff.manifest()
    assert (record.origin, record.libraryId, record.sha256) == ("library", "SF_BST_01", m.file("SF_BST_01").sha256)
    assert record.validation.valid and record.sffVersion == "0.2.3"
    assert record.title == "Corn → Ethanol + Crude oil + DDGS"
    g = record.graph
    assert (len(g.nodes), len(g.edges), g.dangling) == (71, 78, [])
    assert {f.name for f in g.feeds if f.name} == {"Corn"}
    assert {p.name for p in g.products if p.name} == {"Ethanol", "DDGS", "Crude_oil"}
    assert max(n.rank for n in g.nodes) > 10, "drawn left to right, not in one column"
    assert [r.id for r in sff.listed(project_id=PROJECT)] == [record.id]
    assert next(e for e in sff.library() if e.id == "SF_BST_01").fetched


def test_a_reference_flowsheet_older_than_the_schema_is_kept_with_its_findings_and_drawn(warm, library):
    record = sff.import_library("SF_BST_15", project_id=PROJECT, by="openFerment test")
    assert record.sffVersion == "0.0.3" and record.title == "Sugarcane → Ethanol"
    assert record.validation.valid is False and record.validation.schemaVersion == "0.2.4"
    assert "SCHEMA" in {f.checkId for f in record.validation.findings if f.status == "fail"}
    assert record.completeness.score is not None and len(record.graph.nodes) == 54
