#!/usr/bin/env bash
# H5-04 (with H2-04): a locked study runbook is taken back through DELETE /api/state/runbooks/{id}, its lock
# left behind, and made again it answers as an unlocked draft. Run from the repository root:
#   bash bughunt/repro/H5-04/run.sh
# A fresh database bh_r_h5_04_locked, a keyless service on the first free port of 127.0.0.1:9630-9639, one
# project, one kinetics run on person assumptions, one study runbook locked, then the DELETE, the reads, the
# make again and the audit; then the service stopped, the database dropped and the service's data copy removed.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H5-04
DB=bh_r_h5_04_locked
PORT=
for p in $(seq 9630 9639); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9630-9639"; echo "OBSERVED: none free"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT
ORIGIN=$(bh_svc_start "$DB" "$PORT") \
  || { echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless)"
echo "commit: $(git -C "$BH_ROOT" rev-parse --short HEAD); core/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core && echo yes || echo no)"
bh_env ORIGIN="$ORIGIN" "$BH_ROOT/core/.venv/bin/python" -I "$HERE/locked_back.py" \
  || { echo "OBSERVED: locked_back.py failed"; echo "RESULT: NO-DEFECT"; }
if grep -qi "api.anthropic.com" "$BH_WORK/svc-$PORT.log" 2>/dev/null; then echo "note: the service log names api.anthropic.com"; fi
exit 0
