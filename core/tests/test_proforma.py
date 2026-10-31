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


ETHANOL = proforma.ETHANOL


def rec(rid, field, value, unit, *, paper="T1", carbon="glucose", strain="strain-ab12", **kw):
    return {"id": rid, "paperId": paper, "field": field, "value": value, "unit": unit, "carbonSource": carbon,
            "strainId": strain, "organismText": "Test organism", "provenance": "unverified", "status": "unverified",
            "primary": True, **kw}


def assume(key, value, low, high, by="Sean Creighton"):
    return InputAssumption(key=key, value=value, low=low, high=high, by=by, at="2026-10-15")


def by_key(inputs):
    return {i.key: i for i in inputs}


def test_two_records_are_a_pair_and_one_is_held_fixed_and_flagged():
    two = by_key(proforma.bind_inputs(ETHANOL, [rec("a", "ethanol_titre", 10.0, "g/L"), rec("b", "ethanol_titre", 20.0, "g/L")]))["titre"]
    assert (two.low, two.high, two.sampling) == (10.0, 20.0, "uniform")
    one = by_key(proforma.bind_inputs(ETHANOL, [rec("a", "ethanol_titre", 10.0, "g/L")]))["titre"]
    assert one.sampling == "fixed" and proforma.SINGLE in one.flags


def test_an_assumption_needs_a_named_person_and_its_own_range():
    with pytest.raises(proforma.ScenarioRefused, match="placeholder"):
        proforma.bind_inputs(ETHANOL, [], assumptions=[assume("glucose_price", 0.4, 0.3, 0.5, by="me")])
    with pytest.raises(proforma.ScenarioRefused, match="within its own low and high"):
        proforma.bind_inputs(ETHANOL, [], assumptions=[assume("glucose_price", 0.6, 0.3, 0.5)])
    r = by_key(proforma.bind_inputs(ETHANOL, [], assumptions=[assume("glucose_price", 0.4, 0.3, 0.5)]))["glucose_price"]
    assert r.binding == "assumption" and r.source.by == "Sean Creighton" and r.sampling == "uniform"


def test_a_run_with_inputs_waiting_is_refused_listing_every_one(store):
    pool = SimpleNamespace(records=[rec("t", "ethanol_titre", 10.0, "g/L")], records_by_id={})
    with pytest.raises(proforma.ScenarioRefused) as e:
        proforma.run(ProformaRunRequest(scenarioId="sc-k3x9q-1", flowsheet=ETHANOL,
                                        assumptions=[assume("plant_scale", 1000, 1000, 1000)]), pool=pool)
    for key in ("feed_glucose_conc", "yield", "productivity", "glucose_price"):
        assert key in str(e.value)
    assert "titre" not in str(e.value).split(":")[1] and "plant_scale" not in str(e.value)


def test_the_basis_comes_back_as_the_same_sampling(store):
    rs = [rec(f"t{i}", "ethanol_titre", v, "g/L") for i, v in enumerate([10.0, 40.0, 25.0])]
    rs += [rec("p1", "ethanol_productivity", 1.0, "g L-1 h-1"), rec("p2", "ethanol_productivity", 3.0, "g L-1 h-1")]
    rs += [rec("y", "ethanol_yield_substrate", 0.4, "g g-1")]
    inputs = proforma.bind_inputs(ETHANOL, rs, assumptions=[assume("glucose_price", 0.4, 0.3, 0.5)])
    specs, base, kinds = proforma._specs(proforma.basis_inputs(inputs, ETHANOL))
    assert specs["titre"] == {"kind": "triangular", "low": 10.0, "mode": 25.0, "high": 40.0}
    assert specs["productivity"] == {"kind": "uniform", "low": 1.0, "high": 3.0}
    assert specs["yield"] == {"kind": "fixed", "value": pytest.approx(0.4)}
    assert specs["glucose_price"] == {"kind": "uniform", "low": 0.3, "high": 0.5} and base["glucose_price"] == 0.4
    assert kinds == {"titre": "record", "productivity": "record", "yield": "record", "glucose_price": "assumption"}


# ── §8.R ───────────────────────────────────────────────────────────────


def test_r1_a_constant_input_has_no_rank_correlation():
    import numpy as np

    flat, rising = proforma._ranks(np.full(50, 0.3)), proforma._ranks(np.arange(50.0))
    assert proforma._spearman(flat, rising) is None
    two_same = [rec("a", "ethanol_titre", 10.0, "g/L"), rec("b", "ethanol_titre", 10.0, "g/L")]
    assert by_key(proforma.bind_inputs(ETHANOL, two_same))["titre"].sampling == "fixed"
    specs, _, _ = proforma._specs(proforma.basis_inputs(proforma.bind_inputs(ETHANOL, two_same), ETHANOL))
    assert specs["titre"]["kind"] == "fixed"


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
    assert _shelf.package_regression(ETHANOL) is None and _shelf.package_regression("nowhere") is None


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
    for bad, said in ((ETHANOL, "not a reference biorefinery"), ("toy", "STAND-IN for tests"),
                      ("nowhere", "no flowsheet nowhere")):
        for r in (c.get(f"/api/proforma/reference/{bad}"), c.post(f"/api/proforma/reference/{bad}")):
            assert r.status_code == 404 and said in r.json()["detail"]
    assert c.post("/api/proforma/reference/corn_drygrind", headers={"Origin": "https://evil.example"}).status_code == 403
    assert proforma.status()["status"] == before


def test_a_reference_run_is_one_artifact_with_its_basis_and_the_package_values(store, monkeypatch):
    # The run goes through the real code (the basis, the artifact store, the
    # package test parsed from the installed file) with demo.py's STAND-IN
    # answering for the worker, as the double's fixture is made.
    from openferment_core import api, artifacts
    import standins

    monkeypatch.setattr(proforma, "call", standins._standin_call)
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
    assert t.flowsheet == "corn_drygrind" and t.tablesSource == standins.PROFORMA_STANDIN and t.units and t.streams
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
    before = proforma.call(*ETHANOL_RUN)
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
    # The worker put back what it held: the ethanol flowsheet, built before, prices as it did.
    after = proforma.call(*ETHANOL_RUN)
    assert after["base"] == before["base"] and after["tables"]["tea"] == before["tables"]["tea"]


# ── glucose to ethanol through the real worker (OF-BLD-019 §2.3; `sim`) ──
# Every input is a STAND-IN typed here as a fixture's assumption, so the run
# is `assumed`; none is a measurement and no price here is a result.

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
    art = proforma.run_flowsheet("ethanol_glucose_v0", a, samples=8, seed=1, scenario_id="sc-k3x9q-1")
    o = art.output
    assert art.provenance == "assumed" and o["baseInfeasible"] is None and o["feasible"] == o["samples"] == 8
    assert o["basePrice"] > 0 and o["flowsheet"] == "ethanol_glucose_v0"
    assert [i.value for i in art.inputs if i.name == "scenario"] == ["sc-k3x9q-1"]
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
    # §2.R, review 6: the product's row carries the price the run solved, the
    # price every TEA line is read at, never the package's list price.
    [product] = [s for s in t.streams if s.id == t.tea.product]
    assert product.price == pytest.approx(t.tea.productPrice, rel=1e-12) and product.price == pytest.approx(o["basePrice"], rel=1e-12)
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


# ── the warm worker keeps no plant's settings (OF-BLD-019 §2.R) ────────
# Review findings 0, 9 and 10: a plant one op built or ran changed what the
# next op in the same worker priced (the benchmark left corn stover's utility
# prices and cost index behind; the corn plant's chemicals lock ammonia to
# liquid in objects the corn stover plant shares; BioSTEAM's stream tickets
# ran on from whatever was built first). Each op here is held to what a
# worker started for it alone gives, within the replay tolerance the tests
# use (`replays_to_the_last_digits`).

ETHANOL_RUN = ("run", {"flowsheet": "ethanol_glucose_v0", "base": ETHANOL_STANDIN, "specs": {}, "samples": 0, "seed": 0})
BENCHMARK_RUN = ("benchmark", {})
CORN_RUN = ("reference", {"flowsheet": "corn_drygrind", "digits": proforma.REFERENCE_DIGITS})


def in_a_worker_of_its_own(calls):
    """Each call in turn in a worker started for these calls alone, so the
    first answer is what a fresh worker gives."""
    from openferment_core.workers import SimWorker

    w = SimWorker("openferment_core.workers.proforma_worker", timeout_s=proforma.CALL_TIMEOUT_S)
    try:
        return [w.call(op, args) for op, args in calls]
    finally:
        w.close()


@pytest.mark.sim
def test_the_warm_worker_keeps_no_plants_settings():
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(3) as ex:
        ordered = ex.submit(in_a_worker_of_its_own, [ETHANOL_RUN, BENCHMARK_RUN, CORN_RUN, ETHANOL_RUN, BENCHMARK_RUN])
        benchmark_first = ex.submit(in_a_worker_of_its_own, [BENCHMARK_RUN, ETHANOL_RUN])
        corn_first = ex.submit(in_a_worker_of_its_own, [CORN_RUN, BENCHMARK_RUN, ETHANOL_RUN])
        ethanol, benchmark, corn, ethanol_again, benchmark_again = ordered.result()
        fresh_benchmark, ethanol_built_last = benchmark_first.result()
        fresh_corn, benchmark_after_corn, ethanol_after_corn = corn_first.result()
    tol = {"rel": 1e-9, "abs": 1e-12}
    price = lambda r: r["base"]["pricePerKgEthanol"]  # noqa: E731
    seen = {"benchmark after ethanol": benchmark["mespUsdPerGal"], "benchmark first": fresh_benchmark["mespUsdPerGal"],
            "benchmark after the corn plant": benchmark_again["mespUsdPerGal"],
            "benchmark after the corn plant first": benchmark_after_corn["mespUsdPerGal"],
            "ethanol first": price(ethanol), "ethanol after the benchmark and corn": price(ethanol_again),
            "ethanol built after the benchmark": price(ethanol_built_last)}
    # The benchmark, after the ethanol flowsheet built corn's chemicals, and
    # again after the corn plant ran, gives what a worker that ran nothing
    # before gives (finding 10; the corn plant's run reached it through the
    # chemicals its package shares with the corn stover plant's).
    assert benchmark["mespUsdPerGal"] == pytest.approx(fresh_benchmark["mespUsdPerGal"], **tol), seen
    assert benchmark_again["mespUsdPerGal"] == pytest.approx(fresh_benchmark["mespUsdPerGal"], **tol), seen
    assert benchmark_after_corn["mespUsdPerGal"] == pytest.approx(fresh_benchmark["mespUsdPerGal"], **tol), seen
    assert benchmark["mespUsdPerGal"] == pytest.approx(1.968, rel=0.005)
    # So does the corn plant, after the ethanol flowsheet and the benchmark.
    for key in ("ethanolPriceUsdPerKg", "IRR", "ethanolKgPerH", "cornKgPerH"):
        assert corn[key] == pytest.approx(fresh_corn[key], **tol), key
    for expression, value in fresh_corn["measured"].items():
        assert corn["measured"][expression] == pytest.approx(value, **tol), expression
    # The ethanol flowsheet prices as it did first, once the benchmark and the
    # corn plant ran (finding 0), and when built after the benchmark alone;
    # its utility and capital lines with it.
    assert price(ethanol_again) == pytest.approx(price(ethanol), **tol), seen
    assert price(ethanol_built_last) == pytest.approx(price(ethanol), **tol), seen
    assert price(ethanol_after_corn) == pytest.approx(price(ethanol), **tol), seen
    for later in (ethanol_again, ethanol_built_last, ethanol_after_corn):
        for line, v in ethanol["base"]["costLines"].items():
            assert later["base"]["costLines"][line] == pytest.approx(v, **tol), line
        assert later["base"]["readBack"] == pytest.approx(ethanol["base"]["readBack"], **tol)
    # The streams a package leaves unnamed take the same ids whichever plant
    # the worker built first (finding 9).
    ids = lambda r: [s["id"] for s in r["tables"]["streams"]]  # noqa: E731
    wiring = lambda r: [(u["id"], u["ins"], u["outs"]) for u in r["tables"]["units"]]  # noqa: E731
    for later in (ethanol_built_last, ethanol_after_corn):
        assert ids(later) == ids(ethanol) and wiring(later) == wiring(ethanol)
