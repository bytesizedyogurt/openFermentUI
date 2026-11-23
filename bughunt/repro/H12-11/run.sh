#!/usr/bin/env bash
# H12-11: ready's literature row reads ok with the kit's schema behind its newest revision, and no test sees it.
# bash bughunt/repro/H12-11/run.sh (from the repository root). Keyless, no model call, no service.
# In a scratch worktree of 2047f5a it
#   1. counts the tests that call ready.check_literature (one, over a database at head);
#   2. makes a fresh database bh_r_h12_11_kit, takes the kit's schema one revision back (0006 -> 0005) and asks
#      check_literature on the tree as it stands, then with mutation M65 (`at != head` dropped from the row);
#   3. runs test_ready.py, test_db.py and test_import_alpha1.py with M65 applied;
#   4. as a control, runs test_ready.py with M64 (the data row's own revision check dropped) applied.
# Every database made is bh_r_h12_11_*; all are dropped and the worktree removed at the end.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
N="$BH_ROOT/bughunt/notes/H12"
BASE="$BH_WORK/H12-11"
WT="$BASE/wt-$$"
DB=bh_r_h12_11_kit
TESTDB=bh_r_h12_11_t
PY="$BH_ROOT/core/.venv/bin/python"
LOG="$BASE/pytest-$$"

cleanup() {
  bh_db_drop "$DB" >/dev/null 2>&1
  for d in $(psql "$BH_SERVER/postgres" -XAtc "SELECT datname FROM pg_database WHERE datname LIKE '${TESTDB}\_%'" 2>/dev/null); do
    bh_db_drop "$d" >/dev/null 2>&1
  done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  rm -rf "$LOG"
}
trap cleanup EXIT

mkdir -p "$BASE" "$LOG"
git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || { echo "worktree add failed"; echo "RESULT: NO-DEFECT"; exit 0; }
# untracked test fixtures the suite reads (as survivor.sh copies them)
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/" 2>/dev/null
echo "== worktree $WT at $(git -C "$WT" rev-parse --short HEAD), diff: $(git -C "$WT" diff --stat | tail -1)"

wt_py() { (cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 "$PY" "$@"); }

# ── 1. the tests that call check_literature ─────────────────────────────
echo "== 1. callers of ready.check_literature under core/tests/"
grep -rn --include='*.py' "check_literature" "$WT/core/tests" | sed "s#$WT/##"
CALLERS=$(grep -rn --include='*.py' "check_literature" "$WT/core/tests" | wc -l)
echo "   the data row's behind-head test, for comparison:"
grep -n "def test_data_reports_a_database_behind_the_newest_schema" "$WT/core/tests/test_ready.py" | sed 's#^#   core/tests/test_ready.py:#'

# ── 2. the row on a kit schema one revision short ───────────────────────
echo "== 2. check_literature on $DB with sci_rag taken back to 0005"
bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT"; exit 0; }
wt_py - "$BH_SERVER/$DB" <<'EOF'
import sys
from alembic import command
from openferment_core import migrations
url = sys.argv[1]
command.downgrade(migrations._kit_config(url), "0005")
print("   revisions (at, head):", migrations.at_head(url))
EOF
ask() {
  (cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" "$PY" - <<'EOF'
import openferment_core.ready as r
c = r.check_literature()
print(f"{c.mark}\t{c.detail}\t{r.__file__}")
EOF
  )
}
IFS=$'\t' read -r MARK0 DETAIL0 FILE0 < <(ask)
echo "   as it stands:  $MARK0 | $DETAIL0"
echo "   (module $FILE0)"
(cd "$WT" && git apply "$N/mutations/M65.patch") || { echo "M65 does not apply"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "   M65 applied:   $(cd "$WT" && git diff -U0 | grep '^[-+] ' | tr -s ' ' | paste -sd' ' -)"
IFS=$'\t' read -r MARK1 DETAIL1 FILE1 < <(ask)
echo "   with M65:      $MARK1 | $DETAIL1"

# ── 3. the three test files with M65 applied ────────────────────────────
echo "== 3. pytest test_ready.py test_db.py test_import_alpha1.py with M65"
(cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TESTDB" \
   "$PY" -m pytest tests/test_ready.py tests/test_db.py tests/test_import_alpha1.py -q -p no:randomly -p no:cacheprovider \
   -m "not live and not sim and not slow and not lit" > "$LOG/m65.txt" 2>&1)
M65_RC=$?
tail -1 "$LOG/m65.txt" | sed 's#^#   #'
(cd "$WT" && git apply -R "$N/mutations/M65.patch")

# ── 4. control: the data row's mutation M64 ─────────────────────────────
echo "== 4. control: pytest test_ready.py with M64 (data row's at != head dropped)"
(cd "$WT" && git apply "$N/mutations/M64.patch") || echo "   M64 does not apply"
(cd "$WT/core" && bh_env PYTHONPATH="$WT/core" HF_HUB_OFFLINE=1 OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TESTDB" \
   "$PY" -m pytest tests/test_ready.py -q -p no:randomly -p no:cacheprovider \
   -m "not live and not sim and not slow and not lit" > "$LOG/m64.txt" 2>&1)
M64_RC=$?
grep -E "^FAILED" "$LOG/m64.txt" | sed 's#^#   #'
tail -1 "$LOG/m64.txt" | sed 's#^#   #'
(cd "$WT" && git apply -R "$N/mutations/M64.patch")

echo
echo "EXPECTED: with sci_rag at 0005 of 0006 the literature row fails (it does: '$MARK0'), and some test holds that,"
echo "          so M65 turns at least one of test_ready/test_db/test_import_alpha1 red, as M64 does for the data row"
echo "OBSERVED: with M65 the row reads '$MARK1' and says '${DETAIL1}' on a schema at 0005;"
echo "          the three files with M65: '$(tail -1 "$LOG/m65.txt")' (exit $M65_RC); $CALLERS test line(s) call check_literature;"
echo "          control M64: '$(tail -1 "$LOG/m64.txt")' (exit $M64_RC)"

if [ "$MARK0" = fail ] && [ "$MARK1" != fail ] && [ -n "$MARK1" ] && [ "$M65_RC" -eq 0 ] \
   && grep -q " passed" "$LOG/m65.txt" && ! grep -qE "[0-9]+ (failed|error)" "$LOG/m65.txt"; then
  [ "$M64_RC" -ne 0 ] && echo "NOTE: the control M64 is caught: test_data_reports_a_database_behind_the_newest_schema holds the data row's revision check"
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
