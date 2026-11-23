"""H3-01: anchoring (§2.4 rule 3) compares a quote's number bare when the quote's unit does not convert
into the candidate's, labels the match `converted`, and biorepo.write promotes such a record through the
same check. Run by run.sh with OPENFERMENT_DATABASE_URL naming a fresh, migrated test database.

Part A calls validate.anchor_candidate on one-section documents. Part B keeps two candidates part A
anchored and one control, in a project of the fresh database, and sends a reviewer's decisions through
biorepo.write; the document's passages are served through extract.passages the way the test suite's
`held_documents` fixture serves them (core/tests/conftest.py:162).
"""
from __future__ import annotations

import sys

from openferment_core import biorepo, db, extract, projects, units
from openferment_core.literature import kit
from openferment_core.models import ExtractResponse, ProjectCreate, Quantity, ReviewDecision, Usage
from openferment_core.validate import anchor_candidate

P, DOC, BY = "h3-01", "R1", "Repro H3-01"

# field, candidate value, candidate unit, the sentence (its unit as the paper wrote it)
CROSS = [
    ("minimum_selling_price", 2.15, "USD/kg", "The minimum ethanol selling price was 2.15 USD/gal in the base case."),
    ("ethanol_titre", 45, "g/L", "The final ethanol concentration was 45% (v/v) after fermentation."),
    ("ethanol_titre", 5, "g/L", "Ethanol reached 5 mol/L in the broth."),
    ("ethanol_yield_substrate", 0.45, "g/g", "The specific growth rate was 0.45 h-1 on glucose."),
    ("specific_oxygen_uptake", 2, "mmol/g/h", "The specific oxygen uptake rate was 2 mg/g/h in the run."),
    ("minimum_selling_price", 1.2, "USD/kg", "The minimum selling price was 1.2 EUR kg-1 for the product."),
]
# The same symptom through the unit-less branch: the parser reads no unit in '$2.15/gal'.
UNITLESS = ("minimum_selling_price", 2.15, "USD/kg", "The minimum ethanol selling price was $2.15/gal in the base case.")
# Control: a quote whose unit converts into the candidate's, at a value the conversion moves.
CONTROL = ("ethanol_titre", 45, "g/L", "The final ethanol concentration was 45 mg/L after fermentation.")


def anchor(field, value, unit, sentence, cid=None, section="s1"):
    sections = [{"id": section, "text": "Results. " + sentence + " Further text."}]
    raw = {"sectionId": section, "field": field, "value": value, "unit": unit, "quote": sentence,
           "method": "undetermined"}
    return anchor_candidate(raw, sections, paper_id=DOC, candidate_id=cid)


def convert_says(value, quote_unit, cand_unit):
    try:
        return f"converts to {units.convert(value, quote_unit, cand_unit)}"
    except units.UnitError as e:
        return f"UnitError: {e.reason or e}"


print("== Part A: validate.anchor_candidate ==")
from openferment_core.validate import normalize_text, normalize_unit, parse_quantities  # noqa: E402

cross_anchored = 0
for field, value, unit, sentence in CROSS:
    q = parse_quantities(normalize_text(sentence))[0]
    cand, rule, detail = anchor(field, value, unit, sentence)
    print(f"{field} = {value} {unit}  on  {sentence!r}")
    print(f"    the quote states {q.value} {q.unit!r}; units.convert({q.value}, {q.unit!r}, "
          f"{normalize_unit(unit)!r}): {convert_says(q.value, q.unit, normalize_unit(unit))}")
    if cand is not None:
        cross_anchored += cand.valueBasis == "converted"
        print(f"    ANCHORED as {cand.value} {cand.unit}, valueBasis {cand.valueBasis!r}")
    else:
        print(f"    refused on rule {rule!r}: {detail}")

field, value, unit, sentence = UNITLESS
cand, rule, detail = anchor(field, value, unit, sentence)
q = parse_quantities(normalize_text(sentence))[0]
print(f"{field} = {value} {unit}  on  {sentence!r}")
print(f"    the quote parses as {q.value} {q.unit!r}")
print(f"    {'ANCHORED as ' + str(cand.value) + ' ' + cand.unit + ', valueBasis ' + repr(cand.valueBasis) if cand else 'refused on rule ' + repr(rule)}")

field, value, unit, sentence = CONTROL
cand, rule, detail = anchor(field, value, unit, sentence)
control_refused = cand is None and rule == "value"
print(f"control: {field} = {value} {unit}  on  {sentence!r}")
print(f"    {'refused on rule ' + repr(rule) + ': ' + str(detail) if cand is None else 'ANCHORED ' + repr(cand.valueBasis)}")

print()
print("== Part B: biorepo.write in a fresh database ==")
projects.create(ProjectCreate(id=P, name="Repro H3-01", by=BY))
SECTIONS = [
    {"id": "s1", "heading": "Results", "text": "Results. " + CROSS[0][3] + " Further text."},
    {"id": "s2", "heading": "Results", "text": "Results. " + CROSS[1][3] + " Further text."},
    {"id": "s3", "heading": "Results", "text": "Results. " + CONTROL[3] + " Further text."},
]


def passages(document_id):
    if document_id != DOC:
        raise extract.NothingToAnchor(f"this project holds no document {document_id}")
    return SECTIONS


extract.passages = passages  # the kit's passages for R1, as the test suite's held_documents serves them

with projects.using(P):
    db.run(kit._link(P, DOC, {}, BY))
    price, _, _ = anchor_candidate(
        {"sectionId": "s1", "field": "minimum_selling_price", "value": 2.15, "unit": "USD/kg",
         "quote": CROSS[0][3], "method": "undetermined"}, SECTIONS, paper_id=DOC, candidate_id="cl1-R1-00000001")
    titre, _, _ = anchor_candidate(
        {"sectionId": "s2", "field": "ethanol_titre", "value": 45, "unit": "g/L", "quote": CROSS[1][3]},
        SECTIONS, paper_id=DOC, candidate_id="cl1-R1-00000002")
    # The control candidate: 45 mg/L read rightly as 0.045 g/L.
    ctl, _, _ = anchor_candidate(
        {"sectionId": "s3", "field": "ethanol_titre", "value": 0.045, "unit": "g/L", "quote": CONTROL[3]},
        SECTIONS, paper_id=DOC, candidate_id="cl1-R1-00000003")
    assert price and titre and ctl, "a candidate did not anchor"
    extract._persist(ExtractResponse(paperId=DOC, extractedAt="2026-11-10T12:00:00Z",
                                     candidates=[price, titre, ctl], audit=[], usage=Usage(), calls=0))
    print(f"kept candidates: {price.id} {price.value} {price.unit} ({price.valueBasis}); "
          f"{titre.id} {titre.value} {titre.unit} ({titre.valueBasis}); {ctl.id} {ctl.value} {ctl.unit} ({ctl.valueBasis})")

    def decide(rid, **kw):
        d = ReviewDecision(status="verified", provenance="curated", reviewer=BY, recordId=rid,
                           at="2026-11-10T12:00:00Z", **kw)
        try:
            s = biorepo.write(d)
            return f"stored, provenance {s.provenance!r}"
        except biorepo.WriteRefused as e:
            return f"refused: {e}"

    accept_price = decide(price.id)
    gold_titre = decide(titre.id, gold=Quantity(value=45, unit="g/L"))
    gold_ctl = decide(ctl.id, gold=Quantity(value=45, unit="g/L"))
    print(f"accept {price.id} (2.15 USD kg-1 on '2.15 USD/gal'): {accept_price}")
    print(f"gold 45 g/L on {titre.id} ('45% (v/v)'): {gold_titre}")
    print(f"control: gold 45 g/L on {ctl.id} ('45 mg/L'): {gold_ctl}")
    standing = biorepo.read()
    for rid, dec in sorted(standing.decisions.items()):
        rec = next((r for r in standing.records if r.id == rid), None)
        print(f"BioRepo: {rid}  status {dec.status}  provenance {dec.provenance}  "
              f"gold {dec.gold.value if dec.gold else None}  value {rec.value if rec else None} "
              f"{rec.unit if rec else ''}  quote {rec.quote if rec else None!r}")

defect = (
    cross_anchored == len(CROSS)
    and control_refused
    and accept_price.startswith("stored, provenance 'verified'")
    and gold_titre.startswith("stored, provenance 'gold'")
    and gold_ctl.startswith("refused")
)
print()
print("EXPECTED: each of the six candidates whose quote states its number in a unit that does not convert into "
      "the candidate's is refused on rule 'value', as the same-family control (45 g/L on '45 mg/L') is; "
      "biorepo.write refuses to promote 2.15 USD kg-1 on '2.15 USD/gal' and gold 45 g/L on '45% (v/v)'")
print(f"OBSERVED: {cross_anchored} of {len(CROSS)} cross-unit candidates ANCHORED with valueBasis 'converted' "
      f"(no conversion exists; units.convert refuses each pair), the '$2.15/gal' one 'exact'; control "
      f"{'refused' if control_refused else 'ANCHORED'}; biorepo.write: accept {accept_price}; gold on "
      f"'45% (v/v)' {gold_titre}; control gold {gold_ctl.split(':')[0]}")
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
sys.exit(0)
