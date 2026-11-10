"""Stand-in engine objects for H1's hunt."""
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="probe", worker="h1probe.worker", distributions=("openferment-engine-h1probe",),
                      timeout_s=6.0)
BADTHINGS = WorkerEngine(name="probe-badthings", worker="h1probe.worker_badthings",
                         distributions=("openferment-engine-h1probe",), timeout_s=6.0)
MIRROR_TOO = WorkerEngine(name="mirror", worker="h1probe.worker", distributions=("openferment-engine-h1probe",))
BIOSTEAM_TOO = WorkerEngine(name="biosteam", worker="h1probe.worker", distributions=("openferment-engine-h1probe",))
MISNAMED = WorkerEngine(name="something-else", worker="h1probe.worker", distributions=("openferment-engine-h1probe",))


class _NoReplay:
    name = "h1d-nomethod"
    worker = "h1probe.worker"
    heavy = ()

    def version(self): return {}
    def things(self): return []
    def parameters(self, thing, configuration): return []
    def run(self, thing, configuration, inputs, by): raise RuntimeError("no")
    def export_sff(self, run): return "none"


NOMETHOD = _NoReplay()
