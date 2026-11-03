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


def test_an_unknown_input_or_flowsheet_is_refused_in_words(warm, tmp_path):
    with pytest.raises(WorkerError, match="no input sugar"):
        warm.call("evaluate", {"flowsheet": "toy", "values": {"sugar": 1.0}})
    # D11: the words of flowsheets.load's KeyError arrive as it wrote them, unquoted.
    for op, args in (("evaluate", {"values": {}}), ("reference", {"digits": 10}),
                     ("grid", {"axes": {"split": [0.2]}}), ("montecarlo", {"specs": {}, "n": 1}),
                     ("sff_export", {"path": str(tmp_path / "nowhere.sff.json")})):
        with pytest.raises(WorkerError) as e:
            warm.call(op, {"flowsheet": "nowhere", **args})
        assert str(e.value).startswith("Refused: there is no flowsheet nowhere; there are "), (op, str(e.value))


def test_grid_and_montecarlo_pass_the_structure_on_as_evaluate_does(warm):
    """D11: the toy is built once, whole, and takes no structure; grid and
    montecarlo hand the request's structure to each case, so the toy refuses
    one in words there as evaluate does."""
    structure = {"fermenter": {}, "train": {}, "finance": {}, "financeKeys": []}
    asks = (("evaluate", {"values": {}}), ("grid", {"axes": {"split": [0.2, 0.5]}}),
            ("montecarlo", {"specs": {"split": {"kind": "uniform", "low": 0.1, "high": 0.9}}, "n": 2}))
    for op, args in asks:
        with pytest.raises(WorkerError, match="Refused: toy is built once, whole, and takes no structure"):
            warm.call(op, {"flowsheet": "toy", **args, "structure": structure})
        assert warm.call(op, {"flowsheet": "toy", **args}) is not None, op


def test_a_unit_type_the_catalogue_does_not_hold_is_refused_in_its_words(warm):
    """D11: an unknown catalogue type is the worker's Refused, in the catalogue's words."""
    for op, args in (("catalogue_specs", {"type": "nonesuch"}),
                     ("catalogue_unit_check", {"type": "nonesuch", "ins": [], "values": {}, "hold": []})):
        with pytest.raises(WorkerError) as e:
            warm.call(op, args)
        assert str(e.value).startswith("Refused: there is no unit type 'nonesuch' in pureOS's catalogue; it holds "), (
            op, str(e.value))


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


def _digits(value, n: int = 12):
    """Every float of a JSON value to `n` significant digits: one machine's
    sum ends 56.00000000000001 where another's ends 56.0 (CI measured it), and
    a fixture holds what the worker computes, to the digits that mean it."""
    if isinstance(value, float):
        return float(f"{value:.{n}g}")
    if isinstance(value, dict):
        return {k: _digits(v, n) for k, v in value.items()}
    if isinstance(value, list):
        return [_digits(v, n) for v in value]
    return value


def test_the_committed_toy_fixtures_are_what_the_worker_makes(warm):
    # §8.1: the fixtures that need BioSTEAM are regenerated here, where the
    # real worker runs; write `standins.sim_fixtures()` over the file to refresh it.
    import json

    import standins
    committed = json.loads(standins.SIM_FIXTURES.read_text(encoding="utf-8"))
    assert _digits(standins.sim_fixtures()) == _digits(committed), \
        "tests/fixtures/sim/toy.json no longer matches the worker: write standins.sim_fixtures() over it"
