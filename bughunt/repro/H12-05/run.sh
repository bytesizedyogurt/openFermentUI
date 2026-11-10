#!/usr/bin/env bash
# H12-05: core/tests/test_no_seed.py, the test CLAUDE.md:11 and ADR-011 name as what holds "no composition, yield,
# price, titre, strain fact or paper's finding is typed in code or seed" (acceptance A4), passes with a titre, a
# yield, a composition and a price typed into a service module and a yield table by strain exported from src/data/.
# In a worktree of 2047f5a of this run's own (the repository's venv linked in), it runs test_no_seed.py three ways:
#   1. the tree as it is (the baseline);
#   2. a control: src/data/control.ts exports RECORDS, a name the test's own pattern reads (the test should fail);
#   3. the plant: core/openferment_core/typical_values.py and src/data/yields.ts (TYPICAL_YIELDS) typing science,
#      run with test_no_seed.py, test_boundaries.py and test_guidance.py.
# A fresh database of its own (bh_r_h12_05_db) stands in OPENFERMENT_DATABASE_URL, and the tests' own session
# databases are made under the prefix bh_r_h12_05_t; all are dropped, and the worktree removed, at the end.
#   bash bughunt/repro/H12-05/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h12_05_db
TPREFIX=bh_r_h12_05_t
S=$BH_WORK/H12-05; mkdir -p "$S"
WT=$S/wt-$$
T=$(mktemp -d "$S/run.XXXXXX")
cleanup() {
  bh_db_drop "$DB"
  for d in $(psql "$BH_SERVER/postgres" -XAtc "select datname from pg_database where datname like '${TPREFIX}%'" 2>/dev/null); do
    bh_db_drop "$d"; done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$T" "$WT"; rmdir "$S" 2>/dev/null
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || fail "no worktree at 2047f5a"
ln -s "$BH_ROOT/core/.venv" "$WT/core/.venv"
bh_db_fresh "$DB" || fail "bh_db_fresh $DB"
echo "worktree $WT at $(git -C "$WT" rev-parse --short HEAD); database $DB (fresh)"

wtpy() {   # pytest in the worktree, on the worktree's package, keyless, test databases under $TPREFIX
  (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TPREFIX" \
     PYTHONPATH="$WT/core" .venv/bin/python -m pytest "$@" -q -p no:randomly -p no:cacheprovider 2>&1)
}
(cd "$WT/core" && PYTHONPATH="$WT/core" .venv/bin/python -c "import openferment_core; print('the tests import', openferment_core.__file__)")

# 1. Baseline: the tree as it is.
wtpy tests/test_no_seed.py > "$T/base.log"; BASE=$?
echo "1. baseline, test_no_seed.py on the tree as it is: exit $BASE, $(tail -1 "$T/base.log")"

# 2. Control: an export the test's own name pattern reads.
cat > "$WT/src/data/control.ts" <<'TS'
// Control for repro H12-05: a name test_no_seed.py's SEEDED_NAMES reads.
export const RECORDS = [{ id: 'x', value: 1 }];
TS
wtpy tests/test_no_seed.py > "$T/control.log"; CONTROL=$?
echo "2. control, src/data/control.ts exporting RECORDS: exit $CONTROL, $(tail -1 "$T/control.log")"
grep -m1 -o "AssertionError: .*" "$T/control.log" | cut -c1-160 | sed 's/^/   /'
rm -f "$WT/src/data/control.ts"

# 3. The plant: typed science in a service module and in a browser data file.
cat > "$WT/core/openferment_core/typical_values.py" <<'PY'
"""Typical values a run falls back to when a project holds no record (PLANTED by repro H12-05)."""
ETHANOL_TITRE_G_PER_L = 92.0          # a titre: S. cerevisiae CEN.PK113-7D, fed-batch, from a paper's table 2
ETHANOL_YIELD_G_PER_G = 0.48          # a yield
CORN_STOVER_GLUCAN_FRACTION = 0.35    # a composition
ENZYME_PRICE_USD_PER_KG = 4.24        # a price
PY
cat > "$WT/src/data/yields.ts" <<'TS'
// Typical yields by strain (PLANTED by repro H12-05): a paper's findings typed into the browser.
export const TYPICAL_YIELDS = [
  { strain: 's-cerevisiae-cenpk113-7d', product: 'ethanol', gPerG: 0.48, titreGPerL: 92, paper: 'PMC0000000' },
];
TS
echo "3. planted (git status in the worktree, the linked venv left out):"
git -C "$WT" status --short | grep -v ' core/.venv$' | sed 's/^/   /'
grep -nE "^[A-Z_]+ = [0-9.]+" "$WT/core/openferment_core/typical_values.py" | sed 's/^/   typical_values.py:/'
grep -nE "^export const" "$WT/src/data/yields.ts" | sed 's/^/   src\/data\/yields.ts:/'
wtpy tests/test_no_seed.py > "$T/plant.log"; PLANT=$?
echo "   test_no_seed.py with the plant: exit $PLANT, $(tail -1 "$T/plant.log")"
wtpy tests/test_no_seed.py tests/test_boundaries.py tests/test_guidance.py > "$T/plant3.log"; PLANT3=$?
echo "   test_no_seed.py, test_boundaries.py and test_guidance.py with the plant: exit $PLANT3, $(tail -1 "$T/plant3.log")"
TYPED=$(grep -cE "^(ETHANOL_TITRE_G_PER_L|ETHANOL_YIELD_G_PER_G|CORN_STOVER_GLUCAN_FRACTION|ENZYME_PRICE_USD_PER_KG) = " \
        "$WT/core/openferment_core/typical_values.py")
rm -f "$WT/core/openferment_core/typical_values.py" "$WT/src/data/yields.ts"

echo "EXPECTED: test_no_seed.py fails on core/openferment_core/typical_values.py (a titre 92.0 g/L, a yield 0.48 g/g, a glucan fraction 0.35, an enzyme price 4.24 USD/kg) and on src/data/yields.ts exporting TYPICAL_YIELDS by strain, as it fails on the control's RECORDS export (CLAUDE.md:11; ADR-011 'test_no_seed.py holds acceptance A4')"
echo "OBSERVED: baseline exit $BASE ($(tail -1 "$T/base.log")); control exit $CONTROL ($(tail -1 "$T/control.log")); with the $TYPED typed values and the yield table planted, test_no_seed.py exits $PLANT ($(tail -1 "$T/plant.log")), and with test_boundaries.py and test_guidance.py exits $PLANT3 ($(tail -1 "$T/plant3.log"))"
if [ "$BASE" = 0 ] && [ "$CONTROL" != 0 ] && [ "$TYPED" = 4 ] && [ "$PLANT" = 0 ] && [ "$PLANT3" = 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
