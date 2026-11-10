"""H3: a candidate's free-text fields and Rule 1. anchor_candidate holds carbonSource to the cited section's
words and to find_number (dropped and counted otherwise); method and organism, written by the extractor too,
pass with numbers the section does not hold.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/candidate_free_text.py
"""
from openferment_core.validate import anchor_candidate

sentence = "The final ethanol titre was 45 g/L after fermentation."
sections = [{"id": "s1", "text": "Results. " + sentence}]
raw = {"sectionId": "s1", "field": "ethanol_titre", "value": 45, "unit": "g/L", "quote": sentence,
       "method": "HPLC; a repeat at 30 °C reached 85 g/L in 48 h",
       "organism": "a strain that made 85 g/L in fed-batch",
       "carbonSource": "glucose at 120 g/L"}
drops = []
cand, rule, detail = anchor_candidate(raw, sections, paper_id="P1", field_drops=drops)
print("anchored:", cand is not None, rule, detail)
print("method kept:", repr(cand.method))
print("organism kept:", repr(cand.organism))
print("carbonSource kept:", repr(cand.carbonSource), "| drops:", drops)
