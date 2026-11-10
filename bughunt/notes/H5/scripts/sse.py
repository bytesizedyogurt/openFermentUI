"""H5: the event stream. B opens GET /api/events?project=bh-b while A makes a run (job.*, artifact.kept) and
a tool call; B's stream must carry none of A's events. Then B reconnects with Last-Event-ID 0 and with an id
taken from A's own stream, and with ?after=0; the replay must hold none of A's events either. Also the header
naming B over ?project=bh-a, and A's stream for comparison."""
import json
import sys
import threading
import time

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import ORIGIN, OUT

import httpx

ids = json.load(open(f"{OUT}/a_ids.json"))


def read(url, headers, seconds, into):
    c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=None)
    buf = ""
    try:
        with c.stream("GET", url, headers=headers, timeout=httpx.Timeout(seconds + 5, read=seconds + 5)) as r:
            into.append(("status", r.status_code))
            start = time.time()
            for chunk in r.iter_text():
                buf += chunk
                if time.time() - start > seconds:
                    break
    except httpx.ReadTimeout:
        pass
    events = []
    for block in buf.split("\n\n"):
        data = [l[6:] for l in block.splitlines() if l.startswith("data: ")]
        if data:
            events.append(json.loads("".join(data)))
    into.append(("events", events))


def act_in_a():
    c = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=300)
    inputs = [dict(i) for i in ids["kinetics_inputs"]]
    inputs[1] = {"name": "ks", "quantity": {**inputs[1]["quantity"], "value": 0.6 + time.time() % 1 / 10}}
    r = c.post("/api/engines/kinetics/run", headers={"X-OpenFerment-Project": "bh-a"},
               json={"thing": "batch_v1", "by": "alice", "inputs": inputs})
    print("A's run:", r.status_code)
    r = c.post("/api/tools/study_read?by=alice", headers={"X-OpenFerment-Project": "bh-a"}, json={})
    print("A's tool call:", r.status_code)


got = {k: [] for k in ("a", "b", "b_hdr_over_query", "none")}
threads = [threading.Thread(target=read, args=("/api/events?project=bh-a", {}, 8, got["a"])),
           threading.Thread(target=read, args=("/api/events?project=bh-b", {}, 8, got["b"])),
           threading.Thread(target=read, args=("/api/events?project=bh-a", {"X-OpenFerment-Project": "bh-b"}, 8,
                                               got["b_hdr_over_query"])),
           threading.Thread(target=read, args=("/api/events", {}, 3, got["none"]))]
for t in threads:
    t.start()
time.sleep(1.0)
act_in_a()
for t in threads:
    t.join()
for k, v in got.items():
    ev = dict(v).get("events", [])
    print(k, "status", dict(v).get("status"), "events", [(e["id"], e["type"], e["project"]) for e in ev][:12])
a_ids = [e["id"] for e in dict(got["a"]).get("events", [])]
first = min(a_ids) if a_ids else 1
for label, url, hdr in (("B Last-Event-ID 0", "/api/events?project=bh-b", {"Last-Event-ID": "0"}),
                        ("B Last-Event-ID A-1", "/api/events?project=bh-b", {"Last-Event-ID": str(first - 1)}),
                        ("B after=0", "/api/events?project=bh-b&after=0", {}),
                        ("B after=-5", "/api/events?project=bh-b&after=-5", {}),
                        ("A Last-Event-ID 0", "/api/events?project=bh-a", {"Last-Event-ID": "0"})):
    into = []
    read(url, hdr, 2, into)
    ev = dict(into).get("events", [])
    print(label, "status", dict(into).get("status"), "replayed", len(ev), "of projects", sorted({e["project"] for e in ev}))
