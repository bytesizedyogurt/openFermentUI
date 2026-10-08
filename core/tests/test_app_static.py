"""The service serves the built app at / beside /api (OF-BLD-012 §B.4).

A temporary dist/ stands in for `pnpm build`, so nothing here depends on
whether this checkout has been built. The mount the import may already have
made (a built checkout) is set aside for each test and put back after.
"""
from __future__ import annotations

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


def test_assets_are_served(client):
    r = client.get("/assets/app.js")
    assert r.status_code == 200
    assert "console.log" in r.text


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
