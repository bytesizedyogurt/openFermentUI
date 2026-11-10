#!/usr/bin/env bash
# H7-05: an address naming a project the service does not hold (/#/p/<unknown>/...) reloads the page without end.
#
#   bash bughunt/repro/H7-05/run.sh        (from the repository root)
#
# A fresh database (bh_r_h7_05_unknown, made by bh_db_fresh through bh_svc_start), the service on 127.0.0.1:9940 over
# the built app in dist/, one project made through the API, then unknown.mjs in Chromium: a fresh browser opens the
# held project's address (the control) and another fresh browser opens an address naming a project the service does
# not hold; each counts page loads and GET /api/projects over 10 s. Keyless; no model call. Ends with RESULT: DEFECT or
# RESULT: NO-DEFECT and exits 0; the service is stopped and the database and its data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h7_05_unknown; PORT=9940; ORIGIN=http://127.0.0.1:$PORT; HELD=h7-05; UNKNOWN=nosuchproject; SECONDS_WINDOW=10
OUT=$BH_WORK/H7-05; mkdir -p "$OUT"; FACTS=$OUT/facts.json; rm -f "$FACTS"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB" "$OUT"; }
trap cleanup EXIT
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: opening /#/p/$UNKNOWN/runbooks, a project the service does not hold, reloads the page once at most and then settles on one screen, as opening the held project's address does (ADR-009 7.1: an address naming another project opens it, the page reloading in it as a project switch does)."

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$HELD" "H7-05 repro" >/dev/null
LISTED=$(curl -s --noproxy '*' "$ORIGIN/api/projects" | python3 -c "import json,sys; print(','.join(p['id'] for p in json.load(sys.stdin)))")
echo "SETUP: the service holds the projects [$LISTED]"
[ "$LISTED" = "$HELD" ] || finish "the service holds [$LISTED], expected [$HELD] alone"

(cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 300 \
  node unknown.mjs "$ORIGIN" "$HELD" "$UNKNOWN" "$SECONDS_WINDOW" "$FACTS")
[ -s "$FACTS" ] || finish "the browser steps wrote no facts"

python3 - "$FACTS" <<'PY'
import json, sys
f = json.load(open(sys.argv[1]))
s = f["seconds"]
for k in ("held", "unknown"):
    v = f[k]; w = v["inWindow"]
    print(f"OBSERVED: {k} project '{v['projectId']}': {w['loads']} page loads and {w['projects']} GET /api/projects in "
          f"{w['ms']/1000:.1f} s from the first navigation; {v['after']['loads']} more loads in the 2 s after; address "
          f"{v['address']}; localStorage openferment.project {v['stored']!r}; 'Opening project' shown: {v['opening']}; "
          f"main: \"{v['main'][:100]}\"")
h, u = f["held"], f["unknown"]
# The control settles: its first load and the one reload a project switch makes. The unknown address keeps reloading.
defect = (h["inWindow"]["loads"] <= 2 and h["after"]["loads"] == 0
          and u["inWindow"]["loads"] >= 10 and u["after"]["loads"] >= 1)
print("RESULT: " + ("DEFECT" if defect else "NO-DEFECT"))
PY
exit 0
