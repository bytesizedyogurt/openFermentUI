#!/usr/bin/env bash
# H3-05: a later write that moves a correction's sample time (or the corrected reading's) makes the mis-read
# it corrected stand again, and every door takes it as a measurement.
# Run from the repository root: bash bughunt/repro/H3-05/run.sh
# A fresh database bh_r_h3_05_svc, a keyless service on the first free port of 10280..10289, project p1, the
# steps in repro.py; then the service stopped, the database dropped and the service's data copy removed.
# No worktree is needed: nothing is mutated or built, and the service runs over its own data directory.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS="-c client_min_messages=warning"
HERE=/home/user/openFermentUI/bughunt/repro/H3-05
DB=bh_r_h3_05_svc
PORT=""
for p in 10280 10281 10282 10283 10284 10285 10286 10287 10288 10289; do
  [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 10280..10289"; echo "OBSERVED: every port busy"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"
}
trap cleanup EXIT
ORIGIN=$(bh_svc_start "$DB" "$PORT") || { echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless), tree at $(git -C "$BH_ROOT" rev-parse --short HEAD), core/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core && echo yes || echo no)"
bh_project "$ORIGIN" p1 "P one" >/dev/null
OUT=$(cd /tmp && bh_env "$BH_ROOT/core/.venv/bin/python" -I "$HERE/repro.py" "$ORIGIN" 2>&1)
echo "$OUT" | grep -v '^H305_VERDICT'
VERDICT=$(echo "$OUT" | sed -n 's/^H305_VERDICT: \([A-Z-]*\).*/\1/p')
echo "$OUT" | grep '^H305_VERDICT' | sed 's/^H305_VERDICT: /checks: /'
echo "EXPECTED: once s2 corrects s1, dep9/s1 stays corrected whatever later writes do to the sample times while dep9 is open: the move of s2 to 6 h (step 5) is refused in words, or the resolve on dep9/s1 (step 6) is still a 422 and the readings list still leaves dep9/s1 out"
if [ "$VERDICT" = DEFECT ]; then
  echo "OBSERVED: the move is a 200; the resolve on dep9/s1 is a 200 that sets the titre to the mis-read 4.0 g/L with origin measurement, and the readings list offers dep9/s1 4.0 g/L at 5 h beside dep9/s2 40.0 g/L at 6 h"
  echo "RESULT: DEFECT"
else
  echo "OBSERVED: the correction held (or the steps did not run as written; see the lines above)"
  echo "RESULT: NO-DEFECT"
fi
exit 0
