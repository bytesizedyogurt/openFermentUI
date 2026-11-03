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
from standins import assumed_inputs

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
    kept = proforma.run(ProformaRunRequest(scenarioId=HELD, inputs=assumed_inputs(ASSUMED), samples=8), pool=standin)
    made = proforma.run(ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, inputs=assumed_inputs(ASSUMED),
                                           samples=8), pool=standin)
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
    newer = proforma.run(ProformaRunRequest(scenarioId=HELD, inputs=assumed_inputs([assume("plant_scale", 200000.0),
                                                                                     ASSUMED[1]]), samples=8),
                         pool=standin)
    assert newer.artifactId != kept.artifactId
    assert client.get(f"/api/proforma/runs?scenarioId={HELD}").json()["artifact"]["id"] == newer.artifactId
    # Another scenario's run is never answered for this one.
    assert client.get("/api/proforma/runs?scenarioId=sc-other-1").json()["artifact"] is None


def test_a_blank_scenario_is_refused_in_words(client):
    r = client.get("/api/proforma/runs?scenarioId=%20")
    assert r.status_code == 422 and "names the scenario" in r.json()["detail"]
    assert client.get("/api/proforma/runs").status_code == 422


# OF-BLD-019 §7.R (finding 3): a `?fits=` or `?inputs=` nested past
# Python's recursion limit is refused in words, as any other malformed
# value is, never a bare 500.
@pytest.mark.parametrize("path,params,name,words", [
    ("/api/proforma/bind", {"flowsheet": ETHANOL}, "fits", "fits is a JSON object"),
    ("/api/proforma/bind", {"flowsheet": ETHANOL}, "inputs", "inputs is a JSON list"),
    ("/api/proforma/ceiling-check", {"scenarioId": HELD}, "fits", "fits is a JSON object"),
    ("/api/proforma/ceiling-check", {"scenarioId": HELD}, "inputs", "inputs is a JSON list"),
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


# ── a Proforma run is a run of the biosteam engine (alpha 2.2 D3, D6) ──


def test_a_run_is_kept_as_one_row_of_biosteam_with_its_sff_file_and_its_price(client, standin):
    """D3: proforma.run keeps one runs row through engine/runs.keep_run: engine
    biosteam, tool proforma.run, thing the scenario's flowsheet, no
    configuration, the scenario's id on the row, created by the request's
    `by`; its SFF file written as it is kept; outputs.values its price block
    in the unit and on the basis its artifact states."""
    from openferment_core.engine import runs

    asked = ProformaRunRequest(scenarioId=HELD, inputs=assumed_inputs(ASSUMED), samples=8, by="A test person")
    r = proforma.run(asked, pool=standin)
    run = runs.get(r.artifactId)
    assert (run.id, run.engine, run.tool, run.plant, run.configuration) == (r.artifactId, "biosteam", proforma.RUN,
                                                                             ETHANOL, None)
    assert (run.status, run.scenarioId, run.by, run.provenance) == ("done", HELD, "A test person", "assumed")
    assert run.sff.recordId == f"run-{run.id}" and run.sffRefused is None
    art = artifacts.get(r.artifactId)
    unit, on = art.output["tableUnits"]["price"], art.output["tea"]["basis"]
    values = {v["name"]: v["quantity"] for v in run.outputs["values"]}
    # The base case's solved price, named as a library run names its own (engine/runs.py `values_of`).
    assert values["price.solvedPrice"] == {"value": r.basePrice, "unit": unit, "basis": on,
                                           "origin": {"kind": "artifact", "ref": run.id}}
    assert {k: q["value"] for k, q in values.items() if k != "price.solvedPrice"} == {
        f"quantiles.{k}": v for k, v in r.quantiles.items()}
    assert all(q["unit"] == unit and q["basis"] == on for q in values.values()) and set(run.outputs) == {"values"}
    # Served as every run is, its artifact and SFF record beside it, and listed under its engine.
    report = client.get(f"/api/runs/{run.id}").json()
    assert (report["run"]["id"], report["artifact"]["id"], report["flowsheet"]["id"]) == (run.id, run.id,
                                                                                        run.sff.recordId)
    assert report["flowsheet"]["origin"] == "run" and report["parameters"] is None
    assert [x["id"] for x in client.get("/api/runs?engine=biosteam").json()] == [run.id]


def test_the_same_request_twice_is_one_row_answered_from_it(standin, monkeypatch):
    from openferment_core.engine import runs

    asked = ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, inputs=assumed_inputs(ASSUMED), samples=8,
                               by="A test person")
    first = proforma.run(asked, pool=standin)
    asked_of: list[str] = []
    monkeypatch.setattr(proforma, "call", lambda op, args: asked_of.append(op) or standins._standin_call(op, args))
    again = proforma.run(asked.model_copy(update={"by": "Another test person"}), pool=standin)
    assert again.artifactId == first.artifactId and asked_of == [], "answered from its row, the worker never asked"
    (row,) = runs.listed()
    assert row.id == first.artifactId and row.by == "A test person" and row.scenarioId == MADE_HERE


def test_a_refusal_inside_the_run_is_kept_as_a_receipt_and_answered_from_it(client, standin, monkeypatch):
    from openferment_core.engine import runs
    from openferment_core.workers import WorkerError

    said = "a STAND-IN refusal of the flowsheet's base case"

    def refusing(op, args):
        if op == "run":
            raise WorkerError(f"Refused: {said}")
        return standins._standin_call(op, args)

    monkeypatch.setattr(proforma, "call", refusing)
    asked = ProformaRunRequest(scenarioId=HELD, inputs=assumed_inputs(ASSUMED), samples=8, by="A test person")
    with pytest.raises(proforma.ScenarioRefused, match=said) as refused:
        proforma.run(asked, pool=standin)
    (receipt,) = runs.listed()
    assert (receipt.status, receipt.refused, receipt.artifactId, receipt.sff, receipt.engine, receipt.by) == (
        "refused", said, None, None, "biosteam", "A test person")
    assert refused.value.run_id == receipt.id and receipt.scenarioId == HELD
    # Asked again, it is answered from the receipt: the worker is never asked.
    monkeypatch.setattr(proforma, "call", lambda op, args: pytest.fail(f"the worker was asked {op}"))
    with pytest.raises(proforma.ScenarioRefused, match=said):
        proforma.run(asked, pool=standin)
    r = client.post("/api/proforma/run", json=asked.model_dump(mode="json", exclude_none=True))
    assert r.status_code == 422 and said in r.json()["detail"] and len(runs.listed()) == 1


def test_a_run_whose_inputs_wait_keeps_nothing(client, standin):
    from openferment_core.engine import runs

    with pytest.raises(proforma.ScenarioRefused, match="wait for a source"):
        proforma.run(ProformaRunRequest(scenarioId=HELD, samples=8, by="A test person"), pool=standin)
    r = client.post("/api/proforma/run", json={"scenarioId": HELD, "samples": 8, "by": "A test person"})
    assert r.status_code == 422 and "wait for a source" in r.json()["detail"]
    assert runs.listed() == [] and not [a for a in artifacts.all_artifacts() if a.tool == proforma.RUN]
