"""H3-02: validate.find_number lets numbers written in words through, and validate_plan keeps the claim
with its cited record's class (verified).

Pure functions from the tree as it stands: find_number, validate_plan, and the real evidence pool
(evidence_pool.build) over one candidate a named reviewer verified, its class computed by
biorepo.provenance_of. No database, no service, no model, no network.

  bh_env core/.venv/bin/python -I bughunt/repro/H3-02/repro.py
"""
from openferment_core import biorepo, evidence_pool
from openferment_core.models import Candidate, Quantity, ReviewDecision
from openferment_core.postdoc_agent import held_to_rule_one
from openferment_core.validate import SeenSet, find_number, validate_plan

# (sentence with a number in words, the same quantity in a form the rule catches)
PAIRS = [
    ("The minimum selling price was two dollars per gallon in the base case.",
     "The minimum selling price was 2 dollars per gallon in the base case."),
    ("Ten per cent of the sugar was lost to by-products.",
     "Ten percent of the sugar was lost to by-products."),
    ("Ten tonnes of stover were fed each day.",
     "Ten kilograms of stover were fed each day."),
    ("Two thirds of the glucan was converted to ethanol.",
     "Half of the glucan was converted to ethanol."),
    ("Hundreds of litres of broth were made.",
     "A hundred litres of broth were made."),
    ("The yield was ² of theory.",          # superscript two, which validate.py:57-59 names as covered
     "The yield was ½ of theory."),
]
# The three forms practice.py:73-76 names as find_number's gaps (checked for practice drafts alone).
NAMED_IN_PRACTICE = [
    "Ethanol was made at pH5 throughout.",
    "The titre improved x10 over the parent.",
    "The titre doubled when the strain was switched.",
]

print("[1] find_number, word form beside its caught twin")
pair_fail = 0
for words, twin in PAIRS:
    w, t = find_number(words), find_number(twin)
    bad = w is None and t is not None
    pair_fail += bad
    print(f"  {'PASSES' if w is None else 'caught ' + repr(w):14} | twin {'caught ' + repr(t) if t else 'PASSES':14} | {words}")
for s in NAMED_IN_PRACTICE:
    print(f"  {'PASSES' if find_number(s) is None else 'caught':14} | (named in practice.py:73-76)   | {s}")

# One candidate a reviewer verified against the paper's words: the pool computes its class.
AT = "2026-11-10T00:00:00Z"
cand = Candidate(id="r1", paperId="P1", sectionId="s1",
                 quote="The minimum ethanol selling price in the base case is shown in the table.",
                 field="minimum_selling_price", value=0.72, unit="USD kg⁻¹",
                 si=Quantity(value=0.72, unit="USD kg⁻¹"))
dec = ReviewDecision(status="verified", provenance="verified", reviewer="A. Reviewer", recordId="r1", at=AT)
pool = evidence_pool.build([cand], {"r1": dec})
print(f"\n[2] the pool's record r1: value {pool.record('r1')['value']} {pool.record('r1')['unit']}, "
      f"class {pool.record('r1')['provenance']} (biorepo.provenance_of: {biorepo.provenance_of(dec)})")

seen = SeenSet(records={"r1"})
claims = [{"id": f"w{i + 1}", "text": w, "recordIds": ["r1"]} for i, (w, _) in enumerate(PAIRS)]
claims += [{"id": f"d{i + 1}", "text": t, "recordIds": ["r1"]} for i, (_, t) in enumerate(PAIRS)]
res = validate_plan(claims, seen, pool, model="claude-test", at=AT)
kept = {c.id: c for c in res.claims}
print("\n[3] validate_plan (the call postdoc_agent.py:752 makes on the model's claims), each citing r1")
for c in claims:
    k = kept.get(c["id"])
    print(f"  {('KEPT ' + k.provenance) if k else 'dropped':14} {c['id']}: {c['text']}")
print(f"  rejected {res.rejected}: " + "; ".join(res.reasons))

gaps, _ = held_to_rule_one(["Two thirds of the plant's cost has no record behind it."], None, [])
print(f"\n[4] held_to_rule_one keeps the gap: {gaps}")

words_kept = [c["id"] for c in claims if c["id"].startswith("w") and c["id"] in kept and kept[c["id"]].provenance == "verified"]
twins_dropped = [c["id"] for c in claims if c["id"].startswith("d") and c["id"] not in kept]
print(f"\nH302_COUNTS: word-form claims kept as verified {len(words_kept)}/{len(PAIRS)} ({', '.join(words_kept)}); "
      f"twins dropped and counted {len(twins_dropped)}/{len(PAIRS)}; rejected {res.rejected}; pairs passing find_number {pair_fail}/{len(PAIRS)}")
verdict = "DEFECT" if words_kept and len(twins_dropped) == len(PAIRS) and res.rejected == len(PAIRS) else "NO-DEFECT"
print(f"H302_VERDICT: {verdict}")
