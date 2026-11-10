#!/usr/bin/env bash
# H7-07: the Deposition takeover at 810x1080. The run's Next step button is 43 px wide, and a staged protocol run's
# link to its runbook is 18 px tall and shows its underline on hover alone.
#
#   bash bughunt/repro/H7-07/run.sh        (from the repository root)
#
# A fresh database (bh_r_h7_07_bench, made by bh_db_fresh through bh_svc_start), a keyless service on 127.0.0.1:10327
# over the built app in dist/, one project with one placeholder locked runbook and one placeholder three-step protocol
# put through the API, then measure.mjs in Chromium at 810x1080 with touch. No model call. Ends with RESULT: DEFECT or
# RESULT: NO-DEFECT and exits 0; the service is stopped and the database and its data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h7_07_bench; PORT=10327; ORIGIN=http://127.0.0.1:$PORT; PROJECT=h7-07; RB=rb-h7-07-placeholder
PROTO_ID=h7-07-protocol; PROTO_TITLE='H7-07 placeholder protocol'
OUT=$BH_WORK/H7-07; mkdir -p "$OUT"; FACTS=$OUT/facts.json; rm -f "$FACTS"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB" "$OUT"; }
trap cleanup EXIT
api() { curl -s --noproxy '*' -H 'Content-Type: application/json' -H "X-OpenFerment-Project: $PROJECT" "$@"; }
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: at 810x1080 every target in the Deposition takeover measures at least 44 x 44 px, the Next step button and the staged run's runbook link among them, and no affordance appears on hover alone (CLAUDE.md:59; src/screens/Deposition.tsx:9-12)."

# The source as it stands: the Next step button sets a height and no width around a 17 px icon, and the runbook link is
# an inline anchor whose underline is a hover utility.
echo "SOURCE: $(grep -n 'aria-label="Next step"' "$BH_ROOT/src/screens/Deposition.tsx" | head -1 | tr -s ' ')"
echo "SOURCE: $(grep -n 'className="text-accent hover:underline" href={href(`/runbooks/${runbook.id}`)}' "$BH_ROOT/src/screens/Deposition.tsx" | head -1 | tr -s ' ')"
echo "SOURCE: $(grep -n -A9 '^\.btn {' "$BH_ROOT/src/styles.css" | grep -E 'padding|border:' | tr -s ' ' | paste -sd ';')"

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$PROJECT" "H7-07 repro" >/dev/null
# One placeholder runbook, a project row put whole, then locked by the service (a deposition starts from a lock).
api -X PUT "$ORIGIN/api/state/runbooks/$RB" -d "{\"by\":\"H7 Repro\",\"value\":{\"id\":\"$RB\",\"kind\":\"research\",
  \"title\":\"H7-07 placeholder runbook\",\"status\":\"draft\",\"predictions\":[{\"id\":\"p1\",\"label\":\"A placeholder output\",
  \"value\":1.0,\"unit\":\"USD/kg\",\"confidence\":\"low\",\"basis\":\"a placeholder\"}],\"measurementSchema\":[{\"id\":\"m1\",
  \"label\":\"A placeholder output\",\"unit\":\"USD/kg\",\"timepoint\":\"harvest\",\"predictionId\":\"p1\"}]}}" >/dev/null
LOCKED=$(api -X POST "$ORIGIN/api/studies/runbooks/$RB/lock" -d '{"by":"H7 Repro"}' | python3 -c "import json,sys; print(bool(json.load(sys.stdin).get('lockedAt')))" 2>/dev/null)
[ "$LOCKED" = True ] || finish "the placeholder runbook was not locked"
# One placeholder protocol of three steps, the second timed; every word and number stands for nothing.
MADE=$(api -X POST "$ORIGIN/api/protocols" -d "{\"by\":\"H7 Repro\",\"protocol\":{\"id\":\"$PROTO_ID\",\"title\":\"$PROTO_TITLE\",
  \"category\":\"culture\",\"bsl\":1,\"currentVersion\":\"1\",\"versions\":[{\"version\":\"1\",\"baseBatch\":{\"value\":1,\"unit\":\"L\",
  \"label\":\"placeholder batch\"},\"estMinutes\":{\"active\":5,\"total\":10},\"materials\":[{\"name\":\"placeholder material\",
  \"amount\":1,\"unit\":\"g\",\"scaling\":\"per_batch_volume\",\"precision\":0.1}],\"steps\":[{\"id\":\"s1\",\"text\":\"A placeholder first step.\"},
  {\"id\":\"s2\",\"text\":\"A placeholder timed step.\",\"timerSec\":30,\"timerLabel\":\"placeholder wait\"},
  {\"id\":\"s3\",\"text\":\"A placeholder last step.\"}]}]}}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
[ "$MADE" = "$PROTO_ID" ] || finish "the placeholder protocol was not kept"

(cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 600 \
  node measure.mjs "$ORIGIN" "$PROJECT" "$RB" "$PROTO_TITLE" "$FACTS")
[ -s "$FACTS" ] || finish "the browser steps wrote no facts"

python3 - "$FACTS" <<'PY'
import json, sys
f = json.load(open(sys.argv[1]))
if f.get("stopped"):
    print(f"OBSERVED: the browser steps stopped: {f['stopped']}")
    print("RESULT: NO-DEFECT"); sys.exit(0)
st, link = f["staged"], f["staged"]["link"]
lb = link["box"]
print(f"OBSERVED: staged view {st['address']}: the runbook link \"{link['text']}\" (class \"{link['className']}\", display "
      f"{link['display']}) measures {lb['w']} x {lb['h']} px; Begin recording measures {st['begin']['w']} x {st['begin']['h']} px.")
print(f"OBSERVED: the link's underline at rest: {link['decoration']}; under a hover: {link['decorationOnHover']}; "
      f"the :hover rules that match it: {link['hoverRules']}.")
print("OBSERVED: the run's footer: " + "; ".join(f"{b['label']} {b['w']} x {b['h']} px" for b in f["footer"]) + ".")
for s in f["steps"]:
    print(f"OBSERVED: step {s['step']}: Next step measures {s['nextStep']['w']} x {s['nextStep']['h']} px "
          f"(min-width {s['minWidth']}, {'enabled' if s['enabled'] else 'disabled'}).")
next_small = bool(f["steps"]) and all(s["nextStep"]["w"] < 44 or s["nextStep"]["h"] < 44 for s in f["steps"])
link_small = lb["w"] < 44 or lb["h"] < 44
hover_only = link["decoration"] == "none" and link["decorationOnHover"] == "underline"
print(f"OBSERVED: Next step under 44 px on every step: {next_small}; the runbook link under 44 px: {link_small}; "
      f"its underline on hover alone: {hover_only}.")
print("RESULT: " + ("DEFECT" if next_small and link_small else "NO-DEFECT"))
PY
exit 0
