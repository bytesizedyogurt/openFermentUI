"""H12-04 probe: a rebinding page reached through a proxy that rewrites Host.

The browser names the hostile site in Origin; a proxy in front of the service (one that rewrites Host, the case
test_request_guard.py:99-103 lets through for the owner's own name) puts its own loopback address in Host and the
name the browser used in X-Forwarded-Host. The probe sends that POST to /api/projects through the app's own
middleware stack (fastapi TestClient, the tree on PYTHONPATH first) over the database OPENFERMENT_DATABASE_URL
names, then lists the projects with a plain read, and prints one line for each.
Run from a tree's core/ with the repository's Python: prints PROBE status=... and PROBE made=...
"""
from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from openferment_core import guard
from openferment_core.api import app

PID = sys.argv[1] if len(sys.argv) > 1 else "rebound-write"
HOSTILE = {
    "host": "127.0.0.1:8000",                      # the proxy's own loopback address
    "origin": "http://rebind.evil.example.com",    # the page the browser is on
    "x-forwarded-host": "rebind.evil.example.com", # the name the browser used, set by the proxy
}

print("PROBE guard.py loaded from", guard.__file__)
print("PROBE guard.refusal('POST', headers) =", repr(guard.refusal("POST", HOSTILE)))
c = TestClient(app)
r = c.post("/api/projects", json={"id": PID, "name": "made by a rebound page", "by": "rebind.evil.example.com"},
           headers=HOSTILE)
detail = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else r.text
print(f"PROBE status={r.status_code} detail={detail!r}")
listed = c.get("/api/projects", headers={"host": "127.0.0.1:8000"})
ids = [p["id"] for p in listed.json()]
print(f"PROBE made={'yes' if PID in ids else 'no'} projects={ids}")
