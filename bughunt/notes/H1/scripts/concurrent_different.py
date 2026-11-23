"""N different mirror runs at once (placeholder-a set to BASE+k): each answer's outputs must echo its own
value, and each must be its own row. usage: concurrent_different.py ORIGIN PROJECT BASE [N]"""
import sys, threading
import httpx

O, P, BASE = sys.argv[1], sys.argv[2], float(sys.argv[3])
N = int(sys.argv[4]) if len(sys.argv) > 4 else 8
barrier = threading.Barrier(N)
got = {}


def go(k):
    c = httpx.Client(trust_env=False, timeout=120)
    v = BASE + k
    barrier.wait()
    r = c.post(f"{O}/api/engines/mirror/run", headers={"X-OpenFerment-Project": P}, json={
        "thing": "reflect", "by": f"asker-{k}", "inputs": [{"name": "placeholder-a", "quantity": {
            "value": v, "unit": "placeholder-unit", "origin": {"kind": "person-assumption", "by": "H1", "at": "2026-11-10"}}}]})
    run = r.json()["run"]
    echoed = next(o["quantity"]["value"] for o in run["outputs"]["values"] if o["name"] == "placeholder-a")
    got[k] = (r.status_code, run["id"], echoed == v, len(run["diagnostics"]))


ts = [threading.Thread(target=go, args=(k,)) for k in range(N)]
[t.start() for t in ts]; [t.join() for t in ts]
print("answers:", [got[k] for k in sorted(got)])
print("distinct rows:", len({g[1] for g in got.values()}), "of", N, "; every answer echoes its own value:",
      all(g[2] for g in got.values()))
