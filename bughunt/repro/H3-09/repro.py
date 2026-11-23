"""H3-09: the unit table files % DW, % v/v, % of native sites, % sedimentable, % of total expressed and
% of total protein in one family, `percent`, each at factor 1, so each converts into every other 1:1, while
the table's own refusal row (units.json:558) says percentages of different denominators are a category error
to compare. Run by run.sh with OPENFERMENT_DATABASE_URL naming a fresh, migrated test database.

Part A asks the unit engine (units.convert, units.explain_refusal, units.quantity_equals) about pairs of
percentages with different denominators, beside the refusal the table records for % TSP against % DW.
Part B sends one candidate for disruption_protein_yield (denominated in '% of total protein') through
validate.anchor_candidate in each of several percent units, beside the % TSP control. Part C keeps the
'% DW' candidate in a project of the fresh database, sends a reviewer's accept through biorepo.write, reads
the record back and puts it in the field's own unit with units.to_canonical. Part D prints the wt% alias,
which docs/PROGRESS.md:614 already records as an open debt. No service, no model call, no network.
"""
from __future__ import annotations

import sys

from openferment_core import biorepo, db, extract, projects, units
from openferment_core.literature import kit
from openferment_core.models import ExtractResponse, ProjectCreate, ReviewDecision, Usage
from openferment_core.validate import anchor_candidate

P, DOC, BY = "h3-09", "R1", "Repro H3-09"
FIELD = "disruption_protein_yield"

print("== Part A: the table and the unit engine ==")
t = units.tables()
rule = next(r for r in t["refusals"] if {r["a"], r["b"]} == {"proteinShare", "percent"})
print(f"refusal row {rule['a']} / {rule['b']}: {rule['because']!r}")
members = [(k, v["factor"]) for k, v in t["table"].items() if v["family"] == "percent"]
print(f"family 'percent' holds {len(members)} units: " + ", ".join(f"{k!r} (factor {f})" for k, f in members))

# The control: the pair the refusal row is written for.
try:
    units.convert(5, "% TSP", "% DW")
    ctl_refused, ctl_reason = False, None
    print("control  convert(5, '% TSP', '% DW') returned a number")
except units.UnitError as e:
    ctl_refused, ctl_reason = True, e.reason
    print(f"control  convert(5, '% TSP', '% DW') raises UnitError, reason {e.reason!r}")

# Pairs whose denominators differ as plainly as the refusal row's: dry weight, a volume of solution,
# native phosphorylation sites, the sedimentable fraction, total protein.
PAIRS = [("% DW", "% of native sites"), ("% v/v", "% DW"), ("% DW", "% of total protein"),
         ("% of native sites", "% of total protein"), ("% sedimentable", "% v/v"),
         ("% v/v", "% of total expressed")]
converted = []
for a, b in PAIRS:
    try:
        out = units.convert(5, a, b)
        why = units.explain_refusal(a, b)
        converted.append((a, b))
        print(f"probe    convert(5, {a!r}, {b!r}) = {out!r}; explain_refusal = {why!r}")
    except units.UnitError as e:
        print(f"probe    convert(5, {a!r}, {b!r}) raises UnitError: {e} | reason {e.reason!r}")
eq = units.quantity_equals((5, "% DW"), (5, "% of native sites"))
print(f"probe    quantity_equals((5, '% DW'), (5, '% of native sites')) = {eq} (witness.py:85 and :117 read this)")

print()
print(f"== Part B: validate.anchor_candidate, field {FIELD} ==")
spec = units.field(FIELD)
print(f"{FIELD}: canonicalUnit {spec['canonicalUnit']!r}; definition {spec['definition']!r}")
UNITS_B = ["% of total protein", "% DW", "% v/v", "% of native sites", "% TSP"]
SECTIONS = []
for i, u in enumerate(UNITS_B, 1):
    SECTIONS.append({"id": f"s{i}", "heading": "Results",
                     "text": f"Results. Bead milling for 10 min gave a value of 42 {u} in the lysate. Further text."})


def anchor(i, u, cid=None):
    quote = f"Bead milling for 10 min gave a value of 42 {u} in the lysate."
    raw = {"sectionId": f"s{i}", "field": FIELD, "value": 42, "unit": u, "quote": quote, "method": "bead mill"}
    return anchor_candidate(raw, SECTIONS, paper_id=DOC, candidate_id=cid)


anchored = {}
for i, u in enumerate(UNITS_B, 1):
    cand, rule_b, detail = anchor(i, u, cid=f"cl1-R1-0000000{i}")
    anchored[u] = cand
    if cand is not None:
        print(f"42 {u!r:22} ANCHORED as {cand.value} {cand.unit}, valueBasis {cand.valueBasis!r}")
    else:
        print(f"42 {u!r:22} refused on rule {rule_b!r}: {detail}")

print()
print("== Part C: biorepo.write in a fresh database, the '% DW' candidate ==")
stored = canon = None
dw = anchored.get("% DW")
if dw is not None:
    projects.create(ProjectCreate(id=P, name="Repro H3-09", by=BY))

    def passages(document_id):
        if document_id != DOC:
            raise extract.NothingToAnchor(f"this project holds no document {document_id}")
        return SECTIONS

    extract.passages = passages  # the kit's passages for R1, as the suite's held_documents fixture serves them

    with projects.using(P):
        db.run(kit._link(P, DOC, {}, BY))
        extract._persist(ExtractResponse(paperId=DOC, extractedAt="2026-11-10T12:00:00Z",
                                         candidates=[dw], audit=[], usage=Usage(), calls=0))
        d = ReviewDecision(status="verified", provenance="curated", reviewer=BY, recordId=dw.id,
                           at="2026-11-10T12:00:00Z")
        try:
            s = biorepo.write(d)
            stored = s.provenance
            print(f"accept {dw.id}: stored, provenance {s.provenance!r}")
        except biorepo.WriteRefused as e:
            print(f"accept {dw.id}: refused: {e}")
        standing = biorepo.read()
        rec = next((r for r in standing.records if r.id == dw.id), None)
        if rec is not None:
            canon = units.to_canonical(float(rec.value), rec.unit, FIELD)
            print(f"BioRepo: {rec.id}  field {rec.field}  value {rec.value} {rec.unit}  quote {rec.quote!r}")
            print(f"to_canonical({rec.value}, {rec.unit!r}, {FIELD!r}) = {canon!r} {spec['canonicalUnit']}")
else:
    print("skipped: the '% DW' candidate did not anchor")

print()
print("== Part D: the wt% alias (recorded as an open debt, docs/PROGRESS.md:614) ==")
for s in ("wt%", "% (w/w)"):
    print(f"normalize({s!r}) = {units.normalize(s)!r}, family {units.family(s)!r}")
try:
    units.convert(35, "wt%", "% DW")
    print("convert(35, 'wt%', '% DW') returned a number")
except units.UnitError as e:
    print(f"convert(35, 'wt%', '% DW') raises UnitError: {e} | reason {e.reason!r}")

defect = (ctl_refused and ctl_reason == rule["because"] and len(converted) == len(PAIRS) and eq
          and anchored.get("% of total protein") is not None and anchored.get("% TSP") is None
          and anchored.get("% DW") is not None and anchored.get("% v/v") is not None
          and anchored.get("% of native sites") is not None and stored == "verified" and canon == 42.0)
print()
print("EXPECTED: by the table's own refusal row (units.json:558, 'Both are percentages but of different "
      "denominators ... Comparing them directly is a category error'), convert raises UnitError with a reason "
      "for % DW against % of native sites, % v/v against % DW and the other pairs of different denominators, "
      "as it does for % TSP against % DW; quantity_equals((5, '% DW'), (5, '% of native sites')) is False; "
      "anchoring refuses 42 '% DW', '% v/v' and '% of native sites' for disruption_protein_yield "
      "('% of total protein') on rule 'unit', as it refuses 42 '% TSP'")
print(f"OBSERVED: control % TSP -> % DW {'refused with the category-error reason' if ctl_refused else 'CONVERTED'}; "
      f"{len(converted)} of {len(PAIRS)} pairs of different denominators convert 1:1 with no reason "
      f"({'; '.join(a + ' -> ' + b for a, b in converted)}); quantity_equals((5, '% DW'), (5, '% of native sites')) "
      f"= {eq}; disruption_protein_yield anchored 42 in "
      f"{', '.join(repr(u) for u in UNITS_B if anchored.get(u) is not None)} and refused "
      f"{', '.join(repr(u) for u in UNITS_B if anchored.get(u) is None)}; biorepo.write "
      f"{'stored the % DW record with provenance ' + repr(stored) if stored else 'did not store it'}, and "
      f"to_canonical reads it as {canon!r} % of total protein")
print("PYRESULT: DEFECT" if defect else "PYRESULT: NO-DEFECT")
sys.exit(0)
