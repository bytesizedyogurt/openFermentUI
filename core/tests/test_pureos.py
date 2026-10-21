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


def test_a_run_kept_before_the_tables_is_not_said_to_have_had_no_tea():
    """§4.R: a run of OF-BLD-014 Phase 8 was priced by a TEA and kept its
    price, never its tables; its product basis says it predates the tables,
    not that it had no TEA."""
    old = _art(tables=False)
    old.output.update(basePrice=5.1, quantiles={"p50": 5.0}, samples=200)
    tr = pureos.train_of(old, scenarios=[])
    assert tr.product is None and "no TEA" not in tr.productBasis
    assert "kept before runs carried their tables" in tr.productBasis and "run the scenario again" in tr.note


def test_a_run_whose_base_case_could_not_run_says_so_and_why():
    """§4.R: a run made after §2.1 whose base case was infeasible keeps empty
    tables beside its reason; the train says the base case could not run and
    why, never that the run predates the tables or had no TEA."""
    bad = _art(tables=False)
    bad.output.update(baseInfeasible="Infeasible: carbon: this yield and content leave no sugar for respiration",
                      tablesSource=None, tea=None, streams=[], units=[], utilities=None, diagram=None, unitOrder=[],
                      diagramNote="the base case could not run, so it has no tables", tableUnits={})
    tr = pureos.train_of(bad, scenarios=[])
    for words in (tr.note, tr.productBasis):
        assert "base case could not run" in words and "leave no sugar for respiration" in words, words
        assert "kept before" not in words and "no TEA" not in words, words
    assert pureos.summary(tr).note == tr.note and tr.units == [] and tr.overallRecovery is None


# ── a unit whose passes stay apart (§4.R) ────────────────────────────────
#
# BioSTEAM's own ethanol purification (biorefineries.ethanol, the train
# ethanol_glucose_v0 runs): the beer is pumped through one side of a
# process heat exchanger (HXprocess) into the beer column; the column's
# bottoms are pumped back through the other side and leave as stillage. An
# HXprocess copies ins[0] to outs[0] and ins[1] to outs[1] (its `_run`), so
# the two passes never mix: the bottoms are lost at the column, and the
# exchanger passes on all the beer it heats.


def _purification(swap=False):
    streams = [
        _stream("beer", None, "P1", {"E": 100.0, "Water": 900.0}),
        _stream("s1", "P1", "HX", {"E": 100.0, "Water": 900.0}),
        _stream("s4", "HX", "D", {"E": 100.0, "Water": 900.0}),
        _stream("product", "D", None, {"E": 99.0, "Water": 10.0}),
        _stream("s2", "D", "P2", {"E": 1.0, "Water": 890.0}),
        _stream("s3", "P2", "HX", {"E": 1.0, "Water": 890.0}),
        _stream("stillage", "HX", None, {"E": 1.0, "Water": 890.0}),
    ]
    ins, outs = (["s3", "s1"], ["stillage", "s4"]) if swap else (["s1", "s3"], ["s4", "stillage"])
    units = [_unit("P1", 0, ["beer"], ["s1"], "Pump"), _unit("HX", 1, ins, outs, "HXprocess"),
             _unit("D", 2, ["s4"], ["product", "s2"], "BinaryDistillation"), _unit("P2", 3, ["s2"], ["s3"], "Pump")]
    return _art(streams=streams, units=units, tea=_tea(basis_flow=99.0))


@pytest.mark.parametrize("swap", [False, True], ids=["beer-on-side-0", "beer-on-side-1"])
def test_recovery_is_credited_by_pass_so_the_column_loses_its_bottoms_and_the_exchanger_nothing(swap):
    tr = pureos.train_of(_purification(swap), scenarios=[])
    u = _by(tr)
    d, hx = u["D"], u["HX"]
    assert d.recovery == pytest.approx(0.99) and d.lostTo == ["s2"] and d.productLost == pytest.approx(1.0)
    assert hx.onPath and hx.recovery == pytest.approx(1.0) and hx.lostTo == [] and hx.productLost == pytest.approx(0.0)
    # Only the beer's pass is on the path: its product in and out are that pass's.
    assert (hx.productIn, hx.productOut, hx.productOnward) == (pytest.approx(100.0),) * 3
    assert "s3" in (hx.note or "") and "stillage" in (hx.note or ""), hx.note
    assert not u["P2"].onPath and u["P2"].recovery is None and "off the product's path" in u["P2"].note
    assert u["P1"].onPath and u["P1"].recovery == pytest.approx(1.0)
    assert tr.overallRecovery == pytest.approx(0.99) and tr.productLost == pytest.approx(1.0)
    assert [round(x.cumulative, 6) for x in tr.units if x.onPath] == [1.0, 1.0, 0.99]


def test_a_mixing_unit_still_joins_every_inlet_to_every_outlet():
    """Only a unit whose passes BioSTEAM keeps apart is read by pass: a mixer
    or a separator fed by two lines (C: broth and a recycle) is one pass."""
    c = _by(pureos.train_of(_art(), scenarios=[]))["C"]
    assert c.productIn == pytest.approx(52.0) and c.recovery == pytest.approx(47.0 / 52.0)


def test_product_that_enters_a_unit_on_the_path_and_does_not_leave_it_is_lost_there():
    """§4.R: R forms 50 E, H passes 40 E on and nothing elsewhere, D delivers
    40. The ten H consumed are lost at H, so the cumulative and the overall
    recovery agree with H's own."""
    streams = [_stream("feed", None, "R", {"Glucose": 100.0}), _stream("broth", "R", "H", {"E": 50.0, "Water": 50.0}),
               _stream("hot", "H", "D", {"E": 40.0, "Water": 50.0}), _stream("product", "D", None, {"E": 40.0, "Water": 10.0}),
               _stream("bottoms", "D", None, {"Water": 40.0})]
    units = [_unit("R", 0, ["feed"], ["broth"]), _unit("H", 1, ["broth"], ["hot"]), _unit("D", 2, ["hot"], ["product", "bottoms"])]
    tr = pureos.train_of(_art(streams=streams, units=units, tea=_tea(basis_flow=40.0)), scenarios=[])
    h = _by(tr)["H"]
    assert h.recovery == pytest.approx(0.8) and h.productLost == pytest.approx(10.0) and h.lostTo == []
    assert "leaves it by no outlet" in (h.note or ""), h.note
    assert h.cumulative == pytest.approx(0.8) and tr.overallRecovery == pytest.approx(0.8)
    assert tr.productLost == pytest.approx(10.0)


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


def test_the_page_and_pureos_read_give_one_train_one_provenance(tmp_path, monkeypatch, pool):  # noqa: F811
    """§4.R: a run stored as `computed` whose bound record is no longer in
    the pool is worth less now. pureos_read worked that out from its inputs;
    the page served the file's word. Both read it as it stands now."""
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    (tmp_path / "artifacts").mkdir()
    inputs = [BasisInput(name="flowsheet", value="test_line", unit="", source=BasisSource(kind="convention")),
              BasisInput(name="titre", value="a record", unit="", source=BasisSource(kind="record", id="gone-record-1"))]
    a = _art(inputs=inputs)
    assert a.provenance == "computed"
    (tmp_path / "artifacts" / f"{a.id}.json").write_text(a.model_dump_json(), encoding="utf-8")
    row = read("pureos", ctx_for(pool, artifacts=lambda: [a]), ids=[LINE], kind="train").rows[0]
    c = _client()
    page = c.get(f"/api/pureos/train/{LINE}").json()
    listed = next(t for t in c.get("/api/pureos/trains").json() if t["artifactId"] == LINE)
    assert row.provenance != "computed"
    assert page["provenance"] == listed["provenance"] == row.provenance


def test_the_double_serves_what_the_code_reads_from_the_same_run():
    """The double's train is the one the real code reads from the run
    artifacts.json carries (test_demo holds the files to demo.py)."""
    kept = json.loads((PROTOTYPE / "artifacts.json").read_text(encoding="utf-8"))["response"]
    run = Artifact.model_validate(next(a for a in kept if a["tool"] == "proforma.run"))
    served = json.loads((PROTOTYPE / "pureos-train.json").read_text(encoding="utf-8"))["response"]
    assert pureos.train_of(run).model_dump(mode="json") == served


def test_every_run_the_double_keeps_has_its_train_listed_and_served():
    """OF-BLD-019 §7.R (finding 0): the double keeps sc-pha-1's run and
    sc-yeast-1's, and lists and serves a train for each, so pureOS → Train
    after a run of the yeast scenario is drawn by the browser tests."""
    kept = json.loads((PROTOTYPE / "artifacts.json").read_text(encoding="utf-8"))["response"]
    runs = [Artifact.model_validate(a) for a in kept if a["tool"] == "proforma.run"]
    assert len(runs) >= 2
    listed = json.loads((PROTOTYPE / "pureos-trains-archived.json").read_text(encoding="utf-8"))["response"]
    active = json.loads((PROTOTYPE / "pureos-trains.json").read_text(encoding="utf-8"))["response"]
    served = [json.loads((PROTOTYPE / f).read_text(encoding="utf-8"))["response"]
              for f in ("pureos-train.json", "pureos-train-yeast.json")]
    assert {r.id for r in runs} == {t["artifactId"] for t in listed} == {t["artifactId"] for t in served}
    assert [t["scenarioId"] for t in active] == ["sc-yeast-1"]
    for run in runs:
        assert pureos.train_of(run).model_dump(mode="json") in served


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
    # OF-BLD-020 §5.4: a train a model built is a kind train row too, and its
    # kept runs are kind train-run; pureos_build builds one.
    assert module_stores.KINDS["pureos"] == ("unit-operation", "train", "train-unit", "train-run")
    assert [n for n in tools.WHITELIST if n.startswith("pureos")] == ["pureos_read", "pureos_write", "pureos_build"], \
        "a train is read as a kind of pureos_read; pureos_build (OF-BLD-020 §5.4) is the one tool that builds one"
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


# ── BioSTEAM's own purification train, through the real worker (`sim`) ──


@pytest.mark.sim
def test_the_ethanol_train_loses_at_the_beer_column_and_the_exchanger_passes_on_its_beer(tmp_path, monkeypatch):
    """§4.R on BioSTEAM's own `create_ethanol_purification_system`, which
    ethanol_glucose_v0 runs (§2.3): the beer column's bottoms are lost at
    the column, the HXprocess that heats the beer with them passes on all the
    beer, and the pump on the bottoms is off the path. The inputs are the
    test_proforma STAND-INs, a fixture's assumptions: no number here is a
    result, and only which unit loses what is asserted."""
    from openferment_core import proforma
    from openferment_core.models import InputAssumption
    from test_proforma import ETHANOL_STANDIN

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    proforma.start(background=False)
    a = [InputAssumption(key=k, value=v, low=v, high=v, by="openFerment test fixture", at="2026-10-20")
         for k, v in ETHANOL_STANDIN.items()]
    tr = pureos.train_of(proforma.run_flowsheet("ethanol_glucose_v0", a, samples=1, seed=1, scenario_id="sc-yeast-1"),
                         scenarios=[])
    u = _by(tr)
    assert tr.product == "Ethanol" and tr.productStream == "ethanol"
    hx = [x for x in tr.units if x.unitClass == "HXprocess"]
    assert hx, "the purification train has no HXprocess: the case this test holds is gone"
    for x in hx:
        assert x.onPath and x.recovery == pytest.approx(1.0) and x.lostTo == [] and "kept apart" in x.note
        # The beer's pass feeds the beer column; the other pass is the column's bottoms coming back.
        beer_out = next(o for o in x.outs if any(s.id == o and s.sink and u[s.sink].unitClass == "BinaryDistillation"
                                                   for s in tr.streams))
        column = u[next(s.sink for s in tr.streams if s.id == beer_out)]
        assert column.recovery < 1.0 and column.lostTo, "the beer column loses its bottoms"
        bottoms = column.lostTo[0]
        pump = u[next(s.sink for s in tr.streams if s.id == bottoms)]
        assert not pump.onPath and pump.recovery is None
    on = [x for x in tr.units if x.onPath]
    assert on[-1].cumulative == pytest.approx(tr.overallRecovery)
    assert tr.productLost == pytest.approx(sum(x.productLost or 0.0 for x in on))
    assert tr.overallRecovery == pytest.approx(tr.productOut / (tr.productOut + tr.productLost))
