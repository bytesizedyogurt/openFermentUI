"""The service serves the built app at / beside /api (OF-BLD-012 §B.4).

A temporary dist/ stands in for `pnpm build`, so nothing here depends on
whether this checkout has been built. The mount the import may already have
made (a built checkout) is set aside for each test and put back after.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openferment_core import api

MARKER = "outside-dist-marker"


@pytest.fixture
def client(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>openFerment</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('app')", encoding="utf-8")
    # A file beside dist/, standing in for core/.env: a request must never reach it.
    (tmp_path / "beside.txt").write_text(MARKER, encoding="utf-8")

    saved = list(api.app.router.routes)
    api.app.router.routes[:] = [r for r in saved if getattr(r, "name", None) != "app"]
    assert api.mount_app(api.app, dist)
    try:
        yield TestClient(api.app)
    finally:
        api.app.router.routes[:] = saved


def test_root_serves_the_app(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "<title>openFerment</title>" in r.text
    assert r.headers["cache-control"] == "no-cache", "a stale page would name assets a deploy deleted"


def test_assets_are_served(client):
    r = client.get("/assets/app.js")
    assert r.status_code == 200
    assert "console.log" in r.text
    assert r.headers["cache-control"] == api.IMMUTABLE


def test_api_still_answers_first(client):
    """The mount is a catch-all; every /api route must be tried before it."""
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["service"] == "openferment-core"


@pytest.mark.parametrize(
    "path",
    ["/../beside.txt", "/%2e%2e/beside.txt", "/assets/..%2f..%2fbeside.txt", "/..%2fbeside.txt"],
)
def test_nothing_outside_dist(client, path):
    r = client.get(path)
    assert r.status_code == 404
    assert MARKER not in r.text


def test_no_build_means_no_mount(tmp_path):
    bare = FastAPI()
    assert not api.mount_app(bare, tmp_path / "dist")
    assert not [r for r in bare.router.routes if getattr(r, "name", None) == "app"]


# The fixture above mounts a fresh build at the end on purpose, so it cannot
# see the order api.py itself creates. This imports api.py as the daemon does,
# in its own process with a build present, and asks every /api route.
PROBE = r"""
import json
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from openferment_core.api import app

routes = app.router.routes
mounts = [i for i, r in enumerate(routes) if getattr(r, "name", None) == "app"]
api = [(i, r.path, sorted(r.methods)[0]) for i, r in enumerate(routes) if isinstance(r, APIRoute)]
client = TestClient(app)
answers = {}
for _, path, method in api:
    r = client.request(method, path.replace("{paper_id}", "B5"), json={} if method == "POST" else None)
    answers[f"{method} {path}"] = r.headers.get("content-type", "")
print(json.dumps({"mounts": mounts, "last": len(routes) - 1, "api": [i for i, _, _ in api], "answers": answers}))
"""


def test_the_app_as_imported_mounts_last_and_every_api_route_answers(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    env = {
        **os.environ,
        "OPENFERMENT_DIST_DIR": str(dist),
        "OPENFERMENT_DATA_DIR": str(tmp_path / "data"),
        "OPENFERMENT_FIXTURES": "1",
    }
    out = subprocess.run(
        [sys.executable, "-c", PROBE], env=env, cwd=Path(__file__).parents[1],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()[-1]
    seen = json.loads(out)
    assert seen["mounts"] == [seen["last"]], "the build must be mounted, and last"
    assert max(seen["api"]) < seen["last"]
    for route, content_type in seen["answers"].items():
        assert content_type.startswith("application/json"), f"{route} was answered by the static mount"
