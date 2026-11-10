"""P-02's rule alone: biorepo.provenance_of on verified decisions with no gold value that differ only in their label."""
from openferment_core import biorepo
from openferment_core.models import ReviewDecision

for label in ("verified", "gold", "curated", "unverified"):
    d = ReviewDecision(status="verified", provenance=label, gold=None, reviewer="Ada Moreno", recordId="r",
                       at="2026-11-10T00:00:00Z")
    print(f"SERVICE provenance_of(verified, label {label!r}, gold None) = {biorepo.provenance_of(d)}")
