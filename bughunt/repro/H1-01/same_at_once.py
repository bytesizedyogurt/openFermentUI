"""H1-01: N identical kinetics runs asked at once, each naming its own asker as `by`.
For each VALUE (mu_max set to it, so each value is a run no one has asked for before):
the ids and `by` each asker was answered with, the runs row's created_by column beside its body's
by, and what GET /api/runs/{id} serves. Prints one CASE line a value, DEFECT or OK.
usage: same_at_once.py ORIGIN PROJECT DB INPUTS_FILE N VALUE [VALUE ...]"""
import json
import subprocess
import sys
import threading

import httpx

O, P, DB, INPUTS, N = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
VALUES = [float(v) for v in sys.argv[6:]]
SERVER = "postgresql://openferment:openferment@127.0.0.1:5432"
H = {"X-OpenFerment-Project": P}


def running(rid: str) -> int:
    """How many job.running events the project's event stream holds for run `rid`: one an ask that computed."""
    n = 0
    try:
        with httpx.Client(trust_env=False, timeout=httpx.Timeout(10, read=2)) as c:
            with c.stream("GET", f"{O}/api/events?after=0", headers=H) as r:
                for line in r.iter_lines():
                    if line.startswith("data:"):
                        e = json.loads(line[5:])
                        n += e.get("type") == "job.running" and (e.get("data") or {}).get("id") == rid
    except httpx.ReadTimeout:
        pass
    return n


def case(value: float) -> bool:
    print(f"value mu_max={value}, {N} asks at once:")
    values = json.load(open(INPUTS))
    values[0]["quantity"]["value"] = value
    barrier = threading.Barrier(N)
    said: dict[int, tuple] = {}

    def go(k: int) -> None:
        with httpx.Client(trust_env=False, timeout=300) as c:
            barrier.wait()
            r = c.post(f"{O}/api/engines/kinetics/run", headers=H,
                       json={"thing": "batch_v1", "inputs": values, "by": f"asker-{k}"})
            said[k] = ((r.status_code, r.json()["run"]["id"], r.json()["run"]["by"]) if r.status_code == 200
                       else (r.status_code, r.text[:160], None))

    ts = [threading.Thread(target=go, args=(k,)) for k in range(N)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    for k in sorted(said):
        print(f"  asker-{k} answered: status {said[k][0]}, run {said[k][1]}, by {said[k][2]!r}")
    ids = sorted({s[1] for s in said.values() if s[0] == 200})
    answered_by = sorted({s[2] for s in said.values() if s[0] == 200})
    bad = len(ids) != 1 or len(answered_by) != 1 or any(s[0] != 200 for s in said.values())
    for rid in ids:
        q = (f"select created_by, body->>'by' from openferment.runs "
             f"where project_id='{P}' and id='{rid}'")
        row = subprocess.run(["psql", f"{SERVER}/{DB}", "-AtXc", q], capture_output=True, text=True).stdout.strip()
        created_by, body_by = (row.split("|") + [None, None])[:2]
        with httpx.Client(trust_env=False, timeout=60) as c:
            served = c.get(f"{O}/api/runs/{rid}", headers=H).json()["run"]["by"]
        print(f"  row {rid}: created_by {created_by!r}, body by {body_by!r}; GET /api/runs/{rid} serves by {served!r}")
        print(f"  job.running events for {rid}: {running(rid)} (one an ask that computed)")
        if created_by != body_by or served != created_by:
            bad = True
        if answered_by and answered_by != [created_by]:
            bad = True
    print(f"CASE mu_max={value}: {len(ids)} row id(s), askers answered by {answered_by}: {'DEFECT' if bad else 'OK'}")
    return bad


hits = [case(v) for v in VALUES]
print(f"SUMMARY: {sum(hits)} of {len(VALUES)} values gave a row whose names disagree")
sys.exit(0)
