"""What the review of Phase 3 found (OF-BLD-014 §3.R). Each test failed
before its fix."""
from __future__ import annotations

import json
import subprocess
import threading

import pytest

from openferment_core import artifacts, evidence_pool, intake, llm, spend, tools
from openferment_core.models import BasisInput, BasisSource, ReviewDecision
from openferment_core.workers import SimWorker

from test_tools import pool  # noqa: F401  (the stand-in pool fixture)


# R1 — a record a decision rejected is out of the pool, seed records included.
def test_a_seed_record_rejected_by_a_decision_is_not_in_the_pool(pool):  # noqa: F811
    rejected = ReviewDecision(status="rejected", provenance="curated", recordId="r-X1-1", at="2026-10-15T00:00:00Z", reviewer="Sean Creighton", rejectReason="misread")
    p = evidence_pool.build(pool.corpus, [], {"r-X1-1": rejected}, [])
    assert p.record("r-X1-1") is None
    r = tools.run("convert_units", {"recordId": "r-X1-1", "toUnit": "mg L-1"}, tools.ToolContext(pool_factory=lambda: p))
    assert r.error and r.evidence == []


# R2 — a stored artifact's provenance follows its inputs as they stand now.
def test_a_stored_artifact_takes_the_provenance_its_inputs_have_now(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    artifacts.register("t_r2", "v1", lambda inputs, seed: {"value": "x"})
    inp = [BasisInput(name="r", value="v", unit="", source=BasisSource(kind="record", id="r-1"))]
    a = artifacts.compute("t_r2", inp, records_by_id={"r-1": {"provenance": "verified"}})
    assert a.provenance == "computed"
    b = artifacts.compute("t_r2", inp, records_by_id={"r-1": {"provenance": "unverified"}})
    assert b.id == a.id and b.provenance == "unverified"
    assert artifacts.get(a.id).provenance == "unverified", "the stored file says so too"


# R3, R4 — a worker survives C-level stdout and an unserialisable result.
@pytest.fixture()
def worker():
    w = SimWorker("openferment_core.workers.echo_worker", timeout_s=10)
    yield w
    w.close()


def test_output_written_to_fd_1_does_not_corrupt_the_stream(worker):
    assert worker.call("cwrite") == {"quiet": True}
    assert worker.call("echo", {"x": "y"}) == {"x": "y"}


def test_a_result_json_cannot_hold_is_an_error_and_the_worker_lives(worker):
    from openferment_core.workers import WorkerError

    pid = worker.ping()["pid"]
    with pytest.raises(WorkerError):
        worker.call("unserialisable")
    assert worker.ping()["pid"] == pid


# R5a — spend that cannot be read closes the gate rather than resetting the day.
def test_unknown_spend_refuses_and_leaves_the_day_as_it_was(monkeypatch):
    from openferment_core import db
    from openferment_core.db.engine import make_engine

    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "25")
    spend.charge("answer", 24.0)
    down = make_engine("postgresql://nobody:nothing@127.0.0.1:9/none")
    previous_binding, previous_engine = db.bind(None), db.use_engine(down)
    try:
        assert spend.would_pass(5)[0] is True
        with pytest.raises(spend.SpendUnknown):
            spend.charge("answer", 0.1)
    finally:
        db.use_engine(previous_engine)
        db.bind(previous_binding)
        db.run(down.dispose())
    assert spend.total_today() == 24.0


# R5b — a model with no price cannot slip under the cap.
class _NeverSends:
    def __init__(self):
        self.messages = self

    def stream(self, **kw):
        pytest.fail("a request was sent")

def test_a_call_on_a_model_with_no_price_is_refused(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-unpriced-9")
    monkeypatch.setenv("OPENFERMENT_FALLBACK_MODEL", "claude-unpriced-9")
    with pytest.raises(llm.BudgetExhausted, match="no price on file"):
        llm.call(system="s", user="u", schema={"type": "object"}, max_tokens=10, client_factory=lambda: _NeverSends())


# R5c — check and charge are one step: concurrent calls cannot each pass.
def test_concurrent_reservations_cannot_together_pass_the_cap(monkeypatch):
    monkeypatch.setenv("OPENFERMENT_DAILY_BUDGET_USD", "1")
    barrier = threading.Barrier(10)
    granted = []

    def go():
        barrier.wait()
        try:
            granted.append(spend.reserve("answer", 0.3))
        except spend.CapReached:
            pass

    ts = [threading.Thread(target=go) for _ in range(10)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(granted) == 3, "0.3 three times fits under 1.00; a fourth would pass it"
    for g in granted:
        spend.settle(g, "answer", 0.1)
    assert spend.total_today() == pytest.approx(0.3)
    assert spend.state()["reservedUsd"] == 0


# R6 — the spend lock stays out of git.
def test_the_spend_lock_is_ignored():
    root = intake._CORE.parent
    out = subprocess.run(["git", "check-ignore", "core/data/spend.json.lock"], cwd=root, capture_output=True, text=True)
    assert out.returncode == 0


# R7 — a replay the tool now refuses says so; a damaged file is named.
def test_a_replay_the_tool_refuses_is_a_difference_not_a_crash(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    artifacts.register("t_r7", "v1", lambda inputs, seed: {"value": "x"})
    a = artifacts.compute("t_r7", [])

    def refuses(inputs, seed):
        raise ValueError("the engine no longer converts this")

    artifacts.register("t_r7", "v1", refuses)
    r = artifacts.replay(a.id)
    assert not r.identical and "no longer converts" in json.dumps(r.model_dump())


def test_a_damaged_artifact_file_is_a_409_naming_it(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from openferment_core import api

    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    from standins import plant_damaged

    plant_damaged("0123456789abcdef")
    c = TestClient(api.app, base_url="http://127.0.0.1")
    for r in (c.get("/api/biorepo/artifacts/0123456789abcdef"), c.post("/api/biorepo/artifacts/0123456789abcdef/replay")):
        assert r.status_code == 409 and "damaged" in r.json()["detail"]


def test_ready_names_spend_it_cannot_read():
    from openferment_core import db, ready
    from openferment_core.db.engine import make_engine

    down = make_engine("postgresql://nobody:nothing@127.0.0.1:9/none")
    previous_binding, previous_engine = db.bind(None), db.use_engine(down)
    try:
        check = ready.check_roles(False)
    finally:
        db.use_engine(previous_engine)
        db.bind(previous_binding)
        db.run(down.dispose())
    assert check.mark == "fail" and "cannot be read" in check.detail
