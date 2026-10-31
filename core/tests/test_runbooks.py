"""Runbooks from a study (studies/runbooks.py; execution prompt §9.1 step 5),
offline.

The worker is test_comparisons.py's STAND-IN, its run answering a
flowsheet's outputs in their units beside the price. A runbook made from an
engine run predicts the outputs it names in the run's units, names the run
as its basis and measures each at harvest; it is a row of the project's
runbooks in the page's shape, read back as kept. Locked by the service, it
holds the digest the browser's own code writes, a runbook the page made
included, and from then on the store refuses a row whose predictions or
measures differ. A second lock, a runbook with no prediction, a refused
run, an output that is no number and an unknown run are refused in words.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openferment_core import audit, project_state
from openferment_core.api import app
from openferment_core.engine import library, runs, simulator
from openferment_core.models import PredictedOutput, RunbookCreate
from openferment_core.runbook_lock import lock_hash
from openferment_core.studies import runbooks, scenarios
from openferment_core.workers import WorkerError

from test_comparisons import PricedStandIn
from test_runbook_lock import cases
from test_studies import asked

# A runbook as the page keeps one (src/data/types.ts `Runbook`).
PAGE_ROW = {"id": "rb-1", "kind": "research", "title": "A person's runbook", "status": "draft", "stages": [], "note": "",
            "eta": None, "outputs": [], "productId": None, "progressPct": 0, "estCostUsd": None, "strainId": None,
            "predictions": [], "measurementSchema": [], "lockedAt": None, "lockHash": None}


class FlowsheetStandIn(PricedStandIn):
    """The priced stand-in, its run also answering a flowsheet's outputs."""

    def __call__(self, op: str, args: dict):
        out = super().__call__(op, args)
        if op == "library_run":
            out = {**out, "outputs": {"ethanolKgPerH": 21_000.25, "product": "ethanol"},
                   "outputUnits": {"ethanolKgPerH": "kg/hr", "product": ""}}
        return out


@pytest.fixture
def worker(monkeypatch):
    stand_in = FlowsheetStandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


PRICE_AND_ETHANOL = [PredictedOutput(output="price.solvedPrice", label="Minimum selling price"),
                     PredictedOutput(output="outputs.ethanolKgPerH", label="Ethanol made")]


def made(run_id: str, predict: list[PredictedOutput] = PRICE_AND_ETHANOL, title: str = "Cane at the bench"):
    return runbooks.make(RunbookCreate(title=title, runId=run_id, predict=predict, by="Ada Moreno"))


def test_a_runbook_predicts_a_runs_outputs_in_its_units_and_measures_them_at_harvest(worker):
    run = runs.run("sugarcane", by="Ada Moreno").run
    book = made(run.id)
    assert book.id == runbooks.runbook_id(run.id, ["price.solvedPrice", "outputs.ethanolKgPerH"])
    assert book.id.startswith("rb-study-") and (book.kind, book.status, book.lockedAt) == ("research", "draft", None)
    price, ethanol = book.predictions
    assert (price.value, price.unit, price.confidence, price.artifactId) == (pytest.approx(0.0691), "USD/kg", "low",
                                                                             run.artifactId)
    assert all(words in price.basis for words in (run.id, "sugarcane", "computed", "price.solvedPrice"))
    assert (ethanol.value, ethanol.unit, ethanol.label) == (21_000.25, "kg/hr", "Ethanol made")
    assert [(m.id, m.predictionId, m.unit, m.timepoint) for m in book.measurementSchema] == [
        ("m1", "p1", "USD/kg", "harvest"), ("m2", "p2", "kg/hr", "harvest")]
    (kept,) = project_state.load()["runbooks"]
    assert kept["id"] == book.id and kept["lockedAt"] is None and kept["eta"] is None
    assert all(not {"kind", "interval", "recordIds"} & set(p) for p in kept["predictions"]), "absent stays absent"
    assert runbooks.listed() == [book] and runbooks.get(book.id) == book


def test_the_service_locks_a_runbook_under_the_digest_the_page_writes(worker):
    run = runs.run("sugarcane", by="Ada Moreno").run
    book = made(run.id)
    locked = runbooks.lock(book.id, by="Ada Moreno")
    (kept,) = project_state.load()["runbooks"]
    assert locked.lockHash == kept["lockHash"] == lock_hash(kept["predictions"], kept["measurementSchema"])
    assert project_state.load()["runbookLocks"] == {book.id: {"lockedAt": locked.lockedAt, "lockHash": locked.lockHash}}
    assert (("lock", book.id) in [(a.action, a.target) for a in audit.read()])
    with pytest.raises(runbooks.RunbookRefused, match="locked already"):
        runbooks.lock(book.id)
    revised = {**kept, "predictions": [{**kept["predictions"][0], "value": 0.05}, *kept["predictions"][1:]]}
    with pytest.raises(project_state.StateRefused, match="is locked"):
        project_state.put("runbooks", book.id, revised, "Grace")
    project_state.put("runbooks", book.id, {**kept, "status": "running"}, "Ada Moreno")
    assert runbooks.get(book.id).status == "running", "its stages move; its claims stay"
    assert made(run.id, title="Asked again") == runbooks.get(book.id)


def test_the_same_run_and_outputs_asked_again_are_the_runbook_kept_as_it_stands(worker):
    run = runs.run("sugarcane", by="Ada Moreno").run
    book = made(run.id)
    (kept,) = project_state.load()["runbooks"]
    project_state.put("runbooks", book.id, {**kept, "title": "Renamed by a person"}, "Grace")
    again = made(run.id, title="Asked again")
    assert again.id == book.id and again.title == "Renamed by a person"
    assert made(run.id, predict=PRICE_AND_ETHANOL[:1]).id != book.id
    assert len(runbooks.listed()) == 2


def test_a_runbook_the_page_made_locks_as_the_page_would_lock_it():
    for n, case in enumerate(cases()):
        rid = f"rb-page-{n}"
        project_state.put("runbooks", rid, {**PAGE_ROW, "id": rid, "predictions": case["predictions"],
                                            "measurementSchema": case["schema"]}, "Ada Moreno")
        assert runbooks.lock(rid, by="Ada Moreno").lockHash == case["digest"], case["name"]
    assert runbooks.listed() == [], "a person's runbooks are the page's to list"


def test_what_cannot_be_a_runbook_or_locked_is_refused_in_words(worker, monkeypatch):
    run = runs.run("sugarcane", by="Ada Moreno").run
    with pytest.raises(runbooks.RunbookRefused, match="no run"):
        made("0000000000000000")
    with pytest.raises(runbooks.RunbookRefused, match="no number with a unit for outputs.product"):
        made(run.id, predict=[PredictedOutput(output="outputs.product", label="Product")])
    with pytest.raises(runbooks.RunbookRefused, match="for regression.within"):
        made(run.id, predict=[PredictedOutput(output="regression.within", label="Held")])
    with pytest.raises(runbooks.RunbookRefused, match="each output once"):
        made(run.id, predict=[PredictedOutput(output="price.IRR", label="IRR"), PredictedOutput(output="price.IRR", label="Again")])

    def refusing(op, args):
        if op == "library_run":
            raise WorkerError("Refused: infeasible here (BioSTEAM's InfeasibleRegion): M1")
        return worker(op, args)

    monkeypatch.setattr(simulator, "call", refusing)
    scenario = scenarios.make(asked())
    with pytest.raises(library.LibraryRefused):
        scenarios.run(scenario.id, by="Ada Moreno")
    (receipt,) = scenarios.get(scenario.id).runIds
    with pytest.raises(runbooks.RunbookRefused, match="refused by its plant"):
        made(receipt)
    assert runbooks.listed() == []
    project_state.put("runbooks", "rb-1", PAGE_ROW, "Ada Moreno")
    with pytest.raises(runbooks.RunbookRefused, match="no claim"):
        runbooks.lock("rb-1")
    with pytest.raises(runbooks.RunbookNotFound):
        runbooks.lock("rb-none")
    project_state.put("runbooks", "rb-2", {**PAGE_ROW, "id": "rb-2", "status": "shelved"}, "Ada Moreno")
    with pytest.raises(runbooks.RunbookRefused, match="status"):
        runbooks.get("rb-2")
    project_state.put("runbooks", "rb-study-000000000000", {**PAGE_ROW, "id": "rb-study-000000000000",
                                                            "status": "shelved"}, "Ada Moreno")
    with pytest.raises(runbooks.RunbookRefused, match="rb-study-000000000000 is not kept in the runbook page's shape"):
        runbooks.listed()


def test_the_routes_make_read_list_and_lock_a_runbook_as_it_is_kept(worker):
    run = runs.run("sugarcane", by="Ada Moreno").run
    client = TestClient(app)
    body = {"title": "Cane at the bench", "runId": run.id, "by": "Ada Moreno",
            "predict": [{"output": "price.solvedPrice", "label": "Minimum selling price"}]}
    answer = client.post("/api/studies/runbooks", json=body)
    assert answer.status_code == 200
    rb = answer.json()
    assert set(rb["predictions"][0]) == {"id", "label", "value", "unit", "confidence", "basis", "artifactId"}
    assert "lockedAt" in rb and rb["lockedAt"] is None
    assert [r["id"] for r in client.get("/api/studies/runbooks").json()] == [rb["id"]]
    locked = client.post(f"/api/studies/runbooks/{rb['id']}/lock", json={"by": "Ada Moreno"}).json()
    assert locked["lockHash"] == lock_hash(locked["predictions"], locked["measurementSchema"])
    assert client.get(f"/api/studies/runbooks/{rb['id']}").json() == locked
    again = client.post(f"/api/studies/runbooks/{rb['id']}/lock", json={})
    assert again.status_code == 422 and "locked already" in again.json()["detail"]
    assert client.get("/api/studies/runbooks/rb-none").status_code == 404
    assert client.post("/api/studies/runbooks/rb-none/lock", json={}).status_code == 404
    assert client.post("/api/studies/runbooks", json={**body, "predict": []}).status_code == 422
    assert client.post("/api/studies/runbooks", json={**body, "runId": "0000000000000000"}).status_code == 422
