"""fermOS sizes the vessel on BioSTEAM (OF-BLD-020 §4.1, D7, E.2‴).

Every simulation here is a STAND-IN: an artifact in §3.1's shape written
straight into the test's own data directory, its numbers chosen to exercise
the code (a logistic batch on glucose), none a result. The offline tests
answer for the worker with a stand-in as well; the `sim` tests run BioSTEAM.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, intake, params, proforma, vessel
from openferment_core.models import Artifact, BasisInput, BasisSource, Override, VesselRequest

STANDIN = "STAND-IN for this test: invented numbers in §3.1's shape"
AEROBIC_ID = "a0a0a0a0a0a0a0a1"
ANAEROBIC_ID = "a0a0a0a0a0a0a0a2"
FED_ID = "a0a0a0a0a0a0a0a3"
BY = "openFerment test fixture"
AT = "2026-10-21"


def _logistic(t, x0, xm, mu):
    return xm / (1 + (xm / x0 - 1) * math.exp(-mu * t))


def standin_simulation(aerobic: bool, *, family="batch_v1", hours=None, x0=None, xm=None, s0=None, yps=None,
                       mu=None, yxo=None) -> dict:
    """A batch in §3.1's output shape: logistic cells, sugar and product by
    stand-in yields, uptake (dX/dt)/Yx/o. Every argument is a STAND-IN."""
    hours = hours or (16.0 if aerobic else 30.0)
    x0, xm = x0 or (1.0 if aerobic else 2.0), xm or (9.0 if aerobic else 5.0)
    s0 = s0 or (20.0 if aerobic else 100.0)
    mu, yps, yxo = mu or (0.6 if aerobic else 0.3), yps if yps is not None else (0.1 if aerobic else 0.42), yxo or 1.2
    n = 81
    ts = [hours * i / (n - 1) for i in range(n)]
    X = [_logistic(t, x0, xm, mu) for t in ts]
    used = [(s0 - 1.0) * (x - x0) / (xm - x0) for x in X]
    S = [s0 - u for u in used]
    P = [yps * u for u in used]
    our = [(mu * x * (1 - x / xm)) / yxo if aerobic else 0.0 for x in X]
    return {
        "family": family, "title": STANDIN, "parameters": [], "aerobic": aerobic,
        "start": [{"key": "x0", "value": x0}, {"key": "s0", "value": s0}, {"key": "p0", "value": 0.0}],
        "series": {"t": ts, "X": X, "S": S, "P": P}, "units": {"X": "g L⁻¹", "S": "g L⁻¹", "P": "g L⁻¹"},
        "our": {"t": ts, "value": our, "unit": "g O₂ L⁻¹ h⁻¹"},
        "end": {"X": X[-1], "S": S[-1], "P": P[-1], "t": ts[-1]}, "harvestH": ts[-1], "sugarRunsOutH": None,
        "finalTitre": P[-1], "yieldAchieved": yps, "productivity": P[-1] / ts[-1],
        "massBalance": {"closure": 1.0, "ok": True, "note": STANDIN}, "ceiling": None, "flags": [STANDIN],
        "product": "ethanol", "sugar": "glucose",
    }


def keep(aid: str, output: dict, tool: str = vessel.SIMULATION) -> Artifact:
    """Write a stand-in artifact straight into the test's store."""
    art = Artifact(id=aid, tool=tool, toolVersion=STANDIN, inputs=[BasisInput(
        name="stand-in", value=STANDIN, unit="", source=BasisSource(kind="assumption", by=BY, note=STANDIN))],
        output=output, outputHash=artifacts.output_hash(output), provenance="demo", createdAt="2026-10-21T00:00:00Z",
        durationMs=0, seed=None)
    folder = artifacts.folder()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{aid}.json").write_text(art.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return art


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    keep(AEROBIC_ID, standin_simulation(True))
    keep(ANAEROBIC_ID, standin_simulation(False))
    keep(FED_ID, standin_simulation(True, family="fedbatch_v1"))
    return tmp_path


def override(aid: str, key: str, value, by: str = BY) -> Override:
    return Override(scope=f"fermos:vessel:{aid}", key=key, value=value, by=by, at=AT)


# ── a stand-in for the worker (offline) ────────────────────────────────

AER_KEYS = [d.key for d in vessel._decls(vessel.AEROBIC)]
ANA_KEYS = [d.key for d in vessel._decls(vessel.ANAEROBIC)]


class StandInWorker:
    """Answers `vessel_specs` and `vessel_design` as the worker's JSON
    contract does, with STAND-IN defaults and a design of invented numbers."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, op, args):
        self.calls.append((op, args))
        if op == "vessel_specs":
            kind = args["kind"]
            keys = AER_KEYS if kind == vessel.AEROBIC else ANA_KEYS
            out = {"kind": kind, "unitClass": "AeratedBioreactor" if kind == vessel.AEROBIC else "NRELAnaerobicBatchBioreactor",
                   "parameters": {k: {"default": None if k in ("N", "loading_time", "Q_O2_consumption") else
                                      ("Vertical" if k == "vessel_type" else "Carbon steel" if k == "vessel_material" else
                                       "recirculation loop" if k == "heat_exchanger_configuration" else 0.5),
                                      "from": STANDIN} for k in keys + ["batch", "Nmin", "Nmax", "reactions"]},
                   "biosteam": "0.0-standin", "thermosteam": "0.0-standin", "biorefineries": "0.0-standin",
                   "chemicals": "biorefineries.corn.create_chemicals",
                   "operatingHours": 1000.0, "operatingHoursFrom": STANDIN, "costIndex": 500.0, "costIndexYear": None}
            if kind == vessel.AEROBIC:
                out["designs"] = {
                    "Stirred tank": {"method": "Riet", "optimize_power": True, "kW_per_m3": 0.5, "runs": ["Riet"],
                                     "solvesPower": ["Riet"], "registered": ["Riet", "Labik", "Galaction"]},
                    "Bubble column": {"method": "Dewes", "optimize_power": False, "kW_per_m3": 0.5, "runs": ["Dewes"],
                                      "solvesPower": [], "registered": ["Deshpande", "Dewes", "Shah"]},
                }
                out["defaultDesign"] = "Stirred tank"
                out["choices"] = {"vessel_material": ["Carbon steel", "Titanium"], "vessel_type": ["Horizontal", "Vertical"],
                                  "heat_exchanger_configuration": ["jacketed", "recirculation loop"]}
                out["heatPerO2"], out["heatPerO2From"] = -1.0, STANDIN
            return out
        if op == "vessel_design":
            aerobic = args["kind"] == vessel.AEROBIC
            ox = None
            if aerobic:
                ox = {"t": args["our"]["t"], "our": args["our"]["value"], "unit": "mmol L⁻¹ h⁻¹", "otr": 1.0,
                      "short": [], "kLa": 1.0, "kLaNeededAtPeak": 1.0, "kLaUnit": "h⁻¹", "method": "Riet",
                      "aerated": True, "oxygenBasis": args["oxygenBasis"], "targetUptake": 1.0, "sized": 1.0,
                      "balancedUptake": 1.0, "scale": 1.0, "cStar": 1.0, "cL": 0.5, "drivingForce": 0.5,
                      "reactionO2KmolPerH": 1.0}
            return {"unitClass": "AeratedBioreactor" if aerobic else "NRELAnaerobicBatchBioreactor", "unitId": "R1",
                    "aerobic": aerobic, "design": [{"label": "Vessels", "value": 2.0, "unit": "", "readFrom": STANDIN}],
                    "designResults": {"Number of reactors": 2.0, "Reactor volume": 10.0}, "auxiliaries": {},
                    "used": {"T": 300.0}, "coolingAgents": [], "cost": {
                        "purchase": 1.0, "installed": 2.0, "byItem": {"Vessel": {"purchase": 1.0, "installed": 2.0}},
                        "utility": 1.0, "costIndex": 500.0, "costIndexYear": None, "note": STANDIN},
                    "versions": {"biosteam": "0.0-standin"}, "chemicals": "x", "dutyRead": -1.0,
                    "scale": {"how": STANDIN}, "reaction": {"equation": STANDIN, "notes": []}, "oxygen": ox,
                    "warnings": [], "utilitySettings": {}, "heat": {"bst": -1.0, "convention": None, "conventionNote": STANDIN}}
        raise AssertionError(f"the stand-in has no op {op}")


@pytest.fixture()
def worker(monkeypatch):
    w = StandInWorker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(vessel, "_SPECS", {})
    return w


@pytest.fixture()
def client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


def by_key(values):
    return {v.key: v for v in values}


# ── what a simulation gives ────────────────────────────────────────────


def test_a_simulation_is_read_in_one_place(store):
    src = vessel.simulation_inputs(artifacts.get(AEROBIC_ID))
    assert src["aerobic"] and src["start"]["s0"] == 20.0 and src["used"] == pytest.approx(20.0 - src["end"]["S"])
    assert src["made"]["cells"] == pytest.approx(src["end"]["X"] - 1.0) and src["harvestH"] == 16.0
    peak, mean = vessel.oxygen_uptake(src)
    assert peak == max(src["our"]["value"]) and 0 < mean < peak


def test_a_family_with_a_feed_or_another_tool_is_refused_in_words(store):
    with pytest.raises(vessel.VesselRefused, match="fed-batch's feed"):
        vessel.simulation_inputs(artifacts.get(FED_ID))
    other = keep("b0b0b0b0b0b0b0b1", {"x": 1}, tool="thermo_props")
    with pytest.raises(vessel.VesselRefused, match="not a fermOS simulation"):
        vessel.simulation_inputs(other)


# ── the scope (Appendix 2 §C) ──────────────────────────────────────────


def test_the_scope_serves_every_parameter_with_its_source_in_six_groups(store, worker):
    s = vessel.scope(AEROBIC_ID)
    assert s.kind == "fermos-vessel" and s.scope == f"fermos:vessel:{AEROBIC_ID}"
    assert {sp.group for sp in s.specs} == set(vessel.GROUPS)
    assert all(sp.boundsReason.strip() for sp in s.specs)
    v = by_key(s.values)
    src = vessel.simulation_inputs(artifacts.get(AEROBIC_ID))
    assert v["tau"].origin == "simulation" and v["tau"].value == src["harvestH"] and v["tau"].source.id == AEROBIC_ID
    assert v["our_peak"].origin == "simulation" and v["our_peak"].value == max(src["our"]["value"])
    assert v["our_mean"].origin == "simulation"
    assert v["oxygen_basis"].origin == "convention" and v["oxygen_basis"].value == "peak"
    assert v["V_max"].origin == "library-default" and v["V_max"].source.kind == "model"
    assert "AeratedBioreactor" in v["V_max"].source.note
    assert set(s.waiting) == {"plant_scale", "batch_volume"}
    assert any("One of plant_scale and batch_volume is needed" in n for n in s.notes)
    specs = {sp.key: sp for sp in s.specs}
    # Only what the class runs is offered; the rest is named in the note.
    assert specs["method"].choices == ["Riet"] and "Labik" in specs["method"].note and "not offered" in specs["method"].note
    assert specs["oxygen_basis"].choices == ["peak", "batch-average"]


def test_a_bubble_column_offers_dewes_and_no_agitator_by_convention(store, worker):
    s = vessel.scope(AEROBIC_ID, "bubble-column")
    v, specs = by_key(s.values), {sp.key: sp for sp in s.specs}
    assert specs["method"].choices == ["Dewes"] and v["method"].value == "Dewes"
    assert v["kW_per_m3"].origin == "convention" and v["kW_per_m3"].value == 0
    assert specs["optimize_power"].choices == ["false"] and v["optimize_power"].value == "false"


def test_an_anaerobic_scope_is_the_nrel_vessel_and_takes_no_vessel_type(store, worker):
    s = vessel.scope(ANAEROBIC_ID)
    keys = {sp.key for sp in s.specs}
    assert "NRELAnaerobicBatchBioreactor" in s.title and not keys & {"method", "our_peak", "batch_volume", "kW_per_m3"}
    assert s.waiting == ["plant_scale"]
    with pytest.raises(params.ParamRefused, match="NREL batch fermenter"):
        vessel.scope(ANAEROBIC_ID, "stirred-tank")


def test_every_declared_spec_has_a_bounds_reason_and_check_seed_says_so(monkeypatch):
    n, problems = params.check()
    assert problems == [] and n >= len(AER_KEYS) + len(ANA_KEYS)
    # Negative test: a declaration with no reason fails the check (D4).
    d = next(d for d in vessel.DECLARED if d.key == "theta_O2")
    monkeypatch.setattr(d, "reason", " ")
    _, problems = params.check()
    assert any("fermos-vessel" in p for p in problems)


# ── the request's rules ────────────────────────────────────────────────


def test_neither_scale_refuses_in_words_and_so_do_both(store, worker):
    with pytest.raises(vessel.VesselRefused, match="needs plant_scale .* or batch_volume"):
        vessel.design(VesselRequest(simulation=AEROBIC_ID))
    both = [override(AEROBIC_ID, "plant_scale", 1000.0), override(AEROBIC_ID, "batch_volume", 50.0)]
    with pytest.raises(vessel.VesselRefused, match="not both"):
        vessel.design(VesselRequest(simulation=AEROBIC_ID, overrides=both))
    assert not [c for c in worker.calls if c[0] == "vessel_design"]


def test_one_source_exactly_and_a_fit_designs_no_aerated_vessel(store, worker):
    with pytest.raises(vessel.VesselRefused, match="exactly one"):
        vessel.design(VesselRequest())
    with pytest.raises(vessel.VesselRefused, match="exactly one"):
        vessel.design(VesselRequest(simulation=AEROBIC_ID, fit=ANAEROBIC_ID))
    with pytest.raises(vessel.VesselRefused, match="name it as the simulation"):
        vessel.design(VesselRequest(fit=AEROBIC_ID))
    with pytest.raises(vessel.VesselNotFound, match="no artifact"):
        vessel.design(VesselRequest(simulation="ffffffffffffffff"))


def test_the_basis_names_every_parameter_its_source_and_the_person(store, worker):
    req = VesselRequest(simulation=AEROBIC_ID, overrides=[override(AEROBIC_ID, "plant_scale", 1000.0),
                                                           override(AEROBIC_ID, "theta_O2", 0.3)])
    d = vessel.design(req)
    art = artifacts.get(d.artifactId)
    named = {i.name: i for i in art.inputs}
    assert named["simulation"].source.kind == "artifact" and named["simulation"].source.id == AEROBIC_ID
    assert named["plant_scale"].source.kind == "assumption" and named["plant_scale"].source.by == BY
    assert named["theta_O2"].source.by == BY and named["V_max"].source.kind == "model"
    assert named["vessel class"].value == "AeratedBioreactor" and named["unit id"].value == "R1"
    assert named["tau"].source.id == AEROBIC_ID
    assert {"utility prices and cost index", "chemicals", "operating hours", "heat per oxygen consumed"} <= set(named)
    # An assumption makes it demo (D1, D3).
    assert d.provenance == "demo" and art.tool == vessel.TOOL
    p = by_key(d.parameters)
    assert p["theta_O2"].overriddenBy == BY and p["theta_O2"].libraryDefault == 0.5
    assert p["loading_time"].value is None and p["loading_time"].origin == "library-default"
    # Only what is not the class's own default reaches the worker.
    [(_, sent)] = [c for c in worker.calls if c[0] == "vessel_design"]
    assert sent["params"] == {"theta_O2": 0.3} and sent["scale"]["plantScale"] == 1000.0
    assert sent["oxygenBasis"] == "peak" and sent["ourTarget"] == pytest.approx(p["our_peak"].value)
    # The same request twice is the same artifact, and computes nothing again.
    again = vessel.design(req)
    assert again.artifactId == d.artifactId and len([c for c in worker.calls if c[0] == "vessel_design"]) == 1


def test_a_fit_designs_the_anaerobic_vessel_from_its_titre_yield_and_batch_time(store, worker, monkeypatch):
    from openferment_core.models import FermosFitInfo, FitFeed

    fit_id = "c0c0c0c0c0c0c0c1"
    keep(fit_id, {"standIn": STANDIN}, tool="kinetic_fit")
    info = FermosFitInfo(artifactId=fit_id, tool="kinetic_fit", provenance="measured", createdAt=AT,
                         flowsheet="ethanol_glucose_v0", batchTimeH=24.0, feeds=[
                             FitFeed(key="titre", unit="g L-1", value=40.0, derivation=STANDIN),
                             FitFeed(key="yield", unit="g g-1", value=0.4, derivation=STANDIN)])
    monkeypatch.setattr(proforma, "fit_info", lambda art, flowsheet: info)
    d = vessel.design(VesselRequest(fit=fit_id, overrides=[override(fit_id, "plant_scale", 1000.0)]))
    [(_, sent)] = [c for c in worker.calls if c[0] == "vessel_design"]
    assert sent["kind"] == "anaerobic" and sent["tau"] == 24.0 and sent["used"] == pytest.approx(100.0)
    assert sent["made"] == {"Yeast": 0.0, "Ethanol": 40.0} and d.oxygen is None and "no air" in d.oxygenNote
    assert by_key(d.parameters)["tau"].origin == "artifact"
    with pytest.raises(vessel.VesselRefused, match="NREL batch fermenter"):
        vessel.design(VesselRequest(fit=fit_id, vesselType="stirred-tank"))


# ── the endpoints ──────────────────────────────────────────────────────


def test_the_endpoints_answer_and_refuse_in_words(store, worker, client):
    r = client.get("/api/fermos/vessel/specs", params={"simulation": AEROBIC_ID})
    assert r.status_code == 200 and r.json()["kind"] == "fermos-vessel"
    assert client.get("/api/fermos/vessel/specs", params={"simulation": "ffffffffffffffff"}).status_code == 404
    assert client.get("/api/fermos/vessel/specs", params={"simulation": FED_ID}).status_code == 422
    assert client.get("/api/fermos/vessel/specs").status_code == 422
    assert client.get(f"/api/params/fermos:vessel:{AEROBIC_ID}", params={"vesselType": "bubble-column"}).status_code == 200
    missing = client.post("/api/fermos/vessel", json={"simulation": AEROBIC_ID})
    assert missing.status_code == 422 and "plant_scale" in missing.json()["detail"]
    assert client.post("/api/fermos/vessel", json={"simulation": "ffffffffffffffff"}).status_code == 422
    made = client.post("/api/fermos/vessel", json={"simulation": ANAEROBIC_ID, "overrides": [
        override(ANAEROBIC_ID, "plant_scale", 1000.0).model_dump()]})
    assert made.status_code == 200 and made.json()["unitClass"] == "NRELAnaerobicBatchBioreactor"
    listed = client.get("/api/fermos/vessels").json()
    assert [v["artifactId"] for v in listed] == [made.json()["artifactId"]] and listed[0]["source"] == ANAEROBIC_ID


def test_a_worker_that_cannot_answer_is_a_503(store, client, monkeypatch):
    from openferment_core.workers import WorkerError

    def down(op, args):
        raise WorkerError("the Proforma simulator could not start: STAND-IN")

    monkeypatch.setattr(proforma, "call", down)
    monkeypatch.setattr(vessel, "_SPECS", {})
    assert client.get("/api/fermos/vessel/specs", params={"simulation": AEROBIC_ID}).status_code == 503


def test_the_worker_side_holds_no_number_but_its_named_structural_ones():
    """No process number in flowsheets/vessel.py (Rule 1): every literal is 0
    or 1, or a named constant of how a design is solved."""
    import ast

    path = Path(vessel.__file__).parent / "flowsheets" / "vessel.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    named = {"FEED_RTOL", "FEED_STEPS", "SHORT_RTOL"}
    allowed = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in named for t in node.targets):
            allowed |= {id(n) for n in ast.walk(node)}
    odd = [(n.lineno, n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant)
           and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
           and n.value not in (0, 1) and id(n) not in allowed]
    assert odd == [], f"numbers in the vessel's worker code: {odd}"


# ── the real worker (sim) ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    return proforma


@pytest.fixture()
def real(monkeypatch, tmp_path, warm):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    keep(AEROBIC_ID, standin_simulation(True))
    keep(ANAEROBIC_ID, standin_simulation(False))
    return tmp_path


def _row(d, label):
    return next(r.value for r in d.design if r.label == label)


@pytest.mark.sim
def test_an_aerobic_simulation_designs_a_stirred_tank_sized_for_its_peak(real):
    scale = [override(AEROBIC_ID, "plant_scale", 2000.0)]
    d = vessel.design(VesselRequest(simulation=AEROBIC_ID, overrides=scale))
    assert d.unitClass == "AeratedBioreactor" and d.vesselType == "stirred-tank"
    N, V = _row(d, "Vessels"), _row(d, "Volume of each vessel")
    assert N >= 1 and float(N).is_integer() and 0 < V <= by_key(d.parameters)["V_max"].value
    ox = d.oxygen
    assert ox.method == "Riet" and ox.kLa > 0 and ox.aerated and ox.oxygenBasis == "peak"
    # Sized for the peak: the vessel transfers what the peak takes, and no hour is short.
    assert ox.otr == pytest.approx(max(ox.our), rel=1e-6) and ox.short == []
    assert ox.kLaNeededAtPeak == pytest.approx(ox.kLa, rel=1e-6)
    assert _row(d, "Compressor power") > 0 and d.cost.installed > d.cost.purchase > 0
    assert d.heat.bst < 0 and d.heat.convention is not None and d.heat.convention < 0
    assert d.cost.costIndex > 0 and d.provenance == "demo"
    # Sized for the batch average, as BioSTEAM sizes of itself, the peak is short.
    mean = vessel.design(VesselRequest(simulation=AEROBIC_ID, overrides=[
        *scale, override(AEROBIC_ID, "oxygen_basis", "batch-average")]))
    assert mean.oxygen.short and mean.oxygen.kLaNeededAtPeak > mean.oxygen.kLa
    t0, t1 = mean.oxygen.short[0]
    peak_at = mean.oxygen.t[mean.oxygen.our.index(max(mean.oxygen.our))]
    assert t0 < peak_at < t1 and any("rises above" in f for f in mean.flags)
    # The same request twice returns the same artifact.
    assert vessel.design(VesselRequest(simulation=AEROBIC_ID, overrides=scale)).artifactId == d.artifactId
    # A batch volume designs one vessel of that working volume (with a loading time).
    one = vessel.design(VesselRequest(simulation=AEROBIC_ID, overrides=[
        override(AEROBIC_ID, "batch_volume", 50.0), override(AEROBIC_ID, "loading_time", 2.0)]))
    assert _row(one, "Vessels") == 1 and _row(one, "Working volume of each vessel") == pytest.approx(50.0, rel=1e-9)
    with pytest.raises(vessel.VesselRefused, match="needs a loading time"):
        vessel.design(VesselRequest(simulation=AEROBIC_ID, overrides=[override(AEROBIC_ID, "batch_volume", 50.0)]))


@pytest.mark.sim
def test_a_bubble_column_by_dewes_costs_no_agitator_and_the_worker_answers_after(real):
    d = vessel.design(VesselRequest(simulation=AEROBIC_ID, vesselType="bubble-column",
                                    overrides=[override(AEROBIC_ID, "plant_scale", 2000.0)]))
    assert d.oxygen.method == "Dewes" and d.oxygen.kLa > 0 and d.vesselType == "bubble-column"
    assert not any("Agitator" in k for k in d.cost.byItem) and _row(d, "Agitator power, each vessel") == 0
    assert proforma.worker().ping()["worker"] == "proforma"


@pytest.mark.sim
def test_an_anaerobic_simulation_designs_the_nrel_vessel_with_no_compressor(real):
    d = vessel.design(VesselRequest(simulation=ANAEROBIC_ID, overrides=[override(ANAEROBIC_ID, "plant_scale", 50000.0)]))
    art = artifacts.get(d.artifactId)
    assert d.unitClass == "NRELAnaerobicBatchBioreactor" and d.oxygen is None and d.oxygenNote
    assert "compressor" not in art.output["auxiliaries"] and not any("Compressor" in k for k in d.cost.byItem)
    assert _row(d, "Vessels") >= 2 and d.heat.bst < 0 and d.heat.convention is None
    assert _row(d, "Dead time") == pytest.approx(_row(d, "Cycle time") - _row(d, "Batch time (reacting)"))


@pytest.mark.sim
def test_the_real_scope_reads_the_class_defaults_from_biosteam(real):
    s = vessel.scope(AEROBIC_ID)
    v = by_key(s.values)
    assert v["V_wf"].source.note.startswith("AeratedBioreactor's own default") and v["V_wf"].value == v["V_wf"].libraryDefault
    assert v["method"].value == "Riet" and {sp.key: sp for sp in s.specs}["method"].choices == ["Riet"]
    assert "Stainless steel 316" in {sp.key: sp for sp in s.specs}["vessel_material"].choices
    # Every declared key is one the class names (the declarations held to the class).
    for kind in (vessel.AEROBIC, vessel.ANAEROBIC):
        ws = vessel.worker_specs(kind)
        declared = {d.key for d in vessel._decls(kind)} - {"plant_scale", "batch_volume", "oxygen_basis", "our_peak",
                                                           "our_mean"}
        assert declared <= set(ws["parameters"]), declared - set(ws["parameters"])
        assert set(ws["parameters"]) - declared - {"method"} <= set(vessel.NOT_OFFERED) | {"tau"}


ETHANOL_STANDIN = {"feed_glucose_conc": 100.0, "titre": 45.0, "yield": 0.45, "productivity": 2.0,
                   "plant_scale": 50000.0, "glucose_price": 0.4}  # STAND-IN inputs, as test_proforma's
ETHANOL_RUN = ("run", {"flowsheet": "ethanol_glucose_v0", "base": ETHANOL_STANDIN, "specs": {}, "samples": 0, "seed": 0})
# The corn plant, loaded whole: it rebinds names in its package (biorefineries.corn.tea becomes its TEA object
# as an attribute of the package), which a design run after it must not trip on (found by verify's sim stage).
CORN_RUN = ("reference", {"flowsheet": "corn_drygrind", "digits": proforma.REFERENCE_DIGITS})


def _requests(real_dir) -> dict[str, dict]:
    """The worker's requests for three designs, from their bases."""
    out = {}
    for name, req in {
        "aerobic": VesselRequest(simulation=AEROBIC_ID, overrides=[override(AEROBIC_ID, "plant_scale", 2000.0)]),
        "bubble": VesselRequest(simulation=AEROBIC_ID, vesselType="bubble-column",
                                overrides=[override(AEROBIC_ID, "plant_scale", 2000.0)]),
        "anaerobic": VesselRequest(simulation=ANAEROBIC_ID, overrides=[override(ANAEROBIC_ID, "plant_scale", 50000.0)]),
    }.items():
        inputs, *_ = vessel.basis_inputs(req)
        out[name] = vessel.worker_request(inputs)[0]
    return out


def _in_a_worker_of_its_own(calls):
    from openferment_core.workers import SimWorker

    w = SimWorker("openferment_core.workers.proforma_worker", timeout_s=proforma.CALL_TIMEOUT_S)
    try:
        return [w.call(op, args) for op, args in calls]
    finally:
        w.close()


@pytest.mark.sim
def test_three_designs_in_one_warm_worker_leave_no_settings_behind(real):
    from concurrent.futures import ThreadPoolExecutor

    rq = _requests(real)
    A, B, N = (("vessel_design", rq[k]) for k in ("aerobic", "bubble", "anaerobic"))
    with ThreadPoolExecutor(2) as ex:
        warm_one = ex.submit(_in_a_worker_of_its_own, [ETHANOL_RUN, CORN_RUN, A, N, B, ETHANOL_RUN, A])
        fresh = ex.submit(_in_a_worker_of_its_own, [B, N])
        ethanol, _corn, aer, ana, bub, ethanol_again, aer_again = warm_one.result()
        fresh_bub, fresh_ana = fresh.result()
    tol = {"rel": 1e-9, "abs": 1e-12}
    # Across two processes the aerated design moves in its last digits:
    # BioSTEAM's air-flow solve (minimize_scalar at its own tolerance; the
    # xtol it passes is ignored) starts from sums over sets whose order
    # Python's string hash sets, so two hash seeds gave answers 5e-9 apart
    # (measured, 2026-10-21). A setting left behind moves a design by far
    # more (a cost index, a price); within one process the answer is the same.
    across = {"rel": 1e-6, "abs": 1e-9}

    def numbers(r):
        return {**{row["label"] + row["unit"]: row["value"] for row in r["design"] if isinstance(row["value"], float)},
                "installed": r["cost"]["installed"], "costIndex": r["cost"]["costIndex"], "duty": r["heat"]["bst"],
                "utility": r["cost"]["utility"]}

    for later, first, t in ((aer_again, aer, tol), (bub, fresh_bub, across), (ana, fresh_ana, across)):
        a, b = numbers(later), numbers(first)
        assert a.keys() == b.keys()
        for k in a:
            assert a[k] == pytest.approx(b[k], **t), k
    # The ethanol flowsheet prices as it did before the designs ran.
    price = lambda r: r["base"]["pricePerKgEthanol"]  # noqa: E731
    assert price(ethanol_again) == pytest.approx(price(ethanol), **tol)
    assert ethanol_again["base"]["readBack"] == pytest.approx(ethanol["base"]["readBack"], **tol)


@pytest.mark.sim
def test_the_proforma_worker_never_stops_in_a_debugger():
    """BioSTEAM's bubble-column branch answers a failure with a bare
    breakpoint(): in the worker module it raises in words, and returns."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONBREAKPOINT"}
    core = Path(vessel.__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-c", "import openferment_core.workers.proforma_worker; breakpoint()"],
                       cwd=core, env={**env, "PYTHONPATH": str(core)}, capture_output=True, text=True, timeout=180,
                       stdin=subprocess.DEVNULL)
    assert r.returncode != 0 and "does not stop in a debugger" in r.stderr
