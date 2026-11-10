"""An engine whose things are a project's own and that names nothing they rest on."""
from openferment_core.engine import WorkerEngine


class _Own(WorkerEngine):
    things_are = "a placeholder kind of thing a project holds"


ENGINE = _Own(name="h1g-things-are", worker="h1probe.worker", distributions=("openferment-engine-h1probe",))
