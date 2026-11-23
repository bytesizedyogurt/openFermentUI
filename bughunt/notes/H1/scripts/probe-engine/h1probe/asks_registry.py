"""An entry module that asks the registry as it is imported, from its own thread, and from a thread it
starts and waits on; it records what each ask answered and how long it took."""
import threading
import time

from openferment_core.engine import WorkerEngine, registry

SEEN = {}
t0 = time.monotonic()
SEEN["own thread"] = (sorted(registry.found()), round(time.monotonic() - t0, 2))
t1 = time.monotonic()
box = []
th = threading.Thread(target=lambda: box.append(sorted(registry.found())))
th.start(); th.join()
SEEN["started thread"] = (box[0] if box else None, round(time.monotonic() - t1, 2))
ENGINE = WorkerEngine(name="h1f-asks-registry", worker="h1probe.worker", distributions=("openferment-engine-h1probe",))
