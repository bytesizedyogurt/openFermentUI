"""replay_all.py ORIGIN PROJECT OUT.json: replay every artifact the project holds, one at a time, through
`POST /api/biorepo/artifacts/{id}/replay`, and keep each answer (identical, within tolerance, the
differences' count, or the refusal's words). Run against the head's service over a database alpha 2.1
filled, it says whether every alpha 2.1 artifact replays at the head as docs/api/runs.md says.
"""
from __future__ import annotations

import json
import sys
import time

import httpx

origin, project, out = sys.argv[1], sys.argv[2], sys.argv[3]
c = httpx.Client(base_url=origin, trust_env=False, timeout=1800, headers={"X-OpenFerment-Project": project})
arts = c.get("/api/biorepo/artifacts").json()
arts = arts if isinstance(arts, list) else arts.get("artifacts", [])
only = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else None
res = []
for a in arts:
    if only and a["tool"] not in only:
        continue
    t0 = time.monotonic()
    r = c.post(f"/api/biorepo/artifacts/{a['id']}/replay")
    try:
        body = r.json()
    except ValueError:
        body = r.text[:400]
    row = {"id": a["id"], "tool": a["tool"], "status": r.status_code, "s": round(time.monotonic() - t0, 1)}
    if r.status_code == 200 and isinstance(body, dict):
        row.update({k: body.get(k) for k in ("identical", "withinTolerance")})
        row["differences"] = len(body.get("differences") or [])
        row["first"] = (body.get("differences") or [None])[0]
    else:
        row["detail"] = body
    print(json.dumps(row, default=str)[:500], flush=True)
    res.append(row)
json.dump(res, open(out, "w"), indent=1, default=str)
