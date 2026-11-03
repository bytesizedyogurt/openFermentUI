"""Comparisons (studies/comparisons.py; execution prompt §9.1 step 5),
offline.

The worker is a STAND-IN: test_runs.py's for the parameters and the SFF
ops, and a `library_run` whose solved price follows the price a run sets.
Runs are compared output by output with each run's change from the first,
and value by value with each origin, the library's default where a run set
none; the comparison is one `study.comparison` artifact whose provenance is
the weakest of the runs', and it replays; the same runs in the same order
are one comparison; a refused run, an unknown run or one run alone is
refused in words. Runs of a contract engine (the contract's sample, whose
worker computes nothing) compare by their outputs.values, and beside a
library run's price and outputs, at `study comparison 2`: there a library
run has the library's default for a value its plant declares, and every
other cell of a value its run holds none of is empty. Library runs alone
keep `study comparison 1`, and a comparison kept there over another
engine's run replays at version 2 and says so.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts
from openferment_core.api import app
from openferment_core.engine import library, runs, simulator
from openferment_core.engine.sample import SAMPLE
from openferment_core.models import BasisInput, BasisSource, ComparisonCreate, ReplayDifference
from openferment_core.studies import comparisons, scenarios
from openferment_core.workers import WorkerError

from test_engines import given
from test_library import SUGARCANE_PARAMETERS
from test_runs import StandIn
from test_studies import asked

DEFAULTS = {p["key"]: p["value"] for p in SUGARCANE_PARAMETERS}


class PricedStandIn(StandIn):
    """test_runs.py's stand-in, with a run that is priced: the solved price
    is twice the cane's price as the run sets it, in the worker's shapes."""

    def __call__(self, op: str, args: dict):
        if op != "library_run":
            return super().__call__(op, args)
        self.calls.append(op)
        cane = args["overrides"].get("stream.sugarcane.price", DEFAULTS["stream.sugarcane.price"])
        return {"plant": args["plant"], "configuration": args["configuration"], "parameters": SUGARCANE_PARAMETERS,
                "libraryDefaults": DEFAULTS, "overrides": args["overrides"],
                "price": {"priced": True, "teaClass": "SugarcaneTEA", "IRR": 0.1, "solvedPrice": 2 * cane,
                          "product": "ethanol", "units": {"IRR": "", "solvedPrice": "USD/kg"}}}


@pytest.fixture
def worker(monkeypatch):
    stand_in = PricedStandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


def base_and_scenario():
    base = runs.run("sugarcane", by="Ada Moreno").run
    made = scenarios.make(asked())
    return base, scenarios.run(made.id, by="Ada Moreno").run


def test_runs_are_compared_output_by_output_and_value_by_value(worker):
    base, scen = base_and_scenario()
    rep = comparisons.make(ComparisonCreate(title="Dearer cane", runIds=[base.id, scen.id], by="Ada Moreno"))
    art = rep.artifact
    assert art.tool == comparisons.COMPARISON and rep.comparison.id == art.id == rep.comparison.artifactId
    assert rep.comparison.provenance == art.provenance == "assumed", "one run rests on an assumption and an estimate"
    rows = {r["key"]: r for r in art.output["rows"]}
    price = rows["price.solvedPrice"]
    assert price["unit"] == "USD/kg" and price["values"] == [pytest.approx(0.0691), pytest.approx(0.1)]
    assert price["change"][0] == 0 and price["change"][1] == pytest.approx(0.1 / 0.0691 - 1)
    assert rows["price.IRR"]["change"] == [0, 0] and rows["price.IRR"]["unit"] == ""
    values = {v["key"]: v["values"] for v in art.output["values"]}
    assert [c["origin"] for c in values["stream.sugarcane.price"]] == ["library-default", "person-assumption"]
    assert values["stream.sugarcane.price"][0]["value"] == DEFAULTS["stream.sugarcane.price"]
    assert values["stream.sugarcane.price"][1] == {"value": 0.05, "unit": "USD/kg", "origin": "person-assumption",
                                                   "by": "Ada Moreno"}
    assert values["stream.sugarcane.F_mass"][1]["origin"] == "model-estimate"
    assert [r["artifactId"] for r in art.output["runs"]] == [base.artifactId, scen.artifactId]
    assert comparisons.listed() == [rep.comparison] and comparisons.get(rep.comparison.id) == rep


def test_runs_on_the_librarys_own_defaults_compare_as_computed(worker):
    cane = runs.run("sugarcane", by="Ada Moreno").run
    corn = runs.run("corn", by="Ada Moreno").run
    assert cane.provenance == corn.provenance == "computed"
    rep = comparisons.make(ComparisonCreate(title="Two plants as the package builds them", runIds=[cane.id, corn.id]))
    assert rep.comparison.provenance == "computed" and rep.artifact.output["values"] == []
    assert [r["plant"] for r in rep.artifact.output["runs"]] == ["sugarcane", "corn"]


def test_a_comparison_replays_from_its_runs(worker):
    base, scen = base_and_scenario()
    rep = comparisons.make(ComparisonCreate(title="Dearer cane", runIds=[base.id, scen.id]))
    replayed = artifacts.replay(rep.artifact.id)
    assert replayed.identical and replayed.withinTolerance


def test_the_same_runs_in_the_same_order_are_one_comparison(worker):
    base, scen = base_and_scenario()
    first = comparisons.make(ComparisonCreate(title="Dearer cane", runIds=[base.id, scen.id], by="Ada Moreno"))
    again = comparisons.make(ComparisonCreate(title="Dearer cane, renamed", runIds=[base.id, scen.id], by="Grace"))
    assert again.comparison.id == first.comparison.id and again.comparison.title == "Dearer cane, renamed"
    assert again.comparison.by == "Ada Moreno" and len(comparisons.listed()) == 1
    reversed_ = comparisons.make(ComparisonCreate(title="The other way", runIds=[scen.id, base.id]))
    assert reversed_.comparison.id != first.comparison.id


def test_what_cannot_be_compared_is_refused_in_words(worker, monkeypatch):
    base = runs.run("sugarcane", by="Ada Moreno").run
    with pytest.raises(comparisons.ComparisonRefused, match="two or more different runs"):
        comparisons.make(ComparisonCreate(title="t", runIds=[base.id, base.id]))
    with pytest.raises(comparisons.ComparisonRefused, match="no run"):
        comparisons.make(ComparisonCreate(title="t", runIds=[base.id, "0000000000000000"]))

    def refusing(op, args):
        if op == "library_run":
            raise WorkerError("Refused: infeasible here (BioSTEAM's InfeasibleRegion): M1")
        return worker(op, args)

    monkeypatch.setattr(simulator, "call", refusing)
    made = scenarios.make(asked())
    with pytest.raises(library.LibraryRefused):
        scenarios.run(made.id, by="Ada Moreno")
    (receipt,) = scenarios.get(made.id).runIds
    with pytest.raises(comparisons.ComparisonRefused, match="refused by its plant"):
        comparisons.make(ComparisonCreate(title="t", runIds=[base.id, receipt]))
    assert comparisons.listed() == []


def test_the_routes_make_list_read_and_refuse(worker):
    base, scen = base_and_scenario()
    client = TestClient(app)
    made = client.post("/api/studies/comparisons", json={"title": "Dearer cane", "runIds": [base.id, scen.id],
                                                         "by": "Ada Moreno"})
    assert made.status_code == 200 and made.json()["artifact"]["tool"] == "study.comparison"
    cid = made.json()["comparison"]["id"]
    assert [c["id"] for c in client.get("/api/studies/comparisons").json()] == [cid]
    assert client.get(f"/api/studies/comparisons/{cid}").json()["comparison"]["provenance"] == "assumed"
    assert client.get("/api/studies/comparisons/0000000000000000").status_code == 404
    one = client.post("/api/studies/comparisons", json={"title": "t", "runIds": [base.id]})
    assert one.status_code == 422


# ── runs of any engine (alpha 2.2 stage C, D3) ─────────────────────────


def _sample_run(value: float):
    return SAMPLE.run("placeholder", None, [given("a-parameter", value, note="a placeholder")], "Ada Moreno")


def test_runs_of_a_contract_engine_compare_by_their_outputs_values():
    first, second = _sample_run(2.5), _sample_run(3.5)
    rep = comparisons.make(ComparisonCreate(title="Two placeholder runs", runIds=[first.id, second.id], by="Ada Moreno"))
    out = rep.artifact.output
    assert rep.artifact.toolVersion == comparisons.VERSION_ENGINES == "study comparison 2"
    assert [r["key"] for r in out["rows"]] == ["values.given a-parameter", "values.count"]
    given_back, count = out["rows"]
    assert (given_back["unit"], given_back["values"], given_back["change"]) == (
        "placeholder-unit", [2.5, 3.5], [0.0, pytest.approx(0.4)])
    assert (count["unit"], count["values"], count["change"]) == ("1", [1.0, 1.0], [0.0, 0.0])
    assert [(r["artifactId"], r["plant"]) for r in out["runs"]] == [(first.artifactId, "placeholder"),
                                                                    (second.artifactId, "placeholder")]
    (set_here,) = out["values"]
    assert set_here["key"] == "value a-parameter"
    assert [(c["value"], c["unit"], c["origin"], c["by"]) for c in set_here["values"]] == [
        (2.5, "placeholder-unit", "person-assumption", "Ada Moreno"),
        (3.5, "placeholder-unit", "person-assumption", "Ada Moreno")]
    assert rep.comparison.provenance == "assumed" and artifacts.replay(rep.artifact.id).identical


def test_a_library_run_and_a_contract_engines_run_compare_side_by_side(worker):
    """A comparison that holds a run of another engine gives a library run
    the library's default for a value its plant declares, and an empty cell
    (value, unit, origin and by null) for any value its run holds none of:
    the plant's run beside the sample's value, the sample's run beside the
    plant's."""
    base, scen = base_and_scenario()
    sample = _sample_run(2.5)
    rep = comparisons.make(ComparisonCreate(title="A plant beside a placeholder", runIds=[base.id, scen.id, sample.id]))
    assert rep.artifact.toolVersion == comparisons.VERSION_ENGINES
    rows = {r["key"]: r for r in rep.artifact.output["rows"]}
    assert list(rows) == ["price.IRR", "price.solvedPrice", "values.given a-parameter", "values.count"]
    assert rows["price.solvedPrice"]["values"] == [pytest.approx(0.0691), pytest.approx(0.1), None]
    assert rows["price.solvedPrice"]["unit"] == "USD/kg" and rows["price.IRR"]["unit"] == ""
    assert rows["values.given a-parameter"]["values"] == [None, None, 2.5]
    assert rows["values.given a-parameter"]["change"] == [None, None, None], "a change is reckoned from the first run's value"
    assert [r["plant"] for r in rep.artifact.output["runs"]] == ["sugarcane", "sugarcane", "placeholder"]
    values = {v["key"]: v["values"] for v in rep.artifact.output["values"]}
    assert set(values) == {"stream.sugarcane.price", "stream.sugarcane.F_mass", "value a-parameter"}
    assert list(values)[-1] == "value a-parameter", "in the order the runs give them"
    default, person, beside = values["stream.sugarcane.price"]
    assert (default["value"], default["origin"]) == (DEFAULTS["stream.sugarcane.price"], "library-default")
    assert (person["value"], person["origin"]) == (0.05, "person-assumption") and beside == comparisons.NO_VALUE
    assert values["value a-parameter"][:2] == [comparisons.NO_VALUE, comparisons.NO_VALUE]
    assert values["value a-parameter"][2]["origin"] == "person-assumption"


def test_a_comparison_of_library_runs_keeps_version_1_and_one_kept_there_over_another_engine_replays_at_version_2(
        worker, monkeypatch):
    """Library runs alone compare at `study comparison 1`, as they always
    have. A comparison over a run of another engine kept at version 1 (as
    stage B kept one) replays at version 2, and its first difference says so."""
    base, scen = base_and_scenario()
    library_only = comparisons.make(ComparisonCreate(title="Dearer cane", runIds=[base.id, scen.id])).artifact
    assert library_only.toolVersion == comparisons.VERSION
    first, second = _sample_run(2.5), _sample_run(3.5)
    basis = [BasisInput(name=f"run {n}", value=r.artifactId, unit="", source=BasisSource(
        kind="artifact", id=r.artifactId, note=f"engine run of {r.plant}")) for n, r in enumerate((first, second), 1)]
    now = artifacts.registered(comparisons.COMPARISON)
    monkeypatch.setitem(artifacts._REGISTRY, comparisons.COMPARISON, artifacts.Registered(
        comparisons.COMPARISON, comparisons.VERSION, lambda inputs, seed: {"runs": [], "rows": [], "values": []}))
    kept = artifacts.compute(comparisons.COMPARISON, basis)
    monkeypatch.setitem(artifacts._REGISTRY, comparisons.COMPARISON, now)
    assert kept.toolVersion == comparisons.VERSION
    replayed = artifacts.replay(kept.id)
    assert not replayed.identical
    assert replayed.differences[0] == ReplayDifference(path="toolVersion", stored=comparisons.VERSION,
                                                       replayed=comparisons.VERSION_ENGINES)
