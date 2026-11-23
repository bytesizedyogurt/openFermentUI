"""H5-01: project B's literature search returns a document project A ingests while the search runs.

Steps against a service on a fresh database (run.sh starts it):
  1. projects bh-a and bh-b;
  2. A pastes a seed text, then B pastes the same text: the kit stores it once under A's source
     `project:bh-a:paste`, so B's allowlist names A's source and B's exclusion list names A's other
     documents of that source as they stand when B's search reads them (kit.visible);
  3. A pastes up to N private notes, one at a time, while B searches /api/literature/search in a loop;
  4. any hit B receives on a document B does not hold, and A does hold, is A's document read from B.
Prints EXPECTED:, OBSERVED: and one RESULT: line."""
import json
import os
import sys
import threading
import time

import httpx

ORIGIN = os.environ["H501_ORIGIN"]
N = int(os.environ.get("H501_N", "60"))
A, B = "bh-a", "bh-b"
MARK = "RACEMARKH501"
stop = threading.Event()
made: list[str] = []
seen: list[dict] = []
searches = 0


def client() -> httpx.Client:
    return httpx.Client(base_url=ORIGIN, trust_env=False, timeout=120)


def hdr(p: str) -> dict:
    return {"X-OpenFerment-Project": p}


def a_pastes() -> None:
    c = client()
    for i in range(N):
        if stop.is_set():
            break
        r = c.post("/api/intake/paste", headers=hdr(A), json={
            "title": f"A private note {i}", "by": "alice",
            "text": f"{MARK} appears in A's private race note number {i} with token {MARK}N{i}."})
        made.append(r.json().get("documentId"))
    stop.set()


def b_searches() -> None:
    global searches
    c = client()
    while not stop.is_set():
        r = c.get("/api/literature/search", headers=hdr(B), params={"q": f"{MARK} race note", "topK": 10})
        searches += 1
        for h in r.json().get("hits", []):
            if "private race note" in h["text"]:
                seen.append({"documentId": h["documentId"], "passageId": h["passageId"],
                             "title": h["title"], "text": h["text"][:90]})
                # one leak is enough: let A finish the paste in flight, then stop
                stop.set()


c = client()
for pid, by in ((A, "alice"), (B, "bob")):
    r = c.post("/api/projects", json={"id": pid, "name": pid, "by": by})
    assert r.status_code == 201, (pid, r.status_code, r.text[:200])
SEED = f"A seed text {MARK}-SEED that both projects paste, about placeholder growth on a placeholder sugar."
for pid, by in ((A, "alice"), (B, "bob")):
    r = c.post("/api/intake/paste", headers=hdr(pid), json={"title": f"seed by {by}", "text": SEED, "by": by})
    print(f"step: {pid} pastes the seed -> {r.json().get('status')} {r.json().get('documentId')}")
docs_b = c.get("/api/literature/documents", headers=hdr(B)).json()
print("step: B holds", len(docs_b), "document(s), kit source(s):", sorted({d.get("source", "?") for d in docs_b}))
# warm the embedder so the race starts at once
c.get("/api/literature/search", headers=hdr(B), params={"q": "warm", "topK": 1})

t0 = time.time()
tb, ta = threading.Thread(target=b_searches), threading.Thread(target=a_pastes)
tb.start(); time.sleep(0.3); ta.start(); ta.join(); tb.join()
print(f"step: A pasted {len(made)} private notes while B searched {searches} times ({time.time() - t0:.1f} s)")

held_b = {d["documentId"] for d in c.get("/api/literature/documents", headers=hdr(B)).json()}
held_a = {d["documentId"] for d in c.get("/api/literature/documents", headers=hdr(A)).json()}
leaks = {s["documentId"]: s for s in seen if s["documentId"] not in held_b}
for s in leaks.values():
    s["heldByA"], s["heldByB"] = s["documentId"] in held_a, s["documentId"] in held_b
    print("leak:", json.dumps(s))
after = c.get("/api/literature/search", headers=hdr(B), params={"q": f"{MARK} race note", "topK": 10}).json()["hits"]
n_after = sum("private race note" in h["text"] for h in after)
print(f"step: one search from B after A stopped returns {n_after} of A's notes ({len(after)} hits)")

print("EXPECTED: every hit B's /api/literature/search returns is a passage of a document B holds; "
      "none of A's private notes, during A's ingestion or after it")
a_owned = [s for s in leaks.values() if s["heldByA"]]
print(f"OBSERVED: {len(leaks)} distinct A-only document(s) came back in B's hits while A ingested "
      f"({len(a_owned)} held by A, 0 held by B), each with a passage id: "
      + ", ".join(f"'{s['title']}' {s['passageId']}" for s in leaks.values())
      + f"; after A stopped, B's search returns {n_after}")
print("RESULT: DEFECT" if a_owned else "RESULT: NO-DEFECT")
