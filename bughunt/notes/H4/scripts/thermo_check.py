"""H4: thermo props and volatility through the service against thermosteam computed directly.
Service side: POST /api/thermo/props (the azeotrope preset; a library run's stream) and POST /api/thermo/volatility.
Direct side: a separate process with the repository venv (direct_thermo.py).
    cd core && bh_env .venv/bin/python thermo_check.py http://127.0.0.1:8840 h4p <library run id> <stream id>
"""
import json, sys, httpx
O, P, RUN, SID = sys.argv[1:5]
W = "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4"
H = {"X-OpenFerment-Project": P}
out = {}
with httpx.Client(trust_env=False, timeout=600) as c:
    for name, body in (("azeotrope", {"preset": "ethanol-water-azeotrope"}), ("stream", {"artifactId": RUN, "streamId": SID})):
        r = c.post(f"{O}/api/thermo/props", json=body, headers=H)
        print(name, r.status_code)
        d = r.json()
        out[name] = d
        p = d.get("props", d)
        print(json.dumps({k: p.get(k) for k in ("T", "P", "phase", "massFractions", "density", "Cp", "viscosity", "bubblePoint", "dewPoint", "vapourAtBubble", "units", "solved", "notes")}, indent=1)[:2500])
    r = c.post(f"{O}/api/thermo/volatility", json={"product": "ethanol"}, headers=H)
    print("volatility", r.status_code, json.dumps(r.json())[:1500])
    out["volatility"] = r.json()
json.dump(out, open(f"{W}/thermo-svc.json", "w"), indent=1)
