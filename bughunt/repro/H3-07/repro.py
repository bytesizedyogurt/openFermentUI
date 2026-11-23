"""H3-07: units.normalize folds an upper-case SI prefix onto the lower-case one.

Run by run.sh with the repository's Python (bh_py), keyless:
  repro.py ORIGIN
Part A asks the unit engine (units.normalize, units.family, units.convert,
units.quantity_equals) about spellings whose case names a different SI unit:
Mg (megagram), ML (megalitre), Mm (megametre), MG, S (siemens), G (gauss or
giga). The engine's table holds none of these units. Controls: the table's own
keys, the spellings the fixture folds on purpose ('G L-1', 'KDa'), and 'Mg/d',
which the engine refuses. Part B keeps a lesson at the catalogue door
(POST /api/catalogues/lesson) whose numeric answer is 2 Mg, reads it back, and
sends a 'Mg/d' answer as the control.
Prints EXPECTED:, OBSERVED: and one PYRESULT: line.
"""
from __future__ import annotations

import sys

import httpx

from openferment_core import units

ORIGIN = sys.argv[1]
table = units.tables()["table"]


def norm(s: str) -> tuple[str | None, str | None]:
    n = units.normalize(s)
    return n, (table[n]["family"] if n is not None else None)


def conv(v: float, a: str, b: str) -> str:
    try:
        return repr(units.convert(v, a, b))
    except units.UnitError as e:
        return f"UnitError({e})"


print("== Part A: the unit engine (core/openferment_core/units.py) ==")
print("controls:")
for s in ["mg", "mL", "mm", "s", "g", "t d⁻¹", "Mg/d", "ML/d", "furlongs", "G L-1", "KDa"]:
    n, f = norm(s)
    print(f"  normalize({s!r:10}) = {n!r:16} family {f}")

# Each probe: the spelling, the SI unit it names, and the table key a fold would land on.
PROBES = [
    ("Mg", "megagram (10^6 g, a tonne)"),
    ("MG", "megagram, upper case"),
    ("ML", "megalitre (10^6 L)"),
    ("Mm", "megametre (10^6 m)"),
    ("MM", "megamolar"),
    ("S", "siemens"),
    ("G", "gauss, or the giga prefix alone"),
]
folded = []
print("probes (each names a unit the table does not hold):")
for s, meant in PROBES:
    n, f = norm(s)
    print(f"  normalize({s!r:10}) = {n!r:16} family {f!s:8}  ({s} is {meant})")
    if n is not None:
        folded.append(f"{s}->{n}")

print("conversions:")
c_mg = conv(1, "Mg", "kg")
c_ml = conv(1, "ML", "L")
c_mg2 = conv(2, "Mg", "g")
c_mgd = conv(1, "Mg/d", "kg d⁻¹")
print(f"  convert(1, 'Mg', 'kg')       = {c_mg}   (a megagram is 1000 kg)")
print(f"  convert(2, 'Mg', 'g')        = {c_mg2}   (2 Mg is 2e6 g)")
print(f"  convert(1, 'ML', 'L')        = {c_ml}   (a megalitre is 1e6 L)")
print(f"  convert(1, 'Mg/d', 'kg d⁻¹') = {c_mgd}")

print("checkpoint grading (units.quantity_equals, the Python twin of src/engine/units.ts quantityEquals):")
q_right = units.quantity_equals((2000, "kg"), (2, "Mg"), 5)
q_wrong = units.quantity_equals((2, "mg"), (2, "Mg"), 5)
print(f"  quantity_equals((2000, 'kg'), (2, 'Mg'), 5) = {q_right}   (2000 kg is 2 Mg)")
print(f"  quantity_equals((2, 'mg'),    (2, 'Mg'), 5) = {q_wrong}   (2 mg is 2e-9 Mg)")

print()
print("== Part B: the lesson catalogue's door (POST /api/catalogues/lesson) ==")
c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=60)
H = {"X-OpenFerment-Project": "h3-07"}


def lesson(lid: str, unit: str) -> dict:
    return {"kind": "lesson", "id": lid, "name": f"Batch mass in {unit}", "minutes": 5, "checkpoint": [
        {"id": "q1", "prompt": "How heavy is the dry stover batch?", "kind": "numeric",
         "answer": {"value": 2, "unit": unit, "tolerancePct": 5}}]}


r = c.post("/api/catalogues/lesson", json={"entry": lesson("l-mg", "Mg"), "by": "Ada Lovelace"}, headers=H)
keep_mg = r.status_code
print(f"  keep a lesson whose answer is 2 Mg:   HTTP {keep_mg}")
back = c.get("/api/catalogues/lesson/l-mg", headers=H)
kept_unit = None
if back.status_code == 200:
    body = back.json()
    entry = body.get("entry", body)
    try:
        kept_unit = entry["checkpoint"][0]["answer"]["unit"]
    except (KeyError, IndexError, TypeError):
        kept_unit = None
print(f"  read it back: HTTP {back.status_code}, answer unit kept {kept_unit!r}, "
      f"which the engine reads as {units.normalize(kept_unit) if kept_unit else None!r}")
r2 = c.post("/api/catalogues/lesson", json={"entry": lesson("l-mgd", "Mg/d"), "by": "Ada Lovelace"}, headers=H)
keep_mgd = r2.status_code
detail = r2.text[:220].replace("\n", " ")
print(f"  control, an answer of 2 Mg/d:         HTTP {keep_mgd}  {detail}")

print()
print("EXPECTED: 'Mg', 'MG', 'ML', 'Mm', 'MM', 'S' and 'G' name units the table holds no key for, so normalize returns "
      "None for each and convert raises UnitError ('Unknown unit'), as it does for 'Mg/d' "
      "(units.py:24-27 'An unknown unit is UnitError ... Nothing here invents a conversion factor'); "
      "the lesson door refuses a 2 Mg answer with a 422, as it refuses 2 Mg/d")
print(f"EXPECTED: were megagram held, convert(1, 'Mg', 'kg') = 1000.0 and 2000 kg grades as 2 Mg")
print(f"OBSERVED: {len(folded)} of {len(PROBES)} probes fold onto another unit: {', '.join(folded)}")
print(f"OBSERVED: convert(1, 'Mg', 'kg') = {c_mg}; convert(1, 'ML', 'L') = {c_ml}; "
      f"convert(1, 'Mg/d', 'kg d⁻¹') = {c_mgd}")
print(f"OBSERVED: quantity_equals((2000,'kg'),(2,'Mg'),5) = {q_right}; quantity_equals((2,'mg'),(2,'Mg'),5) = {q_wrong}")
print(f"OBSERVED: POST /api/catalogues/lesson keeps an answer of 2 Mg (HTTP {keep_mg}, unit kept {kept_unit!r}) "
      f"and refuses 2 Mg/d (HTTP {keep_mgd})")

defect = (units.normalize("Mg") == "mg" and c_mg == repr(1e-06) and units.normalize("ML") == "mL"
          and units.normalize("Mg/d") is None)
print("PYRESULT: DEFECT" if defect else "PYRESULT: NO-DEFECT")
