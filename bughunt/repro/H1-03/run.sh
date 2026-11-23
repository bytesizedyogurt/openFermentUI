#!/usr/bin/env bash
# H1-03: the documented `conform biosteam --thing ethanol_glucose_v0 --inputs <file>` stops with ProjectRequired.
# Run from the repository root: bash bughunt/repro/H1-03/run.sh
# A fresh database bh_r_h1_03_verdict holds the verdict the command keeps; the command makes and drops its own
# scratch database (openferment_conform_*) as it always does. Keyless: an empty key stands over core/.env, and
# every HTTP(S) proxy variable points at a closed port, so no call leaves the machine. Nothing in core/ is edited.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh

DB=bh_r_h1_03_verdict
W=$BH_WORK/H1-03/run-$$
THING=ethanol_glucose_v0
cleanup() { bh_db_drop "$DB" 2>/dev/null; rm -rf "$W"; }
trap cleanup EXIT
mkdir -p "$W"
cp -R "$BH_DATA_SRC" "$W/data"
if ! bh_db_fresh "$DB"; then
  echo "EXPECTED: a fresh database to keep the verdict in"
  echo "OBSERVED: bh_db_fresh $DB failed; nothing was checked"
  echo "RESULT: NO-DEFECT"
  exit 0
fi

# Every value ethanol_glucose_v0 waits for, each a person's assumption in its parameter's unit (docs/api/engines.md:666-668).
cat > "$W/inputs.json" <<'JSON'
[{"name":"feed_glucose_conc","quantity":{"value":100,"unit":"g L-1","origin":{"kind":"person-assumption","by":"H1-03 reproducer","at":"2026-11-10"}}},
 {"name":"titre","quantity":{"value":50,"unit":"g L-1","origin":{"kind":"person-assumption","by":"H1-03 reproducer","at":"2026-11-10"}}},
 {"name":"yield","quantity":{"value":0.4,"unit":"g g-1","origin":{"kind":"person-assumption","by":"H1-03 reproducer","at":"2026-11-10"}}},
 {"name":"productivity","quantity":{"value":1,"unit":"g L-1 h-1","origin":{"kind":"person-assumption","by":"H1-03 reproducer","at":"2026-11-10"}}},
 {"name":"plant_scale","quantity":{"value":1000,"unit":"t yr-1","origin":{"kind":"person-assumption","by":"H1-03 reproducer","at":"2026-11-10"}}},
 {"name":"glucose_price","quantity":{"value":0.5,"unit":"USD kg-1","origin":{"kind":"person-assumption","by":"H1-03 reproducer","at":"2026-11-10"}}}]
JSON

DEAD=http://127.0.0.1:9
# py [VAR=value ...] -- ARGS: the repository's Python in core/, keyless, offline, over $DB and the private data copy.
py() {
  local pre=(); while [ "$1" != "--" ]; do pre+=("$1"); shift; done; shift
  (cd "$BH_ROOT/core" && bh_env OPENFERMENT_API_KEY= HTTPS_PROXY=$DEAD HTTP_PROXY=$DEAD https_proxy=$DEAD \
     http_proxy=$DEAD ALL_PROXY=$DEAD all_proxy=$DEAD OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
     OPENFERMENT_DATA_DIR="$W/data" OPENFERMENT_SFF_LIBRARY="$W/data/sff-library" "${pre[@]}" \
     .venv/bin/python "$@" 2>&1 | grep -v '^INFO'; exit "${PIPESTATUS[0]}")
}
verdicts() { psql "$BH_SERVER/$DB" -XAtc "SELECT count(*) FROM openferment.engine_checks WHERE engine = 'biosteam'"; }
rows() { grep -cE '^(✓|✗)' <<<"$1"; }

echo "== A: the documented command, every value set: conform biosteam --thing $THING --inputs <file>"
A=$(py -- -m openferment_core.engine.conform biosteam --thing "$THING" --inputs "$W/inputs.json"; echo "exit $?")
echo "$A"
A_KEPT=$(verdicts)

echo "== B: the documented command, no values set: conform biosteam --thing $THING"
B=$(py -- -m openferment_core.engine.conform biosteam --thing "$THING"; echo "exit $?")
echo "$B"

echo "== C (control): B again with OPENFERMENT_PROJECT naming an id no database holds"
C=$(py OPENFERMENT_PROJECT=any-id -- -m openferment_core.engine.conform biosteam --thing "$THING"; echo "exit $?")
echo "$C"

echo "== the frames: the engine's unready, asked as conform's _inside asks it (no project entered yet)"
TRACE=$(py -- -c '
import traceback
from pathlib import Path
from openferment_core.engine import conform
from openferment_core.engine.biosteam import ENGINE
conform.as_served()
try:
    print("unready answered:", ENGINE.unready("ethanol_glucose_v0", []))
except Exception as e:
    frames = [f"{Path(f.filename).parent.name}/{Path(f.filename).name}:{f.lineno} {f.name}"
              for f in traceback.extract_tb(e.__traceback__)]
    print(type(e).__name__, "via", " > ".join(frames))
')
echo "$TRACE"

echo
echo "EXPECTED: A makes the eight checks on $THING with the file's six values: eight rows (each ✓ or ✗) and the verdict kept, one engine_checks row for biosteam in $DB"
echo "OBSERVED: A printed $(rows "$A") row(s), $(grep -o 'exit [0-9]*' <<<"$A"), $A_KEPT verdict row(s) kept: $(grep -m1 '^✗' <<<"$A" | cut -c1-340)"
echo "EXPECTED: B refuses in words naming the values $THING waits for (docs/api/engines.md:671-672), keeping no verdict"
echo "OBSERVED: B: $(grep -m1 '^✗' <<<"$B" | cut -c1-340)"
echo "CONTROL:  C, the same command with any project id set: $(grep -m1 '^✗' <<<"$C" | cut -c1-340)"

if grep -q 'ProjectRequired' <<<"$A" && [ "$(rows "$A")" -lt 8 ] && [ "$A_KEPT" = 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
