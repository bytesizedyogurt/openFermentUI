#!/usr/bin/env bash
# H3-03: a released measured value can be rewritten by any later write, unaudited, and is still served as measured.
# Run from the repository root: bash bughunt/repro/H3-03/run.sh
# A fresh database bh_r_h3_03_svc, a keyless service on the first free port of 9903..9909 then 9900..9902,
# project p1, the writes in repro.py, one look at the deposition screen in Chromium; then the service stopped,
# the database dropped and the service's data copy removed. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS="-c client_min_messages=warning"
HERE=/home/user/openFermentUI/bughunt/repro/H3-03
DB=bh_r_h3_03_svc
PORT=""
for p in 9903 9904 9905 9906 9907 9908 9909 9900 9901 9902; do
  [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9900..9909"; echo "OBSERVED: every port busy"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT
ORIGIN=$(bh_svc_start "$DB" "$PORT") || { echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless), commit $(git -C "$BH_ROOT" rev-parse --short HEAD)"
bh_project "$ORIGIN" p1 "P one" >/dev/null
OUT=$(bh_env "$BH_ROOT/core/.venv/bin/python" -I "$HERE/repro.py" "$ORIGIN" 2>&1)
echo "$OUT" | grep -v '^H303_VERDICT'
if [ -x /opt/pw-browsers/chromium ]; then
  (cd "$BH_ROOT" && NO_PROXY='*' no_proxy='*' timeout 120 node "$HERE/screen.cjs" "$ORIGIN" "$HERE/screen.png") 2>&1 | sed 's/^/[10 deposition screen] /'
fi
VERDICT=$(echo "$OUT" | sed -n 's/^H303_VERDICT: \([A-Z-]*\).*/\1/p')
echo "$OUT" | grep '^H303_VERDICT' | sed 's/^H303_VERDICT: /checks: /'
if [ "$VERDICT" = DEFECT ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
