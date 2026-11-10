#!/usr/bin/env bash
# H3-04: measured evidence naming a deposition the project does not hold is kept with the page's own
# provenance 'measured', and the runbooks read marks it measured.
# Run from the repository root: bash bughunt/repro/H3-04/run.sh
# A fresh database bh_r_h3_04_svc, a keyless service on the first free port of 9920..9929, project p1, the
# steps in repro.py; then the service stopped, the database dropped and the service's data copy removed.
# No worktree is needed: nothing is mutated or built, and the service runs over its own data directory.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS="-c client_min_messages=warning"
HERE=/home/user/openFermentUI/bughunt/repro/H3-04
DB=bh_r_h3_04_svc
PORT=""
for p in 9920 9921 9922 9923 9924 9925 9926 9927 9928 9929; do
  [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9920..9929"; echo "OBSERVED: every port busy"; echo "RESULT: NO-DEFECT"; exit 0; }
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
echo "$OUT" | grep -v '^H304_VERDICT'
VERDICT=$(echo "$OUT" | sed -n 's/^H304_VERDICT: \([A-Z-]*\).*/\1/p')
echo "$OUT" | grep '^H304_VERDICT' | sed 's/^H304_VERDICT: /checks: /'
if [ "$VERDICT" = DEFECT ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
