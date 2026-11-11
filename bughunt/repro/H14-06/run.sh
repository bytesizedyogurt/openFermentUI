#!/usr/bin/env bash
# H14-06: Home's Postdoc destination says "live through openferment-core, on the model it is configured with" while
# GET /api/health answers hasKey false and Postdoc's own screen says "Postdoc is running without an API key".
# A fresh database, the service keyless on 127.0.0.1 (the first free port in 10081-10089: Chromium refuses 10080 as
# an unsafe port), one project made through the API, /api/health read, then Home and Postdoc of the built app (dist/)
# read in headless Chromium. No model call.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE="$BH_ROOT/bughunt/repro/H14-06"
DB=bh_r_h14_06_home; P=h14-06
PORT=""
for p in 10081 10082 10083 10084 10085 10086 10087 10088 10089; do
  [ -z "$(bh_port_pid $p)" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "no free port in 10081-10089"; echo "RESULT: NO-DEFECT (no port to serve on)"; exit 0; }
DATA="$BH_WORK/data-$DB"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$DATA"; }
trap cleanup EXIT
rm -rf "$DATA"

O=$(bh_svc_start "$DB" "$PORT" 2>/dev/null) || { echo "RESULT: NO-DEFECT (the service did not start)"; exit 0; }
echo "service $O over fresh database $DB, no key"
bh_project "$O" "$P" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("step 1: project made:", d.get("id"))'

HEALTH=$(curl -s --noproxy '*' "$O/api/health")
echo "step 2: GET /api/health -> $HEALTH"
HASKEY=$(echo "$HEALTH" | python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("hasKey")).lower())')

NERR="$BH_WORK/h14-06-node.err"
SCR=""
for attempt in 1 2; do
  SCR=$(cd "$HERE" && node screen.mjs "$O" "$P" 2>"$NERR" | tail -1)
  case "$SCR" in "{"*) break;; esac
  echo "  (Chromium read, attempt $attempt, gave no answer: $(tail -3 "$NERR" | tr '\n' ' ' | cut -c1-200))"
done
rm -f "$NERR"
echo "step 3: Home and Postdoc of the built app in Chromium (project $P): $SCR"
read -r CARD NOKEY ANSWERS <<<"$(echo "$SCR" | python3 -c '
import json,sys
try: d=json.loads(sys.stdin.read())
except Exception: d={}
q=lambda s: (s or "-").replace(" ", "_")
c=d.get("homePostdocCard") or []
print(q(" | ".join(c)), q(d.get("postdocNoKey")), q(d.get("postdocAnswersOn")))')"
CARD=${CARD//_/ }; NOKEY=${NOKEY//_/ }; ANSWERS=${ANSWERS//_/ }

echo "step 4: the source at 2047f5a"
git -C "$BH_ROOT" show 2047f5a:src/screens/Home.tsx | grep -n "live through openferment-core" | sed 's/^/  src\/screens\/Home.tsx:/'
git -C "$BH_ROOT" show 2047f5a:src/screens/Home.tsx | grep -c "hasKey\|health" | sed 's/^/  src\/screens\/Home.tsx lines naming health or hasKey: /'
git -C "$BH_ROOT" show 2047f5a:src/screens/Postdoc.tsx | grep -n "!health.hasKey\|running without an API key" | sed 's/^/  src\/screens\/Postdoc.tsx:/'

echo "EXPECTED: with /api/health hasKey false, Home's Postdoc destination line says Postdoc waits for a key, as Postdoc's own screen does (Home.tsx:235 \"What each destination actually has, right now\"; Home.tsx:781 \"an honest current state per entry\"; Postdoc.tsx:146 \"Postdoc is running without an API key\")"
echo "OBSERVED: hasKey $HASKEY; Home's Postdoc card \"$CARD\"; Postdoc's callout \"$NOKEY\"; Postdoc's answers-on line \"$ANSWERS\""
if [ "$HASKEY" = false ] && echo "$CARD" | grep -q "live through openferment-core" && [ "$NOKEY" = "Postdoc is running without an API key" ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
