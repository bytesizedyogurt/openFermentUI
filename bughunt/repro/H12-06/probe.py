"""Probe for H12-06: import the service as uvicorn does (openferment_core.api), read which retired entry a kept
reference run came from (proforma.retired_entry_of, which the run readers, the Proforma tools and pureOS call), and
print which of the worker libraries (workers.WORKER_LIBRARIES) then stand in this, the service's, process."""
import sys
from types import SimpleNamespace

import openferment_core
from openferment_core import api, proforma  # noqa: F401  (the service's process, as uvicorn imports it)
from openferment_core.workers import WORKER_LIBRARIES

print("probe: openferment_core from", openferment_core.__file__)
before = sorted({m.split(".")[0] for m in sys.modules} & set(WORKER_LIBRARIES))
print("probe: worker libraries after importing the service:", before)
art = SimpleNamespace(tool=proforma.REFERENCE, inputs=[], output={"flowsheet": "corn_drygrind"})
print("probe: retired entry of a kept reference run:", proforma.retired_entry_of(art))
after = sorted({m.split(".")[0] for m in sys.modules} & set(WORKER_LIBRARIES))
print("probe: worker libraries after retired_entry_of:", after)
print("PROBE-SEEN " + ",".join(after))
