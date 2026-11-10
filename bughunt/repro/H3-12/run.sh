#!/usr/bin/env bash
# H3-12: anchor_candidate drops a carbonSource that holds a number or stands outside the cited section, and keeps
# a candidate's method and organism as the extractor wrote them, numbers and all.
#   bash bughunt/repro/H3-12/run.sh        (from the repository root; exits 0 either way)
# A fresh test database (bh_r_h3_12_anchor, migrated to head, named to the service and the tests); repro.py with the
# repository's Python on the candidate's own inputs (a pure function: no service, no key, no model call, no
# network); the contract lines as the tree writes them; the tree's own tests of the organism and carbon-source
# rules (pure, no database touched); a check that nothing under core/, src/, scripts/ or examples/ was written.
# The database, and any the tests made (bh_r_h3_12_t_*), are dropped on exit.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h3_12_anchor
HERE=/home/user/openFermentUI/bughunt/repro/H3-12
SCRATCH="$BH_WORK/H3-12"
mkdir -p "$SCRATCH"
STAMP="$SCRATCH/stamp.$$"
cleanup() {
  bh_db_drop "$DB"
  for d in $(psql "$BH_SERVER/postgres" -qXAt -c "SELECT datname FROM pg_database WHERE datname LIKE 'bh_r_h3_12_t%'" 2>/dev/null); do
    bh_db_drop "$d"
  done
  rm -f "$STAMP"
  rmdir "$SCRATCH" 2>/dev/null || true
}
trap cleanup EXIT

bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT (the database could not be made)"; exit 0; }
echo "database: $DB (fresh, migrated to head); tree at $(git -C "$BH_ROOT" rev-parse --short HEAD), core/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core && echo yes || echo no)"
export OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB"
export OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_r_h3_12_t"
touch "$STAMP"

echo
echo "== the contract lines, as written =="
grep -n "A record's value stands inside the verbatim quote" "$BH_ROOT/CLAUDE.md"
sed -n '962,970p' "$BH_ROOT/core/openferment_core/models.py" | nl -ba -v962 -w4 -s': '
grep -n '^FIELD_DROP_REASONS = ' "$BH_ROOT/core/openferment_core/validate.py"
sed -n '1055,1058p' "$BH_ROOT/core/openferment_core/validate.py" | nl -ba -v1055 -w4 -s': '
sed -n '1152,1157p' "$BH_ROOT/core/openferment_core/validate.py" | nl -ba -v1152 -w4 -s': '
sed -n '1164,1170p' "$BH_ROOT/core/openferment_core/validate.py" | nl -ba -v1164 -w4 -s': '
sed -n '107,109p' "$BH_ROOT/core/openferment_core/extract.py" | nl -ba -v107 -w4 -s': '
sed -n '200,202p' "$BH_ROOT/core/tests/test_validate.py" | nl -ba -v200 -w4 -s': '

echo
OUT=$(bh_py "$HERE/repro.py" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|PYRESULT)'

echo
echo "== the tree's own tests of the organism and carbon-source rules (pure functions) =="
T=$( (cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$OPENFERMENT_DATABASE_URL" \
       OPENFERMENT_TEST_DATABASE_URL="$OPENFERMENT_TEST_DATABASE_URL" PYTHONDONTWRITEBYTECODE=1 \
       .venv/bin/python -m pytest -q -p no:cacheprovider \
       "tests/test_validate.py::test_wording_that_names_the_species_alone_stays_as_written" \
       "tests/test_validate.py::test_wording_that_names_two_strains_is_not_resolved_to_either" \
       "tests/test_validate.py::test_a_carbon_source_that_fails_is_dropped_and_its_candidate_kept" 2>&1) )
echo "$T" | tail -3
TESTS_PASS=no; echo "$T" | grep -qE '^[0-9]+ passed' && ! echo "$T" | grep -qE 'failed|error' && TESTS_PASS=yes
echo "the tests pin organism wording kept as written (CD34 stands outside the section) and the carbon-source drop: $TESTS_PASS"

echo
WROTE=$(find "$BH_ROOT/core" "$BH_ROOT/src" "$BH_ROOT/scripts" "$BH_ROOT/examples" -newer "$STAMP" \
          -not -path '*/.venv/*' -not -path '*/node_modules/*' -print 2>/dev/null | head -5)
echo "files written under core/, src/, scripts/, examples/ during the run: ${WROTE:-none}"

echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED)'
if echo "$OUT" | grep -q '^PYRESULT: DEFECT$'; then
  echo "RESULT: DEFECT"
elif echo "$OUT" | grep -q '^PYRESULT: NO-DEFECT' && [ "$TESTS_PASS" = yes ]; then
  echo "RESULT: NO-DEFECT"
elif echo "$OUT" | grep -q '^PYRESULT: NO-DEFECT'; then
  echo "RESULT: NO-DEFECT (the tree's own tests did not pass as run; see the lines above)"
else
  echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
fi
exit 0
