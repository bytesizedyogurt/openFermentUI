#!/usr/bin/env bash
# H7-03: one running deposition open at its bench in two tabs, the service up. Tab B's view was read before tab A's
# reading, so the service refuses tab B's reading as leaving A's out (the recorded debt, PROGRESS.md Known debts).
# What this shows is the part past that debt: tab B's bench and record page go on listing the refused reading as
# recorded and standing, with nothing left in the queue to send it, until a reload removes it.
#
#   bash bughunt/repro/H7-03/run.sh        (from the repository root)
#
# A fresh database (bh_r_h7_03_sameonline, made by bh_db_fresh through bh_svc_start), the service on 127.0.0.1:9340
# over the built app in dist/, one project with one placeholder locked runbook put through the API, then the browser
# steps in sameonline.mjs. Keyless; no model call. Ends with RESULT: DEFECT or RESULT: NO-DEFECT and exits 0; the
# service is stopped and the database and its data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h7_03_sameonline; PORT=9340; ORIGIN=http://127.0.0.1:$PORT; PROJECT=h7-03; RB=rb-h7-03-placeholder
OUT=$BH_WORK/H7-03; mkdir -p "$OUT"; FACTS=$OUT/facts.json; rm -f "$FACTS"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB" "$OUT"; }
trap cleanup EXIT
api() { curl -s --noproxy '*' -H 'Content-Type: application/json' -H "X-OpenFerment-Project: $PROJECT" "$@"; }
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: once the service refuses tab B's write of its 8.8 USD/kg reading (422, said in words: the recorded debt), tab B's bench and the deposition's record page in that tab list what the service keeps (tab A's 7.7 USD/kg) and take the refused reading back, so no reading shows as recorded or standing that the service does not hold (Deposition.tsx:1086-1087 \"The deposition is the record, kept on the service as it changes\"; projectState.ts:159-160 a refused row \"is dropped with its reason\")."

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$PROJECT" "H7-03 repro" >/dev/null
# One placeholder runbook, a project row put whole, then locked by the service (the bench waits for a lock).
api -X PUT "$ORIGIN/api/state/runbooks/$RB" -d "{\"by\":\"H7 Repro\",\"value\":{\"id\":\"$RB\",\"kind\":\"research\",
  \"title\":\"H7-03 placeholder runbook\",\"status\":\"draft\",\"predictions\":[{\"id\":\"p1\",\"label\":\"A placeholder output\",
  \"value\":1.0,\"unit\":\"USD/kg\",\"confidence\":\"low\",\"basis\":\"a placeholder\"}],\"measurementSchema\":[{\"id\":\"m1\",
  \"label\":\"A placeholder output\",\"unit\":\"USD/kg\",\"timepoint\":\"harvest\",\"predictionId\":\"p1\"}]}}" >/dev/null
LOCKED=$(api -X POST "$ORIGIN/api/studies/runbooks/$RB/lock" -d '{"by":"H7 Repro"}' | python3 -c "import json,sys; print(bool(json.load(sys.stdin).get('lockedAt')))" 2>/dev/null)
[ "$LOCKED" = True ] || finish "the placeholder runbook was not locked"

(cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 600 \
  node sameonline.mjs "$ORIGIN" "$PROJECT" "$RB" "$FACTS") | grep -v '^FACTS '
[ -s "$FACTS" ] || finish "the browser steps wrote no facts"

python3 - "$FACTS" <<'PY'
import json, sys
f = json.load(open(sys.argv[1]))
if f.get("stopped"):
    print(f"OBSERVED: the browser steps stopped: {f['stopped']}")
    print("RESULT: NO-DEFECT"); sys.exit(0)
A, B = "7.7 USD/kg", "8.8 USD/kg"
held = (f.get("heldLater") or {}).get("entries", [])
puts = f.get("putsB", [])
refused = [p for p in puts if p.startswith("422 ")]
bench = f.get("benchB") or {}
measures = " | ".join(bench.get("measures", []))
record = f.get("recordB") or []
standing_b = [r for r in record if B.split()[0] in r["text"] and r["stands"] == "true"]
reloaded = " | ".join((f.get("benchBReloaded") or {}).get("measures", []))
outbox = f.get("outboxB")
print(f"OBSERVED: the recorded debt, as its words say: tab B's {len(puts)} PUT(s) to the deposition answered "
      f"{[p.split(' ', 1)[0] for p in puts]}; the first in words: {refused[0][4:220] if refused else 'none'}; "
      f"tab B's toasts: {f.get('toastsB') or 'none'}.")
print(f"OBSERVED: 20 s later the service holds {held}; the browser queue holds {outbox} (nothing owed, so nothing "
      f"will send {B}).")
print(f"OBSERVED: tab B's bench, 20 s on with no reload: header \"{bench.get('header', '')}\"; measure \"{measures}\"; "
      f"panel \"{bench.get('recordedHere', '')}\".")
print(f"OBSERVED: tab B's toasts 20 s on: {f.get('toastsLater') or 'none'}.")
print(f"OBSERVED: tab B's close dialog: \"{f.get('closeDialogB', '')}\"")
print(f"OBSERVED: tab B's record page, no reload: {record}")
print(f"OBSERVED: tab B's bench after a reload: measure \"{reloaded}\".")
defect = (
    A in held and B not in held           # the service kept A's reading and refused B's
    and bool(refused) and outbox == []    # B's writes were refused and left the queue
    and B in measures and "to read back" not in measures  # B's bench lists 8.8 as read back and standing
    and bool(standing_b)                  # B's record page lists 8.8 as standing for its measure
    and B not in reloaded and A in reloaded  # a reload shows what the service keeps
)
print("RESULT: " + ("DEFECT" if defect else "NO-DEFECT"))
PY
exit 0
