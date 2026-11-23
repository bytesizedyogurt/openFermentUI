"""H4: fit exact logistic data (and the Luedeking-Piret product it implies) through POST /api/fermos/fit
with sample=true (kept nowhere), and read back X0, mu, Xmax, alpha, beta against the values that made it.
    cd core && bh_env .venv/bin/python fit_logistic.py http://127.0.0.1:8840 h4p
"""
import json, math, sys, httpx
O, P = sys.argv[1], sys.argv[2]
H = {"X-OpenFerment-Project": P}
x0, mu, xmax, al, be, p0 = 0.2, 0.35, 8.0, 0.45, 0.02, 0.5
ts = [i * 1.5 for i in range(17)]
def X(t): return x0 * xmax / (x0 + (xmax - x0) * math.exp(-mu * t))
def I(t): return (xmax / mu) * math.log((x0 * math.exp(mu * t) + xmax - x0) / xmax)
def Pp(t): return p0 + al * (X(t) - x0) + be * I(t)
series = [{"measureId": "od", "label": "Biomass", "unit": "g L-1", "role": "biomass", "points": [{"entryId": f"x{i}", "t": t, "value": X(t)} for i, t in enumerate(ts)]},
          {"measureId": "etoh", "label": "Ethanol", "unit": "g L-1", "role": "product", "points": [{"entryId": f"p{i}", "t": t, "value": Pp(t)} for i, t in enumerate(ts)]}]
with httpx.Client(trust_env=False, timeout=300) as c:
    r = c.post(f"{O}/api/fermos/fit", json={"depositionId": "dep-h4", "series": series, "sample": True}, headers=H)
    print(r.status_code)
    d = r.json()
    if r.status_code != 200:
        print(d); sys.exit()
    print(d.keys())
    k = d.get("kinetic") or d.get("kineticFit") or {}
    print(json.dumps(d)[:300])
    for key in d:
        v = d[key]
        if isinstance(v, dict) and "params" in v:
            for p in v["params"]:
                want = {"X0": x0, "mu": mu, "Xmax": xmax, "alpha": al, "beta": be, "P0": p0}.get(p["name"])
                print(f"  {key}.{p['name']} = {p['value']:.10g} [{p['unit']}] want {want}")
        if isinstance(v, dict) and "mu" in v and isinstance(v.get("mu"), dict):
            print(f"  {key}.mu = {v['mu']['value']:.6g} window {v.get('window')} (exponential window estimate; true {mu})")
