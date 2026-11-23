#!/usr/bin/env bash
# H7-04: two tabs on one Proforma scenario's parameter panel, the service up; tab A types a value for one parameter,
# tab B then types a value for another, and tab B's write replaces the scope's whole list on the service, so tab A's
# override is gone with no word on either page.
#
#   bash bughunt/repro/H7-04/run.sh        (from the repository root)
#
# A fresh database (bh_r_h7_04_overrides, made by bh_db_fresh through bh_svc_start), the service on 127.0.0.1:9640 over
# the built app in dist/, one project with one BioSTEAM scenario on the shelf flowsheet ethanol_glucose_v0 put through
# PUT /api/state/scenarios/..., then the browser steps in twotabs.mjs. A proforma: scope binds only and starts no
# worker. Keyless; no model call. Ends with RESULT: DEFECT or RESULT: NO-DEFECT and exits 0; the service is stopped and
# the database and its data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h7_04_overrides; PORT=9640; ORIGIN=http://127.0.0.1:$PORT; PROJECT=h7-04; SC=sc-h7-04-twotabs
KEY_A=feed_glucose_conc; KEY_B=titre
OUT=$BH_WORK/H7-04; mkdir -p "$OUT"; FACTS=$OUT/facts.json; rm -f "$FACTS"
# The drop is tried again while a backend the server is still closing holds the database.
dropped() { [ -z "$(psql "$BH_SERVER/postgres" -AtXc "SELECT 1 FROM pg_database WHERE datname = '$DB'")" ]; }
cleanup() {
  bh_svc_stop $PORT
  local i; for i in 1 2 3 4 5 6 7 8 9 10; do bh_db_drop $DB 2>/dev/null; dropped && break; sleep 1; done
  dropped || echo "cleanup: $DB is still there" >&2
  rm -rf "$BH_WORK/data-$DB" "$OUT"
}
trap cleanup EXIT
api() { curl -s --noproxy '*' -H 'Content-Type: application/json' -H "X-OpenFerment-Project: $PROJECT" "$@"; }
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: after tab A types $KEY_A=1.234 and tab B, open on the same scenario, types $KEY_B=5.678, the service keeps both overrides of proforma:$SC (store.ts:2391, an override kept by scope and key, one a parameter), or a page says in words that the other tab's override was replaced."

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$PROJECT" "H7-04 repro" >/dev/null
api -X PUT "$ORIGIN/api/state/scenarios/$SC" -d "{\"by\":\"H7 Repro\",\"value\":{\"id\":\"$SC\",\"modelId\":\"ethanol_glucose_v0\",
  \"flowsheetId\":\"ethanol_glucose_v0\",\"kind\":\"biosteam\",\"name\":\"H7-04 two tabs\",\"description\":\"\",\"product\":\"\",
  \"pinned\":false,\"lastRunId\":null,\"createdAt\":\"2026-11-10T00:00:00Z\"}}" >/dev/null
KEYS=$(api "$ORIGIN/api/params/proforma:$SC" | python3 -c "import json,sys; print(' '.join(s['key'] for s in json.load(sys.stdin).get('specs', [])))" 2>/dev/null)
for k in $KEY_A $KEY_B; do
  printf '%s\n' $KEYS | grep -qx "$k" || finish "the scenario's panel does not name $k: $KEYS"
done

(cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 600 \
  node twotabs.mjs "$ORIGIN" "$PROJECT" "$SC" "$KEY_A" "$KEY_B" "$FACTS")
[ -s "$FACTS" ] || finish "the browser steps wrote no facts"

python3 - "$FACTS" <<'PY'
import json, sys
f = json.load(open(sys.argv[1]))
if f.get("stopped"):
    print(f"OBSERVED: the browser steps stopped: {f['stopped']}")
    print("RESULT: NO-DEFECT"); sys.exit(0)
a, b = f"{f['keyA']}={f['valueA']}", f"{f['keyB']}={f['valueB']}"
print(f"OBSERVED: the service held {f['afterA']} for {f['scope']} after tab A typed {a}, and {f['afterB']} after tab B "
      f"typed {b}; tab A sent {f['sent']['A']}, tab B sent {f['sent']['B']}.")
print(f"OBSERVED: tab B showed {f['keyA']} as \"{f['bShowsKeyA']}\" when it wrote; tab A after a reload shows {f['keyA']} as "
      f"\"{f['aShowsKeyAAfterReload']}\" (overridden: {f['aOverriddenAfterReload']}); toasts on tab A: "
      f"{f['words']['A'] or 'none'}; toasts on tab B: {f['words']['B'] or 'none'}.")
# The defect: tab A's override reached the service, tab B's write carried only its own and erased A's, and neither
# page said a word about it.
defect = (a in f["afterA"] and b in f["afterB"] and a not in f["afterB"]
          and any(b in s and a not in s for s in f["sent"]["B"] if isinstance(s, list))
          and f["aOverriddenAfterReload"] != "true" and not f["words"]["A"] and not f["words"]["B"])
print("RESULT: " + ("DEFECT" if defect else "NO-DEFECT"))
PY
exit 0
