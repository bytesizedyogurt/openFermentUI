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


def test_the_committed_document_is_the_services():
    committed = json.loads(DOC.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(api.app.openapi(), sort_keys=True))
