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
precision its basis states. A run's outputs.values are the numbers its
artifact states a unit for, each a quantity of the artifact; `keep_run` keeps
any engine's computation, or its receipt, in the one shape, and says so on
the event stream; it answers a run kept already as it was first kept, and
refuses in words, keeping nothing, a call outside its rules or an engine
name nothing registers; a run's parameters are a library run's alone. The
real worker is test_runs_sim.py.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from conftest import TEST_PROJECT
from openferment_core import artifacts, events, llm
from openferment_core.api import app
from openferment_core.engine import library, runs, sff, simulator
from openferment_core.models import BasisInput, BasisSource, ReplayTolerance

from test_library import SUGARCANE_PARAMETERS, StandInWorker, over
from test_sff import StandInToolkit

# The model the service calls first: the one whose estimates these are.
MODEL = llm.DEFAULT_PRIMARY


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


def test_a_runs_parameters_read_as_the_panel_reads_them_each_value_the_runs_own(worker):
    estimate = over("stream.sugarcane.F_mass", 300_000.0, by=MODEL, origin="model-estimate", note="a typical mill")
    rep = runs.run("sugarcane", None, [over("stream.sugarcane.price", 0.05, by="Ada Moreno", note="a quote"), estimate],
                   by="Ada Moreno")
    panel = rep.parameters
    assert (panel.scope, panel.kind, panel.waiting) == ("library:sugarcane", "library", [])
    assert [s.key for s in panel.specs] == [p["key"] for p in SUGARCANE_PARAMETERS]
    values = {v.key: v for v in panel.values}
    price, flow, vessel = (values[k] for k in ("stream.sugarcane.price", "stream.sugarcane.F_mass", "unit.T202.vessel_type"))
    assert (price.value, price.origin, price.overriddenBy, price.source.kind) == (0.05, "assumption", "Ada Moreno", "assumption")
    assert (flow.value, flow.origin, flow.overriddenBy) == (300_000.0, "model-estimate", MODEL)
    assert (vessel.value, vessel.origin, vessel.libraryDefault) == ("Field erected", "library-default", "Field erected")
    assert vessel.source.id == "biorefineries.sugarcane@" + library._installed("biorefineries")
    assert runs.report(rep.run.id).parameters == panel


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
    assert body["run"]["engine"] == "biosteam"
    assert [r["id"] for r in client.get("/api/runs", params={"engine": "biosteam"}).json()] == [body["run"]["id"]]
    assert client.get("/api/runs", params={"engine": "an-engine-that-ran-nothing"}).json() == []
    report = client.get(f"/api/runs/{body['run']['id']}").json()
    assert report["run"] == body["run"] and report["flowsheet"]["id"] == f"run-{body['run']['id']}"
    assert report["parameters"]["kind"] == "library" and report["parameters"] == body["parameters"]
    assert client.get("/api/runs/0000000000000000").status_code == 404
    refused = client.post("/api/library/sugarcane/run", json={"overrides": [over("stream.nosuch.price", 1.0).model_dump()]})
    assert refused.status_code == 422 and "no parameter" in refused.json()["detail"]


# ── one shape for every run (alpha 2.2 stage C, D3) ────────────────────


class ValuedStandIn(StandIn):
    """test_runs' stand-in, its run answering a price block and a
    flowsheet's outputs of placeholders in a placeholder unit: numbers and
    words the artifact states a unit for, and one of each it states none for."""

    def __call__(self, op: str, args: dict):
        out = super().__call__(op, args)
        if op == "library_run":
            out = {**out, "price": {"priced": True, "a-number": 1.5, "a-word": "placeholder", "unstated": 2.5,
                                    "units": {"a-number": "placeholder-unit", "a-word": "placeholder-unit"}},
                   "outputs": {"an-output": 3.5, "a-label": "placeholder", "unstated": 4.5},
                   "outputUnits": {"an-output": "placeholder-unit", "a-label": ""}}
        return out


def test_a_library_runs_outputs_values_are_the_numbers_its_artifact_states_a_unit_for(monkeypatch):
    monkeypatch.setattr(simulator, "call", ValuedStandIn())
    monkeypatch.setattr(library, "_PARAMETERS", {})
    rep = runs.run("sugarcane", by="Ada Moreno")
    run, art = rep.run, rep.artifact
    origin = {"kind": "artifact", "ref": art.id}
    assert run.outputs["values"] == [
        {"name": "price.a-number", "quantity": {"value": 1.5, "unit": "placeholder-unit", "origin": origin}},
        {"name": "outputs.an-output", "quantity": {"value": 3.5, "unit": "placeholder-unit", "origin": origin}},
        {"name": "outputs.a-label", "quantity": {"value": "placeholder", "unit": "", "origin": origin}}]
    # What a library run kept before, as it was kept.
    assert run.outputs["price"] == art.output["price"] and run.outputs["outputs"] == art.output["outputs"]
    assert run.outputs["regression"]["of"] == len(art.output["checks"])
    assert runs.values_of(art) == run.outputs["values"] and runs.report(run.id).run == run


def test_keep_run_keeps_any_engines_computation_or_its_receipt_in_one_shape_and_says_so(monkeypatch):
    def basis(value: float) -> list[BasisInput]:
        return [BasisInput(name="a-value", value=value, unit="placeholder-unit",
                           source=BasisSource(kind="convention", note="a placeholder"))]

    monkeypatch.setitem(artifacts._REGISTRY, "test.kept", artifacts.Registered(
        "test.kept", "1", lambda i, seed: {"answer": 2.5}))
    art = artifacts.compute("test.kept", basis(1.0))
    engine = SimpleNamespace(name="placeholder-engine", version=lambda: {"placeholder-distribution": "0.0"})
    start = events.newest()
    rep = runs.keep_run(engine, "a-thing", None, tool="test.kept", version="1", basis=basis(1.0), by=" Ada Moreno ",
                        art=art, sff_refused="the placeholder engine has no plant")
    run = rep.run
    assert (run.id, run.engine, run.plant, run.configuration, run.status, run.by) == (
        art.id, "placeholder-engine", "a-thing", None, "done", "Ada Moreno")
    assert run.versions == {"placeholder-distribution": "0.0"}, "a basis that names no simulator: the engine's own"
    assert run.outputs == {"values": []} and run.sffRefused == "the placeholder engine has no plant"
    assert [i.quantity.origin.kind for i in run.inputs] == ["convention"] and rep.parameters is None
    assert runs.listed("placeholder-engine") == [run] and runs.report(run.id).run == run
    (done,) = events.recent(TEST_PROJECT, start)
    assert (done.type, done.data["status"], done.data["engine"], done.data["artifactId"]) == (
        "job.done", "done", "placeholder-engine", art.id)
    # A refusal inside the computation is kept as its receipt, under the id of its basis.
    start = events.newest()
    receipt = runs.keep_run(engine, "a-thing", None, tool="test.kept", version="1", basis=basis(2.0),
                            refused="the placeholder engine refuses these values, in these words").run
    assert receipt.id == artifacts.artifact_id("test.kept", "1", basis(2.0)) and receipt.by == "this browser"
    assert (receipt.status, receipt.artifactId, receipt.provenance, receipt.outputs) == ("refused", None, None, {})
    (failed,) = events.recent(TEST_PROJECT, start)
    assert (failed.type, failed.data["status"], failed.data["words"]) == ("job.failed", "refused", receipt.refused)
    with pytest.raises(ValueError, match="one of the two"):
        runs.keep_run(engine, "a-thing", None, tool="test.kept", version="1", basis=basis(3.0))
    with pytest.raises(ValueError, match="one of the two"):
        runs.keep_run(engine, "a-thing", None, tool="test.kept", version="1", basis=basis(1.0), art=art, refused="words")
    with pytest.raises(ValueError, match="is no computation of run"):
        runs.keep_run(engine, "a-thing", None, tool="test.kept", version="1", basis=basis(3.0), art=art)
    assert {r.id for r in runs.listed()} == {run.id, receipt.id}


def test_a_runs_parameters_are_a_library_runs_alone(monkeypatch):
    """parameters_of reads a library run alone: a run of another tool whose
    output holds parameters in a shape of its own answers none."""
    inputs = [BasisInput(name="a-value", value=1.0, unit="placeholder-unit",
                         source=BasisSource(kind="convention", note="a placeholder"))]
    monkeypatch.setitem(artifacts._REGISTRY, "test.parameters", artifacts.Registered(
        "test.parameters", "1", lambda i, seed: {"parameters": [{"unit": "U1", "values": []}]}))
    art = artifacts.compute("test.parameters", inputs)
    engine = SimpleNamespace(name="placeholder-engine", version=lambda: {})
    rep = runs.keep_run(engine, "a-thing", None, tool="test.parameters", version="1", basis=inputs, art=art,
                        sff_refused="no plant")
    assert rep.parameters is None and runs.report(rep.run.id).parameters is None
    assert rep.run.versions == {}, "an engine whose version() names nothing: the basis names none either"


def _kept_basis(value: float) -> list[BasisInput]:
    return [BasisInput(name="a-value", value=value, unit="placeholder-unit",
                       source=BasisSource(kind="convention", note="a placeholder"))]


@pytest.fixture
def kept_tool(monkeypatch):
    """A tool of the test's own, computing a placeholder from its basis, and an engine that names itself."""
    monkeypatch.setitem(artifacts._REGISTRY, "test.kept", artifacts.Registered(
        "test.kept", "1", lambda i, seed: {"answer": 2.5}))
    return SimpleNamespace(name="placeholder-engine", version=lambda: {"placeholder-distribution": "0.0"})


def test_keep_run_answers_a_run_kept_already_as_it_was_first_kept(kept_tool):
    """The same run kept twice is one row: the second keeper is answered the
    first keeper's row, its `by` and `at` the first asker's, and nothing is
    written or said on the event stream. A receipt kept twice is the first
    receipt."""
    art = artifacts.compute("test.kept", _kept_basis(1.0))
    first = runs.keep_run(kept_tool, "a-thing", None, tool="test.kept", version="1", basis=_kept_basis(1.0),
                          by="First Person", art=art, sff_refused="the placeholder engine has no plant")
    start = events.newest()
    again = runs.keep_run(kept_tool, "a-thing", None, tool="test.kept", version="1", basis=_kept_basis(1.0),
                          by="Second Person", art=art, sff_refused="other words", scenario_id="a-scenario")
    assert again.run == first.run and again.run.by == "First Person" and again.run.scenarioId is None
    assert again.run.sffRefused == "the placeholder engine has no plant"
    assert events.recent(TEST_PROJECT, start) == [], "the row as first kept: no second job.done"
    receipt = runs.keep_run(kept_tool, "a-thing", None, tool="test.kept", version="1", basis=_kept_basis(2.0),
                            by="First Person", refused="the placeholder engine refuses these values").run
    start = events.newest()
    held = runs.keep_run(kept_tool, "a-thing", None, tool="test.kept", version="1", basis=_kept_basis(2.0),
                         by="Second Person", refused="other words").run
    assert held == receipt and held.refused == "the placeholder engine refuses these values"
    assert events.recent(TEST_PROJECT, start) == []
    assert [(r.id, r.by) for r in runs.listed()] == [(receipt.id, "First Person"), (first.run.id, "First Person")]


def test_keep_run_refuses_a_call_outside_its_rules_and_keeps_nothing(kept_tool):
    """A run that computed names its SFF record or the words for why none
    was written, one of the two; a receipt names neither; an engine given by
    name is one registered here. Each refusal keeps nothing."""
    art = artifacts.compute("test.kept", _kept_basis(1.0))
    asked = dict(tool="test.kept", version="1", basis=_kept_basis(1.0))
    with pytest.raises(ValueError, match="its SFF record, or with the words for why its engine wrote none"):
        runs.keep_run(kept_tool, "a-thing", None, **asked, art=art)
    flowsheet = SimpleNamespace(id="run-placeholder")
    with pytest.raises(ValueError, match="its SFF record, or with the words for why its engine wrote none"):
        runs.keep_run(kept_tool, "a-thing", None, **asked, art=art, flowsheet=flowsheet, sff_refused="words")
    with pytest.raises(ValueError, match="a receipt keeps no SFF file"):
        runs.keep_run(kept_tool, "a-thing", None, **asked, refused="words", sff_refused="words")
    with pytest.raises(ValueError, match="no engine named 'placeholder-engine' is registered here"):
        runs.keep_run("placeholder-engine", "a-thing", None, **asked, art=art, sff_refused="words")
    assert runs.listed() == []
