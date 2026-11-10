"""R2: D.0's claim 'a NaN or infinite input is refused in words at every door' (commit 6f85338).

Posts a body whose one quantity's value is the JSON tokens NaN / Infinity (which Python's and
FastAPI's JSON reader accept) to each door that takes a run's value, and prints the status and
the first words of the answer. Usage: python nan_doors.py http://127.0.0.1:8970 <project>
"""
from __future__ import annotations

import sys

import httpx

ORIGIN, PROJECT = sys.argv[1], sys.argv[2]
H = {"X-OpenFerment-Project": PROJECT, "content-type": "application/json"}
ORIGIN_PA = '{"kind":"person-assumption","by":"R2","at":"2026-11-10"}'


def q(tok: str, unit: str = "h⁻¹", where: str = "value") -> str:
    if where == "value":
        return '{"value":%s,"unit":"%s","origin":%s}' % (tok, unit, ORIGIN_PA)
    return '{"value":1.0,"unit":"%s","%s":%s,"origin":%s}' % (unit, where, tok, ORIGIN_PA)


def inputs(name: str, tok: str, unit: str, where: str = "value") -> str:
    return '[{"name":"%s","quantity":%s}]' % (name, q(tok, unit, where))


DOORS = [
    ("POST", "/api/engines/kinetics/run", lambda t: '{"thing":"batch_v1","by":"R2","inputs":%s}' % inputs("mu_max", t, "h⁻¹")),
    ("POST", "/api/fermos/simulate", lambda t: '{"family":"batch_v1","by":"R2","inputs":%s}' % inputs("mu_max", t, "h⁻¹")),
    ("POST", "/api/params/fermos.simulation/resolve", lambda t: '{"inputs":%s}' % inputs("mu_max", t, "h⁻¹")),
    ("POST", "/api/library/cornstover/run", lambda t: '{"by":"R2","inputs":%s}' % inputs("feedstock_price", t, "USD/kg")),
    ("POST", "/api/studies/scenarios", lambda t: '{"title":"R2 nan","plant":"cornstover","by":"R2","values":[{"key":"feedstock_price","quantity":%s}]}' % q(t, "USD/kg")),
    ("POST", "/api/biorepo/decisions", lambda t: '{"status":"accepted","provenance":"verified","recordId":"r2-nan","at":"2026-11-10T00:00:00Z","reviewer":"R2","corrected":%s}' % q(t, "g/L")),
]

with httpx.Client(trust_env=False, timeout=120) as c:
    for tok in ("NaN", "Infinity"):
        for method, path, body in DOORS:
            r = c.request(method, ORIGIN + path, headers=H, content=body(tok).encode())
            words = r.text.replace("\n", " ")[:220]
            print(f"{tok:8} {r.status_code} {method} {path}: {words}")
