"""Proforma's worker (OF-BLD-014 §8.1), against a real BioSTEAM process.

Marked `sim`: `pnpm test:sim` runs these, `test:core` leaves them out. The toy
flowsheet's answer is worked by hand in `flowsheets/toy.py`: a mixer feeding
a splitter, so the top carries the split share of each feed."""
from __future__ import annotations

import pytest

from openferment_core import proforma
from openferment_core.workers import WorkerError

pytestmark = pytest.mark.sim


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    return proforma


def test_the_toy_balances_by_hand(warm):
    out = warm.call("evaluate", {"flowsheet": "toy", "values": {}})
    assert out["topWater"] == pytest.approx(60.0, rel=1e-9)
    assert out["topEthanol"] == pytest.approx(30.0, rel=1e-9)
    assert out["bottomTotal"] == pytest.approx(60.0, rel=1e-9)


def test_a_changed_input_reaches_the_simulation(warm):
    out = warm.call("evaluate", {"flowsheet": "toy", "values": {"split": 0.25, "ethanol": 80.0}})
    assert out["topEthanol"] == pytest.approx(20.0, rel=1e-9) and out["bottomTotal"] == pytest.approx(135.0, rel=1e-9)


def test_an_unknown_input_or_flowsheet_is_refused_in_words(warm):
    with pytest.raises(WorkerError, match="no input sugar"):
        warm.call("evaluate", {"flowsheet": "toy", "values": {"sugar": 1.0}})
    with pytest.raises(WorkerError):
        warm.call("evaluate", {"flowsheet": "nowhere", "values": {}})


def test_a_grid_walks_every_point(warm):
    out = warm.call("grid", {"flowsheet": "toy", "axes": {"split": [0.2, 0.5], "water": [10.0, 20.0, 30.0]}})
    assert len(out["cells"]) == 6 and out["cells"][0]["outputs"]["topWater"] == pytest.approx(2.0, rel=1e-9)


def test_a_seeded_montecarlo_repeats_itself(warm):
    specs = {"split": {"kind": "uniform", "low": 0.1, "high": 0.9}, "ethanol": {"kind": "triangular", "low": 40.0, "mode": 50.0, "high": 70.0}}
    a = warm.call("montecarlo", {"flowsheet": "toy", "specs": specs, "n": 20, "seed": 4})
    b = warm.call("montecarlo", {"flowsheet": "toy", "specs": specs, "n": 20, "seed": 4})
    c = warm.call("montecarlo", {"flowsheet": "toy", "specs": specs, "n": 20, "seed": 5})
    assert a == b and a != c and len(a["samples"]) == 20
    for s in a["samples"]:
        assert 0.1 <= s["inputs"]["split"] <= 0.9 and 40.0 <= s["inputs"]["ethanol"] <= 70.0
        assert s["outputs"]["topEthanol"] == pytest.approx(s["inputs"]["ethanol"] * s["inputs"]["split"], rel=1e-9)


def test_the_status_endpoint(warm):
    from fastapi.testclient import TestClient

    from openferment_core import api

    r = TestClient(api.app, base_url="http://127.0.0.1").get("/api/proforma/status").json()
    assert r["status"] == "ready" and r["error"] is None


def test_the_committed_toy_fixtures_are_what_the_worker_makes(warm):
    # §8.1: the fixtures that need BioSTEAM are regenerated here, where the
    # real worker runs; write `standins.sim_fixtures()` over the file to refresh it.
    import json

    import standins
    committed = json.loads(standins.SIM_FIXTURES.read_text(encoding="utf-8"))
    assert standins.sim_fixtures() == committed, "tests/fixtures/sim/toy.json no longer matches the worker: write standins.sim_fixtures() over it"
