"""A study's scenarios (studies/scenarios.py; execution prompt §9.1 step 5;
ADR-006), offline.

The worker is test_runs.py's STAND-IN (the sugarcane plant's parameters, a
small SFF file). A scenario is checked against its plant's parameters and
kept, one per plant, configuration and values; it refuses what the plant
cannot take; running it is an engine run whose basis names each value's
author and which is `assumed`; a refused run is kept with the scenario as a
receipt; the Proforma screens' scenarios in the same table stay theirs.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from openferment_core import project_state
from openferment_core.api import app
from openferment_core.engine import library, runs, simulator
from openferment_core.models import Origin, Quantity, ScenarioCreate, ScenarioValue
from openferment_core.studies import scenarios
from openferment_core.workers import WorkerError

from test_runs import StandIn

MODEL = "claude-opus-5-5"


@pytest.fixture
def worker(monkeypatch):
    stand_in = StandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


def person(key: str, value: float, unit: str) -> ScenarioValue:
    return ScenarioValue(key=key, quantity=Quantity(value=value, unit=unit, origin=Origin(
        kind="person-assumption", by="Ada Moreno", at="2026-10-30", note="a delivered price quoted to us")))


def estimate(key: str, value: float, unit: str) -> ScenarioValue:
    return ScenarioValue(key=key, quantity=Quantity(value=value, unit=unit, origin=Origin(
        kind="model-estimate", by=MODEL, at="2026-10-30T12:00:00Z", note="a typical mill's crushing rate")))


def asked(**kw) -> ScenarioCreate:
    base = dict(title="A dearer cane", plant="sugarcane", by="Ada Moreno",
                values=[person("stream.sugarcane.price", 0.05, "USD/kg"),
                        estimate("stream.sugarcane.F_mass", 300000.0, "kg/hr")])
    return ScenarioCreate(**{**base, **kw})


def test_a_scenario_is_checked_against_its_plant_and_kept(worker):
    made = scenarios.make(asked())
    assert made.id.startswith("ssc-") and len(made.id) == 16 and made.kind == "engine"
    assert (made.plant, made.configuration, made.by, made.runIds) == ("sugarcane", None, "Ada Moreno", [])
    assert [v.quantity.origin.kind for v in made.values] == ["person-assumption", "model-estimate"]
    assert scenarios.listed() == [made] and scenarios.get(made.id) == made
    assert worker.calls == ["library_parameters"], "checking a scenario reads the plant's parameters and runs nothing"


def test_the_same_values_on_the_same_plant_are_one_scenario(worker):
    first = scenarios.make(asked())
    again = scenarios.make(asked(title="Dearer cane, renamed", by="Grace Hopper",
                                 values=list(reversed(first.values))))
    assert again.id == first.id and again.title == "Dearer cane, renamed" and again.by == "Ada Moreno"
    assert [s.id for s in scenarios.listed()] == [first.id]


@pytest.mark.parametrize("values, said", [
    ([person("stream.sugarcane.nothing", 1.0, "USD/kg")], "reads back no parameter"),
    ([person("stream.sugarcane.price", 0.05, "USD/t")], "is in USD/kg"),
    ([person("unit.T202.vessel_type", 1.0, "")], "read back in words"),
    ([person("stream.sugarcane.price", 0.05, "USD/kg"), estimate("stream.sugarcane.price", 0.04, "USD/kg")], "twice"),
])
def test_a_scenario_refuses_what_its_plant_cannot_take(worker, values, said):
    with pytest.raises(scenarios.ScenarioRefused, match=said):
        scenarios.make(asked(values=values))
    assert scenarios.listed() == []


def test_a_scenarios_value_is_an_assumption_or_an_estimate_with_its_moment():
    with pytest.raises(ValidationError, match="person's assumption or a model's estimate"):
        ScenarioValue(key="k", quantity=Quantity(value=1.0, unit="", origin=Origin(kind="record", ref="r-1")))
    with pytest.raises(ValidationError, match="says when"):
        ScenarioValue(key="k", quantity=Quantity(value=1.0, unit="", origin=Origin(kind="model-estimate", by=MODEL)))
    with pytest.raises(ValidationError, match="one value per parameter"):
        ScenarioValue(key="k", quantity=Quantity(value=1.0, unit="", low=0.5, origin=Origin(
            kind="person-assumption", by="Ada Moreno", at="2026-10-30")))
    with pytest.raises(ValidationError, match="finite number"):
        ScenarioValue(key="k", quantity=Quantity(value="dear", unit="", origin=Origin(
            kind="person-assumption", by="Ada Moreno", at="2026-10-30")))


def test_a_plant_not_on_the_shelf_is_refused(worker):
    with pytest.raises(scenarios.ScenarioRefused, match="nosuch"):
        scenarios.make(asked(plant="nosuch"))


def test_running_a_scenario_is_an_engine_run_naming_each_values_author(worker):
    made = scenarios.make(asked())
    rep = scenarios.run(made.id, by="Ada Moreno")
    assert rep.run.status == "done" and rep.run.scenarioId == made.id and rep.run.provenance == "assumed"
    origins = {i.name: (i.quantity.origin.kind, i.quantity.origin.by) for i in rep.run.inputs}
    assert origins["stream.sugarcane.price"] == ("person-assumption", "Ada Moreno")
    assert origins["stream.sugarcane.F_mass"] == ("model-estimate", MODEL)
    assert scenarios.get(made.id).runIds == [rep.run.id]
    again = scenarios.run(made.id, by="Ada Moreno")
    assert again.run.id == rep.run.id and scenarios.get(made.id).runIds == [rep.run.id]


def test_a_refused_run_is_kept_with_its_scenario_as_a_receipt(worker, monkeypatch):
    made = scenarios.make(asked())

    def refusing(op, args):
        if op == "library_run":
            raise WorkerError("Refused: infeasible here (BioSTEAM's InfeasibleRegion): M1 over 100 %")
        return worker(op, args)

    monkeypatch.setattr(simulator, "call", refusing)
    with pytest.raises(library.LibraryRefused, match="InfeasibleRegion"):
        scenarios.run(made.id, by="Ada Moreno")
    (receipt,) = scenarios.get(made.id).runIds
    assert runs.get(receipt).status == "refused" and runs.get(receipt).scenarioId == made.id


def test_the_proforma_screens_scenarios_stay_theirs_in_the_same_table(worker):
    project_state.put("scenarios", "sc-made-1", {"id": "sc-made-1", "kind": "biosteam", "name": "n", "pinned": False},
                      "Ada Moreno")
    made = scenarios.make(asked())
    assert [s["id"] for s in project_state.load()["scenarios"]] == ["sc-made-1"]
    assert [s.id for s in scenarios.listed()] == [made.id]


def test_the_routes_make_read_run_and_refuse(worker):
    client = TestClient(app)
    made = client.post("/api/studies/scenarios", json=asked().model_dump(mode="json"))
    assert made.status_code == 200
    sid = made.json()["id"]
    assert [s["id"] for s in client.get("/api/studies/scenarios").json()] == [sid]
    assert client.get(f"/api/studies/scenarios/{sid}").json()["title"] == "A dearer cane"
    ran = client.post(f"/api/studies/scenarios/{sid}/run", json={"by": "Ada Moreno"})
    assert ran.status_code == 200 and ran.json()["run"]["scenarioId"] == sid
    assert client.get("/api/studies/scenarios/ssc-000000000000").status_code == 404
    bad = client.post("/api/studies/scenarios", json=asked(
        values=[person("stream.sugarcane.price", 0.05, "USD/t")]).model_dump(mode="json"))
    assert bad.status_code == 422 and "is in USD/kg" in bad.json()["detail"]
