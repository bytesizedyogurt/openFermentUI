#!/usr/bin/env bash
# H6-02: `pnpm db:import-alpha1` carries a verified decision whose gold value is a model's estimate into the
# record store, and BioRepo serves it as verified, gold; the record store's own door refuses the same decision.
# Run from the repository root: bash bughunt/repro/H6-02/run.sh
# One alpha 1.0 data directory (biorepo.json alone, written by alpha 1.0's own models, an origin of kind
# model-estimate added to the gold value), a fresh database bh_r_h6_02_import, the importer, then a keyless
# service on 127.0.0.1:10230 that reads the result and asks its own door. Everything made is removed after.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=$BH_ROOT/bughunt/repro/H6-02
DB=bh_r_h6_02_import
PORT=10230
W=$BH_WORK/H6-02
DATA=$W/alpha1-data
URL=$BH_SERVER/$DB
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$W"
}
trap cleanup EXIT
verdict() { echo "RESULT: $1"; exit 0; }
bh_svc_stop "$PORT"
rm -rf "$W"; mkdir -p "$W"

echo "== 1. an alpha 1.0 biorepo.json, written by alpha 1.0's models, the gold value given an origin model-estimate"
git -C "$BH_ROOT" show alpha-1.0:core/openferment_core/models.py > "$W/models-a1.py"
(cd "$W" && bh_env "$BH_ROOT/core/.venv/bin/python" -I "$HERE/gen.py" "$W/models-a1.py" "$DATA") > "$W/gen.out" 2>&1 \
  || { cat "$W/gen.out"; echo "EXPECTED: a data directory to import"; echo "OBSERVED: gen.py failed"; verdict NO-DEFECT; }
sed 's/^/  /' "$W/gen.out"
DECISION=$(head -1 "$W/gen.out")

echo "== 2. the importer (package.json's db:import-alpha1 module, the tree's own venv) into a fresh $DB"
bh_db_fresh "$DB" || { echo "EXPECTED: a fresh database"; echo "OBSERVED: bh_db_fresh failed"; verdict NO-DEFECT; }
( cd "$BH_ROOT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 OPENFERMENT_DATABASE_URL="$URL" \
    .venv/bin/python -m openferment_core.import_alpha1 --name "Alpha 1.0 estimate" --by "Ada Moreno" --data "$DATA" ) \
  > "$W/import.out" 2>&1
IMPORT_EXIT=$?
sed 's/^/  /' "$W/import.out"
echo "  exit $IMPORT_EXIT"
PID=$(sed -n 's/^carried .* into project \([^:]*\):$/\1/p' "$W/import.out")
if [ "$IMPORT_EXIT" != 0 ] || [ -z "$PID" ]; then
  echo "EXPECTED: the importer refuses the decision (rule estimate), naming biorepo.json and cl1-P1-0001, nothing written"
  echo "OBSERVED: the importer did not carry the directory (exit $IMPORT_EXIT): $(grep -m1 '^refused:' "$W/import.out")"
  verdict NO-DEFECT
fi
ROW=$(psql "$URL" -XAtc "select body->>'status', body->>'provenance', body->'gold'->'origin'->>'kind', body->'gold'->'origin'->>'by'
                          from openferment.decisions where project_id='$PID' and record_id='cl1-P1-0001'")
echo "  the decisions row (status|provenance|gold origin kind|by): $ROW"

echo "== 3. a keyless service on $PORT over the imported database: BioRepo's overlay, then its own door"
ORIGIN=$(BH_KEEP_DB=1 bh_svc_start "$DB" "$PORT") \
  || { echo "EXPECTED: a service to read the import"; echo "OBSERVED: the service did not start"; verdict NO-DEFECT; }
H="X-OpenFerment-Project: $PID"
OVERLAY=$(curl -s --noproxy '*' -H "$H" "$ORIGIN/api/biorepo/overlay" | python3 -c "
import json,sys; r=json.load(sys.stdin)['records'].get('cl1-P1-0001') or {}
g=r.get('gold') or {}; o=g.get('origin') or {}
print(r.get('status'), r.get('provenance'), g.get('value'), g.get('unit'), o.get('kind'), o.get('by'))")
echo "  GET /api/biorepo/overlay reads cl1-P1-0001 (status provenance gold.value gold.unit origin.kind origin.by): $OVERLAY"
CHECK=$(curl -s --noproxy '*' -H "$H" -H 'content-type: application/json' -X POST "$ORIGIN/api/biorepo/check" -d "$DECISION" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ok'), d.get('rule'), '|', (d.get('why') or '')[:150])")
echo "  POST /api/biorepo/check with the same decision: ok rule | why: $CHECK"

echo "EXPECTED: the importer refuses the directory as biorepo.write refuses the decision (rule estimate): a model's estimate never enters a record store (CLAUDE.md:54)"
echo "OBSERVED: import exit $IMPORT_EXIT into project $PID; BioRepo serves cl1-P1-0001 as '$OVERLAY'; the store's own door answers '$CHECK'"
set -- $OVERLAY
if [ "${1:-}" = verified ] && [ "${2:-}" = gold ] && [ "${5:-}" = model-estimate ] && [ "${CHECK%% *}" = False ] \
   && [ "$(echo "$CHECK" | awk '{print $2}')" = estimate ]; then
  verdict DEFECT
fi
verdict NO-DEFECT
