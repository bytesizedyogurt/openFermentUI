"""Proforma on the service's side (OF-BLD-014 §8.2–§8.3), with no simulator."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import intake, proforma


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def test_a_benchmark_not_yet_run_reads_as_none_and_starts_nothing(store):
    from openferment_core import api

    before = proforma.status()["status"]
    r = TestClient(api.app, base_url="http://127.0.0.1").get("/api/proforma/benchmark").json()
    assert r["artifact"] is None and r["simulator"]["status"] == before


def test_the_benchmark_cites_the_package_it_ran(store):
    inputs = proforma.benchmark_inputs()
    assert {i.source.kind for i in inputs} == {"model"}
    assert inputs[0].source.id.startswith("biorefineries.cornstover@")
