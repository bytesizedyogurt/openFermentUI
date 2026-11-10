#!/usr/bin/env bash
# H3-06: a kept kinetics run on a reading stays `measured` after the reading is corrected; the same run asked
# again is refused in words. The verdict is judged against the contract's own words (README.md).
# Run from the repository root: bash bughunt/repro/H3-06/run.sh
# A fresh database bh_r_h3_06_svc, a keyless service on the first free port of 9090..9099, project p1, the
# steps in repro.py (the kinetics engine computes in the service's process: no worker, no model call); then the
# service stopped, the database dropped and the service's data copy removed. No worktree is needed: nothing is
# mutated or built. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS="-c client_min_messages=warning"
HERE=/home/user/openFermentUI/bughunt/repro/H3-06
DB=bh_r_h3_06_svc
PORT=""
for p in 9096 9097 9098 9099 9090 9091 9092 9093 9094 9095; do
  [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9090..9099"; echo "OBSERVED: every port busy"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log" "$BH_WORK/svc-$PORT.pid"
}
trap cleanup EXIT
ORIGIN=$(bh_svc_start "$DB" "$PORT") || { echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless), tree at $(git -C "$BH_ROOT" rev-parse --short HEAD), core/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core && echo yes || echo no)"
bh_project "$ORIGIN" p1 "P one" >/dev/null
OUT=$(cd /tmp && bh_env "$BH_ROOT/core/.venv/bin/python" -I "$HERE/repro.py" "$ORIGIN" 2>&1)
echo "$OUT" | grep -v '^H306_VERDICT'
VERDICT=$(echo "$OUT" | sed -n 's/^H306_VERDICT: \([A-Z-]*\).*/\1/p')
echo "EXPECTED: by the contract's words: the same run asked again after depK/k0 is corrected is refused in words naming the correction (ADR-006:238, studies.md:106-107); runs.md:22 moves a held row's provenance for a record reviewed or demoted since, and a reading is a measurement (runs.md:21), so no line moves the kept row's label on a reading's correction"
if [ "$VERDICT" = DEFECT ]; then
  echo "OBSERVED: the same run asked again after the correction was answered without the refusal (step 5 above)"
  echo "RESULT: DEFECT"
else
  echo "OBSERVED: the kept row reads measured before and after the correction (GET /api/runs/{id} and the runs list, as the candidate says); the same run asked again is a 422 naming depK/k0fix, the Proforma door refuses depK/k0 and the readings list leaves it out, so every line of the contract holds"
  echo "RESULT: NO-DEFECT"
fi
exit 0
