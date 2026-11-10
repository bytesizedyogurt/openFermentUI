"""H3: claims whose words state a number pass validate.validate_plan (Rule 1; ADR-006: "Text with a bare
number is still dropped and counted"), and an estimate's unit carries words with a number past every check.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/claims_with_numbers.py
Pure functions with a stand-in evidence pool; no database, no model.
"""
from openferment_core.validate import SeenSet, validate_plan


class Pool:
    def __init__(self, recs):
        self.recs = recs

    def record(self, rid):
        return self.recs.get(rid)


pool = Pool({"r1": {"id": "r1", "paperId": "P1", "value": 0.72, "unit": "USD kg⁻¹", "provenance": "verified"}})
seen = SeenSet(records={"r1"})
claims = [
    {"id": "c1", "text": "The minimum selling price was two dollars per gallon in the base case.", "recordIds": ["r1"]},
    {"id": "c2", "text": "Two thirds of the glucan was converted to ethanol.", "recordIds": ["r1"]},
    {"id": "c3", "text": "Conversion sat in the high-90s percent across the runs.", "recordIds": ["r1"]},
    {"id": "c4", "text": "The titre doubled when the strain was switched.", "recordIds": ["r1"]},
    {"id": "c5", "text": "Ten per cent of the sugar was lost to by-products.", "recordIds": ["r1"]},
    # control: digits are dropped
    {"id": "c6", "text": "The minimum selling price was 2 dollars per gallon.", "recordIds": ["r1"]},
    # an estimate whose unit field holds a number in words
    {"id": "c7", "text": "The selling price the model estimates for the plant.", "support": "unsupported",
     "values": [{"label": "selling price", "estimate": {"value": 2.1, "unit": "USD/gal, about 40 cents above the 2011 design",
                                                         "basis": "the design report's price structure"}}]},
]
res = validate_plan(claims, seen, pool, model="claude-test", at="2026-11-10T00:00:00Z")
kept = {c.id: c for c in res.claims}
for c in claims:
    k = kept.get(c["id"])
    if k:
        extra = ""
        if k.values:
            q = k.values[0].quantity
            extra = f" | value {q.value} unit {q.unit!r} origin {q.origin.kind}"
        print(f"KEPT    {c['id']} ({k.provenance}){extra}: {c['text']}")
    else:
        print(f"dropped {c['id']}: {c['text']}")
print("rejected:", res.rejected, res.reasons)
