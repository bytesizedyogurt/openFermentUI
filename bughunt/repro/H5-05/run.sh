#!/usr/bin/env bash
# H5-05: POST /api/fermos/forecast naming a fit the project does not hold answers HTTP 500 with no words.
# Run from the repository root:
#   bash bughunt/repro/H5-05/run.sh
# A fresh database bh_r_h5_05_forecast, a keyless service on the first free port of 127.0.0.1:10310-10319,
# two projects, one kinetic fit kept in the first from a synthetic batch, then the forecast door asked for an
# unknown fit, for the first project's fit from the second, and the tool door's growth_forecast; then the
# service log searched for the exception. The service is stopped, the database dropped and the service's data
# copy removed. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H5-05
DB=bh_r_h5_05_forecast
PORT=
for p in $(seq 10310 10319); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 10310-10319"; echo "OBSERVED: none free"; echo "RESULT: NO-DEFECT"; exit 0; }
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
OUT=$(bh_env ORIGIN="$ORIGIN" "$BH_ROOT/core/.venv/bin/python" -I "$HERE/forecast.py" 2>&1) \
  || OUT="$OUT
OBSERVED: forecast.py failed
RESULT: NO-DEFECT"
echo "$OUT" | grep -v '^RESULT:'
echo
echo "service log ($BH_WORK/svc-$PORT.log), the exception raised through the forecast route:"
grep -E "api.py\", line [0-9]+, in fermos_forecast|fermos.py\", line [0-9]+, in forecast_run" "$BH_WORK/svc-$PORT.log" \
  | sed 's/^[ |]*/  /' | sort | uniq -c
grep -oE "openferment_core.artifacts.ArtifactNotFound: '[^']*'" "$BH_WORK/svc-$PORT.log" | sort | uniq -c | sed 's/^/  /'
grep -q "openferment_core.artifacts.ArtifactNotFound" "$BH_WORK/svc-$PORT.log" \
  && echo "  the log holds openferment_core.artifacts.ArtifactNotFound (a KeyError), past fermos.py:927's except FileNotFoundError"
if grep -qi "api.anthropic.com" "$BH_WORK/svc-$PORT.log" 2>/dev/null; then echo "note: the service log names api.anthropic.com"; fi
echo "$OUT" | grep '^RESULT:' | tail -1
exit 0
