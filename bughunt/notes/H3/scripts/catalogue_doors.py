"""H3: a model's estimate and measured values in words at the catalogue's doors.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/catalogue_doors.py http://127.0.0.1:8830
"""
import json
import sys

import httpx

O = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8830"
c = httpx.Client(base_url=O, trust_env=False, timeout=60)
H = {"X-OpenFerment-Project": "p1"}
est = {"value": 45, "unit": "g/L", "origin": {"kind": "model-estimate", "by": "claude-x", "at": "2026-11-09"}}
r = c.post("/api/catalogues/strain", json={"entry": {"kind": "strain", "id": "s-h3", "name": "H3 strain", "titre": est},
                                           "by": "Ada Lovelace"}, headers=H)
print("person's keep with an estimate field no kind takes:", r.status_code, "titre" in r.text)
lesson = {"kind": "lesson", "id": "l-h3", "name": "Units", "minutes": 5, "checkpoint": [
    {"id": "q1", "prompt": "How heavy is the batch?", "kind": "numeric", "answer": {"value": 2, "unit": "Mg", "tolerancePct": 5}}]}
r = c.post("/api/catalogues/lesson", json={"entry": lesson, "by": "Ada Lovelace"}, headers=H)
print("a lesson whose answer is 2 Mg (read as milligrams):", r.status_code)
A = {**H, "X-OpenFerment-Assistant": "hunt-agent/0.1"}
r = c.post("/api/tools/catalogue_write", headers=A, json={
    "kind": "strain", "id": "hunt-agent.0.1-s1", "name": "Strain making 45 g/L", "species": "Saccharomyces cerevisiae",
    "summary": "reaches a titre of 45 g/L at 30 °C in 48 h", "note": "read from a paper: 0.45 g/g yield"})
b = r.json()
print("catalogue_write in the model's lane:", r.status_code, b.get("error"))
s = b.get("summary") or {}
print("   kept:", json.dumps({k: s.get(k) for k in ("name", "summary", "note", "agent", "via")}, ensure_ascii=False))
