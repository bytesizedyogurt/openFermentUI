"""Proforma's slow runs (OF-BLD-014 §8.2, §8.3): `pnpm test:slow`, outside
verify. Each starts the real BioSTEAM worker and runs a whole flowsheet."""
from __future__ import annotations

import pytest

from openferment_core import artifacts, intake, proforma

pytestmark = [pytest.mark.slow, pytest.mark.sim]


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def test_the_benchmark_reproduces_the_published_price(store):
    # B.3: 1.968 USD per gallon with the package's defaults, within 0.5 %.
    art = proforma.run_benchmark()
    assert art.output["mespUsdPerGal"] == pytest.approx(1.968, rel=0.005)
    assert art.output["package"] == "biorefineries.cornstover@2.35.1"
    assert art.provenance == "computed" and {i.source.kind for i in art.inputs} == {"model"}
    assert proforma.stored_benchmark().id == art.id
    # The plant is built afresh for every run (OF-BLD-019 §2.R), so a replay
    # in the same worker builds a second plant, and BioSTEAM's sums over a
    # set of units move the last digit, as they do for a reference run:
    # measured, 0.6588136420152626 against …628 USD/kg. The replay is held to
    # the last digits, as the ethanol runs' are.
    from test_proforma import replays_to_the_last_digits

    replays_to_the_last_digits(art.id)


# ── the dry-grind corn plant (OF-BLD-019 §2.2) ─────────────────────────
# The authority is the installed package's own test file: each value below
# is read from biorefineries/tests/test_biorefineries.py, test_corn, by
# flowsheets/shelf.py's `package_regression` (test_proforma holds that
# parser to the eleven values the file writes). This installation must
# reproduce every one of them within the test's own rtol (5 %).

CORN_TEST = (
    "tea.IRR", "feedstock.price", "product.price", "tea.sales", "tea.material_cost", "tea.installed_equipment_cost",
    "tea.utility_cost", "units.get_heating_duty()", "units.get_cooling_duty()",
    "units.get_electricity_consumption()", "units.get_electricity_production()",
)


def test_the_corn_plant_reproduces_its_package_test(store):
    import numpy as np

    from openferment_core.flowsheets import shelf

    regression = shelf.package_regression("corn_drygrind")
    assert regression is not None and regression.test == "test_corn"
    assert tuple(v.expression for v in regression.values) == CORN_TEST
    art = proforma.run_reference("corn_drygrind")
    measured = art.output["measured"]
    for v in regression.values:
        # as the package's test asserts it: numpy.allclose(measured, value, rtol=5e-2)
        assert np.allclose(measured[v.expression], v.package, rtol=v.rtol), (v.expression, measured[v.expression], v.package)
    assert all(c["within"] for c in art.output["checks"])
    assert art.output["ethanolPriceUsdPerKg"] == pytest.approx(regression.values[2].package, rel=1e-9)
    assert art.output["IRR"] == pytest.approx(measured["tea.IRR"])
    assert art.provenance == "computed" and {i.source.kind for i in art.inputs} == {"model", "convention"}
    # A fresh build of the plant replays to the same output, digit for digit.
    assert artifacts.replay(art.id).identical
    assert proforma.stored_reference("corn_drygrind").id == art.id


def test_the_corn_stover_plant_answers_through_the_reference_endpoint_too(store):
    # The benchmark's own endpoints answer as before; the same plant's
    # reference run gives the benchmark's price and every table.
    from fastapi.testclient import TestClient

    from openferment_core import api

    c = TestClient(api.app, base_url="http://127.0.0.1")
    bench = c.post("/api/proforma/benchmark").json()["artifact"]
    assert bench["tool"] == proforma.BENCHMARK and bench["output"]["mespUsdPerGal"] == pytest.approx(1.968, rel=0.005)
    ref = c.post("/api/proforma/reference/cornstover_benchmark").json()
    art = ref["artifact"]
    assert art["tool"] == proforma.REFERENCE and ref["regression"]["test"] == "test_cornstover"
    assert art["output"]["mespUsdPerGal"] == pytest.approx(bench["output"]["mespUsdPerGal"], rel=1e-9)
    assert art["output"]["tea"]["product"] == "ethanol" and art["output"]["units"]
    assert c.get("/api/proforma/benchmark").json()["artifact"]["id"] == bench["id"]
    assert proforma.run_benchmark().output == bench["output"]
    # MEASURED 2026-10-20 (biosteam 2.54.0, biorefineries 2.35.1): the
    # package's own test_cornstover does not hold on these versions for two
    # of its eleven values, installed equipment cost and electricity
    # consumption; the run says so in its checks, and this pins the finding.
    outside = {k["expression"] for k in art["output"]["checks"] if not k["within"]}
    assert outside == {"tea.installed_equipment_cost", "units.get_electricity_consumption()"}
    # The corn stover plant's facilities are built from a set, so their order
    # and the names BioSTEAM gives unnamed streams change from one build to
    # the next; its numbers do not.
    replay = artifacts.replay(art["id"])
    moved = {d.path.split("[")[0].split(".")[0] for d in replay.differences}
    assert moved <= {"streams", "units", "unitOrder", "…"}, moved


# ── glucose to ethanol (OF-BLD-019 §2.3) ───────────────────────────────
# PLACEHOLDER inputs, chosen here to exercise the flowsheet; none is a
# measurement and no price below is a result.

ETHANOL_CASE = {"feed_glucose_conc": 100.0, "titre": 45.0, "yield": 0.45, "productivity": 2.0, "plant_scale": 100000.0,
                "glucose_price": 0.4}
# What this lock (biosteam 2.54.0, thermosteam 0.54.2, biorefineries 2.35.1)
# gave on ETHANOL_CASE, measured 2026-10-20: a regression value for the
# code, held within 1 %, never shown as a price of anything.
ETHANOL_REGRESSION_USD_PER_KG = 1.0654458162278913


@pytest.fixture(scope="module")
def eth():
    from openferment_core.flowsheets import ethanol_glucose_v0

    return ethanol_glucose_v0, ethanol_glucose_v0.build()


def test_the_ethanol_price_on_fixed_stand_ins_holds_its_regression_value(eth):
    f, b = eth
    out = f.evaluate(b, ETHANOL_CASE)
    assert out["pricePerKgEthanol"] == pytest.approx(ETHANOL_REGRESSION_USD_PER_KG, rel=0.01)
    assert sum(out["costLines"].values()) == pytest.approx(out["pricePerKgEthanol"], rel=1e-12)
    # The glucose is charged on glucose alone, and the feed holds the bound
    # glucose per litre of solution, by thermosteam's volume.
    assert b.glucose.cost == pytest.approx(ETHANOL_CASE["glucose_price"] * b.glucose.imass["Glucose"], rel=1e-12)
    solution = b.M1.outs[0]
    assert solution.imass["Glucose"] / solution.F_vol == pytest.approx(ETHANOL_CASE["feed_glucose_conc"], rel=1e-9)
    # The fermenter makes what the yield says from the glucose fed.
    assert b.R1.outs[1].imass["Ethanol"] + b.R1.outs[0].imass["Ethanol"] == pytest.approx(
        ETHANOL_CASE["yield"] * b.glucose.imass["Glucose"], rel=1e-9)


def test_an_ethanol_case_gives_one_price_whatever_ran_before(eth):
    # The recycle is emptied before every case (carried over, it moved a
    # price in its fourth digit); what remains is BioSTEAM's own noise in the
    # last digit, which a fresh build does not remove either (measured).
    f, b = eth
    first = f.evaluate(b, ETHANOL_CASE)["pricePerKgEthanol"]
    f.evaluate(b, {**ETHANOL_CASE, "feed_glucose_conc": 20.0, "yield": 0.3})
    assert f.evaluate(b, ETHANOL_CASE)["pricePerKgEthanol"] == pytest.approx(first, rel=1e-12)
    assert f.evaluate(f.build(), ETHANOL_CASE)["pricePerKgEthanol"] == pytest.approx(first, rel=1e-12)


def test_a_dearer_glucose_raises_the_ethanol_price(eth):
    f, b = eth
    prices = [f.evaluate(b, {**ETHANOL_CASE, "glucose_price": p})["pricePerKgEthanol"] for p in (0.2, 0.3, 0.4, 0.5)]
    assert all(a < c for a, c in zip(prices, prices[1:]))


def test_a_whole_yeast_run_through_the_worker(store, monkeypatch):
    from types import SimpleNamespace

    import standins
    from openferment_core.models import InputAssumption, ProformaRunRequest

    # A scenario the service holds by its id, on the ethanol flowsheet: the seed's left with it (ADR-010).
    monkeypatch.setattr(proforma, "seed_scenarios", lambda: [
        {"id": "sc-held-ethanol", "name": "A held test scenario", "kind": "biosteam", "modelId": "ethanol_glucose_v0"}])
    rs = standins._standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    a = [InputAssumption(key=k, value=v, low=lo, high=hi, by="openFerment test fixture", at="2026-10-20")
         for k, v, lo, hi in standins.YEAST_STANDIN_ASSUMED]
    out = proforma.run(ProformaRunRequest(scenarioId="sc-held-ethanol", assumptions=a, seed=3), pool=pool)
    assert out.samples == 500 and out.feasible + sum(out.infeasible.values()) == 500 and out.baseInfeasible is None
    assert set(out.infeasible) <= {"yield", "concentration", "convergence"}
    assert out.provenance == "demo" and out.flowsheet == "ethanol_glucose_v0" and out.tea.teaClass == "ConventionalEthanolTEA"
    q = out.quantiles
    assert q["p5"] <= q["p25"] <= q["p50"] <= q["p75"] <= q["p95"]
    assert {s.key for s in out.sensitivity} <= {"feed_glucose_conc", "titre", "yield", "productivity", "glucose_price"}
    assert len(out.grid.msp) == 125 and sum(out.baseCostLines.values()) == pytest.approx(out.basePrice, rel=1e-12)
    assert [i.value for i in artifacts.get(out.artifactId).inputs if i.name == "scenario"] == ["sc-held-ethanol"]
    from test_proforma import replays_to_the_last_digits

    replays_to_the_last_digits(out.artifactId)


def test_an_ethanol_case_prices_on_biosteams_own_utility_prices_whatever_ran_before(eth):
    # §2.R, review 1: the corn stover plant sets its own utility prices and
    # cost index as it builds (CEPCI 525.4, free steam and cooling water, in
    # biorefineries.cellulosic's load_process_settings). Run here, in this
    # process and outside the worker's package_defaults, it leaves them set;
    # an ethanol case still prices on BioSTEAM's own defaults, which its
    # basis names, and reads each back.
    import biosteam as bst

    from openferment_core.flowsheets import cornstover_benchmark

    f, b = eth
    first = f.evaluate(b, ETHANOL_CASE)
    cornstover_benchmark.run()
    left = (bst.CE, bst.PowerUtility.price)
    out = f.evaluate(b, ETHANOL_CASE)
    rb = out["readBack"]
    bst.process_tools.default_utilities()
    bst.process_tools.default_CEPCI()
    assert left != (bst.CE, bst.PowerUtility.price), "the corn stover plant left BioSTEAM's defaults as they were"
    assert rb["cepci"] == bst.CE and rb["electricityPrice"] == bst.PowerUtility.price
    agents = {a.ID: a for a in (*bst.HeatUtility.heating_agents, *bst.HeatUtility.cooling_agents)}
    for agent_id in ("low_pressure_steam", "cooling_water"):
        key = "".join(w if i == 0 else w.capitalize() for i, w in enumerate(agent_id.split("_")))
        a = agents[agent_id]
        assert rb[f"{key}RegenerationPrice"] == a.regeneration_price and rb[f"{key}T"] == a.T, agent_id
        assert rb[f"{key}HeatTransferPrice"] == a.heat_transfer_price, agent_id
    assert out["pricePerKgEthanol"] == pytest.approx(first["pricePerKgEthanol"], rel=1e-12)
    assert out["pricePerKgEthanol"] == pytest.approx(ETHANOL_REGRESSION_USD_PER_KG, rel=0.01)
