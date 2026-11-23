"""H1-07's stand-in engine object, registered under `openferment.engines` by run.sh's dist-info.

`h107` lists two things of the one id `dup`: the first states precision rtol 0, atol 0, the second
rtol 1, atol 1. A third thing, `single`, of precision 0 and 0, is the control in the same engine."""
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="h107", worker="h107standin.worker", distributions=("openferment-engine-h107",),
                      timeout_s=20.0)
