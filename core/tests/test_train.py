"""pureOS's train: data, checked, resolved, run in the worker, kept as one
artifact, and read by every reader (OF-BLD-020 §5.2; D9, D10, E.2‴, E.3‴).

Offline: `validate` names every refusal at once, in words; the inlet from a
kept simulation is its broth at harvest, read as the program's chemicals; a
broth flow nobody gave holds the run back, naming what would bind it; a
train's unit scope expands per component over the train's chemicals and binds
records by the train's program, product and step; `run_train` keeps one
`pureos.train_run` artifact on a stand-in worker, its basis naming every unit's
type, class and id and every value's source; `train_of` reads a train run by
pass, as it reads a Proforma run; the endpoints answer 422, 409 and 503 in
words.

Marked `sim` (the real Proforma worker): a three-unit train (solids
centrifuge, flash, drum dryer) on a stand-in yeast broth converges with each
unit's recovery a share and the overall the product of the onward fractions
along its path; a unit that cannot run refuses the train naming the unit and
BioSTEAM's words; a simulation's harvest takes its broth flow from a vessel
design; and the ethanol train built from the catalogue on the beer of
`ethanol_glucose_v0` (beer column and rectifier as `BinaryDistillation`, the
molecular sieve, each reading its values from the package's own unit) gives
the package's own ethanol purity on the same inlet.

Every STAND-IN here is an `assumption` of this test, typed under the
fixture's name and noted STAND-IN; none is a measurement, a published value
or a result, and only what the code does with it is asserted.
"""
from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, fermos, intake, params, proforma, pureos
from openferment_core.models import (
    BasisSource,
    InputAssumption,
    Override,
    ParamResolveRequest,
    SimulationRequest,
    TrainParam,
    TrainSpec,
    TrainUnitSpec,
)
from openferment_core.pureos import catalogue, train_spec
from test_catalogue import StandInWorker

CORE = Path(__file__).resolve().parent.parent
PKG = CORE / "openferment_core"
BY = "openFerment test fixture"
AT = "2026-10-21"
STANDIN = "STAND-IN for this test: an assumption typed to exercise the code, not a result"
# STAND-IN parameters for fermos.simulate (as test_vessel's), none a result.
SIM_STANDIN = {"mu_max": 0.3, "ks": 0.5, "yxs": 0.1, "alpha": 2.0, "yps": 0.45, "p_max": 95.0, "x0": 0.5,
               "s0": 100.0, "p0": 0.0}


def typed(v):
    return {"value": v, "by": BY, "at": AT, "note": STANDIN}


def spec_of(**kw) -> TrainSpec:
    base = {"id": "t1", "name": "A test train", "program": "yeast", "product": "ethanol",
            "inlet": {"kind": "typed", "params": {"broth_flow": typed(1.0), "conc.Yeast": typed(10.0),
                                                  "conc.Ethanol": typed(50.0), "conc.Glucose": typed(5.0)}},
            "units": [{"id": "C1", "type": "centrifugation", "params": {"split.Yeast": typed(0.9)}},
                      {"id": "F1", "type": "flash", "params": {"P": typed(101325.0), "V": typed(0.1)},
                       "outlets": {"vapour": "waste", "liquid": "onward"}}]}
    return TrainSpec.model_validate({**base, **kw})


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


# ── a stand-in worker ──────────────────────────────────────────────────

# Stand-in versions and stream defaults: words and numbers for this test.
VERSIONS = {"biosteam": "0.0-standin", "thermosteam": "0.0-standin", "biorefineries": "0.0-standin"}
STREAM_T, STREAM_P = 298.15, 101325.0
# The share of the product a stand-in unit sends off its path.
LOSS = 0.1
# A STAND-IN of a class's own split table, by component (as PressureFilter
# fills one when none is given): invented for the test, none a result.
TABLE = {"Water": 0.04, "Ethanol": 0.04, "Glucose": 0.03, "Yeast": 0.98, "Octane": 0.04}


class TrainWorker(StandInWorker):
    """Answers `catalogue_specs` as test_catalogue's stand-in does, and
    `train_specs`, `flowsheet_unit_values` and `train_run` with STAND-IN
    tables: each unit sends everything on but LOSS of the product, which
    leaves by its first other outlet; no BioSTEAM runs."""

    def __init__(self, fail: str | None = None):
        super().__init__()
        self.fail = fail

    def __call__(self, op, args):
        if op == "catalogue_specs":
            # What a class requires has no default of its own, as BioSTEAM's
            # flash, columns and evaporator give none: None here too.
            got = super().__call__(op, args)
            e = catalogue.entry(args["type"])
            needed = {k for alts, _ in e.needs for alt in alts for k in alt}
            for k in needed & set(got["defaults"]):
                got["defaults"][k] = {"value": None, "from": STANDIN}
            # §5.R: a class that fills its own split table when none is given
            # (PressureFilter) has it read by component, as the worker reads it.
            for p in e.params:
                if p.per == "component" and p.bst == "split" and "library-default" in p.rule:
                    got["defaults"][p.key] = {"value": None, "from": STANDIN, "byComponent": dict(TABLE)}
            return got
        self.calls.append((op, args))
        if op == "train_specs":
            return {"chemicals": ["Water", "Ethanol", "Glucose", "Yeast", "Octane"], "T": STREAM_T, "P": STREAM_P,
                    "phase": "l", "from": STANDIN, "versions": VERSIONS}
        if op == "flowsheet_unit_values":
            return {"flowsheet": args["flowsheet"], "versions": VERSIONS, "units": {
                u["unit"]: {"unitClass": catalogue.entry(u["type"]).cls, "unread": {"Lr": STANDIN},
                            "values": {"light_key": "Ethanol", "heavy_key": "Water", "k": 1.5, "y_top": 0.6,
                                       "x_bot": 0.01, "split.Ethanol": 0.2, "split.Water": 0.9}}
                for u in args["units"]}}
        if op == "train_run":
            if self.fail:
                from openferment_core.workers import WorkerError

                raise WorkerError(self.fail)
            return self.run(args)
        raise AssertionError(f"the stand-in worker has no op {op}")

    @staticmethod
    def run(args):
        inlet = args["inlet"]
        flows = dict(inlet["flows"] or {k: v * inlet["brothFlow"] for k, v in inlet["concentrations"].items()})
        if inlet.get("balance"):
            flows[inlet["balance"]] = 1000.0 * inlet["brothFlow"]  # a STAND-IN balance
        product = args["product"]
        streams = [{"id": "inlet", "source": None, "sink": args["units"][0]["id"], "phase": "l", "T": inlet["T"],
                    "P": inlet["P"], "massFlow": sum(flows.values()), "massFlows": flows, "price": None}]
        units, outlets, costs, current = [], {}, [], flows
        for n, u in enumerate(args["units"]):
            names = [p.name for p in catalogue.entry(u["type"]).ports if p.side == "out"]
            onward = next(k for k, r in u["outlets"].items() if r == "onward")
            lost = next(k for k in names if k != onward)
            on = {k: v * (1 - LOSS) if k == product else v for k, v in current.items()}
            off = {product: current.get(product, 0.0) * LOSS}
            ids = {k: f"{u['id']}_{k.replace('-', '_')}" for k in names}
            nxt = args["units"][n + 1]["id"] if n + 1 < len(args["units"]) else None
            for k in names:
                fl = on if k == onward else off if k == lost else {}
                streams.append({"id": ids[k], "source": u["id"], "sink": nxt if k == onward else None, "phase": "l",
                                "T": inlet["T"], "P": inlet["P"], "massFlow": sum(fl.values()), "massFlows": fl,
                                "price": None})
            ins = ["inlet"] if n == 0 else [outlets[args["units"][n - 1]["id"]][next(
                k for k, r in args["units"][n - 1]["outlets"].items() if r == "onward")]]
            units.append({"id": u["id"], "unitClass": catalogue.entry(u["type"]).cls, "line": None, "order": n,
                          "ins": ins, "outs": [ids[k] for k in names], "installedCost": 2.0, "purchaseCost": 1.0,
                          "heatingDuty": None, "coolingDuty": None, "power": None})
            outlets[u["id"]] = ids
            costs.append({"unit": u["id"], "unitClass": catalogue.entry(u["type"]).cls, "purchaseCost": 1.0,
                          "installedCost": 2.0, "items": {"STAND-IN item": 1.0}, "utilityCost": 0.0})
            current = on
        last = args["units"][-1]
        product_stream = outlets[last["id"]][next(k for k, r in last["outlets"].items() if r == "onward")]
        return {"tablesSource": STANDIN, "streams": streams, "units": units, "utilities": None, "diagram": None,
                "diagramNote": "not drawn: a stand-in", "unitOrder": [u["id"] for u in args["units"]],
                "tableUnits": {"massFlow": "kg/hr"},
                "inlet": {"flows": flows, "water": flows.get(inlet.get("balance") or "", None), "waterNote": STANDIN,
                          "T": inlet["T"], "P": inlet["P"], "phase": inlet["phase"], "volume": inlet["brothFlow"]},
                "productStream": product_stream, "outlets": outlets, "costs": costs, "utilitySettings": {},
                "versions": VERSIONS}


@pytest.fixture()
def worker(monkeypatch):
    w = TrainWorker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(catalogue, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_UNITS", {})
    return w


@pytest.fixture()
def no_pool(monkeypatch):
    monkeypatch.setattr(train_spec, "_pool", lambda: None)


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


# ── a train is data: validate (offline) ────────────────────────────────


def test_a_well_formed_train_validates_with_no_refusal():
    v = pureos.validation(spec_of())
    assert v.ok and v.refusals == []


def test_validate_names_every_refusal_at_once_in_words():
    bad = spec_of(units=[
        {"id": "C1", "type": "centrifugation", "outlets": {"cake": "recycle:F1", "liquid": "onward", "lees": "waste"},
         "params": {"split": typed(0.5), "nonesuch": typed(1.0)}},
        {"id": "C1", "type": "flash", "outlets": {"vapour": "onward", "liquid": "onward"}},
        {"id": "F1", "type": "flashy"},
        {"id": "M1", "type": "flash", "outlets": {"vapour": "recycle:C1", "liquid": "waste"}},
        {"id": "inlet", "type": "tank", "outlets": {"outlet": "somewhere"}},
        {"id": "S1", "type": "molecular-sieve", "outlets": {"regenerate": "recycle:M1"},
         "readFrom": {"flowsheet": "corn_drygrind", "unit": "U301"}, "records": {"approx_duty": ["r-x"]}},
    ])
    said = pureos.validate(bad)
    text = " | ".join(said)
    expected = [
        "unit C1's outlet cake recycles to F1, a unit after it: a recycle goes back to an earlier unit (D9), and a "
        "forward one is refused",
        "unit C1 (centrifugation) has no outlet 'lees'; its outlets are cake, liquid",
        "split is set per component, as split.<component>: the template itself takes no value",
        "unit C1 (centrifugation) has no parameter 'nonesuch'",
        "two units are named C1",
        "unit C1 (flash) sends 2 outlets on (vapour, liquid): a unit of a train sends one on",
        "there is no unit type 'flashy' in pureOS's catalogue",
        "unit M1 (flash) sends no outlet on",
        "inlet names the train's inlet, not a unit",
        "unit inlet's outlet outlet goes onward, to waste or to recycle:<an earlier unit>; 'somewhere' is none of them",
        "unit S1's outlet regenerate recycles to M1 (flash), whose inlet takes one stream",
        "unit S1 reads from corn_drygrind, a reference biorefinery",
        "unit S1: approx_duty binds from no record field, so no record can be named for it",
    ]
    for words in expected:
        assert words in text, (words, said)
    assert not pureos.validation(bad).ok
    assert pureos.validate(spec_of(units=[])) == ["a train holds at least one unit"]


def test_the_inlet_is_held_to_its_kind():
    said = " | ".join(pureos.validate(spec_of(inlet={"kind": "simulation", "streamId": "beer", "params": {
        "conc.Ethanol": typed(1.0)}})))
    assert "a simulation inlet names its artifact (ref)" in said
    assert "a stream id belongs to a run-stream inlet" in said
    assert "the inlet (simulation) has no parameter 'conc.Ethanol'" in said
    said = " | ".join(pureos.validate(spec_of(inlet={"kind": "run-stream", "ref": "a" * 16, "vessel": "b" * 16})))
    assert "a run's stream as the inlet names the stream (streamId)" in said
    assert "a vessel gives the broth flow of a simulation's harvest alone" in said
    # OF-BLD-020 §6.2: a run-stream's ref is a run's artifact id or a scenario's id, whose broth it may take.
    said = " | ".join(pureos.validate(spec_of(inlet={"kind": "run-stream", "ref": "not an id!"})))
    assert "a run-stream inlet's ref is a run's artifact id (16 hex) or a scenario's id" in said
    assert "names the stream (streamId)" not in said
    said = " | ".join(pureos.validate(spec_of(inlet={"kind": "simulation", "ref": "sc-yeast-1"})))
    assert "the inlet's ref is an artifact id (16 hex); 'sc-yeast-1' is not one" in said
    assert pureos.validate(spec_of(inlet={"kind": "run-stream", "ref": "sc-yeast-1"})) == []


def test_a_train_refuses_extra_fields_and_a_true_or_false_value():
    with pytest.raises(ValueError):
        TrainSpec.model_validate({**spec_of().model_dump(), "price": 1.0})
    with pytest.raises(ValueError, match="never true or false"):
        spec_of(units=[{"id": "C1", "type": "centrifugation", "params": {"split.Yeast": typed(True)}}])


def test_the_validate_endpoint_returns_the_refusals_and_runs_nothing(client, monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("validate started the simulator")

    monkeypatch.setattr(proforma, "call", refuse)
    ok = client.post("/api/pureos/train/validate", json=spec_of().model_dump(mode="json"))
    assert ok.status_code == 200 and ok.json() == {"ok": True, "refusals": [], "places": {}}
    bad = spec_of(units=[{"id": "C1", "type": "centrifugation", "outlets": {"cake": "recycle:C1"}}])
    r = client.post("/api/pureos/train/validate", json=bad.model_dump(mode="json")).json()
    assert r["ok"] is False and any("recycles to C1, itself" in w for w in r["refusals"])
    # OF-BLD-020 §5.3: each refusal by its place, so the Builder says a unit's on its card.
    assert r["places"]["C1"] == [w for w in r["refusals"] if w.startswith("unit C1")]


# ── the inlet (offline) ────────────────────────────────────────────────


def real_simulation(**more):
    """A batch_v1 run through the real fermos.simulate (scipy, no BioSTEAM)
    on STAND-IN overrides."""
    values = {**SIM_STANDIN, **more}
    scope = "fermos:family:batch_v1"
    return fermos.simulate(SimulationRequest(family="batch_v1", product="ethanol", sugar="glucose", overrides=[
        Override(scope=scope, key=k, value=v, by=BY, at=AT, note=STANDIN) for k, v in values.items()]))


def test_the_inlet_from_a_simulation_is_its_broth_at_harvest_read_as_the_programs_chemicals(store, worker):
    sim = real_simulation()
    art = artifacts.get(sim.artifactId)
    spec = spec_of(inlet={"kind": "simulation", "ref": sim.artifactId, "params": {"broth_flow": typed(2.0)}})
    inlet = pureos.inlet_stream(spec)
    h = fermos.harvest(art)
    at = {"hour": h.hour, "state": {x.state: x.value for x in h.states}}
    assert inlet.read.harvestHour == pytest.approx(art.output["harvestH"])
    assert inlet.read.concentrations == pytest.approx({"Yeast": at["state"]["X"], "Ethanol": at["state"]["P"],
                                                       "Glucose": at["state"]["S"]})
    assert inlet.chemicals == ["Ethanol", "Glucose", "Water", "Yeast"]
    assert inlet.worker["balance"] == "Water" and inlet.worker["brothFlow"] == 2.0
    assert (inlet.worker["T"], inlet.worker["P"]) == (STREAM_T, STREAM_P)
    by = {b.name: b for b in inlet.basis}
    assert by["inlet"].source.kind == "artifact" and by["inlet"].source.id == sim.artifactId
    assert by["inlet.conc.Yeast"].source == BasisSource(kind="artifact", id=sim.artifactId, note=(
        f"X of simulation {sim.artifactId} at {at['hour']:.6g} h, in g L⁻¹ as the simulation keeps it, read as Yeast"))
    assert by["inlet.broth_flow"].source.kind == "assumption" and by["inlet.broth_flow"].source.by == BY
    assert by["inlet.harvest_hour"].source.id == sim.artifactId
    assert by["inlet.T"].source.kind == "model" and by["cells read as"].value == "Yeast"
    assert "absent" in by["inlet absent"].value
    # A person's hour reads the broth at that hour, and says so.
    later = pureos.inlet_stream(spec.model_copy(update={"inlet": spec.inlet.model_copy(update={"params": {
        **spec.inlet.params, "harvest_hour": spec.inlet.params["broth_flow"].model_copy(update={"value": 4.0})}})}))
    assert later.read.concentrations["Ethanol"] == pytest.approx(
        {x.state: x.value for x in fermos.harvest(art, 4.0).states}["P"])
    assert any("an hour openFerment test fixture named" in n for n in later.read.notes)


def test_a_waiting_broth_flow_refuses_the_run_naming_it_and_what_would_bind_it(store, worker):
    sim = real_simulation()
    spec = spec_of(inlet={"kind": "simulation", "ref": sim.artifactId})
    with pytest.raises(pureos.TrainRefused, match=r"the inlet: broth_flow waits .*name a vessel design of simulation "
                                                  rf"{sim.artifactId} \(its working volume × vessels ÷ cycle time\)"):
        pureos.run_train(spec)
    assert not [c for c in worker.calls if c[0] == "train_run"]


def test_an_inlet_that_cannot_be_read_is_refused_in_words(store, worker):
    with pytest.raises(pureos.TrainRefused, match="there is no kept artifact aaaaaaaaaaaaaaaa here"):
        pureos.inlet_stream(spec_of(inlet={"kind": "simulation", "ref": "a" * 16, "params": {"broth_flow": typed(1.0)}}))
    sim = real_simulation()
    with pytest.raises(pureos.TrainRefused, match="makes ethanol; the train's product is phb"):
        pureos.inlet_stream(spec_of(product="phb", inlet={"kind": "simulation", "ref": sim.artifactId}))
    with pytest.raises(pureos.TrainRefused, match="a typed inlet names at least one component"):
        pureos.inlet_stream(spec_of(inlet={"kind": "typed", "params": {"broth_flow": typed(1.0)}}))


# ── a train's unit scope (offline) ─────────────────────────────────────


def _record(rid, field, value, unit, words, paper="Q1"):
    return {"id": rid, "field": field, "value": value, "unit": unit, "paperId": paper, "quote": words,
            "method": None, "conditions": None, "provenance": "unverified", "status": "unverified"}


def stand_in_pool(*records):
    return SimpleNamespace(records=list(records), records_by_id={r["id"]: r for r in records})


def test_a_units_scope_expands_over_the_trains_chemicals_and_binds_the_products_split_by_its_step(store, worker,
                                                                                               monkeypatch):
    pool = stand_in_pool(
        _record("r-st-1", "step_recovery", 90.0, "%", "after centrifugation the broth kept"),
        _record("r-st-2", "step_recovery", 80.0, "%", "after centrifugation the broth kept"),
        _record("r-st-3", "step_recovery", 50.0, "%", "after the chromatography column"),
        _record("r-st-4", "step_recovery", 70.0, "%", "after centrifugation", paper="A1"),
    )
    monkeypatch.setattr(train_spec, "_pool", lambda: pool)
    spec = spec_of()
    s = params.scope("pureos:unit:t1:C1", ParamResolveRequest(train=spec))
    keys = [sp.key for sp in s.specs]
    assert [k for k in keys if k.startswith("split.")] == ["split.Ethanol", "split.Glucose", "split.Water",
                                                            "split.Yeast"]
    v = {x.key: x for x in s.values}
    eth = v["split.Ethanol"]
    # The liquid goes on, so the split to the cake (outlet 0) is one less the recovery.
    assert eth.origin == "record" and eth.recordIds == ["r-st-1", "r-st-2"]
    assert (eth.value, eth.low, eth.high) == pytest.approx((0.15, 0.1, 0.2))
    assert "one less it: the split is to outlet cake, and the product goes on by liquid" in eth.detail
    assert "1 naming another step or none" in eth.detail and "1 not on the yeast program's papers" in eth.detail
    # Another component's split nobody set is left to the class, which reads it as none to outlet 0; the
    # water's is the cake moisture's (§5.R part a, finding 6).
    assert v["split.Glucose"].origin == "not-read" and "as none of it to outlet cake" in v["split.Glucose"].detail
    assert v["split.Water"].origin == "not-read" and "moisture content sets the water" in v["split.Water"].detail
    bare = {x.key: x for x in params.scope("pureos:unit:t1:C1", ParamResolveRequest(train=spec_of(units=[
        {"id": "C1", "type": "centrifugation", "outlets": {"cake": "waste", "liquid": "onward"}}]))).values}
    assert bare["split.Water"].origin == "not-read"
    assert v["moisture_content"].origin == "library-default"
    # The cake routed on takes the recovery as it is.
    cake_on = spec_of(units=[{"id": "C1", "type": "centrifugation", "outlets": {"cake": "onward", "liquid": "waste"}}])
    on = {x.key: x for x in params.scope("pureos:unit:t1:C1", ParamResolveRequest(train=cake_on)).values}
    assert on["split.Ethanol"].value == pytest.approx(0.85)
    # Records named for a key bind it alone; one that cannot is refused in words.
    named = spec_of(units=[{"id": "C1", "type": "centrifugation", "records": {"split.Ethanol": ["r-st-1"]}}])
    got = {x.key: x for x in params.scope("pureos:unit:t1:C1", ParamResolveRequest(train=named)).values}
    assert got["split.Ethanol"].recordIds == ["r-st-1"] and got["split.Ethanol"].value == pytest.approx(0.1)
    wrong = spec_of(units=[{"id": "C1", "type": "centrifugation", "records": {"split.Ethanol": ["r-st-3", "r-zz"]}}])
    with pytest.raises(params.ParamRefused) as refused:
        params.scope("pureos:unit:t1:C1", ParamResolveRequest(train=wrong))
    assert "record r-zz is not in the evidence pool here" in str(refused.value)
    assert "record r-st-3: naming another step or none" in str(refused.value)


def test_percentages_bind_shares_and_a_disruption_yield_binds_one_pass_alone(store, worker, monkeypatch):
    pool = stand_in_pool(
        _record("r-cr-1", "step_recovery", 95.0, "%", "the chromatography step recovered"),
        _record("r-cr-2", "product_purity", 98.0, "%", "after chromatography the pool was"),
        _record("r-cm-1", "cake_moisture", 60.0, "%", "the centrifuge cake held"),
        _record("r-dy-1", "disruption_protein_yield", 40.0, "% of total protein", "released by homogenisation"),
        _record("r-pc-1", "partition_coefficient", 3.0, "", "partitioned into the solvent"),
        _record("r-bad", "product_purity", 0.98, "g g-1", "after chromatography"),
    )
    monkeypatch.setattr(train_spec, "_pool", lambda: pool)

    def values(unit):
        return {x.key: x for x in params.scope(f"pureos:unit:t1:{unit['id']}",
                                               ParamResolveRequest(train=spec_of(units=[unit]))).values}

    chrom = values({"id": "K1", "type": "chromatography"})
    assert chrom["recovery"].value == pytest.approx(0.95) and chrom["recovery"].recordIds == ["r-cr-1"]
    assert "each a percentage over a hundred, a share" in chrom["recovery"].detail
    assert chrom["purity"].value == pytest.approx(0.98) and "1 in g g-1, not a percentage" in chrom["purity"].detail
    cake = values({"id": "C1", "type": "centrifugation"})
    assert cake["moisture_content"].value == pytest.approx(0.6) and cake["moisture_content"].origin == "record"
    lle = values({"id": "L1", "type": "lle"})
    assert lle["partition_coefficient.Ethanol"].value == pytest.approx(3.0)
    assert lle["partition_coefficient.Water"].origin == "library-default"
    one = values({"id": "H1", "type": "cell-disruption", "params": {"passes": typed(1.0)}})
    assert one["release"].value == pytest.approx(0.4) and one["release"].recordIds == ["r-dy-1"]
    two = values({"id": "H1", "type": "cell-disruption", "params": {"passes": typed(2.0)}})
    assert two["release"].origin == "waiting" and "which is one pass's only when the unit runs one pass" in two[
        "release"].detail


def test_the_scope_names_its_train_its_unit_and_its_inlet(store, worker, no_pool):
    spec = spec_of()
    with pytest.raises(params.ParamRefused, match="this scope names train t2; the train sent is t1"):
        params.scope("pureos:unit:t2:C1", ParamResolveRequest(train=spec))
    with pytest.raises(params.ScopeUnknown, match="train t1 has no unit Z9; its units are C1, F1 and its inlet"):
        params.scope("pureos:unit:t1:Z9", ParamResolveRequest(train=spec))
    with pytest.raises(params.ParamRefused, match="unit C1 of train t1 is a centrifugation, not a flash"):
        params.scope("pureos:unit:t1:C1", ParamResolveRequest(train=spec, unitType="flash"))
    with pytest.raises(params.ScopeUnknown, match="resolved with its train"):
        params.scope("pureos:unit:t1:inlet", ParamResolveRequest())
    inlet = params.scope("pureos:unit:t1:inlet", ParamResolveRequest(train=spec))
    v = {x.key: x for x in inlet.values}
    assert inlet.waiting == ["broth_flow"] and v["conc.Ethanol"].origin == "not-read"
    assert v["T"].origin == "library-default" and v["T"].value == STREAM_T
    # The panel's resolve refuses what the run refuses, in the unit's needs.
    flash = "pureos:unit:t1:F1"
    with pytest.raises(params.ParamRefused, match="Flash drum waits for"):
        params.resolve_scope(flash, ParamResolveRequest(train=spec, overrides=[
            Override(scope=flash, key="P", value=101325.0, by=BY, at=AT)]))


def test_the_get_scope_takes_the_train_as_json(client, store, worker, no_pool):
    spec = spec_of()
    r = client.get("/api/params/pureos:unit:t1:C1", params={"train": spec.model_dump_json()})
    assert r.status_code == 200 and "split.Ethanol" in [s["key"] for s in r.json()["specs"]]
    bad = client.get("/api/params/pureos:unit:t1:C1", params={"train": "{\"id\": 1}"})
    assert bad.status_code == 422 and "a pureOS train as JSON" in bad.json()["detail"]


# ── the run (offline, a stand-in worker) ───────────────────────────────


def test_a_run_keeps_one_artifact_whose_basis_names_every_unit_and_source(store, worker, no_pool):
    spec = spec_of()
    run = pureos.run_train(spec, [Override(scope="pureos:unit:t1:F1", key="V", value=0.2, by="Another Person", at=AT,
                                           note=STANDIN)])
    art = artifacts.get(run.artifactId)
    assert art.tool == "pureos.train_run" and run.provenance == "demo" == art.provenance
    by = {b.name: b for b in art.inputs}
    assert by["C1 type"].value == "centrifugation" and by["C1 class"].value == "SolidsCentrifuge"
    assert by["C1 class"].source == BasisSource(kind="model", id="biosteam@0.0-standin",
                                                note="BioSTEAM's SolidsCentrifuge, built as unit C1")
    assert (by["C1 outlet cake"].value, by["C1 outlet liquid"].value) == ("waste", "onward")
    assert by["C1.split.Yeast"].source.kind == "assumption" and by["C1.split.Yeast"].source.by == BY
    # The request's override replaces the train's typed value of its key.
    assert by["F1.V"].value == 0.2 and by["F1.V"].source.by == "Another Person"
    assert by["F1.vessel_material"].source.kind == "model" and by["F1.vessel_material"].source.id.startswith("biosteam@")
    assert {"biosteam", "thermosteam", "biorefineries", "utility prices and cost index", "diagram"} <= set(by)
    assert json.loads(by["train"].value)["units"][0]["id"] == "C1"
    # A class's own default is left to the class; every other value is passed.
    [(_, sent)] = [c for c in worker.calls if c[0] == "train_run"]
    assert sent["units"][1]["values"] == {"P": 101325.0, "V": 0.2}
    assert sent["units"][0]["outlets"] == {"cake": "waste", "liquid": "onward"}
    assert sent["inlet"]["concentrations"] == {"Ethanol": 50.0, "Glucose": 5.0, "Yeast": 10.0}
    # The same train again is the same artifact, and the worker is not asked twice.
    again = pureos.run_train(spec, [Override(scope="pureos:unit:t1:F1", key="V", value=0.2, by="Another Person",
                                             at=AT, note=STANDIN)])
    assert again.artifactId == run.artifactId and len([c for c in worker.calls if c[0] == "train_run"]) == 1
    # Every reader reads the one artifact.
    assert run.train.productStream == "F1_liquid" and run.purity.productStream == "F1_liquid"
    assert run.train.tool == "pureos.train_run" and (run.train.trainId, run.train.trainName) == ("t1", "A test train")
    assert run.train.program == "yeast" and run.spec == spec
    assert [c.unit for c in run.costs] == ["C1", "F1"] and run.costs[0].items == {"STAND-IN item": 1.0}
    assert {p.unit: p.type for p in run.parameters} == {"C1": "centrifugation", "F1": "flash"}
    v = {x.key: x for x in run.parameters[0].values}
    assert v["split.Yeast"].origin == "assumption" and v["split.Yeast"].overriddenBy == BY
    assert any("no record or person set split.Ethanol, split.Glucose;" in n for n in run.notes), run.notes
    assert any("Unit C1: the moisture content" in n and "sets the Water" in n for n in run.notes), run.notes


def test_purity_names_each_streams_product_share_and_its_largest_other_components():
    streams = [{"id": "s", "massFlow": 10.0, "massFlows": {"Ethanol": 6.0, "Water": 3.0, "Glucose": 0.5, "Yeast": 0.3,
                                                           "CO2": 0.2}},
               {"id": "empty", "massFlow": 0.0, "massFlows": {}}]
    p = train_spec.purity_of(streams, "Ethanol", "s")
    assert p.productFraction == pytest.approx(0.6) and p.impuritiesShown == train_spec.IMPURITIES
    s = p.streams[0]
    assert [(i.chemical, round(i.massFraction, 9)) for i in s.impurities] == [("Water", 0.3), ("Glucose", 0.05),
                                                                              ("Yeast", 0.03)]
    assert p.streams[1].productFraction is None


def test_train_of_reads_a_train_run_by_pass(store, worker, no_pool):
    run = pureos.run_train(spec_of())
    tr = pureos.train_of(artifacts.get(run.artifactId))
    u = {x.id: x for x in tr.units}
    assert u["C1"].recovery == pytest.approx(1 - LOSS) and u["F1"].recovery == pytest.approx(1 - LOSS)
    assert tr.overallRecovery == pytest.approx((1 - LOSS) ** 2) == u["F1"].cumulative
    assert u["C1"].lostTo == ["C1_cake"] and tr.product == "Ethanol"
    assert "the library's chemical for the train's product, ethanol" in tr.productBasis
    # trains() and train() list and open it by the train's id or the run's.
    assert pureos.train("t1").artifactId == run.artifactId == pureos.train(run.artifactId).artifactId
    listed = pureos.trains()
    assert [(t.tool, t.trainId, t.trainName) for t in listed] == [("pureos.train_run", "t1", "A test train")]


def test_the_endpoints_run_list_and_open_a_train(client, store, worker, no_pool):
    body = {"train": spec_of().model_dump(mode="json"), "overrides": [], "by": None, "includeArchived": False}
    r = client.post("/api/pureos/train/run", json=body)
    assert r.status_code == 200, r.text
    aid = r.json()["artifactId"]
    assert r.json()["train"]["overallRecovery"] == pytest.approx((1 - LOSS) ** 2)
    runs = client.get("/api/pureos/train-runs").json()
    assert [x["artifactId"] for x in runs] == [aid] and runs[0]["trainId"] == "t1"
    assert client.get("/api/pureos/train/t1").json()["artifactId"] == aid
    assert client.post("/api/pureos/train/run", json={**body, "price": 1}).status_code == 422


def test_the_run_endpoint_answers_422_409_and_503_in_words(client, store, worker, no_pool, monkeypatch):
    spec = spec_of(units=[{"id": "F1", "type": "flash", "params": {"P": typed(101325.0)}}])
    r = client.post("/api/pureos/train/run", json={"train": spec.model_dump(mode="json")})
    assert r.status_code == 422 and "unit F1: Flash drum waits for" in r.json()["detail"]
    waiting = spec_of(units=[{"id": "D1", "type": "distillation"}])
    detail = client.post("/api/pureos/train/run", json={"train": waiting.model_dump(mode="json")}).json()["detail"]
    for words in ("unit D1 (distillation): light_key waits", "unit D1 (distillation): k waits",
                  "unit D1: BinaryDistillation waits for Light key and Heavy key"):
        assert words in detail, detail
    # A damaged inlet artifact is a 409.
    folder = store / "artifacts"
    folder.mkdir(exist_ok=True)
    (folder / ("b" * 16 + ".json")).write_text("{ not json", encoding="utf-8")
    damaged = spec_of(inlet={"kind": "simulation", "ref": "b" * 16, "params": {"broth_flow": typed(1.0)}})
    r = client.post("/api/pureos/train/run", json={"train": damaged.model_dump(mode="json")})
    assert r.status_code == 409 and "damaged on disk" in r.json()["detail"]
    # The worker's refusal is a 422 in its words; a worker that cannot answer, a 503.
    monkeypatch.setattr(proforma, "call", TrainWorker(fail="Refused: unit F1 (flash, Flash) did not converge: BioSTEAM "
                                                           "said: STAND-IN"))
    r = client.post("/api/pureos/train/run", json={"train": spec_of().model_dump(mode="json")})
    assert r.status_code == 422 and r.json()["detail"] == "unit F1 (flash, Flash) did not converge: BioSTEAM said: STAND-IN"
    monkeypatch.setattr(proforma, "call", TrainWorker(fail="WorkerCrashed: STAND-IN"))
    r = client.post("/api/pureos/train/run", json={"train": spec_of().model_dump(mode="json")})
    assert r.status_code == 503 and "could not run the train" in r.json()["detail"]


def test_a_train_of_an_archived_program_hides_and_runs_only_with_the_switch(store, worker, no_pool, monkeypatch):
    with pytest.raises(pureos.TrainRefused, match=r"train t1 belongs to PHA, archived \(hidden\)"):
        pureos.run_train(spec_of(program="pha"))
    with pytest.raises(pureos.TrainRefused, match="program pha has no chemical set here"):
        pureos.run_train(spec_of(program="pha"), include_archived=True)
    run = pureos.run_train(spec_of())
    art = artifacts.get(run.artifactId)
    from openferment_core import module_stores

    assert module_stores.artifact_program(art) == "yeast"
    # A run kept for a program archived later hides from the lists with it.
    monkeypatch.setattr(train_spec, "program_of_run", lambda a, r=None: "pha")
    assert pureos.train_runs() == [] and [s.artifactId for s in pureos.train_runs(True)] == [run.artifactId]


def test_a_product_with_no_library_chemical_refuses_the_train(store, worker, no_pool):
    with pytest.raises(pureos.TrainRefused, match="product 'phb' names no chemical of thermosteam's library here.*A "
                                                  "train traces its product by the library's own name for it"):
        pureos.run_train(spec_of(product="phb"))


def test_a_unit_reading_a_flowsheets_own_unit_takes_its_values_first_as_the_packages(store, worker, no_pool):
    spec = spec_of(units=[{"id": "D1", "type": "distillation",
                           "readFrom": {"flowsheet": "ethanol_glucose_v0", "unit": "D302"},
                           "params": {"k": typed(2.0)}}])
    run = pureos.run_train(spec)
    by = {b.name: b for b in artifacts.get(run.artifactId).inputs}
    assert by["D1.y_top"].value == 0.6 and by["D1.y_top"].source.id == "biorefineries@0.0-standin"
    assert "unit D302 of ethanol_glucose_v0 as the worker builds it" in by["D1.y_top"].source.note
    # A person's value still wins over the package's.
    assert by["D1.k"].value == 2.0 and by["D1.k"].source.kind == "assumption"
    assert by["D1 reads"].value == "ethanol_glucose_v0 D302"
    [(_, sent)] = [c for c in worker.calls if c[0] == "train_run"]
    assert sent["units"][0]["values"]["light_key"] == "Ethanol" and sent["units"][0]["values"]["k"] == 2.0


# ── §5.R (part a): what the night-two review found (offline) ───────────


def _values_of(spec, unit_id, overrides=()):
    """A unit's values as the Builder's panel resolves them: the train's
    typed values laid on as the scope's overrides, and any more given."""
    scope = f"pureos:unit:{spec.id}:{unit_id}"
    unit = next(u for u in spec.units if u.id == unit_id)
    typed_ = [Override(scope=scope, key=k, **p.model_dump()) for k, p in unit.params.items()]
    got = params.resolve_scope(scope, ParamResolveRequest(train=spec, overrides=[*typed_, *overrides])).values
    return {x.key: x for x in got}


def test_a_step_record_binds_a_unit_only_where_its_words_name_the_step_as_a_word(store, worker, monkeypatch):
    """Finding 0: 'which' holds 'hic' and 'second' holds 'sec', and neither
    names a chromatography step; the record still binds the centrifuge whose
    step its words name. A mode named by its abbreviation binds as written in
    capitals ('SEC'), never as seconds ('sec')."""
    pool = stand_in_pool(
        _record("r-c-1", "step_recovery", 60.0, "%", "The yield, which we measured after the second centrifugation, was 60%"),
        _record("r-c-2", "product_purity", 92.0, "%", "Ethanol secreted into the broth reached a purity of 92% after "
                                                       "distillation"),
        _record("r-c-3", "step_recovery", 70.0, "%", "held for 30 sec before the pellet was collected"),
    )
    monkeypatch.setattr(train_spec, "_pool", lambda: pool)
    spec = spec_of(units=[{"id": "C1", "type": "centrifugation"}, {"id": "K1", "type": "chromatography"}])
    k1 = _values_of(spec, "K1")
    assert k1["recovery"].origin == "waiting" and k1["recovery"].recordIds == []
    assert "2 naming another step or none" in k1["recovery"].detail, k1["recovery"].detail
    assert k1["purity"].origin == "waiting" and "1 naming another step or none" in k1["purity"].detail
    c1 = _values_of(spec, "C1")
    assert c1["split.Ethanol"].origin == "record" and c1["split.Ethanol"].recordIds == ["r-c-1"]
    # An abbreviation in capitals names the mode's step.
    sec = stand_in_pool(_record("r-c-4", "step_recovery", 80.0, "%", "after SEC the pool held"))
    monkeypatch.setattr(train_spec, "_pool", lambda: sec)
    assert _values_of(spec, "K1")["recovery"].recordIds == ["r-c-4"]
    # A word that holds a step's word inside it names nothing: 'pellet' holds 'lle'.
    assert train_spec._names_step({"quote": "the pellet was collected"}, ["lle"]) is False
    assert train_spec._names_step({"quote": "after liquid-liquid extraction"}, ["liquid liquid extraction"]) is True


def test_the_unset_split_words_name_the_outlet_the_split_goes_to(store, worker, no_pool):
    """Findings 1 and 7: the drum dryer's split goes to its hot gas (outlet
    1), so a component its split does not name stays in the dried solids;
    the words on the panel and in the run's notes say so."""
    spec = spec_of(units=[{"id": "D1", "type": "drying-drum", "params": {"split.Ethanol": typed(0.9)},
                           "outlets": {"dried": "waste", "hot-gas": "onward"}}])
    v = _values_of(spec, "D1")
    words = v["split.Glucose"].detail
    assert v["split.Glucose"].origin == "not-read"
    assert "none of it to outlet hot-gas" in words and "all of it leaves by dried" in words, words
    assert "outlet dried" not in words.replace("leaves by dried", "")
    run = pureos.run_train(spec)
    note = next(n for n in run.notes if n.startswith("Unit D1: no record or person set"))
    assert "none of it to outlet hot-gas" in note and "none of it to outlet dried" not in note, note
    # A centrifuge's split goes to its cake (outlet 0), as before.
    c = _values_of(spec_of(units=[{"id": "C1", "type": "centrifugation", "params": {"split.Yeast": typed(0.9)}}]), "C1")
    assert "none of it to outlet cake" in c["split.Ethanol"].detail and "all of it leaves by liquid" in c[
        "split.Ethanol"].detail


def test_a_pressure_filters_split_is_its_own_table_until_a_share_is_set_and_then_the_whole_table_is_passed(
        store, worker, no_pool):
    """Findings 1 and 5: the pressure filter fills its split from its own
    table when none is given and drops the whole table once any share is:
    each unset share is the class's table share, read in the worker, served
    as its library default; nothing set is left to the class and said so;
    one share set passes every share, the others the class's own."""
    bare = spec_of(units=[{"id": "P1", "type": "pressure-filtration"}])
    v = _values_of(bare, "P1")
    # Water's share is the moisture content's (finding 6), so the table's water is not read.
    assert v["split.Water"].origin == "not-read"
    for c in ("Ethanol", "Glucose", "Yeast"):
        x = v[f"split.{c}"]
        assert x.origin == "library-default" and x.value == pytest.approx(TABLE[c]), (c, x)
        assert x.libraryDefault == pytest.approx(TABLE[c]) and "own table" in x.detail
    run = pureos.run_train(bare)
    [(_, sent)] = [c for c in worker.calls if c[0] == "train_run"]
    assert not [k for k in sent["units"][0]["values"] if k.startswith("split.")]
    assert not any("none of it to outlet retentate" in n for n in run.notes), run.notes
    assert any("PressureFilter's own table" in n for n in run.notes), run.notes
    # One share set: every share goes to the class, the rest at the table's own.
    one = spec_of(units=[{"id": "P1", "type": "pressure-filtration", "params": {"split.Ethanol": typed(0.05)}}])
    run = pureos.run_train(one)
    sent = [c for c in worker.calls if c[0] == "train_run"][-1][1]
    split = {k: x for k, x in sent["units"][0]["values"].items() if k.startswith("split.")}
    assert split == pytest.approx({"split.Ethanol": 0.05, "split.Glucose": TABLE["Glucose"], "split.Yeast": TABLE["Yeast"]})
    p = {x.key: x for x in run.parameters[0].values}
    assert p["split.Yeast"].origin == "library-default" and p["split.Yeast"].value == pytest.approx(TABLE["Yeast"])
    assert any("passed with it" in n for n in run.notes), run.notes


def test_a_run_reads_back_every_record_that_bound_a_value(store, worker, monkeypatch):
    """Findings 2 and 9: two records bind a centrifuge's split; the run's
    parameters name both, as its basis does."""
    pool = stand_in_pool(_record("r-st-1", "step_recovery", 90.0, "%", "after centrifugation the broth kept"),
                         _record("r-st-2", "step_recovery", 80.0, "%", "after centrifugation the broth kept"))
    monkeypatch.setattr(train_spec, "_pool", lambda: pool)
    run = pureos.run_train(spec_of(units=[{"id": "C1", "type": "centrifugation"}]))
    basis = [i.value for i in artifacts.get(run.artifactId).inputs if i.name == "C1.split.Ethanol record"]
    v = {x.key: x for x in run.parameters[0].values}
    assert basis == ["r-st-1", "r-st-2"] and v["split.Ethanol"].recordIds == basis
    assert v["split.Ethanol"].origin == "record"


def test_the_moisture_content_sets_the_water_and_a_split_of_water_beside_it_is_refused(store, worker, no_pool):
    """Finding 6: BioSTEAM's solids separators and drum dryer move water to
    meet the moisture content and never read a split of water: unset, the
    water's split is served not read and saying why; typed beside a moisture,
    it is refused in words by the panel's resolve and the run, and never
    enters a basis."""
    spec = spec_of(units=[{"id": "C1", "type": "centrifugation", "params": {"split.Yeast": typed(0.9)}}])
    v = _values_of(spec, "C1")
    assert v["moisture_content"].value is not None
    assert v["split.Water"].origin == "not-read" and "moisture content sets the water" in v["split.Water"].detail
    run = pureos.run_train(spec)
    assert not [i for i in artifacts.get(run.artifactId).inputs if i.name.startswith("C1.split.Water")]
    typed_water = spec_of(units=[{"id": "C1", "type": "centrifugation", "params": {"split.Yeast": typed(0.9),
                                                                                  "split.Water": typed(0.05)}}])
    got = pureos.check_train(typed_water)
    assert not got.ok and any("split.Water" in w and "moisture content" in w for w in got.places["C1"]), got.places
    with pytest.raises(pureos.TrainRefused, match=r"unit C1: split.Water .*moisture content"):
        pureos.run_train(typed_water)
    with pytest.raises(params.ParamRefused, match="moisture content"):
        _values_of(spec, "C1", [Override(scope="pureos:unit:t1:C1", key="split.Water", value=0.05, by=BY, at=AT)])
    # The drum dryer and the pressure filter alike.
    for unit in ({"id": "D1", "type": "drying-drum", "params": {"split.Ethanol": typed(0.9)}},
                 {"id": "P1", "type": "pressure-filtration"}):
        w = _values_of(spec_of(units=[unit]), unit["id"])["split.Water"]
        assert w.origin == "not-read" and "moisture content sets the water" in w.detail, (unit["id"], w)


def test_the_molecular_sieves_ports_say_what_the_class_sends_each(store):
    """Finding 8: BioSTEAM's MolecularSieve sends its split to outlet 0, which
    the package uses for the water the sieves release (recycled); the
    dehydrated product leaves by outlet 1, and goes on by default."""
    e = catalogue.entry("molecular-sieve")
    outs = [p for p in e.ports if p.side == "out"]
    assert [p.name for p in outs] == ["regenerate", "product"]
    assert outs[1].onward and "dehydrated" in outs[1].what and not outs[0].onward
    split = next(p for p in e.params if p.key == "split")
    assert "regenerate (outlet 0)" in split.gloss and "dehydrated product (outlet 0)" not in split.gloss
    assert train_spec.routes(TrainUnitSpec(id="U1", type="molecular-sieve")) == {"regenerate": "waste",
                                                                                "product": "onward"}


# ── Rule 1 and E.3‴ (offline) ──────────────────────────────────────────


@pytest.mark.parametrize("rel", ["pureos/train_spec.py", "flowsheets/train.py", "pureos/from_run.py"])
def test_no_process_number_in_the_trains_code(rel):
    """Every number literal is 0 or 1, or a module-level constant named with
    its reason (PER_CENT, a unit's definition; IMPURITIES, a reading
    convention)."""
    tree = ast.parse((PKG / rel).read_text(encoding="utf-8"))
    named = {"PER_CENT", "IMPURITIES"}
    allowed_nodes = {id(n.value) for n in tree.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id in named for t in n.targets)}
    found = [(n.lineno, n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant)
             and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
             and n.value not in (0, 1) and id(n) not in allowed_nodes]
    assert found == [], found


def test_the_service_runs_nothing_of_biosteam_to_validate_or_read_a_train():
    """Importing the service and validating a train loads neither BioSTEAM
    nor the worker's train module (E.3‴), and the train run's tool is
    registered, so a kept run replays on a service just started."""
    import subprocess
    import sys

    code = ("import sys\n"
            "from openferment_core import api, pureos\n"
            "from fastapi.testclient import TestClient\n"
            f"spec = {spec_of().model_dump(mode='json')!r}\n"
            "r = TestClient(api.app, base_url='http://127.0.0.1').post('/api/pureos/train/validate', json=spec)\n"
            "assert r.status_code == 200 and r.json()['ok'], r.text\n"
            "steam = sorted(m for m in sys.modules if m.split('.')[0] in ('biosteam', 'thermosteam', 'biorefineries'))\n"
            "assert not steam, steam\n"
            "assert 'openferment_core.flowsheets.train' not in sys.modules\n"
            # A kept train run replays on a service just started (as §8.R holds the vessel's).
            "from openferment_core import artifacts\n"
            "artifacts.registered('pureos.train_run')\n")
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


def three_units(**inlet) -> TrainSpec:
    """Solids centrifuge, flash, drum dryer on a STAND-IN yeast broth: the
    liquid on, its liquid on, the dryer's hot gas on (the ethanol leaves with
    it). No split of water is typed: the centrifuge's cake moisture and the
    dryer's product moisture set the water (§5.R part a, finding 6)."""
    return spec_of(inlet=inlet or {"kind": "typed", "params": {
        "broth_flow": typed(1.0), "conc.Yeast": typed(10.0), "conc.Ethanol": typed(50.0), "conc.Glucose": typed(5.0),
        "T": typed(305.0)}}, units=[
        {"id": "C1", "type": "centrifugation", "params": {"split.Yeast": typed(0.9), "split.Ethanol": typed(0.05)}},
        {"id": "F1", "type": "flash", "params": {"P": typed(101325.0), "V": typed(0.1)},
         "outlets": {"vapour": "waste", "liquid": "onward"}},
        {"id": "D1", "type": "drying-drum", "params": {"split.Ethanol": typed(0.9)},
         "outlets": {"dried": "waste", "hot-gas": "onward"}}])


def with_water(spec: TrainSpec) -> TrainSpec:
    """The same train with a split of water typed on the centrifuge and the
    drum dryer, beside the moisture each class meets (STAND-INs)."""
    water = {"C1": 0.05, "D1": 0.5}
    return spec.model_copy(update={"units": [
        u.model_copy(update={"params": {**u.params, "split.Water": TrainParam(**typed(water[u.id]))}}) if u.id in water
        else u for u in spec.units]})


@pytest.mark.sim
def test_a_three_unit_train_converges_and_its_recovery_is_the_product_of_its_onward_fractions(real):
    run = pureos.run_train(three_units())
    tr = run.train
    u = {x.id: x for x in tr.units}
    assert [x.id for x in tr.units] == ["C1", "F1", "D1"] and all(x.onPath for x in tr.units)
    for x in tr.units:
        assert 0 < x.recovery < 1, (x.id, x.recovery)
    assert tr.overallRecovery == pytest.approx(math.prod(x.recovery for x in tr.units), rel=1e-9)
    assert tr.productStream == "D1_hot_gas" == run.purity.productStream and tr.product == "Ethanol"
    # The centrifuge and the flash keep their mass; the drum dryer's outlets
    # carry the oxygen its fuel burns beyond its inlets (§5.1), said so.
    for x in (u["C1"], u["F1"]):
        assert x.massOut == pytest.approx(x.massIn, rel=1e-9)
    assert u["D1"].massOut > u["D1"].massIn and any("DrumDryer" in n for n in run.notes)
    assert run.inlet.water > 0 and "Water is the balance" in run.inlet.waterNote
    assert run.inlet.flows["Ethanol"] == pytest.approx(50.0)
    assert all(c.costModel and c.installedCost > 0 for c in run.costs)
    assert run.provenance == "demo"
    assert artifacts.replay(run.artifactId).identical


@pytest.mark.sim
def test_the_moisture_sets_the_water_and_the_drum_dryers_split_goes_to_its_hot_gas_on_the_real_worker(real):
    """§5.R (part a), findings 6 and 7, on the real worker: a split of water
    typed beside a cake's or a dried product's moisture is refused naming
    both units, before the worker runs a train; without it the train runs,
    its basis holds no split of water, the cake's water is the moisture's,
    and the drum dryer's note says an unnamed component stays in the dried
    solids, as its stream table shows."""
    with pytest.raises(pureos.TrainRefused) as e:
        pureos.run_train(with_water(three_units()))
    said = str(e.value)
    for uid in ("C1", "D1"):
        assert f"unit {uid}: split.Water" in said and "moisture content" in said, said
    run = pureos.run_train(three_units())
    names = {i.name for i in artifacts.get(run.artifactId).inputs}
    assert not {"C1.split.Water", "D1.split.Water"} & names
    streams = {s.id: s for s in run.train.streams}
    cake = streams["C1_cake"].massFlows
    moisture = next(i.value for i in artifacts.get(run.artifactId).inputs if i.name == "C1.moisture_content")
    assert cake["Water"] / sum(cake.values()) == pytest.approx(moisture, rel=1e-9)
    note = next(n for n in run.notes if n.startswith("Unit D1: no record or person set"))
    assert "none of it to outlet hot-gas" in note and "none of it to outlet dried" not in note, note
    entering = streams["F1_liquid"].massFlows
    for chem in ("Glucose", "Yeast"):
        if entering.get(chem):
            assert streams["D1_dried"].massFlows.get(chem, 0.0) == pytest.approx(entering[chem], rel=1e-9), chem


@pytest.mark.sim
def test_a_pressure_filter_keeps_its_own_table_for_every_share_nobody_set_on_the_real_worker(real):
    """§5.R (part a), findings 1 and 5, on the real worker: the class's own
    table share of each component is read in the worker and served as its
    library default; with one share set the rest still split by the table
    (the run passes the whole table), and with none set the class fills it
    and the run says so."""
    one = spec_of(units=[{"id": "P1", "type": "pressure-filtration", "params": {"split.Ethanol": typed(0.05)}}])
    share = _values_of(one, "P1")["split.Yeast"]
    assert share.origin == "library-default" and share.value is not None and 0 < share.value < 1
    run = pureos.run_train(one)
    streams = {s.id: s for s in run.train.streams}
    fed = run.inlet.flows["Yeast"]
    assert streams["P1_retentate"].massFlows["Yeast"] == pytest.approx(fed * share.value, rel=1e-9)
    p = {x.key: x for x in run.parameters[0].values}
    assert p["split.Yeast"].origin == "library-default" and p["split.Yeast"].value == pytest.approx(share.value)
    bare = pureos.run_train(spec_of(units=[{"id": "P1", "type": "pressure-filtration"}]))
    assert not any("none of it to outlet retentate" in n for n in bare.notes), bare.notes
    kept = {s.id: s for s in bare.train.streams}["P1_retentate"].massFlows["Yeast"]
    assert kept == pytest.approx(fed * share.value, rel=1e-9)


@pytest.mark.sim
def test_a_forward_recycle_is_refused_before_the_worker_runs(real):
    spec = three_units()
    bad = spec.model_copy(update={"units": [spec.units[0].model_copy(update={"outlets": {"cake": "recycle:D1"}}),
                                            *spec.units[1:]]})
    with pytest.raises(pureos.TrainRefused, match="recycles to D1, a unit after it"):
        pureos.run_train(bad)


@pytest.mark.sim
def test_a_unit_that_cannot_run_refuses_the_train_naming_it_and_biosteams_words(real):
    spec = spec_of(units=[
        {"id": "C1", "type": "centrifugation", "params": {"split.Yeast": typed(0.9)}},
        {"id": "U1", "type": "uf-df", "params": {"concentration_factor": typed(2.0),
                                                 "sieving_coefficient.Ethanol": typed(1.0)}}])
    with pytest.raises(pureos.TrainRefused, match=r"unit U1 \(uf-df, Ultrafiltration\) did not converge: BioSTEAM said: "
                                                  r"ValueError.*needs the sieving coefficient of Glucose"):
        pureos.run_train(spec)


@pytest.mark.sim
def test_a_simulations_harvest_takes_its_broth_flow_from_a_vessel_design(real):
    from openferment_core import vessel
    from openferment_core.models import VesselRequest

    sim = real_simulation()
    d = vessel.design(VesselRequest(simulation=sim.artifactId, overrides=[Override(
        scope=f"fermos:vessel:{sim.artifactId}", key="plant_scale", value=50000.0, by=BY, at=AT, note=STANDIN)]))
    rows = {r.label: r.value for r in d.design}
    spec = three_units(kind="simulation", ref=sim.artifactId, vessel=d.artifactId)
    run = pureos.run_train(spec)
    assert run.inlet.brothFlow == pytest.approx(rows["Working volume of each vessel"] * rows["Vessels"]
                                                / rows["Cycle time"])
    by = {b.name: b for b in artifacts.get(run.artifactId).inputs}
    assert by["inlet.broth_flow"].source == BasisSource(kind="artifact", id=d.artifactId, note=by["inlet.broth_flow"]
                                                        .source.note)
    assert run.inlet.flows["Yeast"] == pytest.approx(run.inlet.concentrations["Yeast"] * run.inlet.brothFlow)
    assert run.train.program == "yeast" and run.train.overallRecovery > 0


# The ethanol flowsheet's STAND-IN inputs (assumptions of this test, none a
# result): enough to run the package's purification train once.
ETHANOL_STANDIN = {"feed_glucose_conc": 100.0, "titre": 45.0, "yield": 0.45, "productivity": 2.0,
                   "plant_scale": 50000.0, "glucose_price": 0.3}
# The package's own units the catalogue's units read: its beer column, its
# rectifier and its molecular sieves (biorefineries.ethanol's D302, D303,
# U301, as ethanol_glucose_v0 builds them).
PACKAGE_UNITS = (("D1", "distillation", "D302"), ("D2", "distillation", "D303"), ("U1", "molecular-sieve", "U301"))
# The test's tolerance, as the document sets it: within 1 % of the package's.
WITHIN = 0.01
# Measured on 2026-10-21 (BioSTEAM 2.54.0, biorefineries 2.35.1): the two
# purities agree to every digit, so the train is held to a millionth as well,
# which a reading error under the document's 1 % would still break.
MEASURED = 1e-6


@pytest.mark.sim
@pytest.mark.parametrize("recycle", [True, False], ids=["sieve-regenerate-recycled", "sieve-regenerate-wasted"])
def test_the_ethanol_train_from_the_catalogue_gives_the_packages_own_purity_on_the_same_beer(real, recycle):
    run = proforma.run_flowsheet("ethanol_glucose_v0", [
        InputAssumption(key=k, value=v, low=v, high=v, by=BY, at=AT, note=STANDIN) for k, v in ETHANOL_STANDIN.items()],
        samples=1)
    tables = proforma.tables_of(run)
    package = next(s for s in tables.streams if s.id == "ethanol")
    package_purity = package.massFlows["Ethanol"] / package.massFlow
    # The package's sieve sends its water-rich share to its outlet 0 (the
    # catalogue's `regenerate`), which the package recycles to the
    # rectifier; its outlet 1 (`product`) is the fuel-grade ethanol (§5.R
    # part a, finding 8: the catalogue's ports say so, and route so by default).
    units = [{"id": uid, "type": t, "readFrom": {"flowsheet": "ethanol_glucose_v0", "unit": pkg}}
             for uid, t, pkg in PACKAGE_UNITS]
    units[-1]["outlets"] = {"regenerate": "recycle:D2" if recycle else "waste", "product": "onward"}
    spec = TrainSpec.model_validate({"id": "ethanol-train", "name": "The ethanol train", "program": "yeast",
                                     "product": "ethanol", "inlet": {"kind": "run-stream", "ref": run.id,
                                                                     "streamId": "beer"}, "units": units})
    got = pureos.run_train(spec)
    assert got.purity.productStream == "U1_product"
    assert abs(got.purity.productFraction - package_purity) <= WITHIN * package_purity, (got.purity.productFraction,
                                                                                         package_purity)
    assert got.purity.productFraction == pytest.approx(package_purity, rel=MEASURED)
    if recycle:
        # With the package's recycle the ethanol delivered is the package's too.
        out = next(s for s in got.train.streams if s.id == "U1_product").massFlows["Ethanol"]
        assert out == pytest.approx(package.massFlows["Ethanol"], rel=WITHIN)
    # Every value the units took is the package's, read, never typed: a
    # `model` input naming biorefineries' version.
    inputs = artifacts.get(got.artifactId).inputs
    by = {b.name: b for b in inputs}
    for uid, _, pkg in PACKAGE_UNITS:
        assert by[f"{uid} reads"].value == f"ethanol_glucose_v0 {pkg}"
    for key in ("D1.light_key", "D1.heavy_key", "D1.k", "D1.y_top", "D1.x_bot", "D1.P", "D2.k", "D2.y_top", "D2.x_bot",
                "D2.P", "U1.split.Ethanol", "U1.split.Water"):
        assert by[key].source.kind == "model" and by[key].source.id.startswith("biorefineries@"), key
    assert not [b for b in inputs if b.source.kind == "assumption" and b.name.startswith(("D1.", "D2.", "U1."))]
    assert by["inlet"].source.id == run.id and by["inlet stream"].value == "beer"
