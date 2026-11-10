"""An entry module that imports cobra and is otherwise well formed: discovery counts the modules
its import adds, so it is set aside, unless an earlier entry module left cobra imported."""
import cobra  # noqa: F401

from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="h1z-heavy-unseen", worker="h1probe.worker", distributions=("openferment-engine-h1probe",))
