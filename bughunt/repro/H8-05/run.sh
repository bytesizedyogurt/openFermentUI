#!/usr/bin/env bash
# H8-05: POST /api/flowsheets/import-url answers 500 Internal Server Error when a public host answers
# 302 with a Location that has a scheme and no host ('https:127.0.0.1/x', 'javascript:alert(1)').
#   bash bughunt/repro/H8-05/run.sh        (from the repository root; exits 0 either way)
# The app runs in process through TestClient over a fresh test database; httpx's transport and the
# collectors' resolver are stand-ins, so nothing leaves the machine. No service port, no model call.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
unset OPENFERMENT_FIXTURES OPENFERMENT_FIXTURE_DIR
export PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h8_05_importurl
HERE=/home/user/openFermentUI/bughunt/repro/H8-05
SCRATCH="$BH_WORK/H8-05"
cleanup() { bh_db_drop "$DB"; rm -rf "$SCRATCH"; }
trap cleanup EXIT

bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head)"
mkdir -p "$SCRATCH/data/sff-library"
OUT=$(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
        OPENFERMENT_DATA_DIR="$SCRATCH/data" OPENFERMENT_SFF_LIBRARY="$SCRATCH/data/sff-library" \
        .venv/bin/python -I "$HERE/repro.py" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):' | grep -v -E '^INFO (httpx|openferment.api)'
echo "openferment.flowsheets rows in project h8-05 (nothing should be kept):" \
  "$(psql "$BH_SERVER/$DB" -qXAt -c "SELECT count(*) FROM openferment.flowsheets WHERE project_id='h8-05'" 2>&1)"
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "$OUT" | grep -E '^RESULT: ' || echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
exit 0
