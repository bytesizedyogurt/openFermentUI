#!/usr/bin/env bash
# H7-01: two tabs on one project while the service is stopped; the browser's one durable snapshot keeps the queue of
# the tab that saved last, so tab A's reading is erased and never reaches the service.
#
#   bash bughunt/repro/H7-01/run.sh        (from the repository root)
#
# A fresh database (bh_r_h7_01_twotabs, made by bh_db_fresh through bh_svc_start), the service on 127.0.0.1:9310 over
# the built app in dist/, one project with one placeholder locked runbook put through the API, then the browser steps in
# twotabs.mjs. Keyless; no model call. Ends with RESULT: DEFECT or RESULT: NO-DEFECT and exits 0; the service is
# stopped and the database and its data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h7_01_twotabs; PORT=9310; ORIGIN=http://127.0.0.1:$PORT; PROJECT=h7-01; RB=rb-h7-01-placeholder
OUT=$BH_WORK/H7-01; mkdir -p "$OUT"; FACTS=$OUT/facts.json; rm -f "$FACTS"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB" "$OUT"; }
trap cleanup EXIT
api() { curl -s --noproxy '*' -H 'Content-Type: application/json' -H "X-OpenFerment-Project: $PROJECT" "$@"; }
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: tab A's reading (5.5 USD/kg) stays in the browser's queue through tab B's save and both tabs closing, and the service holds it once it answers again (ADR-014: a write the service has not yet acknowledged survives a reload and is sent when the service answers)."

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$PROJECT" "H7-01 repro" >/dev/null
# One placeholder runbook, a project row put whole, then locked by the service (the bench waits for a lock).
api -X PUT "$ORIGIN/api/state/runbooks/$RB" -d "{\"by\":\"H7 Repro\",\"value\":{\"id\":\"$RB\",\"kind\":\"research\",
  \"title\":\"H7-01 placeholder runbook\",\"status\":\"draft\",\"predictions\":[{\"id\":\"p1\",\"label\":\"A placeholder output\",
  \"value\":1.0,\"unit\":\"USD/kg\",\"confidence\":\"low\",\"basis\":\"a placeholder\"}],\"measurementSchema\":[{\"id\":\"m1\",
  \"label\":\"A placeholder output\",\"unit\":\"USD/kg\",\"timepoint\":\"harvest\",\"predictionId\":\"p1\"}]}}" >/dev/null
LOCKED=$(api -X POST "$ORIGIN/api/studies/runbooks/$RB/lock" -d '{"by":"H7 Repro"}' | python3 -c "import json,sys; print(bool(json.load(sys.stdin).get('lockedAt')))" 2>/dev/null)
[ "$LOCKED" = True ] || finish "the placeholder runbook was not locked"

(cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 600 \
  node twotabs.mjs "$ORIGIN" "$PROJECT" "$RB" "$DB" "$PORT" "$FACTS") | grep -v '^FACTS '
[ -s "$FACTS" ] || finish "the browser steps wrote no facts"

python3 - "$FACTS" <<'PY'
import json, sys
f = json.load(open(sys.argv[1]))
if f.get("stopped"):
    print(f"OBSERVED: the browser steps stopped: {f['stopped']}")
    print("RESULT: NO-DEFECT"); sys.exit(0)
dep_a, dep_b = f["depA"], f["depB"]
def ids(q): return [e["id"] for e in q] if isinstance(q, list) else []
def entries(h): return (h or {}).get("entries", [])
a_after_a = dep_a in ids(f["afterA"])
a_after_b = dep_a in ids(f["afterB"])
a_closed = dep_a in ids(f["afterClose"])
b_closed = dep_b in ids(f["afterClose"])
held_a, held_b = entries(f["heldA"]), entries(f["heldB"])
print(f"OBSERVED: queue after tab A wrote: {ids(f['afterA'])}; after tab B wrote: {ids(f['afterB'])}; "
      f"with both tabs closed: {ids(f['afterClose'])} (A {dep_a}, B {dep_b}).")
print(f"OBSERVED: once the service answered and a tab opened, the service held A's deposition with {held_a or 'no entries'} "
      f"and B's with {held_b or 'no entries'}; tab A had shown, before it closed: \"{f.get('benchA', '')}\"; "
      f"words on the new tab about a dropped reading: {f.get('warned') or 'none'}.")
# The queue works for the tab that saved last (B's reading reaches the service through it), and A's reading, queued
# first, is gone from the snapshot and never reaches the service.
defect = a_after_a and not a_after_b and not a_closed and b_closed and "6.6 USD/kg" in held_b and "5.5 USD/kg" not in held_a
print("RESULT: " + ("DEFECT" if defect else "NO-DEFECT"))
PY
exit 0
