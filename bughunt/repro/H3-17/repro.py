"""H3-17: a person's keep of a strain with a field no kind takes (titre) at POST /api/catalogues/strain.

  python -I repro.py ORIGIN
Prints the steps and one line H317_VERDICT: DEFECT|NO-DEFECT <words>.
"""
import json
import sys

import httpx

O = sys.argv[1]
c = httpx.Client(base_url=O, trust_env=False, timeout=60)
H = {"X-OpenFerment-Project": "p1"}

# Control: a field of another kind (a species on a product) is refused by the route with a 422.
r0 = c.post("/api/catalogues/product", headers=H, json={
    "entry": {"kind": "product", "id": "p-h317", "name": "H3-17 product", "species": "Saccharomyces cerevisiae"},
    "by": "Ada Lovelace"})
print(f"control, a species on a product: {r0.status_code} {r0.text[:220]}")

# The case: a strain carrying `titre`, a field no kind takes, here a quantity whose origin is a model's estimate.
est = {"value": 45, "unit": "g/L", "origin": {"kind": "model-estimate", "by": "claude-x", "at": "2026-11-09"}}
r1 = c.post("/api/catalogues/strain", headers=H, json={
    "entry": {"kind": "strain", "id": "s-h317", "name": "H3-17 strain", "titre": est}, "by": "Ada Lovelace"})
body1 = r1.json() if r1.headers.get("content-type", "").startswith("application/json") else {}
print(f"keep, a titre on a strain: {r1.status_code}; answer names titre: {'titre' in r1.text}; "
      f"answer's keys: {sorted(body1) if isinstance(body1, dict) else body1}")
if r1.status_code == 422:
    print(f"   refusal: {r1.text[:300]}")

r2 = c.get("/api/catalogues/strain/s-h317", headers=H)
print(f"read back /api/catalogues/strain/s-h317: {r2.status_code}; holds titre: {'titre' in r2.text}; "
      f"by={r2.json().get('by') if r2.status_code == 200 else None!r}")

control_ok = r0.status_code == 422
if r1.status_code == 200 and "titre" not in r1.text and r2.status_code == 200:
    print(f"H317_VERDICT: DEFECT the keep answered {r1.status_code}, the entry s-h317 was kept and titre dropped "
          f"without a word (control 422: {control_ok})")
elif r1.status_code == 422 and "titre" in r1.text:
    print("H317_VERDICT: NO-DEFECT the keep was refused with a 422 naming titre")
else:
    print(f"H317_VERDICT: NO-DEFECT another answer: {r1.status_code} {r1.text[:200]}")
