"""The mirror engine: the one object its entry point names (docs/api/engines.md, `WorkerEngine`).

It computes with nothing heavy, so `heavy` stays `()`; its worker is a module of its own.
"""
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="mirror", worker="openferment_engine_mirror.worker",
                      distributions=("openferment-engine-mirror",))
