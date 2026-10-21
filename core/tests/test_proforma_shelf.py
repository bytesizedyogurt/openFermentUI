"""The shelf of flowsheets and the one artifact per run (OF-BLD-019 §2.1).

Offline: the shelf is data the service serves without BioSTEAM, it never
holds the toy, and a run stored before the tables still reads. Marked `sim`
(`pnpm test:sim`, the real worker): the toy flowsheet's run artifact carries
every table; the PHA draft's TEA breakdown is read from the TEA object and
its lines sum to the price; with Graphviz's `dot` on the path the diagram is
the SVG it drew. Every input value below is a PLACEHOLDER chosen to exercise
a flowsheet; none is a measurement and no price here is a result.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, intake, proforma
from openferment_core.flowsheets import KNOWN, shelf
from openferment_core.models import Artifact, BasisInput, BasisSource, InputAssumption, ProformaRunRequest

CORE = Path(__file__).resolve().parent.parent
FIXTURE_BY = "openFerment test fixture"


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def assume(key, value, low=None, high=None):
    return InputAssumption(key=key, value=value, low=value if low is None else low, high=value if high is None else high,
                           by=FIXTURE_BY, at="2026-10-20", note="PLACEHOLDER for a test")


# ── the shelf is data (offline) ────────────────────────────────────────


def test_the_shelf_and_the_service_read_it_without_biosteam():
    code = ("import sys; from openferment_core import proforma; from openferment_core.flowsheets import shelf; "
            "proforma.shelf(True); assert 'biosteam' not in sys.modules and 'thermosteam' not in sys.modules, "
            "sorted(m for m in sys.modules if 'steam' in m)")
    r = subprocess.run([sys.executable, "-c", code], cwd=CORE, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]


def test_the_shelf_holds_the_flowsheets_that_exist_and_never_the_toy():
    # OF-BLD-020 §6.1: a vessel and a train, priced (test_custom_train holds it).
    assert set(shelf.SHELF) == {"cornstover_benchmark", "corn_drygrind", "ethanol_glucose_v0", "pha_sugar_v0",
                                "custom_train_v1"}
    assert set(KNOWN) == {"cornstover_benchmark", "corn_drygrind", "ethanol_glucose_v0", "pha_sugar_v0",
                          "custom_train_v1", "toy"}
    for fid in KNOWN:
        assert (CORE / "openferment_core" / "flowsheets" / f"{fid}.py").is_file(), f"{fid} has no module"
    cs, pha = shelf.SHELF["cornstover_benchmark"], shelf.SHELF["pha_sugar_v0"]
    assert cs.reference and cs.program is None and cs.inputs == [] and cs.source.startswith("biorefineries ")
    assert cs.source.endswith(", cornstover")
    assert not pha.reference and pha.program == "pha" and pha.source == "this repository"
    with pytest.raises(shelf.NotOnShelf, match="STAND-IN for tests and is not on the shelf"):
        shelf.info("toy")
    with pytest.raises(shelf.NotOnShelf, match="there is no flowsheet nowhere"):
        shelf.info("nowhere")
    assert shelf.info("toy", allow_toy=True).id == "toy"


def test_the_pha_entry_is_the_binding_proforma_does():
    pha = shelf.SHELF["pha_sugar_v0"]
    by_key = {i.key: i for i in pha.inputs}
    assert list(by_key) == list(proforma.KEYS)
    for key, (label, unit, field_id, _canonical, _scale) in proforma.BOUND.items():
        assert by_key[key].fields == [field_id] and by_key[key].name == label and by_key[key].unit == unit
    for key, (label, unit) in proforma.ASSUMED.items():
        assert by_key[key].fields == [] and by_key[key].name == label and by_key[key].unit == unit
    assert pha.priceBasis == proforma.PRICE_BASIS and pha.leavesOut == proforma.LEAVES_OUT
    assert tuple(pha.gridInputs) == proforma.GRID_KEYS and pha.priceOutput == "pricePerKgPha"
    assert {i.kind for i in pha.inputs} == {"process", "economic"}


def test_every_program_on_the_shelf_is_a_program():
    from openferment_core import programs

    ids = {p.id for p in programs.programs()}
    for f in shelf.SHELF.values():
        assert f.program is None or f.program in ids, f"{f.id} names program {f.program}"


def test_the_shelf_endpoint_leaves_an_archived_program_out_unless_asked():
    from openferment_core import api

    c = TestClient(api.app, base_url="http://127.0.0.1")
    off = [f["id"] for f in c.get("/api/proforma/shelf").json()]
    on = c.get("/api/proforma/shelf?includeArchived=true").json()
    # PHA is archived (OF-BLD-016); the corn plant (§2.2), glucose to ethanol (§2.3) and a vessel and a train
    # (OF-BLD-020 §6.1) are the yeast program's.
    assert off == ["cornstover_benchmark", "corn_drygrind", "ethanol_glucose_v0", "custom_train_v1"]
    assert [f["id"] for f in on] == ["cornstover_benchmark", "corn_drygrind", "ethanol_glucose_v0", "pha_sugar_v0",
                                     "custom_train_v1"]
    assert all("toy" != f["id"] for f in on)
    pha = next(f for f in on if f["id"] == "pha_sugar_v0")
    assert set(pha) >= {"id", "title", "description", "source", "program", "reference", "inputs", "outputs",
                        "packageTest"}
    assert set(pha["inputs"][0]) == {"key", "name", "dimension", "unit", "fields", "kind", "note"}


def test_a_run_asks_for_a_sample_count_within_its_cap(store):
    assert ProformaRunRequest(scenarioId="sc-pha-1").samples == proforma.SAMPLES
    pool = SimpleNamespace(records=[], records_by_id={})
    for n in (0, proforma.MAX_SAMPLES + 1):
        with pytest.raises(proforma.ScenarioRefused, match=f"between 1 and {proforma.MAX_SAMPLES} samples"):
            proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", samples=n), pool=pool)


def test_run_flowsheet_refuses_the_toy_a_reference_and_what_waits(store):
    with pytest.raises(proforma.ScenarioRefused, match="not on the shelf"):
        proforma.run_flowsheet("toy", [assume("water", 100.0)])
    with pytest.raises(proforma.ScenarioRefused, match="reference biorefinery"):
        proforma.run_flowsheet("cornstover_benchmark", [])
    with pytest.raises(proforma.ScenarioRefused, match="wait for a source.*ethanol, split"):
        proforma.run_flowsheet("toy", [assume("water", 100.0)], allow_toy=True)
    with pytest.raises(proforma.ScenarioRefused, match="takes no input sugar"):
        proforma.run_flowsheet("toy", [assume("sugar", 1.0)], allow_toy=True)


def test_a_run_stored_before_the_tables_still_reads():
    inputs = [BasisInput(name="flowsheet", value="pha_sugar_v0", unit="", source=BasisSource(kind="convention"))]
    old = Artifact(id="0" * 16, tool=proforma.RUN, toolVersion="pha_sugar_v0 · biosteam 2.54.0 · biorefineries 2.35.1",
                   inputs=inputs, output={"quantiles": {}, "basePrice": None}, outputHash="", provenance="demo",
                   createdAt="2026-10-15T00:00:00Z", durationMs=0)
    t = proforma.tables_of(old)
    assert t.flowsheet == "pha_sugar_v0" and t.tea is None and t.streams == [] and t.units == [] and t.diagram is None


def test_the_stand_in_run_carries_every_table_and_says_it_is_the_stand_in(store, monkeypatch):
    # The double's fixture (demo.py --prototype) comes from this path: the real
    # binding and artifact code over the closed-form STAND-IN evaluator.
    from openferment_core import demo

    monkeypatch.setattr(proforma, "call", demo._standin_call)
    monkeypatch.setattr(proforma, "yield_cap", lambda: None)
    rs = demo._standin_records()
    a = [InputAssumption(key=k, value=v, low=lo, high=hi, by=FIXTURE_BY, at="2026-10-20")
         for k, v, lo, hi in (("recovery", 0.95, 0.9, 0.98), ("sugarPrice", 0.4, 0.3, 0.5), ("sugarFeed", 10000.0, 10000.0, 10000.0))]
    run = proforma.run(ProformaRunRequest(scenarioId="sc-pha-1", assumptions=a, samples=50),
                       pool=SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs}))
    assert run.samples == 50 and run.flowsheet == "pha_sugar_v0" and run.tablesSource == demo.PROFORMA_STANDIN
    assert [u.id for u in run.units] == run.unitOrder == ["R1", "C1", "D1"] and len(run.streams) == 6
    assert run.tea is not None and sum(line.perUnit for line in run.tea.lines) == pytest.approx(run.basePrice, rel=1e-12)
    assert run.utilities.heatingUnit == "GJ/hr" and run.tableUnits == shelf.TABLE_UNITS
    art = artifacts.get(run.artifactId)
    assert art.tool == proforma.RUN and art.toolVersion.startswith(proforma.RUN_VERSION)
    read = proforma.tables_of(art)
    assert all(getattr(read, k) == getattr(run, k) for k in type(read).model_fields)


# ── the real worker (sim) ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    return proforma


TOY = [assume("water", 100.0), assume("ethanol", 50.0), assume("split", 0.6)]
EVERY_KEY = {"flowsheet", "base", "basePrice", "baseCostLines", "baseInfeasible", "readBack", "quantiles", "histogram",
             "sensitivity", "samples", "feasible", "infeasible", "grid", "tablesSource", "tea", "streams", "units",
             "utilities", "diagram", "diagramNote", "unitOrder", "tableUnits"}


@pytest.mark.sim
def test_the_toy_run_artifact_carries_every_table(warm, store):
    import shutil

    art = proforma.run_flowsheet("toy", TOY, samples=8, seed=3, allow_toy=True)
    assert art.tool == proforma.RUN and art.provenance == "demo"  # every input a fixture's assumption
    assert set(art.output) == EVERY_KEY
    t = proforma.tables_of(art)
    assert t.flowsheet == "toy" and t.tablesSource.startswith("BioSTEAM ") and t.tea is None  # the toy prices nothing
    assert [u.id for u in t.units] == t.unitOrder == ["toy_M", "toy_S"]
    assert [u.unitClass for u in t.units] == ["Mixer", "Splitter"] and [u.order for u in t.units] == [0, 1]
    feeds = {s.id: s for s in t.streams if s.source is None}
    assert set(feeds) == {"toy_water", "toy_ethanol"} and feeds["toy_water"].massFlows == {"Water": pytest.approx(100.0)}
    top, bottom = [s for s in t.streams if s.source == "toy_S"]
    # Worked by hand in flowsheets/toy.py: the top carries the split share of each feed.
    assert top.massFlows == {"Water": pytest.approx(60.0), "Ethanol": pytest.approx(30.0)} and top.sink is None
    assert bottom.massFlow == pytest.approx(60.0) and top.T > 0 and top.P > 0 and top.phase == "l"
    assert t.utilities.heatingUnit == "GJ/hr" and t.utilities.electricityConsumptionUnit == "MW"
    assert t.tableUnits == shelf.TABLE_UNITS
    if shutil.which("dot") is None:
        # §2.R: the note is a fact about the host that made the run, and the
        # basis says the diagram was not drawn, so a host with dot draws its own.
        assert t.diagram is None and "Graphviz was not on the host that made this run" in t.diagramNote
        assert [i.value for i in art.inputs if i.name == "diagram"] == [proforma.DIAGRAM_NOT_DRAWN]
        # A basis that asks for the diagram, replayed where dot is absent, says so.
        asked = warm.call("run", {"flowsheet": "toy", "base": {}, "specs": {}, "samples": 0, "seed": 0, "diagram": True})
        assert asked["tables"]["diagram"] is None and "basis asks for the diagram" in asked["tables"]["diagramNote"]
    else:
        assert "<svg" in t.diagram
    assert art.output["samples"] == art.output["feasible"] == 8 and art.output["grid"] is None
    assert artifacts.replay(art.id).identical
    assert proforma.run_flowsheet("toy", TOY, samples=8, seed=3, allow_toy=True).id == art.id


@pytest.mark.sim
def test_the_worker_refuses_a_reference_case_by_case(warm):
    from openferment_core.workers import WorkerError

    with pytest.raises(WorkerError, match="reference biorefinery"):
        warm.call("evaluate", {"flowsheet": "cornstover_benchmark", "values": {}})


PHA = {"titre": 50.0, "yield": 0.3, "content": 0.7, "productivity": 1.0, "recovery": 0.95, "sugarPrice": 0.4,
       "sugarFeed": 10000.0}


@pytest.mark.sim
def test_the_pha_tea_breakdown_is_the_tea_objects_and_sums_to_the_price(warm):
    r = warm.call("run", {"flowsheet": "pha_sugar_v0", "base": PHA, "specs": {}, "samples": 0, "seed": 0})
    assert r["baseInfeasible"] is None and r["montecarlo"]["samples"] == [] and r["grid"] is None
    t, price = r["tables"], r["base"]["pricePerKgPha"]
    tea = t["tea"]
    assert tea["teaClass"] == "CellulosicEthanolTEA" and tea["product"] == "product" and tea["feedstock"] == "sugar"
    assert sum(line["perUnit"] for line in tea["lines"]) == pytest.approx(price, rel=1e-9)
    hours = tea["operatingHours"]
    assert tea["feedstockCost"] == pytest.approx(PHA["sugarPrice"] * PHA["sugarFeed"] * hours, rel=1e-9)
    assert tea["materialCost"] == pytest.approx(tea["feedstockCost"] + tea["otherMaterialCost"], rel=1e-12)
    assert tea["basisFlow"] == pytest.approx(PHA["sugarFeed"] * PHA["yield"] * PHA["recovery"], rel=1e-6)
    assert tea["sales"] - tea["coproductCredits"] == pytest.approx(price * tea["basisFlow"] * hours, rel=1e-9)
    assert tea["FCI"] >= tea["installedEquipmentCost"] > 0 and tea["laborCost"] > 0 and tea["IRR"] is not None
    assert [u["id"] for u in t["units"]] == ["M1", "R1", "C1", "D1"] and t["units"][1]["unitClass"] == "AeratedBioreactor"
    assert t["units"][1]["coolingDuty"] > 0 and t["units"][1]["power"] > 0 and t["units"][0]["heatingDuty"] is None
    assert sum(u["installedCost"] for u in t["units"]) == pytest.approx(tea["installedEquipmentCost"], rel=1e-9)
    ids = [s["id"] for s in t["streams"]]
    assert len(ids) == len(set(ids)) and {"sugar", "broth", "product"} <= set(ids)
    assert t["utilities"]["cooling"] > 0 and t["utilities"]["coolingUnit"] == "GJ/hr"


@pytest.mark.sim
def test_with_dot_on_the_path_the_diagram_is_the_svg_it_drew(tmp_path, monkeypatch):
    # A STAND-IN `dot` that reads the graph and answers fixed SVG, first on
    # the path of a worker of its own: the branch every host with Graphviz
    # takes, run where Graphviz may be absent.
    from openferment_core.workers import SimWorker

    fake = tmp_path / "bin"
    fake.mkdir()
    dot = fake / "dot"
    dot.write_text("#!/bin/sh\ncat > /dev/null\nprintf '<svg xmlns=\"http://www.w3.org/2000/svg\"><title>stand-in dot</title></svg>'\n")
    dot.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ.get('PATH', '')}")
    w = SimWorker("openferment_core.workers.proforma_worker", timeout_s=proforma.START_TIMEOUT_S)
    try:
        r = w.call("run", {"flowsheet": "toy", "base": {}, "specs": {}, "samples": 0, "seed": 0})
        not_drawn = w.call("run", {"flowsheet": "toy", "base": {}, "specs": {}, "samples": 0, "seed": 0, "diagram": False})
    finally:
        w.close()
    assert r["tables"]["diagram"] == '<svg xmlns="http://www.w3.org/2000/svg"><title>stand-in dot</title></svg>'
    assert r["tables"]["diagramNote"] is None
    # §2.R: a run whose basis says it was made where dot was absent is not drawn here either: its replay is that run.
    assert not_drawn["tables"]["diagram"] is None and "not on the host that made this run" in not_drawn["tables"]["diagramNote"]
