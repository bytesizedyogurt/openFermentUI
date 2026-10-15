"""Proforma on the service's side (OF-BLD-014 §8.1).

One `SimWorker` runs BioSTEAM in its own process. Its cold start takes about
forty seconds, so the worker starts on first use, or with the service when
`OPENFERMENT_WARM_PROFORMA=1`, and `status()` says where it is: `cold`,
`starting`, `ready` or `failed`, so the screen can say the simulator is
starting rather than look stuck.
"""
from __future__ import annotations

import os
import threading
from typing import Any, Literal

from .workers import SimWorker, WorkerCrashed, WorkerError, WorkerTimeout

# A cold import plus a first build; a setting, not a measurement (B.3 measured
# the import at forty seconds).
START_TIMEOUT_S = 240.0
CALL_TIMEOUT_S = 600.0

Status = Literal["cold", "starting", "ready", "failed"]

_WORKER: SimWorker | None = None
_STATE: dict[str, Any] = {"status": "cold", "error": None}
_LOCK = threading.Lock()


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
        _STATE.update(status="failed", error=str(e))


def start(background: bool = True) -> dict[str, Any]:
    """Start the worker if it is cold or failed; return the status."""
    with _LOCK:
        if _STATE["status"] in ("cold", "failed"):
            _STATE.update(status="starting", error=None)
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
    """A request on the warm worker; the first one starts it and waits."""
    if _STATE["status"] != "ready":
        start(background=False)
    if _STATE["status"] != "ready":
        raise WorkerError(f"the Proforma simulator could not start: {_STATE['error']}")
    return worker().call(op, args)


def warm_on_start() -> bool:
    return os.environ.get("OPENFERMENT_WARM_PROFORMA", "").strip() == "1"
