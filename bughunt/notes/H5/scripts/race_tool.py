"""H5 (the tool door, search_passages, the evidence Postdoc and MCP clients cite): as race.py.

H5: B's literature search reads a document A ingests while the search runs. B holds one document whose
kit source is A's (`project:bh-a:paste`, after B pasted a text A had pasted first), so the kit's allowlist for
B names A's source and its exclusion list names A's other documents of that source as they stood when B's
search began (kit.visible). A pastes new documents while B searches; any hit of B's that is a document B
never held is a document of A's read from B. Prints each one found."""
import json
import sys
import threading
import time

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import ORIGIN

import httpx

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
stop = threading.Event()
made: list[str] = []
seen: list[dict] = []


def a_pastes():
    c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=120)
    for i in range(N):
        r = c.post("/api/intake/paste", headers={"X-OpenFerment-Project": "bh-a"}, json={
            "title": f"A race {i}", "by": "alice",
            "text": f"RACETOOLQX appears in A's private race note number {i} with token RACETOOLQX{i}."})
        made.append(r.json().get("documentId"))
    stop.set()


def b_searches():
    c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=120)
    n = 0
    while not stop.is_set():
        r = c.post("/api/tools/search_passages?by=bob", headers={"X-OpenFerment-Project": "bh-b"},
                  json={"query": "RACETOOLQX race note", "k": 6})
        n += 1
        for h in (r.json().get("summary") or {}).get("passages", []):
            if "RACETOOLQX" in json.dumps(h) and "SEED" not in json.dumps(h):
                seen.append({"documentId": h.get("paperId"), "title": h.get("paperTitle"), "text": json.dumps(h)[:160]})
    print("B searched", n, "times")


# B comes to hold a document whose kit source is A's: A pastes a text first, B pastes the same text.
seed = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=120)
SEED = "A seed text RACETOOLQX-SEED that both projects paste, about Saccharomyces placeholder growth on glucose."
for pid, by in (("bh-a", "alice"), ("bh-b", "bob")):
    print(pid, "pastes the seed:", seed.post("/api/intake/paste", headers={"X-OpenFerment-Project": pid},
                                          json={"title": f"seed by {by}", "text": SEED, "by": by}).json().get("status"))
t1, t2 = threading.Thread(target=a_pastes), threading.Thread(target=b_searches)
t2.start(); time.sleep(0.5); t1.start(); t1.join(); t2.join()
c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=120)
held_b = {d["documentId"] for d in c.get("/api/literature/documents", headers={"X-OpenFerment-Project": "bh-b"}).json()}
leaks = [s for s in seen if s["documentId"] not in held_b]
print("A pasted", len(made), "documents; B's hits on A's race notes:", len(leaks))
for s in {s["documentId"]: s for s in leaks}.values():
    print(json.dumps(s))
after = (c.post("/api/tools/search_passages?by=bob", headers={"X-OpenFerment-Project": "bh-b"},
               json={"query": "RACETOOLQX race note", "k": 6}).json().get("summary") or {}).get("passages", [])
print("a search from B after A stopped finds", sum("private race note" in json.dumps(h) for h in after), "race notes")
