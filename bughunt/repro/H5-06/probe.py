"""H5-06 probe: requests that name no project, against a keyless service over a fresh test database.

One project (bh-a) holds a product, a strain and a skill. Each route is asked twice, with
X-OpenFerment-Project: bh-a and with no project named, and its status and words are printed. The
contract (ADR-005; api.py's DESCRIPTION) is a 422 in words naming X-OpenFerment-Project at the first
store call of a request that names none. Prints EXPECTED, OBSERVED and RESULT lines."""
import json
import os
import sys

import httpx

O = os.environ["ORIGIN"]
HDR = "X-OpenFerment-Project"
A = {HDR: "bh-a"}
c = httpx.Client(base_url=O, trust_env=False, timeout=60)


def call(method, path, headers=None, **kw):
    r = c.request(method, path, headers=headers or {}, **kw)
    try:
        body = r.json()
    except ValueError:
        body = r.text
    return r.status_code, body


def words(body):
    if isinstance(body, dict):
        for k in ("detail", "error", "why"):
            if body.get(k):
                return str(body[k])
    return json.dumps(body, ensure_ascii=False)


def keep(kind, entry):
    s, b = call("POST", f"/api/catalogues/{kind}", A, json={"by": "alice", "entry": {"kind": kind, **entry}})
    print(f"  kept {kind} {entry['id']} in bh-a: {s}")
    if s != 200:
        print(f"  {words(b)[:300]}")
        sys.exit(f"setup failed at {kind}")


s, b = call("POST", "/api/projects", json={"id": "bh-a", "name": "bh-a", "by": "alice"})
print(f"setup: project bh-a: {s}")
keep("product", {"id": "product-a", "name": "Product A", "category": "industrial_enzyme",
                 "sequence": "MKTAYIAKQR", "sequenceSource": "a placeholder typed for this reproduction"})
keep("strain", {"id": "strain-a", "name": "Strain A", "species": "Placeholder species A"})
keep("skill", {"id": "SK-A", "name": "Skill A", "family": "placeholder", "mastery": ["criterion"],
               "criticality": "routine", "recencyDays": 30, "supervisedRuns": 1})

EVIDENCE = {"id": "e-aaaa1", "personId": "p-a", "skillId": "SK-A", "kind": "knowledge", "at": "2026-11-10T07:00:00Z",
            "source": {"kind": "lesson", "ref": "lesson-a"}, "raw": "x", "outcome": "pass"}
PROBES = [
    ("GET /api/audit", "GET", "/api/audit", {}),
    ("GET /api/catalogues/product", "GET", "/api/catalogues/product", {}),
    ("GET /api/protparam?product=product-a", "GET", "/api/protparam", {"params": {"product": "product-a"}}),
    ("POST /api/pureos/propose", "POST", "/api/pureos/propose", {"json": {"host": "strain-a", "product": "product-a"}}),
    ("POST /api/guild/check", "POST", "/api/guild/check", {"json": EVIDENCE}),
    ("POST /api/guild/evidence", "POST", "/api/guild/evidence", {"json": EVIDENCE}),
    ("POST /api/tools/catalogue_read?by=bob", "POST", "/api/tools/catalogue_read",
     {"params": {"by": "bob"}, "json": {"kind": "product"}}),
    ("POST /api/tools/literature_document?by=bob", "POST", "/api/tools/literature_document",
     {"params": {"by": "bob"}, "json": {"document": "0123456789abcdef0123456789abcdef"}}),
]

print()
broken = []
for label, method, path, kw in PROBES:
    s1, b1 = call(method, path, A, **kw) if not label.endswith("evidence") else (None, None)
    s0, b0 = call(method, path, None, **kw)
    w0 = words(b0)
    ok = s0 == 422 and HDR in w0
    if label.endswith("evidence"):
        print(f"{label}")
    else:
        print(f"{label}\n  naming bh-a: {s1} {words(b1)[:200]}")
    print(f"  naming none: {s0} {w0[:260]}")
    print(f"  as the contract says (422 naming {HDR}): {'yes' if ok else 'no'}")
    if not ok:
        broken.append(f"{label} {s0}")

print()
control = [p for p in ("GET /api/audit", "GET /api/catalogues/product") if not any(b.startswith(p + " ") for b in broken)]
print(f"EXPECTED: every request naming no project, once it reaches a store read, answers 422 in words naming {HDR} "
      "(ADR-005 Implementation; api.py DESCRIPTION), as GET /api/audit does")
print(f"OBSERVED: {len(broken)} of {len(PROBES)} answer otherwise: " + "; ".join(broken)
      + f". Answering as the contract says: {', '.join(control) or 'none'}")
defect = len(control) == 2 and any(b.startswith(("GET /api/protparam", "POST /api/pureos/propose", "POST /api/guild/check"))
                                   for b in broken)
print(f"RESULT: {'DEFECT' if defect else 'NO-DEFECT'}")
