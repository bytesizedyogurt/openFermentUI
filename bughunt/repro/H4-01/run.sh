#!/usr/bin/env bash
# H4-01: the composed cellulosic_ethanol_v0 at its default, with no value set, closes its cost card on the
# ethanol's set price; cornstover, the same plant unit for unit, closes on the solved price, so the two cards
# differ in their Capital recovery line by the whole gap.
# Run from the repository root: bash bughunt/repro/H4-01/run.sh
# A fresh database bh_r_h4_01_card, a keyless service on 127.0.0.1:10220 serving the built app, one project, two
# library runs with no inputs, each run's page read in Chromium; then the service stopped, the database dropped
# and the service's data copy and the run files removed. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H4-01
DB=bh_r_h4_01_card
PORT=10220
OUT=$BH_WORK/H4-01/out
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
bh_project "$ORIGIN" h401 "H4-01" >/dev/null
IDS=$(bh_env H401_ORIGIN="$ORIGIN" H401_PROJECT=h401 H401_OUT="$OUT" "$PY" -I "$HERE/compare.py" run) || {
  echo "EXPECTED: two library runs"; echo "OBSERVED: $IDS"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "runs: $IDS"
(cd "$BH_ROOT" && NO_PROXY='*' no_proxy='*' timeout 180 node "$HERE/screen.mjs" "$ORIGIN" h401 "$OUT" $IDS) 2>&1 \
  | sed 's/^/[screen.mjs] /'
[ -f "$OUT/cellulosic_ethanol_v0.png" ] && cp "$OUT/cellulosic_ethanol_v0.png" "$HERE/screen-cellulosic_ethanol_v0.png"
bh_env H401_OUT="$OUT" "$PY" -I "$HERE/compare.py" judge \
  || { echo "OBSERVED: compare.py judge failed"; echo "RESULT: NO-DEFECT"; }
exit 0
