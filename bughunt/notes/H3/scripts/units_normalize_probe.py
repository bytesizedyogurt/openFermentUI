"""H3: what units.normalize makes of spellings a paper or a bench writes.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/units_normalize_probe.py
Read-only: it imports openferment_core and prints.
"""
from openferment_core import units

PROBES = [
    # case folding onto another prefix
    ("Mg", "megagram (tonne)"), ("Mg/d", "megagrams per day"), ("ML", "megalitre"), ("Mm", "megametre"),
    ("MM", "?"), ("S", "siemens"), ("mS", "millisiemens"), ("G", "gauss / giga"), ("Kg", "kilogram"),
    ("KG", "kilogram"), ("MG", "?"), ("UM", "?"), ("um", "micrometre in ASCII"), ("uM", "micromolar"),
    ("M", "molar"), ("m", "metre"), ("C", "coulomb / Celsius"), ("F", "farad / Fahrenheit"),
    # labelled mass ratios that are no mass ratio
    ("g/gal", "grams per gallon"), ("gal/g", "gallons per gram"), ("g/gmol", "grams per gram-mole (molar mass)"),
    ("gmol/g", "gram-moles per gram"), ("g gal-1", "grams per gallon"), ("gal g-1", "gallons per gram"),
    ("g/gL", "?"), ("g/glucose", "g per g glucose"), ("g EtOH/g glucose", "g per g"),
    ("g/gDW", "g per g dry weight"), ("gpm/gpm", "gallons per minute ratio"), ("g/gpm", "grams per gpm"),
    ("g/gram", "g per g"), ("g/g dry", "?"),
    # weight percent
    ("wt%", "weight percent"), ("% (w/w)", "weight percent"), ("% w/w", "weight percent"),
    # empty and blank
    ("", "no unit"), ("   ", "blank"),
    # micro sign vs Greek mu
    ("µg/mL", "micro sign"), ("μg/mL", "greek mu"), ("μm", "greek mu metre"),
]

for raw, meant in PROBES:
    n = units.normalize(raw)
    fam = units.tables()["table"][n]["family"] if n is not None else None
    print(f"{raw!r:24} meant {meant:34} -> {n!r:22} family {fam}")

print()
for v, a, b in [(1, "Mg", "kg"), (1, "g/gal", "g/g"), (180.16, "g/gmol", "g g⁻¹"), (1, "gal/g", "kg kg⁻¹"),
                (5, "% DW", "% of native sites"), (5, "% v/v", "% DW"), (35, "wt%", "% CDW"),
                (5, "% DW", "% v/v")]:
    try:
        print(f"convert({v}, {a!r}, {b!r}) = {units.convert(v, a, b)!r}")
    except units.UnitError as e:
        print(f"convert({v}, {a!r}, {b!r}) refused: {e} | reason {e.reason}")
print("explain_refusal('% TSP', '% DW') =", units.explain_refusal("% TSP", "% DW"))
