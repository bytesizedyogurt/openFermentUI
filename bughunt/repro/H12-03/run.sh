#!/usr/bin/env bash
# H12-03: the day's lock in spend._reserve (core/openferment_core/spend.py:156) can go, two reservations at once then
# each see room only one of them has and the $1.00 cap is overrun, and every test that holds the spend gate stays
# green, the one named for this race (core/tests/test_phase3_review.py:96-117, "R5c") among them.
# In a worktree of 2047f5a of this run's own (the repository's venv linked in, the worktree's core first on the path):
#   1. head: probe.py (two threads behind a barrier reserve $0.60 each against a $1.00 cap, on real connections,
#      20 rounds) over a fresh database, then test_spend, test_phase3_review, test_llm and test_ready;
#   2. the mutation: the one line `await db.lock(s, "spend", day.isoformat())` deleted from _reserve, then the
#      probe over a database made fresh again, and the same four test files.
# The probe's database is bh_r_h12_03_db and the tests' session databases take the prefix bh_r_h12_03_t; all are
# dropped, and the worktree removed, at the end. Keyless, no service, no network, no model call.
#   bash bughunt/repro/H12-03/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
HERE=$BH_ROOT/bughunt/repro/H12-03
DB=bh_r_h12_03_db
TPREFIX=bh_r_h12_03_t
ROUNDS=20
TESTS=(tests/test_spend.py tests/test_phase3_review.py tests/test_llm.py tests/test_ready.py)
RACE_TEST=tests/test_phase3_review.py::test_concurrent_reservations_cannot_together_pass_the_cap
S=$BH_WORK/H12-03; mkdir -p "$S"
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
echo "worktree $WT at $(git -C "$WT" rev-parse --short HEAD)"

probe() {   # the probe over database $DB, made fresh first, on the worktree's package
  bh_db_fresh "$DB" || return 1
  (cd "$WT/core" && bh_env PYTHONPATH="$WT/core" OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
     timeout 600 .venv/bin/python "$HERE/probe.py" "$ROUNDS" 2>&1)
}
wtpy() {    # pytest in the worktree, on the worktree's package, keyless, test databases under $TPREFIX
  (cd "$WT/core" && bh_env OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TPREFIX" PYTHONPATH="$WT/core" \
     timeout 600 .venv/bin/python -m pytest "$@" -q -rA -p no:randomly -p no:cacheprovider \
     -m "not live and not sim and not slow and not lit" 2>&1)
}
overruns() { sed -n 's/.*the cap overrun) in \([0-9]*\);.*/\1/p' "$1" | tail -1; }
race_test() { grep -oE "^(PASSED|FAILED|ERROR) $RACE_TEST" "$1" | head -1 | cut -d' ' -f1; }

echo "the lock at the head (core/openferment_core/spend.py, _reserve and _settle):"
grep -n 'await db.lock(s, "spend", day.isoformat())' "$WT/core/openferment_core/spend.py" | sed 's/^/   spend.py:/'
echo "the test binding (core/openferment_core/db/session.py): every session takes the one connection in turn:"
grep -n 'async with binding.turn' "$WT/core/openferment_core/db/session.py" | sed 's/^/   session.py:/'

# 1. Head.
probe > "$T/probe-head.log" || fail "the probe at the head did not run: $(tail -3 "$T/probe-head.log")"
HEAD_OVER=$(overruns "$T/probe-head.log")
echo "1. head, probe over a fresh $DB:"; sed 's/^/   /' "$T/probe-head.log"
wtpy "${TESTS[@]}" > "$T/tests-head.log"; HEAD_RC=$?
echo "   test_spend, test_phase3_review, test_llm, test_ready: exit $HEAD_RC, $(tail -1 "$T/tests-head.log")"
echo "   $RACE_TEST: $(race_test "$T/tests-head.log")"

# 2. The mutation: the day's lock deleted from _reserve (one line).
(cd "$WT" && git apply) <<'PATCH' || fail "the mutation does not apply"
--- a/core/openferment_core/spend.py
+++ b/core/openferment_core/spend.py
@@ -153,7 +153,6 @@
 async def _reserve(role: str, projected_usd: float, project_id: str | None) -> str:
     day = date.fromisoformat(today())
     async with _session() as s:
-        await db.lock(s, "spend", day.isoformat())
         now = datetime.now(timezone.utc)
         # An abandoned reservation holds nothing; its row goes.
         await s.execute(delete(t.spend).where(t.spend.c.state == "reserved", t.spend.c.expires_at <= now))
PATCH
echo "2. mutation applied: $(git -C "$WT" diff --stat -- core/openferment_core/spend.py | tail -1)"
git -C "$WT" diff -U0 -- core/openferment_core/spend.py | grep '^-[^-]' | sed 's/^/   /'
probe > "$T/probe-mut.log" || fail "the probe with the mutation did not run: $(tail -3 "$T/probe-mut.log")"
MUT_OVER=$(overruns "$T/probe-mut.log")
echo "   probe over $DB made fresh again:"; sed 's/^/   /' "$T/probe-mut.log"
wtpy "${TESTS[@]}" > "$T/tests-mut.log"; MUT_RC=$?
echo "   test_spend, test_phase3_review, test_llm, test_ready: exit $MUT_RC, $(tail -1 "$T/tests-mut.log")"
echo "   $RACE_TEST: $(race_test "$T/tests-mut.log")"
grep -E "^(FAILED|ERROR) " "$T/tests-mut.log" | head -5 | sed 's/^/   /'

echo "EXPECTED: with the day's lock gone from spend._reserve, two reservations at once each see room only one has (spend.py:175-177 'Check and hold are one step under the day's lock, so two calls at once cannot each see room that only one of them has (§3.R)'; CLAUDE.md:140 stop condition 'Spend above the daily cap'), and a test fails, test_phase3_review.py:96-97 'R5c — check and charge are one step: concurrent calls cannot each pass' first"
echo "OBSERVED: head: the probe overran the \$1.00 cap in ${HEAD_OVER:-?} of $ROUNDS rounds and the four test files exit $HEAD_RC ($(tail -1 "$T/tests-head.log")); with the lock deleted: the probe overran it in ${MUT_OVER:-?} of $ROUNDS rounds (two \$0.60 reservations held at once), and the four test files exit $MUT_RC ($(tail -1 "$T/tests-mut.log")), the R5c race test $(race_test "$T/tests-mut.log")"
if [ "${HEAD_OVER:-x}" = 0 ] && [ "${MUT_OVER:-0}" -gt 0 ] 2>/dev/null && [ "$HEAD_RC" = 0 ] && [ "$MUT_RC" = 0 ] \
   && [ "$(race_test "$T/tests-mut.log")" = PASSED ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
