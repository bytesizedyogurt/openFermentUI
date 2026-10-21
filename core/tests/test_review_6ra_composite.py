"""OF-BLD-020 §6.R (part a): the composite, as the night-two review found it
(main-4/22, main-25, main-28, main-29, main-30; the browser's main-11/23 and
main-15/26 are held by check:store).

Offline (stand-in workers, as test_custom_train's):

- main-4/22: a vessel designed for one vessel's batch volume sizes no plant,
  so a composite built on it is refused in words naming the batch volume,
  by the binding, the panel and the run alike, before any worker runs.
- main-25: a train run whose unit is fed a side inlet (a solvent, kg h⁻¹ as
  that run held it) is refused as a composite's train in words: the
  composite sets its beer from the plant scale, and the side flow is not
  scaled with it.
- main-28: a finance override of another scenario's scope is refused in the
  run's words, as an input's is.
- main-29: a depreciation schedule longer than the plant's life (BioSTEAM's
  own table, read from its file) is refused by the panel's resolve and the
  run in words naming the life, before the worker runs.
- main-30: `GET /api/proforma/bind` on a flowsheet with no Finance group
  refuses a finance key it does not take, as the run does.

Marked `sim` (the real Proforma worker): an aerated vessel designed by batch
volume and a three-unit train on its harvest, priced at a typed plant scale,
is refused in words naming the batch volume.

Every STAND-IN here is an `assumption` of this test, typed under the
fixture's name and noted STAND-IN; none is a measurement, a published value
or a result, and only what the code does with it is asserted.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from openferment_core import artifacts, composite, proforma, pureos, vessel
from openferment_core.flowsheets import shelf
from openferment_core.models import Override, VesselRequest
from test_custom_train import (  # noqa: F401 (the fixtures, by name)
    AT,
    BY,
    FLOWSHEET,
    POOL,
    SCOPE,
    STANDIN,
    client,
    inputs_typed,
    over,
    parts,
    real,
    request,
    store,
    warm,
    worker,
)
from test_train import spec_of, typed
from test_vessel import AEROBIC_ID, keep, standin_simulation

# STAND-INs of this test, as the review's own probe typed them.
BATCH_VOLUME, LOADING, PLANT = 50.0, 2.0, 50000.0


def vessel_override(aid: str, key: str, value) -> Override:
    return Override(scope=f"fermos:vessel:{aid}", key=key, value=value, by=BY, at=AT, note=STANDIN)


def batch_volume_design(aid: str):
    return vessel.design(VesselRequest(simulation=aid, overrides=[
        vessel_override(aid, "batch_volume", BATCH_VOLUME), vessel_override(aid, "loading_time", LOADING)]))


def runs(worker) -> list:
    return [c for c in worker.calls if c[0] == "run"]


# ── main-4/22: one vessel's batch volume sizes no plant ─────────────────


def test_a_vessel_designed_by_batch_volume_is_refused_as_a_composites_fermenter_in_words(store, worker, client):
    keep(AEROBIC_ID, standin_simulation(True))
    d = batch_volume_design(AEROBIC_ID)
    assert "batch_volume" in {i.name for i in artifacts.get(d.artifactId).inputs}
    run = pureos.run_train(spec_of())
    p = SimpleNamespace(vessel=d.artifactId, train=run.artifactId)
    words = (rf"vessel design {d.artifactId} was designed for one vessel's batch volume \(batch_volume\)")
    with pytest.raises(proforma.ScenarioRefused, match=words):
        composite.parts_of(p.vessel, p.train)
    with pytest.raises(proforma.ScenarioRefused, match=words):
        proforma.run(request(p, overrides=[*inputs_typed(), over("plant_scale", PLANT)]), pool=POOL)
    with pytest.raises(proforma.ScenarioRefused, match=words):
        proforma.bind_flowsheet(FLOWSHEET, pool=POOL, vessel=p.vessel, train_run=p.train)
    r = client.get(f"/api/params/{SCOPE}?flowsheet={FLOWSHEET}&vessel={p.vessel}&trainRun={p.train}")
    assert r.status_code == 422 and "designed for one vessel's batch volume" in r.json()["detail"]
    assert "design the vessel at a plant scale in fermOS → Vessel" in r.json()["detail"]
    assert not runs(worker)


# ── main-11/23: the basis names the person a vessel value came from ────


def test_a_vessel_value_a_person_typed_names_them_in_the_composites_basis(store, worker):
    from test_vessel import ANAEROBIC_ID

    sean = "Sean Creighton"
    d = vessel.design(VesselRequest(simulation=ANAEROBIC_ID, overrides=[
        vessel_override(ANAEROBIC_ID, "plant_scale", PLANT),
        Override(scope=f"fermos:vessel:{ANAEROBIC_ID}", key="V_wf", value=0.8, by=sean, at=AT, note=STANDIN)]))
    run = pureos.run_train(spec_of())
    r = proforma.run(request(SimpleNamespace(vessel=d.artifactId, train=run.artifactId),
                             overrides=[*inputs_typed(), over("IRR", 0.1, by=sean)]), pool=POOL)
    by = {b.name: b for b in artifacts.get(r.artifactId).inputs}
    # The design's value stays the design's source (its provenance follows the artifact), naming the person.
    assert by["fermenter.V_wf"].source.kind == "artifact" and by["fermenter.V_wf"].source.id == d.artifactId
    assert by["fermenter.V_wf"].source.by == sean
    # A value the design took from the simulation or the class names nobody.
    assert by["fermenter.tau"].source.by is None
    assert by["finance.IRR"].source.kind == "assumption" and by["finance.IRR"].source.by == sean


# ── main-25: a side inlet's flow is not scaled to the plant ────────────


def test_a_train_run_with_a_side_inlet_fed_is_refused_as_a_composites_train_in_words(parts, worker):
    spec = spec_of(units=[{"id": "L1", "type": "lle", "params": {"solvent.Octane": typed(500.0)},
                           "outlets": {"extract": "onward", "raffinate": "waste"}}])
    run = pureos.run_train(spec)
    units = composite.train_of(artifacts.get(run.artifactId))["units"]
    assert units[0]["sides"] == {"solvent": {"Octane": 500.0}}  # as the train run held it, kg h⁻¹
    with pytest.raises(proforma.ScenarioRefused, match=rf"train run {run.artifactId} feeds unit L1 a side inlet "
                                                       r"\(solvent: Octane 500 kg h⁻¹\) at that run's own rate"):
        composite.parts_of(parts.vessel, run.artifactId)
    with pytest.raises(proforma.ScenarioRefused, match="is not scaled with it"):
        proforma.run(request(SimpleNamespace(vessel=parts.vessel, train=run.artifactId)), pool=POOL)
    assert not runs(worker)
    # A train with no side inlet fed stands, as before.
    assert composite.parts_of(parts.vessel, parts.train).train.id == parts.train


# ── main-28: an override names the scope it changes ────────────────────


def test_a_finance_override_of_another_scenarios_scope_is_refused_as_an_inputs_is(parts, worker):
    stray = over("IRR", 0.1, scope="proforma:sc-B")
    with pytest.raises(proforma.ScenarioRefused, match="an override names the scope it changes, and these were sent "
                                                       f"for {SCOPE}: proforma:sc-B"):
        proforma.run(request(parts, overrides=[*inputs_typed(), stray]), pool=POOL)
    assert not runs(worker)
    # Its own scope's finance override still prices.
    proforma.run(request(parts, overrides=[*inputs_typed(), over("IRR", 0.1)]), pool=POOL)
    assert runs(worker)[-1][1]["structure"]["finance"] == {"IRR": 0.1}


# ── main-29: a schedule longer than the plant's life ───────────────────


def test_a_depreciation_schedule_longer_than_the_plants_life_is_refused_in_words(parts, worker, client):
    defaults = shelf.package_tea_defaults()
    start, end = defaults["duration"]
    life = end - start
    lengths = shelf.depreciation_lengths()
    longer = next(name for name, n in lengths.items() if n > life)
    fits = next(name for name, n in lengths.items() if n <= life)
    words = (rf"the depreciation schedule {longer} writes the capital off over {lengths[longer]} years by BioSTEAM's "
             rf"own table, longer than the plant's life of {life} years \({start} to {end}\)")
    import openferment_core.params as params

    with pytest.raises(params.ParamRefused, match=words):
        composite.finance_values([over("depreciation", longer)])
    assert composite.finance_values([over("depreciation", fits)])  # one that fits stands
    ask = {"flowsheet": FLOWSHEET, "vessel": parts.vessel, "trainRun": parts.train,
           "overrides": [over("depreciation", longer).model_dump()]}
    r = client.post(f"/api/params/{SCOPE}/resolve", json=ask)
    assert r.status_code == 422 and f"the depreciation schedule {longer} writes the capital off" in r.json()["detail"]
    with pytest.raises(proforma.ScenarioRefused, match=words):
        proforma.run(request(parts, overrides=[*inputs_typed(), over("depreciation", longer)]), pool=POOL)
    assert not runs(worker)
    # A shortened life catches a shorter schedule the same way.
    seven = lengths[defaults["depreciation"]]
    with pytest.raises(params.ParamRefused, match=rf"longer than the plant's life of {seven - 1} years"):
        composite.finance_values([over("duration.end", float(start + seven - 1))])


# ── main-30: bind refuses a key the flowsheet does not take ────────────


def test_bind_on_a_flowsheet_with_no_finance_refuses_a_finance_key_as_the_run_does(client):
    import json

    for key, value in (("IRR", 0.2), ("income_tax", 5.0), ("depreciation", 3.0)):
        typed_ = json.dumps([over(key, value).model_dump(mode="json")])
        r = client.get("/api/proforma/bind", params={"flowsheet": "ethanol_glucose_v0", "overrides": typed_})
        assert r.status_code == 422 and f"ethanol_glucose_v0 takes no input {key}" in r.json()["detail"], r.text


# ── the real worker (sim) ──────────────────────────────────────────────


@pytest.mark.sim
def test_a_real_batch_volume_vessel_and_its_train_at_a_typed_plant_scale_are_refused_in_words(real):
    from test_train import three_units
    from test_vessel import real_simulation

    sim = real_simulation(True)
    d = batch_volume_design(sim.artifactId)
    run = pureos.run_train(three_units(kind="simulation", ref=sim.artifactId, vessel=d.artifactId))
    p = SimpleNamespace(vessel=d.artifactId, train=run.artifactId)
    with pytest.raises(proforma.ScenarioRefused, match=r"designed for one vessel's batch volume \(batch_volume\)"):
        proforma.run(request(p, overrides=[*inputs_typed(**{"yield": 0.12}), over("plant_scale", PLANT)]), pool=POOL)
