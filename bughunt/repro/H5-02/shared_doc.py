"""H5-02 (and H8-02): a document two projects hold. Project A pastes a text under its own title, licence
class, licence words and url; project B pastes the identical text under its own title and licence class.
Then B's reads (documents, overlay, search, stats) are scanned for what A typed and for the licence class
B stated. Prints EXPECTED:, OBSERVED: and one RESULT: line. ORIGIN in the environment names the service."""
import json
import os

import httpx

C = httpx.Client(base_url=os.environ["ORIGIN"], trust_env=False, timeout=600)
A, B = "h502-a", "h502-b"


def call(method, path, project=None, **kw):
    h = {"X-OpenFerment-Project": project} if project else {}
    r = C.request(method, path, headers=h, **kw)
    if r.status_code >= 400:
        raise SystemExit(f"OBSERVED: {method} {path} as {project} answered {r.status_code} {r.text[:300]}")
    return r.json()


for p in (A, B):
    call("POST", "/api/projects", json={"id": p, "name": p, "by": "bughunt"})

# Text 1 (H5-02's shape): A gives a url and licence words; B gives licence words of its own, no url.
T1 = ("Acetobacter placeholderii H502ONE made gluconic acid from glucose in shaken flasks.\n\n"
      "A second paragraph of the same placeholder text, H502ONE.")
# Text 2 (H8-02's shape): A gives licence words and no url; B gives no licence words.
T2 = ("Zymomonas placeholderii H502TWO made ethanol from xylose in a stirred vessel.\n\n"
      "A second paragraph of the same placeholder text, H502TWO.")
A1 = dict(title="A confidential draft title", text=T1, by="alice", licenceClass="open_commercial",
          licence="CC-BY-4.0 as A states it", url="https://example.org/a-private-place")
B1 = dict(title="B's own title", text=T1, by="bob", licenceClass="restricted",
          licence="all rights reserved as B states it")
A2 = dict(title="A's second title", text=T2, by="alice", licenceClass="restricted",
          licence="A's words: internal use alone")
B2 = dict(title="B's second title", text=T2, by="bob", licenceClass="open_commercial")

out = {}
for key, project, body in (("A1", A, A1), ("B1", B, B1), ("A2", A, A2), ("B2", B, B2)):
    out[key] = call("POST", "/api/intake/paste", project, json=body)
    o = out[key]
    print(f"paste {key} as {project}: status={o['status']} title={o['title']!r} licenceClass={o['licenceClass']} "
          f"documentId={o['documentId']}")

d1, d2 = out["B1"]["documentId"], out["B2"]["documentId"]
same = d1 == out["A1"]["documentId"] and d2 == out["A2"]["documentId"]
print(f"B's documents are A's (one kit row each): {same}; B's statuses: {out['B1']['status']}, {out['B2']['status']}")

# B's reads.
docs = {d["documentId"]: d for d in call("GET", "/api/literature/documents", B)}
overlay = call("GET", "/api/biorepo/overlay", B)["papers"]
hits1 = [h for h in call("GET", "/api/literature/search", B, params={"q": "H502ONE gluconic acid", "topK": 5})["hits"]
         if h["documentId"] == d1]
hits2 = [h for h in call("GET", "/api/literature/search", B, params={"q": "H502TWO ethanol xylose", "topK": 5})["hits"]
         if h["documentId"] == d2]
stats = call("GET", "/api/literature/stats", B)

FIELDS_DOC = ("title", "citation", "source", "sourceRef", "licenceClass")
FIELDS_OV = ("title", "url", "license", "licenceClass")
for name, d, hits in (("text 1", d1, hits1), ("text 2", d2, hits2)):
    row = docs.get(d, {})
    print(f"B GET /api/literature/documents, {name}: "
          + json.dumps({k: row.get(k) for k in FIELDS_DOC} | {"selection.licence": (row.get("selection") or {}).get("licence"),
                                                                "selection.url": (row.get("selection") or {}).get("url")}))
    ov = overlay.get(d, {})
    print(f"B GET /api/biorepo/overlay, {name}: "
          + json.dumps({k: ov.get(k) for k in FIELDS_OV} | {"section headings": sorted({s["heading"] for s in ov.get("sections", [])})}))
    print(f"B GET /api/literature/search, {name}: "
          + json.dumps([{k: h.get(k) for k in ("title", "sectionPath", "citation", "licenceClass")} for h in hits[:1]]))
print("B GET /api/literature/stats: " + json.dumps({"sources": stats["sources"], "license_classes": stats["license_classes"]}))

# What A typed, and what of it reaches B's reads.
A_WORDS = [A1["title"], A1["url"], A1["licence"], A2["title"], A2["licence"], f"project:{A}:"]
reads = {"documents": [docs.get(d1), docs.get(d2)], "overlay": [overlay.get(d1), overlay.get(d2)],
         "search": hits1 + hits2, "stats": stats}
leaks = []
for where, value in reads.items():
    text = json.dumps(value)
    for w in A_WORDS:
        if json.dumps(w)[1:-1] in text:
            leaks.append(f"{where} carries {w!r}")

# The licence class B stated, against the class B's reads serve.
wrong = []
for name, d, stated, hits in (("text 1", d1, B1["licenceClass"], hits1), ("text 2", d2, B2["licenceClass"], hits2)):
    served = {"documents": docs.get(d, {}).get("licenceClass"), "overlay": overlay.get(d, {}).get("licenceClass"),
              "search": hits[0]["licenceClass"] if hits else None}
    for where, cls in served.items():
        if cls is not None and cls != stated:
            wrong.append(f"{name}: B stated {stated}, its {where} read serves {cls}")

print("EXPECTED: B's paste answers 'linked' with B's own title and class, and B's every read of the two documents "
      "serves B's own selection (its titles, its stated classes restricted and open_commercial, its licence words or "
      "none, no url): no title, url, licence words or project id A typed.")
print(f"OBSERVED: B's paste answers: ({out['B1']['status']}, {out['B1']['title']!r}, {out['B1']['licenceClass']}) and "
      f"({out['B2']['status']}, {out['B2']['title']!r}, {out['B2']['licenceClass']}).")
print(f"OBSERVED: A's words in B's reads ({len(leaks)}): " + ("; ".join(leaks) or "none"))
print(f"OBSERVED: licence class in B's reads against B's statement ({len(wrong)}): " + ("; ".join(wrong) or "all agree"))
print("RESULT: " + ("DEFECT" if same and (leaks or wrong) else "NO-DEFECT"))
