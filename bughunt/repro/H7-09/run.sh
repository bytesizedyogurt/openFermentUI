#!/usr/bin/env bash
# H7-09: Settings' Storage row and durable.ts's header say a deposition at hour 14 with timers running cannot be lost
# to a page reload; a deposition's run at the bench keeps its step, timers and deviation notes in page memory alone,
# and one reload ends the run and loses them.
#
#   bash bughunt/repro/H7-09/run.sh        (from the repository root)
#
# The static half: the four sentences as the tree has them (Settings.tsx, durable.ts, Deposition.tsx,
# ProtocolDetail.tsx), and the store's snapshot and save subscription, which name no run. The live half: a fresh
# database (bh_r_h7_09_reload, made by bh_db_fresh through bh_svc_start), a keyless service on 127.0.0.1:9213 over the
# built app in dist/, one project with one placeholder locked runbook and one placeholder three-step protocol (the
# second step timed) put through the API, then reload.mjs in Chromium at 810x1080: Settings' Storage row read, a
# deposition started from the runbook with the protocol, a deviation note recorded, the timer started, the browser's
# IndexedDB snapshot read, one reload with the leave-page prompt accepted, the screen and the snapshot read again.
# No model call. Ends with RESULT: DEFECT or RESULT: NO-DEFECT and exits 0; the service is stopped and the database
# and its data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h7_09_reload; PORT=9213; ORIGIN=http://127.0.0.1:$PORT; PROJECT=h7-09; RB=rb-h7-09-placeholder
PROTO_ID=h7-09-protocol; PROTO_TITLE='H7-09 placeholder protocol'
OUT=$BH_WORK/H7-09; mkdir -p "$OUT"; FACTS=$OUT/facts.json; STATE=$OUT/state.json; rm -f "$FACTS" "$STATE"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB" "$OUT"; }
trap cleanup EXIT
api() { curl -s --noproxy '*' -H 'Content-Type: application/json' -H "X-OpenFerment-Project: $PROJECT" "$@"; }
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: one account of a deposition across a reload: Settings' Storage row (src/screens/Settings.tsx:1254-1256) and durable.ts's header (src/lib/durable.ts:6-8) say a deposition at hour 14 with timers running and deviations logged cannot be lost to a page reload, so a deposition's run with a running timer and a deviation note comes back after one reload with both; or else Settings and durable.ts say what Deposition.tsx:298 and ProtocolDetail.tsx:1264 say, that a run lives for the session."

# Static: the four sentences, and the store's snapshot of what survives a reload.
S_SET=$(grep -n 'hour 14 with timers running cannot be lost to a page reload' "$BH_ROOT/src/screens/Settings.tsx" | cut -d: -f1)
S_DUR=$(grep -n '14 with timers running and deviations logged cannot be lost to a page' "$BH_ROOT/src/lib/durable.ts" | cut -d: -f1)
S_DEP=$(grep -n "A run at the bench lives in this page's memory, so a reload ends it" "$BH_ROOT/src/screens/Deposition.tsx" | cut -d: -f1)
S_PRO=$(grep -n 'Deposition records step completions, deviations and timers for this session only' "$BH_ROOT/src/screens/ProtocolDetail.tsx" | cut -d: -f1)
echo "OBSERVED: src/screens/Settings.tsx:$(( ${S_SET:-3} - 2 ))-${S_SET:-0}: \"$(sed -n "$(( ${S_SET:-3} - 2 )),${S_SET:-0}p" "$BH_ROOT/src/screens/Settings.tsx" | tr -s ' ' | sed 's/^ //' | paste -sd' ')\""
echo "OBSERVED: src/lib/durable.ts:$(( ${S_DUR:-2} - 1 ))-$(( ${S_DUR:-0} + 1 )): \"$(sed -n "$(( ${S_DUR:-2} - 1 )),$(( ${S_DUR:-0} + 1 ))p" "$BH_ROOT/src/lib/durable.ts" | sed 's#^// ##' | paste -sd' ')\""
echo "OBSERVED: src/screens/Deposition.tsx:${S_DEP:-none} and src/screens/ProtocolDetail.tsx:${S_PRO:-none} say a run lives in page memory, for this session only"
SNAP_FROM=$(grep -n '^function snapshotOf' "$BH_ROOT/src/store.ts" | cut -d: -f1)
SNAP_RUNS=$(awk -v from="${SNAP_FROM:-0}" 'NR>=from && from>0 { print; if (NR>from && /^}/) exit }' "$BH_ROOT/src/store.ts" | grep -c '\bruns\b\|activeRunId')
SUB_FROM=$(grep -n 'useStore.subscribe((s, prev) => {' "$BH_ROOT/src/store.ts" | tail -1 | cut -d: -f1)
SUB_RUNS=$(sed -n "${SUB_FROM:-1},$(( ${SUB_FROM:-1} + 16 ))p" "$BH_ROOT/src/store.ts" | grep -c 's\.runs')
DUR_RUNS=$(grep -c '\bruns\b\|RunState\|deviations\|timers' "$BH_ROOT/src/lib/durable.ts")
echo "OBSERVED: src/store.ts:${SNAP_FROM:-none} snapshotOf names runs or activeRunId on $SNAP_RUNS lines; the save subscription at src/store.ts:${SUB_FROM:-none} watches s.runs on $SUB_RUNS lines; src/lib/durable.ts names runs, RunState, deviations or timers on $DUR_RUNS lines (the header's sentence among them)"
[ -n "$S_SET" ] && [ -n "$S_DUR" ] || finish "the tree carries neither contract sentence"

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$PROJECT" "H7-09 repro" >/dev/null
# One placeholder runbook, a project row put whole, then locked by the service (a deposition starts from a lock).
api -X PUT "$ORIGIN/api/state/runbooks/$RB" -d "{\"by\":\"H7 Repro\",\"value\":{\"id\":\"$RB\",\"kind\":\"research\",
  \"title\":\"H7-09 placeholder runbook\",\"status\":\"draft\",\"predictions\":[{\"id\":\"p1\",\"label\":\"A placeholder output\",
  \"value\":1.0,\"unit\":\"USD/kg\",\"confidence\":\"low\",\"basis\":\"a placeholder\"}],\"measurementSchema\":[{\"id\":\"m1\",
  \"label\":\"A placeholder output\",\"unit\":\"USD/kg\",\"timepoint\":\"harvest\",\"predictionId\":\"p1\"}]}}" >/dev/null
LOCKED=$(api -X POST "$ORIGIN/api/studies/runbooks/$RB/lock" -d '{"by":"H7 Repro"}' | python3 -c "import json,sys; print(bool(json.load(sys.stdin).get('lockedAt')))" 2>/dev/null)
[ "$LOCKED" = True ] || finish "the placeholder runbook was not locked"
# One placeholder protocol of three steps, the second timed; every word and number stands for nothing.
MADE=$(api -X POST "$ORIGIN/api/protocols" -d "{\"by\":\"H7 Repro\",\"protocol\":{\"id\":\"$PROTO_ID\",\"title\":\"$PROTO_TITLE\",
  \"category\":\"culture\",\"bsl\":1,\"currentVersion\":\"1\",\"versions\":[{\"version\":\"1\",\"baseBatch\":{\"value\":1,\"unit\":\"L\",
  \"label\":\"placeholder batch\"},\"estMinutes\":{\"active\":5,\"total\":10},\"materials\":[{\"name\":\"placeholder material\",
  \"amount\":1,\"unit\":\"g\",\"scaling\":\"per_batch_volume\",\"precision\":0.1}],\"steps\":[{\"id\":\"s1\",\"text\":\"A placeholder first step.\"},
  {\"id\":\"s2\",\"text\":\"A placeholder timed step.\",\"timerSec\":600,\"timerLabel\":\"placeholder wait\"},
  {\"id\":\"s3\",\"text\":\"A placeholder last step.\"}]}]}}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
[ "$MADE" = "$PROTO_ID" ] || finish "the placeholder protocol was not kept"
echo "SETUP: project $PROJECT, locked runbook $RB, protocol $PROTO_ID (step 2 timed, 600 s)"

(cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 600 \
  node reload.mjs "$ORIGIN" "$PROJECT" "$RB" "$PROTO_TITLE" "$FACTS")
[ -s "$FACTS" ] || finish "the browser steps wrote no facts"
# What the service keeps of the project after the reload: its depositions, and whether the note reached it.
api "$ORIGIN/api/state" > "$STATE"

python3 - "$FACTS" "$STATE" "$SNAP_RUNS" "$SUB_RUNS" <<'PY'
import json, sys
f = json.load(open(sys.argv[1])); state_text = open(sys.argv[2]).read()
snap_runs, sub_runs = int(sys.argv[3]), int(sys.argv[4])
if f.get("stopped"):
    print(f"OBSERVED: the browser steps stopped: {f['stopped']}")
    print("RESULT: NO-DEFECT"); sys.exit(0)
note, b, a = f["note"], f["before"], f["after"]
row = f["storageRow"] or ""
runs_key = '"runs"' in (b["snapshot"] or "")
snap_keys = sorted(json.loads(b["snapshot"]).keys()) if b["snapshot"] else None
claim = "hour 14 with timers running cannot be lost to a page reload" in row
print(f"OBSERVED: Settings > About, the Storage row on the built app: \"{row}\"")
print(f"OBSERVED: before the reload: address {b['address']}; the bench header \"{b['header']}\"; the deviation note on screen {b['noteShown']}; "
      f"the timer 'placeholder wait' on screen {b['timerShown']} with {b['pauseShown']} Pause button(s); "
      f"the IndexedDB snapshot holds the note {note in (b['snapshot'] or '')}, the timer {'placeholder wait' in (b['snapshot'] or '')}, "
      f"a key named runs {runs_key}; its keys {snap_keys}")
print(f"OBSERVED: leave-page prompts accepted: {f['dialogs']}")
print(f"OBSERVED: after one reload: address {a['address']}; \"This run is no longer active\" shown {a['noLongerActive']}; "
      f"the deviation note on screen {a['noteShown']}; the timer on screen {a['timerShown']} with {a['pauseShown']} Pause button(s); "
      f"the IndexedDB snapshot holds the note {note in (a['snapshot'] or '')}")
print(f"OBSERVED: after the reload the screen reads: \"{a['endsWords'] or a['screen'][:200]}\"")
try:
    st = json.loads(state_text); deps = st.get("depositions", [])
except Exception:
    deps = []
print(f"OBSERVED: the service keeps {len(deps)} deposition(s) for the project; the note in its state {note in state_text}; "
      f"the timer label in its state {'placeholder wait' in state_text}")
lost = (b["noteShown"] and b["timerShown"] and b["pauseShown"] > 0
        and note not in (b["snapshot"] or "") and note not in (a["snapshot"] or "") and note not in state_text
        and a["noLongerActive"] and not a["noteShown"] and not a["timerShown"] and a["pauseShown"] == 0)
defect = claim and lost and snap_runs == 0 and sub_runs == 0
print("RESULT: " + ("DEFECT" if defect else "NO-DEFECT"))
PY
exit 0
