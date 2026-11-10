#!/usr/bin/env bash
# H7-06: with the service stopped, the runbook, deposition, paper, Guild skill and Postdoc conversation pages say the
# project keeps no such row, while the strain, lesson and protocol pages say the service is not running.
#
#   bash bughunt/repro/H7-06/run.sh        (from the repository root)
#
# A fresh database (bh_r_h7_06_words, made by bh_db_fresh through bh_svc_start), the service on 127.0.0.1:10020 over
# the built app in dist/, one project, and placeholder rows kept through the service's own routes (seed.py): a runbook,
# a deposition, a Postdoc conversation, a skill, a pasted paper, and for the controls a strain, a lesson and a
# protocol. words.mjs opens each row's page in Chromium with the service up, then the service is stopped (nothing
# listens on 10020) and words.mjs opens the same addresses again, the page's own files served from dist/ by the
# browser and every /api request failing at the closed port. Keyless; no model call. Ends with RESULT: DEFECT or
# RESULT: NO-DEFECT and exits 0; the service is stopped and the database and its data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h7_06_words; PORT=10020; ORIGIN=http://127.0.0.1:$PORT; PROJECT=h7-06
OUT=$BH_WORK/H7-06; rm -rf "$OUT"; mkdir -p "$OUT"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB" "$OUT"; }
trap cleanup EXIT
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }
NODE() { (cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 300 node "$@"); }

echo "EXPECTED: with the service stopped, each detail page of a row the project keeps says the service is not running" \
     "and names the command that starts it, as the strain, lesson and protocol pages do (src/lib/http.ts:3-4," \
     "ServiceDown: nothing answered, the remedy names the command that starts the service); no page says the project" \
     "holds no such row."

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$PROJECT" "H7-06 repro" >/dev/null
IDS=$(python3 "$HERE/seed.py" "$ORIGIN" "$PROJECT") || finish "the placeholder rows were not kept: $IDS"
echo "SETUP: project $PROJECT keeps $IDS"
python3 - "$IDS" > "$OUT/paths.json" <<'PY'
import json, sys
i = json.loads(sys.argv[1])
print(json.dumps({
    "runbook": f"/runbooks/{i['runbook']}", "deposition": f"/runbooks/depositions/{i['deposition']}",
    "paper": f"/biorepo/paper/{i['paper']}", "skill": f"/guild/skills/{i['skill']}",
    "conversation": f"/postdoc/{i['conversation']}",
    "strain": f"/geneos/hosts/{i['strain']}", "lesson": f"/primer/{i['lesson']}",
    "protocol": f"/runbooks/protocols/{i['protocol']}"}))
PY

NODE words.mjs up "$ORIGIN" "$PROJECT" "$OUT/paths.json" "$OUT/up.json" "$BH_ROOT/dist"
[ -s "$OUT/up.json" ] || finish "the browser wrote no facts with the service up"

bh_svc_stop $PORT
if curl -s --noproxy '*' -m 3 "$ORIGIN/api/health" >/dev/null 2>&1; then finish "the service still answers on $PORT"; fi
echo "SETUP: the service is stopped; GET $ORIGIN/api/health finds nothing listening"

NODE words.mjs stopped "$ORIGIN" "$PROJECT" "$OUT/paths.json" "$OUT/stopped.json" "$BH_ROOT/dist"
[ -s "$OUT/stopped.json" ] || finish "the browser wrote no facts with the service stopped"

python3 - "$OUT/up.json" "$OUT/stopped.json" <<'PY'
import json, sys
up, down = (json.load(open(p)) for p in sys.argv[1:3])
# Each page: the words that show the row with the service up, and, for a page under test, the words that say the
# project holds no such row.
UNDER_TEST = {
    "runbook": ("H7-06 placeholder runbook", "The project keeps no runbook of that id"),
    "deposition": ("dep-h706 started", "This project holds no deposition with this id"),
    "paper": ("A placeholder paragraph that stands for nothing", "is not a document this project holds"),
    "skill": ("H7-06 placeholder skill", "The project's skill catalogue holds no skill h706-skill"),
    "conversation": ("H7-06 placeholder conversation", "No conversation yet: a person asks the first question"),
}
CONTROLS = {
    "strain": "H7-06 placeholder strain",
    "lesson": "H7-06 placeholder lesson",
    "protocol": "H7-06 placeholder protocol",
}
SERVICE = ("The service is not running", "needs the service", "Start it with")
print(f"OBSERVED: with the service stopped the pages made {down['apiRequests']} /api requests, "
      f"{down['apiFailed']} of them failed at the connection and {down['apiAnswered']} answered")

def shown(name, state):
    return (up if state == "up" else down)["pages"][name]

def snippet(text, at, width=150):
    i = text.find(at)
    return text[:width] if i < 0 else text[max(0, i - 40):i + width]

held_up, said_none, named = {}, {}, {}
for name, (row, none) in UNDER_TEST.items():
    u, d = shown(name, "up"), shown(name, "stopped")
    held_up[name] = row in u["main"]
    said_none[name] = none in d["main"] and row not in d["main"]
    named[name] = [w for w in SERVICE if w in d["body"]]
    print(f"OBSERVED: under test {name} {u['path']}: service up, the row shows: {held_up[name]}; service stopped: "
          f"\"{snippet(d['main'], none)}\"; says the project holds no such row: {said_none[name]}; names the service: "
          f"{named[name] or 'nothing'}")
controls_held = {}
for name, row in CONTROLS.items():
    u, d = shown(name, "up"), shown(name, "stopped")
    words = [w for w in SERVICE if w in d["main"]]
    controls_held[name] = row in u["main"] and "The service is not running" in d["main"]
    print(f"OBSERVED: control {name} {u['path']}: service up, the row shows: {row in u['main']}; service stopped: "
          f"\"{snippet(d['main'], 'The service is not running')}\"; names the service: {words or 'nothing'}")
silent = [n for n in UNDER_TEST if not named[n]]
print(f"OBSERVED: {sum(said_none.values())} of {len(UNDER_TEST)} pages under test say the project holds no such row "
      f"with the service stopped, {len(silent)} of them ({', '.join(silent) or 'none'}) say nothing of the service; "
      f"{sum(controls_held.values())} of {len(CONTROLS)} controls say the service is not running")
defect = all(held_up.values()) and all(said_none.values()) and all(controls_held.values())
print("RESULT: " + ("DEFECT" if defect else "NO-DEFECT"))
PY
exit 0
