#!/usr/bin/env bash
# H3-15: a deposition write that appends a second entry under an id an earlier entry holds is kept, and
# the ref <deposition>/<id> reaches the first entry alone.
# Run from the repository root: bash bughunt/repro/H3-15/run.sh
# A fresh database bh_r_h3_15_svc, a keyless service on the first free port of 10390..10399, project p1,
# the steps in repro.py; then the service stopped, the database dropped and the service's data copy removed.
# No worktree is needed: nothing is mutated or built, and the service runs over its own data directory.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS="-c client_min_messages=warning"
HERE=/home/user/openFermentUI/bughunt/repro/H3-15
DB=bh_r_h3_15_svc
PORT=""
for p in 10390 10391 10392 10393 10394 10395 10396 10397 10398 10399; do
  [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 10390..10399"; echo "OBSERVED: every port busy"; echo "RESULT: NO-DEFECT"; exit 0; }
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
echo "$OUT" | grep -v '^H315_VERDICT'
VERDICT=$(echo "$OUT" | sed -n 's/^H315_VERDICT: \([A-Z-]*\).*/\1/p')
echo "EXPECTED: the second write of depD refused in words (a 422): an entry's id is one the deposition holds, so its ref would name two readings; depD keeps one entry under d1"
echo "OBSERVED: $(echo "$OUT" | grep '^H315_VERDICT' | sed 's/^H315_VERDICT: [A-Z-]* //'); $(echo "$OUT" | grep '^depD entries kept' ); $(echo "$OUT" | grep '^depD readings offered')"
if [ "$VERDICT" = DEFECT ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
