#!/usr/bin/env bash
# H6-05 (with H10-04, the same drift): ADR-001 and CLAUDE.md say a row's `body` is the Pydantic model kept
# as JSONB; the migrations make every content column of schema openferment PostgreSQL `json`, as
# core/openferment_core/db/models.py's own docstring says it chose.
#   bash bughunt/repro/H6-05/run.sh            (from the repository root)
# Fresh database bh_r_h6_05_types migrated to head (both schemas), its column types read from
# information_schema, the two documents and models.py read with grep; no service, no key, no model call.
set -u
export PGOPTIONS="-c client_min_messages=warning"
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
DB=bh_r_h6_05_types
cleanup() { bh_db_drop "$DB"; }
trap cleanup EXIT

echo "tree: $(git rev-parse --short HEAD); core/ src/ scripts/ examples/ as at 2047f5a: $(git diff --quiet 2047f5a -- core src scripts examples && echo yes || echo NO)"
bh_db_fresh "$DB" || { echo "OBSERVED: the database did not migrate"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "database $DB made from empty and migrated to head: $(psql "$BH_SERVER/$DB" -XAtc "select version_num from openferment.alembic_version" 2>/dev/null || psql "$BH_SERVER/$DB" -XAtc "select string_agg(version_num, ',') from alembic_version")"
echo

Q() { psql "$BH_SERVER/$DB" -XAtc "$1"; }
echo "-- schema openferment: the type of every content column (body, record, selection, settings, input, result)"
Q "select '  ' || data_type || ': ' || count(*) || ' columns (' || string_agg(distinct column_name, ',') || ')'
   from information_schema.columns where table_schema='openferment'
   and column_name in ('body','record','selection','settings','input','result') group by data_type"
BODY_JSON=$(Q "select count(*) from information_schema.columns where table_schema='openferment' and column_name='body' and data_type='json'")
BODY_ALL=$(Q "select count(*) from information_schema.columns where table_schema='openferment' and column_name='body'")
CONTENT_JSON=$(Q "select count(*) from information_schema.columns where table_schema='openferment' and column_name in ('body','record','selection','settings','input','result') and data_type='json'")
JSONB_ANY=$(Q "select count(*) from information_schema.columns where table_schema='openferment' and data_type='jsonb'")
echo "  body columns: $BODY_ALL, of type json: $BODY_JSON; columns of type jsonb anywhere in schema openferment: $JSONB_ANY"
echo
echo "-- what the two types keep (a cast, no table written): models.py names key order as its reason for json"
echo "  '{\"b\":1,\"a\":-0}'::json  -> $(Q "select '{\"b\":1,\"a\":-0}'::json::text")"
echo "  '{\"b\":1,\"a\":-0}'::jsonb -> $(Q "select '{\"b\":1,\"a\":-0}'::jsonb::text")"
echo

echo "-- the documents"
ADR=$(sed -n 62p docs/decisions/ADR-001-postgresql.md); CLM=$(sed -n 66p CLAUDE.md)
echo "  docs/decisions/ADR-001-postgresql.md:62: ${ADR#"${ADR%%[![:space:]]*}"}"
echo "  CLAUDE.md:66: $CLM"
grep -n 'JSONB' docs/PROGRESS.md | cut -c1-170 | sed 's/^/  docs\/PROGRESS.md:/'
L=$(grep -n 'are `json`' docs/PROGRESS.md | cut -d: -f1 | head -1)
[ -n "$L" ] && awk -v a=$((L-1)) -v b="$L" 'NR>=a&&NR<=b{sub(/^ +/,""); print "  docs/PROGRESS.md:" NR ": " $0}' docs/PROGRESS.md
echo "-- the tree"
awk 'NR>=5&&NR<=9{print "  core/openferment_core/db/models.py:" NR ": " $0}' core/openferment_core/db/models.py
grep -n '^from sqlalchemy.dialects.postgresql' core/openferment_core/db/models.py | sed 's/^/  core\/openferment_core\/db\/models.py:/'
grep -n 'Column("body", JSON' core/openferment_core/db/models.py | sed 's/^/  core\/openferment_core\/db\/models.py:/'
echo "  postgresql.JSON columns in the migrations: $(grep -c 'postgresql.JSON(' core/openferment_core/db/alembic/versions/*.py | grep -v ':0$' | sed 's#.*/##' | tr '\n' ' ')"
echo "  postgresql.JSONB columns in the migrations: $(grep -l 'JSONB' core/openferment_core/db/alembic/versions/*.py | wc -l) files"
echo

DOC_JSONB=0
case "$ADR" in *"dumped as JSONB"*) DOC_JSONB=$((DOC_JSONB+1));; esac
case "$CLM" in *'JSONB `body`'*) DOC_JSONB=$((DOC_JSONB+1));; esac
echo "EXPECTED: the content columns a migrated database holds are of the type ADR-001:62 and CLAUDE.md:66 name (JSONB), or the two documents say json as models.py:6-9 does"
echo "OBSERVED: $CONTENT_JSON content columns of type json ($BODY_JSON of $BODY_ALL body columns), $JSONB_ANY of type jsonb; $DOC_JSONB of the 2 documents say JSONB"
if [ "$CONTENT_JSON" -gt 0 ] && [ "$JSONB_ANY" = 0 ] && [ "$DOC_JSONB" -gt 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
