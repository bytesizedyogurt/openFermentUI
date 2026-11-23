"""The service answers a model on every JSON route (alpha 2.2 E.0a and E.0b;
ADR-007, implementation notes): each route declares the model it writes and
its handler returns that model, and the OpenAPI document lists every property
of a schema the service only writes as required, so the browser's generated
type reads each such field as one the service sends. A schema a request takes
keeps Pydantic's own required list, and so does every schema served as kept:
the runbook family and the rows a project keeps of its pages.
"""
from __future__ import annotations

import typing

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel

from openferment_core import api, artifacts, proforma
from openferment_core.engine import library, simulator
from openferment_core.models import BasisInput, BasisSource, Health, SimulatorStatus
from test_library import StandInWorker

# The routes that answer something besides a JSON model, each named by what
# it serves: the three event streams, a flowsheet's own file, and a study's
# export package.
STREAMS = {("POST", "/api/ask/stream"), ("GET", "/api/events"), ("POST", "/api/literature/answer")}
FILES = {("GET", "/api/flowsheets/{record_id}/file"), ("GET", "/api/studies/export")}
# The routes that serve their rows as kept (`response_model_exclude_unset`):
# the four that serve a runbook, and the project's state (E.0b); and the
# audit log, its rows' null fields left out (`response_model_exclude_none`,
# E.16).
SERVED_AS_KEPT = {("GET", "/api/studies/runbooks"), ("POST", "/api/studies/runbooks"),
                  ("GET", "/api/studies/runbooks/{runbook_id}"), ("POST", "/api/studies/runbooks/{runbook_id}/lock"),
                  ("GET", "/api/state"), ("GET", "/api/audit")}
# What a route served as kept serves whole, by the schema each family starts
# from: the project's state reads each Live conversation from the whole of
# what Postdoc keeps, every field set (project_state.state), and
# test_project_state.py holds each one to its whole dump.
SERVED_WHOLE = {("GET", "/api/state"): {"LiveConversation"}}


def routes():
    for r in api.app.routes:
        if isinstance(r, APIRoute) and r.include_in_schema:
            for method in sorted(r.methods):
                yield method, r.path_format, r


def models_named(t: typing.Any) -> list[type[BaseModel]]:
    """The Pydantic models a response annotation names: the model itself, a
    list's member, a union's members. A dict, Any and None name none."""
    if isinstance(t, type) and issubclass(t, BaseModel):
        return [t]
    return [m for a in typing.get_args(t) for m in models_named(a)]


def classes() -> dict[str, type[BaseModel]]:
    """Every model a route takes or answers, and every model inside one, by
    the name of its schema."""
    found: dict[str, type[BaseModel]] = {}

    def walk(t: typing.Any) -> None:
        if isinstance(t, type) and issubclass(t, BaseModel):
            if t.__name__ not in found:
                found[t.__name__] = t
                for f in t.model_fields.values():
                    walk(f.annotation)
            return
        for a in typing.get_args(t):
            walk(a)

    for _, _, r in routes():
        walk(r.response_model)
        for p in r.dependant.body_params:
            walk(p.field_info.annotation)
    return found


def pydantic_required(model: type[BaseModel]) -> list[str]:
    """The fields Pydantic lists as required: those with no default."""
    return [f.alias or name for name, f in model.model_fields.items() if f.is_required()]


def names_a_schema(s: dict) -> bool:
    """A response schema that is a component: a reference, a list of one, or
    one or none."""
    if "$ref" in s:
        return True
    if s.get("type") == "array":
        return names_a_schema(s.get("items", {}))
    members = [m for m in s.get("anyOf", []) if m.get("type") != "null"]
    return bool(members) and all(names_a_schema(m) for m in members)


def marked(doc: dict) -> set[str]:
    return api.response_only(doc) - api.AS_KEPT


# ── every JSON route declares the model it writes ──────────────────────


def test_every_json_route_declares_the_model_it_writes():
    bare = {(method, path) for method, path, r in routes() if not models_named(r.response_model)}
    assert bare == STREAMS | FILES, (
        f"routes answering no model beyond the named ones: {sorted(bare - STREAMS - FILES)}; named ones that now "
        f"answer a model, to take out of this file's sets: {sorted((STREAMS | FILES) - bare)}")


def test_the_document_names_a_schema_for_every_json_answer():
    doc = api.app.openapi()
    for method, path, _ in routes():
        if (method, path) in STREAMS | FILES:
            continue
        answers = {s: r for s, r in doc["paths"][path][method.lower()]["responses"].items() if s.startswith("2")}
        assert answers, f"{method} {path}"
        for status, answer in answers.items():
            schema = answer["content"]["application/json"]["schema"]
            assert names_a_schema(schema), f"{method} {path} {status}: {schema}"


def test_the_routes_that_gained_a_model_answer_it():
    client = TestClient(api.app)
    health = client.get("/api/health")
    assert health.status_code == 200 and list(health.json()) == list(Health.model_fields)
    assert health.json()["ok"] is True and health.json()["service"] == "openferment-core"
    status = client.get("/api/proforma/status").json()
    assert list(status) == list(SimulatorStatus.model_fields) == ["status", "error"]
    assert status["status"] in ("cold", "starting", "ready", "failed")
    assert client.get("/api/proforma/runs", params={"scenarioId": "sc-none"}).json() == {"scenarioId": "sc-none",
                                                                                         "artifact": None}
    assert client.get("/api/protparam", params={"product": "no-such-product"}).status_code == 404


# ── a schema the service only writes lists every property as required ──


def test_a_schema_the_service_only_writes_lists_every_property_as_required():
    doc = api.app.openapi()
    schemas = doc["components"]["schemas"]
    only = marked(doc)
    assert {"Health", "SimulatorStatus", "ScenarioRunsResponse", "ThermoPropsStored", "ThermoPropsAnswer",
            "StoredAnswer", "GridDim", "LiteratureStats", "ProformaRunResult", "ProformaTables", "RegressionCheck",
            "ToolResult", "AnswerPlan"} <= only
    for name in only:
        properties = schemas[name].get("properties")
        if properties:
            assert schemas[name]["required"] == list(properties), name
    assert not [n for n in schemas if n.endswith(("-Input", "-Output"))], "no schema splits in two"


def test_a_schema_a_request_takes_keeps_pydantics_required_list():
    doc = api.app.openapi()
    schemas = doc["components"]["schemas"]
    found = classes()
    asked = [n for n in schemas if n in found and n not in marked(doc)]
    assert {"TrainSpec", "TrainParam", "Quantity", "ProformaRunRequest", "EngineRunRequest", "EngineInput"} <= set(asked)
    for name in asked:
        assert schemas[name].get("required", []) == pydantic_required(found[name]), name


def test_the_runbook_family_served_as_kept_keeps_its_optional_fields():
    doc = api.app.openapi()
    schemas = doc["components"]["schemas"]
    found = classes()
    assert api.AS_KEPT <= set(schemas) and api.AS_KEPT <= api.response_only(doc)
    for name in api.AS_KEPT:
        assert schemas[name].get("required", []) == pydantic_required(found[name]), name
    prediction = schemas["Prediction"]["required"]
    assert {"kind", "interval", "artifactId", "recordIds"}.isdisjoint(prediction)
    assert {"lockedAt", "lockHash", "estCostUsd"}.isdisjoint(schemas["Runbook"]["required"])


def test_every_schema_a_route_serves_as_kept_is_in_the_family():
    """A route that leaves a model's unset fields out of its answer serves
    schemas whose fields a reader may find absent: each is in AS_KEPT, keeps
    Pydantic's own required list (a schema a request takes, or one whose
    every field is required, which no answer leaves out), or is one the route
    serves whole (SERVED_WHOLE)."""
    doc = api.app.openapi()
    schemas = doc["components"]["schemas"]
    found = classes()
    as_kept = set()
    for method, path, r in routes():
        if r.response_model_exclude_unset or r.response_model_exclude_none or r.response_model_exclude_defaults:
            as_kept.add((method, path))
            named: set[str] = set()
            answers = {s: a for s, a in doc["paths"][path][method.lower()]["responses"].items() if s.startswith("2")}
            api._named_in(answers, named)
            whole = api._reached(SERVED_WHOLE.get((method, path), set()), schemas)
            loose = [n for n in api._reached(named, schemas) - whole - api.AS_KEPT
                     if schemas[n].get("required", []) != pydantic_required(found[n])]
            assert loose == [], f"{method} {path} serves as kept schemas that list a field it may leave out: {loose}"
    assert as_kept == SERVED_AS_KEPT


def test_the_rows_a_project_keeps_are_served_as_kept_and_keep_their_optional_fields():
    """The rows of GET /api/state are in AS_KEPT, each listing the fields a
    row may leave out as optional, and the state itself lists every field."""
    doc = api.app.openapi()
    schemas = doc["components"]["schemas"]
    found = classes()
    rows = {"Deposition", "DepositionEntry", "DepositionObservation", "Reconciliation", "ReconciliationDelta",
            "MeasuredEvidence", "MeasuredConditions", "ProformaScenario", "TrainMade", "Override"}
    assert rows <= api.AS_KEPT
    for name in rows:
        assert schemas[name].get("required", []) == pydantic_required(found[name]), name
    # A row keeps the fields its model does not name; an override is the panel's, which writes its own fields alone.
    assert all(schemas[name].get("additionalProperties") is True for name in rows - {"Override"})
    assert "additionalProperties" not in schemas["Override"]
    assert {"correctedAt"}.isdisjoint(schemas["DepositionEntry"]["required"])
    assert {"sampleTimes", "seriesRoles"}.isdisjoint(schemas["Deposition"]["required"])
    assert {"origin", "ref", "unit", "chosenBy", "low", "high", "note"}.isdisjoint(schemas["Override"]["required"])
    assert {"flowsheetId", "lastRunId", "createdAt", "vessel", "trainRun"}.isdisjoint(
        schemas["ProformaScenario"]["required"])
    state = schemas["ProjectState"]
    assert state["required"] == list(state["properties"]) and "refused" in state["required"]
    assert schemas["LiveConversation"]["required"] == list(schemas["LiveConversation"]["properties"])


def test_a_model_that_writes_itself_keeps_pydantics_required_list():
    """Quantity's own serializer leaves its unset basis, range and origin out
    of what it writes, so no model with a serializer of its own is marked."""
    doc = api.app.openapi()
    writes_itself = {n for n, m in classes().items() if m.__pydantic_decorators__.model_serializers}
    assert "Quantity" in writes_itself
    assert writes_itself.isdisjoint(marked(doc))


# ── a run's tables and its checks, read by the run's id ────────────────


@pytest.fixture
def plant_run(monkeypatch):
    """A library run of sugarcane, kept, on test_library.py's stand-in worker:
    it holds the package test's eleven checks."""
    monkeypatch.setattr(simulator, "call", StandInWorker())
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return library.run("sugarcane")


def test_a_runs_tables_and_checks_are_read_by_its_id(plant_run):
    client = TestClient(api.app)
    tables = client.get(f"/api/biorepo/artifacts/{plant_run.id}/tables")
    assert tables.status_code == 200 and tables.json() == proforma.tables_of(plant_run).model_dump(mode="json")
    checks = client.get(f"/api/biorepo/artifacts/{plant_run.id}/checks")
    assert checks.status_code == 200 and len(checks.json()) == 11 and all(c["within"] for c in checks.json())
    assert checks.json() == [c.model_dump(mode="json") for c in proforma.checks_of(plant_run)]


@pytest.fixture
def other_tool():
    saved = dict(artifacts._REGISTRY)
    artifacts.register("t_words", "v1", lambda inputs, seed: {"words": "placeholder"})
    yield artifacts.compute("t_words", [BasisInput(name="x", value="x", unit="",
                                                   source=BasisSource(kind="convention", note="a placeholder"))])
    artifacts._REGISTRY.clear()
    artifacts._REGISTRY.update(saved)


@pytest.mark.parametrize("read", ["tables", "checks"])
def test_a_read_of_a_runs_tables_or_checks_names_what_holds_them(other_tool, read):
    client = TestClient(api.app)
    missing = client.get(f"/api/biorepo/artifacts/0000000000000000/{read}")
    assert missing.status_code == 404 and "no artifact" in missing.json()["detail"]
    refused = client.get(f"/api/biorepo/artifacts/{other_tool.id}/{read}")
    said = refused.json()["detail"]
    assert refused.status_code == 422 and "a t_words artifact" in said
    assert all(tool in said for tool in proforma.TABLE_TOOLS)
