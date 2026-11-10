#!/usr/bin/env bash
# H14-08: Home's pureOS destination reads "45 unit operations · no process model" while pureOS's own page says it
# builds a train unit by unit from BioSTEAM's units and runs it, and the service registers pureOS's `train` engine.
# A fresh database, the service keyless on 127.0.0.1 (a port in 10380-10389), one project, GET /api/engines, then
# Home and /p/<project>/pureos of the built app read in headless Chromium, then the source lines at 2047f5a.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE="$BH_ROOT/bughunt/repro/H14-08"
DB=bh_r_h14_08_home; P=h14-08
PORT=""
for p in 10380 10381 10382 10383 10384 10385 10386 10387 10388 10389; do
  [ -z "$(bh_port_pid $p)" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "no free port in 10380-10389"; echo "RESULT: NO-DEFECT (no port to serve on)"; exit 0; }
DATA="$BH_WORK/data-$DB"
SHOT="$BH_WORK/H14-08"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$DATA" "$SHOT"-*.png; }
trap cleanup EXIT
rm -rf "$DATA"

O=$(bh_svc_start "$DB" "$PORT" 2>/dev/null) || { echo "RESULT: NO-DEFECT (the service did not start)"; exit 0; }
echo "service $O over fresh database $DB, no key"
bh_project "$O" "$P" >/dev/null
echo "step 1: project $P made"

ENG=$(curl -s --noproxy '*' "$O/api/engines" -H "X-OpenFerment-Project: $P")
TRAIN=$(echo "$ENG" | python3 -c '
import json,sys
d=json.load(sys.stdin)
t=[e for e in d if e.get("name")=="train" and not e.get("error")]
print("registered" if t else "absent")
print("step 2: GET /api/engines names", ", ".join(e.get("name","?")+("" if not e.get("error") else " (set aside)") for e in d), file=sys.stderr)
for e in t:
    print("  train:", json.dumps({k:e.get(k) for k in ("name","version","worker","entryPoint","description") if k in e})[:400], file=sys.stderr)
' 2>&1)
echo "$TRAIN" | grep -v '^registered$\|^absent$'
TRAIN_OK=$(echo "$TRAIN" | grep -c '^registered$')
TRAIN_WORD=absent; [ "$TRAIN_OK" = 1 ] && TRAIN_WORD=registered

SCR=$(cd "$HERE" && node screen.mjs "$O" "$P" "$SHOT" 2>&1 | tail -1)
read -r HOMELINE SUB PRODUCED <<<"$(echo "$SCR" | python3 -c '
import json,sys
try: d=json.loads(sys.stdin.read())
except Exception: d={}
h=d.get("homePureos") or []; p=d.get("produced") or []
q=lambda s: (s or "-").replace(" ", "_")
print(q(" | ".join(h)), q(d.get("subtitle")), q(" ".join(p)))')"
echo "step 3: Home of the built app in Chromium, the pureOS destination: \"${HOMELINE//_/ }\""
echo "step 4: /p/$P/pureos subtitle: \"${SUB//_/ }\""
echo "step 5: /p/$P/pureos footer: \"${PRODUCED//_/ }\""

echo "step 6: the source at 2047f5a:"
git -C "$BH_ROOT" show 2047f5a:src/screens/Home.tsx | grep -n "What each destination actually has" | sed 's/^/  src\/screens\/Home.tsx:/'
git -C "$BH_ROOT" show 2047f5a:src/screens/Home.tsx | grep -n "pureOS: { now:" | sed 's/^ *//; s/^/  src\/screens\/Home.tsx:/'
git -C "$BH_ROOT" show 2047f5a:src/screens/PureOS.tsx | grep -no "pureOS builds a train unit by unit from a catalogue of BioSTEAM's units and runs it" | sed 's/^/  src\/screens\/PureOS.tsx:/'
git -C "$BH_ROOT" show 2047f5a:core/pyproject.toml | grep -n '^train = ' | sed 's/^/  core\/pyproject.toml:/'

echo "EXPECTED: Home's pureOS line says what pureOS holds now (Home.tsx:235 \"What each destination actually has, right now\"): trains built in the Builder and run on BioSTEAM through the registered train engine, as pureOS's own page says"
echo "OBSERVED: train engine ${TRAIN_WORD} on the service; Home reads \"${HOMELINE//_/ }\" while pureOS's page reads \"pureOS builds a train unit by unit from a catalogue of BioSTEAM's units and runs it\" and \"${PRODUCED//_/ }\""
if [ "$TRAIN_OK" = 1 ] && echo "$HOMELINE" | grep -q "no_process_model" && echo "$SUB" | grep -q "builds_a_train_unit_by_unit"; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
