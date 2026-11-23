#!/usr/bin/env bash
# H3-10: validate.claim_values holds an estimate's label and basis to the number rule and takes its unit as any
# non-empty text, so 'USD/gal, about 40 cents above the 2011 design' stands as the unit of a kept value.
#   bash bughunt/repro/H3-10/run.sh        (from the repository root; exits 0 either way)
# A fresh test database (bh_r_h3_10_claims, migrated to head); repro.py with the repository's Python asks one
# question through the service's answer path (api._answer, the body of POST /api/ask) of a stand-in model that
# answers one plan: no service, no key, no model call, no network. The database is dropped on exit.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
export PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h3_10_claims
HERE=/home/user/openFermentUI/bughunt/repro/H3-10
cleanup() { bh_db_drop "$DB"; }
trap cleanup EXIT

bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head)"
export OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB"
export OPENFERMENT_FIXTURES=1
echo "== the rule as written (core/openferment_core/validate.py) =="
grep -n -E 'an estimate names its unit|estimate.get\("unit"\)|basis holds a number' "$BH_ROOT/core/openferment_core/validate.py"
echo
echo "== the answer path with a stand-in model =="
OUT=$(bh_py "$HERE/repro.py" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|PYRESULT):'
echo
echo "the turn row the answer left (openferment.turns, c1's first value as kept):"
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "SELECT id, status, c->>'id', c->>'provenance', c->'values'->0->'quantity'->>'unit'
     FROM openferment.turns, jsonb_array_elements(body::jsonb->'plan'->'claims') AS c
    WHERE project_id='h3-10' ORDER BY id" 2>&1
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
if echo "$OUT" | grep -q '^PYRESULT: DEFECT$'; then
  echo "RESULT: DEFECT"
elif echo "$OUT" | grep -q '^PYRESULT: NO-DEFECT'; then
  echo "RESULT: NO-DEFECT"
else
  echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
fi
exit 0
