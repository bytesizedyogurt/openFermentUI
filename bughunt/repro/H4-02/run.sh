#!/usr/bin/env bash
# H4-02: a custom_train_v1 run's cost card closes on the TEA's price per kg of the product stream while its lines
# are per kg of the product the stream contains and sum to the run's base price; the note under it says the lines
# sum to the closing row and that the TEA solved another price.
# Run from the repository root: bash bughunt/repro/H4-02/run.sh
# A fresh database bh_r_h4_02_card, a keyless service on 127.0.0.1:9030 serving the built app, one project; a
# fermOS simulation, its vessel design, an ethanol_glucose_v0 run read into a train and the train run, then the
# composite run from the vessel and the train run; its page read in Chromium. Then the service stopped, the
# database dropped and the service's data copy and the run files removed. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H4-02
DB=bh_r_h4_02_card
PORT=9030
OUT=$BH_WORK/H4-02/out
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
bh_project "$ORIGIN" h402 "H4-02" >/dev/null
ID=$(cd "$BH_ROOT/core" && bh_env H402_ORIGIN="$ORIGIN" H402_PROJECT=h402 H402_OUT="$OUT" "$PY" -I "$HERE/chain.py" run \
  2> >(sed 's/^/[chain.py] /' >&2)) || {
  echo "EXPECTED: a composite run"; echo "OBSERVED: the chain stopped: $ID"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "composite run: $ID"
(cd "$BH_ROOT" && NO_PROXY='*' no_proxy='*' timeout 180 node "$HERE/screen.mjs" "$ORIGIN" h402 "$OUT" "$ID") 2>&1 \
  | sed 's/^/[screen.mjs] /'
[ -f "$OUT/composite.png" ] && cp "$OUT/composite.png" "$HERE/screen-composite.png"
bh_env H402_OUT="$OUT" "$PY" -I "$HERE/chain.py" judge \
  || { echo "OBSERVED: chain.py judge failed"; echo "RESULT: NO-DEFECT"; }
exit 0
