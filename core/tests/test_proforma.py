"""Proforma on the service's side (OF-BLD-014 §8.2–§8.3), with no simulator."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import intake, proforma


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def test_a_benchmark_not_yet_run_reads_as_none_and_starts_nothing(store):
    from openferment_core import api

    before = proforma.status()["status"]
    r = TestClient(api.app, base_url="http://127.0.0.1").get("/api/proforma/benchmark").json()
    assert r["artifact"] is None and r["simulator"]["status"] == before


def test_the_benchmark_cites_the_package_it_ran(store):
    inputs = proforma.benchmark_inputs()
    assert {i.source.kind for i in inputs} == {"model"}
    assert inputs[0].source.id.startswith("biorefineries.cornstover@")


# ── binding (§8.3) ─────────────────────────────────────────────────────
# Every record here is a FIXTURE written in the test; none is a measurement.

from types import SimpleNamespace  # noqa: E402

from openferment_core.models import InputAssumption, ProformaRunRequest  # noqa: E402


def rec(rid, field, value, unit, *, paper="P6", carbon="glucose", strain="c-necator-h16", **kw):
    return {"id": rid, "paperId": paper, "field": field, "value": value, "unit": unit, "carbonSource": carbon,
            "strainId": strain, "organismText": "Ralstonia eutropha", "provenance": "unverified", "status": "unverified",
            "primary": True, **kw}


def assume(key, value, low, high, by="Sean Creighton"):
    return InputAssumption(key=key, value=value, low=low, high=high, by=by, at="2026-10-15")


def by_key(inputs):
    return {i.key: i for i in inputs}


def test_three_records_give_their_median_and_range_and_sample_triangular():
    rs = [rec(f"t{i}", "pha_titre", v, "g/L") for i, v in enumerate([10.0, 40.0, 25.0])]
    t = by_key(proforma.bind(rs))["titre"]
    assert (t.value, t.low, t.high, t.sampling, t.binding) == (25.0, 10.0, 40.0, "triangular", "records")
    assert t.recordIds == ["t0", "t1", "t2"]


def test_two_records_are_a_pair_and_one_is_held_fixed_and_flagged():
    two = by_key(proforma.bind([rec("a", "pha_titre", 10.0, "g/L"), rec("b", "pha_titre", 20.0, "g/L")]))["titre"]
    assert (two.low, two.high, two.sampling) == (10.0, 20.0, "uniform")
    one = by_key(proforma.bind([rec("a", "pha_titre", 10.0, "g/L")]))["titre"]
    assert one.sampling == "fixed" and proforma.SINGLE in one.flags


def test_the_gate_and_the_carbon_source_decide_what_binds():
    rs = [
        rec("ok", "pha_titre", 10.0, "g/L", carbon="sunflower stalk hydrolysate"),
        rec("nocarbon", "pha_titre", 11.0, "g/L", carbon=None),
        rec("oil", "pha_titre", 12.0, "g/L", carbon="glycerol"),
        rec("estimate", "pha_titre", 13.0, "g/L", provenance="industry-estimate"),
        rec("computed", "pha_titre", 13.0, "g/L", provenance="computed"),
        rec("cites", "pha_titre", 14.0, "g/L", primary=False),
        rec("rejected", "pha_titre", 15.0, "g/L", status="rejected"),
        rec("caseins", "pha_titre", 16.0, "g/L", paper="B5"),
    ]
    t = by_key(proforma.bind(rs))["titre"]
    assert t.recordIds == ["ok"] and t.leftOutNoCarbon == 1 and t.leftOutOtherCarbon == 1


def test_content_in_percent_of_dry_mass_becomes_a_share():
    c = by_key(proforma.bind([rec("c", "pha_content_cdw", 60.0, "% CDW")]))["content"]
    assert c.value == pytest.approx(0.6)


def test_a_host_filter_narrows_the_binding():
    rs = [rec("h", "pha_titre", 10.0, "g/L"), rec("k", "pha_titre", 20.0, "g/L", strain="p-putida-kt2440")]
    assert by_key(proforma.bind(rs, host="p-putida-kt2440"))["titre"].recordIds == ["k"]


def test_a_yield_above_the_ceiling_is_clipped_and_said():
    rs = [rec("y1", "pha_yield_substrate", 0.3, "g g-1"), rec("y2", "pha_yield_substrate", 0.7, "g g-1")]
    y = by_key(proforma.bind(rs, cap=(0.48, "ceilingid")))["yield"]
    assert y.high == pytest.approx(0.48) and any("clipped" in f for f in y.flags)


def test_a_refused_conversion_stops_the_binding_with_the_engines_reason():
    y = by_key(proforma.bind([rec("bad", "pha_titre", 1.0, "% CDW")]))["titre"]
    assert y.binding == "waiting" and "binding stopped" in y.flags[0]


def test_an_assumption_needs_a_named_person_and_its_own_range():
    with pytest.raises(proforma.ScenarioRefused, match="placeholder"):
        proforma.bind([], assumptions=[assume("recovery", 0.9, 0.8, 0.95, by="me")])
    with pytest.raises(proforma.ScenarioRefused, match="within its own low and high"):
        proforma.bind([], assumptions=[assume("recovery", 0.99, 0.8, 0.95)])
    r = by_key(proforma.bind([], assumptions=[assume("recovery", 0.9, 0.8, 0.95)]))["recovery"]
    assert r.binding == "assumption" and r.source.by == "Sean Creighton" and r.sampling == "uniform"


def test_a_run_with_inputs_waiting_is_refused_listing_every_one(store):
    pool = SimpleNamespace(records=[rec("t", "pha_titre", 10.0, "g/L")], records_by_id={})
    with pytest.raises(proforma.ScenarioRefused) as e:
        proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", assumptions=[assume("sugarFeed", 1000, 1000, 1000)]), pool=pool)
    for key in ("yield", "content", "productivity", "recovery", "sugarPrice"):
        assert key in str(e.value)
    assert "titre" not in str(e.value).split(":")[1] and "sugarFeed" not in str(e.value)


def test_the_basis_comes_back_as_the_same_sampling(store):
    rs = [rec(f"t{i}", "pha_titre", v, "g/L") for i, v in enumerate([10.0, 40.0, 25.0])]
    rs += [rec("y1", "pha_yield_substrate", 0.3, "g g-1"), rec("y2", "pha_yield_substrate", 0.7, "g g-1")]
    rs += [rec("c", "pha_content_cdw", 60.0, "% CDW")]
    inputs = proforma.bind(rs, assumptions=[assume("sugarPrice", 0.4, 0.3, 0.5)], cap=(0.48, "cap"))
    specs, base, kinds = proforma._specs(proforma.basis_inputs(inputs, (0.48, "cap")))
    assert specs["titre"] == {"kind": "triangular", "low": 10.0, "mode": 25.0, "high": 40.0}
    assert specs["yield"] == {"kind": "uniform", "low": 0.3, "high": 0.48}
    assert specs["content"] == {"kind": "fixed", "value": pytest.approx(0.6)}
    assert specs["sugarPrice"] == {"kind": "uniform", "low": 0.3, "high": 0.5} and base["sugarPrice"] == 0.4
    assert kinds == {"titre": "record", "yield": "record", "content": "record", "sugarPrice": "assumption"}


def test_the_scenario_endpoints(store, monkeypatch):
    from openferment_core import api, evidence_pool

    rs = [rec("t", "pha_titre", 10.0, "g/L"), rec("k", "pha_titre", 20.0, "g/L", strain="p-putida-kt2440")]
    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}))
    c = TestClient(api.app, base_url="http://127.0.0.1")
    # PHA is archived (OF-BLD-016): its scenario is served with the switch on (OF-BLD-019 §2.3).
    [sc] = [x for x in c.get("/api/proforma/scenarios?includeArchived=true").json() if x["id"] == "sc-pha-1"]
    assert sc["id"] == "sc-pha-1" and sc["hosts"] == ["c-necator-h16", "p-putida-kt2440"]
    assert set(sc["waiting"]) == {"yield", "content", "productivity", "recovery", "sugarPrice", "sugarFeed"}
    narrowed = c.get("/api/proforma/scenarios?includeArchived=true&host=p-putida-kt2440").json()
    assert next(x for x in narrowed if x["id"] == "sc-pha-1")["inputs"][0]["recordIds"] == ["k"]
    r = c.post("/api/proforma/run", json={"scenarioId": "sc-pha-1"})
    assert r.status_code == 422 and "wait for a source" in r.json()["detail"]
    assert c.post("/api/proforma/run", json={"scenarioId": "sc-pha-1"}, headers={"Origin": "https://evil.example"}).status_code == 403


# ── §8.R ───────────────────────────────────────────────────────────────


def test_r1_a_constant_input_has_no_rank_correlation():
    import numpy as np

    flat, rising = proforma._ranks(np.full(50, 0.3)), proforma._ranks(np.arange(50.0))
    assert proforma._spearman(flat, rising) is None
    two_same = [rec("a", "pha_titre", 10.0, "g/L"), rec("b", "pha_titre", 10.0, "g/L")]
    assert by_key(proforma.bind(two_same))["titre"].sampling == "fixed"
    specs, _, _ = proforma._specs(proforma.basis_inputs(proforma.bind(two_same), None))
    assert specs["titre"]["kind"] == "fixed"


def test_r2_an_assumption_fills_an_input_whose_binding_stopped():
    t = by_key(proforma.bind([rec("bad", "pha_titre", 1.0, "% CDW")], assumptions=[assume("titre", 50, 40, 60)]))["titre"]
    assert t.binding == "assumption" and any("binding stopped" in f for f in t.flags)


def test_r3_a_run_with_no_feasible_sample_makes_no_evidence():
    from types import SimpleNamespace

    art = SimpleNamespace(output={"quantiles": {}, "feasible": 0}, id="x")
    with pytest.raises(proforma.ScenarioRefused, match="no sample"):
        proforma.evidence_of(art)


# ── the dry-grind corn plant, the yeast program's reference (OF-BLD-019 §2.2) ──

from openferment_core.flowsheets import shelf as _shelf  # noqa: E402

# The eleven values biorefineries 2.35.1's own test asserts for the corn
# plant, RESTATED here from biorefineries/tests/test_biorefineries.py,
# test_corn (rtol 5e-2 each), only to hold the parser that reads that file
# to it. The file is the authority: the service, the slow test and the
# screens read the values from it through `shelf.package_regression`.
TEST_CORN = [
    ("tea.IRR", 0.05381572438333119),
    ("feedstock.price", 0.13227735731092652),
    ("product.price", 0.48547915353569393),
    ("tea.sales", 74992038.8556337),
    ("tea.material_cost", 52925382.42511212),
    ("tea.installed_equipment_cost", 65387501.9390586),
    ("tea.utility_cost", 10442066.327145828),
    ("units.get_heating_duty()", 111.3588815958425),
    ("units.get_cooling_duty()", 105.08735576937576),
    ("units.get_electricity_consumption()", 1.6248530112233648),
    ("units.get_electricity_production()", 0.0),
]


def test_the_corn_plant_is_the_yeast_programs_reference_on_the_shelf():
    corn = _shelf.SHELF["corn_drygrind"]
    assert corn.reference and corn.program == "yeast" and corn.source.startswith("biorefineries ")
    assert corn.source.endswith(", corn") and _shelf.REFERENCE_MODULES["corn_drygrind"] == "biorefineries.corn"
    assert corn.packageTest == "biorefineries/tests/test_biorefineries.py::test_corn"
    assert corn.priceOutput in corn.outputs and corn.priceBasis
    # Every input is the package's own default, named, bound to nothing.
    assert corn.inputs and {i.kind for i in corn.inputs} == {"convention"}
    assert all(i.fields == [] and i.note.startswith("the package's own default") for i in corn.inputs)
    assert len({i.key for i in corn.inputs}) == len(corn.inputs)


def test_the_package_test_values_are_read_from_the_installed_file():
    reg = _shelf.package_regression("corn_drygrind")
    assert reg is not None, "biorefineries is not installed here, or its test file moved"
    assert (reg.file, reg.test) == ("biorefineries/tests/test_biorefineries.py", "test_corn")
    assert reg.package.startswith("biorefineries ")
    assert [(v.expression, v.package) for v in reg.values] == TEST_CORN
    assert {v.rtol for v in reg.values} == {0.05}
    assert all(v.label != v.expression and v.unit is not None for v in reg.values)
    assert [v.expression for v in _shelf.package_regression("cornstover_benchmark").values] == [e for e, _ in TEST_CORN]
    assert _shelf.package_regression("pha_sugar_v0") is None and _shelf.package_regression("nowhere") is None


def test_a_check_holds_as_numpy_allclose_holds_it():
    from openferment_core.models import PackageRegression, RegressionValue

    reg = PackageRegression(package="p", file="f", test="t", values=[
        RegressionValue(expression="a", label="a", unit="", package=100.0, rtol=0.05),
        RegressionValue(expression="b", label="b", unit="", package=0.0, rtol=0.05),
        RegressionValue(expression="c", label="c", unit="", package=1.0, rtol=0.05),
    ])
    a, b, c = proforma.regression_checks(reg, {"a": 104.9, "b": 1e-9})
    assert a.within and a.relDiff == pytest.approx(0.049)
    assert b.within and b.relDiff is None  # zero asserted: |measured| within numpy's absolute tolerance
    assert not c.within and c.measured is None
    [d] = proforma.regression_checks(reg.model_copy(update={"values": reg.values[:1]}), {"a": 105.1})
    assert not d.within


def test_a_reference_not_yet_run_reads_as_none_and_starts_nothing(store):
    from openferment_core import api

    before = proforma.status()["status"]
    c = TestClient(api.app, base_url="http://127.0.0.1")
    r = c.get("/api/proforma/reference/corn_drygrind").json()
    assert r["artifact"] is None and r["simulator"]["status"] == before
    assert r["flowsheet"]["id"] == "corn_drygrind" and r["regression"]["test"] == "test_corn"
    assert c.get("/api/proforma/reference/cornstover_benchmark").json()["regression"]["test"] == "test_cornstover"
    for bad, said in (("pha_sugar_v0", "not a reference biorefinery"), ("toy", "STAND-IN for tests"),
                      ("nowhere", "no flowsheet nowhere")):
        for r in (c.get(f"/api/proforma/reference/{bad}"), c.post(f"/api/proforma/reference/{bad}")):
            assert r.status_code == 404 and said in r.json()["detail"]
    assert c.post("/api/proforma/reference/corn_drygrind", headers={"Origin": "https://evil.example"}).status_code == 403
    assert proforma.status()["status"] == before


def test_a_reference_run_is_one_artifact_with_its_basis_and_the_package_values(store, monkeypatch):
    # The run goes through the real code (the basis, the artifact store, the
    # package test parsed from the installed file) with demo.py's STAND-IN
    # answering for the worker, as the double's fixture is made.
    from openferment_core import api, artifacts, demo

    monkeypatch.setattr(proforma, "call", demo._standin_call)
    art = proforma.run_reference("corn_drygrind")
    assert art.tool == proforma.REFERENCE and art.toolVersion.startswith(proforma.REFERENCE_VERSION)
    assert art.provenance == "computed" and {i.source.kind for i in art.inputs} == {"model", "convention"}
    named = {i.name: i for i in art.inputs}
    assert named["flowsheet"].source.id.startswith("biorefineries.corn@")
    assert named["precision"].value == f"{proforma.REFERENCE_DIGITS} significant digits"
    assert "_ins_size_is_fixed" in str(named["compatibility"].value)
    for i in _shelf.SHELF["corn_drygrind"].inputs:  # each default named in the basis, its value read back
        assert named[i.key].value == "the package's default" and named[i.key].source.kind == "model"
    o = art.output
    assert [c["expression"] for c in o["checks"]] == [e for e, _ in TEST_CORN]
    assert o["regression"]["test"] == "test_corn" and o[_shelf.SHELF["corn_drygrind"].priceOutput] is not None
    t = proforma.tables_of(art)  # the one reader reads a reference run as it reads a scenario run
    assert t.flowsheet == "corn_drygrind" and t.tablesSource == demo.PROFORMA_STANDIN and t.units and t.streams
    assert proforma.stored_reference("corn_drygrind").id == art.id and proforma.stored_reference("cornstover_benchmark") is None
    c = TestClient(api.app, base_url="http://127.0.0.1")
    assert c.get("/api/proforma/reference/corn_drygrind").json()["artifact"]["id"] == art.id
    again = c.post("/api/proforma/reference/corn_drygrind").json()
    assert again["artifact"]["id"] == art.id and again["artifact"]["createdAt"] == art.createdAt  # stored, not rerun
    assert artifacts.replay(art.id).identical
    # The benchmark's own endpoint answers exactly as before: a reference
    # run of any plant is not the benchmark's artifact.
    proforma.run_reference("cornstover_benchmark")
    assert c.get("/api/proforma/benchmark").json()["artifact"] is None


@pytest.mark.sim
def test_the_corn_plant_runs_in_the_worker_and_reads_back_every_input(store):
    # Marked sim: the real worker builds the package's plant (about a second
    # once BioSTEAM is loaded); test_proforma_slow holds its numbers to the
    # package's test.
    proforma.start(background=False)
    pha = {"titre": 50.0, "yield": 0.3, "content": 0.7, "productivity": 1.0, "recovery": 0.95, "sugarPrice": 0.4,
           "sugarFeed": 10000.0}  # PLACEHOLDER inputs to exercise the PHA draft; no price here is a result
    before = proforma.call("run", {"flowsheet": "pha_sugar_v0", "base": pha, "specs": {}, "samples": 0, "seed": 0})
    art = proforma.run_reference("corn_drygrind")
    o = art.output
    corn = _shelf.SHELF["corn_drygrind"]
    assert set(o["readBack"]) == {i.key for i in corn.inputs}
    assert all(isinstance(v, float) for k, v in o["readBack"].items() if k != "depreciation")
    assert set(o["measured"]) == set(_shelf.TEST_QUANTITIES) and len(o["checks"]) == len(TEST_CORN)
    assert set(corn.outputs) <= set(o) and o["simulator"].startswith("biosteam ")
    t = proforma.tables_of(art)
    assert t.tea.product == "ethanol" and t.tea.feedstock == "corn" and t.tea.teaClass == "ConventionalEthanolTEA"
    assert "SimultaneousSaccharificationFermentation" in {u.unitClass for u in t.units}
    assert len({s.id for s in t.streams}) == len(t.streams) and all(s.id for s in t.streams)
    assert t.unitOrder == [u.id for u in t.units]
    assert sum(line.perUnit for line in t.tea.lines) == pytest.approx(o["ethanolPriceUsdPerKg"], rel=1e-8)
    # The units the shelf states for the package test's duties are BioSTEAM's
    # own: the worker reads the UnitGroup's DUTY_UNITS and ELEC_UNITS.
    assert _shelf.TEST_QUANTITIES["units.get_heating_duty()"][1] == t.utilities.heatingUnit
    assert _shelf.TEST_QUANTITIES["units.get_cooling_duty()"][1] == t.utilities.coolingUnit
    assert _shelf.TEST_QUANTITIES["units.get_electricity_consumption()"][1] == t.utilities.electricityConsumptionUnit
    assert _shelf.TEST_QUANTITIES["units.get_electricity_production()"][1] == t.utilities.electricityProductionUnit
    # The worker put back what it held: the PHA draft, built before, prices as it did.
    after = proforma.call("run", {"flowsheet": "pha_sugar_v0", "base": pha, "specs": {}, "samples": 0, "seed": 0})
    assert after["base"] == before["base"] and after["tables"]["tea"] == before["tables"]["tea"]


# ── glucose to ethanol through the real worker (OF-BLD-019 §2.3; `sim`) ──
# Every input is a STAND-IN typed here as a fixture's assumption, so the run
# is `demo`; none is a measurement and no price here is a result.

ETHANOL_STANDIN = {"feed_glucose_conc": 100.0, "titre": 45.0, "yield": 0.45, "productivity": 2.0,
                   "plant_scale": 100000.0, "glucose_price": 0.4}


def replays_to_the_last_digits(artifact_id: str, rel: float = 1e-9) -> None:
    """A run of the ethanol flowsheet replays, identically or with every
    difference a number within `rel`: BioSTEAM's solvers carry noise in the
    last digits between cases (measured 2026-10-20: one ulp of the price in
    some cases), and the replay names it rather than hiding it."""
    from openferment_core import artifacts

    r = artifacts.replay(artifact_id)
    for d in r.differences:
        if d.path in ("…", "toolVersion"):
            assert d.path == "…", d
            continue
        assert isinstance(d.stored, (int, float)) and isinstance(d.replayed, (int, float)), d
        assert d.replayed == pytest.approx(d.stored, rel=rel, abs=1e-12), d


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    return proforma


@pytest.mark.sim
def test_the_ethanol_flowsheet_converges_on_stand_in_assumptions(warm, store):
    from openferment_core import artifacts

    a = [assume(k, v, v, v, by="openFerment test fixture") for k, v in ETHANOL_STANDIN.items()]
    art = proforma.run_flowsheet("ethanol_glucose_v0", a, samples=8, seed=1, scenario_id="sc-yeast-1")
    o = art.output
    assert art.provenance == "demo" and o["baseInfeasible"] is None and o["feasible"] == o["samples"] == 8
    assert o["basePrice"] > 0 and o["flowsheet"] == "ethanol_glucose_v0"
    assert [i.value for i in art.inputs if i.name == "scenario"] == ["sc-yeast-1"]
    t = proforma.tables_of(art)
    assert t.tea.teaClass == "ConventionalEthanolTEA" and t.tea.product == "ethanol" and t.tea.feedstock == "glucose"
    assert sum(line.perUnit for line in t.tea.lines) == pytest.approx(o["basePrice"], rel=1e-9)
    classes = [u.unitClass for u in t.units]
    assert classes[:2] == ["Mixer", "Fermenter"] and classes.count("BinaryDistillation") == 2 and "MolecularSieve" in classes
    rb = o["readBack"]
    # The theoretical yield is computed in the worker from the reaction and
    # thermosteam's molecular weights; the document states 0.511.
    assert rb["theoreticalYieldGPerG"] == pytest.approx(0.511, abs=5e-4)
    assert rb["fermenterConversion"] == pytest.approx(ETHANOL_STANDIN["yield"] / rb["theoreticalYieldGPerG"], rel=1e-12)
    assert rb["batchTimeH"] == pytest.approx(ETHANOL_STANDIN["titre"] / ETHANOL_STANDIN["productivity"], rel=1e-12)
    assert rb["denaturantFraction"] == 0 and rb["productEthanolMassFraction"] > rb["beerEthanolGPerL"] / 1000
    # The feed's glucose is the bound concentration, by thermosteam's volume of the solution.
    glucose = next(s for s in t.streams if s.id == "glucose_solution")
    assert glucose.massFlows["Glucose"] == pytest.approx(rb["glucoseFedKgPerH"], rel=1e-12)
    assert artifacts.get(art.id).id == art.id
    replays_to_the_last_digits(art.id)


@pytest.mark.sim
def test_a_yield_above_the_theoretical_cannot_run_and_says_why(warm):
    above = {**ETHANOL_STANDIN, "yield": 0.6}
    r = warm.call("run", {"flowsheet": "ethanol_glucose_v0", "base": above, "specs": {"yield": {"kind": "fixed", "value": 0.6}},
                          "samples": 3, "seed": 0})
    assert r["base"] is None and "above the theoretical yield of ethanol on glucose" in r["baseInfeasible"]
    assert r["tables"] is None
    assert [s["infeasible"]["reason"] for s in r["montecarlo"]["samples"]] == ["yield"] * 3
