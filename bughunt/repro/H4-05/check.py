"""H4-05: batch_v1 with μmax 0, asked to run until the sugar runs out, with β or maintenance draining the sugar.

Solvable by hand. With μ = 0 and kd = 0 the cells hold at X0, so
    dS/dt = -(β/Yps + m)·X0, constant, and the sugar falls in a straight line.
The family's run-out hour is the first hour S reaches RUN_OUT_SHARE (1e-3) of S0:
    t_out = (1 - 1e-3)·S0 / ((β/Yps + m)·X0).
Case beta:  β 0.1 g g-1 h-1, m 0, X0 2, Yp/s 0.5, S0 20 -> 0.4 g/L/h, t_out 49.95 h.
Case maint: β 0, m 0.1 g g-1 h-1, X0 2, S0 20       -> 0.2 g/L/h, t_out 99.9 h.
Control:    β 0, m 0: the sugar never falls, and a refusal is right.
Each case is posted once with no run length ('until the sugar runs out') and the two draining cases once more with a
run length past the hand's run-out hour, where the family reports the hour itself.
Reads H405_ORIGIN and H405_PROJECT; prints EXPECTED, OBSERVED and RESULT lines.
"""
import math
import os

import httpx

O, P = os.environ["H405_ORIGIN"], os.environ["H405_PROJECT"]
H = {"X-OpenFerment-Project": P}
UNITS = {"mu_max": "h⁻¹", "ks": "g L⁻¹", "yxs": "g g⁻¹", "alpha": "g g⁻¹", "beta": "g g⁻¹ h⁻¹", "yps": "g g⁻¹",
         "maintenance": "g g⁻¹ h⁻¹", "p_max": "g L⁻¹", "x0": "g L⁻¹", "s0": "g L⁻¹", "p0": "g L⁻¹", "t_end": "h"}
SHARE = 1e-3


def body(vals: dict) -> dict:
    origin = {"kind": "person-assumption", "by": "h405", "at": "2026-11-10"}
    return {"family": "batch_v1", "by": "h405",
            "inputs": [{"name": k, "quantity": {"value": v, "unit": UNITS[k], "origin": origin}} for k, v in vals.items()]}


BASE = {"mu_max": 0.0, "ks": 1.0, "yxs": 0.5, "alpha": 0.0, "yps": 0.5, "p_max": 1e12, "x0": 2.0, "s0": 20.0, "p0": 0.0}
CASES = {
    "beta": {**BASE, "beta": 0.1, "maintenance": 0.0},
    "maint": {**BASE, "beta": 0.0, "maintenance": 0.1},
}
CONTROL = {**BASE, "beta": 0.0, "maintenance": 0.0}


def by_hand(v: dict) -> float:
    rate = (v["beta"] / v["yps"] + v["maintenance"]) * v["x0"]
    return (1 - SHARE) * v["s0"] / rate


defect = []
with httpx.Client(trust_env=False, timeout=300) as c:
    for name, v in CASES.items():
        hand = by_hand(v)
        rate = (v["beta"] / v["yps"] + v["maintenance"]) * v["x0"]
        r_until = c.post(f"{O}/api/fermos/simulate", json=body(v), headers=H)
        r_len = c.post(f"{O}/api/fermos/simulate", json=body({**v, "t_end": math.ceil(hand * 1.2)}), headers=H)
        d_len = r_len.json() if r_len.status_code == 200 else {}
        print(f"case {name}: μmax 0, β {v['beta']}, m {v['maintenance']}, X0 {v['x0']}, Yp/s {v['yps']}, S0 {v['s0']}"
              f" -> by hand the sugar falls at {rate:g} g/L/h and runs out at {hand:.6g} h")
        print(f"  until the sugar runs out: HTTP {r_until.status_code}"
              f" {r_until.json().get('detail') if r_until.status_code != 200 else 'sugarRunsOutH ' + str(r_until.json().get('sugarRunsOutH'))}")
        print(f"  run length {math.ceil(hand * 1.2)} h: HTTP {r_len.status_code} sugarRunsOutH {d_len.get('sugarRunsOutH')}"
              f" harvestH {d_len.get('harvestH')} end S {d_len.get('end', {}).get('S')}")
        same_family_reports = (r_len.status_code == 200 and d_len.get("sugarRunsOutH") is not None
                               and abs(d_len["sugarRunsOutH"] - hand) <= 1e-6 * hand)
        refused_as_never = (r_until.status_code == 422 and "never runs out" in str(r_until.json().get("detail")))
        defect.append(same_family_reports and refused_as_never)
    r_ctl = c.post(f"{O}/api/fermos/simulate", json=body(CONTROL), headers=H)
    print(f"control: μmax 0, β 0, m 0 (the sugar never falls), until the sugar runs out: HTTP {r_ctl.status_code}"
          f" {r_ctl.json().get('detail')}")

print("EXPECTED: asked to run until the sugar runs out, a batch whose sugar falls at a constant rate ends at its run-out"
      " hour (49.95 h for β 0.1, 99.9 h for m 0.1), or is refused only where the sugar stops falling"
      " (kinetics.py:59-61); the control, whose sugar never falls, may be refused")
print("OBSERVED: " + ("both draining cases are refused with 'the sugar never runs out', and the same family, given a"
                      " run length, reports the run-out hour the hand computes" if all(defect)
                      else f"the draining cases are not refused as never running out ({defect})"))
print("RESULT: " + ("DEFECT" if all(defect) else "NO-DEFECT"))
