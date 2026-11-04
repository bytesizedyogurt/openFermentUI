"""A deposition's reading as a value a run sets (measurements.py; ADR-006's
measurement, the implementation note of 2026-11-03; alpha 2.2 §6.3, D7),
offline.

The project keeps one deposition of placeholder readings, each a software
placeholder in a placeholder unit or in a unit the unit tables convert; the
library's worker is test_runs.py's STAND-IN, the sample engine computes
nothing, and fermOS integrates the STAND-IN parameters test_vessel.py's
simulations use. The lookup's every refusal is said in words before anything
runs; a reading that stands is set in its parameter's unit with its depositor
and the time it was taken, a conversion stated in its note; a study scenario
resting on readings runs on the stand-in, and its run's provenance and its
inputs' origins read back from GET /api/runs/{id}; a contract engine's run
(the sample engine) and a fermOS simulation take readings; every door that
takes values refuses an unheld reading with a 422 in words, and the study
tool with an error; every reader of a value a run set reads a reading as
set; and the runbooks and fermOS reads list the deposition.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from openferment_core import api, artifacts, module_stores, params, project_state, tools, units
from openferment_core.basis import InputRefused, measurement_source, resolved
from openferment_core.engine import library, runs
from openferment_core.measurements import MeasurementRefused, corrected_by, looked_up
from openferment_core.models import BasisInput, BasisSource, EngineInput, Override, ParameterValue
from openferment_core.studies import comparisons, scenarios

from test_custom_train import INPUTS_STANDIN
from test_engines import engines, train_engines  # noqa: F401  (the registries of the sample and train engines)
from test_runs import StandIn

# test_custom_train.py's STAND-IN titre, deposited here as a reading in its unit.
TITRE = INPUTS_STANDIN["titre"]

# Who deposited the readings, and when the standing ones were taken.
DEPOSITOR = "Ada Moreno"
TAKEN = "2026-11-03T09:10:00Z"
DEPOSITION = "dep-1"
FLOW, PRICE = "stream.sugarcane.F_mass", "stream.sugarcane.price"


def _entry(entry_id: str, measure: str, value: float, unit: str, *, at: str = TAKEN, confirmed: bool = True) -> dict:
    return {"id": entry_id, "measureId": measure, "stepId": "s-1", "at": at, "value": value, "unit": unit,
            "raw": "a placeholder reading", "confirmed": confirmed}


# Placeholder readings, each a software placeholder: a flow read twice with no time (the later corrects the
# earlier), one read in another spelling of its unit, one no person confirmed, a series on one measure (each
# reading its own, the first corrected at its time), and one in a unit no flow is denominated in.
ENTRIES = [
    _entry("de-1", "m-flow", 2.0, "kg/hr", at="2026-11-03T09:00:00Z"),
    _entry("de-2", "m-price", 0.05, "USD/kg", confirmed=False),
    _entry("de-3", "m-flow", 3.0, "kg/hr"),
    _entry("de-4", "m-flow-h", 2.5, "kg/h"),
    _entry("de-5", "m-series", 1.0, "placeholder-unit"),
    _entry("de-6", "m-series", 2.0, "placeholder-unit"),
    _entry("de-7", "m-series", 1.5, "placeholder-unit", at="2026-11-03T09:20:00Z"),
    _entry("de-8", "m-hours", 4.0, "h"),
    _entry("de-9", "m-price-kept", 0.04, "USD/kg"),
]
SAMPLE_TIMES = {"de-5": 1, "de-6": 2, "de-7": 1}


def deposit(entries: list[dict] | None = None, deposition_id: str = DEPOSITION, **over) -> dict:
    body = {"id": deposition_id, "runbookId": "rb-1", "protocolId": "pr-1", "operatorId": None, "state": "running",
            "startedAt": "2026-11-03T08:00:00Z", "closedAt": None, "entries": list(ENTRIES if entries is None else entries),
            "observations": [], "reconciliation": None, "sampleTimes": dict(SAMPLE_TIMES), **over}
    project_state.put("depositions", deposition_id, body, by=DEPOSITOR)
    return body


def reading(entry: str, value: float, unit: str, *, name: str = FLOW, deposition: str = DEPOSITION, **origin) -> dict:
    """A value as a request carries a reading: its reading's own value and unit, and the reading it is."""
    return {"name": name, "quantity": {"value": value, "unit": unit,
                                       "origin": {"kind": "measurement", "ref": f"{deposition}/{entry}", **origin}}}


def measured(entry: str, value: float, unit: str, **kw) -> EngineInput:
    return EngineInput.model_validate(reading(entry, value, unit, **kw))


@pytest.fixture
def worker(monkeypatch):
    from openferment_core.engine import simulator

    stand_in = StandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


# ── the lookup ─────────────────────────────────────────────────────────


def test_a_reading_that_stands_is_set_in_its_parameters_unit_with_its_depositor_and_time():
    deposit()
    got = looked_up(measured("de-3", 3.0, "kg/hr"), "kg/hr")
    q = got.quantity
    assert (got.name, q.value, q.unit) == (FLOW, 3.0, "kg/hr")
    assert (q.origin.kind, q.origin.ref, q.origin.by, q.origin.at, q.origin.note) == (
        "measurement", "dep-1/de-3", DEPOSITOR, TAKEN, None)
    # A reading in another unit of the parameter's family is converted through the unit tables, said in its note,
    # the person's own note after it.
    other = looked_up(measured("de-4", 2.5, "kg/h", note="a placeholder note"), "kg/hr").quantity
    assert (other.value, other.unit) == (units.convert(2.5, "kg/h", "kg/hr"), "kg/hr")
    assert other.origin.note == "2.5 kg/h as deposited, 2.5 kg/hr in the parameter's unit (units.convert); a placeholder note"
    # A value naming the reading's own depositor and time, the time in another spelling of the same moment, is
    # the same reading, kept with the entry's own spelling.
    named = looked_up(measured("de-3", 3.0, "kg/hr", by=DEPOSITOR, at="2026-11-03T09:10:00+00:00"), "kg/hr")
    assert named == got
    # A value that is no reading comes back as it stands, and the basis's door reads no deposition for it.
    typed = EngineInput.model_validate({"name": FLOW, "quantity": {"value": 3.0, "unit": "kg/hr", "origin": {
        "kind": "person-assumption", "by": DEPOSITOR, "at": "2026-11-03"}}})
    assert looked_up(typed, "kg/hr") is typed and resolved(typed, "kg/hr") is typed


@pytest.mark.parametrize("entry, value, unit, unit_of, origin, said", [
    ("de-1", 3.0, "kg/hr", "kg/hr", {}, "reading dep-1/de-1 was corrected by dep-1/de-3, the reading that stands"),
    ("de-5", 1.0, "placeholder-unit", "placeholder-unit", {}, "reading dep-1/de-5 was corrected by dep-1/de-7"),
    ("de-2", 0.05, "USD/kg", "USD/kg", {}, "reading dep-1/de-2 waits for a person to confirm its number"),
    ("de-99", 1.0, "kg/hr", "kg/hr", {}, "deposition dep-1 holds no reading de-99; it holds 9 readings"),
    ("de-3", 3.5, "kg/hr", "kg/hr", {}, "reading dep-1/de-3 is 3 kg/hr, and the value sent is 3.5 kg/hr: a measurement "
                                        "carries its reading's own value and unit"),
    ("de-3", 3.0, "kg/h", "kg/hr", {}, "reading dep-1/de-3 is 3 kg/hr, and the value sent is 3.0 kg/h"),
    ("de-8", 4.0, "h", "kg/hr", {}, "is denominated in kg/hr, and reading dep-1/de-8 is in h, which does not convert"),
    ("de-3", 3.0, "kg/hr", "kg/hr", {"by": "Grace Hopper"},
     "reading dep-1/de-3 was deposited by Ada Moreno, and the value sent names Grace Hopper"),
    ("de-3", 3.0, "kg/hr", "kg/hr", {"at": "2026-11-04T09:10:00Z"},
     "reading dep-1/de-3 was taken at 2026-11-03T09:10:00Z, and the value sent names 2026-11-04T09:10:00Z"),
])
def test_each_rule_of_the_lookup_refuses_in_words(entry, value, unit, unit_of, origin, said):
    deposit()
    with pytest.raises(MeasurementRefused, match=said):
        looked_up(measured(entry, value, unit, **origin), unit_of)


def test_a_reading_in_a_series_is_its_own_and_one_the_project_does_not_hold_is_refused():
    deposit()
    assert looked_up(measured("de-6", 2.0, "placeholder-unit"), "placeholder-unit").quantity.value == 2.0
    assert looked_up(measured("de-7", 1.5, "placeholder-unit"), "placeholder-unit").quantity.origin.at == \
        "2026-11-03T09:20:00Z"
    with pytest.raises(MeasurementRefused, match="the project holds no deposition dep-9, so it holds no reading dep-9/de-1"):
        looked_up(measured("de-1", 2.0, "kg/hr", deposition="dep-9"), "kg/hr")
    with pytest.raises(MeasurementRefused, match="a measurement is its reading's one value, and this quantity also "
                                                 "carries low and high"):
        looked_up(EngineInput.model_validate({"name": FLOW, "quantity": {
            "value": 3.0, "unit": "kg/hr", "low": 2.0, "high": 4.0,
            "origin": {"kind": "measurement", "ref": "dep-1/de-3"}}}), "kg/hr")
    with pytest.raises(ValidationError, match="names the reading it is as <deposition id>/<entry id>"):
        EngineInput.model_validate(reading("de-3", 3.0, "kg/hr") | {"quantity": {
            "value": 3.0, "unit": "kg/hr", "origin": {"kind": "measurement", "ref": "dep-1"}}})


def test_a_reading_corrected_by_one_still_waiting_to_be_read_back_says_the_newer_number_waits():
    deposit([*ENTRIES, _entry("de-10", "m-flow", 3.1, "kg/hr", confirmed=False)])
    with pytest.raises(MeasurementRefused, match="reading dep-1/de-3 was corrected by dep-1/de-10, which waits for a "
                                                 "person to confirm its number at the bench"):
        looked_up(measured("de-3", 3.0, "kg/hr"), "kg/hr")


@pytest.mark.parametrize("by, said", [
    ("", "was kept by a browser with no person's name set, and a measurement names the person who took it: set your "
         "name in Settings before you deposit"),
    (project_state.UNNAMED, "was kept by a browser with no person's name set"),
    ("test", "was kept under the name 'test', which names nobody: 'test' is a placeholder"),
])
def test_a_reading_kept_by_nobody_named_is_no_measurement(by, said):
    project_state.put("depositions", DEPOSITION, {
        "id": DEPOSITION, "runbookId": "rb-1", "protocolId": None, "operatorId": None, "state": "closed",
        "startedAt": TAKEN, "closedAt": TAKEN, "entries": [_entry("de-3", "m-flow", 3.0, "kg/hr")], "observations": [],
        "reconciliation": None}, by=by)
    with pytest.raises(MeasurementRefused, match=f"reading dep-1/de-3 {said}"):
        looked_up(measured("de-3", 3.0, "kg/hr"), "kg/hr")
    assert TestClient(api.app).get("/api/depositions/readings").json() == [], "and no person is offered it"
    with pytest.raises(params.ParamRefused, match="names the person who deposited its reading: its reading was kept"):
        params.checked([_mu_max()], [Override(scope=SIM, key="mu_max", value=0.3, by=by or project_state.UNNAMED,
                                              at=TAKEN, origin="measurement", ref="dep-1/de-3")])


def test_a_reading_whose_conversion_is_no_finite_number_is_refused():
    deposit([_entry("de-1", "m-flow", 1e308, "kg s⁻¹")], sampleTimes={})
    assert units.convert(1e308, "kg s⁻¹", "g h⁻¹") == float("inf")
    with pytest.raises(MeasurementRefused, match="reading dep-1/de-1 is 1e\\+308 kg s⁻¹, which in g h⁻¹ is no finite "
                                                 "number"):
        looked_up(measured("de-1", 1e308, "kg s⁻¹"), "g h⁻¹")


def _mu_max():
    from openferment_core import kinetics

    return next(s for s in kinetics.family("batch_v1").specs() if s.key == "mu_max")


def test_the_reading_that_stands_for_its_measure_is_the_latest_at_its_time():
    body = deposit()
    by_id = {e["id"]: e for e in body["entries"]}
    assert corrected_by(body, by_id["de-1"]) == "de-3" and corrected_by(body, by_id["de-3"]) is None
    assert corrected_by(body, by_id["de-5"]) == "de-7" and corrected_by(body, by_id["de-6"]) is None
    assert corrected_by(body, by_id["de-7"]) is None


# ── what a person chooses from ─────────────────────────────────────────


# The runbook the deposition tests, as the project keeps it: placeholder words for its title and measures.
RUNBOOK = {"id": "rb-1", "title": "A placeholder runbook", "kind": "research", "status": "draft", "predictions": [],
           "measurementSchema": [
               {"id": "m-flow", "label": "A placeholder flow", "unit": "kg/hr", "timepoint": "harvest",
                "predictionId": None},
               {"id": "m-series", "label": "A placeholder series", "unit": "placeholder-unit", "timepoint": "t=1",
                "predictionId": None}]}


def test_the_readings_a_person_chooses_from_are_those_the_lookup_takes_each_with_its_runbook_measure_and_depositor():
    project_state.put("runbooks", "rb-1", RUNBOOK, by=DEPOSITOR)
    deposit()
    # A second deposition, kept by another person with no protocol's steps (the bench's readings alone), on a
    # runbook the project does not hold.
    project_state.put("depositions", "dep-2", {
        "id": "dep-2", "runbookId": "rb-9", "protocolId": None, "operatorId": None, "state": "closed",
        "startedAt": "2026-11-03T08:00:00Z", "closedAt": "2026-11-03T08:30:00Z",
        "entries": [_entry("de-1", "m-price", 0.04, "USD/kg")], "observations": [], "reconciliation": None},
        by="Grace Hopper")
    client = TestClient(api.app)
    every = client.get("/api/depositions/readings")
    assert every.status_code == 200, every.text
    # Every confirmed reading that stands, the latest taken first: de-1 and de-5 are corrected, de-2 waits for a
    # person to confirm it.
    assert [r["ref"] for r in every.json()] == ["dep-1/de-7", "dep-1/de-3", "dep-1/de-4", "dep-1/de-6", "dep-1/de-8",
                                                "dep-1/de-9", "dep-2/de-1"]
    held = {r["ref"]: r for r in every.json()}
    assert held["dep-1/de-3"] == {
        "ref": "dep-1/de-3", "depositionId": "dep-1", "entryId": "de-3", "runbookId": "rb-1",
        "runbook": "A placeholder runbook", "measureId": "m-flow", "measure": "A placeholder flow", "value": 3.0,
        "unit": "kg/hr", "at": TAKEN, "by": DEPOSITOR, "hours": None, "inUnit": None, "note": None}
    assert (held["dep-1/de-6"]["hours"], held["dep-1/de-7"]["hours"]) == (2.0, 1.0)
    assert (held["dep-2/de-1"]["by"], held["dep-2/de-1"]["runbook"], held["dep-2/de-1"]["measure"]) == (
        "Grace Hopper", None, None)
    # Asked in a unit: the readings in it or in a unit that converts into it, each in that unit with the conversion
    # in words, and each one the lookup takes in that unit.
    flows = client.get("/api/depositions/readings", params={"unit": "kg/hr"}).json()
    assert [r["ref"] for r in flows] == ["dep-1/de-3", "dep-1/de-4"]
    in_h = {r["ref"]: r for r in flows}["dep-1/de-4"]
    assert (in_h["value"], in_h["unit"], in_h["inUnit"]) == (2.5, "kg/h", units.convert(2.5, "kg/h", "kg/hr"))
    assert in_h["note"] == "2.5 kg/h as deposited, 2.5 kg/hr in the parameter's unit (units.convert)"
    for r in flows:
        got = looked_up(measured(r["entryId"], r["value"], r["unit"]), "kg/hr").quantity
        assert (got.value, got.origin.ref, got.origin.by, got.origin.at) == (r["inUnit"], r["ref"], r["by"], r["at"])
    assert [r["ref"] for r in client.get("/api/depositions/readings", params={"unit": "placeholder-unit"}).json()] == [
        "dep-1/de-7", "dep-1/de-6"]
    assert client.get("/api/depositions/readings", params={"unit": "a-unit-no-reading-is-in"}).json() == []
    # An empty unit asks for what a unitless parameter takes, and no reading here is unitless.
    assert client.get("/api/depositions/readings", params={"unit": ""}).json() == []


# ── a study scenario resting on readings, run on the stand-in ───────────


def test_a_scenario_resting_on_readings_runs_measured_and_its_run_reads_them_back(worker):
    deposit()
    client = TestClient(api.app)
    made = client.post("/api/studies/scenarios", json={
        "title": "The flow read at the bench", "plant": "sugarcane", "by": "Grace Hopper",
        "values": [{"key": FLOW, "quantity": reading("de-4", 2.5, "kg/h")["quantity"]}]})
    assert made.status_code == 200, made.text
    (kept,) = made.json()["values"]
    # Kept as its reading's own value and unit, its depositor and time filled from the rows.
    assert kept["quantity"]["unit"] == "kg/h" and kept["quantity"]["origin"] == {
        "kind": "measurement", "ref": "dep-1/de-4", "by": DEPOSITOR, "at": TAKEN, "note": None}
    named = client.post("/api/studies/scenarios", json={
        "title": "The same", "plant": "sugarcane", "by": "Grace Hopper",
        "values": [{"key": FLOW, "quantity": reading("de-4", 2.5, "kg/h", by=DEPOSITOR, at=TAKEN)["quantity"]}]})
    assert named.json()["id"] == made.json()["id"], "naming the reading's own depositor and time is one scenario"
    ran = client.post(f"/api/studies/scenarios/{made.json()['id']}/run", json={"by": "Grace Hopper"})
    assert ran.status_code == 200, ran.text
    run_id = ran.json()["run"]["id"]
    report = client.get(f"/api/runs/{run_id}").json()
    run = report["run"]
    assert run["provenance"] == "measured" and report["artifact"]["provenance"] == "measured"
    (flow,) = [i for i in run["inputs"] if i["name"] == FLOW]
    origin = flow["quantity"]["origin"]
    set_to = units.convert(2.5, "kg/h", "kg/hr")
    assert (flow["quantity"]["value"], flow["quantity"]["unit"]) == (set_to, "kg/hr")
    assert (origin["kind"], origin["ref"], origin["by"], origin["at"]) == ("measurement", "dep-1/de-4", DEPOSITOR, TAKEN)
    assert "2.5 kg/h as deposited, 2.5 kg/hr in the parameter's unit" in origin["note"]
    # The plant was built with the reading set, as a person's value is, and held to no package test.
    (asked,) = [args for op, args in worker.library.calls if op == "library_run"]
    assert asked["overrides"] == {FLOW: set_to}
    art = artifacts.get(run["artifactId"])
    assert art.output["regression"] is None and art.output["checks"] == []
    assert library.plant_of(art)["overrides"] == {FLOW: set_to}
    # The panel reads the reading as the run's own value.
    value = {v["key"]: v for v in report["parameters"]["values"]}[FLOW]
    assert (value["origin"], value["overriddenBy"], value["source"]["kind"]) == ("measurement", DEPOSITOR, "deposition")


def test_the_export_names_each_reading_and_carries_the_deposition_it_rests_on(worker):
    import json

    from openferment_core.studies import exports

    deposit()
    made = scenarios.make(scenarios.ScenarioCreate(title="The flow read at the bench", plant="sugarcane", by=DEPOSITOR,
                                                   values=[scenarios.ScenarioValue.model_validate(
                                                       {"key": FLOW, "quantity": reading("de-4", 2.5, "kg/h")["quantity"]})]))
    scenarios.run(made.id, by=DEPOSITOR)
    files = exports.files()
    held = json.loads(files["study.json"])
    (dep,) = held["depositions"]
    assert (dep["id"], dep["depositedBy"], [e["id"] for e in dep["record"]["entries"]]) == (
        DEPOSITION, DEPOSITOR, [e["id"] for e in ENTRIES])
    md = files["study.md"].decode()
    # The run's inputs and the scenario's values name the reading beside its depositor, and the deposition is there.
    assert md.count(f"{DEPOSITOR}, reading dep-1/de-4") == 2
    assert "### Deposition `dep-1`" in md and "| `dep-1/de-4` | m-flow-h | 2.5 | kg/h |" in md


def test_a_reading_beside_a_persons_value_runs_assumed(worker):
    deposit()
    made = scenarios.make(scenarios.ScenarioCreate(title="A reading and a quote", plant="sugarcane", by=DEPOSITOR, values=[
        scenarios.ScenarioValue.model_validate({"key": FLOW, "quantity": reading("de-3", 3.0, "kg/hr")["quantity"]}),
        scenarios.ScenarioValue.model_validate({"key": PRICE, "quantity": {"value": 0.05, "unit": "USD/kg", "origin": {
            "kind": "person-assumption", "by": DEPOSITOR, "at": "2026-11-03", "note": "a placeholder quote"}}})]))
    assert scenarios.run(made.id, by=DEPOSITOR).run.provenance == "assumed"


def test_a_reading_corrected_after_its_scenario_was_made_is_refused_when_it_runs_and_nothing_is_kept(worker):
    deposit()
    client = TestClient(api.app)
    made = client.post("/api/studies/scenarios", json={
        "title": "The flow", "plant": "sugarcane", "by": DEPOSITOR,
        "values": [{"key": FLOW, "quantity": reading("de-3", 3.0, "kg/hr")["quantity"]}]}).json()
    deposit([*ENTRIES, _entry("de-10", "m-flow", 3.1, "kg/hr")])
    ran = client.post(f"/api/studies/scenarios/{made['id']}/run", json={"by": DEPOSITOR})
    assert ran.status_code == 422 and "reading dep-1/de-3 was corrected by dep-1/de-10" in ran.json()["detail"]
    assert runs.listed() == [] and scenarios.get(made["id"]).runIds == []
    assert not [c for c in worker.library.calls if c[0] == "library_run"]


def test_the_library_and_the_engine_door_take_a_reading_and_refuse_one_the_project_does_not_hold(worker, engines):  # noqa: F811
    deposit()
    client = TestClient(api.app)
    lib = client.post("/api/library/sugarcane/run", json={"inputs": [reading("de-3", 3.0, "kg/hr")], "by": DEPOSITOR})
    assert lib.status_code == 200, lib.text
    assert lib.json()["run"]["provenance"] == "measured"
    door = client.post("/api/engines/biosteam/run", json={"thing": "sugarcane", "inputs": [reading("de-3", 3.0, "kg/hr")],
                                                          "by": DEPOSITOR})
    assert door.status_code == 200 and door.json()["run"]["id"] == lib.json()["run"]["id"], "one path, one run"
    for path, body in (("/api/library/sugarcane/run", {"inputs": [reading("de-1", 2.0, "kg/hr", deposition="dep-9")]}),
                       ("/api/engines/biosteam/run", {"thing": "sugarcane",
                                                      "inputs": [reading("de-1", 2.0, "kg/hr", deposition="dep-9")]}),
                       ("/api/studies/scenarios", {"title": "t", "plant": "sugarcane", "values": [
                           {"key": FLOW, "quantity": reading("de-1", 2.0, "kg/hr", deposition="dep-9")["quantity"]}]})):
        refused = client.post(path, json=body)
        assert refused.status_code == 422, (path, refused.text)
        assert "the project holds no deposition dep-9" in refused.json()["detail"], path
    assert len(runs.listed()) == 1 and scenarios.listed() == []


# ── a contract engine's run ───────────────────────────────────────────


def test_a_contract_engines_run_takes_a_reading_and_is_measured(engines):  # noqa: F811
    deposit()
    client = TestClient(api.app)
    asked = {"thing": "placeholder", "by": DEPOSITOR, "inputs": [reading("de-6", 2.0, "placeholder-unit", name="a-parameter")]}
    run = client.post("/api/engines/sample/run", json=asked).json()["run"]
    assert run["provenance"] == "measured"
    (value,) = [i for i in run["inputs"] if i["name"] == "value a-parameter"]
    origin = value["quantity"]["origin"]
    assert (origin["kind"], origin["ref"], origin["by"], origin["at"]) == ("measurement", "dep-1/de-6", DEPOSITOR, TAKEN)
    assert origin["note"] == f"measured on {TAKEN}"
    assert [(v["name"], v["quantity"]["value"]) for v in run["outputs"]["values"]] == [("given a-parameter", 2.0),
                                                                                    ("count", 1.0)]
    refused = client.post("/api/engines/sample/run", json={"thing": "placeholder", "inputs": [
        reading("de-2", 0.05, "USD/kg", name="a-parameter")]})
    assert refused.status_code == 422 and "waits for a person to confirm" in refused.json()["detail"]
    assert len(runs.listed("sample")) == 1


# ── fermOS, pureOS, Proforma and the panels' resolve ──────────────────


SIM = "fermos:family:batch_v1"
# test_vessel.py's STAND-IN parameters for fermos.simulate, each deposited here as a reading in its unit.
SIM_STANDIN = {"mu_max": 0.3, "ks": 0.5, "yxs": 0.1, "alpha": 2.0, "yps": 0.45, "p_max": 95.0, "x0": 0.5,
               "s0": 100.0, "p0": 0.0}


def test_a_simulation_resting_on_readings_alone_is_measured_and_reads_each_back_as_a_measurement():
    from openferment_core import fermos
    from openferment_core.models import SimulationRequest
    from standins import family_units

    unit_of = family_units("batch_v1")
    deposit([_entry(f"de-{k}", f"m-{k}", v, unit_of[k]) for k, v in SIM_STANDIN.items()], sampleTimes={})
    asked = SimulationRequest(family="batch_v1", product="ethanol", sugar="glucose", by=DEPOSITOR, inputs=[
        measured(f"de-{k}", v, unit_of[k], name=k) for k, v in SIM_STANDIN.items()])
    sim = fermos.simulate(asked)
    assert sim.provenance == "measured"
    held = {v.key: v for v in [*sim.parameters, *sim.start]}
    assert all(held[k].origin == "measurement" and held[k].overriddenBy == DEPOSITOR for k in SIM_STANDIN), held
    assert runs.get(sim.artifactId).provenance == "measured"
    refused = TestClient(api.app).post("/api/fermos/simulate", json={
        "family": "batch_v1", "inputs": [reading("de-1", 0.3, unit_of["mu_max"], name="mu_max", deposition="dep-9")]})
    assert refused.status_code == 422 and "the project holds no deposition dep-9" in refused.json()["detail"]


def test_the_panels_resolve_reads_a_reading_as_a_measurement_and_refuses_one_unheld():
    from standins import family_units

    unit_of = family_units("batch_v1")
    deposit([_entry("de-1", "m-mu", 0.3, unit_of["mu_max"])], sampleTimes={})
    client = TestClient(api.app)
    got = client.post(f"/api/params/{SIM}/resolve", json={"inputs": [reading("de-1", 0.3, unit_of["mu_max"], name="mu_max")]})
    assert got.status_code == 200, got.text
    (mu,) = [v for v in got.json()["values"] if v["key"] == "mu_max"]
    assert (mu["origin"], mu["overriddenBy"], mu["source"]["kind"], mu["source"]["id"]) == (
        "measurement", DEPOSITOR, "deposition", "dep-1/de-1")
    refused = client.post(f"/api/params/{SIM}/resolve", json={"inputs": [
        reading("de-2", 0.3, unit_of["mu_max"], name="mu_max")]})
    assert refused.status_code == 422 and "deposition dep-1 holds no reading de-2" in refused.json()["detail"]


def test_a_train_run_takes_a_reading_at_pureos_door_and_refuses_one_unheld(train_engines):  # noqa: F811
    from test_train import spec_of

    deposit([_entry("de-1", "m-vapour", 0.2, "")], sampleTimes={})
    client = TestClient(api.app)
    train = spec_of().model_dump(mode="json")
    ran = client.post("/api/pureos/train/run", json={"train": train, "by": DEPOSITOR,
                                                    "inputs": [reading("de-1", 0.2, "", name="F1.V")]})
    assert ran.status_code == 200, ran.text
    (v,) = [i for i in runs.get(ran.json()["artifactId"]).inputs if i.name == "F1.V"]
    assert (v.quantity.value, v.quantity.origin.kind, v.quantity.origin.ref) == (0.2, "measurement", "dep-1/de-1")
    refused = client.post("/api/pureos/train/run", json={"train": train, "inputs": [
        reading("de-1", 0.2, "", name="F1.V", deposition="dep-9")]})
    assert refused.status_code == 422 and "the project holds no deposition dep-9" in refused.json()["detail"]


def test_a_proforma_run_binds_a_reading_as_its_inputs_named_value_with_the_reading_as_its_source(monkeypatch, tmp_path):
    import standins
    from types import SimpleNamespace

    from openferment_core import intake, proforma
    from openferment_core.models import ProformaRunRequest
    from standins import proforma_units

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    held = {"id": "sc-held-1", "name": "A held test scenario", "kind": "biosteam", "modelId": "ethanol_glucose_v0"}
    monkeypatch.setattr(proforma, "held_scenarios", lambda: [held])
    rs = standins._standin_yeast_records()
    pool = SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})
    unit_of = proforma_units("ethanol_glucose_v0")
    deposit([_entry("de-1", "m-titre", TITRE, unit_of["titre"])], sampleTimes={})
    typed = [standins.as_input(Override(scope="proforma:sc-held-1", key=k, value=v, by="openFerment test fixture",
                                        at="2026-10-21", note="a STAND-IN for a test"), unit_of[k])
             for k, v in (("plant_scale", 100000.0), ("glucose_price", 0.4))]
    r = proforma.run(ProformaRunRequest(scenarioId="sc-held-1", samples=8, by=DEPOSITOR, inputs=[
        *typed, measured("de-1", TITRE, unit_of["titre"], name="titre")]), pool=pool)
    titre = {i.key: i for i in r.inputs}["titre"]
    assert (titre.binding, titre.value, titre.sampling) == ("assumption", TITRE, "fixed")
    assert titre.source == measurement_source("dep-1/de-1", DEPOSITOR, TAKEN)
    # Bound as a named value is, and said as the reading it is: no person's assumption.
    assert proforma._a_reading(titre)
    assert proforma._yield_words(titre) == f"a deposition's reading (dep-1/de-1), deposited by {DEPOSITOR}, one value held fixed"
    assert "what the reading measured" in proforma._row_words("above", "measurement", True)
    got = {i.name: i for i in artifacts.get(r.artifactId).inputs}
    assert got["titre"].source == titre.source and got["titre high"].value == TITRE
    assert r.provenance == "assumed", "beside the person's prices"
    refused = TestClient(api.app).post("/api/proforma/run", json={"scenarioId": "sc-held-1", "samples": 4, "inputs": [
        reading("de-1", TITRE, unit_of["titre"], name="titre", deposition="dep-9")]})
    assert refused.status_code == 422 and "the project holds no deposition dep-9" in refused.json()["detail"]


def test_a_vessel_design_reads_a_reading_back_as_a_measurement(monkeypatch, tmp_path):
    from openferment_core import intake, proforma, vessel
    from openferment_core.models import VesselRequest
    from test_vessel import AEROBIC_ID, StandInWorker, keep, standin_simulation

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    keep(AEROBIC_ID, standin_simulation(True))
    w = StandInWorker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(vessel, "_SPECS", {})
    unit = vessel.UNITS["plant_scale"]
    # test_vessel.py's STAND-IN plant scale, deposited here as a reading in its unit.
    deposit([_entry("de-1", "m-scale", 1000.0, unit)], sampleTimes={})
    d = vessel.design(VesselRequest(simulation=AEROBIC_ID, by=DEPOSITOR,
                                    inputs=[measured("de-1", 1000.0, unit, name="plant_scale")]))
    scale = {v.key: v for v in d.parameters}["plant_scale"]
    assert (scale.origin, scale.overriddenBy, scale.source.id) == ("measurement", DEPOSITOR, "dep-1/de-1")
    [(_, sent)] = [c for c in w.calls if c[0] == "vessel_design"]
    assert sent["scale"]["plantScale"] == 1000.0
    refused = TestClient(api.app).post("/api/fermos/vessel", json={"simulation": AEROBIC_ID, "inputs": [
        reading("de-1", 1000.0, unit, name="plant_scale", deposition="dep-9")]})
    assert refused.status_code == 422 and "the project holds no deposition dep-9" in refused.json()["detail"]


# ── every reader of a value a run set ─────────────────────────────────


def test_every_reader_of_a_value_a_run_set_reads_a_reading_as_set(worker):
    from openferment_core import fermos, proforma
    from openferment_core.pureos import train_spec
    from openferment_core.tools.engine import parameter_evidence, run_result
    from openferment_core.tools.writes import _bound_by

    deposit()
    base = runs.run("sugarcane", None, [], by=DEPOSITOR)
    rep = TestClient(api.app).post("/api/library/sugarcane/run", json={"by": DEPOSITOR, "inputs": [
        reading("de-3", 3.0, "kg/hr"), {"name": PRICE, "quantity": {"value": 0.05, "unit": "USD/kg", "origin": {
            "kind": "person-assumption", "by": DEPOSITOR, "at": "2026-11-03"}}}]}).json()
    report = runs.report(rep["run"]["id"])
    # The comparison's cells: the reading with its origin and depositor beside the package's own default.
    made = comparisons.make(comparisons.ComparisonCreate(title="t", runIds=[base.run.id, report.run.id], by=DEPOSITOR))
    cells = {row["key"]: row["values"] for row in made.artifact.output["values"]}
    assert cells[FLOW][1] == {"value": 3.0, "unit": "kg/hr", "origin": "measurement", "by": DEPOSITOR,
                              "ref": "dep-1/de-3"}
    assert cells[FLOW][0]["origin"] == "library-default"
    # engine_report's parameters: a reading measured, a person's value assumed, the package's own computed.
    by_key = {e.id.split(":parameters.", 1)[1]: e for e in parameter_evidence(report, "sugarcane", 10)}
    assert by_key[FLOW].provenance == "measured" and "a deposition's reading (dep-1/de-3)" in by_key[FLOW].label
    assert by_key[PRICE].provenance == "assumed" and "a person's assumption" in by_key[PRICE].label
    assert run_result(report).summary["valuesSet"] == [
        {"key": FLOW, "value": 3.0, "unit": "kg/hr", "origin": "measurement", "by": DEPOSITOR, "reading": "dep-1/de-3"},
        {"key": PRICE, "value": 0.05, "unit": "USD/kg", "origin": "person-assumption", "by": DEPOSITOR}]
    # What bound a parameter, in a tool's words, and the read-backs of fermOS and pureOS.
    source = measurement_source("dep-1/de-3", DEPOSITOR, TAKEN)
    value = ParameterValue(key=FLOW, value=3.0, source=source, origin="measurement", overriddenBy=DEPOSITOR)
    assert _bound_by(value, set(), {})["boundBy"] == "a deposition's reading, dep-1/de-3, deposited by Ada Moreno"
    given = BasisInput(name="mu_max", value=0.3, unit="h⁻¹", source=source)
    from openferment_core import kinetics

    specs = [s for s in kinetics.family("batch_v1").specs() if s.key == "mu_max"]
    (read,) = fermos._values_of(specs, [given])
    assert (read.origin, read.overriddenBy) == ("measurement", DEPOSITOR)
    (place,) = train_spec._values([("V", given)], lambda key: None)
    assert (place.origin, place.overriddenBy) == ("measurement", DEPOSITOR)
    # Proforma's sampling holds a reading fixed at its value, its kind the reading's.
    _, base_case, kinds = proforma._specs([BasisInput(name=f"titre{part}", value=TITRE, unit="g/L", source=source)
                                           for part in ("", " low", " high")])
    assert (base_case["titre"], kinds["titre"]) == (TITRE, "deposition")
    # A panel's measurement names who deposited it, on one line.
    spec = next(s for s in kinetics.family("batch_v1").specs() if s.key == "mu_max")
    with pytest.raises(params.ParamRefused, match="names the person who deposited its reading"):
        params.checked([spec], [Override(scope=SIM, key="mu_max", value=0.3, by="", at=TAKEN, origin="measurement",
                                         ref="dep-1/de-3")])


# ── the tool door ─────────────────────────────────────────────────────


def test_the_study_tool_takes_a_reading_its_caller_names_and_refuses_one_unheld(worker):
    deposit()
    ctx = tools.ToolContext(model="a-placeholder-model")
    made = tools.run("study_scenario", {"title": "The flow read at the bench", "plant": "sugarcane", "values": [
        {"key": FLOW, "quantity": {"value": 3.0, "unit": "kg/hr", "note": "the flow the bench read",
                                   "origin": {"kind": "measurement", "ref": "dep-1/de-3"}}}]}, ctx)
    assert made.error is None, made.error
    (value,) = made.summary["values"]
    assert (value["origin"], value["by"], value["note"]) == ("measurement", DEPOSITOR, "the flow the bench read")
    ran = tools.run("engine_run", {"scenario": made.summary["scenarioId"]}, ctx)
    assert ran.error is None and ran.summary["provenance"] == "measured", ran.error
    refused = tools.run("study_scenario", {"title": "t", "plant": "sugarcane", "values": [
        {"key": FLOW, "quantity": {"value": 3.0, "unit": "kg/hr", "origin": {"kind": "measurement", "ref": "dep-9/de-3"}}}]},
        ctx)
    assert refused.error.startswith("study_scenario refused: ") and "the project holds no deposition dep-9" in refused.error
    # A reading's origin names the reading alone: the depositor and the time are the deposition's, and a caller
    # who writes either is refused in words, as REST refuses one naming another person.
    named = tools.run("study_scenario", {"title": "t", "plant": "sugarcane", "values": [
        {"key": FLOW, "quantity": {"value": 3.0, "unit": "kg/hr", "note": "the flow the bench read", "origin": {
            "kind": "measurement", "ref": "dep-1/de-3", "by": "someone else", "at": "2026-11-04"}}}]}, ctx)
    assert named.error == (
        'study_scenario refused: a reading\'s origin names the reading alone, {"kind": "measurement", "ref": '
        '"<deposition id>/<entry id>"}; values[0].quantity.origin.by, values[0].quantity.origin.at are the '
        "deposition's to say, and the service fills each from it")
    assert len(scenarios.listed()) == 1


# ── the module reads ──────────────────────────────────────────────────


def test_the_runbooks_and_fermos_reads_list_the_projects_depositions_and_each_reading_a_run_may_take():
    project_state.put("runbooks", "rb-1", RUNBOOK, by=DEPOSITOR)
    deposit()
    assert "runbooks" not in module_stores.PARTIAL and "fermos" not in module_stores.PARTIAL
    stores = module_stores.Stores()
    (row,) = [r for r in stores.rows("runbooks") if r.kind == "deposition"]
    assert (row.id, row.ref, row.state, row.status) == (DEPOSITION, "runbooks/deposition/dep-1", "open", "running")
    d = row.detail
    assert (d["runbookId"], d["readings"], d["confirmed"], d["depositedBy"]) == ("rb-1", 9, 8, DEPOSITOR)
    # The readings that stand are those the lookup takes, in the order they were taken, as the route lists them.
    listed = {r["ref"] for r in TestClient(api.app).get("/api/depositions/readings").json()}
    assert d["standing"] == ["dep-1/de-3", "dep-1/de-4", "dep-1/de-6", "dep-1/de-7", "dep-1/de-8", "dep-1/de-9"]
    assert set(d["standing"]) == listed
    for ref in d["standing"]:
        entry = next(e for e in ENTRIES if e["id"] == ref.split("/")[1])
        assert looked_up(measured(entry["id"], entry["value"], entry["unit"]), entry["unit"]).quantity.origin.ref == ref
    # Each reading that stands is a row of its own, its value and unit as the bench kept them, marked measured.
    readings = {r.id: r for r in stores.rows("runbooks") if r.kind == "reading"}
    assert list(readings) == d["standing"]
    flow = readings["dep-1/de-3"]
    assert (flow.ref, flow.state, flow.status, flow.provenance) == ("runbooks/reading/dep-1/de-3", "open", "confirmed",
                                                                    "measured")
    assert flow.label == "A placeholder flow, read at the bench in deposition dep-1"
    assert {k: flow.detail[k] for k in ("reading", "measure", "value", "unit", "at", "depositedBy", "runbook")} == {
        "reading": "dep-1/de-3", "measure": "A placeholder flow", "value": 3.0, "unit": "kg/hr", "at": TAKEN,
        "depositedBy": DEPOSITOR, "runbook": "A placeholder runbook"}
    (fermos_row,) = [r for r in stores.rows("fermos") if r.kind == "deposition"]
    assert (fermos_row.ref, fermos_row.detail["series"], fermos_row.detail["fits"], fermos_row.detail["keptWith"]) == (
        "fermos/deposition/dep-1", 1, [], "runbooks/deposition/dep-1")
    assert fermos_row.detail["standing"] == d["standing"]
    read = tools.run("runbooks_read", {"ids": ["dep-1"], "words": "", "kind": "deposition", "state": "", "limit": 5},
                     tools.ToolContext(person=DEPOSITOR))
    assert read.error is None and [r.ref for r in read.rows] == ["runbooks/deposition/dep-1"]
    assert "partial" not in read.summary
    assert {"deposition", "reading", "measured-evidence"} <= set(module_stores.KINDS["runbooks"])
    assert "deposition" in module_stores.KINDS["fermos"]
    # A question naming a deposition, or the measure a reading is of, finds the module and the reading.
    asked = module_stores.coverage("What does the most recent deposition hold of a placeholder flow?", stores)
    (runbooks,) = [m for m in asked.modules if m.module == "runbooks"]
    assert runbooks.named and "runbooks/reading/dep-1/de-3" in [h.ref for h in runbooks.hits]
    closed = deposit(state="closed", closedAt="2026-11-03T12:00:00Z")
    assert closed["state"] == "closed"
    assert {r.state for r in module_stores.Stores().rows("runbooks") if r.kind in ("deposition", "reading")} == {"locked"}


def test_the_runbooks_read_lists_the_measured_evidence_a_reconciliation_released():
    project_state.put("runbooks", "rb-1", RUNBOOK, by=DEPOSITOR)
    deposit(state="closed", closedAt="2026-11-03T12:00:00Z")
    released = {"id": "me-1", "depositionId": DEPOSITION, "runbookId": "rb-1", "productId": None,
                "predictionId": "p-1", "label": "A placeholder prediction", "value": 3.0, "unit": "kg/hr",
                "provenance": "measured", "conditions": {"protocolId": None, "scale": 1, "strainId": None},
                "deviations": [], "confirmed": True, "at": "2026-11-03T12:10:00Z"}
    project_state.put("measuredEvidence", "me-1", released, by=DEPOSITOR)
    project_state.put("measuredEvidence", "me-2", {**released, "id": "me-2", "confirmed": False}, by=DEPOSITOR)
    read = tools.run("runbooks_read", {"ids": [], "words": "", "kind": "measured-evidence", "state": "", "limit": 5},
                     tools.ToolContext(person=DEPOSITOR))
    assert read.error is None
    rows = {r.id: r for r in read.rows}
    assert (rows["me-1"].ref, rows["me-1"].state, rows["me-1"].provenance) == (
        "runbooks/measured-evidence/me-1", "locked", "measured")
    assert rows["me-1"].label == "A placeholder prediction, measured in deposition dep-1"
    assert (rows["me-1"].detail["value"], rows["me-1"].detail["unit"], rows["me-1"].detail["depositionId"]) == (
        3.0, "kg/hr", DEPOSITION)
    # A released value nobody read back is marked unverified, as the lookup takes no unconfirmed number.
    assert rows["me-2"].provenance == "unverified" and rows["me-2"].detail["confirmed"] is False


def test_a_model_reads_a_reading_through_runbooks_read_and_makes_a_measured_scenario_from_what_it_returned(worker):
    project_state.put("runbooks", "rb-1", RUNBOOK, by=DEPOSITOR)
    deposit()
    ctx = tools.ToolContext(model="a-placeholder-model")
    read = tools.run("runbooks_read", {"ids": [], "words": "placeholder flow", "kind": "reading", "state": "",
                                       "limit": 5}, ctx)
    assert read.error is None, read.error
    row = next(r for r in read.rows if r.detail["unit"] == "kg/hr")
    asked = {"value": row.detail["value"], "unit": row.detail["unit"], "note": "the flow the bench read",
             "origin": {"kind": "measurement", "ref": row.detail["reading"]}}
    made = tools.run("study_scenario", {"title": "The flow the bench read", "plant": "sugarcane",
                                        "values": [{"key": FLOW, "quantity": asked}]}, ctx)
    assert made.error is None, made.error
    ran = tools.run("engine_run", {"scenario": made.summary["scenarioId"]}, ctx)
    assert ran.error is None and ran.summary["provenance"] == "measured", ran.error
    (value,) = scenarios.get(made.summary["scenarioId"]).values
    assert (value.quantity.origin.kind, value.quantity.origin.ref, value.quantity.origin.by) == (
        "measurement", row.detail["reading"], DEPOSITOR)


def test_conformance_holds_a_measurement_default_to_a_reading_the_project_holds():
    from openferment_core.engine import conform
    from openferment_core.models import Origin

    deposit()
    assert conform._names_its_ground(Origin(kind="measurement", ref="dep-1/de-3", at=TAKEN, by=DEPOSITOR))
    assert not conform._names_its_ground(Origin(kind="measurement", ref="dep-9/de-3", at=TAKEN, by=DEPOSITOR))
    assert not conform._names_its_ground(Origin(kind="measurement", ref="dep-1/de-99", at=TAKEN, by=DEPOSITOR))


def test_a_measurement_reaches_the_basis_only_through_the_lookup():
    """A door that converts a reading without its lookup cannot reach the
    basis: the converter itself looks it up (basis.override_of), so an
    unheld reading is refused there in words."""
    from openferment_core.basis import override_of

    with pytest.raises(InputRefused, match="the project holds no deposition dep-1"):
        override_of(SIM, measured("de-3", 3.0, "kg/hr", name="mu_max"), "kg/hr")
    assert BasisSource.model_fields.keys() == {"kind", "id", "note", "by"}, "a reading adds no field to a basis source"
