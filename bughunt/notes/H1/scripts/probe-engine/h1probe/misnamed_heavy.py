"""An entry module that imports cobra (a worker library) and whose object names itself wrongly:
set aside for its name, with cobra left in the service's process."""
import cobra  # noqa: F401

from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="not-its-entry-name", worker="h1probe.worker")
