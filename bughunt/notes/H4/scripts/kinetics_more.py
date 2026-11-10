"""H4: more fermOS cases against hand values.
  A. Fed-batch, exponential feed, Monod with a small Ks: the culture grows at mu_set, so X V = X0 V0 exp(mu_set t).
  B. Fed-batch, constant feed, a little growth: the mass balance closure the result reports.
  C. Fed-batch, constant feed, no uptake at all: closure (the dilution-alone case of kinetics_cases.py), and the same
     case with the feed carrying no sugar.
  D. Chemostat past washout: D above mu_max Sf/(Ks+Sf).
    cd core && bh_env .venv/bin/python kinetics_more.py http://127.0.0.1:8840 h4p
"""
import json, math, sys, httpx
sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H4/scripts")
O, P = sys.argv[1], sys.argv[2]
H = {"X-OpenFerment-Project": P}
U = {"mu_max": "h⁻¹", "ks": "g L⁻¹", "kd": "h⁻¹", "yxs": "g g⁻¹", "alpha": "g g⁻¹", "beta": "g g⁻¹ h⁻¹",
     "yps": "g g⁻¹", "maintenance": "g g⁻¹ h⁻¹", "p_max": "g L⁻¹", "x0": "g L⁻¹", "s0": "g L⁻¹", "p0": "g L⁻¹",
     "v0": "L", "t_end": "h", "feed_rate": "L h⁻¹", "mu_set": "h⁻¹", "feed_conc": "g L⁻¹", "dilution_rate": "h⁻¹",
     "feed_profile": ""}
def q(k, v): return {"value": v, "unit": U[k], "origin": {"kind": "person-assumption", "by": "h4", "at": "2026-11-10"}}
c = httpx.Client(trust_env=False, timeout=300)
def sim(family, vals):
    r = c.post(f"{O}/api/fermos/simulate", json={"family": family, "by": "h4",
               "inputs": [{"name": k, "quantity": q(k, v)} for k, v in vals.items()]}, headers=H)
    return r.status_code, r.json()
BIG = 1e12
# A
ms, X0, V0 = 0.1, 1.0, 1.0
code, d = sim("fedbatch_v1", {"mu_max": 1.0, "ks": 0.001, "yxs": 0.5, "alpha": 0.0, "yps": 0.5, "p_max": BIG,
                              "feed_profile": "exponential", "feed_rate": 0.01, "mu_set": ms, "feed_conc": 400.0,
                              "x0": X0, "s0": 0.0005, "p0": 0.0, "v0": V0, "t_end": 20.0})
print("A", code)
if code == 200:
    s = d["series"]
    worst = max(abs(x * v - X0 * V0 * math.exp(ms * t)) / (X0 * V0 * math.exp(ms * t)) for t, x, v in zip(s["t"], s["X"], s["V"]) if t > 2)
    print(f"  X V against X0 V0 exp(mu_set t), t > 2 h: worst rel {worst:.3e}; end {d['end']}; closure {d['massBalance']}")
    print("  flags", d["flags"])
else:
    print(d)
# B
code, d = sim("fedbatch_v1", {"mu_max": 0.2, "ks": 1.0, "yxs": 0.5, "alpha": 0.3, "yps": 0.5, "p_max": BIG,
                              "feed_profile": "constant", "feed_rate": 0.05, "mu_set": 0.1, "feed_conc": 100.0,
                              "x0": 1.0, "s0": 10.0, "p0": 0.0, "v0": 1.0, "t_end": 20.0})
print("B", code, d.get("massBalance") if code == 200 else d, d.get("flags") if code == 200 else "")
# C: no uptake, a feed with sugar; then with water alone
for sf in (100.0, 0.0):
    code, d = sim("fedbatch_v1", {"mu_max": 0.0, "ks": 1.0, "yxs": 0.5, "alpha": 0.0, "yps": 0.5, "p_max": BIG,
                                  "feed_profile": "constant", "feed_rate": 0.05, "mu_set": 0.1, "feed_conc": sf,
                                  "x0": 2.0, "s0": 20.0, "p0": 3.0, "v0": 1.0, "t_end": 20.0})
    print(f"C feed {sf} g/L", code, d.get("massBalance") if code == 200 else d, d.get("flags") if code == 200 else "")
# D
code, d = sim("chemostat_v1", {"mu_max": 0.4, "ks": 1.0, "yxs": 0.5, "alpha": 0.0, "yps": 0.5, "p_max": BIG,
                               "dilution_rate": 0.5, "feed_conc": 20.0, "x0": 1.0, "s0": 1.0, "p0": 0.0, "t_end": 80.0})
print("D", code)
if code == 200:
    print("  end", d["end"], "flags", d["flags"])
    print("  steady", json.dumps(d["steadyState"])[:500])
