"""H4: one anaerobic vessel design (POST /api/fermos/vessel) of a kept simulation at a plant scale;
prints the design table and the hand reading of the broth flow (plant scale / operating hours / titre).
    cd core && bh_env .venv/bin/python vessel_one.py http://127.0.0.1:8840 h4p <simulation id> <t per yr>
"""
import json, sys, httpx
O, P, SIM, SCALE = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
W = "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4"
H = {"X-OpenFerment-Project": P}
q = {"value": SCALE, "unit": "t yr⁻¹", "origin": {"kind": "person-assumption", "by": "h4", "at": "2026-11-10"}}
with httpx.Client(trust_env=False, timeout=900) as c:
    sim = c.get(f"{O}/api/biorepo/artifacts/{SIM}", headers=H).json()
    r = c.post(f"{O}/api/fermos/vessel", json={"simulation": SIM, "by": "h4", "inputs": [{"name": "plant_scale", "quantity": q}]}, headers=H)
    print(r.status_code)
    d = r.json()
    json.dump(d, open(f"{W}/vessel-{SIM}.json", "w"), indent=1)
    if r.status_code != 200:
        print(d); sys.exit()
    print(d.keys())
    for row in d.get("design", d.get("rows", [])):
        print("  ", row)
    for k in ("scale", "reaction", "oxygen", "heat", "flags", "notes", "costs"):
        if k in d: print(k, json.dumps(d[k])[:900])
    out = sim.get("output", sim)
    titre = out.get("finalTitre")
    print("titre", titre, "harvestH", out.get("harvestH"))
