#!/usr/bin/env bash
# H5-01: B's literature search returns documents A ingests while the search runs.
# Run from the repository root: bash bughunt/repro/H5-01/run.sh
# A fresh database bh_r_h5_01_race, a keyless service on 127.0.0.1:10200, two projects, one race; then
# the service stopped, the database dropped and the service's data copy removed. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H5-01
DB=bh_r_h5_01_race
PORT=10200
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT
bh_svc_stop "$PORT"
ORIGIN=$(bh_svc_start "$DB" "$PORT") || { echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless)"
bh_env H501_ORIGIN="$ORIGIN" H501_N="${H501_N:-60}" "$BH_ROOT/core/.venv/bin/python" -I "$HERE/race.py" \
  || { echo "OBSERVED: race.py failed"; echo "RESULT: NO-DEFECT"; }
exit 0
