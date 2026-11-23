"""H1-06's stand-in engine objects, registered under `openferment.engines` by run.sh's dist-info.

`h106` states an infinite absolute precision for its thing `infprec` (the defect's case) beside a thing
`fine` of precision 0 and 0 (a control in the same engine). `h106neg` states a negative absolute
precision (a control: a things answer outside the shape the service does refuse)."""
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="h106", worker="h106standin.worker", distributions=("openferment-engine-h106",),
                      timeout_s=20.0)
NEG = WorkerEngine(name="h106neg", worker="h106standin.worker_neg", distributions=("openferment-engine-h106",),
                   timeout_s=20.0)
