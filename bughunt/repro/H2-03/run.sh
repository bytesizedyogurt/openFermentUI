#!/usr/bin/env bash
# H2-03: after a lock, the state door keeps a runbook row whose lockedAt and lockHash are other than the ones
# runbook_locks keeps, and GET /api/studies/runbooks/{id} answers the row's. A kinetics forecast run (the
# fastest engine run, no BioSTEAM), a study runbook of its finals.product, the lock, then two PUTs of the
# frozen predictions and measures through PUT /api/state/runbooks/{id}:
#   A. lockedAt and lockHash both rewritten (the candidate's case): the page's own lockIntact reads "lock broken"
#   B. lockedAt alone moved back to 2020, the frozen digest kept: the page reads it "locked", intact, at 2020
#   bash bughunt/repro/H2-03/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
DB=bh_r_h2_03_lock
PORT=""
for p in $(seq 9680 9689); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "no free port in 9680-9689"; echo "RESULT: NO-DEFECT"; exit 0; }
O=http://127.0.0.1:$PORT; P=h2-03
mkdir -p "$BH_WORK/H2-03"
W=$(mktemp -d "$BH_WORK/H2-03/run.XXXXXX")
cleanup() {
  bh_svc_stop "$PORT"; PGOPTIONS='-c client_min_messages=warning' bh_db_drop "$DB"
  rm -rf "$W" "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"; rmdir "$BH_WORK/H2-03" 2>/dev/null || true
}
trap cleanup EXIT

api() {  # api METHOD PATH [JSON | @file]: the body on stdout, the status as the last line
  local m="$1" path="$2" body="${3:-}"
  local args=(-s --noproxy '*' -X "$m" -H "X-OpenFerment-Project: $P" -w '\n%{http_code}' "$O$path")
  [ -n "$body" ] && args+=(-H 'content-type: application/json' --data-binary "$body")
  curl "${args[@]}"
}
body() { sed '$d'; }  # the body without the status line

(export PGOPTIONS='-c client_min_messages=warning'; bh_db_fresh "$DB") || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $(BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PORT")  database: $DB (fresh)"
bh_project "$O" "$P" >/dev/null

# One kinetics fit of logistic readings and its forecast: the run the runbook predicts from.
python3 -I - "$W" <<'PY'
import json, math, sys
ts = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24]
X = lambda t: 5.0 / (1 + (5.0 - 0.1) / 0.1 * math.exp(-0.4 * t))
series = [
    {"measureId": "m-x", "label": "biomass", "unit": "g L-1", "role": "biomass",
     "points": [{"t": t, "value": round(X(t), 5), "entryId": f"x{t}", "confirmed": True} for t in ts]},
    {"measureId": "m-p", "label": "ethanol", "unit": "g L-1", "role": "product",
     "points": [{"t": t, "value": round(4.0 * (X(t) - 0.1), 5), "entryId": f"p{t}", "confirmed": True} for t in ts]},
    {"measureId": "m-s", "label": "glucose", "unit": "g L-1", "role": "substrate",
     "points": [{"t": t, "value": round(max(0.0, 60 - 10 * (X(t) - 0.1)), 5), "entryId": f"s{t}", "confirmed": True} for t in ts]},
]
json.dump({"depositionId": "dep-h2-03", "series": series}, open(f"{sys.argv[1]}/fit.json", "w"))
PY
jget() { python3 -I -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
FIT=$(api POST /api/fermos/fit "@$W/fit.json" | body | jget "['kineticArtifactId']")
RUN=$(api POST /api/fermos/forecast "{\"fitArtifactId\":\"$FIT\",\"by\":\"Repro H2-03\"}" | body | jget "['artifactId']")
echo "fit: $FIT  forecast run: $RUN"

api POST /api/studies/runbooks "{\"title\":\"H2-03 lock\",\"runId\":\"$RUN\",\"by\":\"Repro H2-03\",\"predict\":[{\"output\":\"values.finals.product\",\"label\":\"product\"}]}" > "$W/made.txt"
RID=$(body < "$W/made.txt" | jget "['id']")
api POST "/api/studies/runbooks/$RID/lock" '{"by":"Repro H2-03"}' > "$W/lock.txt"
echo "runbook: $RID  made $(tail -1 "$W/made.txt"), locked $(tail -1 "$W/lock.txt")"

# The locked row with only its lock fields rewritten, then the same with the frozen digest kept.
python3 -I - "$W" <<'PY'
import json, sys
w = sys.argv[1]
locked = json.loads(open(f"{w}/lock.txt").read().rsplit("\n", 1)[0])
a = {**locked, "lockedAt": "2020-01-01T00:00:00Z", "lockHash": "0000000000000000"}
b = {**locked, "lockedAt": "2020-01-01T00:00:00Z"}
json.dump({"by": "Repro H2-03", "value": a}, open(f"{w}/put_a.json", "w"))
json.dump({"by": "Repro H2-03", "value": b}, open(f"{w}/put_b.json", "w"))
PY
api PUT "/api/state/runbooks/$RID" "@$W/put_a.json" > "$W/put_a.txt"
api GET "/api/studies/runbooks/$RID" > "$W/get_a.txt"
api GET /api/state > "$W/state_a.txt"
api PUT "/api/state/runbooks/$RID" "@$W/put_b.json" > "$W/put_b.txt"
api GET "/api/studies/runbooks/$RID" > "$W/get_b.txt"
api GET /api/state > "$W/state_b.txt"
api GET "/api/audit?target=$RID" > "$W/audit.txt"
curl -s --noproxy '*' -H "X-OpenFerment-Project: $P" "$O/api/studies/export?by=Repro%20H2-03" -o "$W/pkg.zip"

# The page's verdict on each served row, from the browser's own code (src/engine/lock.ts lockIntact).
for x in a b; do
  node --input-type=module -e "
    import { readFileSync } from 'node:fs';
    const { lockIntact } = await import('$BH_ROOT/src/engine/lock.ts');
    const t = readFileSync('$W/get_$x.txt', 'utf8'); const row = JSON.parse(t.slice(0, t.lastIndexOf('\n')));
    console.log(lockIntact(row) ? 'locked' : 'lock broken');" > "$W/intact_$x.txt" 2>"$W/node_$x.err" || echo "?" > "$W/intact_$x.txt"
done

python3 -I - "$W" "$RID" <<'PY' || echo "RESULT: NO-DEFECT (the steps did not complete; see the lines above)"
import json, sys, zipfile
w, rid = sys.argv[1], sys.argv[2]
def read(name):
    text = open(f"{w}/{name}.txt").read()
    b, _, status = text.rpartition("\n")
    return int(status), (json.loads(b) if b.strip() else None)
_, locked = read("lock")
T, H = locked["lockedAt"], locked["lockHash"]
print(f"POST /api/studies/runbooks/{rid}/lock: lockedAt {T}, lockHash {H}")
res = {}
for x, what in (("a", "lockedAt 2020-01-01T00:00:00Z and lockHash 0000000000000000"),
                ("b", "lockedAt 2020-01-01T00:00:00Z, lockHash the frozen one")):
    s_put, put = read(f"put_{x}")
    s_get, got = read(f"get_{x}")
    _, state = read(f"state_{x}")
    kept = state["runbookLocks"].get(rid, {})
    row = next(r for r in state["runbooks"] if r["id"] == rid)
    same = (got["predictions"], got["measurementSchema"]) == (locked["predictions"], locked["measurementSchema"])
    verdict = open(f"{w}/intact_{x}.txt").read().strip()
    print(f"{x.upper()}. PUT /api/state/runbooks/{rid} with the frozen predictions and measures, {what}: {s_put}")
    print(f"   GET /api/studies/runbooks/{rid}: {s_get} lockedAt {got.get('lockedAt')}, lockHash {got.get('lockHash')}; "
          f"predictions and measures the frozen ones: {same}")
    print(f"   GET /api/state: runbookLocks[{rid}] = {kept.get('lockedAt')}, {kept.get('lockHash')}; "
          f"the row's lockedAt {row.get('lockedAt')}, lockHash {row.get('lockHash')}")
    print(f"   src/engine/lock.ts lockIntact on the served row: {verdict}")
    res[x] = (s_put, got.get("lockedAt"), got.get("lockHash"), kept.get("lockedAt"), kept.get("lockHash"), same, verdict)
_, audit = read("audit")
print("GET /api/audit?target=" + rid + ":", [(x.get("action"), x.get("state")) for x in audit] if isinstance(audit, list) else audit)
md = zipfile.ZipFile(f"{w}/pkg.zip").read("study.md").decode()
line = next((l for l in md.splitlines() if l.startswith("Locked ")), "(no Locked line)")
print(f"export study.md, the runbook's lock line: {line}")
print(f"EXPECTED: each PUT refused in words (a lock is kept as it was made), or the lock runbook_locks keeps "
      f"({T}, {H}) laid over the row's, so GET answers {T} and {H} and the page reads the frozen predictions "
      f"as locked at {T}")
a, b = res["a"], res["b"]
print(f"OBSERVED: A kept {a[0]}, GET answers {a[1]}, {a[2]} and the page reads '{a[6]}' over the frozen "
      f"predictions; B kept {b[0]}, GET answers {b[1]}, {b[2]} and the page reads '{b[6]}' at a moment before "
      f"the lock was made; runbook_locks still holds {a[3]}, {a[4]}")
defect = (a[0] == 200 and a[1] == "2020-01-01T00:00:00Z" and a[2] == "0000000000000000"
          and (a[3], a[4]) == (T, H) and a[5] and a[6] == "lock broken"
          and b[0] == 200 and b[1] == "2020-01-01T00:00:00Z" and b[2] == H and (b[3], b[4]) == (T, H))
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
exit 0
