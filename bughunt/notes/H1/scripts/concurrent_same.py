"""Two (or N) identical engine runs at once, each naming a different person as `by`, on a value no
run has set before; then the row's body `by` against its created_by column, and how each ask ended.
usage: concurrent_same.py ORIGIN PROJECT DB VALUE [N]"""
import json, sys, threading, subprocess
import httpx
origin, project, dbname, value = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
n = int(sys.argv[5]) if len(sys.argv) > 5 else 2
body = lambda who: {"thing": "reflect", "by": who, "inputs": [{"name": "placeholder-a", "quantity": {
    "value": value, "unit": "placeholder-unit", "origin": {"kind": "person-assumption", "by": "A. Person", "at": "2026-10-30"}}}]}
out = [None] * n
barrier = threading.Barrier(n)
def go(k):
    c = httpx.Client(trust_env=False, timeout=120)
    barrier.wait()
    r = c.post(f"{origin}/api/engines/mirror/run", json=body(f"asker-{k}"), headers={"X-OpenFerment-Project": project})
    out[k] = (r.status_code, r.text)
    if r.status_code == 200:
        print(f"asker-{k} was answered run {r.json()['run']['id']} by {r.json()['run']['by']!r}")
ts = [threading.Thread(target=go, args=(k,)) for k in range(n)]
[t.start() for t in ts]; [t.join() for t in ts]
for k, (code, text) in enumerate(out):
    try:
        run = json.loads(text if code != 200 else "{}")
    except Exception:
        run = None
    print(k, code, text[:200] if code != 200 else "")
ids = set()
for k, (code, text) in enumerate(out):
    pass
c = httpx.Client(trust_env=False)
runs = c.get(f"{origin}/api/runs?engine=mirror", headers={"X-OpenFerment-Project": project}).json()
mine = [r for r in runs if any(i["name"] == "value placeholder-a" and i["quantity"]["value"] == value for i in r["inputs"])]
for r in mine:
    q = f"select id, created_by, body->>'by', body->>'at' from openferment.runs where project_id='{project}' and id='{r['id']}'"
    print("row:", subprocess.run(["psql", f"postgresql://openferment:openferment@127.0.0.1:5432/{dbname}", "-Atc", q],
                                 capture_output=True, text=True).stdout.strip())
print("rows for this value:", len(mine))
