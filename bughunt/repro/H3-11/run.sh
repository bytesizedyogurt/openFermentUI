#!/usr/bin/env bash
# H3-11: an estimate whose basis says 'about 30% above the 2011 design report' drops its claim, and the same
# words as study_scenario's quantity note are stamped into the estimate's origin and kept in the run's basis.
#   bash bughunt/repro/H3-11/run.sh        (from the repository root; exits 0 either way)
# A fresh test database (bh_r_h3_11_doors, migrated to head); repro.py with the repository's Python asks one
# question through the service's answer path (api._answer, the body of POST /api/ask) of a stand-in model that
# calls study_scenario, then engine_run, then answers a plan. The worker is the tests' stand-in: no BioSTEAM, no
# service, no key, no model call, no network. The database and the scratch data directory are removed on exit.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
export PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h3_11_doors
HERE=/home/user/openFermentUI/bughunt/repro/H3-11
DATA="$BH_WORK/H3-11/data"
cleanup() { bh_db_drop "$DB"; rm -rf "$BH_WORK/H3-11"; }
trap cleanup EXIT

BEFORE=$(git -C "$BH_ROOT" status --porcelain -- core src scripts examples | md5sum)
bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head)"
mkdir -p "$DATA"

echo "== the two rules as the tree writes them =="
grep -n -E "estimate's basis holds a number" "$BH_ROOT/core/openferment_core/validate.py"
grep -n -E '"basis": \{"type": "string", "description"' "$BH_ROOT/core/openferment_core/postdoc_agent.py"
grep -n -E 'note: str = Field\(default="", max_length=600, description="What the value rests on' \
  "$BH_ROOT/core/openferment_core/tools/__init__.py"
grep -n -E 'origin.model_copy\(update=\{"note"' "$BH_ROOT/core/openferment_core/tools/__init__.py"
grep -n -E 'note=f"estimated on' "$BH_ROOT/core/openferment_core/basis.py"
echo

echo "== one ask with a stand-in model =="
OUT=$(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_FIXTURES=1 \
        OPENFERMENT_DATA_DIR="$DATA" OPENFERMENT_SFF_LIBRARY="$DATA/sff-library" PYTHONDONTWRITEBYTECODE=1 \
        .venv/bin/python "$HERE/repro.py" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|PYRESULT):'
echo

echo "the rows the ask left (openferment.scenarios, openferment.runs), read with psql:"
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "SELECT 'scenario', id, v->'quantity'->'origin'->>'kind', v->'quantity'->'origin'->>'note'
     FROM openferment.scenarios, jsonb_array_elements(body::jsonb->'values') AS v
    WHERE project_id='h3-11' ORDER BY id" 2>&1
psql "$BH_SERVER/$DB" -qXAt -F ' | ' -c \
  "SELECT 'run', id, i->'quantity'->'origin'->>'kind', i->'quantity'->'origin'->>'note'
     FROM openferment.runs, jsonb_array_elements(body::jsonb->'inputs') AS i
    WHERE project_id='h3-11' AND i->>'name'='stream.sugarcane.price' ORDER BY id" 2>&1
AFTER=$(git -C "$BH_ROOT" status --porcelain -- core src scripts examples | md5sum)
[ "$BEFORE" = "$AFTER" ] && echo "core/, src/, scripts/, examples/: unchanged by this run" \
                         || echo "core/, src/, scripts/, examples/: CHANGED by this run (see git status)"
echo

echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
if echo "$OUT" | grep -q '^PYRESULT: DEFECT'; then
  echo "RESULT: DEFECT"
elif echo "$OUT" | grep -q '^PYRESULT: NO-DEFECT'; then
  echo "RESULT: NO-DEFECT"
else
  echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
fi
exit 0
