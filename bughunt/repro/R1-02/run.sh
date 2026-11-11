#!/usr/bin/env bash
# R1-02: a Departures row of docs/PROGRESS.md still gives "No store holds a protocol in this build" as
# its reason, while the tree at 2047f5a keeps a project's protocols (E.12a, ADR-017).
# bash bughunt/repro/R1-02/run.sh (from the repository root). Keyless, no model call.
#   1. reads docs/PROGRESS.md at 2047f5a: the row that carries the sentence, the section it stands in,
#      the later row of the same table that says a project keeps its protocols since E.12a, and the
#      E.12a notes the Decisions row and ADR-016 carry;
#   2. makes a fresh database bh_r_r1_02_store, starts the service over it on 127.0.0.1:10940, keeps one
#      placeholder protocol through POST /api/protocols and reads it back from the route and the table.
# DEFECT: the row still says no store holds a protocol, it names no later step, and the store of this
# build keeps and serves one. The database is dropped and the service stopped at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
C=2047f5a
DB=bh_r_r1_02_store
PORT=10940
P=bh-r1-02
SENT="No store holds a protocol in this build"
TMP="$BH_WORK/R1-02/tmp-$$"

left() { psql "$BH_SERVER/postgres" -XAtc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_r1\_02\_%'" 2>/dev/null; }
dropall() {
  local i d; for i in 1 2 3 4 5; do
    [ -z "$(left)" ] && return 0
    for d in $(left); do bh_db_drop "$d" >/dev/null 2>&1; done; sleep 1
  done
}
cleanup() {
  bh_svc_stop "$PORT" >/dev/null 2>&1
  dropall
  rm -rf "$TMP"
}
trap cleanup EXIT
nodefect() { echo "$1"; echo "RESULT: NO-DEFECT"; exit 0; }
mkdir -p "$TMP"
cd "$BH_ROOT" || nodefect "no repository at $BH_ROOT"
git show "$C:docs/PROGRESS.md" > "$TMP/PROGRESS.md" || nodefect "cannot read docs/PROGRESS.md at $C"
F="$TMP/PROGRESS.md"

# ── 1. the record ───────────────────────────────────────────────────────
echo "== 1. docs/PROGRESS.md at $C"
ROW=$(grep -n -F "$SENT" "$F" | head -1 | cut -d: -f1)
[ -n "$ROW" ] || nodefect "no line of docs/PROGRESS.md at $C says: $SENT"
SECTION=$(awk -v n="$ROW" 'NR<=n && /^## /{s=$0} NR==n{print s; exit}' "$F")
WHERE=$(sed -n "${ROW}p" "$F" | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}')
WHY=$(sed -n "${ROW}p" "$F" | awk -F'|' '{gsub(/^ +| +$/,"",$4); print $4}')
echo "   line $ROW, under \"$SECTION\", row \"$WHERE\""
echo "   its Why: $WHY"
ROW_LATER=$(sed -n "${ROW}p" "$F" | grep -c -E "E\.12a|ADR-017|E\.12[^a]|since E\.")
echo "   later steps the row names (E.12a, E.12, ADR-017): $ROW_LATER"
SAME=$(awk -v n="$ROW" 'NR>n && /^## /{exit} NR>n && /A project keeps its protocols on the service since E\.12a/{print NR}' "$F" | head -1)
if [ -n "$SAME" ]; then
  echo "   the same table, line $SAME, row \"$(sed -n "${SAME}p" "$F" | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}')\", says:"
  sed -n "${SAME}p" "$F" | grep -o "A project keeps its protocols on the service since E\.12a[^|]*" | sed 's/^/     /'
fi
DEC=$(grep -n "^| \[016\]" "$F" | head -1)
echo "   the Decisions row of ADR-016 (line ${DEC%%:*}): $(echo "$DEC" | grep -o "alpha 2.2 E.12a[^)]*")"
ADR=$(git show "$C:docs/decisions/ADR-016-bench-readings-alone.md" | grep -n "Implementation note (alpha 2.2 E.12a)")
echo "   docs/decisions/ADR-016-bench-readings-alone.md:${ADR%%:*}: ${ADR#*:}"
MIG=$(git show "$C:core/openferment_core/db/alembic/versions/0010_protocols.py" | grep -n "create_table('protocols'")
echo "   core/openferment_core/db/alembic/versions/0010_protocols.py:${MIG%%:*}: $(echo "${MIG#*:}" | sed 's/^ *//')"
PATHS=$(git show "$C:docs/api/openapi.json" | python3 -c "import json,sys; print(' '.join(p for p in json.load(sys.stdin)['paths'] if 'protocol' in p))")
echo "   docs/api/openapi.json protocol paths: $PATHS"

# ── 2. the store of this build ──────────────────────────────────────────
echo "== 2. the store: a fresh database $DB, the service on 127.0.0.1:$PORT"
O=$(bh_svc_start "$DB" "$PORT" 2>"$TMP/start.err") || nodefect "the service did not start; see $BH_WORK/svc-$PORT.log"
TABLE=$(psql "$BH_SERVER/$DB" -XAtc "SELECT table_schema || '.' || table_name FROM information_schema.tables WHERE table_schema = 'openferment' AND table_name = 'protocols'")
echo "   after migration to head, information_schema.tables holds: ${TABLE:-no protocols table}"
echo "   POST /api/projects: $(bh_project "$O" "$P" | head -c 120)"
H=(-H 'content-type: application/json' -H "X-OpenFerment-Project: $P")
BODY='{"protocol": {"id": "PR-PLACEHOLDER", "title": "A placeholder protocol", "category": "sop", "bsl": 1,
  "organisms": ["Placeholder organism"], "purpose": "A placeholder purpose.", "currentVersion": "1.0",
  "versions": [{"version": "1.0", "baseBatch": {"value": 1, "unit": "placeholder-unit", "label": "placeholder batch"},
    "materials": [], "steps": [{"id": "s1", "text": "A placeholder step.", "skills": []}],
    "estMinutes": {"active": 1, "total": 2}}]}, "by": "Ada"}'
CODE=$(curl -s --noproxy '*' -o "$TMP/made.json" -w '%{http_code}' -X POST "$O/api/protocols" "${H[@]}" -d "$BODY")
echo "   POST /api/protocols: HTTP $CODE, $(python3 -c "import json,sys; b=json.load(open(sys.argv[1])); print('kept', b.get('id'), 'version', [v['version'] for v in b.get('versions',[])], 'by', [v.get('by') for v in b.get('versions',[])]) if isinstance(b,dict) and 'id' in b else print(b)" "$TMP/made.json")"
LISTED=$(curl -s --noproxy '*' "$O/api/protocols" "${H[@]}" | python3 -c "import json,sys; print(','.join(p['id'] for p in json.load(sys.stdin)))")
echo "   GET /api/protocols: [$LISTED]"
ROWS=$(psql "$BH_SERVER/$DB" -XAtc "SELECT count(*) FROM openferment.protocols WHERE project_id = '$P'")
echo "   SELECT count(*) FROM openferment.protocols WHERE project_id = '$P': $ROWS"
bh_svc_stop "$PORT"; dropall
echo "== service on $PORT stopped ($( [ -z "$(bh_port_pid "$PORT")" ] && echo nothing listens || echo still listening)); databases bh_r_r1_02_* left: $(left | wc -l)"

echo "EXPECTED: the Departures row \"$WHERE\" gives a reason true of the tree at $C, or names E.12a as the Decisions row of ADR-016 and ADR-016's note do: the readings-alone mode stands beside a project's protocols (ADR-017), which the store keeps since E.12a"
echo "OBSERVED: line $ROW of docs/PROGRESS.md (\"$SECTION\") says \"$SENT\" and names no step after C.7 (matches of E.12a, E.12 or ADR-017 in the row: $ROW_LATER); line ${SAME:-none} of the same table says a project keeps its protocols on the service since E.12a; the store at $C has the table ${TABLE:-none}, POST /api/protocols answered $CODE, GET /api/protocols lists [$LISTED], the table holds $ROWS row(s)"
if [ "$SECTION" = "## Departures from the execution prompt" ] && [ "$ROW_LATER" = 0 ] \
   && [ "$TABLE" = "openferment.protocols" ] && [ "$CODE" = 200 ] && [ "$LISTED" = "PR-PLACEHOLDER" ] && [ "$ROWS" = 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
