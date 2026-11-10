"""H3: a unit written with the Greek small letter mu (U+03BC), as text extracted from many PDFs carries it,
beside the micro sign (U+00B5) the unit table keys use.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/greek_mu.py
"""
from openferment_core import units
from openferment_core.validate import anchor_candidate

for u in ("µg/mL", "μg/mL", "µmol/m2/s", "μmol/m2/s", "μL", "μM"):
    print(f"{u!r:16} U+{ord(u[0]):04X} -> {units.normalize(u)!r}")
for mu in ("µ", "μ"):
    s = f"Secreted protein reached 150 {mu}g/mL in the supernatant."
    cand, rule, detail = anchor_candidate({"sectionId": "s1", "field": "titer_secreted", "value": 150, "unit": f"{mu}g/mL",
                                           "quote": s}, [{"id": "s1", "text": s}], paper_id="P1")
    print(f"U+{ord(mu):04X}: anchored={cand is not None} rule={rule} {detail or ''}")
