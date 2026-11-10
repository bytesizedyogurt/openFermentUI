#!/usr/bin/env bash
# H7-02: a reload while the service is away leaves the project's rows unloaded; the bench says the deposition is not
# found while its reading waits in the browser's queue, and once the service answers nothing is sent until a second
# reload.
#
#   bash bughunt/repro/H7-02/run.sh        (from the repository root)
#
# Two ways of the service being away, each on a fresh database (bh_db_fresh through bh_svc_start) with the service on
# its own port over the built app in dist/, one project with one placeholder locked runbook put through the API:
#   refuse  (127.0.0.1:9040, bh_r_h7_02_refuse): every /api request the page makes refused at the browser.
#   dbaway  (127.0.0.1:9041, bh_r_h7_02_dbaway): the service keeps serving the page and its database takes no
#           connection, so every /api call answers 500; the shipped one-origin deployment can reload this way.
# Keyless; no model call. RESULT keys on the refuse run, the candidate's own scenario; the dbaway run is reported
# beside it. Exits 0; services stopped, databases and their data copies removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
PROJECT=h7-02; RB=rb-h7-02-placeholder
OUT=$BH_WORK/H7-02; mkdir -p "$OUT"; rm -f "$OUT"/facts-*.json
cleanup() {
  for p in 9040 9041; do bh_svc_stop $p; done
  for d in bh_r_h7_02_refuse bh_r_h7_02_dbaway; do
    psql "$BH_SERVER/postgres" -qXc "ALTER DATABASE \"$d\" ALLOW_CONNECTIONS true" >/dev/null 2>&1
    bh_db_drop $d; rm -rf "$BH_WORK/data-$d"
  done
  rm -rf "$OUT"
}
trap cleanup EXIT

echo "EXPECTED: after a reload while the service is away, the bench shows the deposition with its queued reading laid over it, and once the service answers the queue is sent with no further reload (ADR-014: \"a decision made while the service is away survives a reload and is sent when the service answers\"; src/lib/projectState.ts: \"a deposition at the bench survives a reload while the service is away and is sent when it answers again\")."

# scenario AWAY DB PORT: the service, the project, the locked runbook, then the browser steps; facts in $OUT/facts-AWAY.json.
scenario() {
  local away=$1 db=$2 port=$3 origin=http://127.0.0.1:$3
  api() { curl -s --noproxy '*' -H 'Content-Type: application/json' -H "X-OpenFerment-Project: $PROJECT" "$@"; }
  bh_svc_start "$db" "$port" >/dev/null || { echo "{\"stopped\":\"the service did not start on $port\"}" > "$OUT/facts-$away.json"; return; }
  bh_project "$origin" "$PROJECT" "H7-02 repro" >/dev/null
  api -X PUT "$origin/api/state/runbooks/$RB" -d "{\"by\":\"H7-02 Repro\",\"value\":{\"id\":\"$RB\",\"kind\":\"research\",
    \"title\":\"H7-02 placeholder runbook\",\"status\":\"draft\",\"predictions\":[{\"id\":\"p1\",\"label\":\"A placeholder output\",
    \"value\":1.0,\"unit\":\"USD/kg\",\"confidence\":\"low\",\"basis\":\"a placeholder\"}],\"measurementSchema\":[{\"id\":\"m1\",
    \"label\":\"A placeholder output\",\"unit\":\"USD/kg\",\"timepoint\":\"harvest\",\"predictionId\":\"p1\"}]}}" >/dev/null
  local locked
  locked=$(api -X POST "$origin/api/studies/runbooks/$RB/lock" -d '{"by":"H7-02 Repro"}' | python3 -c "import json,sys; print(bool(json.load(sys.stdin).get('lockedAt')))" 2>/dev/null)
  [ "$locked" = True ] || { echo '{"stopped":"the placeholder runbook was not locked"}' > "$OUT/facts-$away.json"; bh_svc_stop "$port"; return; }
  echo "== $away: service on $port over $db"
  (cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 400 \
    node reload.mjs "$origin" "$PROJECT" "$RB" "$db" "$away" "$OUT/facts-$away.json")
  bh_svc_stop "$port"
}

scenario refuse bh_r_h7_02_refuse 9040
scenario dbaway bh_r_h7_02_dbaway 9041

python3 - "$OUT/facts-refuse.json" "$OUT/facts-dbaway.json" <<'PY'
import json, os, sys
def load(p):
    try: return json.load(open(p))
    except Exception as e: return {"stopped": f"no facts ({e})"}
def queued(q, dep):
    return [e for e in q if isinstance(e, dict) and e.get("id") == dep] if isinstance(q, list) else []
def entries(h): return (h or {}).get("entries") if isinstance(h, dict) else None
def judge(f):
    if f.get("stopped"): return False, f"the browser steps stopped: {f['stopped']}"
    dep = f["dep"]
    q_reload = queued(f.get("outboxAfterReload"), dep)
    in_queue = any("4.4 USD/kg" in e.get("entries", []) for e in q_reload)
    no_reload, second = entries(f.get("heldNoReload")) or [], entries(f.get("heldSecondReload")) or []
    defect = (in_queue and f.get("reloadState") == "missing" and "4.4 USD/kg" not in no_reload
              and "4.4 USD/kg" in second)
    words = (f"[{f['away']}] before the reload, service away, the bench said: \"{f.get('benchBefore', '')[:160]}\" "
             f"(words about a write waiting for the service: {f.get('waitWordsBefore') or 'none'}). "
             f"After a reload, service still away: bench data-state={f.get('reloadState')}, \"{f.get('reloadText', '')[:170]}\"; "
             f"the IndexedDB queue held {dep} with {q_reload[0]['entries'] if q_reload else 'nothing'} and "
             f"{q_reload[0]['observations'] if q_reload else 0} observation(s). "
             f"45 s after the service answered, no reload: the service held {no_reload or 'no entries'} "
             f"(bench data-state={f.get('benchNoReload')}, queue {len(queued(f.get('outboxNoReload'), dep))} entr(y/ies) for it). "
             f"Within 30 s of a second reload: the service held {second or 'no entries'} "
             f"with {(f.get('heldSecondReload') or {}).get('observations', 0)} observation(s); queue after: {f.get('outboxSecondReload')}.")
    return defect, words
d_refuse, w_refuse = judge(load(sys.argv[1]))
d_db, w_db = judge(load(sys.argv[2]))
print(f"OBSERVED: {w_refuse}")
print(f"OBSERVED: {w_db}")
print(f"OBSERVED: the defect shows with /api refused at the browser: {'yes' if d_refuse else 'no'}; "
      f"with the service up and its database away (the one-origin deployment): {'yes' if d_db else 'no'}.")
print("RESULT: " + ("DEFECT" if d_refuse else "NO-DEFECT"))
PY
exit 0
