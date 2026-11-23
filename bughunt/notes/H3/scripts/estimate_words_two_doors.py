"""H3: a model's estimate says what it rests on in words at two doors, and only one holds those words to
Rule 1. A claim's estimate whose `basis` holds a number is dropped (validate.claim_values); the same words
as a tool quantity's `note` (study_scenario, the one tool that takes quantities) pass numbers_in and are
stamped into the estimate's origin, where the run's basis keeps them ("estimated on <at>: <note>").

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/estimate_words_two_doors.py
Pure functions; no database, no model, no worker.
"""
from openferment_core import basis, tools
from openferment_core.models import Origin
from openferment_core.validate import SeenSet, claim_values

WORDS = "about 30% above the 2011 design report"

# The claim door.
vals, why = claim_values([{"label": "titre", "estimate": {"value": 50, "unit": "g L-1", "basis": WORDS}}],
                         SeenSet(), None, "claude-x", "2026-11-10T00:00:00Z")
print("claim door:", "dropped:" if why else "kept:", why or vals)

# The tool door (study_scenario's values[].quantity).
paths = tools._quantity_paths_of("study_scenario")
raw = {"title": "t", "plant": "cornstover", "values": [
    {"key": "x", "quantity": {"value": 50, "unit": "g L-1", "note": WORDS}}]}
print("tool door quantity paths:", sorted(paths))
print("tool door numbers_in:", tools.numbers_in(raw, quantities=paths) or "none found")
out = tools.stamped(raw, Origin(kind="model-estimate", by="claude-x", at="2026-11-10T00:00:00Z"), paths)
origin = out["values"][0]["quantity"]["origin"]
print("tool door stamped origin:", origin)
src = basis.estimate_source(origin["by"], origin["at"], origin.get("note"))
print("the run's basis source:", src.model_dump())
