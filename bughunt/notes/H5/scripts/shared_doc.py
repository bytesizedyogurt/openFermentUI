"""H5: a document two projects hold. A pastes a text under its own title, licence class and url; B pastes
the identical text under another title and licence class. Prints what each project's reads say of the
document: the title, source, sourceRef, licence class and url B sees are A's."""
import json
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import call, j

TEXT = ("Acetobacter placeholderii H5SHARED2 made gluconic acid from glucose in shaken flasks.\n\n"
        "A second paragraph of the same placeholder text, H5SHARED2.")
a = j(call("POST", "/api/intake/paste", "bh-a", json={
    "title": "A confidential draft title", "text": TEXT, "by": "alice", "licenceClass": "open_commercial",
    "licence": "CC-BY-4.0 as A states it", "url": "https://example.org/a-private-place"}))
b = j(call("POST", "/api/intake/paste", "bh-b", json={
    "title": "B's own title", "text": TEXT, "by": "bob", "licenceClass": "restricted",
    "licence": "all rights reserved as B states it"}))
print("A's paste answer:", json.dumps(a))
print("B's paste answer:", json.dumps(b))
doc = b.get("documentId")
for p in ("bh-a", "bh-b"):
    docs = [d for d in j(call("GET", "/api/literature/documents", p)) if d["documentId"] == doc]
    print(p, "literature/documents:", json.dumps({k: docs[0].get(k) for k in ("title", "citation", "source", "sourceRef", "licenceClass")}) if docs else None)
    ov = j(call("GET", "/api/biorepo/overlay", p))["papers"].get(doc, {})
    print(p, "overlay paper:", json.dumps({k: ov.get(k) for k in ("title", "url", "license", "licenceClass", "source")}))
    hits = j(call("GET", "/api/literature/search", p, params={"q": "H5SHARED2 gluconic", "topK": 3}))
    print(p, "search hits:", [(h["title"], h.get("licenceClass") or h.get("licence_class")) for h in hits.get("hits", [])])
