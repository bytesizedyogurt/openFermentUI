"""The seam: a vessel and a train become a flowsheet Proforma prices, and every
reader reads the one run (OF-BLD-020 §6.1; D11, D3, E.2‴, E.3‴).

Offline: `custom_train_v1` is on the shelf, built on the yeast chemical set
(the one pureOS holds) from a vessel design and a train run; its file holds
no number but zero and one; a run, a binding and the panel refuse in words a
part that is missing, of another tool, not on file, damaged, built on another
chemical set, or whose unit id the fermenter takes; the vessel design binds the plant scale it was designed at (a
person's value wins); the panel serves the group Finance, each parameter the
package's own default read from its file, a person's value their named
assumption; a run hands the worker the fermenter as the design holds it, the
train's units as their run held them and the finance a person set, and its
basis names both artifacts and every finance parameter's source.

Marked `sim` (the real Proforma worker): a vessel designed for a stand-in
simulation and a three-unit train run on its harvest broth price on stand-in
assumptions and converge; the stream table's units are the feed mixer, the
vessel's class and the train's types; pureOS reads the run as any run; the
finance read back is the package's, and a person's where they set it; and the
run replays.

Every STAND-IN here is an `assumption` of this test, typed under the
fixture's name and noted STAND-IN; none is a measurement, a published value
or a result, and only what the code does with it is asserted.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, composite, intake, proforma, pureos, vessel
import standins  # test-only stand-ins, moved out of demo.py (alpha 2.0 stage 1)
from openferment_core.flowsheets import shelf
from openferment_core.models import Override, ProformaRunRequest, VesselRequest
from openferment_core.pureos import catalogue, train_spec
from test_train import TrainWorker, spec_of
from test_vessel import ANAEROBIC_ID, StandInWorker as VesselWorker, keep, standin_simulation

CORE = Path(__file__).resolve().parent.parent
PKG = CORE / "openferment_core"
BY = "openFerment test fixture"
AT = "2026-10-21"
STANDIN = "STAND-IN for this test: an assumption typed to exercise the code, not a result"
FLOWSHEET = "custom_train_v1"
SCENARIO = "sc-composite-test"
SCOPE = f"proforma:{SCENARIO}"
# STAND-IN inputs for the composite's run (assumptions of this test, none a
# result): enough to price it once. The plant scale is the vessel design's.
INPUTS_STANDIN = {"feed_glucose_conc": 100.0, "titre": 45.0, "yield": 0.42, "productivity": 2.0, "glucose_price": 0.3}
# The stand-in vessel design's plant scale.
PLANT_STANDIN = 50000.0


def over(key, value, *, scope=SCOPE, by=BY) -> Override:
    return Override(scope=scope, key=key, value=value, by=by, at=AT, note=STANDIN)


def inputs_typed(**more) -> list[Override]:
    return [over(k, v) for k, v in {**INPUTS_STANDIN, **more}.items()]


class Worker:
    """The vessel's ops to test_vessel's stand-in, the train's to
    test_train's, every Proforma run to demo's stand-in evaluator; each call
    kept."""

    def __init__(self):
        self.vessel, self.train, self.calls = VesselWorker(), TrainWorker(), []

    def __call__(self, op, args):
        self.calls.append((op, args))
        if op.startswith("vessel_"):
            return self.vessel(op, args)
        if op in ("catalogue_specs", "train_specs", "flowsheet_unit_values", "train_run"):
            return self.train(op, args)
        return standins._standin_call(op, args)


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    keep(ANAEROBIC_ID, standin_simulation(False))
    return tmp_path


@pytest.fixture()
def worker(monkeypatch):
    w = Worker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(vessel, "_SPECS", {})
    monkeypatch.setattr(catalogue, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_UNITS", {})
    monkeypatch.setattr(train_spec, "_pool", lambda: None)
    return w


@pytest.fixture()
def parts(store, worker):
    """A stand-in vessel design (the NREL vessel, at a stand-in plant scale)
    and a stand-in train run, each made by the real code on the stand-in
    workers."""
    d = vessel.design(VesselRequest(simulation=ANAEROBIC_ID, overrides=[Override(
        scope=f"fermos:vessel:{ANAEROBIC_ID}", key="plant_scale", value=PLANT_STANDIN, by=BY, at=AT, note=STANDIN)]))
    run = pureos.run_train(spec_of())
    return SimpleNamespace(vessel=d.artifactId, train=run.artifactId)


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


POOL = SimpleNamespace(records=[], records_by_id={})


def request(parts, **kw) -> ProformaRunRequest:
    return ProformaRunRequest(**{"scenarioId": SCENARIO, "flowsheet": FLOWSHEET, "vessel": parts.vessel,
                                 "trainRun": parts.train, "overrides": inputs_typed(), "samples": 3, **kw})


# ── the shelf (offline) ────────────────────────────────────────────────


def test_the_shelf_holds_the_composite_the_yeast_programs_built_from_a_vessel_and_a_train():
    info = shelf.info(FLOWSHEET)
    assert not info.reference and info.builtFrom == ["fermos.vessel", "pureos.train_run"]
    # Its program is the chemical set its train builds on, the one pureOS holds.
    assert set(train_spec.PROGRAM_CHEMICALS) == {info.program} == {"yeast"}
    assert [i.key for i in info.inputs] == ["feed_glucose_conc", "titre", "yield", "productivity", "plant_scale",
                                           "glucose_price"]
    assert set(info.gridInputs) <= {i.key for i in info.inputs} and info.priceOutput in info.outputs
    assert "the fermenter's beer is its inlet" in info.description
    # No seed scenario names it: a scenario on it is made in the browser alone.
    assert all(s.get("modelId") != FLOWSHEET for s in proforma.seed_scenarios())
    # The worker loads it by its id; its module is that id's (the tree's rule for every shelf flowsheet).
    assert (PKG / "flowsheets" / f"{FLOWSHEET}.py").is_file()


def test_no_process_number_in_the_composites_file():
    """Every number literal in flowsheets/custom_train_v1.py is 0 or 1."""
    tree = ast.parse((PKG / "flowsheets" / f"{FLOWSHEET}.py").read_text(encoding="utf-8"))
    found = [(n.lineno, n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant)
             and isinstance(n.value, (int, float)) and not isinstance(n.value, bool) and n.value not in (0, 1)]
    assert found == [], found


def test_the_shelf_endpoint_lists_it(client):
    served = client.get("/api/proforma/shelf").json()
    assert next(f for f in served if f["id"] == FLOWSHEET)["builtFrom"] == ["fermos.vessel", "pureos.train_run"]


# ── the parts, refused in words (offline) ──────────────────────────────


def test_a_missing_part_refuses_the_run_and_the_binding_in_words(parts, worker):
    for kw, missing in (({"vessel": None}, "no vessel design (vessel)"), ({"trainRun": None}, "no train run (trainRun)"),
                        ({"vessel": None, "trainRun": None}, "no vessel design (vessel) and no train run (trainRun)")):
        with pytest.raises(proforma.ScenarioRefused, match=rf"this names {re.escape(missing)}\. fermOS → Vessel designs one"):
            proforma.run(request(parts, **kw), pool=POOL)
    with pytest.raises(proforma.ScenarioRefused, match="names no vessel design"):
        proforma.bind_flowsheet(FLOWSHEET, pool=POOL)
    # Named for another flowsheet, both are refused.
    with pytest.raises(proforma.ScenarioRefused, match="ethanol_glucose_v0 is not built from a vessel design or a train "
                                                       "run: vessel and trainRun belong to a scenario on custom_train_v1"):
        proforma.run(request(parts, flowsheet="ethanol_glucose_v0"), pool=POOL)
    assert not [c for c in worker.calls if c[0] == "run"]


def test_a_part_of_another_tool_not_on_file_or_damaged_is_refused_in_words(parts, store):
    with pytest.raises(proforma.ScenarioRefused, match=rf"artifact {parts.train} is a pureos.train_run artifact, not the "
                                                       r"vessel design \(fermos.vessel\)"):
        composite.parts_of(parts.train, parts.train)
    with pytest.raises(proforma.ScenarioRefused, match=rf"artifact {parts.vessel} is a fermos.vessel artifact, not the "
                                                       r"train run \(pureos.train_run\)"):
        composite.parts_of(parts.vessel, parts.vessel)
    with pytest.raises(proforma.ScenarioRefused, match="there is no kept artifact aaaaaaaaaaaaaaaa here for the vessel "
                                                       "design: fermOS → Vessel designs one"):
        composite.parts_of("a" * 16, parts.train)
    from standins import plant_damaged

    plant_damaged("b" * 16)
    with pytest.raises(proforma.ScenarioRefused, match="the train run, artifact bbbbbbbbbbbbbbbb is damaged on disk"):
        composite.parts_of(parts.vessel, "b" * 16)


def test_a_train_run_of_another_chemical_set_is_refused(parts, monkeypatch):
    monkeypatch.setattr(train_spec, "program_of_run", lambda a, r=None: "another-set")
    with pytest.raises(proforma.ScenarioRefused, match=rf"train run {parts.train} is built on the chemical set another-set, "
                                                       "which pureOS does not hold"):
        composite.parts_of(parts.vessel, parts.train)
    monkeypatch.setattr(train_spec, "program_of_run", lambda a, r=None: None)
    with pytest.raises(proforma.ScenarioRefused, match=rf"train run {parts.train} names no chemical set it was built on"):
        composite.parts_of(parts.vessel, parts.train)


def test_a_train_unit_the_fermenter_takes_is_refused(store, worker):
    d = vessel.design(VesselRequest(simulation=ANAEROBIC_ID, overrides=[Override(
        scope=f"fermos:vessel:{ANAEROBIC_ID}", key="plant_scale", value=PLANT_STANDIN, by=BY, at=AT, note=STANDIN)]))
    spec = spec_of(units=[{"id": "R1", "type": "centrifugation", "params": {"split.Yeast": {
        "value": 0.9, "by": BY, "at": AT, "note": STANDIN}}}])
    run = pureos.run_train(spec)
    with pytest.raises(proforma.ScenarioRefused, match=rf"train run {run.artifactId} names a unit R1, which "
                                                       r"custom_train_v1's feed mixer \(M1\) or fermenter"):
        composite.parts_of(d.artifactId, run.artifactId)


# ── the binding and the panel (offline) ────────────────────────────────


def test_the_vessel_design_binds_the_plant_scale_it_was_designed_at_and_a_persons_value_wins(parts):
    got = proforma.bind_flowsheet(FLOWSHEET, pool=POOL, vessel=parts.vessel, train_run=parts.train)
    scale = next(i for i in got.inputs if i.key == "plant_scale")
    assert scale.binding == "artifact" and scale.value == PLANT_STANDIN and scale.source.id == parts.vessel
    assert f"the plant scale vessel design {parts.vessel} was designed at, typed by {BY}" == scale.source.note
    assert got.product == "ethanol" and "plant_scale" not in got.waiting
    typed = proforma.named_values(None, [over("plant_scale", 7.0)])[0]
    mine = proforma.bind_flowsheet(FLOWSHEET, pool=POOL, vessel=parts.vessel, train_run=parts.train, assumptions=typed)
    assert next(i for i in mine.inputs if i.key == "plant_scale").binding == "assumption"


def test_a_batch_volume_design_is_refused_as_the_composites_fermenter(store, worker, monkeypatch):
    # A design of one vessel's batch volume (its basis names no plant scale).
    d = vessel.design(VesselRequest(simulation=ANAEROBIC_ID, overrides=[Override(
        scope=f"fermos:vessel:{ANAEROBIC_ID}", key="plant_scale", value=PLANT_STANDIN, by=BY, at=AT, note=STANDIN)]))
    art = artifacts.get(d.artifactId)
    art = art.model_copy(update={"inputs": [i.model_copy(update={"name": i.name.replace("plant_scale", "batch_volume")})
                                            for i in art.inputs]})
    monkeypatch.setattr(artifacts, "get", lambda aid, real=artifacts.get: art if aid == d.artifactId else real(aid))
    run = pureos.run_train(spec_of())
    # OF-BLD-020 §6.R (main-4/22): one vessel's batch volume sizes no plant, so
    # the composite refuses it in words, where it once waited for a plant scale
    # and then priced one vessel of whatever size the plant's flow asked.
    with pytest.raises(proforma.ScenarioRefused, match=rf"vessel design {d.artifactId} was designed for one vessel's "
                                                       r"batch volume \(batch_volume\)"):
        proforma.bind_flowsheet(FLOWSHEET, pool=POOL, vessel=d.artifactId, train_run=run.artifactId)


def test_the_panel_serves_finance_from_the_packages_own_file_and_a_persons_value_is_theirs(parts, client):
    defaults = shelf.package_tea_defaults()
    assert defaults is not None and "IRR" in defaults
    q = f"flowsheet={FLOWSHEET}&vessel={parts.vessel}&trainRun={parts.train}"
    got = client.get(f"/api/params/{SCOPE}?{q}")
    assert got.status_code == 200, got.text
    body = got.json()
    finance = [s for s in body["specs"] if s["group"] == "Finance"]
    keys = [s["key"] for s in finance]
    # Every parameter the package's defaults name, a schedule a key a year, a pair a key an end.
    flat = []
    for k, v in defaults.items():
        if k == "duration":
            flat += ["duration.start", "duration.end"]
        elif k == "construction_schedule":
            flat += [f"construction_schedule.{n}" for n in range(1, len(v) + 1)]
        else:
            flat.append(k)
    assert sorted(keys) == sorted(flat)
    values = {v["key"]: v for v in body["values"]}
    assert values["IRR"]["origin"] == "library-default" and values["IRR"]["value"] == defaults["IRR"]
    assert values["IRR"]["libraryDefault"] == defaults["IRR"]
    assert "default_tea_parameters['IRR']" in values["IRR"]["source"]["note"]
    assert values["construction_schedule.2"]["value"] == defaults["construction_schedule"][1]
    assert values["plant_scale"]["origin"] == "artifact" and values["plant_scale"]["source"]["id"] == parts.vessel
    dep = next(s for s in finance if s["key"] == "depreciation")
    assert defaults["depreciation"] in dep["choices"] and all(c.startswith("MACRS") for c in dep["choices"])
    # A person's value is their named assumption, and the resolve says what a run adds for it.
    ask = {"flowsheet": FLOWSHEET, "vessel": parts.vessel, "trainRun": parts.train,
           "overrides": [over("IRR", 0.1).model_dump(), over("depreciation", "MACRS10").model_dump()]}
    r = client.post(f"/api/params/{SCOPE}/resolve", json=ask)
    assert r.status_code == 200, r.text
    added = {b["name"]: b for b in r.json()["basisInputs"]}
    assert added["finance.IRR"]["source"]["kind"] == "assumption" and added["finance.IRR"]["source"]["by"] == BY
    assert added["finance.depreciation"]["value"] == "MACRS10"
    assert added["assumptions read from"]["value"] == "overrides"
    # A schedule that does not sum to the whole is refused in the run's own words.
    bad = {**ask, "overrides": [over("construction_schedule.1", 0.9).model_dump()]}
    r = client.post(f"/api/params/{SCOPE}/resolve", json=bad)
    assert r.status_code == 422 and "the construction schedule's shares sum to" in r.json()["detail"]
    # A choice not offered, and a scope with no parts, are refused in words.
    r = client.post(f"/api/params/{SCOPE}/resolve", json={**ask, "overrides": [over("depreciation", "MACRS8").model_dump()]})
    assert r.status_code == 422 and "depreciation is one of" in r.json()["detail"]
    r = client.get(f"/api/params/{SCOPE}?flowsheet={FLOWSHEET}")
    assert r.status_code == 422 and "names no vessel design (vessel) and no train run (trainRun)" in r.json()["detail"]


def test_the_bind_endpoint_takes_the_parts(parts, client):
    r = client.get(f"/api/proforma/bind?flowsheet={FLOWSHEET}&vessel={parts.vessel}&trainRun={parts.train}")
    assert r.status_code == 200, r.text
    assert next(i for i in r.json()["inputs"] if i["key"] == "plant_scale")["binding"] == "artifact"
    r = client.get(f"/api/proforma/bind?flowsheet={FLOWSHEET}&vessel={parts.vessel}")
    assert r.status_code == 422 and "no train run (trainRun)" in r.json()["detail"]


# ── the run (offline, a stand-in worker) ───────────────────────────────


def test_a_run_hands_the_worker_the_vessels_fermenter_the_trains_units_and_the_persons_finance(parts, worker):
    r = proforma.run(request(parts, overrides=[*inputs_typed(), over("IRR", 0.1)]), pool=POOL)
    asked = [a for op, a in worker.calls if op == "run"][-1]
    st = asked["structure"]
    v = artifacts.get(parts.vessel)
    assert st["fermenter"]["vessel"] == parts.vessel and st["fermenter"]["unitClass"] == v.output["unitClass"]
    assert st["fermenter"]["unitId"] == v.output["unitId"] and st["fermenter"]["kind"] == "anaerobic"
    # Every design parameter the design passed BioSTEAM, as it passed it (a class default left to the class).
    given = {i.name: i for i in v.inputs}
    assert st["fermenter"]["params"] == {k: vessel._bool(given[k].value) for k in vessel.DESIGN_KEYS
                                         if k in given and given[k].source.kind != "model"}
    assert st["fermenter"]["tau"] == float(given["tau"].value)
    # The train's units as their run held them, on the fermenter's beer.
    assert st["train"]["units"] == train_spec.worker_units(artifacts.get(parts.train))["units"]
    assert [u["id"] for u in st["train"]["units"]] == ["C1", "F1"] and st["train"]["product"] == "Ethanol"
    # The finance a person set, alone; every key named for the read-back.
    assert st["finance"] == {"IRR": 0.1} and "construction_schedule.2" in st["financeKeys"]
    # The plant scale is the vessel design's, sampled as the artifact gives it.
    assert asked["base"]["plant_scale"] == PLANT_STANDIN
    # Nothing carried of the parts is sampled.
    assert not [k for k in asked["specs"] if "." in k]
    assert r.provenance == "assumed" and r.basePrice is not None


def test_the_basis_names_both_artifacts_and_every_finance_parameters_source(parts, worker):
    r = proforma.run(request(parts, overrides=[*inputs_typed(), over("IRR", 0.1)]), pool=POOL)
    by = {b.name: b for b in artifacts.get(r.artifactId).inputs}
    assert by["vessel"].source.kind == "artifact" and by["vessel"].source.id == parts.vessel
    assert by["train run"].source.kind == "artifact" and by["train run"].source.id == parts.train
    assert "is not an input of this flowsheet: the fermenter's beer is the train's inlet" in by["train inlet"].source.note
    assert by["plant_scale vessel"].source.id == parts.vessel and by["plant_scale vessel"].value == PLANT_STANDIN
    # Every finance parameter, with its source: the package's own (a model input) or the person's.
    for s in composite.finance_specs():
        assert f"finance.{s.key}" in by, s.key
    assert by["finance.IRR"].source.kind == "assumption" and by["finance.IRR"].source.by == BY
    assert by["finance.income_tax"].source.kind == "model" and by["finance.income_tax"].source.id.startswith("biorefineries@")
    # The fermenter's design parameters, each the vessel design's, and the train's values with their own sources.
    assert by["fermenter.tau"].source == by["fermenter.tau"].source.model_copy(update={"kind": "artifact", "id": parts.vessel})
    assert by["train.C1 type"].value == "centrifugation" and by["train.C1.split.Yeast"].source.kind == "assumption"
    assert by["train.product chemical"].value == "Ethanol" and by["flowsheet"].value == FLOWSHEET
    assert by["scenario"].value == SCENARIO
    # A finance override that cannot stand is refused before the worker runs.
    n = len(worker.calls)
    with pytest.raises(proforma.ScenarioRefused, match="the plant's life ends"):
        proforma.run(request(parts, overrides=[*inputs_typed(), over("duration.end", 2000.0)]), pool=POOL)
    assert len(worker.calls) == n


def test_the_run_endpoint_refuses_in_words_and_pureos_reads_the_run(parts, worker, client):
    body = request(parts).model_dump(mode="json")
    r = client.post("/api/proforma/run", json={**body, "vessel": None})
    assert r.status_code == 422 and "no vessel design (vessel)" in r.json()["detail"]
    r = client.post("/api/proforma/run", json=body)
    assert r.status_code == 200, r.text
    tr = pureos.train(r.json()["artifactId"])
    assert tr.flowsheet == FLOWSHEET and tr.scenarioId == SCENARIO and tr.units


def test_flowsheet_runs_refuse_the_composite_with_no_scenario():
    with pytest.raises(proforma.ScenarioRefused, match="built from fermos.vessel and pureos.train_run artifacts a scenario "
                                                       "names"):
        proforma.run_flowsheet(FLOWSHEET, [])


def test_the_service_imports_no_biosteam_to_bind_the_composite():
    import subprocess
    import sys

    code = ("import sys\n"
            "from openferment_core import composite, proforma, params\n"
            "composite.finance_specs(); composite.finance_sources()\n"
            "params.check()\n"
            "steam = sorted(m for m in sys.modules if m.split('.')[0] in ('biosteam', 'thermosteam', 'biorefineries'))\n"
            "assert not steam, steam\n"
            "assert 'openferment_core.flowsheets.custom_train_v1' not in sys.modules\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=CORE, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]


# ── the real worker (sim) ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    return proforma


@pytest.fixture()
def real(monkeypatch, tmp_path, warm):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(train_spec, "_SPECS", {})
    return tmp_path


def _sim_parts(aerobic: bool):
    """A batch simulated by the real fermos.simulate on STAND-IN overrides,
    its vessel designed by BioSTEAM at a stand-in plant scale, and the
    three-unit train run on its harvest broth with that design's broth flow."""
    from test_train import three_units
    from test_vessel import real_simulation

    sim = real_simulation(aerobic)
    d = vessel.design(VesselRequest(simulation=sim.artifactId, overrides=[Override(
        scope=f"fermos:vessel:{sim.artifactId}", key="plant_scale", value=PLANT_STANDIN, by=BY, at=AT, note=STANDIN)]))
    run = pureos.run_train(three_units(kind="simulation", ref=sim.artifactId, vessel=d.artifactId))
    return SimpleNamespace(vessel=d.artifactId, train=run.artifactId, design=d, run=run)


@pytest.mark.sim
@pytest.mark.parametrize("aerobic", [False, True], ids=["nrel-vessel", "aerated-vessel"])
def test_a_vessel_and_a_three_unit_train_price_and_converge_and_every_reader_reads_the_one_run(real, aerobic):
    p = _sim_parts(aerobic)
    # The aerated stand-in makes less ethanol of its glucose: a yield it reaches.
    y = 0.12 if aerobic else INPUTS_STANDIN["yield"]
    r = proforma.run(request(p, overrides=[*inputs_typed(**{"yield": y}), over("IRR", 0.1)], samples=4), pool=POOL)
    assert r.baseInfeasible is None and r.feasible == r.samples == 4 and r.basePrice > 0
    assert r.provenance == "assumed"
    # The stream table's units: the feed mixer, the vessel's class, the train's types.
    classes = [u.unitClass for u in r.units]
    assert classes == ["Mixer", p.design.unitClass, "SolidsCentrifuge", "Flash", "DrumDryer"]
    assert [u.id for u in r.units] == ["M1", p.design.unitId, "C1", "F1", "D1"]
    beer = next(s for s in r.streams if s.id == "beer")
    assert beer.source == p.design.unitId and beer.sink == "C1" and beer.massFlows["Ethanol"] > 0
    # The read-back: the yield reached, the batch time the titre over the
    # productivity, the vessel's own reacting time beside it, the finance as
    # the TEA holds it (the package's, the person's IRR).
    rb = r.readBack
    assert rb["batchTimeH"] == pytest.approx(INPUTS_STANDIN["titre"] / INPUTS_STANDIN["productivity"])
    assert rb["vesselTauH"] == pytest.approx(p.design.parameters and next(
        v.value for v in p.design.parameters if v.key == "tau"))
    assert rb["finance.IRR"] == pytest.approx(0.1)
    for key, value in shelf.package_tea_defaults().items():
        if isinstance(value, list):
            continue
        if isinstance(value, (int, float)) and key != "IRR":
            assert rb[f"finance.{key}"] == pytest.approx(value), key
    assert rb["finance.construction_schedule.1"] == pytest.approx(shelf.package_tea_defaults()["construction_schedule"][0])
    # The ethanol the fermenter made is the bound yield of the glucose fed:
    # in the beer and in the vent, which carries some away with the gas.
    produced = rb["glucoseFedKgPerH"] * y
    made = sum(s.massFlows.get("Ethanol", 0.0) for s in r.streams if s.source == p.design.unitId)
    assert made == pytest.approx(produced, rel=1e-6)
    # pureOS reads the composite run as any run: the product the price is per, traced through the train.
    tr = pureos.train(r.artifactId)
    assert tr.product == "Ethanol" and tr.productStream == "D1_hot_gas" and tr.overallRecovery is not None
    assert [u.id for u in tr.units] == ["M1", p.design.unitId, "C1", "F1", "D1"]
    assert proforma.tables_of(artifacts.get(r.artifactId)).flowsheet == FLOWSHEET
    assert artifacts.replay(r.artifactId).identical


@pytest.mark.sim
def test_the_worker_reads_the_packages_finance_as_the_service_does(real):
    """The finance the panel serves (read from the installed file) is the
    dict the worker builds the TEA from (imported in the worker)."""
    p = _sim_parts(False)
    r = proforma.run(request(p, samples=1), pool=POOL)
    rb = r.readBack
    for s in composite.finance_specs():
        if s.choices is not None:
            continue
        got = composite.finance_sources()[s.key]["library-default"].value
        assert rb[f"finance.{s.key}"] == pytest.approx(got), s.key


@pytest.mark.sim
def test_a_yield_the_vessels_reaction_cannot_reach_is_a_case_it_cannot_hold(real):
    p = _sim_parts(True)
    with pytest.raises(proforma.ScenarioRefused, match="yield: 2 of 2.*this yield is above what the vessel's reaction "
                                                       "makes of the glucose"):
        proforma.run(request(p, overrides=inputs_typed(**{"yield": 0.5}), samples=2), pool=POOL)
