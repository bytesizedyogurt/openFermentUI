"""Take the kit's demo corpus (CC0, core/tests/fixtures/kit-demo) into a project through Intake's upload, as the
proof's step 3 does, write a stand-in extraction for each document's first sentence that holds a number, extract,
and accept one candidate. Offline: the service must run with OPENFERMENT_FIXTURES=1 and its fixture dir named.

usage: bh_py seed_demo.py ORIGIN PROJECT FIXTURE_DIR
"""
import json
import re
import sys
import time
from pathlib import Path

import httpx

ORIGIN, PROJECT, FIXTURES = sys.argv[1], sys.argv[2], Path(sys.argv[3])
DEMO = Path("/home/user/openFermentUI/core/tests/fixtures/kit-demo")
H = {"X-OpenFerment-Project": PROJECT}
c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600, headers=H)
rows = [json.loads(l) for l in (DEMO / "manifest.jsonl").read_text().splitlines() if l.strip() and not l.startswith("#")]
for row in rows:
    p = DEMO / row["path"]
    r = c.post("/api/intake/upload", files={"file": (p.name, p.read_bytes(), "text/markdown")},
               data={"by": "Ada Moreno", "title": row["title"], "licenceClass": row["license_class"],
                     "licence": "CC0 (kit demo manifest)", "reason": "hunt P"})
    print("upload", p.name, r.status_code, r.json().get("status"))
papers = c.get("/api/biorepo/overlay").json()["papers"]
kept = []
for doc_id, paper in papers.items():
    # the first sentence of a section holding a number and a unit-like word
    for s in paper["sections"]:
        m = re.search(r"([^.]*?\b(\d+(?:\.\d+)?)\s*(days)\b[^.]*)", s["text"])
        if m:
            quote, value = m.group(1).strip(), float(m.group(2))
            break
    else:
        continue
    unit = {"days": "d", "percent": "%", "years": "yr", "hours": "h"}.get(m.group(3), m.group(3))
    resp = {"_note": "hunt P's stand-in extraction", "usage": {"models": ["hunt-p-standin"]},
            "raw": {"candidates": [{"sectionId": s["id"], "field": "time_to_colony", "value": value, "unit": unit,
                                    "isPrimary": True, "confidence": 0.9, "quote": quote}]}}
    (FIXTURES / "extract").mkdir(parents=True, exist_ok=True)
    (FIXTURES / "extract" / f"{doc_id}.json").write_text(json.dumps(resp))
    got = c.post(f"/api/intake/{doc_id}/extract?force=true").json()
    print("extract", doc_id, len(got.get("candidates", [])), got.get("rejectionReasons"))
    kept += got.get("candidates", [])
if kept:
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    d = c.post("/api/biorepo/decisions", json={"status": "verified", "provenance": "curated", "reviewer": "Ada Moreno",
                                                "recordId": kept[0]["id"], "at": at})
    print("accept", kept[0]["id"], d.status_code, d.text[:300])
print(json.dumps({"candidates": [k["id"] for k in kept]}))
