#!/usr/bin/env bash
# H3-01: anchoring (§2.4 rule 3) compares a quote's number bare when the quote's unit does not convert
# into the candidate's, labels it `converted`, and biorepo.write promotes such a record to verified or gold.
#   bash bughunt/repro/H3-01/run.sh        (from the repository root; exits 0 either way)
# Pure anchoring calls, then a reviewer's decisions through biorepo.write on a fresh test database.
# No service, no model call, no network.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
DB=bh_r_h3_01_anchor
HERE=/home/user/openFermentUI/bughunt/repro/H3-01
cleanup() { PGOPTIONS='-c client_min_messages=warning' bh_db_drop "$DB"; }
trap cleanup EXIT

(export PGOPTIONS='-c client_min_messages=warning'; bh_db_fresh "$DB") \
  || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head)"
export OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB"
export OPENFERMENT_FIXTURES=1
OUT=$(bh_py "$HERE/repro.py" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):'
echo "the database's records rows (openferment.records) the decisions left:"
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "SELECT id, field, value, unit, provenance, quote FROM openferment.records WHERE project_id='h3-01' ORDER BY id, version" 2>&1
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "$OUT" | grep -E '^RESULT: ' || echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
exit 0
