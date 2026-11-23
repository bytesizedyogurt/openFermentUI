"""P-03: two of the kit's CC0 demo documents enter a project through Intake's upload, so the project holds
two documents with no PMCID, DOI or PMID. A stand-in extraction (fixture mode, no model) gives each one
candidate; one candidate is accepted through biorepo.write (POST /api/biorepo/decisions). The overlay the
browser reads is saved to OUT.

usage: python seed.py ORIGIN PROJECT FIXTURE_DIR OUT
"""
import json
import re
import sys
import time
from pathlib import Path

import httpx

ORIGIN, PROJECT, FIXTURES, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
DEMO = Path("/home/user/openFermentUI/core/tests/fixtures/kit-demo")
DOCS = ("anaerobic-digestion-primer.md", "central-valley-residue-policy.md")
c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600, headers={"X-OpenFerment-Project": PROJECT})
rows = [json.loads(l) for l in (DEMO / "manifest.jsonl").read_text().splitlines() if l.strip() and not l.startswith("#")]
for row in rows:
    p = DEMO / row["path"]
    if p.name not in DOCS:
        continue
    r = c.post("/api/intake/upload", files={"file": (p.name, p.read_bytes(), "text/markdown")},
               data={"by": "Ada Moreno", "title": row["title"], "licenceClass": row["license_class"],
                     "licence": "CC0 (kit demo manifest)", "reason": "P-03 repro"})
    print("upload", p.name, r.status_code, r.json().get("status"))

papers = c.get("/api/biorepo/overlay").json()["papers"]
kept = []
for doc_id, paper in papers.items():
    for s in paper["sections"]:
        m = re.search(r"([^.]*?\b(\d+(?:\.\d+)?)\s*days\b[^.]*)", s["text"])
        if m:
            break
    else:
        continue
    resp = {"_note": "P-03 stand-in extraction", "usage": {"models": ["p03-standin"]},
            "raw": {"candidates": [{"sectionId": s["id"], "field": "time_to_colony", "value": float(m.group(2)),
                                    "unit": "d", "isPrimary": True, "confidence": 0.9, "quote": m.group(1).strip()}]}}
    (FIXTURES / "extract").mkdir(parents=True, exist_ok=True)
    (FIXTURES / "extract" / f"{doc_id}.json").write_text(json.dumps(resp))
    got = c.post(f"/api/intake/{doc_id}/extract?force=true").json()
    print("extract", doc_id, "candidates", len(got.get("candidates", [])))
    kept += got.get("candidates", [])

if kept:
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    d = c.post("/api/biorepo/decisions", json={"status": "verified", "provenance": "verified",
                                                "reviewer": "Ada Moreno", "recordId": kept[0]["id"], "at": at})
    paper = papers[kept[0]["paperId"]]
    print(f"DECISION: biorepo.write on {kept[0]['id']} (paper doi={paper.get('doi')!r} pmcid={paper.get('pmcid')!r})"
          f" answered HTTP {d.status_code} {d.text[:160]}")
overlay = c.get("/api/biorepo/overlay").json()
OUT.write_text(json.dumps(overlay))
for doc_id, p in overlay["papers"].items():
    print(f"HELD: {doc_id} doi={p.get('doi')!r} pmcid={p.get('pmcid')!r} (OverlayPaper carries no pmid field)")
