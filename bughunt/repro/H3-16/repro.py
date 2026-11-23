"""H3-16: a unit written with the Greek small letter mu (U+03BC) does not normalise, so a candidate quoting it
is refused on rule 'unit'; the same unit written with the micro sign (U+00B5) anchors.

  bh_py bughunt/repro/H3-16/repro.py http://127.0.0.1:<port>      (run.sh starts the service)

Part 1 is the unit engine alone (pure functions on the tree's code). Part 2 is the service: one project, two
pasted documents (one sentence each, one spelling of micro each), and biorepo_write's `candidate` action at
the HTTP tool door in the model's lane, each candidate's unit copied as the document wrote it, the way the
extractor is told to ("Give the unit as the paper wrote it", extract.py:111). No model is called and nothing
leaves 127.0.0.1.
"""
import sys
import unicodedata

import httpx

from openferment_core import units

MU, MICRO = "μ", "µ"

print("== part 1: units.normalize on each spelling ==")
print(f"unicodedata.normalize('NFKC', U+00B5) = U+{ord(unicodedata.normalize('NFKC', MICRO)):04X}"
      f"   (Unicode's compatibility form of the micro sign is the Greek small letter mu)")
pairs = [("g/mL", "g mL⁻¹"), ("g/L", "g L⁻¹"), ("L", "L"), ("M", "mol L⁻¹"), ("l", "L"),
         ("mol/m²/s", "mol m⁻² s⁻¹"), ("g mL⁻¹", "g mL⁻¹")]
unit_split = []
for tail, _ in pairs:
    a, b = units.normalize(MICRO + tail), units.normalize(MU + tail)
    unit_split.append(a is not None and b is None)
    print(f"  micro sign {MICRO + tail!r:16} -> {a!r:18}   Greek mu {MU + tail!r:16} -> {b!r}")
try:
    units.convert(150, MU + "g/mL", "g L⁻¹")
    conv = "converted"
except units.UnitError as e:
    conv = f"UnitError: {e}"
print(f"  units.convert(150, 'μg/mL', 'g L⁻¹') -> {conv}")
print(f"  table keys holding U+00B5: {sum(MICRO in k for k in units.tables()['table'])}; holding U+03BC: "
      f"{sum(MU in k for k in units.tables()['table'])}; alias keys holding U+00B5: "
      f"{sum(MICRO in k for k in units.tables()['aliases'])}; holding U+03BC: "
      f"{sum(MU in k for k in units.tables()['aliases'])}")

print()
print("== part 2: the service, biorepo_write candidate, the unit copied as each document wrote it ==")
O = sys.argv[1]
P = "h3-16"
c = httpx.Client(base_url=O, trust_env=False, timeout=180)
r = c.post("/api/projects", json={"id": P, "name": "H3-16", "by": "bughunt"})
print("project made:", r.status_code)
HP = {"X-OpenFerment-Project": P}
HA = {**HP, "X-OpenFerment-Assistant": "hunt-agent/0.1"}

docs = {}
for name, mu in (("greek", MU), ("micro", MICRO)):
    text = f"Secreted protein reached 150 {mu}g/mL in the supernatant after 72 h of induction."
    p = c.post("/api/intake/paste", headers=HP, json={"title": f"H3-16 {name} spelling", "text": text, "by": "bughunt",
                                                    "licenceClass": "unknown", "reason": "H3-16 reproduction"})
    pb = p.json()
    docs[name] = (pb.get("documentId"), text)
    print(f"paste ({name}: U+{ord(mu):04X}): {p.status_code} status={pb.get('status')!r} documentId={pb.get('documentId')!r}")


def candidate(doc: str, unit: str) -> tuple[int, dict]:
    did, text = docs[doc]
    w = c.post("/api/tools/biorepo_write", headers=HA, json={
        "action": "candidate", "target": did,
        "fields": {"paperId": did, "sectionId": "p0", "field": "titer_secreted", "value": "150", "unit": unit,
                   "quote": text},
        "note": "H3-16: the unit as the document wrote it"})
    return w.status_code, w.json()


results = {}
for label, doc, unit in (("greek doc, unit as written (U+03BC)", "greek", MU + "g/mL"),
                         ("micro doc, unit as written (U+00B5)", "micro", MICRO + "g/mL"),
                         ("greek doc, unit retyped with U+00B5 (workaround)", "greek", MICRO + "g/mL")):
    code, body = candidate(doc, unit)
    results[label] = body
    s = body.get("summary") or {}
    print(f"  {label}: HTTP {code}; error={body.get('error')!r}; state={s.get('state')!r} "
          f"candidateId={s.get('candidateId')!r}")

g_err = results["greek doc, unit as written (U+03BC)"].get("error") or ""
m_ok = (results["micro doc, unit as written (U+00B5)"].get("summary") or {}).get("state") == "proposed"
w_ok = (results["greek doc, unit retyped with U+00B5 (workaround)"].get("summary") or {}).get("state") == "proposed"
greek_refused_on_unit = "rule unit" in g_err and "does not normalise" in g_err

print()
print("EXPECTED: 'μg/mL' (U+03BC) normalises to 'µg mL⁻¹' as 'µg/mL' (U+00B5) does, the two spellings of one "
      "unit a paper prints, and a candidate copying the unit as the paper wrote it is proposed under either "
      "spelling")
print(f"OBSERVED: normalize gives a key for the micro sign and None for the Greek mu on "
      f"{sum(unit_split)} of {len(unit_split)} spellings; biorepo_write on the Greek-mu document answered "
      f"{g_err!r}; on the micro-sign document proposed={m_ok}; the Greek-mu quote with the unit retyped in U+00B5 "
      f"proposed={w_ok}")
print("RESULT: DEFECT" if (all(unit_split) and greek_refused_on_unit and m_ok) else "RESULT: NO-DEFECT")
