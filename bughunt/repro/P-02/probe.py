"""P-02's service half: one held document, one candidate on it, and one verified decision on that candidate
that carries the label 'gold' and no gold value. Prints what the service computes and serves for it.

usage: bh_py probe.py ORIGIN PROJECT FIXTURE_DIR OUT_JSON
Offline: the service runs with OPENFERMENT_FIXTURES=1, so extraction reads the stand-in written here.
"""
import json
import re
import sys
from pathlib import Path

import httpx

ORIGIN, PROJECT, FIXTURES, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
DOC = Path("/home/user/openFermentUI/core/tests/fixtures/kit-demo/fixture/central-valley-residue-policy.md")
c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600, headers={"X-OpenFerment-Project": PROJECT})
AT = "2026-11-10T23:10:00Z"

# 1. The document, through Intake's upload (CC0, the kit's demo corpus).
r = c.post("/api/intake/upload", files={"file": (DOC.name, DOC.read_bytes(), "text/markdown")},
           data={"by": "Ada Moreno", "title": "Central Valley residue policy (kit demo)", "licenceClass": "public",
                 "licence": "CC0 (kit demo manifest)", "reason": "P-02 reproduction"})
print("upload:", r.status_code, r.json().get("status"))

# 2. One candidate on it: a stand-in extraction of the first sentence naming days, anchored by the service.
papers = c.get("/api/biorepo/overlay").json()["papers"]
doc_id, sec, quote, value = None, None, None, None
for pid, paper in papers.items():
    for s in paper["sections"]:
        m = re.search(r"([^.]*?\b(\d+(?:\.\d+)?)\s*days\b[^.]*)", s["text"])
        if m:
            doc_id, sec, quote, value = pid, s["id"], m.group(1).strip(), float(m.group(2))
            break
    if doc_id:
        break
stand_in = {"_note": "P-02's stand-in extraction", "usage": {"models": ["p02-standin"]},
            "raw": {"candidates": [{"sectionId": sec, "field": "time_to_colony", "value": value, "unit": "d",
                                    "isPrimary": True, "confidence": 0.9, "quote": quote}]}}
(FIXTURES / "extract").mkdir(parents=True, exist_ok=True)
(FIXTURES / "extract" / f"{doc_id}.json").write_text(json.dumps(stand_in))
got = c.post(f"/api/intake/{doc_id}/extract?force=true").json()
cands = got.get("candidates", [])
print("extract:", len(cands), "candidate(s)", got.get("rejectionReasons"))
if not cands:
    OUT.write_text(json.dumps({"error": "no candidate"}))
    sys.exit(0)
rid = cands[0]["id"]


def decision(label):
    return {"status": "verified", "provenance": label, "gold": None, "reviewer": "Ada Moreno", "recordId": rid, "at": AT}


# 3. The dry run for the same verified decision under each label: what the service would keep.
check = {}
for label in ("verified", "gold"):
    a = c.post("/api/biorepo/check", json=decision(label)).json()
    check[label] = a
    print(f"check, verified, label {label!r}, gold null ->", json.dumps(a)[:200])

# 4. The decision itself, label 'gold', no gold value.
stored = c.post("/api/biorepo/decisions", json=decision("gold"))
s = stored.json()
print("decision answered:", stored.status_code, {k: s.get(k) for k in ("status", "provenance", "gold")})

# 5. Postdoc's evidence pool reads it.
pool = c.post("/api/tools/biorepo_read", json={"ids": [rid], "words": "", "kind": "", "state": "", "limit": 5}).json()
pool_rows = [(row["id"], row.get("kind"), row.get("provenance")) for row in pool.get("rows", [])]
print("biorepo_read:", pool_rows)

# 6. The overlay the browser applies at load.
ov = c.get("/api/biorepo/overlay").json()
dec = (ov.get("records") or {}).get(rid) or {}
print("overlay decision:", {k: dec.get(k) for k in ("status", "provenance", "gold")})

OUT.write_text(json.dumps({"recordId": rid, "check": check, "stored": s, "pool": pool_rows, "overlay": dec}))
