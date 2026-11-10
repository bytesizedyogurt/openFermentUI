"""H4: quick calls of the remaining fermOS and pureOS routes: a kept logistic fit of exact data and its forecast
(the forecast's median final biomass against the logistic's own Xmax), the catalogue's specs for one type,
a proposal, and a train's validation.
    cd core && bh_env .venv/bin/python quick_routes.py http://127.0.0.1:8840 h4p
"""
import json, math, sys, httpx
O, P = sys.argv[1], sys.argv[2]
H = {"X-OpenFerment-Project": P}
W = "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4"
x0, mu, xmax = 0.2, 0.35, 8.0
ts = [i * 1.5 for i in range(17)]
X = lambda t: x0 * xmax / (x0 + (xmax - x0) * math.exp(-mu * t))
series = [{"measureId": "od", "label": "Biomass", "unit": "g L-1", "role": "biomass",
           "points": [{"entryId": f"x{i}", "t": t, "value": X(t)} for i, t in enumerate(ts)]}]
with httpx.Client(trust_env=False, timeout=600) as c:
    r = c.post(f"{O}/api/fermos/fit", json={"depositionId": "dep-h4", "series": series}, headers=H)
    print("fit", r.status_code, json.dumps(r.json())[:300])
    fit = r.json().get("kineticArtifactId")
    if fit:
        r = c.post(f"{O}/api/fermos/forecast", json={"fitArtifactId": fit, "by": "h4"}, headers=H)
        d = r.json()
        print("forecast", r.status_code, json.dumps({k: d.get(k) for k in ("finals", "units", "flags", "notes")})[:900])
    r = c.get(f"{O}/api/pureos/catalogue/distillation/specs", headers=H)
    print("catalogue specs", r.status_code, json.dumps(r.json())[:400])
    r = c.post(f"{O}/api/pureos/propose", json={"product": "ethanol", "host": "yeast"}, headers=H)
    print("propose", r.status_code, json.dumps(r.json())[:600])
    fr = json.load(open(f"{W}/train-egv0-fromrun.json"))
    r = c.post(f"{O}/api/pureos/train/validate", json=fr["train"], headers=H)
    print("validate", r.status_code, json.dumps(r.json())[:300])
