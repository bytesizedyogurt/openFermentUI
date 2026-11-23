"""Imports cobra (a worker library) and is otherwise well formed: discovery should set it aside, cobra named."""
import cobra  # noqa: F401

from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="h1z-heavy-unseen", worker="h1_02_standin.worker")
