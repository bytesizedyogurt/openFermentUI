"""A scenario's newest run on the service (OF-BLD-019 §3.R, findings 8 and
21): `GET /api/proforma/runs?scenarioId=` answers the newest stored
`proforma.run` whose basis names the scenario, or none, so Proforma's page,
its index card and Compare find a run made from another browser, by
Postdoc's run_flowsheet or by the API, as pureOS and selling_price do.

Every record and assumption here is a FIXTURE written in the test; the runs
go through the real binding and artifact code over the closed-form STAND-IN
evaluator (standins.py), with no simulator. The scenario is one a fixture
holds by its id (`held`): the seed's went with the seed (alpha 2.0, ADR-010).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openferment_core import artifacts, intake, proforma
import standins  # test-only stand-ins, moved out of demo.py (alpha 2.0 stage 1)
from openferment_core.models import InputAssumption, ProformaRunRequest

ETHANOL = "ethanol_glucose_v0"
BY = "openFerment test fixture"
MADE_HERE = "sc-k3x9q-1"  # an id as the browser's createScenario makes them
HELD = "sc-held-1"  # a scenario the service holds by its id, as the `held` fixture holds it


@pytest.fixture(autouse=True)
def held(monkeypatch):
    """One scenario the service holds by its id, on the ethanol flowsheet."""
    row = {"id": HELD, "name": "A held test scenario", "kind": "biosteam", "modelId": ETHANOL}
    monkeypatch.setattr(proforma, "held_scenarios", lambda: [row])
    return row


@pytest.fixture()
def standin(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    rs = standins._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


@pytest.fixture()
def client(monkeypatch, standin):
    from openferment_core import api, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: standin)
    return TestClient(api.app, base_url="http://127.0.0.1")


def assume(key, value, low=None, high=None):
    return InputAssumption(key=key, value=value, low=value if low is None else low, high=value if high is None else high,
                           by=BY, at="2026-10-20", note="a STAND-IN for a test")


ASSUMED = [assume("plant_scale", 100000.0), assume("glucose_price", 0.4, 0.3, 0.5)]


def test_a_scenario_with_no_run_on_the_service_reads_as_none(client):
    r = client.get(f"/api/proforma/runs?scenarioId={HELD}")
    assert r.status_code == 200 and r.json() == {"scenarioId": HELD, "artifact": None}
    # A read: it starts no simulator.
    assert proforma.status()["status"] in ("cold", "failed")


def test_the_newest_run_of_each_scenario_is_found_by_the_scenario_its_basis_names(client, standin, monkeypatch):
    kept = proforma.run(ProformaRunRequest(scenarioId=HELD, assumptions=ASSUMED, samples=8), pool=standin)
    made = proforma.run(ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, assumptions=ASSUMED, samples=8),
                        pool=standin)
    got = client.get(f"/api/proforma/runs?scenarioId={HELD}").json()
    assert got["scenarioId"] == HELD and got["artifact"]["id"] == kept.artifactId
    assert got["artifact"]["tool"] == proforma.RUN
    assert [i["value"] for i in got["artifact"]["inputs"] if i["name"] == "scenario"] == [HELD]
    assert client.get(f"/api/proforma/runs?scenarioId={MADE_HERE}").json()["artifact"]["id"] == made.artifactId
    # The answer is the artifact as the store keeps it, the one pureOS and selling_price read.
    assert got["artifact"] == artifacts.get(kept.artifactId).model_dump(mode="json")
    assert proforma.latest_run(HELD).id == kept.artifactId
    # A newer run of the same scenario is the one answered. Its time is set a
    # second on: a run's time is kept to the second, and two runs in one
    # second are ordered by their ids (OF-BLD-020 §2.2 found the tie when the
    # basis, and so the ids, changed).
    from datetime import datetime, timedelta

    then = datetime.fromisoformat(proforma.latest_run(HELD).createdAt.replace("Z", "+00:00"))
    later = (then + timedelta(seconds=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
    monkeypatch.setattr(artifacts, "_now", lambda: later)
    newer = proforma.run(ProformaRunRequest(scenarioId=HELD, assumptions=[assume("plant_scale", 200000.0),
                                                                                    ASSUMED[1]], samples=8), pool=standin)
    assert newer.artifactId != kept.artifactId
    assert client.get(f"/api/proforma/runs?scenarioId={HELD}").json()["artifact"]["id"] == newer.artifactId
    # Another scenario's run is never answered for this one.
    assert client.get("/api/proforma/runs?scenarioId=sc-other-1").json()["artifact"] is None


def test_a_blank_scenario_is_refused_in_words(client):
    r = client.get("/api/proforma/runs?scenarioId=%20")
    assert r.status_code == 422 and "names the scenario" in r.json()["detail"]
    assert client.get("/api/proforma/runs").status_code == 422


# OF-BLD-019 §7.R (finding 3): a `?fits=` or `?assumptions=` nested past
# Python's recursion limit is refused in words, as any other malformed
# value is, never a bare 500.
@pytest.mark.parametrize("path,params,name,words", [
    ("/api/proforma/bind", {"flowsheet": ETHANOL}, "fits", "fits is a JSON object"),
    ("/api/proforma/ceiling-check", {"scenarioId": HELD}, "fits", "fits is a JSON object"),
    ("/api/proforma/ceiling-check", {"scenarioId": HELD}, "assumptions", "assumptions is a JSON list"),
])
def test_deeply_nested_json_in_a_query_is_refused_in_words(monkeypatch, standin, path, params, name, words):
    from openferment_core import api, evidence_pool

    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: standin)
    c = TestClient(api.app, base_url="http://127.0.0.1", raise_server_exceptions=False)
    # Past Python's json recursion limit (about ten thousand), inside a URL
    # an HTTP client still sends.
    for deep in ("[" * 12000, '[{"a":' * 3000):
        r = c.get(path, params={**params, name: deep})
        assert r.status_code == 422, (r.status_code, r.text[:200])
        assert words in r.json()["detail"]
