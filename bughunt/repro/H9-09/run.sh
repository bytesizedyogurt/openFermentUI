#!/usr/bin/env bash
# H9-09: a call held before midnight UTC settles its cost into the next day, which never counted its hold,
# so the next day's spend passes OPENFERMENT_DAILY_BUDGET_USD. A fresh test database, no service, no model call.
# usage, from the repository root: bash bughunt/repro/H9-09/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H9-09
DB=bh_r_h9_09_spend
T=$BH_WORK/H9-09; mkdir -p "$T"
cleanup() { bh_db_drop "$DB"; rm -rf "$T"; }
trap cleanup EXIT

echo "EXPECTED: with a 1.00 USD cap, two calls whose worst case is 0.90 each never both spend on one UTC day:"
echo "EXPECTED: a call held at 23:59:30 and settled at 00:00:40 either counts against the new day while in flight"
echo "EXPECTED: (so a 0.90 call asked at 00:00:10 is refused) or is charged to the day that held it"
echo "EXPECTED: (llm.py:37-39: a call whose worst case could take the UTC day past OPENFERMENT_DAILY_BUDGET_USD is refused before it is sent)."

bh_db_fresh "$DB" || { echo "OBSERVED: the test database could not be made"; echo "RESULT: NO-DEFECT"; exit 0; }
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DAILY_BUDGET_USD=1.00 \
   .venv/bin/python "$HERE/across_midnight.py") > "$T/out.log" 2>&1
grep -v '^VERDICT:' "$T/out.log"
rows=$(psql "$BH_SERVER/$DB" -AtXc "select day, state, usd from openferment.spend order by seq" | tr '\n' ' ')
echo "OBSERVED: spend rows (day|state|usd): $rows"
if grep -q '^VERDICT: DEFECT$' "$T/out.log"; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
