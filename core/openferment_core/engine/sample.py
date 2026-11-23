"""The engine contract's own sample engine (docs/api/engines.md; ADR-015).

`SAMPLE` is a `WorkerEngine` over `workers/sample_worker.py`, which computes
nothing. No entry point registers it: the contract's tests register it in
their own registry, so the service's engines are those of the group alone.
"""
from __future__ import annotations

from .contract import WorkerEngine

SAMPLE = WorkerEngine(name="sample", worker="openferment_core.workers.sample_worker",
                      distributions=("openferment-core",))
