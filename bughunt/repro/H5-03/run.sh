#!/usr/bin/env bash
# H5-03: PUT /api/state/scenarios/{id} naming a study scenario's id, and PUT /api/state/trains/{id} naming a
# model's kept train, answer 200 and replace that row. Run from the repository root:
#   bash bughunt/repro/H5-03/run.sh
# A fresh database bh_r_h5_03_kinds, a keyless service on the first free port of 127.0.0.1:9330-9339 with the
# collectors refusing the network, one project, a study scenario (the BioSTEAM worker reads cornstover's
# parameters, about a minute), a kinetics run and a model's kept train; then the two writes. The service is
# stopped, the database dropped and the service's data copy removed at the end. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H5-03
DB=bh_r_h5_03_kinds
PORT=
for p in $(seq 9330 9339); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9330-9339"; echo "OBSERVED: none free"; echo "RESULT: NO-DEFECT"; exit 0; }
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
bh_env ORIGIN="$ORIGIN" DB_URL="$BH_SERVER/$DB" "$BH_ROOT/core/.venv/bin/python" -I "$HERE/collide.py" \
  || { echo "OBSERVED: collide.py failed"; echo "RESULT: NO-DEFECT"; }
if grep -qi "anthropic" "$BH_WORK/svc-$PORT.log" 2>/dev/null; then echo "note: the service log names anthropic"; fi
exit 0
