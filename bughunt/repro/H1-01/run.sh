#!/usr/bin/env bash
# H1-01: identical runs asked at once keep one row whose body `by` and created_by name different askers.
# The head's own service (kinetics, a core engine) on a fresh database, port 9610; keyless, no model call.
# usage, from the repository root: bash bughunt/repro/H1-01/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H1-01
DB=bh_r_h1_01_svc
PORT=9610
T=$BH_WORK/H1-01; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT

echo "EXPECTED: four identical kinetics run requests asked at once, each naming its own asker, keep one runs row"
echo "EXPECTED: whose created_by column and body by name the same asker, and every asker is answered with that name"
echo "EXPECTED: (docs/api/engines.md:541-544: its by and created_by are the first asker's, whoever asks again)."

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" h101 >/dev/null
bh_py -c "from openferment_core.fermos_engine import write_placeholder_inputs as w; w('$T/inputs.json', by='H1-01 repro')"
# One plain run first, so the kinetics worker is warm and the four asks race on the run alone.
(cd "$BH_ROOT/core" && bh_env .venv/bin/python "$HERE/same_at_once.py" "$O" h101 "$DB" "$T/inputs.json" 1 0.39) > "$T/warm.log" 2>&1
sed 's/^/warm: /' "$T/warm.log" | grep -E "CASE|Error|error" | head -5
(cd "$BH_ROOT/core" && bh_env .venv/bin/python "$HERE/same_at_once.py" "$O" h101 "$DB" "$T/inputs.json" 4 0.41 0.42 0.43 0.44 0.45) | tee "$T/race.log"

n=$(grep -c ': DEFECT$' "$T/race.log")
rows=$(psql "$BH_SERVER/$DB" -AtXc "select count(*) from openferment.runs where project_id='h101' and created_by <> body->>'by'")
echo "OBSERVED: $n of 5 values gave a defect line; the database holds $rows runs row(s) whose created_by differs from body by"
if [ "${n:-0}" -gt 0 ] || [ "${rows:-0}" -gt 0 ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
