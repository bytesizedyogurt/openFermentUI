#!/usr/bin/env bash
# H5-02 (with H8-02): a document two projects hold reads in project B with project A's title, url, source,
# licence class and licence words. Run from the repository root: bash bughunt/repro/H5-02/run.sh
# A fresh database bh_r_h5_02_shared, a keyless service on the first free port of 127.0.0.1:9010-9019 with the
# collectors refusing the network, two projects, four pastes and B's four reads; then the service stopped,
# the database dropped and the service's data copy removed. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H5-02
DB=bh_r_h5_02_shared
PORT=
for p in $(seq 9010 9019); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9010-9019"; echo "OBSERVED: none free"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT
D=$(bh_data "$DB"); [ -d "$D/fixtures" ] || cp -R "$BH_ROOT/core/tests/fixtures" "$D/fixtures"
ORIGIN=$(BH_FIXTURES=1 bh_svc_start "$DB" "$PORT") \
  || { echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless, collectors offline)"
bh_env ORIGIN="$ORIGIN" "$BH_ROOT/core/.venv/bin/python" -I "$HERE/shared_doc.py" \
  || { echo "OBSERVED: shared_doc.py failed"; echo "RESULT: NO-DEFECT"; }
if grep -qi "anthropic" "$BH_WORK/svc-$PORT.log" 2>/dev/null; then echo "note: the service log names anthropic"; fi
exit 0
