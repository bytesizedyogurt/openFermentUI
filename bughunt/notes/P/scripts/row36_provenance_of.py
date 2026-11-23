"""Row 36: biorepo.provenance_of, the one rule the write and import_alpha1 compute a decision's class by, on two
verified decisions with no gold value that differ only in the label they carry."""
from openferment_core import biorepo
from openferment_core.models import ReviewDecision

for label in ("verified", "gold", "curated", "unverified"):
    d = ReviewDecision(status="verified", provenance=label, gold=None, reviewer="Ada Moreno", recordId="r", at="2026-11-10T00:00:00Z")
    print(f"verified, label {label!r}, gold None -> {biorepo.provenance_of(d)}")
