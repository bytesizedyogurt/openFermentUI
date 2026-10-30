"""Engine runs on the `runs` table (engine/runs.py; execution prompt §7.4;
ADR-004, ADR-003, ADR-006), offline.

The worker is a STAND-IN: test_library's for the library ops (the sugarcane
plant's shapes) and test_sff's for the SFF ops (a small file, fixed
verdicts). A run is kept with each input a quantity with its origin, its
artifact, its versions and the SFF file it wrote; the same basis asked again
is answered from its row; a plant's refusal is kept as a receipt and
answered from it; a request the runner refuses keeps nothing; a file that
cannot be written leaves the run standing with the words why; a model's
estimate reaches a run, which is `assumed`; a replay holds a run to the
precision its basis states. The real worker is test_runs_sim.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts
from openferment_core.api import app
from openferment_core.engine import library, runs, sff, simulator
from openferment_core.models import BasisInput, BasisSource, ReplayTolerance

from test_library import StandInWorker, over
from test_sff import StandInToolkit

MODEL = "claude-opus-5-5"


class StandIn:
    """The library ops to test_library's stand-in, the SFF ops to test_sff's;
    every op asked, in order."""

    def __init__(self, refuse: str | None = None):
        self.library, self.toolkit = StandInWorker(refuse=refuse), StandInToolkit()
        self.calls: list[str] = []

    def __call__(self, op: str, args: dict):
        self.calls.append(op)
        return (self.toolkit if op.startswith("sff_") else self.library)(op, args)


@pytest.fixture
def worker(monkeypatch):
    stand_in = StandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


def test_a_run_is_kept_with_its_inputs_origins_its_artifact_its_versions_and_its_sff_file(worker):
    rep = runs.run("sugarcane", None, [over("stream.sugarcane.price", 0.05, by="Ada Moreno")], by="Ada Moreno")
    run = rep.run
    assert worker.calls == ["library_parameters", "library_run", "sff_export"]
    assert (run.status, run.provenance, run.plant, run.configuration) == ("done", "assumed", "sugarcane", None)
    assert run.id == run.artifactId == rep.artifact.id and run.tool == library.LIBRARY_RUN and run.by == "Ada Moreno"
    origins = {i.name: i.quantity.origin.kind for i in run.inputs}
    assert origins["plant"] == origins["simulator"] == "library-default"
    assert origins["precision"] == "convention" and origins["stream.sugarcane.price"] == "person-assumption"
    price = next(i.quantity for i in run.inputs if i.name == "stream.sugarcane.price")
    assert (price.value, price.unit, price.origin.by, price.origin.at) == (0.05, "USD/kg", "Ada Moreno", "2026-10-30")
    assert run.versions == {"biosteam": library._installed("biosteam"), "thermosteam": library._installed("thermosteam"),
                            "biorefineries": library._installed("biorefineries")}
    assert run.outputs["price"] == {"priced": True}
    assert run.sff.recordId == f"run-{run.id}" and run.sff.valid is False and run.sff.score == 0.5 and run.sff.tags == []
    assert rep.flowsheet.origin == "run" and rep.flowsheet.runArtifactId == run.id and run.sffRefused is None
    assert runs.listed() == [run]
    again = runs.report(run.id)
    assert again.run == run and again.artifact == rep.artifact and again.flowsheet.id == rep.flowsheet.id


def test_the_same_basis_asked_again_is_answered_from_its_row(worker):
    first = runs.run("sugarcane", by="Ada Moreno")
    asked = len(worker.calls)
    again = runs.run("sugarcane", by="Ada Moreno")
    assert again.run == first.run and len(worker.calls) == asked
    assert len(runs.listed()) == 1


def test_a_plant_that_refuses_is_kept_as_a_receipt_and_answered_from_it(monkeypatch):
    said = "infeasible here (BioSTEAM's InfeasibleRegion): M207 NH3 over 100 %"
    stand_in = StandIn(refuse=said)
    monkeypatch.setattr(simulator, "call", stand_in)
    with pytest.raises(library.LibraryRefused, match="InfeasibleRegion"):
        runs.run("sugarcane", by="Ada Moreno")
    (receipt,) = runs.listed()
    assert (receipt.status, receipt.refused, receipt.artifactId, receipt.provenance, receipt.sff) == (
        "refused", said, None, None, None)
    assert {i.name for i in receipt.inputs} >= {"plant", "simulator", "precision"}
    asked = len(stand_in.calls)
    with pytest.raises(library.LibraryRefused, match="M207"):
        runs.run("sugarcane", by="Ada Moreno")
    assert len(stand_in.calls) == asked, "a receipt answers again without building the plant"
    rep = runs.report(receipt.id)
    assert rep.artifact is None and rep.flowsheet is None


def test_a_request_the_runner_refuses_keeps_nothing(worker):
    with pytest.raises(library.LibraryRefused, match="no parameter"):
        runs.run("sugarcane", None, [over("stream.nosuch.price", 1.0)], by="Ada Moreno")
    assert runs.listed() == []


def test_a_run_whose_file_cannot_be_written_stands_and_says_why(worker, monkeypatch):
    def refuse(*a, **k):
        raise sff.SFFRefused("the toolkit could not write this plant")

    monkeypatch.setattr(sff, "export", refuse)
    rep = runs.run("sugarcane", by="Ada Moreno")
    assert rep.run.status == "done" and rep.run.sff is None and rep.flowsheet is None
    assert rep.run.sffRefused == "the toolkit could not write this plant"


def test_a_models_estimate_reaches_a_run_and_the_run_is_assumed(worker):
    estimate = over("stream.sugarcane.price", 0.05, by=MODEL, origin="model-estimate")
    rep = runs.run("sugarcane", None, [estimate], by="Ada Moreno")
    price = next(i.quantity for i in rep.run.inputs if i.name == "stream.sugarcane.price")
    assert (price.origin.kind, price.origin.by) == ("model-estimate", MODEL)
    assert rep.run.provenance == rep.artifact.provenance == "assumed"


def test_a_replay_holds_a_run_to_the_precision_its_basis_states(monkeypatch):
    inputs = [BasisInput(name="x", value=1.0, unit="", source=BasisSource(kind="convention", note="n"))]
    state = {"price": 0.6588136420, "tiny": 0.0, "name": "ethanol"}
    tol = ReplayTolerance(rtol=1e-9, atol=1e-8, why="ten significant digits")
    monkeypatch.setitem(artifacts._REGISTRY, "test.tolerant", artifacts.Registered(
        "test.tolerant", "1", lambda i, seed: dict(state), tolerance_of=lambda i: tol))
    art = artifacts.compute("test.tolerant", inputs)
    assert artifacts.replay(art.id).identical and artifacts.replay(art.id).withinTolerance
    state.update(price=0.6588136421, tiny=1e-12)
    near = artifacts.replay(art.id)
    assert not near.identical and near.withinTolerance and near.tolerance == tol
    assert {d.path for d in near.differences} == {"price", "tiny"}
    state.update(price=0.65882)
    assert not artifacts.replay(art.id).withinTolerance
    state.update(price=0.6588136420, tiny=0.0, name="water")
    assert not artifacts.replay(art.id).withinTolerance, "words are held to be the same"


def test_a_library_runs_tolerance_is_one_unit_in_its_last_kept_digit(worker):
    inputs = library.run_inputs("sugarcane", None, [])
    tol = library.tolerance(inputs)
    assert tol.rtol == pytest.approx(1e-9) and tol.atol == library.ALLCLOSE_ATOL and "10 significant digits" in tol.why


def test_a_tool_that_states_no_precision_replays_identical_or_not_at_all(monkeypatch):
    inputs = [BasisInput(name="x", value=1.0, unit="", source=BasisSource(kind="convention", note="n"))]
    state = {"price": 1.0}
    monkeypatch.setitem(artifacts._REGISTRY, "test.exact", artifacts.Registered(
        "test.exact", "1", lambda i, seed: dict(state)))
    art = artifacts.compute("test.exact", inputs)
    state.update(price=1.0 + 1e-15)
    r = artifacts.replay(art.id)
    assert (r.identical, r.withinTolerance, r.tolerance) == (False, False, None)


def test_the_routes_run_list_report_and_refuse(worker):
    client = TestClient(app)
    ran = client.post("/api/library/sugarcane/run", json={
        "overrides": [over("stream.sugarcane.price", 0.05).model_dump()], "by": "Ada Moreno"})
    assert ran.status_code == 200
    body = ran.json()
    assert body["run"]["status"] == "done" and body["run"]["provenance"] == "assumed"
    assert body["artifact"]["tool"] == "library.run" and body["flowsheet"]["origin"] == "run"
    listed = client.get("/api/runs").json()
    assert [r["id"] for r in listed] == [body["run"]["id"]]
    report = client.get(f"/api/runs/{body['run']['id']}").json()
    assert report["run"] == body["run"] and report["flowsheet"]["id"] == f"run-{body['run']['id']}"
    assert client.get("/api/runs/0000000000000000").status_code == 404
    refused = client.post("/api/library/sugarcane/run", json={"overrides": [over("stream.nosuch.price", 1.0).model_dump()]})
    assert refused.status_code == 422 and "no parameter" in refused.json()["detail"]
