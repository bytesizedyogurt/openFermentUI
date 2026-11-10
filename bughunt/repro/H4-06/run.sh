#!/usr/bin/env bash
# H4-06: cellulosic_ethanol_v0 reports its denatured product stream's whole mass as ethanolKgPerH and
# ethanolKgPerKgDryFeed, which the Comparison screen names 'Ethanol made per hour' and 'Ethanol per kg of dry feed'.
# Run from the repository root: bash bughunt/repro/H4-06/run.sh
# A fresh database bh_r_h4_06_run, a keyless service on a free port among 127.0.0.1:9710-9719, one project, one
# library run of cellulosic_ethanol_v0 with no inputs (its default configuration); the run's outputs set beside
# its own ethanol stream. Then the service stopped, the database dropped, the data copy and run file removed.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H4-06
DB=bh_r_h4_06_run
PY="$BH_ROOT/core/.venv/bin/python"
OUT=$BH_WORK/H4-06/out
PORT=""
for p in 9710 9711 9712 9713 9714 9715 9716 9717 9718 9719; do
  [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9710-9719"; echo "OBSERVED: none free"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$OUT"
}
trap cleanup EXIT
rm -rf "$OUT"; mkdir -p "$OUT"
ORIGIN=$(bh_svc_start "$DB" "$PORT") || {
  echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless), tree at $(git -C "$BH_ROOT" rev-parse --short HEAD);" \
  "files of core, src, scripts and examples differing from 2047f5a: $(git -C "$BH_ROOT" diff --name-only 2047f5a -- core src scripts examples | wc -l)"
bh_project "$ORIGIN" h406 "H4-06" >/dev/null
curl -s --noproxy '*' --max-time 600 -X POST "$ORIGIN/api/library/cellulosic_ethanol_v0/run" \
  -H 'content-type: application/json' -H 'X-OpenFerment-Project: h406' -d '{"by":"h406"}' > "$OUT/run.json"
bh_env "$PY" -I "$HERE/judge.py" "$OUT/run.json" "$BH_ROOT" \
  || { echo "OBSERVED: judge.py failed"; echo "RESULT: NO-DEFECT"; }
exit 0
