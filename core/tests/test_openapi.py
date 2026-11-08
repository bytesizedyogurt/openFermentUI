"""The OpenAPI document (docs/api/openapi.json; execution prompt §7.3 item 1,
A5): every route carries its project scope, and the committed file is what the
service writes (`pnpm gen:api --check` holds it; this test holds the scope)."""
from __future__ import annotations

import json
from pathlib import Path

from openferment_core import api, projects

DOC = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"
METHODS = ("get", "post", "put", "patch", "delete")


def operations(doc: dict):
    for path, item in doc["paths"].items():
        for method, op in item.items():
            if method in METHODS:
                yield path, method, op


def test_every_route_carries_its_project_scope():
    doc = api.app.openapi()
    seen = list(operations(doc))
    assert seen and all(op.get("x-openferment-scope") in ("project", "none") for _, _, op in seen)
    unscoped = {path for path, _, op in seen if op["x-openferment-scope"] == "none"}
    assert unscoped == {p for p, _, _ in seen if p.startswith(api.UNSCOPED)}
    assert {"/api/health", "/api/projects"} <= unscoped
    for path, method, op in seen:
        named = [p for p in op.get("parameters", []) if p.get("name") == projects.HEADER and p.get("in") == "header"]
        assert bool(named) == (op["x-openferment-scope"] == "project"), f"{method} {path}"


def test_every_scoped_operation_names_its_project_query_and_its_404():
    """Alpha 2.2 D.0 (B16): a scoped operation takes `?project=` beside the
    header and declares the 404 a project the database lacks is answered
    with; the document's description says how a request names its project
    and what the guard admits."""
    doc = api.app.openapi()
    refusal = {"$ref": "#/components/schemas/Refusal"}
    assert "Refusal" in doc["components"]["schemas"]
    for path, method, op in operations(doc):
        if op["x-openferment-scope"] != "project":
            assert not any(p.get("name") == projects.QUERY for p in op.get("parameters", [])), f"{method} {path}"
            continue
        queries = [p for p in op["parameters"] if p["name"] == projects.QUERY and p["in"] == "query"]
        assert len(queries) == 1, f"{method} {path}"
        assert op["responses"]["404"]["content"]["application/json"]["schema"] == refusal, f"{method} {path}"
    said = doc["info"]["description"]
    assert projects.HEADER in said and f"?{projects.QUERY}=" in said and "404" in said and "Origin" in said
    from openferment_core import guard

    assert all(f"`{suffix}`" in said for suffix in guard.OWN_SUFFIXES), "every name the guard admits, as guard.py lists"
    assert "Tailscale Funnel changes nothing" in said


def test_the_catalogue_reads_the_event_streams_and_the_tool_door_say_what_they_take_and_answer():
    from openferment_core import tools

    doc = api.app.openapi()
    entry = {"$ref": "#/components/schemas/CatalogueEntry"}
    one = doc["paths"]["/api/catalogues/{kind}/{entry_id}"]["get"]["responses"]
    assert one["200"]["content"]["application/json"]["schema"] == entry and "404" in one
    listed = doc["paths"]["/api/catalogues/{kind}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert listed["items"] == entry
    assert "agent" in doc["components"]["schemas"]["CatalogueEntry"]["properties"]
    for path, method in (("/api/events", "get"), ("/api/ask/stream", "post"), ("/api/literature/answer", "post")):
        assert list(doc["paths"][path][method]["responses"]["200"]["content"]) == ["text/event-stream"], path
    door = doc["paths"]["/api/tools/{name}"]["post"]
    assert [p["in"] for p in door["parameters"] if p["name"] == tools.ASSISTANT_HEADER] == ["header"]
    audit = doc["paths"]["/api/audit"]["get"]["description"]
    assert "1 to 500" in audit and "+00:00" in audit and "detail.via" in audit
    row = doc["components"]["schemas"]["AuditRow"]
    assert all(row["properties"][k].get("description") for k in ("id", "at", "target", "askId", "effort", "detail")), \
        "each field said in words"
    # A served row always holds its id; a field it may leave out is no required one.
    assert "id" in row["required"] and {"target", "askId", "effort"}.isdisjoint(row["required"])
    asked = {p["name"] for p in doc["paths"]["/api/audit"]["get"]["parameters"] if p["in"] == "query"}
    assert {"limit", "action", "target", "who"} <= asked


def test_the_committed_document_is_the_services():
    committed = json.loads(DOC.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(api.app.openapi(), sort_keys=True))
