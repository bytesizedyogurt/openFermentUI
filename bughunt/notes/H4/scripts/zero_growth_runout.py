"""H4: batch_v1 with mu_max 0 and a non-growth product (beta 0.1, X0 2, Yp/s 0.5, S0 20): by hand the sugar falls at
beta X0 / Yp/s = 0.4 g/L/h and runs out at 50 h (to 1e-3 of its start at 49.95 h). Asked 'until the sugar runs out' the
route refuses, saying it never runs out; asked with a run length of 60 h it says the hour it ran out.
    cd core && bh_env .venv/bin/python zero_growth_runout.py http://127.0.0.1:8840 h4p
"""
import sys, httpx
O, P = sys.argv[1], sys.argv[2]
H = {"X-OpenFerment-Project": P}
U = {"mu_max": "h⁻¹", "ks": "g L⁻¹", "yxs": "g g⁻¹", "alpha": "g g⁻¹", "beta": "g g⁻¹ h⁻¹", "yps": "g g⁻¹",
     "p_max": "g L⁻¹", "x0": "g L⁻¹", "s0": "g L⁻¹", "p0": "g L⁻¹", "t_end": "h"}
def body(vals):
    return {"family": "batch_v1", "by": "h4", "inputs": [{"name": k, "quantity": {"value": v, "unit": U[k], "origin": {
        "kind": "person-assumption", "by": "h4", "at": "2026-11-10"}}} for k, v in vals.items()]}
base = {"mu_max": 0.0, "ks": 1.0, "yxs": 0.5, "alpha": 0.0, "beta": 0.1, "yps": 0.5, "p_max": 1e12, "x0": 2.0, "s0": 20.0, "p0": 0.0}
with httpx.Client(trust_env=False, timeout=300) as c:
    r = c.post(f"{O}/api/fermos/simulate", json=body(base), headers=H)
    print("until the sugar runs out:", r.status_code, r.json().get("detail"))
    r = c.post(f"{O}/api/fermos/simulate", json=body({**base, "t_end": 60.0}), headers=H)
    d = r.json()
    print("t_end 60 h:", r.status_code, "sugarRunsOutH", d.get("sugarRunsOutH"), "harvestH", d.get("harvestH"), "end", d.get("end"))
