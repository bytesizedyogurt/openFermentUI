"""H3-08: units.normalize reads a word starting with g (gal, gmol, gpm) as a labelled gram, so g/gal, gal/g,
g/gmol and their kin become the yield unit g g⁻¹ and convert 1:1. Run by run.sh with OPENFERMENT_DATABASE_URL
naming a fresh, migrated test database.

Part A asks the unit engine (units.normalize, units.convert) about the spellings, beside controls the
labelled-gram rule is written for. Part B sends one candidate in grams per gallon through
validate.anchor_candidate. Part C keeps that candidate in a project of the fresh database and sends a
reviewer's accept through biorepo.write, then reads the record back. No service, no model call, no network.
"""
from __future__ import annotations

import sys

from openferment_core import biorepo, db, extract, projects, units
from openferment_core.literature import kit
from openferment_core.models import ExtractResponse, ProjectCreate, ReviewDecision, Usage
from openferment_core.validate import anchor_candidate

P, DOC, BY = "h3-08", "R1", "Repro H3-08"

# The rule's own examples (units.py:104-105) and a plain g/g: each is a mass ratio and reads as g g⁻¹.
CONTROLS_YIELD = ["g/g", "g EtOH/g glucose", "gx/g", "gDW gglucose⁻¹", "g biomass [g glucose]⁻¹"]
# Units the engine does not hold: each reads as unknown.
CONTROLS_UNKNOWN = ["gal", "gmol", "gpm", "g/furlong"]
# Gallons, gram-moles and gallons per minute: none is a gram, and the engine holds none of them.
PROBES = ["g/gal", "gal/g", "g/gmol", "gmol/g", "g gal-1", "gal g-1", "g/gallon", "gpm/gpm", "g/gpm"]

print("== Part A: units.normalize and units.convert ==")
ctl_yield_ok = True
for s in CONTROLS_YIELD:
    n = units.normalize(s)
    ctl_yield_ok &= n == "g g⁻¹"
    print(f"control  normalize({s!r:28}) = {n!r}")
ctl_unknown_ok = True
for s in CONTROLS_UNKNOWN:
    n = units.normalize(s)
    ctl_unknown_ok &= n is None
    print(f"control  normalize({s!r:28}) = {n!r}")
misread = []
for s in PROBES:
    n = units.normalize(s)
    fam = units.family(s)
    if n == "g g⁻¹":
        misread.append(s)
    print(f"probe    normalize({s!r:28}) = {n!r}  family {fam!r}")
print(f"for comparison: normalize('g mol-1') = {units.normalize('g mol-1')!r} "
      f"family {units.family('g mol-1')!r}")

conversions = []
for v, a, b in [(180.16, "g/gmol", "g g⁻¹"), (1, "gal/g", "kg kg⁻¹"), (1, "g/gal", "mg g⁻¹")]:
    try:
        out = units.convert(v, a, b)
        conversions.append(True)
        print(f"convert({v}, {a!r}, {b!r}) = {out!r}")
    except units.UnitError as e:
        conversions.append(False)
        print(f"convert({v}, {a!r}, {b!r}) raises UnitError: {e}")

print()
print("== Part B: validate.anchor_candidate ==")
SENT = "The broth held 0.45 g/gal of residual ethanol at harvest."
CTRL = "The broth held 0.45 g/furlong of residual ethanol at harvest."
SECTIONS = [
    {"id": "s1", "heading": "Results", "text": "Results. " + SENT + " Further text."},
    {"id": "s2", "heading": "Results", "text": "Results. " + CTRL + " Further text."},
]


def anchor(section, unit, quote, cid=None):
    raw = {"sectionId": section, "field": "ethanol_yield_substrate", "value": 0.45, "unit": unit,
           "quote": quote, "method": "undetermined"}
    return anchor_candidate(raw, SECTIONS, paper_id=DOC, candidate_id=cid)


cand, rule, detail = anchor("s1", "g/gal", SENT, cid="cl1-R1-00000001")
anchored = cand is not None
print(f"ethanol_yield_substrate = 0.45 'g/gal' on {SENT!r}")
print(f"    {'ANCHORED as ' + str(cand.value) + ' ' + cand.unit + ', valueBasis ' + repr(cand.valueBasis) if cand else 'refused on rule ' + repr(rule) + ': ' + str(detail)}")
c2, r2, d2 = anchor("s2", "g/furlong", CTRL)
ctl_refused = c2 is None and r2 == "unit"
print(f"control: ethanol_yield_substrate = 0.45 'g/furlong' on {CTRL!r}")
print(f"    {'refused on rule ' + repr(r2) + ': ' + str(d2) if c2 is None else 'ANCHORED ' + repr(c2.valueBasis)}")

print()
print("== Part C: biorepo.write in a fresh database ==")
stored = None
if anchored:
    projects.create(ProjectCreate(id=P, name="Repro H3-08", by=BY))

    def passages(document_id):
        if document_id != DOC:
            raise extract.NothingToAnchor(f"this project holds no document {document_id}")
        return SECTIONS

    extract.passages = passages  # the kit's passages for R1, as the suite's held_documents fixture serves them

    with projects.using(P):
        db.run(kit._link(P, DOC, {}, BY))
        extract._persist(ExtractResponse(paperId=DOC, extractedAt="2026-11-10T12:00:00Z",
                                         candidates=[cand], audit=[], usage=Usage(), calls=0))
        d = ReviewDecision(status="verified", provenance="curated", reviewer=BY, recordId=cand.id,
                           at="2026-11-10T12:00:00Z")
        try:
            s = biorepo.write(d)
            stored = s.provenance
            print(f"accept {cand.id}: stored, provenance {s.provenance!r}")
        except biorepo.WriteRefused as e:
            print(f"accept {cand.id}: refused: {e}")
        standing = biorepo.read()
        for rid, dec in sorted(standing.decisions.items()):
            rec = next((r for r in standing.records if r.id == rid), None)
            print(f"BioRepo: {rid}  field {rec.field if rec else None}  status {dec.status}  "
                  f"provenance {dec.provenance}  value {rec.value if rec else None} {rec.unit if rec else ''}  "
                  f"quote {rec.quote if rec else None!r}")
else:
    print("skipped: the candidate did not anchor")

defect = (ctl_yield_ok and ctl_unknown_ok and len(misread) == len(PROBES) and all(conversions)
          and anchored and ctl_refused and stored == "verified")
print()
print("EXPECTED: normalize names a gram labelled by what it weighs (g EtOH/g glucose, gx/g, gDW gglucose⁻¹) "
      "g g⁻¹ and returns None for a spelling holding gallons (gal), gram-moles (gmol) or gallons per minute "
      "(gpm), as it does for 'gal', 'gmol', 'gpm' and 'g/furlong'; convert raises UnitError ('Unknown unit') "
      "for g/gmol, gal/g and g/gal; anchoring refuses 0.45 'g/gal' for ethanol_yield_substrate on rule 'unit', "
      "as it refuses 0.45 'g/furlong'")
print(f"OBSERVED: controls {'held' if ctl_yield_ok and ctl_unknown_ok else 'MOVED'}; {len(misread)} of "
      f"{len(PROBES)} probes normalise to 'g g⁻¹' ({', '.join(misread)}); convert returned a number for "
      f"{sum(conversions)} of 3 pairs (180.16 g/gmol = 180.16 g g⁻¹, 1 gal/g = 1 kg kg⁻¹, 1 g/gal = 1000 mg g⁻¹); "
      f"0.45 'g/gal' {'ANCHORED as 0.45 g g⁻¹ valueBasis ' + repr(cand.valueBasis) if anchored else 'refused'}, "
      f"control 'g/furlong' {'refused on rule unit' if ctl_refused else 'ANCHORED'}; biorepo.write "
      f"{'stored it with provenance ' + repr(stored) if stored else 'did not store it'}")
print("PYRESULT: DEFECT" if defect else "PYRESULT: NO-DEFECT")
sys.exit(0)
