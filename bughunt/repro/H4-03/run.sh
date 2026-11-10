#!/usr/bin/env bash
# H4-03: cornstover run twice through POST /api/library/cornstover/run, once with nothing set and once with its
# feedstock price set to the library's own default; the second run is simulated a second time, unsettled, and
# prices ethanol about 2.3e-5 apart from the first, where the run's basis states ten significant digits.
# Run from the repository root: bash bughunt/repro/H4-03/run.sh
# A fresh database bh_r_h4_03_feed, a keyless service on 127.0.0.1:10300, one project, the plant's parameters read
# and two library runs; then the service stopped, the database dropped and the service's data copy and the run
# files removed. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H4-03
DB=bh_r_h4_03_feed
PORT=10300
OUT=$BH_WORK/H4-03/out
PY="$BH_ROOT/core/.venv/bin/python"
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$OUT"
}
trap cleanup EXIT
bh_svc_stop "$PORT"
rm -rf "$OUT"; mkdir -p "$OUT"
ORIGIN=$(bh_svc_start "$DB" "$PORT") || {
  echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless), tree at $(git -C "$BH_ROOT" rev-parse --short HEAD);" \
  "files of core, src, scripts and examples differing from 2047f5a: $(git -C "$BH_ROOT" diff --name-only 2047f5a -- core src scripts examples | wc -l)"
bh_project "$ORIGIN" h403 "H4-03" >/dev/null
bh_env H403_ORIGIN="$ORIGIN" H403_PROJECT=h403 H403_OUT="$OUT" "$PY" -I "$HERE/check.py" \
  || { echo "OBSERVED: check.py failed"; echo "RESULT: NO-DEFECT"; }
exit 0
