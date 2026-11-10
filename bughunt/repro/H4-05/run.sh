#!/usr/bin/env bash
# H4-05: a batch_v1 run with μmax 0, asked to run until the sugar runs out, is refused because "the sugar never runs
# out"; β or maintenance drains the sugar at a constant rate, and the same family, given a run length, reports
# the hour it runs out. Run from the repository root: bash bughunt/repro/H4-05/run.sh
# A fresh database bh_r_h4_05_svc, a keyless service on 127.0.0.1:9410, one project, five POSTs to
# /api/fermos/simulate (check.py); then the service stopped, the database dropped and the service's data copy removed.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H4-05
DB=bh_r_h4_05_svc
PORT=9410
PY="$BH_ROOT/core/.venv/bin/python"
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT
bh_svc_stop "$PORT"
ORIGIN=$(bh_svc_start "$DB" "$PORT") || {
  echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless), tree at $(git -C "$BH_ROOT" rev-parse --short HEAD);" \
  "files of core, src, scripts and examples differing from 2047f5a: $(git -C "$BH_ROOT" diff --name-only 2047f5a -- core src scripts examples | wc -l)"
echo "the refusal in the tree:"
grep -n "never runs out" "$BH_ROOT/core/openferment_core/kinetics.py" | sed 's/^/  kinetics.py:/'
bh_project "$ORIGIN" h405 "H4-05" >/dev/null
bh_env H405_ORIGIN="$ORIGIN" H405_PROJECT=h405 "$PY" -I "$HERE/check.py" \
  || { echo "OBSERVED: check.py failed"; echo "RESULT: NO-DEFECT"; }
exit 0
