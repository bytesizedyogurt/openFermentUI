"""Probe for N09: after the service reads which retired entry a kept reference run came from
(proforma.retired_entry_of, called by the run readers), which of BioSTEAM, thermosteam and biorefineries stand in
the service's own process. On the head: none. With N09: all three."""
import sys
from types import SimpleNamespace

from openferment_core import api, proforma  # noqa: F401  (the service's process, as uvicorn imports it)

art = SimpleNamespace(tool=proforma.REFERENCE, inputs=[], output={"flowsheet": "corn_drygrind"})
print("retired entry:", proforma.retired_entry_of(art))
print("heavy modules in the service process:",
      sorted({m.split(".")[0] for m in sys.modules if m.split(".")[0] in ("biosteam", "thermosteam", "biorefineries")}))
