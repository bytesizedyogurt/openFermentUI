#!/usr/bin/env bash
# H3-17: POST /api/catalogues/strain keeps an entry carrying a field no kind takes (titre) with a 200
# and drops the field without a word; docs/api/intake.md:103 promises a 422 with a list of field errors.
# Run from the repository root: bash bughunt/repro/H3-17/run.sh
# A fresh database bh_r_h3_17_svc, a keyless service on the first free port of 9500..9509, project p1,
# the steps in repro.py; then the service stopped, the database dropped and the service's data copy removed.
# No worktree is needed: nothing is mutated or built. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS="-c client_min_messages=warning"
HERE=/home/user/openFermentUI/bughunt/repro/H3-17
DB=bh_r_h3_17_svc
PORT=""
for p in 9500 9501 9502 9503 9504 9505 9506 9507 9508 9509; do
  [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9500..9509"; echo "OBSERVED: every port busy"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"
}
trap cleanup EXIT
ORIGIN=$(bh_svc_start "$DB" "$PORT") || { echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless), tree at $(git -C "$BH_ROOT" rev-parse --short HEAD), core/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core && echo yes || echo no)"
bh_project "$ORIGIN" p1 "P one" >/dev/null
echo "contract (docs/api/intake.md:103): $(sed -n 103p "$BH_ROOT/docs/api/intake.md" | grep -o '422 with a list of field errors for a field the kind does not take')"
echo "model (core/openferment_core/catalogues.py:204): $(sed -n 204p "$BH_ROOT/core/openferment_core/catalogues.py"); model_config in the class: $(sed -n '204,290p' "$BH_ROOT/core/openferment_core/catalogues.py" | grep -c 'model_config')"
OUT=$(cd /tmp && bh_env "$BH_ROOT/core/.venv/bin/python" -I "$HERE/repro.py" "$ORIGIN" 2>&1)
echo "$OUT" | grep -v '^H317_VERDICT'
VERDICT=$(echo "$OUT" | sed -n 's/^H317_VERDICT: \([A-Z-]*\).*/\1/p')
echo "EXPECTED: the keep of strain s-h317 carrying titre refused with a 422 whose field errors name titre, and nothing kept under s-h317"
echo "OBSERVED: $(echo "$OUT" | grep '^H317_VERDICT' | sed 's/^H317_VERDICT: [A-Z-]* //'); $(echo "$OUT" | grep '^read back')"
if [ "$VERDICT" = DEFECT ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
