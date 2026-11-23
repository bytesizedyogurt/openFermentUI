"""Imports cobra (a worker library), then offers an object that names itself wrongly: discovery sets it
aside for its name."""
import cobra  # noqa: F401

from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="not-its-entry-name", worker="h1_02_standin.worker")
