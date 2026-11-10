"""N identical kinetics runs at once (POST /api/engines/kinetics/run, batch_v1 with conform's placeholder
values and mu_max set to VALUE), each naming a different asker; then the row's created_by column against
its body's by. usage: concurrent_kinetics.py ORIGIN PROJECT DB INPUTS_FILE VALUE [N]"""
import json, subprocess, sys, threading
import httpx

O, P, DB, INPUTS, VALUE = sys.argv[1:6]
N = int(sys.argv[6]) if len(sys.argv) > 6 else 4
values = json.load(open(INPUTS))
values[0]["quantity"]["value"] = float(VALUE)
barrier = threading.Barrier(N)
said = {}


def go(k):
    c = httpx.Client(trust_env=False, timeout=300)
    barrier.wait()
    r = c.post(f"{O}/api/engines/kinetics/run", json={"thing": "batch_v1", "inputs": values, "by": f"asker-{k}"},
               headers={"X-OpenFerment-Project": P})
    said[k] = (r.status_code, r.json()["run"]["id"] if r.status_code == 200 else r.text[:200],
               r.json()["run"]["by"] if r.status_code == 200 else None)


ts = [threading.Thread(target=go, args=(k,)) for k in range(N)]
[t.start() for t in ts]; [t.join() for t in ts]
for k in sorted(said):
    print(f"asker-{k}: {said[k]}")
ids = {v[1] for v in said.values() if v[0] == 200}
for rid in ids:
    q = f"select id, created_by, body->>'by' from openferment.runs where project_id='{P}' and id='{rid}'"
    print("row:", subprocess.run(["psql", f"postgresql://openferment:openferment@127.0.0.1:5432/{DB}", "-AtXc", q],
                                 capture_output=True, text=True).stdout.strip())
