"""A second request while the simulator starts waits for that start
(OF-BLD-019 §7.R, finding 6).

`proforma.call` (engine/simulator.py's `call`) starts a cold worker and waits; a request arriving while
another is starting it used to see `starting`, wait for nothing, and fail
with "the Proforma simulator could not start: None". It now waits for the
start in progress, bounded by the start's own timeout, and says in words
when that start failed or has not finished. Offline: a stand-in worker
whose ping sleeps.
"""
from __future__ import annotations

import threading
import time

import pytest

from openferment_core import proforma
from openferment_core.engine import simulator
from openferment_core.workers import WorkerError


class SlowStart:
    """A STAND-IN for the Proforma worker: ping sleeps, then answers or fails."""

    def __init__(self, delay: float, fails: bool = False):
        self.delay, self.fails, self.calls = delay, fails, []

    def ping(self, timeout_s=None):
        time.sleep(self.delay)
        if self.fails:
            raise WorkerError("the stand-in would not start")
        return {"ok": True}

    def call(self, op, args):
        self.calls.append(op)
        return f"ok:{op}"


@pytest.fixture
def cold(monkeypatch):
    def install(w):
        monkeypatch.setattr(simulator, "_WORKER", w)
        monkeypatch.setattr(simulator, "_STATE", {"status": "cold", "error": None})
        return w
    return install


def _two_calls(gap: float = 0.2):
    out: dict[str, object] = {}

    def first():
        try:
            out["a"] = proforma.call("reference", {})
        except Exception as e:  # noqa: BLE001 — the answer is what is compared
            out["a"] = e

    t = threading.Thread(target=first)
    t.start()
    time.sleep(gap)
    assert proforma.status()["status"] == "starting"
    try:
        out["b"] = proforma.call("thermo", {})
    except Exception as e:  # noqa: BLE001
        out["b"] = e
    t.join(5)
    return out


def test_a_request_during_the_cold_start_waits_and_is_answered(cold):
    w = cold(SlowStart(1.0))
    out = _two_calls()
    assert out["a"] == "ok:reference"
    assert out["b"] == "ok:thermo", out["b"]
    assert proforma.status()["status"] == "ready" and sorted(w.calls) == ["reference", "thermo"]


def test_a_start_that_fails_is_told_in_its_own_words_to_both(cold):
    cold(SlowStart(0.6, fails=True))
    out = _two_calls()
    for k in ("a", "b"):
        assert isinstance(out[k], WorkerError), out[k]
        assert "None" not in str(out[k]) and "would not start" in str(out[k])


def test_a_start_longer_than_its_timeout_is_said_to_be_starting(cold, monkeypatch):
    cold(SlowStart(1.5))
    monkeypatch.setattr(simulator, "START_TIMEOUT_S", 0.3)
    out = _two_calls()
    assert isinstance(out["b"], WorkerError)
    assert "still starting" in str(out["b"]) and "None" not in str(out["b"])
    assert out["a"] == "ok:reference"
