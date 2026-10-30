"""The seam: the broth that leaves fermOS is the stream that enters pureOS
(OF-BLD-020 §6.2, D10).

Offline (scipy, no BioSTEAM; a stand-in Proforma worker answers the
stream defaults as test_train's does):

- `fermos.harvest` reads a kept simulation's broth from the series its
  artifact keeps, never integrating again: at the simulation's own harvest
  hour it is the end state, by component; at a person's hour it reads that
  hour's kept point, or the nearest one and says so; an hour outside the
  simulated span is refused in words; a simulation that keeps no product in
  the broth refuses to be an inlet in words naming what it lacks.
- A train's simulation inlet reads its composition through the same read:
  at harvest it equals the simulation's end state within rounding; a
  person's hour reads that hour's state and the basis names the person;
  `inlet source` says which source was read.
- A run-stream inlet that names a scenario reads that scenario's newest run
  and the stream its flowsheet names on the shelf as its broth; a flowsheet
  that names none is refused in words naming the streams the run holds; a
  scenario with no run is refused; the shelf's broth streams are the ids
  each flowsheet file gives its fermenter's outlet.
- `GET /api/fermos/harvest` answers the read, 404 for a simulation not on
  file, 409 for one damaged on disk and 422 in words for the refusals.

Marked `sim` (the real Proforma worker): a scenario's newest run of the
glucose-to-ethanol flowsheet gives a train the stream its shelf entry names
as the broth, the fermenter's own outlet, and the catalogue's ethanol train
on it gives the package's own purity, as on the beer named by id.

Every STAND-IN here is an `assumption` of this test, typed under the
fixture's name and noted STAND-IN; none is a measurement, a published value
or a result, and only what the code does with it is asserted.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, fermos, kinetics, pureos
from openferment_core.flowsheets import shelf
from openferment_core.models import Artifact, TrainSpec
from openferment_core.pureos import train_spec
from standins import plant_artifact, plant_damaged
from test_builder import STREAMS, _keep
from test_train import (  # noqa: F401 (the fixtures, by name)
    BY,
    no_pool,
    real,
    real_simulation,
    spec_of,
    store,
    typed,
    warm,
    worker,
)

PKG = Path(__file__).resolve().parent.parent / "openferment_core"
# How the program's chemicals read a yeast simulation's states (train_spec).
CHEMICAL_OF = {"X": "Yeast", "S": "Glucose", "P": "Ethanol"}
# Within rounding: the kept series' last point and the end state the
# artifact keeps are the solver's dense output and its last step at one hour.
ROUNDING = 1e-9


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


def sim_inlet(sim_id: str, **params) -> TrainSpec:
    """A train whose inlet is the simulation's harvest, its broth flow a
    STAND-IN typed under the fixture's name."""
    return spec_of(inlet={"kind": "simulation", "ref": sim_id, "params": {"broth_flow": typed(1.0), **params}})


def by_name(basis) -> dict:
    return {b.name: b for b in basis}


def states_of(h) -> dict[str, float]:
    return {x.state: x.value for x in h.states}


def keep_copy(art: Artifact, aid: str, **output) -> Artifact:
    """A copy of a kept simulation written by hand under another id, its
    output changed as given (a STAND-IN artifact for a refusal)."""
    return plant_artifact(art.model_copy(update={"id": aid, "output": {**art.output, **output}}))


# ── fermos.harvest: read from the kept series, never integrated again ──


def test_the_harvest_is_the_end_state_read_from_the_kept_series_and_nothing_is_integrated_again(store, monkeypatch):
    sim = real_simulation()
    art = artifacts.get(sim.artifactId)
    assert sim.sugarRunsOutH == sim.harvestH == sim.end["t"]

    def never(*_a, **_k):
        raise AssertionError("the harvest integrated the simulation again")

    monkeypatch.setattr(fermos, "_trajectory", never)
    monkeypatch.setattr(kinetics, "_integrate", never)
    kept_before = sorted(a.id for a in artifacts.all_artifacts())
    h = fermos.harvest(sim.artifactId)
    assert sorted(a.id for a in artifacts.all_artifacts()) == kept_before  # nothing kept
    assert h.hourSource == fermos.HARVEST_HOUR and h.how == "the hour its sugar runs out"
    assert h.asked == h.hour == h.harvestH == sim.harvestH and h.exact and h.runEndH == sim.end["t"]
    assert [x.state for x in h.states] == ["X", "S", "P"]
    assert all(x.unit == art.output["units"][x.state] == "g L⁻¹" for x in h.states)
    for state, value in states_of(h).items():
        assert value == pytest.approx(sim.end[state], rel=ROUNDING, abs=ROUNDING), state
    assert states_of(h)["P"] == pytest.approx(sim.finalTitre, rel=ROUNDING)
    assert h.absent == kinetics.ABSENT and h.provenance == art.provenance
    assert (h.strain, h.product, h.sugar) == (art.output["strain"], "ethanol", "glucose")


def test_a_persons_hour_reads_that_hours_kept_point_or_the_nearest_and_says_so(store):
    sim = real_simulation()
    t = sim.series["t"]
    k = len(t) // 2
    at = fermos.harvest(sim.artifactId, t[k])
    assert at.hourSource == fermos.PERSONS_HOUR and at.how == "an hour a person named"
    assert at.exact and at.hour == t[k] and "the kept point at" in at.read
    assert states_of(at) == {s: sim.series[s][k] for s in ("X", "S", "P")}
    # Between two kept points: the nearer one, said so, nothing interpolated.
    between = t[k] + (t[k + 1] - t[k]) / 4
    near = fermos.harvest(sim.artifactId, between)
    assert not near.exact and near.asked == between and near.hour == t[k]
    assert "the nearest kept point" in near.read and "nothing is integrated again" in near.read
    assert states_of(near) == states_of(at)


@pytest.mark.parametrize("where", ["after", "before"])
def test_an_hour_outside_the_simulated_span_is_refused_in_words(store, where):
    sim = real_simulation()
    hour = sim.end["t"] * 2 if where == "after" else -sim.end["t"]
    with pytest.raises(fermos.SimulationRefused, match=rf"lies outside simulation {sim.artifactId}, which keeps its "
                                                       r"broth from 0 to .* h"):
        fermos.harvest(sim.artifactId, hour)
    with pytest.raises(fermos.SimulationRefused, match="not a number of hours"):
        fermos.harvest(sim.artifactId, float("nan"))


def test_a_simulation_with_no_product_series_refuses_to_be_an_inlet_naming_what_it_lacks(store, worker):
    sim = real_simulation()
    art = artifacts.get(sim.artifactId)
    series = {k: v for k, v in art.output["series"].items() if k != "P"}
    bare = keep_copy(art, "c" * 16, series=series)
    with pytest.raises(fermos.SimulationRefused) as e:
        fermos.harvest(bare.id)
    words = str(e.value)
    assert f"simulation {bare.id} keeps no product series (P, the product in the broth)" in words
    assert "its family batch_v1 has one, and the artifact keeps no series of it" in words
    assert "it keeps X, S, so its broth is no train's inlet" in words
    with pytest.raises(pureos.TrainRefused, match=r"the inlet: simulation c{16} keeps no product series \(P"):
        pureos.inlet_stream(sim_inlet(bare.id))
    # A family fermOS does not have says so, and names what the artifact keeps.
    other = keep_copy(art, "d" * 16, family="nowhere_v1", series=series)
    with pytest.raises(fermos.SimulationRefused, match=r"its family nowhere_v1 is none fermOS has; it keeps S, X, so"):
        fermos.harvest(other.id)


def test_a_series_that_cannot_be_read_and_another_artifact_are_refused_in_words(store):
    sim = real_simulation()
    art = artifacts.get(sim.artifactId)
    short = keep_copy(art, "e" * 16, series={**art.output["series"], "S": art.output["series"]["S"][:3]})
    with pytest.raises(fermos.SimulationRefused, match="series of S cannot be read on its"):
        fermos.harvest(short.id)
    no_hours = keep_copy(art, "f" * 16, series={"X": [1.0], "P": [1.0]})
    with pytest.raises(fermos.SimulationRefused, match="keeps no series of hours"):
        fermos.harvest(no_hours.id)
    other = plant_artifact(art.model_copy(update={"id": "a" * 16, "tool": "kinetic_fit"}))
    with pytest.raises(fermos.SimulationRefused, match="is a kinetic_fit, not a simulation fermOS keeps"):
        fermos.harvest(other.id)


# ── the simulation inlet reads through the same read ───────────────────


def test_the_inlet_at_harvest_equals_the_simulations_end_state_by_component(store, worker):
    sim = real_simulation()
    inlet = pureos.inlet_stream(sim_inlet(sim.artifactId))
    assert inlet.read.harvestHour == sim.harvestH
    want = {CHEMICAL_OF[s]: sim.end[s] for s in ("X", "S", "P")}
    assert set(inlet.read.concentrations) == set(want)
    for chem, value in want.items():
        assert inlet.read.concentrations[chem] == pytest.approx(value, rel=ROUNDING, abs=ROUNDING), chem
    b = by_name(inlet.basis)
    assert b["inlet source"].value == fermos.HARVEST_HOUR and b["inlet source"].source.kind == "convention"
    assert f"the broth of simulation {sim.artifactId} at its own harvest hour" in b["inlet source"].source.note
    assert "the hour its sugar runs out" in b["inlet source"].source.note
    assert b["inlet.harvest_hour"].source.kind == "artifact" and b["inlet.harvest_hour"].source.id == sim.artifactId
    assert b["inlet absent"].value == kinetics.ABSENT


def test_a_persons_hour_reads_that_hours_state_and_the_basis_names_the_person(store, worker):
    sim = real_simulation()
    t = sim.series["t"]
    k = len(t) // 3
    inlet = pureos.inlet_stream(sim_inlet(sim.artifactId, harvest_hour=typed(t[k])))
    assert inlet.read.harvestHour == t[k]
    assert inlet.read.concentrations == {CHEMICAL_OF[s]: sim.series[s][k] for s in ("X", "S", "P")}
    b = by_name(inlet.basis)
    assert b["inlet.harvest_hour"].source.kind == "assumption" and b["inlet.harvest_hour"].source.by == BY
    assert b["inlet source"].value == fermos.PERSONS_HOUR and f"an hour {BY} named" in b["inlet source"].source.note
    assert any(f"an hour {BY} named, not the simulation's own harvest hour" in n for n in inlet.read.notes)
    # An hour between two kept points reads the nearer one, and the inlet says so.
    between = pureos.inlet_stream(sim_inlet(sim.artifactId, harvest_hour=typed(t[k] + (t[k + 1] - t[k]) / 4)))
    assert between.read.concentrations == inlet.read.concentrations
    assert any("the nearest kept point" in n for n in between.read.notes)
    assert "the nearest kept point" in by_name(between.basis)["inlet.conc.Ethanol"].source.note
    # An hour outside the run refuses the inlet in words.
    with pytest.raises(pureos.TrainRefused, match=r"the inlet: the hour .* h lies outside simulation"):
        pureos.inlet_stream(sim_inlet(sim.artifactId, harvest_hour=typed(sim.end["t"] * 2)))


def test_a_train_run_on_a_simulations_harvest_names_its_source(store, worker, no_pool):
    sim = real_simulation()
    run = pureos.run_train(sim_inlet(sim.artifactId))
    art = artifacts.get(run.artifactId)
    assert by_name(art.inputs)["inlet source"].value == fermos.HARVEST_HOUR
    assert run.inlet.ref == sim.artifactId and run.inlet.refTool == fermos.SIMULATION
    assert any(n.startswith(f"the broth of simulation {sim.artifactId} at its own harvest hour") for n in run.inlet.notes)
    assert artifacts.replay(run.artifactId).identical


# ── a scenario's run inlet: its newest run's broth ─────────────────────


def test_a_scenario_inlet_reads_its_newest_runs_broth_as_its_flowsheet_names_it(store, worker, no_pool):
    older = _keep("bbbbbbbbbbbbbbb2")
    plant_artifact(older.model_copy(update={"createdAt": "2026-10-20T10:00:00Z"}))
    newest = _keep()  # 2026-10-21, sc-k3x9q-1, ethanol_glucose_v0
    spec = spec_of(inlet={"kind": "run-stream", "ref": "sc-k3x9q-1"})
    assert pureos.validate(spec) == []
    inlet = pureos.inlet_stream(spec)
    beer = next(s for s in STREAMS if s["id"] == shelf.SHELF["ethanol_glucose_v0"].brothStream)
    assert inlet.read.ref == newest.id and inlet.read.streamId == beer["id"] == "beer"
    assert inlet.read.flows == {c: m for c, m in beer["massFlows"].items() if m > 0}
    b = by_name(inlet.basis)
    assert b["inlet"].source.id == newest.id and b["inlet stream"].value == "beer"
    assert b["inlet source"].value == "a scenario's newest run"
    assert ("the stream ethanol_glucose_v0 names as its broth, read from its shelf entry" in
            b["inlet source"].source.note and "the newest run of scenario sc-k3x9q-1" in b["inlet source"].source.note)
    assert train_spec.chemicals_of(spec) == sorted(c for c, m in beer["massFlows"].items() if m > 0)
    # A stream the train names is taken instead, from the same newest run.
    named = pureos.inlet_stream(spec_of(inlet={"kind": "run-stream", "ref": "sc-k3x9q-1", "streamId": "s1"}))
    assert named.read.streamId == "s1" and "as the train names it" in by_name(named.basis)["inlet source"].source.note
    # The run keeps what it read: the run, the stream and the source.
    spec = spec_of(inlet={"kind": "run-stream", "ref": "sc-k3x9q-1"}, units=[
        {"id": "C1", "type": "centrifugation", "params": {"split.Ethanol": typed(0.05)}},
        {"id": "F1", "type": "flash", "params": {"P": typed(101325.0), "V": typed(0.1)},
         "outlets": {"vapour": "waste", "liquid": "onward"}}])
    run = pureos.run_train(spec)
    assert (run.inlet.ref, run.inlet.streamId, run.inlet.refTool) == (newest.id, "beer", "proforma.run")
    assert run.spec.inlet.ref == "sc-k3x9q-1" and any("names as its broth" in n for n in run.inlet.notes)
    assert artifacts.replay(run.artifactId).identical


def test_a_scenario_inlet_whose_flowsheet_names_no_broth_is_refused_naming_the_runs_streams(store, worker):
    _keep(flowsheet="corn_drygrind", scenario="sc-corn")
    with pytest.raises(pureos.TrainRefused) as e:
        pureos.inlet_stream(spec_of(inlet={"kind": "run-stream", "ref": "sc-corn"}))
    words = str(e.value)
    assert "the newest run of scenario sc-corn on file, is of corn_drygrind, whose shelf entry names no broth" in words
    assert "name the stream the train takes, one of " + ", ".join(s["id"] for s in STREAMS) in words
    with pytest.raises(pureos.TrainRefused, match="there is no kept artifact or scenario run sc-none here"):
        pureos.inlet_stream(spec_of(inlet={"kind": "run-stream", "ref": "sc-none"}))
    with pytest.raises(pureos.TrainRefused, match=r"holds no stream nonesuch; its streams are glucose, water"):
        pureos.inlet_stream(spec_of(inlet={"kind": "run-stream", "ref": "sc-corn", "streamId": "nonesuch"}))


# The attribute each scenario flowsheet keeps its fermenter on (`self.R1`).
FERMENTER = "R1"


def test_the_shelf_names_each_broth_by_the_id_its_flowsheet_file_gives_the_fermenters_outlet():
    """A scenario flowsheet's `brothStream` is read from its file: one of the
    stream names the fermenter's own `outs` give (`self.R1 = <unit>(...,
    outs=...)`), never another unit's and never guessed; a reference names
    none (its package names its streams)."""
    for info in shelf.SHELF.values():
        if info.reference:
            assert info.brothStream is None, info.id
            continue
        assert info.brothStream, info.id
        tree = ast.parse((PKG / "flowsheets" / f"{info.id}.py").read_text(encoding="utf-8"))
        fermenters = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Attribute) and t.attr == FERMENTER for t in node.targets)
                      and isinstance(node.value, ast.Call)]
        assert len(fermenters) == 1, (info.id, len(fermenters))
        outs = {c.value for kw in fermenters[0].keywords if kw.arg == "outs" for c in ast.walk(kw.value)
                if isinstance(c, ast.Constant) and isinstance(c.value, str)}
        assert info.brothStream in outs, (info.id, outs)
        assert info.brothStream != "vent", info.id  # the gas the fermenter vents is no broth


# ── GET /api/fermos/harvest ────────────────────────────────────────────


def test_the_harvest_endpoint_reads_the_kept_series_and_refuses_in_words(client, store):
    sim = real_simulation()
    r = client.get(f"/api/fermos/harvest?simulation={sim.artifactId}")
    assert r.status_code == 200 and r.json() == fermos.harvest(sim.artifactId).model_dump(mode="json")
    assert r.json()["hourSource"] == fermos.HARVEST_HOUR
    t = sim.series["t"]
    r = client.get(f"/api/fermos/harvest?simulation={sim.artifactId}&hour={t[4]!r}")
    assert r.status_code == 200 and r.json()["hourSource"] == fermos.PERSONS_HOUR and r.json()["hour"] == t[4]
    r = client.get(f"/api/fermos/harvest?simulation={sim.artifactId}&hour={sim.end['t'] * 2!r}")
    assert r.status_code == 422 and "lies outside simulation" in r.json()["detail"]
    r = client.get("/api/fermos/harvest?simulation=0123456789abcdef")
    assert r.status_code == 404 and "there is no kept simulation 0123456789abcdef" in r.json()["detail"]
    art = artifacts.get(sim.artifactId)
    keep_copy(art, "c" * 16, series={k: v for k, v in art.output["series"].items() if k != "P"})
    r = client.get(f"/api/fermos/harvest?simulation={'c' * 16}")
    assert r.status_code == 422 and "keeps no product series (P" in r.json()["detail"]
    plant_damaged("9" * 16)
    r = client.get(f"/api/fermos/harvest?simulation={'9' * 16}")
    assert r.status_code == 409 and "damaged on disk" in r.json()["detail"]
    assert client.get("/api/fermos/harvest").status_code == 422


# ── the real worker (sim) ──────────────────────────────────────────────


@pytest.mark.sim
def test_a_scenarios_newest_real_run_gives_a_train_its_beer_as_the_shelf_names_it(real):
    """The glucose-to-ethanol flowsheet run by the real worker on STAND-IN
    inputs under a scenario's id: a train that names the scenario takes the
    stream the shelf names as the flowsheet's broth from that run's own
    table, and the catalogue's ethanol train on it gives the package's own
    purity, as on the run's beer named by id."""
    from openferment_core import proforma
    from openferment_core.models import InputAssumption
    from test_train import AT, ETHANOL_STANDIN, MEASURED, PACKAGE_UNITS, STANDIN

    run = proforma.run_flowsheet("ethanol_glucose_v0", [
        InputAssumption(key=k, value=v, low=v, high=v, by=BY, at=AT, note=STANDIN) for k, v in ETHANOL_STANDIN.items()],
        samples=1, scenario_id="sc-seam-sim")
    beer = next(s for s in proforma.tables_of(run).streams if s.id == shelf.SHELF["ethanol_glucose_v0"].brothStream)
    assert beer.source == "R1"  # the fermenter's own outlet, in the run BioSTEAM made
    units = [{"id": uid, "type": t, "readFrom": {"flowsheet": "ethanol_glucose_v0", "unit": pkg}}
             for uid, t, pkg in PACKAGE_UNITS]
    units[-1]["outlets"] = {"regenerate": "recycle:D2", "product": "onward"}
    spec = TrainSpec.model_validate({"id": "seam-train", "name": "The seam's train", "program": "yeast",
                                     "product": "ethanol", "inlet": {"kind": "run-stream", "ref": "sc-seam-sim"},
                                     "units": units})
    inlet = pureos.inlet_stream(spec)
    assert (inlet.read.ref, inlet.read.streamId) == (run.id, beer.id)
    assert inlet.read.flows == {c: m for c, m in beer.massFlows.items() if m > 0}
    got = pureos.run_train(spec)
    by_id = pureos.run_train(spec.model_copy(update={"inlet": spec.inlet.model_copy(update={"ref": run.id,
                                                                                            "streamId": beer.id})}))
    assert got.purity.productFraction == pytest.approx(by_id.purity.productFraction, rel=MEASURED)
    package = next(s for s in proforma.tables_of(run).streams if s.id == "ethanol")
    assert got.purity.productFraction == pytest.approx(package.massFlows["Ethanol"] / package.massFlow, rel=MEASURED)
