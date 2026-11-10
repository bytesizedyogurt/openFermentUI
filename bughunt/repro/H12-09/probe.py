"""H12-09 probe: what the guard and the app say to a changing request under a public .net name.

The page and the service look like one site after a DNS rebinding, so Origin matches Host
(guard.py:10-12). Run with the package of the tree under test first on PYTHONPATH, and
OPENFERMENT_DATABASE_URL naming a fresh test database. Prints PROBE lines alone.
"""
from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from openferment_core import api, guard

logging.disable(logging.CRITICAL)
NAME = "rebind.evil.example.net"
HEADERS = {"host": f"{NAME}:8000", "origin": f"http://{NAME}:8000"}

why = guard.refusal("POST", HEADERS)
print(f"PROBE guard.answers_to({NAME!r}) = {guard.answers_to(NAME)}")
print(f"PROBE guard.refusal('POST', Host and Origin {NAME}:8000) = {why!r}")
with TestClient(api.app, base_url=f"http://{NAME}:8000") as client:
    made = client.post("/api/projects", json={"name": "Made through a rebound name", "by": "a hostile page"},
                       headers=HEADERS)
    print(f"PROBE POST /api/projects under Host {NAME}:8000 -> {made.status_code} {made.text[:160]}")
    held = [p["id"] for p in client.get("/api/projects", headers=HEADERS).json()]
    print(f"PROBE projects the database holds after it: {held}")
print(f"PROBE-STATUS {made.status_code}")
