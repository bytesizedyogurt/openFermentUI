"""pureOS → Builder's service side (OF-BLD-020 §5.3).

The Builder asks the service three things beyond §5.2's: what a run of the
train it holds would refuse (`POST /api/pureos/train/check`, every refusal
at once, each by its place, running no train), a train run's own tables
beside the train (`TrainRun.units`, `utilities`, `diagram`, `diagramNote`,
`unitOrder`), and a kept run's units read into a train
(`POST /api/pureos/train/from-run`). Offline, a stand-in worker answers as
test_train's does and the runs are written by hand; marked `sim`, the real
Proforma worker runs the glucose-to-ethanol flowsheet, its train is read
from the run and run again, and gives the package's own purity.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, intake, proforma, pureos
from openferment_core.models import Artifact, BasisInput, BasisSource, InputAssumption, Override, TrainSpec
from openferment_core.pureos import from_run as fr
from test_train import (  # noqa: F401 (the fixtures, by name)
    AT,
    BY,
    ETHANOL_STANDIN,
    STANDIN,
    MEASURED,
    no_pool,
    real,
    spec_of,
    store,
    three_units,
    typed,
    warm,
    worker,
)


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


# ── what a run would refuse, by its place (offline) ────────────────────


def _waiting_spec() -> TrainSpec:
    """A typed inlet with no broth flow; a centrifuge with no split; a flash
    with its pressure and vapour fraction typed."""
    return spec_of(inlet={"kind": "typed", "params": {"conc.Ethanol": typed(50.0)}},
                   units=[{"id": "C1", "type": "centrifugation"},
                          {"id": "F1", "type": "flash", "params": {"P": typed(101325.0), "V": typed(0.1)},
                           "outlets": {"vapour": "waste", "liquid": "onward"}}])


def test_check_says_everything_a_run_would_refuse_each_by_its_place_and_runs_no_train(store, worker, no_pool):
    spec = _waiting_spec()
    got = pureos.check_train(spec)
    assert got.ok is False
    assert set(got.places) == {"inlet", "C1"}
    assert any("broth_flow waits" in w for w in got.places["inlet"])
    assert any("Solids centrifuge waits for Split" in w for w in got.places["C1"])
    assert got.refusals == [w for ws in got.places.values() for w in ws] or sorted(got.refusals) == sorted(
        w for ws in got.places.values() for w in ws)
    # The run refuses in the same words, every one at once: the inlet's and the units'.
    with pytest.raises(pureos.TrainRefused) as e:
        pureos.run_train(spec)
    assert str(e.value) == "; ".join(got.refusals) and dict(
        (p, [w for q, w in e.value.places if q == p]) for p, _ in e.value.places) == got.places
    assert not [c for c in worker.calls if c[0] == "train_run"]
    # Settled, nothing is refused, and still no train runs.
    done = spec_of(inlet={"kind": "typed", "params": {"broth_flow": typed(1.0), "conc.Ethanol": typed(50.0)}},
                   units=[{"id": "C1", "type": "centrifugation", "params": {"split.Ethanol": typed(0.05)}},
                          *[u.model_dump() for u in spec.units[1:]]])
    assert pureos.check_train(done).model_dump() == {"ok": True, "refusals": [], "places": {}}
    assert not [c for c in worker.calls if c[0] == "train_run"]


def test_check_puts_the_validations_refusals_and_a_stray_override_in_their_places(store, worker, no_pool):
    bad = spec_of(units=[{"id": "C1", "type": "centrifugation", "outlets": {"cake": "recycle:C1"}}])
    got = pureos.check_train(bad)
    assert not got.ok and list(got.places) == ["C1"] and "recycles to C1, itself" in got.places["C1"][0]
    stray = pureos.check_train(spec_of(), [Override(scope="pureos:unit:t9:C1", key="split.Yeast", value=0.5, by=BY,
                                                    at=AT)])
    assert list(stray.places) == ["train"] and "pureos:unit:t9:C1" in stray.refusals[0]
    # A request's override settles what the train left waiting, as the run's would.
    settle = pureos.check_train(_waiting_spec(), [
        Override(scope="pureos:unit:t1:inlet", key="broth_flow", value=1.0, by=BY, at=AT),
        Override(scope="pureos:unit:t1:C1", key="split.Ethanol", value=0.05, by=BY, at=AT)])
    assert settle.ok, settle.refusals


def test_the_check_endpoint_answers_in_the_validations_shape_and_503_when_the_worker_cannot(client, store, worker,
                                                                                            no_pool, monkeypatch):
    r = client.post("/api/pureos/train/check", json={"train": _waiting_spec().model_dump(mode="json")})
    assert r.status_code == 200 and r.json()["ok"] is False and set(r.json()["places"]) == {"inlet", "C1"}
    assert not [c for c in worker.calls if c[0] == "train_run"]
    from openferment_core.workers import WorkerError

    def down(op, args):
        raise WorkerError("STAND-IN: the worker could not start")

    monkeypatch.setattr(proforma, "call", down)
    from openferment_core.pureos import catalogue, train_spec

    monkeypatch.setattr(train_spec, "_SPECS", {})
    monkeypatch.setattr(catalogue, "_SPECS", {})
    r = client.post("/api/pureos/train/check", json={"train": spec_of().model_dump(mode="json")})
    assert r.status_code == 503 and "could not read the train's units" in r.json()["detail"]
    assert client.post("/api/pureos/train/check", json={"train": spec_of().model_dump(mode="json"),
                                                        "nonesuch": 1}).status_code == 422


# ── a run carries its tables (offline) ─────────────────────────────────


def test_a_train_run_carries_its_own_tables_beside_the_train(store, worker, no_pool):
    run = pureos.run_train(spec_of())
    t = proforma.tables_of(artifacts.get(run.artifactId))
    assert [u.id for u in run.units] == [u.id for u in t.units] == ["C1", "F1"]
    assert run.unitOrder == t.unitOrder and run.diagram is None and run.diagramNote == "not drawn: a stand-in"
    assert run.utilities is None and run.units[0].installedCost == t.units[0].installedCost
    # Read again, a kept run says the same.
    assert pureos.run_of(artifacts.get(run.artifactId)) == run


# ── a run's units read into a train (offline) ──────────────────────────


def _stream(sid, source, sink, flows):
    return {"id": sid, "source": source, "sink": sink, "phase": "l", "T": 300.0, "P": 101325.0,
            "massFlow": sum(flows.values()), "massFlows": flows, "price": None}


def _unit(uid, order, cls, ins, outs):
    return {"id": uid, "unitClass": cls, "line": None, "order": order, "ins": ins, "outs": outs,
            "installedCost": 1.0, "purchaseCost": 1.0, "heatingDuty": None, "coolingDuty": None, "power": None}


# A run of the ethanol flowsheet, written by hand (every number invented for
# the test, a balance that holds on paper): the fermenter forms ethanol from
# the glucose a mixer makes up; a pump, a beer column, a mixer, a rectifier
# and a sieve whose water-rich share runs back to the mixer; the stillage
# leaves through a pump off the path. E (ethanol) 50 formed; 2 in the
# stillage; the sieve recycles 3; 48 leave as product.
STREAMS = [
    _stream("glucose", None, "M1", {"Glucose": 100.0}),
    _stream("water", None, "M1", {"Water": 400.0}),
    _stream("solution", "M1", "R1", {"Glucose": 100.0, "Water": 400.0}),
    _stream("beer", "R1", "P1", {"Ethanol": 50.0, "Water": 400.0}),
    _stream("s1", "P1", "D1", {"Ethanol": 50.0, "Water": 400.0}),
    _stream("stillage", "D1", "P2", {"Ethanol": 2.0, "Water": 350.0}),
    _stream("waste", "P2", None, {"Ethanol": 2.0, "Water": 350.0}),
    _stream("distilled", "D1", "M2", {"Ethanol": 48.0, "Water": 50.0}),
    _stream("recycle", "U1", "M2", {"Ethanol": 3.0, "Water": 30.0}),
    _stream("s2", "M2", "D2", {"Ethanol": 51.0, "Water": 80.0}),
    _stream("bottoms", "D2", None, {"Water": 49.0}),
    _stream("s3", "D2", "U1", {"Ethanol": 51.0, "Water": 31.0}),
    _stream("ethanol", "U1", None, {"Ethanol": 48.0, "Water": 1.0}),
]
UNITS = [
    _unit("M1", 0, "Mixer", ["glucose", "water"], ["solution"]),
    _unit("R1", 1, "Fermenter", ["solution"], ["beer"]),
    _unit("P1", 2, "Pump", ["beer"], ["s1"]),
    _unit("D1", 3, "BinaryDistillation", ["s1"], ["distilled", "stillage"]),
    _unit("P2", 4, "Pump", ["stillage"], ["waste"]),
    _unit("M2", 5, "Mixer", ["distilled", "recycle"], ["s2"]),
    _unit("D2", 6, "BinaryDistillation", ["s2"], ["s3", "bottoms"]),
    _unit("U1", 7, "MolecularSieve", ["s3"], ["recycle", "ethanol"]),
]
RUN_ID = "bbbbbbbbbbbbbbb1"


def _tea(basis_flow=48.0):
    return {"teaClass": "TEA", "product": "ethanol", "feedstock": "glucose", "productPrice": 1.0,
            "basisFlow": basis_flow, "basis": "kg of ethanol", "operatingHours": 8000.0, "sales": 1.0,
            "materialCost": 1.0, "feedstockCost": 1.0, "otherMaterialCost": 0.0, "utilityCost": 1.0,
            "purchaseCost": 1.0, "installedEquipmentCost": 1.0, "FCI": 1.0, "TCI": 1.0, "FOC": 1.0,
            "laborCost": None, "capitalRecovery": 1.0, "coproductCredits": 0.0, "IRR": None, "incomeTax": None,
            "lines": []}


def _keep(aid=RUN_ID, *, tool="proforma.run", flowsheet="ethanol_glucose_v0", streams=STREAMS, units=UNITS,
          tea="default", scenario="sc-k3x9q-1") -> Artifact:
    """A run written by hand into this test's store, as the service keeps one."""
    out = {"flowsheet": flowsheet, "tablesSource": "tables written for this test",
           "tea": _tea() if tea == "default" else tea, "streams": streams, "units": units, "utilities": None,
           "diagram": None, "diagramNote": None, "unitOrder": [u["id"] for u in units],
           "tableUnits": {"massFlow": "kg/hr"}}
    inputs = [BasisInput(name="flowsheet", value=flowsheet, unit="", source=BasisSource(kind="convention"))]
    if scenario:
        inputs.append(BasisInput(name="scenario", value=scenario, unit="", source=BasisSource(kind="convention")))
    art = Artifact(id=aid, tool=tool, toolVersion="test", output=out, outputHash="0" * 64, provenance="computed",
                   createdAt="2026-10-21T10:00:00Z", durationMs=0, inputs=inputs)
    folder = artifacts.folder()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{aid}.json").write_text(art.model_dump_json(), encoding="utf-8")
    return art


def test_a_runs_train_takes_every_unit_the_product_passes_through_by_its_class(store, monkeypatch):
    monkeypatch.setattr(proforma, "call", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a simulator started")))
    _keep()
    got = pureos.from_run(RUN_ID)
    spec = got.train
    assert [(u.id, u.type) for u in spec.units] == [("P1", "pump"), ("D1", "distillation"), ("M2", "mixer"),
                                                    ("D2", "distillation"), ("U1", "molecular-sieve")]
    # The product is the run's, by the library's name, and its program the scenario's.
    assert (spec.product, spec.program, spec.id) == ("ethanol", "yeast", f"from-{RUN_ID}")
    # The inlet is the stream the product enters the first unit taken by.
    assert spec.inlet.model_dump() == {"kind": "run-stream", "ref": RUN_ID, "streamId": "beer", "vessel": None,
                                       "params": {}}
    by = {u.id: u for u in spec.units}
    assert by["D1"].outlets == {"distillate": "onward", "bottoms": "waste"}
    # The sieve's water-rich share runs back to the mixer before the rectifier, which takes several streams.
    assert by["U1"].outlets == {"regenerate": "recycle:M2", "product": "onward"}
    # Each unit reads its values from the flowsheet's own unit of the same id.
    assert all(u.readFrom is not None and u.readFrom.flowsheet == "ethanol_glucose_v0" and u.readFrom.unit == u.id
               for u in spec.units)
    unmapped = {m.unitId: m.why for m in got.unmapped}
    assert set(unmapped) == {"M1", "R1", "P2"}
    assert "no Ethanol enters M1" in unmapped["M1"] and "no Ethanol enters R1" in unmapped["R1"]
    assert "off the product's path" in unmapped["P2"]
    assert got.refusals == [] and pureos.validate(spec) == []
    assert any("The inlet is beer" in n for n in got.notes)
    assert any("package's version" in n for n in got.notes)


def test_a_unit_whose_class_no_type_holds_is_named_and_the_line_passes_through_it(store):
    units = [*UNITS[:3], _unit("H1", 3, "HXprocess", ["s1", "s9"], ["s1h", "s9c"]),
             *(dict(u, order=u["order"] + 1) for u in UNITS[3:])]
    units[4] = dict(units[4], ins=["s1h"])
    streams = [*(dict(s, sink="H1") if s["id"] == "s1" else s for s in STREAMS),
               _stream("s1h", "H1", "D1", {"Ethanol": 50.0, "Water": 400.0}), _stream("s9", None, "H1", {"Water": 1.0}),
               _stream("s9c", "H1", None, {"Water": 1.0})]
    _keep(streams=streams, units=units)
    got = pureos.from_run(RUN_ID, train_id="tr-mine")
    assert got.train.id == "tr-mine" and [u.id for u in got.train.units][:2] == ["P1", "D1"]
    assert {m.unitId: m.unitClass for m in got.unmapped}["H1"] == "HXprocess"
    assert "HXprocess is no unit type" in {m.unitId: m.why for m in got.unmapped}["H1"]
    assert got.train.units[0].outlets == {"outlet": "onward"}
    assert any("H1 (HXprocess), which the train leaves out" in n for n in got.notes)


def test_a_train_run_is_read_back_into_its_own_units_with_no_package_to_read_from(store, worker, no_pool):
    run = pureos.run_train(three_units())
    got = pureos.from_run(run.artifactId)
    assert [(u.id, u.type) for u in got.train.units] == [("C1", "centrifugation"), ("F1", "flash"), ("D1", "drying-drum")]
    assert all(u.readFrom is None for u in got.train.units) and got.train.product == "ethanol"
    assert got.train.inlet.ref == run.artifactId and got.train.inlet.streamId == "inlet"
    assert any("class's own defaults" in n for n in got.notes)


def test_a_run_no_train_is_read_from_is_refused_in_words(store, monkeypatch):
    with pytest.raises(pureos.RunNotOnFile, match="there is no kept artifact cccccccccccccccc here"):
        pureos.from_run("c" * 16)
    _keep("ddddddddddddddd1", tea=None)
    with pytest.raises(pureos.TrainRefused, match="names no product to trace"):
        pureos.from_run("ddddddddddddddd1")
    _keep("ddddddddddddddd2", units=[dict(u, unitClass="StandIn") for u in UNITS])
    with pytest.raises(pureos.TrainRefused, match="no unit of run ddddddddddddddd2 that its product passes through"):
        pureos.from_run("ddddddddddddddd2")
    elsewhere = [dict(s, massFlows={("Unobtainium" if k == "Ethanol" else k): v for k, v in s["massFlows"].items()})
                 for s in STREAMS]
    _keep("ddddddddddddddd3", streams=elsewhere, tea=_tea())
    with pytest.raises(pureos.TrainRefused, match="traces Unobtainium, which no product a train traces here is"):
        pureos.from_run("ddddddddddddddd3")
    other = _keep("ddddddddddddddd4", tool="convert_units")
    with pytest.raises(pureos.TrainRefused, match="is a convert_units artifact"):
        pureos.from_run(other.id)


def test_the_from_run_endpoint_answers_200_404_and_422_and_starts_no_simulator(client, store, monkeypatch):
    monkeypatch.setattr(proforma, "call", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a simulator started")))
    _keep()
    r = client.post("/api/pureos/train/from-run", json={"artifactId": RUN_ID, "trainId": "tr-1"})
    assert r.status_code == 200 and r.json()["train"]["id"] == "tr-1" and len(r.json()["train"]["units"]) == 5
    assert client.post("/api/pureos/train/from-run", json={"artifactId": "e" * 16}).status_code == 404
    _keep("ddddddddddddddd1", tea=None)
    bad = client.post("/api/pureos/train/from-run", json={"artifactId": "ddddddddddddddd1"})
    assert bad.status_code == 422 and "names no product" in bad.json()["detail"]
    assert client.post("/api/pureos/train/from-run", json={"artifactId": RUN_ID, "units": []}).status_code == 422


def test_a_composite_runs_train_reads_no_unit_of_the_composite_and_takes_its_train_runs_own(store, worker, no_pool,
                                                                                             monkeypatch):
    """Findings 3, 14 and 24 (§5.R part a): a `custom_train_v1` run's units
    are its fermenter's and its train run's, and the worker reads no unit of
    the composite; a train read from it reads none either, takes each unit's
    named records and flowsheet unit from the train run the composite names,
    says so, and checks clean. `validate` refuses a unit reading a flowsheet
    built from parts."""
    # The worker refuses the composite's units, as the real one does.
    real_answer = worker.__class__.__call__

    def refuse_composite(self, op, args):
        if op == "flowsheet_unit_values" and args["flowsheet"] == "custom_train_v1":
            from openferment_core.workers import WorkerError

            raise WorkerError("Refused: custom_train_v1 is built from a vessel design and a train run: its units are "
                              "the fermenter and that train's own, read from the train run")
        return real_answer(self, op, args)

    monkeypatch.setattr(worker.__class__, "__call__", refuse_composite)
    # The train run the composite names: D1, D2 and U1, read from the package's own units.
    reads = {"D1": "D302", "D2": "D303", "U1": "U301"}
    train_run = pureos.run_train(spec_of(units=[
        {"id": uid, "type": "molecular-sieve" if uid == "U1" else "distillation",
         "readFrom": {"flowsheet": "ethanol_glucose_v0", "unit": pkg},
         "params": {"k": typed(2.0)} if uid != "U1" else {},
         "outlets": {"regenerate": "waste", "product": "onward"} if uid == "U1" else {}}
        for uid, pkg in reads.items()]))
    composite = _keep(flowsheet="custom_train_v1", scenario=None)
    composite.inputs.append(BasisInput(name="train run", value=train_run.artifactId, unit="", source=BasisSource(
        kind="artifact", id=train_run.artifactId)))
    (artifacts.folder() / f"{RUN_ID}.json").write_text(composite.model_dump_json(), encoding="utf-8")
    got = pureos.from_run(RUN_ID)
    by = {u.id: u for u in got.train.units}
    assert not [u.id for u in got.train.units if u.readFrom is not None and u.readFrom.flowsheet == "custom_train_v1"]
    assert {uid: (u.readFrom.flowsheet, u.readFrom.unit) for uid, u in by.items() if u.readFrom is not None} == {
        uid: ("ethanol_glucose_v0", pkg) for uid, pkg in reads.items()}
    assert any(train_run.artifactId in n and "custom_train_v1" in n for n in got.notes), got.notes
    assert got.refusals == []
    checked = pureos.check_train(got.train)
    assert not any("built from a vessel design" in w for w in checked.refusals), checked.refusals
    # A unit that reads a flowsheet built from parts is refused in words.
    bad = TrainSpec.model_validate({**got.train.model_dump(), "units": [
        {**got.train.units[0].model_dump(), "readFrom": {"flowsheet": "custom_train_v1", "unit": "P1"}},
        *(u.model_dump() for u in got.train.units[1:])]})
    assert any("built from a vessel design and a train run" in w for w in pureos.validate(bad)), pureos.validate(bad)


# ── the real worker (sim) ──────────────────────────────────────────────


@pytest.mark.sim
def test_a_shelf_runs_train_read_from_the_run_gives_the_packages_own_purity(real):
    """The glucose-to-ethanol flowsheet run on STAND-IN inputs: its train,
    read from the run by class, takes the package's columns, its sieve and
    the units around them, each reading the package's own values, and run
    again by pureOS delivers the package's own purity on the run's beer."""
    run = proforma.run_flowsheet("ethanol_glucose_v0", [
        InputAssumption(key=k, value=v, low=v, high=v, by=BY, at=AT, note=STANDIN) for k, v in ETHANOL_STANDIN.items()],
        samples=1)
    got = pureos.from_run(run.id)
    spec = got.train
    by = {u.id: u for u in spec.units}
    assert (by["D302"].type, by["D303"].type, by["U301"].type) == ("distillation", "distillation", "molecular-sieve")
    assert spec.inlet.streamId == "beer" and got.refusals == []
    unmapped = {m.unitId: m.unitClass for m in got.unmapped}
    assert unmapped.get("R1") == "Fermenter" and unmapped.get("H302") == "HXprocess"
    # The sieve's water-rich share runs back before the rectifier, as the package recycles it: BioSTEAM's
    # MolecularSieve sends its split to outlet 0, the regenerate, and the dehydrated ethanol goes on by outlet 1,
    # the product (§5.R part a, finding 8).
    assert by["U301"].outlets["product"] == "onward" and by["U301"].outlets["regenerate"].startswith("recycle:")
    from openferment_core.models import ParamResolveRequest
    from openferment_core import params
    from openferment_core.pureos import catalogue

    sieve = {x.key: x for x in params.scope(f"pureos:unit:{spec.id}:U301", ParamResolveRequest(train=spec)).values}
    assert sieve["split.Ethanol"].value < sieve["split.Water"].value  # the package's: outlet 0 is water-rich
    ports = {p.name: p for p in catalogue.entry("molecular-sieve").ports if p.side == "out"}
    assert ports["product"].onward and "dehydrated" in ports["product"].what
    assert "dehydrated" not in ports["regenerate"].what
    assert pureos.check_train(spec).ok
    out = pureos.run_train(spec)
    package = next(s for s in proforma.tables_of(run).streams if s.id == "ethanol")
    assert out.purity.productFraction == pytest.approx(package.massFlows["Ethanol"] / package.massFlow, rel=MEASURED)
    assert out.units and out.unitOrder == [u.id for u in out.units]


@pytest.mark.sim
def test_a_composite_runs_train_reads_no_unit_of_the_composite_on_the_real_worker(real, monkeypatch):
    """Findings 3, 14 and 24 (§5.R part a), on the real worker: a train read
    from a `custom_train_v1` run (an NREL vessel and the three-unit train)
    reads no unit of the composite, which the worker refuses to read, so no
    unit of it is held for that; what the train run's units took from a
    person is named in its notes, and waits for a person here."""
    from openferment_core.pureos import train_spec
    from test_custom_train import POOL, _sim_parts, request

    monkeypatch.setattr(train_spec, "_UNITS", {})
    p = _sim_parts(False)
    composite = proforma.run(request(p, samples=1), pool=POOL)
    got = pureos.from_run(composite.artifactId)
    assert [u.id for u in got.train.units] == ["C1", "F1", "D1"]
    assert all(u.readFrom is None for u in got.train.units) and got.refusals == []
    assert any(p.train in n and "custom_train_v1" in n and "not carried" in n for n in got.notes), got.notes
    checked = pureos.check_train(got.train)
    assert not any("built from a vessel design" in w for w in checked.refusals), checked.refusals
