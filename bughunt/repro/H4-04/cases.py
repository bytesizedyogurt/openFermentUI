"""H4-04: fermOS's fed-batch with no uptake, through POST /api/fermos/simulate.

    cases.py ORIGIN PROJECT

Three fed-batches on a constant feed, 1 L start, 0.05 L/h for 20 h:
  noUptakeSugar  mu_max 0, no maintenance, no product terms, the feed at 100 g/L sugar
  noUptakeWater  the same with a feed carrying no sugar
  control        a little growth (mu_max 0.2, alpha 0.3), the feed at 100 g/L

With no uptake the closed form is V = V0 + F t, X = X0 V0 / V, P = P0 V0 / V and
S = (S0 V0 + F Sf t) / V: the cells take up nothing, so the sugar consumed is zero.
For each case the script prints the worst relative error of V, X, S, P against that closed form
(no-uptake cases), the route's massBalance and flags, and the sugar consumed as a share of the sugar
the vessel held and was fed. The last line is a JSON verdict the run.sh reads.
"""
import json
import re
import sys

import httpx

O, PROJECT = sys.argv[1], sys.argv[2]
H = {"X-OpenFerment-Project": PROJECT}
U = {"mu_max": "h⁻¹", "ks": "g L⁻¹", "yxs": "g g⁻¹", "alpha": "g g⁻¹", "yps": "g g⁻¹", "p_max": "g L⁻¹",
     "x0": "g L⁻¹", "s0": "g L⁻¹", "p0": "g L⁻¹", "v0": "L", "t_end": "h", "feed_rate": "L h⁻¹",
     "mu_set": "h⁻¹", "feed_conc": "g L⁻¹", "feed_profile": ""}
BIG = 1e12  # a Pmax no product reaches


def q(k, v):
    return {"value": v, "unit": U[k], "origin": {"kind": "person-assumption", "by": "H4-04", "at": "2026-11-10"}}


c = httpx.Client(trust_env=False, timeout=300)


def sim(vals):
    r = c.post(f"{O}/api/fermos/simulate", headers=H,
               json={"family": "fedbatch_v1", "by": "H4-04",
                     "inputs": [{"name": k, "quantity": q(k, v)} for k, v in vals.items()]})
    return r.status_code, r.json()


X0, S0, P0, V0, F, T = 2.0, 20.0, 3.0, 1.0, 0.05, 20.0
base = {"ks": 1.0, "yxs": 0.5, "yps": 0.5, "p_max": BIG, "feed_profile": "constant", "feed_rate": F,
        "mu_set": 0.1, "v0": V0, "t_end": T}
cases = {
    "noUptakeSugar": {**base, "mu_max": 0.0, "alpha": 0.0, "feed_conc": 100.0, "x0": X0, "s0": S0, "p0": P0},
    "noUptakeWater": {**base, "mu_max": 0.0, "alpha": 0.0, "feed_conc": 0.0, "x0": X0, "s0": S0, "p0": P0},
    "control": {**base, "mu_max": 0.2, "alpha": 0.3, "feed_conc": 100.0, "x0": 1.0, "s0": 10.0, "p0": 0.0},
}
verdict = {}
for name, vals in cases.items():
    code, d = sim(vals)
    if code != 200:
        print(f"{name}: refused {code} {d}")
        verdict[name] = {"status": code}
        continue
    mb, flags = d["massBalance"], d["flags"]
    sf = vals["feed_conc"]
    inventory = vals["s0"] * V0 + F * sf * T  # grams of sugar the vessel held and was fed
    consumed = float(re.search(r"Sugar consumed, (\S+) g", mb["note"]).group(1))
    row = {"closure": mb["closure"], "ok": mb["ok"], "flags": flags, "consumedG": consumed, "inventoryG": inventory}
    if name.startswith("noUptake"):
        s = d["series"]
        exact = {"V": lambda t: V0 + F * t, "X": lambda t: X0 * V0 / (V0 + F * t),
                 "S": lambda t: (S0 * V0 + F * sf * t) / (V0 + F * t), "P": lambda t: P0 * V0 / (V0 + F * t)}
        worst = {k: max(abs(y - f(t)) / max(abs(f(t)), 1e-9) for t, y in zip(s["t"], s[k])) for k, f in exact.items()}
        row["worstRel"] = worst
        print(f"{name}: series against the closed form, worst relative error "
              + ", ".join(f"{k} {e:.2e}" for k, e in worst.items()))
    print(f"{name}: massBalance closure {mb['closure']:.4g} ok {mb['ok']}")
    print(f"{name}: note: {mb['note']}")
    print(f"{name}: flags {flags}")
    verdict[name] = row
print("VERDICT " + json.dumps(verdict))
