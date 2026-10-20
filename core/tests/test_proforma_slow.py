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
    assert artifacts.replay(art.id).identical


# ── the PHA flowsheet (§8.3) ───────────────────────────────────────────
# PLACEHOLDER inputs, chosen here to exercise the flowsheet; none is a
# measurement and no price below is a result.

CASE = {"titre": 50.0, "yield": 0.3, "content": 0.7, "productivity": 1.0, "recovery": 0.95, "sugarPrice": 0.4,
        "sugarFeed": 10000.0}


@pytest.fixture(scope="module")
def pha():
    from openferment_core.flowsheets import pha_sugar_v0

    return pha_sugar_v0, pha_sugar_v0.build()


def test_the_reactions_balance(pha):
    f, b = pha
    from thermosteam.reaction import Reaction

    for text in (f.POLYMER, f.RESPIRATION):
        Reaction(text, reactant="Glucose", X=1.0, check_atomic_balance=True)  # raises when unbalanced
    st = b.cells_reaction
    assert st["Glucose"] == pytest.approx(-1.0) and st["NH3"] < 0 and st[f.CELLS] > 0


def test_polymer_out_is_sugar_in_times_yield_times_recovery(pha):
    f, b = pha
    out = f.evaluate(b, CASE)
    assert out["phaKgPerH"] == pytest.approx(CASE["sugarFeed"] * CASE["yield"] * CASE["recovery"], rel=1e-6)
    assert sum(out["costLines"].values()) == pytest.approx(out["pricePerKgPha"], rel=1e-12)
    assert set(out["costLines"]) == {"capex", "media", "utilities", "labor", "downstream", "other"}
    # The sugar is charged on sugar alone (§8.3 found the probe priced the diluted feed).
    assert b.feed.cost == pytest.approx(CASE["sugarPrice"] * CASE["sugarFeed"], rel=1e-9)


def test_a_resimulated_case_equals_a_fresh_build(pha):
    f, b = pha
    f.evaluate(b, {**CASE, "titre": 60.0, "yield": 0.32})
    again = f.evaluate(b, CASE)["pricePerKgPha"]
    fresh = f.evaluate(f.build(), CASE)["pricePerKgPha"]
    assert again == pytest.approx(fresh, rel=1e-7)


def test_a_higher_sugar_price_raises_the_price(pha):
    f, b = pha
    prices = [f.evaluate(b, {**CASE, "sugarPrice": p})["pricePerKgPha"] for p in (0.2, 0.3, 0.4, 0.5)]
    assert all(a < c for a, c in zip(prices, prices[1:]))


def test_no_sugar_left_for_respiration_is_refused_with_the_carbon_reason(pha):
    f, b = pha
    with pytest.raises(f.Infeasible) as e:
        f.evaluate(b, {**CASE, "yield": 0.45, "content": 0.4})
    assert e.value.reason == "carbon" and "no sugar for respiration" in str(e.value)


def test_a_whole_run_through_the_worker(store):
    from types import SimpleNamespace

    from openferment_core.models import ProformaRunRequest, InputAssumption

    def rec(rid, field, value, unit):
        return {"id": rid, "paperId": "P6", "field": field, "value": value, "unit": unit, "carbonSource": "glucose",
                "strainId": "c-necator-h16", "provenance": "unverified", "status": "unverified", "primary": True}

    rs = [rec(f"t{i}", "pha_titre", v, "g/L") for i, v in enumerate((30.0, 50.0, 70.0))]
    rs += [rec(f"y{i}", "pha_yield_substrate", v, "g g-1") for i, v in enumerate((0.25, 0.3, 0.35))]
    rs += [rec("c0", "pha_content_cdw", 70.0, "% CDW"), rec("c1", "pha_content_cdw", 80.0, "% CDW")]
    rs += [rec(f"p{i}", "pha_productivity", v, "g L-1 h-1") for i, v in enumerate((0.5, 1.0, 1.5))]
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    a = [InputAssumption(key=k, value=v, low=lo, high=hi, by="Sean Creighton", at="2026-10-15")
         for k, v, lo, hi in (("recovery", 0.95, 0.9, 0.98), ("sugarPrice", 0.4, 0.3, 0.5), ("sugarFeed", 10000, 10000, 10000))]
    out = proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", assumptions=a, seed=3), pool=pool)
    assert out.samples == 500 and out.feasible + sum(out.infeasible.values()) == 500
    assert set(out.infeasible) <= {"carbon", "oxygen", "balance"}
    assert out.provenance == "demo" and out.evidence.figure == "distribution"
    q = out.quantiles
    assert q["p5"] <= q["p25"] <= q["p50"] <= q["p75"] <= q["p95"]
    assert sum(b.count for b in out.histogram) == out.feasible
    assert sum(out.baseCostLines.values()) == pytest.approx(out.basePrice, rel=1e-12)
    assert {s.key for s in out.sensitivity} == {"titre", "yield", "content", "productivity", "recovery", "sugarPrice"}
    assert len(out.grid.msp) == 125
    again = proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", assumptions=a, seed=3), pool=pool)
    assert again.artifactId == out.artifactId and again.quantiles == out.quantiles
    assert artifacts.replay(out.artifactId).identical


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
