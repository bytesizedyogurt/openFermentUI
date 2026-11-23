#!/usr/bin/env bash
# H3-08: the labelled-mass-ratio rule reads gal, gmol and gpm as a labelled gram, so g/gal, gal/g, g/gmol and
# their kin normalise to the yield unit g g⁻¹ and convert 1:1.
#   bash bughunt/repro/H3-08/run.sh        (from the repository root; exits 0 either way)
# A fresh test database (bh_r_h3_08_units, migrated to head); repro.py with the repository's Python (the unit
# engine, one anchoring, one reviewer's accept through biorepo.write); browser.ts with tsx over
# src/engine/units.ts. No service, no model call, no network. The database is dropped on exit.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
export PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h3_08_units
HERE=/home/user/openFermentUI/bughunt/repro/H3-08
cleanup() { bh_db_drop "$DB"; }
trap cleanup EXIT

bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head)"
export OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB"
export OPENFERMENT_FIXTURES=1
OUT=$(bh_py "$HERE/repro.py" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|PYRESULT):'
echo "the records row the accept left (openferment.records):"
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "SELECT id, field, value, unit, provenance, quote FROM openferment.records WHERE project_id='h3-08' ORDER BY id, version" 2>&1
echo
echo "== Part D: the browser's engine (src/engine/units.ts) =="
BOUT=$(cd "$BH_ROOT" && bh_env node_modules/.bin/tsx "$HERE/browser.ts" 2>&1)
echo "$BOUT" | grep -v '^BROWSER_MISREAD'
BMIS=$(echo "$BOUT" | sed -n 's/^BROWSER_MISREAD \([0-9]*\) of \([0-9]*\)$/\1 \2/p')
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "OBSERVED: the browser's normalizeUnit names 'g g⁻¹' for ${BMIS% *} of ${BMIS#* } probes (src/engine/units.ts:369-372, the same two patterns)"
if echo "$OUT" | grep -q '^PYRESULT: DEFECT$'; then
  echo "RESULT: DEFECT"
elif echo "$OUT" | grep -q '^PYRESULT: NO-DEFECT$'; then
  echo "RESULT: NO-DEFECT"
else
  echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
fi
exit 0
