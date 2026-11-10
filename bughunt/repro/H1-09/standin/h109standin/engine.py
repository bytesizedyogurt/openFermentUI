"""H1-09's stand-in engine object, registered under `openferment.engines` by run.sh's dist-info.

`h109` runs two things: `extra`, whose one output carries a fourth key `stray` beside its name, value
and unit, and `nounit`, the control, whose one output lacks its unit."""
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="h109", worker="h109standin.worker", distributions=("openferment-engine-h109",),
                      timeout_s=20.0)
