"""pureOS reads the train, unit by unit, from the run Proforma priced
(OF-BLD-019 §4.1, D1).

Every train here is read by `pureos.train_of` from a `proforma.run`
artifact's stream and unit tables. The tables are written by hand for the
test, a line whose mass balance can be checked on paper: a reactor that
forms the product, a centrifuge that loses some of it to a centrate a
wastewater unit takes off the path, and a dryer that sends a recycle back
to the centrifuge. Nothing here starts BioSTEAM, reads a key or the network.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import intake, module_stores, pureos, tools
from openferment_core.models import Artifact, BasisInput, BasisSource
from test_module_tools import ctx_for, read
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)

PROTOTYPE = Path(__file__).parent / "fixtures" / "prototype"
LINE = "aaaaaaaaaaaaaaa1"


def _stream(sid, source, sink, flows):
    return {"id": sid, "source": source, "sink": sink, "phase": "l", "T": 300.0, "P": 101325.0,
            "massFlow": sum(flows.values()), "massFlows": flows, "price": None}


def _unit(uid, order, ins, outs, cls="Unit"):
    return {"id": uid, "unitClass": cls, "line": None, "order": order, "ins": ins, "outs": outs,
            "installedCost": 1.0, "purchaseCost": 1.0, "heatingDuty": None, "coolingDuty": None, "power": None}


def _tea(product="product", basis_flow=45.0):
    return {"teaClass": "TEA", "product": product, "feedstock": "feed", "productPrice": 1.0, "basisFlow": basis_flow,
            "basis": "kg of E", "operatingHours": 8000.0, "sales": 1.0, "materialCost": 1.0, "feedstockCost": 1.0,
            "otherMaterialCost": 0.0, "utilityCost": 1.0, "purchaseCost": 1.0, "installedEquipmentCost": 1.0,
            "FCI": 1.0, "TCI": 1.0, "FOC": 1.0, "laborCost": None, "capitalRecovery": 1.0, "coproductCredits": 0.0,
            "IRR": None, "incomeTax": None, "lines": []}


# R forms E; C splits the broth and the recycle into a cake and a centrate;
# D dries the cake into the product and sends a recycle back to C; W, off
# the path, takes the centrate to waste. E balance: C 50 + 2 in, 47 + 5 out;
# D 47 in, 2 + 45 out.
STREAMS = [
    _stream("feed", None, "R", {"Glucose": 100.0}),
    _stream("broth", "R", "C", {"E": 50.0, "Water": 50.0}),
    _stream("centrate", "C", "W", {"E": 5.0, "Water": 40.0}),
    _stream("cake", "C", "D", {"E": 47.0, "Water": 15.0}),
    _stream("recycle", "D", "C", {"E": 2.0, "Water": 5.0}),
    _stream("product", "D", None, {"E": 45.0, "Water": 10.0}),
    _stream("waste", "W", None, {"E": 5.0, "Water": 40.0}),
]
UNITS = [_unit("R", 0, ["feed"], ["broth"]), _unit("C", 1, ["broth", "recycle"], ["centrate", "cake"], "SolidsCentrifuge"),
         _unit("D", 2, ["cake"], ["recycle", "product"]), _unit("W", 3, ["centrate"], ["waste"])]


def _art(aid=LINE, *, streams=STREAMS, units=UNITS, tea=None, flowsheet="test_line", created="2026-10-20T10:00:00Z",
         inputs=None, tool="proforma.run", tables=True) -> Artifact:
    out = {"flowsheet": flowsheet, "basePrice": None}
    if tables:
        out.update({"tablesSource": "tables written for this test", "tea": tea if tea is not None else _tea(),
                    "streams": streams, "units": units, "utilities": None, "diagram": None, "diagramNote": None,
                    "unitOrder": [u["id"] for u in units], "tableUnits": {"massFlow": "kg/hr"}})
    return Artifact(id=aid, tool=tool, toolVersion="test", output=out, outputHash="0" * 64, provenance="computed",
                    createdAt=created, durationMs=0,
                    inputs=inputs or [BasisInput(name="flowsheet", value=flowsheet, unit="",
                                                 source=BasisSource(kind="convention"))])


def _by(tr):
    return {u.id: u for u in tr.units}


# ── what a unit passes on ────────────────────────────────────────────────


def test_recovery_counts_the_outlets_that_lead_on_never_outlets_over_inlets():
    tr = pureos.train_of(_art(), scenarios=[])
    u = _by(tr)
    c = u["C"]
    # Mass is conserved in a unit that reacts nothing: outlets over inlets is one.
    assert c.productOut == pytest.approx(c.productIn) == pytest.approx(52.0)
    assert c.recovery == pytest.approx(47.0 / 52.0)
    assert (c.productOnward, c.productLost, c.lostTo) == (pytest.approx(47.0), pytest.approx(5.0), ["centrate"])
    # The dryer's recycle runs back to the centrifuge, which leads on: not a loss.
    assert u["D"].recovery == pytest.approx(1.0) and u["D"].lostTo == []
    assert (tr.product, tr.productStream, tr.productOut, tr.productLost) == ("E", "product", 45.0, 5.0)
    assert tr.overallRecovery == pytest.approx(45.0 / 50.0)


def test_a_unit_no_product_enters_says_so_and_divides_nothing():
    u = _by(pureos.train_of(_art(), scenarios=[]))
    assert u["R"].recovery is None and u["R"].productIn == 0.0
    assert u["R"].note == "no E enters R: the product is formed here"
    empty = pureos.train_of(_art(streams=STREAMS + [_stream("air", None, "X", {"N2": 1.0}), _stream("vent", "X", "C", {"N2": 1.0})],
                                 units=UNITS + [_unit("X", 4, ["air"], ["vent"])]), scenarios=[])
    assert _by(empty)["X"].recovery is None and _by(empty)["X"].note == "no E enters or leaves X"


def test_cumulative_falls_by_each_loss_and_ends_at_the_overall_recovery():
    tr = pureos.train_of(_art(), scenarios=[])
    on = [u for u in tr.units if u.onPath]
    assert [u.id for u in on] == ["R", "C", "D"]
    assert [round(u.cumulative, 6) for u in on] == [1.0, 0.9, 0.9]
    assert all(a.cumulative >= b.cumulative for a, b in zip(on, on[1:]))
    assert on[-1].cumulative == pytest.approx(tr.overallRecovery)


def test_a_unit_off_the_path_is_named_and_carries_no_recovery():
    w = _by(pureos.train_of(_art(), scenarios=[]))["W"]
    assert not w.onPath and w.recovery is None and w.cumulative is None and w.productLost is None
    assert w.productIn == 5.0 and "off the product's path" in w.note


def test_masses_in_and_out_are_every_component_summed():
    c = _by(pureos.train_of(_art(), scenarios=[]))["C"]
    assert c.massIn == pytest.approx(100.0 + 7.0) and c.massOut == pytest.approx(45.0 + 62.0)


# ── what the product is ─────────────────────────────────────────────────


def test_the_product_is_the_component_the_price_is_per_else_the_largest():
    tr = pureos.train_of(_art(), scenarios=[])
    assert tr.product == "E" and "the component the run's price is per" in tr.productBasis
    whole = pureos.train_of(_art(tea=_tea(basis_flow=55.0)), scenarios=[])
    assert whole.product == "E" and "the largest component of product" in whole.productBasis
    unstated = pureos.train_of(_art(tea=_tea(basis_flow=None)), scenarios=[])
    assert unstated.product == "E"


def test_a_run_with_no_tea_names_no_product_and_reads_no_recovery():
    out = _art()
    out.output["tea"] = None
    tr = pureos.train_of(out, scenarios=[])
    assert tr.product is None and tr.overallRecovery is None and "no TEA" in tr.productBasis
    assert len(tr.units) == 4 and all(u.recovery is None and u.productIn is None for u in tr.units)


def test_a_priced_stream_missing_from_the_table_is_said():
    tr = pureos.train_of(_art(tea=_tea(product="gone")), scenarios=[])
    assert tr.product is None and "holds no such stream" in tr.productBasis and tr.overallRecovery is None


def test_a_run_kept_before_runs_carried_tables_says_how_to_get_them():
    tr = pureos.train_of(_art(tables=False), scenarios=[])
    assert tr.units == [] and tr.streams == [] and "run the scenario again" in tr.note


# ── which scenario, which program ───────────────────────────────────────

SCENARIOS = [
    {"id": "sc-a", "name": "A", "kind": "biosteam", "modelId": "test_line", "program": None},
    {"id": "sc-x", "name": "X", "kind": "authored", "modelId": "test_line", "program": None},
    {"id": "sc-p", "name": "P", "kind": "biosteam", "modelId": "pha_sugar_v0", "program": "pha"},
]


def test_a_run_belongs_to_the_one_seed_scenario_of_its_flowsheet_or_to_its_own_scenario_input():
    assert pureos.scenario_of(_art(), SCENARIOS) == ("sc-a", "A")
    named = _art(inputs=[BasisInput(name="scenario", value="sc-mine", unit="", source=BasisSource(kind="convention"))])
    assert pureos.scenario_of(named, SCENARIOS) == ("sc-mine", None)
    two = SCENARIOS + [{"id": "sc-b", "name": "B", "kind": "biosteam", "modelId": "test_line"}]
    assert pureos.scenario_of(_art(), two) == (None, None)


def test_trains_keep_the_newest_run_of_each_scenario_and_hide_an_archived_program():
    old, new = _art("aaaaaaaaaaaaaaa1", created="2026-10-01T00:00:00Z"), _art("aaaaaaaaaaaaaaa2", created="2026-10-02T00:00:00Z")
    pha = _art("aaaaaaaaaaaaaaa3", flowsheet="pha_sugar_v0", created="2026-09-01T00:00:00Z")
    other = _art("aaaaaaaaaaaaaaa4", tool="kinetic_fit")
    every = pureos.trains(True, arts=[old, pha, new, other], scenarios=SCENARIOS)
    assert [(t.scenarioId, t.artifactId, t.runs) for t in every] == [("sc-a", new.id, 2), ("sc-p", pha.id, 1)]
    assert every[1].program == "pha"
    shown = pureos.trains(False, arts=[old, pha, new, other], scenarios=SCENARIOS)
    assert [t.scenarioId for t in shown] == ["sc-a"]


def test_a_train_opens_by_scenario_or_by_run_and_refuses_anything_else_in_words():
    old, new = _art("aaaaaaaaaaaaaaa1", created="2026-10-01T00:00:00Z"), _art("aaaaaaaaaaaaaaa2", created="2026-10-02T00:00:00Z")
    fit = _art("aaaaaaaaaaaaaaa4", tool="kinetic_fit")
    arts = [old, new, fit]
    assert pureos.train("sc-a", arts=arts, scenarios=SCENARIOS).artifactId == new.id
    assert pureos.train(old.id, arts=arts, scenarios=SCENARIOS).artifactId == old.id
    with pytest.raises(pureos.TrainNotFound, match="kinetic_fit artifact, not a Proforma run"):
        pureos.train(fit.id, arts=arts, scenarios=SCENARIOS)
    with pytest.raises(pureos.TrainNotFound, match="no Proforma run of sc-none is on file here: run the scenario in Proforma"):
        pureos.train("sc-none", arts=arts, scenarios=SCENARIOS)


# ── the endpoints ────────────────────────────────────────────────────────


@pytest.fixture()
def stored(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    folder = tmp_path / "artifacts"
    folder.mkdir()
    kept = json.loads((PROTOTYPE / "artifacts.json").read_text(encoding="utf-8"))["response"]
    run = next(a for a in kept if a["tool"] == "proforma.run")
    for a in (_art(), Artifact.model_validate(run)):
        (folder / f"{a.id}.json").write_text(a.model_dump_json(), encoding="utf-8")
    return run


def _client():
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


def test_get_trains_lists_one_a_scenario_and_takes_the_switch_from_the_request(stored):
    c = _client()
    off = c.get("/api/pureos/trains").json()
    on = c.get("/api/pureos/trains?includeArchived=true").json()
    assert [t["artifactId"] for t in off] == [LINE], "the PHA run is hidden with the switch off"
    assert {t["artifactId"] for t in on} == {LINE, stored["id"]}
    pha = next(t for t in on if t["artifactId"] == stored["id"])
    assert (pha["scenarioId"], pha["program"], pha["product"], pha["unitCount"]) == ("sc-pha-1", "pha", "PHB", 3)
    assert pha["overallRecovery"] == pytest.approx(0.95)


def test_get_train_reads_by_scenario_or_run_and_404s_in_words(stored):
    c = _client()
    by_scenario = c.get("/api/pureos/train/sc-pha-1").json()
    assert by_scenario["artifactId"] == stored["id"] and [u["id"] for u in by_scenario["units"]] == ["R1", "C1", "D1"]
    assert c.get(f"/api/pureos/train/{LINE}").json()["overallRecovery"] == pytest.approx(0.9)
    missing = c.get("/api/pureos/train/sc-nothing")
    assert missing.status_code == 404 and "run the scenario in Proforma" in missing.json()["detail"]


def test_the_double_serves_what_the_code_reads_from_the_same_run():
    """The double's train is the one the real code reads from the run
    artifacts.json carries (test_demo holds the files to demo.py)."""
    kept = json.loads((PROTOTYPE / "artifacts.json").read_text(encoding="utf-8"))["response"]
    run = Artifact.model_validate(next(a for a in kept if a["tool"] == "proforma.run"))
    served = json.loads((PROTOTYPE / "pureos-train.json").read_text(encoding="utf-8"))["response"]
    assert pureos.train_of(run).model_dump(mode="json") == served


# ── pureos_read: trains and their units, by id ───────────────────────────


def test_pureos_read_finds_a_train_and_its_units_by_scenario_or_by_run(pool):  # noqa: F811
    kept = json.loads((PROTOTYPE / "artifacts.json").read_text(encoding="utf-8"))["response"]
    run = Artifact.model_validate(next(a for a in kept if a["tool"] == "proforma.run"))
    ctx = ctx_for(pool, artifacts=lambda: [run])
    got = read("pureos", ctx, ids=["sc-pha-1"])
    assert [(r.kind, r.id) for r in got.rows] == [("train", "sc-pha-1"), ("train-unit", "sc-pha-1:R1"),
                                                  ("train-unit", "sc-pha-1:C1"), ("train-unit", "sc-pha-1:D1")]
    train, c1 = got.rows[0], got.rows[2]
    assert train.ref == "pureos/train/sc-pha-1" and train.provenance == "demo"
    assert train.detail["artifactId"] == run.id and train.detail["overallRecovery"] == pytest.approx(0.95)
    assert c1.detail["recovery"] == pytest.approx(0.95) and c1.detail["lostTo"] == ["spent_medium"]
    by_run = read("pureos", ctx, ids=[run.id], kind="train-unit")
    assert [r.id for r in by_run.rows] == ["sc-pha-1:R1", "sc-pha-1:C1", "sc-pha-1:D1"]
    assert read("pureos", ctx, kind="train").summary["count"] == 1


def test_an_archived_train_is_hidden_and_a_read_by_its_id_says_whose(pool):  # noqa: F811
    kept = json.loads((PROTOTYPE / "artifacts.json").read_text(encoding="utf-8"))["response"]
    run = Artifact.model_validate(next(a for a in kept if a["tool"] == "proforma.run"))
    ctx = ctx_for(pool, include_archived=False, artifacts=lambda: [run])
    got = read("pureos", ctx, ids=["sc-pha-1"])
    assert got.rows == [] and "PHA" in got.summary["hidden"]


def test_the_kinds_name_trains_and_the_registry_stays_closed():
    assert module_stores.KINDS["pureos"] == ("unit-operation", "train", "train-unit")
    assert len(tools.WHITELIST) == 29, "a train is a kind of pureos_read, never a thirtieth tool"
    described = next(t for t in tools.infos() if t.name == "pureos_read").description
    assert "train-unit" in described and "artifact id" in described


# ── the vocabulary names BioSTEAM's own classes ─────────────────────────


def _biosteam_unit_classes() -> set[str]:
    """Every class BioSTEAM's units package defines, read from its files:
    found without importing BioSTEAM, which lives in the worker alone."""
    import ast
    import warnings

    spec = importlib.util.find_spec("biosteam")
    if spec is None or not spec.submodule_search_locations:
        pytest.skip("BioSTEAM is not installed here (the sim extra)")
    root = Path(list(spec.submodule_search_locations)[0]) / "units"
    names: set[str] = set()
    for path in root.rglob("*.py"):
        with warnings.catch_warnings():  # the package's own escape sequences are its business
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(path.read_text(encoding="utf-8"))
        names |= {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    return names


def test_every_class_the_vocabulary_names_is_one_biosteam_defines_and_names_one_step():
    ops = module_stores._projection()["pureos"]["unitOperations"]
    named = [(c, o["id"]) for o in ops for c in o.get("biosteamClasses") or []]
    assert named, "the vocabulary names no BioSTEAM class"
    assert len({c for c, _ in named}) == len(named), "a BioSTEAM class names two steps"
    missing = {c for c, _ in named} - _biosteam_unit_classes()
    assert not missing, f"BioSTEAM defines no class {sorted(missing)}"
    assert {o for _, o in named} >= {"distillation", "molecular-sieve", "centrifugation"}
