"""H1-08's stand-in engine object, registered under `openferment.engines` by run.sh's dist-info.

`h108` runs one thing, `cfg`, whose configurations are "one" and " two " (a space on each side of
"two"), with "one" its default."""
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="h108", worker="h108standin.worker", distributions=("openferment-engine-h108",),
                      timeout_s=20.0)
