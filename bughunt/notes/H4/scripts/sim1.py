"""H4: one fermOS simulation through POST /api/fermos/simulate; prints the answer's shape."""
import json, sys, httpx
O = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8840"
H = {"X-OpenFerment-Project": "h4p"}
def q(v, u): return {"value": v, "unit": u, "origin": {"kind": "person-assumption", "by": "h4", "at": "2026-11-10"}}
vals = {"mu_max": (0.0, "h⁻¹"), "ks": (1.0, "g L⁻¹"), "yxs": (0.5, "g g⁻¹"), "alpha": (0.0, "g g⁻¹"),
        "beta": (0.1, "g g⁻¹ h⁻¹"), "yps": (0.5, "g g⁻¹"), "p_max": (1000.0, "g L⁻¹"),
        "x0": (2.0, "g L⁻¹"), "s0": (20.0, "g L⁻¹"), "p0": (0.0, "g L⁻¹"), "t_end": (40.0, "h")}
req = {"family": "batch_v1", "by": "h4", "inputs": [{"name": k, "quantity": q(*v)} for k, v in vals.items()]}
with httpx.Client(trust_env=False, timeout=120) as c:
    r = c.post(f"{O}/api/fermos/simulate", json=req, headers=H)
print(r.status_code)
d = r.json()
if r.status_code != 200: print(d); sys.exit()
print(d.keys())
for k, v in d.items():
    s = json.dumps(v)
    print(k, ":", s[:600])
