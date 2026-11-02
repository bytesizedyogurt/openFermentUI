"""The engine's simulator: the Proforma worker, BioSTEAM in a process of
its own (OF-BLD-014 §8.1; execution prompt §7.2).

One `SimWorker` runs BioSTEAM, thermosteam, biorefineries and the vendored
SFF toolkit. Its cold start takes about thirty seconds, so the worker starts
on first use, or with the service when `OPENFERMENT_WARM_PROFORMA=1`, and
`status()` says where it is: `cold`, `starting`, `ready` or `failed`, so the
screen can say the simulator is starting rather than look stuck. Every
engine module reaches the worker through `call`; proforma.py, thermo.py,
vessel.py and pureOS reach it through the names proforma.py re-exports.
"""
from __future__ import annotations

import os
import threading
from typing import Any, Literal

from ..workers import SimWorker, WorkerCrashed, WorkerError, WorkerTimeout

# A cold import plus a first build; a setting, not a measurement (B.3 measured
# the import at forty seconds).
START_TIMEOUT_S = 240.0
CALL_TIMEOUT_S = 600.0

Status = Literal["cold", "starting", "ready", "failed"]

_WORKER: SimWorker | None = None
_STATE: dict[str, Any] = {"status": "cold", "error": None}
_LOCK = threading.Lock()
# Set when a start in progress has settled, ready or failed (OF-BLD-019
# §7.R): a request arriving while another starts the worker waits on it.
_SETTLED = threading.Event()


def worker() -> SimWorker:
    global _WORKER
    with _LOCK:
        if _WORKER is None:
            _WORKER = SimWorker("openferment_core.workers.proforma_worker", timeout_s=CALL_TIMEOUT_S)
        return _WORKER


def status() -> dict[str, Any]:
    return dict(_STATE)


def _warm() -> None:
    try:
        worker().ping(timeout_s=START_TIMEOUT_S)
        _STATE.update(status="ready", error=None)
    except (WorkerError, WorkerCrashed, WorkerTimeout) as e:
        _STATE.update(status="failed", error=str(e) or type(e).__name__)
    finally:
        _SETTLED.set()


def start(background: bool = True) -> dict[str, Any]:
    """Start the worker if it is cold or failed; return the status."""
    with _LOCK:
        if _STATE["status"] in ("cold", "failed"):
            _STATE.update(status="starting", error=None)
            _SETTLED.clear()
            go = True
        else:
            go = False
    if go:
        if background:
            threading.Thread(target=_warm, name="proforma-warm", daemon=True).start()
        else:
            _warm()
    return status()


def call(op: str, args: dict[str, Any]) -> Any:
    """A request on the warm worker; the first one starts it and waits, and
    one arriving while another starts it waits for that start, as long as
    a start may take (OF-BLD-019 §7.R), then says in words why it cannot
    run: the start's own error, or that the simulator is still starting."""
    if _STATE["status"] != "ready":
        start(background=False)
    if _STATE["status"] == "starting":
        _SETTLED.wait(timeout=START_TIMEOUT_S)
    if _STATE["status"] == "starting":
        raise WorkerError("the Proforma simulator is still starting; try again in a minute")
    if _STATE["status"] != "ready":
        raise WorkerError(f"the Proforma simulator could not start: {_STATE['error'] or 'it gave no reason'}")
    return worker().call(op, args)


def warm_on_start() -> bool:
    return os.environ.get("OPENFERMENT_WARM_PROFORMA", "").strip() == "1"
