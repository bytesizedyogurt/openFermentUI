"""H3: anchoring (§2.4 rule 3, validate.anchor_candidate) takes a number the sentence states in a unit
that does not convert into the candidate's, compares it bare, and labels it `converted`.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/anchor_unit_mismatch.py
Pure functions, no database. biorepo.write re-anchors every promoted value (gold included) through the
same anchor_candidate, so the same sentences pass a reviewer's verified or gold decision.
"""
from openferment_core import units
from openferment_core.validate import anchor_candidate

CASES = [
    # field, value, unit the candidate claims, the sentence
    ("minimum_selling_price", 2.15, "USD/kg", "The minimum ethanol selling price was $2.15/gal in the base case."),
    ("ethanol_titre", 45, "g/L", "The final ethanol concentration was 45% (v/v) after fermentation."),
    ("ethanol_titre", 5, "g/L", "Ethanol reached 5 mol/L in the broth."),
    ("ethanol_yield_substrate", 0.45, "g/g", "The specific growth rate was 0.45 h-1 on glucose."),
    ("minimum_selling_price", 1.2, "USD/kg", "The minimum selling price was 1.2 EUR kg-1 for the product."),
    ("specific_oxygen_uptake", 2, "mmol/g/h", "The specific oxygen uptake rate was 2 mg/g/h in the run."),
    # control: a sentence in a unit that converts, at the wrong value, is refused
    ("ethanol_titre", 45, "g/L", "The final ethanol concentration was 45 mg/L after fermentation."),
]

for field, value, unit, sentence in CASES:
    sections = [{"id": "s1", "text": "Results. " + sentence + " Further text."}]
    raw = {"sectionId": "s1", "field": field, "value": value, "unit": unit, "quote": sentence,
           "method": "undetermined"}
    cand, rule, detail = anchor_candidate(raw, sections, paper_id="P1")
    if cand is not None:
        print(f"ANCHORED  {field} = {cand.value} {cand.unit} (valueBasis {cand.valueBasis!r}, si {cand.si.value} {cand.si.unit})")
    else:
        print(f"refused   {field} = {value} {unit}: {rule}: {detail}")
    print(f"          sentence: {sentence}")

print()
print("units.convert(2.15, 'USD gal⁻¹', 'USD kg⁻¹'):")
try:
    units.convert(2.15, "USD gal⁻¹", "USD kg⁻¹")
except units.UnitError as e:
    print("  refused:", e, "|", e.reason)
