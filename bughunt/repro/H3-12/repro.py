"""H3-12: anchor_candidate holds a candidate's carbonSource to the cited section and the number rule, and keeps
its method and organism as the extractor wrote them. This script shows the behaviour on the candidate's own
inputs, then reads what the tree itself says about each field, and computes whether the behaviour departs from
that contract. A pure function: no service, no key, no model call, no network.

  cd core && .venv/bin/python ../bughunt/repro/H3-12/repro.py
"""
from __future__ import annotations

import inspect

from openferment_core import models, validate
from openferment_core.validate import anchor_candidate, find_number

# ── 1. the candidate's own inputs (bughunt/notes/H3/scripts/candidate_free_text.py) ──────────────
sentence = "The final ethanol titre was 45 g/L after fermentation."
sections = [{"id": "s1", "text": "Results. " + sentence}]
raw = {"sectionId": "s1", "field": "ethanol_titre", "value": 45, "unit": "g/L", "quote": sentence,
       "method": "HPLC; a repeat at 30 °C reached 85 g/L in 48 h",
       "organism": "a strain that made 85 g/L in fed-batch",
       "carbonSource": "glucose at 120 g/L"}
drops: list[tuple[str, str]] = []
cand, rule, detail = anchor_candidate(raw, sections, paper_id="P1", field_drops=drops)
print("== 1. the behaviour, on the candidate's inputs ==")
print("anchored:", cand is not None, rule, detail)
assert cand is not None
print("value:", cand.value, cand.unit, "| the value stands in the quote:", "45 g/L" in cand.quote)
print("method kept:", repr(cand.method))
print("organism kept:", repr(cand.organism), "| organismText:", repr(cand.organismText))
print("carbonSource kept:", repr(cand.carbonSource), "| drops:", drops)
method_kept = cand.method == raw["method"]
organism_kept = cand.organism == raw["organism"]
carbon_dropped = cand.carbonSource is None and [d[0] for d in drops] == ["carbonSource"]
value_in_quote = "45 g/L" in cand.quote
behaviour = method_kept and organism_kept and carbon_dropped and value_in_quote
print("behaviour as the candidate states it (method and organism kept, carbonSource dropped):", behaviour)

# ── 2. what the tree says about each field ─────────────────────────────────────────────────────
print()
print("== 2. the contract as the tree writes it ==")
print("validate.FIELD_DROP_REASONS (the fields anchoring may drop from a kept candidate):",
      validate.FIELD_DROP_REASONS)
doc = " ".join((anchor_candidate.__doc__ or "").split())
drop_sentence = doc[doc.find("A candidate that anchors may still lose a field"):].split(". Each")[0]
print("anchor_candidate's docstring:", repr(drop_sentence))
src = inspect.getsource(models.Candidate)
lines = [ln.strip() for ln in src.splitlines()]
org_comment = " ".join(ln.lstrip("# ") for ln in lines
                       if ln.startswith("#") and ("organism" in ln or "wording" in ln or "extractor" in ln))
carbon_comment = " ".join(ln.lstrip("# ") for ln in lines
                          if ln.startswith("#") and ("cells were fed" in ln or "stand in the cited" in ln
                                                      or "the candidate kept" in ln))
print("models.Candidate on organism:", repr(org_comment))
print("models.Candidate on carbonSource:", repr(carbon_comment))
method_comment = [ln for ln in lines if ln.startswith("#") and "method" in ln.lower()]
print("models.Candidate comments naming method:", method_comment or "none")

drops_only_carbon = tuple(validate.FIELD_DROP_REASONS) == ("carbonSource",)
doc_names_carbon_alone = "a carbon source whose words are not in the cited section, or carry a number, is dropped" \
    in drop_sentence and "method" not in drop_sentence and "organism" not in drop_sentence
organism_kept_as_worded = "the wording otherwise" in org_comment
method_unheld = not method_comment
contract_holds_method_or_organism = not (drops_only_carbon and doc_names_carbon_alone
                                         and organism_kept_as_worded and method_unheld)
print("the tree holds method or organism to the section or the number rule:", contract_holds_method_or_organism)

# ── 3. what the candidate's expected rule would do to a paper's own words ──────────────────────
print()
print("== 3. find_number (the rule carbonSource passes) on wordings a paper writes ==")
for label, text in [
    ("organism", "Saccharomyces cerevisiae 424A(LNH-ST)"),
    ("organism", "Zymomonas mobilis 8b"),
    ("organism", "Pseudomonas putida KT2440"),
    ("method", "HPLC (Aminex HPX-87H, 65 °C)"),
    ("method", "absorbance at 600 nm"),
    ("method", "HPLC with refractive index detection"),
]:
    print(f"  {label:9s}{text!r:45s} find_number -> {find_number(text)!r}")

# ── verdict ────────────────────────────────────────────────────────────────────────────────────
print()
print("EXPECTED (the candidate): method and organism dropped and counted as carbonSource is, when they hold a "
      "number or stand outside the cited section")
print("EXPECTED (the tree's contract): the value 45 g/L inside its quote (CLAUDE.md:54); carbonSource dropped "
      "and counted (models.py:967-970, validate.py:859 FIELD_DROP_REASONS == ('carbonSource',)); organism kept as the "
      "extractor's wording when no strain resolves (models.py:962-964 'the wording otherwise'); method kept "
      "as given, held to presence alone where the field requires one (validate.py:1152-1157)")
print(f"OBSERVED: anchored {cand is not None}; value {cand.value} {cand.unit} in the quote {value_in_quote}; "
      f"method kept {cand.method!r}; organism kept {cand.organism!r}; carbonSource dropped "
      f"{carbon_dropped} ({drops[0][1] if drops else 'no drop'}); the tree holds method or organism to the "
      f"section or the number rule: {contract_holds_method_or_organism}")
if behaviour and contract_holds_method_or_organism:
    print("PYRESULT: DEFECT")
elif behaviour:
    print("PYRESULT: NO-DEFECT (the behaviour is the contract as the tree writes and tests it)")
else:
    print("PYRESULT: NO-DEFECT (the behaviour the candidate states did not occur)")
