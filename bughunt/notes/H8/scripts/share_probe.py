"""Two projects that hold one document, a project with none: what each reads.

Usage: python share_probe.py ORIGIN
Makes projects gamma, delta and nothing (if absent) on a local test service, pastes into
gamma and delta, then reads documents, overlay, search and stats in each.
"""
from __future__ import annotations

import json
import sys

import httpx

origin = sys.argv[1]


def client(project: str | None) -> httpx.Client:
    h = {"X-OpenFerment-Project": project} if project else {}
    return httpx.Client(base_url=origin, trust_env=False, timeout=300, headers=h)


root = client(None)
for p in ("gamma", "delta", "nothing"):
    root.post("/api/projects", json={"id": p, "name": p, "by": "h8"})

G, D, N = client("gamma"), client("delta"), client("nothing")
GAMMA_TEXT = ("The biorefinery processes 2000 Mg of dry corn stover per day, and the saccharification "
              "step releases glucose at the rate the H8 share probe names.")
DELTA_TEXT = GAMMA_TEXT.replace("2000 Mg", "2000 mg").upper()
PRIVATE = "Gamma keeps this alone: the H8 private passage about xylanase loading in gamma."

g1 = G.post("/api/intake/paste", json={"title": "Gamma's own title for the stover note", "text": GAMMA_TEXT,
                                         "by": "gamma-person", "licenceClass": "restricted",
                                         "licence": "Gamma's licence words: internal use alone"}).json()
g2 = G.post("/api/intake/paste", json={"title": "Gamma private", "text": PRIVATE, "by": "gamma-person"}).json()
d1 = D.post("/api/intake/paste", json={"title": "Delta's title", "text": DELTA_TEXT, "by": "delta-person",
                                         "licenceClass": "open_commercial"}).json()
print("gamma paste:", g1["status"], g1["documentId"], g1["licenceClass"])
print("gamma private:", g2["status"], g2["documentId"])
print("delta paste of other text (unit case changed, upper-cased):", d1["status"], d1["documentId"],
      "outcome licenceClass:", d1["licenceClass"], "title:", d1["title"])

for name, c in (("gamma", G), ("delta", D), ("nothing", N)):
    docs = c.get("/api/literature/documents").json()
    print(f"\n== {name}: {len(docs)} documents")
    for d in docs:
        print("  ", d["documentId"], "| title:", d["title"], "| class:", d["licenceClass"], "| source:", d["source"],
              "| sourceRef:", d["sourceRef"], "| linkedBy:", d["linkedBy"], "| selection licence:",
              (d["selection"] or {}).get("licence"))
    ov = c.get("/api/biorepo/overlay").json()
    for pid, paper in (ov.get("papers") or {}).items():
        print("   overlay", pid, "| license:", paper.get("license"), "| licenceClass:", paper.get("licenceClass"),
              "| text:", [s["text"][:90] for s in paper.get("sections", [])])
    for q in ("corn stover saccharification glucose", "xylanase loading private passage"):
        s = c.get("/api/literature/search", params={"q": q}).json()
        print(f"   search {q!r}:", [(h["documentId"], h["licenceClass"], h["text"][:50]) for h in s["hits"]],
              "degraded:", s.get("degradedStages"))
    st = c.get("/api/literature/stats").json()
    print("   stats:", json.dumps(st))
