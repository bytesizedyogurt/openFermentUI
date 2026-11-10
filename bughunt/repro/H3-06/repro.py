"""H3-06: a kept kinetics run on nine readings, one reading corrected after the run is kept.

What it reads, in order:
  1. depK deposited with nine confirmed readings by a named person; one kinetics run (batch_v1) on them all.
  2. The kept row's provenance, GET /api/runs/{id} and the runs list, before the correction.
  3. depK/k0 corrected by a later entry k0fix (the bench's correction: same measure, `correctedAt`).
  4. The kept row's provenance again, by GET /api/runs/{id} and the runs list.
  5. The same run asked again, the same request byte for byte (ADR-006: "A run looks its readings up again
     each time it runs, and refuses in words one corrected since").
  6. The same reading at another door (Proforma resolve) and the readings list.

  python repro.py http://127.0.0.1:PORT
Prints the observations and one line H306_VERDICT: DEFECT|NO-DEFECT, judged against the contract's own words.
"""
from __future__ import annotations

import json
import sys

import httpx

O = sys.argv[1]
c = httpx.Client(base_url=O, trust_env=False, timeout=300)
H = {"X-OpenFerment-Project": "p1"}
ADA = "Ada Lovelace"
T0 = "2026-11-09T10:00:00Z"

READ = {  # key: (value, unit as deposited)
    "mu_max": (0.0125, "min⁻¹"), "ks": (0.5, "g/L"), "yxs": (0.1, "g/g"), "alpha": (2.0, "g/g"),
    "yps": (0.45, "g/g"), "p_max": (90.0, "g/L"), "x0": (0.1, "g/L"), "s0": (100.0, "g/L"), "p0": (0.0, "g/L"),
}
entries = [{"id": f"k{n}", "measureId": f"mk_{k}", "stepId": "readings", "at": T0, "value": v, "unit": u,
            "raw": f"{v} {u}", "confirmed": True} for n, (k, (v, u)) in enumerate(READ.items())]
dep = {"id": "depK", "runbookId": "rbK", "protocolId": None, "operatorId": None, "startedAt": T0, "closedAt": None,
       "state": "running", "observations": [], "reconciliation": None, "sampleTimes": {}, "entries": entries}
r = c.put("/api/state/depositions/depK", json={"by": ADA, "value": dep}, headers=H)
print(f"1. deposit depK (nine confirmed readings, by {ADA}): {r.status_code}")

inputs = [{"name": k, "quantity": {"value": v, "unit": u, "origin": {"kind": "measurement", "ref": f"depK/k{n}"}}}
          for n, (k, (v, u)) in enumerate(READ.items())]
request = {"thing": "batch_v1", "inputs": inputs, "by": ADA}
r = c.post("/api/engines/kinetics/run", json=request, headers=H)
body = r.json()
run = body.get("run") or {}
rid = run.get("id")
print(f"   kinetics run batch_v1 on the nine readings: {r.status_code}, run {rid}, provenance {run.get('provenance')}")


def kept(label: str) -> tuple[str | None, str | None]:
    got = c.get(f"/api/runs/{rid}", headers=H).json().get("run") or {}
    listed = c.get("/api/runs", headers=H).json()
    listed = listed if isinstance(listed, list) else listed.get("runs", [])
    row = next((x for x in listed if x.get("id") == rid), {})
    mu = next((i for i in got.get("inputs", []) if i["name"].endswith("mu_max")), {})
    origin = (mu.get("quantity") or {}).get("origin") or {}
    print(f"{label} GET /api/runs/{rid}: provenance {got.get('provenance')}; runs list: {row.get('provenance')}; "
          f"its mu_max input's origin: {origin.get('kind')} {origin.get('ref')}")
    return got.get("provenance"), row.get("provenance")


before = kept("2. before the correction,")

st = c.get("/api/state", headers=H).json()
held = next(d for d in st["depositions"] if d["id"] == "depK")
first = held["entries"][0]
held["entries"].append({**first, "id": "k0fix", "value": first["value"] / 10, "raw": "0.00125 min⁻¹ (corrected)",
                        "correctedAt": "2026-11-09T12:00:00Z"})
r = c.put("/api/state/depositions/depK", json={"by": ADA, "value": held}, headers=H)
print(f"3. correct depK/k0 (0.0125 min⁻¹) by a later entry depK/k0fix (0.00125 min⁻¹): {r.status_code}")

after = kept("4. after the correction,")

r = c.post("/api/engines/kinetics/run", json=request, headers=H)
again_body = r.text
again_run = (r.json().get("run") or {}) if r.status_code == 200 else {}
print(f"5. the same run asked again: {r.status_code} {again_body[:240]}")

door = c.post("/api/params/proforma:sc-h306/resolve", headers=H, json={"flowsheet": "ethanol_glucose_v0", "inputs": [
    {"name": "titre", "quantity": {"value": first["value"], "unit": first["unit"],
                                   "origin": {"kind": "measurement", "ref": "depK/k0"}}}]})
print(f"6. depK/k0 at the Proforma resolve door: {door.status_code} {door.text[:200]}")
offered = c.get("/api/depositions/readings", params={"unit": "h⁻¹"}, headers=H)
refs = [x.get("ref") for x in (offered.json() if offered.status_code == 200 else [])] if offered.status_code == 200 else []
print(f"   GET /api/depositions/readings?unit=h⁻¹: {offered.status_code}, offers {refs}")

refused_again = r.status_code == 422 and "corrected" in again_body
print(f"checks: re-ask refused in words naming the correction: {refused_again}; "
      f"kept row before {before}, after {after}")
# The contract: ADR-006:238 and studies.md:106-107 promise the refusal when a run runs again; runs.md:22 promises a
# held row follows its artifact when a *record* the basis rests on is reviewed or demoted. A reading is a
# `measurement` (runs.md:21), so no line promises the kept row's label moves on a reading's correction.
verdict = "NO-DEFECT" if refused_again else "DEFECT"
print(f"H306_VERDICT: {verdict}")
