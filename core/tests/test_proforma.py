"""Proforma on the service's side (OF-BLD-014 §8.2–§8.3), with no simulator."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import intake, proforma


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def test_the_retired_reference_entries_leave_no_route_and_no_shelf_entry(store):
    # alpha 2.2 D8: the shelf's hand-written entries cornstover_benchmark and
    # corn_drygrind retired; the library shelf's cornstover and corn run the
    # same packages' plants, and the reference screen reads them.
    from openferment_core import api
    from openferment_core.engine import library
    from openferment_core.flowsheets import KNOWN, shelf

    c = TestClient(api.app, base_url="http://127.0.0.1")
    before = proforma.status()["status"]
    for path in ("/api/proforma/benchmark", "/api/proforma/reference/cornstover_benchmark",
                 "/api/proforma/reference/corn_drygrind"):
        assert c.get(path).status_code == 404 and c.post(path).status_code in (404, 405), path
    assert proforma.status()["status"] == before
    assert not {"cornstover_benchmark", "corn_drygrind"} & {*shelf.SHELF, *KNOWN}
    assert [f["id"] for f in c.get("/api/proforma/shelf").json()] == ["ethanol_glucose_v0", "custom_train_v1"]
    # The plants each retired entry built are the library shelf's.
    plants = {p.id: p for p in library.shelf().plants}
    assert {proforma.RETIRED_PLANTS[e] for e in ("cornstover_benchmark", "corn_drygrind")} <= set(plants)
    assert all(plants[p].kind == "plant" and f"test_{p}" in plants[p].tests for p in proforma.RETIRED_PLANTS.values())


# ── binding (§8.3) ─────────────────────────────────────────────────────
# Every record here is a FIXTURE written in the test; none is a measurement.

from types import SimpleNamespace  # noqa: E402

from openferment_core.models import InputAssumption, ProformaRunRequest  # noqa: E402
from standins import assumed_inputs


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
                                        inputs=assumed_inputs([assume("plant_scale", 1000, 1000, 1000)])), pool=pool)
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


# ── the package's own test, read from its file (OF-BLD-019 §2.2; ADR-013) ──

from openferment_core.flowsheets import shelf as _shelf  # noqa: E402

# The eleven values biorefineries 2.35.1's own test asserts for the corn
# plant, RESTATED here from biorefineries/tests/test_biorefineries.py,
# test_corn (rtol 5e-2 each), only to hold the parser that reads that file
# to it. The file is the authority: the service and the screens read the
# values from it through `shelf.regression_of` (engine/library.regression).
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


def test_the_package_test_values_are_read_from_the_installed_file():
    from openferment_core.engine import library

    reg = library.regression("corn", None)
    assert reg is not None, "biorefineries is not installed here, or its test file moved"
    assert (reg.file, reg.test) == ("biorefineries/tests/test_biorefineries.py", "test_corn")
    assert reg == _shelf.regression_of(library.TEST_FILE, "test_corn")
    assert reg.package.startswith("biorefineries ")
    assert [(v.expression, v.package) for v in reg.values] == TEST_CORN
    assert {v.rtol for v in reg.values} == {0.05}
    assert all(v.label != v.expression and v.unit is not None for v in reg.values)
    assert [v.expression for v in library.regression("cornstover", None).values] == [e for e, _ in TEST_CORN]
    assert _shelf.regression_of(library.TEST_FILE, "test_nowhere") is None
    assert _shelf.regression_of("biorefineries/tests/no_such_file.py", "test_corn") is None


def test_a_check_holds_as_numpy_allclose_holds_it():
    from openferment_core.models import PackageRegression, RegressionValue

    reg = PackageRegression(package="p", file="f", test="t", values=[
        RegressionValue(expression="a", label="a", unit="", package=100.0, rtol=0.05),
        RegressionValue(expression="b", label="b", unit="", package=0.0, rtol=0.05),
        RegressionValue(expression="c", label="c", unit="", package=1.0, rtol=0.05),
    ])
    from openferment_core.engine import library

    a, b, c = library.checks(reg, {"a": 104.9, "b": 1e-9})
    assert a.within and a.relDiff == pytest.approx(0.049)
    assert b.within and b.relDiff is None  # zero asserted: |measured| within numpy's absolute tolerance
    assert not c.within and c.measured is None
    [d] = library.checks(reg.model_copy(update={"values": reg.values[:1]}), {"a": 105.1})
    assert not d.within


# ── runs kept from the retired reference entries replay (alpha 2.2 D8) ──
# proforma.reference and proforma_benchmark stay registered, so an artifact a
# person kept replays from its stored basis through the code that computed
# it (workers/kept_references.py); no route or tool makes a new one.


def kept_reference_basis(entry: str, digits: int = proforma.REFERENCE_DIGITS) -> list:
    """A basis as a reference run of a retired entry kept it: the package's
    plant, the simulator, the digits it keeps and whether it was drawn."""
    from openferment_core.models import BasisInput, BasisSource

    package = {"corn_drygrind": "biorefineries.corn", "cornstover_benchmark": "biorefineries.cornstover"}[entry]
    return [
        BasisInput(name="flowsheet", value=entry, unit="", source=BasisSource(
            kind="model", id=f"{package}@{proforma._installed('biorefineries')}", note="every setting the package's own")),
        BasisInput(name="simulator", value=f"biosteam {proforma._installed('biosteam')}", unit="", source=BasisSource(
            kind="model", id=f"biosteam@{proforma._installed('biosteam')}", note="the process simulator the package runs on")),
        BasisInput(name="precision", value=f"{digits} significant digits", unit="", source=BasisSource(
            kind="convention", note="every number the run keeps is rounded so")),
        BasisInput(name="diagram", value=proforma.DIAGRAM_NOT_DRAWN, unit="", source=BasisSource(kind="convention")),
    ]


def head_basis(entry: str | None = None) -> list:
    """A basis exactly as fd17f32 wrote it before the shelf's reference
    entries retired (tests/fixtures/kept_bases.json): a reference run of
    `entry`, or the benchmark when no entry is named. Every input names the
    package, the simulator or a stated convention."""
    import json
    from pathlib import Path

    from openferment_core.models import BasisInput

    kept = json.loads((Path(__file__).parent / "fixtures" / "kept_bases.json").read_text(encoding="utf-8"))
    rows = kept["benchmark"] if entry is None else kept["reference"][entry]
    return [BasisInput.model_validate(r) for r in rows]


def kept_benchmark_basis() -> list:
    """A basis as the benchmark kept it: the package's plant and the simulator."""
    from openferment_core.models import BasisInput, BasisSource

    ref = f"biorefineries.cornstover@{proforma._installed('biorefineries')}"
    return [
        BasisInput(name="model", value="biorefineries.cornstover.Biorefinery", unit="", source=BasisSource(
            kind="model", id=ref, note="the corn stover ethanol biorefinery, with every setting the package's own")),
        BasisInput(name="simulator", value=f"biosteam {proforma._installed('biosteam')}", unit="", source=BasisSource(
            kind="model", id=f"biosteam@{proforma._installed('biosteam')}", note="the process simulator the package runs on")),
    ]


def test_a_kept_reference_run_replays_through_its_registered_tool(store, monkeypatch):
    # The stand-in answers for the worker's replay op; everything else is the
    # real code: the registration, the artifact store, the package test read
    # from the installed file as the library plant's.
    from openferment_core import artifacts
    import standins

    monkeypatch.setattr(proforma, "call", standins._standin_call)
    reg = artifacts.registered(proforma.REFERENCE)
    assert reg.version.startswith(proforma.REFERENCE_VERSION + " · biosteam ")
    art = artifacts.compute(proforma.REFERENCE, kept_reference_basis("corn_drygrind"))
    o = art.output
    assert art.provenance == "computed" and o["regression"]["test"] == "test_corn"
    assert [c["expression"] for c in o["checks"]] == [e for e, _ in TEST_CORN]
    t = proforma.tables_of(art)  # a kept reference run reads as any run's tables
    assert t.flowsheet == "corn_drygrind" and t.tablesSource == standins.PROFORMA_STANDIN and t.units and t.streams
    assert artifacts.replay(art.id).identical
    # The library plant's test holds a kept corn stover run as it held it.
    stover = artifacts.compute(proforma.REFERENCE, kept_reference_basis("cornstover_benchmark"))
    assert stover.output["regression"]["test"] == "test_cornstover"
    # A kept run's SFF file is the library plant's run to write, said in words.
    with pytest.raises(proforma.ScenarioRefused, match="the library plant corn's to write"):
        proforma.plant_of(art)


def test_a_kept_benchmark_replays_through_its_registered_tool(store, monkeypatch):
    from openferment_core import artifacts

    said = []

    def worker(op, args):
        said.append(op)
        return {"package": "STAND-IN", "mespUsdPerKg": 1.0, "references": []}

    monkeypatch.setattr(proforma, "call", worker)
    assert artifacts.registered(proforma.BENCHMARK).version.startswith("biorefineries.cornstover@")
    art = artifacts.compute(proforma.BENCHMARK, kept_benchmark_basis())
    assert artifacts.replay(art.id).identical and said == ["replay_benchmark", "replay_benchmark"]
    with pytest.raises(proforma.ScenarioRefused, match="the library plant cornstover's to write"):
        proforma.plant_of(art)


@pytest.mark.sim
def test_a_kept_corn_reference_run_replays_in_the_worker(store):
    # Marked sim: the real worker builds the package's plant through the code
    # the retired entry ran (about a second once BioSTEAM is loaded), on the
    # basis fd17f32 wrote for it, holds it to the package's own test, and a
    # replay builds it afresh to the same output; the worker puts back what
    # it held.
    from openferment_core import artifacts

    proforma.start(background=False)
    before = proforma.call(*ETHANOL_RUN)
    art = artifacts.compute(proforma.REFERENCE, head_basis("corn_drygrind"))
    o = art.output
    assert all(c["within"] for c in o["checks"]) and len(o["checks"]) == len(TEST_CORN)
    assert set(o["measured"]) == set(_shelf.TEST_QUANTITIES) and o["simulator"].startswith("biosteam ")
    assert {"ethanolPriceUsdPerKg", "IRR", "ethanolKgPerH", "cornKgPerH", "references"} <= set(o)
    assert all(isinstance(v, float) for k, v in o["readBack"].items() if k != "depreciation") and o["readBack"]
    t = proforma.tables_of(art)
    assert t.tea.product == "ethanol" and t.tea.feedstock == "corn" and t.tea.teaClass == "ConventionalEthanolTEA"
    assert "SimultaneousSaccharificationFermentation" in {u.unitClass for u in t.units}
    assert sum(line.perUnit for line in t.tea.lines) == pytest.approx(o["ethanolPriceUsdPerKg"], rel=1e-8)
    # The units the package test's duties are stated in are BioSTEAM's own.
    assert _shelf.TEST_QUANTITIES["units.get_heating_duty()"][1] == t.utilities.heatingUnit
    assert _shelf.TEST_QUANTITIES["units.get_electricity_consumption()"][1] == t.utilities.electricityConsumptionUnit
    assert artifacts.replay(art.id).identical
    after = proforma.call(*ETHANOL_RUN)
    assert after["base"] == before["base"] and after["tables"]["tea"] == before["tables"]["tea"]


@pytest.mark.sim
def test_a_kept_corn_stover_reference_run_and_a_kept_benchmark_replay_in_the_worker(store):
    # Marked sim: the corn stover plant built twice for each of a reference
    # run and the benchmark, on the bases fd17f32 wrote, through
    # workers/kept_references.py's Cornstover and benchmark(). The reference
    # run's facilities are built from a set, so the order of its streams and
    # units, and the names BioSTEAM gives unnamed streams, may move from one
    # build to the next; its numbers hold. The benchmark's price is held to
    # the last digits, as the removed slow test held it.
    from openferment_core import artifacts

    proforma.start(background=False)
    stover = artifacts.compute(proforma.REFERENCE, head_basis("cornstover_benchmark"))
    o = stover.output
    assert stover.provenance == "computed" and o["regression"]["test"] == "test_cornstover"
    assert o["tea"]["product"] == "ethanol" and o["units"] and o["streams"]
    # ADR-013: the package's own test_cornstover fails two of its values on these pins, and the run says so.
    assert {c["expression"] for c in o["checks"] if not c["within"]} == {"tea.installed_equipment_cost",
                                                                        "units.get_electricity_consumption()"}
    replay = artifacts.replay(stover.id)
    moved = {d.path.split("[")[0].split(".")[0] for d in replay.differences}
    assert replay.identical or moved <= {"streams", "units", "unitOrder", "…"}, moved
    bench = artifacts.compute(proforma.BENCHMARK, head_basis())
    assert bench.provenance == "computed" and {i.source.kind for i in bench.inputs} == {"model"}
    assert bench.output["mespUsdPerGal"] == pytest.approx(o["mespUsdPerGal"], rel=1e-9), "one plant, one price"
    assert bench.output["package"] == o["package"] and set(bench.output["settings"]) == set(o["settings"])
    replays_to_the_last_digits(bench.id)


# ── glucose to ethanol through the real worker (OF-BLD-019 §2.3; `sim`) ──
# Every input is a STAND-IN typed here as a fixture's assumption, so the run
# is `assumed`; none is a measurement and no price here is a result.

ETHANOL_STANDIN = {"feed_glucose_conc": 100.0, "titre": 45.0, "yield": 0.45, "productivity": 2.0,
                   "plant_scale": 100000.0, "glucose_price": 0.4}


def replays_to_the_last_digits(artifact_id: str, rel: float = 1e-9) -> None:
    """A run of the ethanol flowsheet replays identically, as the biosteam
    engine's scenario flowsheets state (rtol 0, atol 0; proforma.thing_list):
    measured 2026-11-03 over five replays, with a sampled range and other runs
    between them. The helper names any difference it meets, each a number
    within `rel`, as it held one ulp of the price in some cases on
    2026-10-20, so a host whose solvers carry noise in the last digits says
    so in the difference's words."""
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
# next op in the same worker priced (the corn stover plant left its utility
# prices and cost index behind; the corn plant's chemicals lock ammonia to
# liquid in objects the corn stover plant shares; BioSTEAM's stream tickets
# ran on from whatever was built first). The two plants run here as the
# library shelf runs them (alpha 2.2 D8), on their package's own values.
# Each op is held to what a worker started for it alone gives: the ethanol
# flowsheet within the replay tolerance the tests use
# (`replays_to_the_last_digits`), a library run within the precision its
# basis states (engine/library.py `tolerance`).

ETHANOL_RUN = ("run", {"flowsheet": "ethanol_glucose_v0", "base": ETHANOL_STANDIN, "specs": {}, "samples": 0, "seed": 0})
STOVER_RUN = ("library_run", {"plant": "cornstover", "configuration": None, "overrides": {}, "digits": 10})
CORN_RUN = ("library_run", {"plant": "corn", "configuration": None, "overrides": {}, "digits": 10})


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
        ordered = ex.submit(in_a_worker_of_its_own, [ETHANOL_RUN, STOVER_RUN, CORN_RUN, ETHANOL_RUN, STOVER_RUN])
        stover_first = ex.submit(in_a_worker_of_its_own, [STOVER_RUN, ETHANOL_RUN])
        corn_first = ex.submit(in_a_worker_of_its_own, [CORN_RUN, STOVER_RUN, ETHANOL_RUN])
        ethanol, stover, corn, ethanol_again, stover_again = ordered.result()
        fresh_stover, ethanol_built_last = stover_first.result()
        fresh_corn, stover_after_corn, ethanol_after_corn = corn_first.result()
    tol = {"rel": 1e-9, "abs": 1e-12}
    # A library run keeps ten significant digits: one unit in the last of them, and the package test's atol.
    held = {"rel": 1e-9, "abs": 1e-8}
    price = lambda r: r["base"]["pricePerKgEthanol"]  # noqa: E731
    solved = lambda r: r["price"]["solvedPrice"]  # noqa: E731
    seen = {"corn stover after ethanol": solved(stover), "corn stover first": solved(fresh_stover),
            "corn stover after the corn plant": solved(stover_again),
            "corn stover after the corn plant first": solved(stover_after_corn),
            "ethanol first": price(ethanol), "ethanol after corn stover and corn": price(ethanol_again),
            "ethanol built after corn stover": price(ethanol_built_last)}
    # The corn stover plant, after the ethanol flowsheet built corn's
    # chemicals, and again after the corn plant ran, gives what a worker that
    # ran nothing before gives (finding 10; the corn plant's run reached it
    # through the chemicals its package shares with the corn stover plant's).
    for later in (stover, stover_again, stover_after_corn):
        assert solved(later) == pytest.approx(solved(fresh_stover), **held), seen
        for expression, value in fresh_stover["measured"].items():
            assert later["measured"][expression] == pytest.approx(value, **held), expression
    # So does the corn plant, after the ethanol flowsheet and the corn stover plant.
    for key in ("solvedPrice", "packagePrice", "IRR", "feedstockKgPerH"):
        assert corn["price"][key] == pytest.approx(fresh_corn["price"][key], **held), key
    for expression, value in fresh_corn["measured"].items():
        assert corn["measured"][expression] == pytest.approx(value, **held), expression
    # The ethanol flowsheet prices as it did first, once the two plants ran
    # (finding 0), and when built after the corn stover plant alone; its
    # utility and capital lines with it.
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
