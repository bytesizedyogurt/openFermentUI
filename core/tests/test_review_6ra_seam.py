"""OF-BLD-020 §6.R (part a): the harvest read and the vessel, as the reviews
found them (the second review, over §6.2: seam-0, seam-1, seam-2).

Offline (scipy, no BioSTEAM; stand-in workers answer the train's stream
defaults and the vessel's specs and design):

- seam-0: a batch run with a run length keeps its own harvest hour (the hour
  its sugar runs out) as a kept point, so `fermos.harvest` at that hour, the
  pureOS inlet and the vessel all read the broth the artifact's own titre and
  residual sugar describe, never a grid neighbour; a simulation kept before,
  whose harvest hour is not a kept point, is refused at its own hour in
  words (a person's hour still reads the nearest kept point, said so), and
  a simulation's version follows the change.
- seam-1: within one vessel design the broth read at harvest and the titre
  it is sized by come from the same hour; a design computed through the new
  read is kept under a version of its own.
- seam-2: a kept simulation whose series cannot be read is a 422 in words on
  the vessel's endpoints and its parameter scope, never a bare 500.

Every STAND-IN here is an `assumption` of this test, typed under the
fixture's name and noted STAND-IN; none is a measurement, a published value
or a result, and only what the code does with it is asserted.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import test_vessel as tv
from openferment_core import artifacts, fermos, kinetics, proforma, pureos, vessel
from openferment_core.models import Artifact, Override, TrainSpec, VesselRequest
from standins import plant_artifact
from test_train import (  # noqa: F401 (the fixtures, by name)
    AT,
    BY,
    SIM_STANDIN,
    STANDIN,
    real_simulation,
    spec_of,
    store,
    typed,
    worker,
)

# Within rounding: the solver's dense output read at one hour in one call
# and in another (the kept series and the titre at harvest).
ROUNDING = 1e-9
# The run lengths the review measured past the sugar's run-out (STAND-INs
# of this test, as the review's own were): neither falls on a grid hour.
LENGTHS = (100.0, 37.3)


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


@pytest.fixture()
def vessel_worker(monkeypatch):
    """test_vessel's stand-in for the vessel's worker ops."""
    w = tv.StandInWorker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(vessel, "_SPECS", {})
    return w


def sim_inlet(sim_id: str) -> TrainSpec:
    return spec_of(inlet={"kind": "simulation", "ref": sim_id, "params": {"broth_flow": typed(1.0)}})


def states_of(h) -> dict[str, float]:
    return {x.state: x.value for x in h.states}


def keep_copy(art: Artifact, aid: str, **output) -> Artifact:
    """A copy of a kept simulation written by hand under another id, its
    output changed as given (a STAND-IN artifact)."""
    return plant_artifact(art.model_copy(update={"id": aid, "output": {**art.output, **output}}))


def without_harvest_point(art: Artifact, aid: str) -> Artifact:
    """The simulation as a version-1 run kept it: its series on the display
    grid and its segment ends alone, with no point at its harvest hour."""
    series = art.output["series"]
    k = series["t"].index(art.output["harvestH"])
    return keep_copy(art, aid, series={key: [v for i, v in enumerate(col) if i != k] for key, col in series.items()})


def scale(aid: str) -> Override:
    return Override(scope=f"fermos:vessel:{aid}", key="plant_scale", value=2000.0, by=BY, at=AT, note=STANDIN)


# ── seam-0: the harvest hour is a kept point ───────────────────────────


@pytest.mark.parametrize("t_end", LENGTHS)
def test_a_batch_run_with_a_run_length_reads_its_own_broth_at_its_own_harvest_hour(store, worker, t_end):
    sim = real_simulation(t_end=t_end)
    assert sim.end["t"] > sim.harvestH  # the run goes on after its sugar runs out
    assert sim.harvestH in sim.series["t"]
    h = fermos.harvest(sim.artifactId)
    assert h.exact and h.hour == h.asked == sim.harvestH and "the kept point at" in h.read
    assert states_of(h)["P"] == pytest.approx(sim.finalTitre, rel=ROUNDING)
    assert states_of(h)["S"] == pytest.approx(kinetics.RUN_OUT_SHARE * SIM_STANDIN["s0"], rel=1e-6)
    inlet = pureos.inlet_stream(sim_inlet(sim.artifactId))
    assert inlet.read.concentrations["Ethanol"] == pytest.approx(sim.finalTitre, rel=ROUNDING)
    assert inlet.read.concentrations["Glucose"] == pytest.approx(states_of(h)["S"], rel=ROUNDING)
    assert not any("the nearest kept point" in n for n in inlet.read.notes)


def test_the_oxygen_uptake_is_kept_on_the_same_hours_as_the_states(store):
    sim = tv.real_simulation(True, t_end=LENGTHS[0])
    assert sim.our.t == sim.series["t"] and sim.harvestH in sim.our.t


def test_a_simulations_version_follows_the_kept_hours(store):
    sim = real_simulation()
    art = artifacts.get(sim.artifactId)
    assert art.toolVersion == f"kinetics batch_v1 2 · scipy {kinetics.versions()['scipy']}"
    # A run until its sugar runs out ends at its harvest hour: it was a kept point already.
    assert sim.harvestH == sim.end["t"] == sim.series["t"][-1]


def test_an_older_simulation_with_no_point_at_its_harvest_hour_is_refused_there_in_words(store, worker):
    sim = real_simulation(t_end=LENGTHS[0])
    old = without_harvest_point(artifacts.get(sim.artifactId), "c" * 16)
    with pytest.raises(fermos.SimulationRefused) as e:
        fermos.harvest(old.id)
    words = str(e.value)
    assert f"simulation {old.id} keeps no point at its own harvest hour, {sim.harvestH:.6g} h" in words
    assert "simulate it again" in words
    # A person's hour is theirs: the nearest kept point, said so.
    near = fermos.harvest(old.id, sim.harvestH)
    assert not near.exact and "the nearest kept point" in near.read
    # pureOS's inlet and the vessel refuse it in the read's words.
    with pytest.raises(pureos.TrainRefused, match=rf"simulation c{{16}} keeps no point at its own harvest hour"):
        pureos.inlet_stream(sim_inlet(old.id))
    with pytest.raises(vessel.VesselRefused, match=rf"simulation c{{16}} keeps no point at its own harvest hour"):
        vessel.simulation_inputs(artifacts.get(old.id))


# ── seam-1: one design, one hour ───────────────────────────────────────


@pytest.mark.parametrize("t_end", LENGTHS)
def test_a_vessels_broth_and_the_titre_it_is_sized_by_are_read_at_one_hour(store, t_end):
    sim = tv.real_simulation(True, t_end=t_end)
    src = vessel.simulation_inputs(artifacts.get(sim.artifactId))
    assert src["made"]["ethanol"] + src["start"]["p0"] == pytest.approx(src["finalTitre"], rel=ROUNDING)
    assert src["end"]["S"] == pytest.approx(kinetics.RUN_OUT_SHARE * tv.SIM_STANDIN["s0"], rel=1e-6)
    assert not any("the nearest kept point" in n for n in src["readNotes"])


def test_a_design_through_the_new_read_is_kept_under_a_version_of_its_own(store, vessel_worker):
    sim = tv.real_simulation(True, t_end=LENGTHS[0])
    d = vessel.design(VesselRequest(simulation=sim.artifactId, overrides=[scale(sim.artifactId)]))
    art = artifacts.get(d.artifactId)
    assert art.toolVersion.startswith("vessel 3 · ")
    # The same basis under the version that read the nearest kept point names another artifact.
    before = artifacts.artifact_id(vessel.TOOL, art.toolVersion.replace("vessel 3", "vessel 2", 1), art.inputs, art.seed)
    assert before != d.artifactId


# ── seam-2: a series that cannot be read is a 422 on the vessel ────────


def test_a_kept_simulation_whose_series_cannot_be_read_is_a_422_on_the_vessel(store, vessel_worker, client):
    sim = tv.real_simulation(True, t_end=20.0)
    art = artifacts.get(sim.artifactId)
    assert sim.end["t"] > sim.harvestH  # read through fermos.harvest
    bad = keep_copy(art, "e" * 16, series={**art.output["series"], "S": art.output["series"]["S"][:-1]})
    r = client.get(f"/api/fermos/vessel/specs?simulation={bad.id}")
    assert r.status_code == 422 and "cannot be read" in r.json()["detail"], r.text
    r = client.post("/api/fermos/vessel", json={"simulation": bad.id, "overrides": [scale(bad.id).model_dump()]})
    assert r.status_code == 422 and "cannot be read" in r.json()["detail"], r.text
    r = client.get(f"/api/params/fermos:vessel:{bad.id}")
    assert r.status_code == 422 and "cannot be read" in r.json()["detail"], r.text
    # The simulation it was copied from still answers.
    assert client.get(f"/api/fermos/vessel/specs?simulation={sim.artifactId}").status_code == 200
