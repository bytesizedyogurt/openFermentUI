"""H8-01's steps against a service over a fresh test database (run.sh starts it).

Usage: python -I probe.py ORIGIN
Project ra pastes a sentence with "2000 Mg"; project rb pastes the same sentence with "2000 mg"
(one letter's case apart). A control: rb pastes it once more with "2000 kg" (one word apart).
Prints what rb was answered and what rb's passages and search read, then the verdict line.
Talks to the local service alone (trust_env off).
"""
from __future__ import annotations

import json
import sys

import httpx

ORIGIN = sys.argv[1]


def client(project: str | None = None) -> httpx.Client:
    h = {"X-OpenFerment-Project": project} if project else {}
    return httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600, headers=h)


def project(pid: str) -> httpx.Client:
    r = client().post("/api/projects", json={"id": pid, "name": pid, "by": "h8-01"})
    assert r.status_code in (200, 201), (r.status_code, r.text)
    return client(pid)


def passages(c: httpx.Client, doc: str) -> str:
    paper = c.get("/api/biorepo/overlay").json()["papers"][doc]
    return " | ".join(s["text"] for s in paper["sections"])


ra, rb = project("ra"), project("rb")
mega = "The biorefinery processes 2000 Mg of dry corn stover per day in the H8-01 repro."
milli = mega.replace("2000 Mg", "2000 mg")
kilo = mega.replace("2000 Mg", "2000 kg")

ga = ra.post("/api/intake/paste", json={"title": "ra's note", "text": mega, "by": "ra"}).json()
gb = rb.post("/api/intake/paste", json={"title": "rb's note", "text": milli, "by": "rb"}).json()
gk = rb.post("/api/intake/paste", json={"title": "rb's control", "text": kilo, "by": "rb"}).json()

held_b = passages(rb, gb["documentId"])
held_k = passages(rb, gk["documentId"])
hits = rb.get("/api/literature/search", params={"q": "corn stover per day"}).json()["hits"]
hit_texts = sorted({h.get("text") or h.get("content") or h.get("quote") or json.dumps(h)[:200] for h in hits})

print("ra pasted:              ", mega)
print("rb pasted:              ", milli)
print("ra's outcome:           ", ga["status"], ga["documentId"])
print("rb's outcome:           ", gb["status"], gb["documentId"], "(same document as ra's)" if gb["documentId"] == ga["documentId"] else "")
print("rb's passage reads:     ", held_b)
print("rb's search hits read:  ", hit_texts)
print("control, rb pasted:     ", kilo)
print("control outcome:        ", gk["status"], gk["documentId"], "| its passage:", held_k)

defect = (gb["status"] == "linked" and gb["documentId"] == ga["documentId"]
          and "2000 Mg" in held_b and "2000 mg" not in held_b)
control_ok = gk["status"] == "ingested" and "2000 kg" in held_k
print("VERDICT:", "DEFECT" if defect else "NO-DEFECT", "| control (one word apart ingested as its own):",
      "yes" if control_ok else "no")
