"""H3: a kept run stays `measured` after the reading it rests on is corrected. Run after
kinetics_provenance.py (it reads depK and the run of every value a reading).

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/kinetics_corrected.py http://127.0.0.1:8830
"""
import sys

import httpx

O = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8830"
c = httpx.Client(base_url=O, trust_env=False, timeout=300)
H = {"X-OpenFerment-Project": "p1"}
runs = c.get("/api/runs", headers=H).json()
runs = runs if isinstance(runs, list) else runs.get("runs", [])
measured = [r["id"] for r in runs if r.get("engine") == "kinetics" and r.get("provenance") == "measured"]
rid = measured[0]
st = c.get("/api/state", headers=H).json()
dep = next(d for d in st["depositions"] if d["id"] == "depK")
first = dep["entries"][0]
dep["entries"].append({**first, "id": "k0fix", "value": first["value"] / 10, "raw": "corrected",
                       "correctedAt": "2026-11-09T12:00:00Z"})
print("correct depK/k0:", c.put("/api/state/depositions/depK", json={"by": "Ada Lovelace", "value": dep}, headers=H).status_code)
print("the kept run on depK/k0:", c.get(f"/api/runs/{rid}", headers=H).json()["run"]["provenance"])
again = c.post("/api/params/proforma:sc-h3/resolve", headers=H, json={"flowsheet": "ethanol_glucose_v0", "inputs": [
    {"name": "titre", "quantity": {"value": first["value"], "unit": first["unit"],
                                   "origin": {"kind": "measurement", "ref": "depK/k0"}}}]})
print("the same reading at a door now:", again.status_code, again.text[:200])
