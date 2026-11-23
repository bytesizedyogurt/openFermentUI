#!/usr/bin/env bash
# H12-04: the guard's check that a forwarded host is one the service answers to
# (core/openferment_core/guard.py:133, `answers_to(hostname(forwarded))`) can go, a rebinding page reached through a
# proxy that rewrites Host then changes things, and every test that holds the guard stays green.
# In a worktree of 2047f5a of this run's own (the repository's venv linked in, the worktree's core first on the path):
#   1. head: probe.py over a fresh database (a POST /api/projects with Host 127.0.0.1:8000, Origin
#      http://rebind.evil.example.com and X-Forwarded-Host rebind.evil.example.com, then a plain read of the
#      projects), then test_request_guard, test_key_override and test_projects;
#   2. the mutation: `answers_to(hostname(forwarded)) and ` deleted from guard.refusal (one line), then the probe over
#      a database made fresh again, and the same three test files.
# The probe's database is bh_r_h12_04_db and the tests' session databases take the prefix bh_r_h12_04_t; all are
# dropped, and the worktree removed, at the end. Keyless, no service, no port, no network, no model call.
#   bash bughunt/repro/H12-04/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
HERE=$BH_ROOT/bughunt/repro/H12-04
DB=bh_r_h12_04_db
TPREFIX=bh_r_h12_04_t
TESTS=(tests/test_request_guard.py tests/test_key_override.py tests/test_projects.py)
S=$BH_WORK/H12-04; mkdir -p "$S"
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
     timeout 300 .venv/bin/python "$HERE/probe.py" rebound-write 2>&1 | grep '^PROBE')
}
wtpy() {    # pytest in the worktree, on the worktree's package, keyless, test databases under $TPREFIX
  (cd "$WT/core" && bh_env OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TPREFIX" PYTHONPATH="$WT/core" \
     timeout 600 .venv/bin/python -m pytest "$@" -q -p no:randomly -p no:cacheprovider \
     -m "not live and not sim and not slow and not lit" 2>&1)
}
field() { sed -n "s/^PROBE $2=\([^ ]*\).*/\1/p" "$1" | tail -1; }

echo "the check at the head (core/openferment_core/guard.py, refusal):"
grep -n 'answers_to(hostname(forwarded))' "$WT/core/openferment_core/guard.py" | sed 's/^/   guard.py:/'
echo "the tests' only cases with X-Forwarded-Host (core/tests/test_request_guard.py):"
grep -n 'x-forwarded-host' "$WT/core/tests/test_request_guard.py" | sed 's/^/   test_request_guard.py:/'

# 1. Head.
probe > "$T/probe-head.log" || fail "the probe at the head did not run: $(tail -3 "$T/probe-head.log")"
echo "1. head, probe over a fresh $DB:"; sed 's/^/   /' "$T/probe-head.log"
HEAD_STATUS=$(field "$T/probe-head.log" status); HEAD_MADE=$(field "$T/probe-head.log" made)
wtpy "${TESTS[@]}" > "$T/tests-head.log"; HEAD_RC=$?
echo "   test_request_guard, test_key_override, test_projects: exit $HEAD_RC, $(tail -1 "$T/tests-head.log")"

# 2. The mutation: the forwarded host no longer held to a name the service answers to (one line).
(cd "$WT" && git apply) <<'PATCH' || fail "the mutation does not apply"
--- a/core/openferment_core/guard.py
+++ b/core/openferment_core/guard.py
@@ -130,7 +130,7 @@
     # preflight, and this service approves none.
     forwarded = headers.get("x-forwarded-host")
     if same_site(origin, headers.get("host")) or (
-        forwarded and answers_to(hostname(forwarded)) and same_site(origin, forwarded)
+        forwarded and same_site(origin, forwarded)
     ):
         return None
     return f"a page on {origin or 'an unnamed origin'!r} may not change anything here"
PATCH
echo "2. mutation applied: $(git -C "$WT" diff --stat -- core/openferment_core/guard.py | tail -1)"
git -C "$WT" diff -U0 -- core/openferment_core/guard.py | grep -E '^[-+][^-+]' | sed 's/^/   /'
probe > "$T/probe-mut.log" || fail "the probe with the mutation did not run: $(tail -3 "$T/probe-mut.log")"
echo "   probe over $DB made fresh again:"; sed 's/^/   /' "$T/probe-mut.log"
MUT_STATUS=$(field "$T/probe-mut.log" status); MUT_MADE=$(field "$T/probe-mut.log" made)
wtpy "${TESTS[@]}" > "$T/tests-mut.log"; MUT_RC=$?
echo "   test_request_guard, test_key_override, test_projects: exit $MUT_RC, $(tail -1 "$T/tests-mut.log")"
grep -E "^(FAILED|ERROR) " "$T/tests-mut.log" | head -5 | sed 's/^/   /'

echo "EXPECTED: with answers_to(hostname(forwarded)) gone from guard.refusal, a test fails: the guard is the access control (CLAUDE.md:52 'the loopback bind and core/openferment_core/guard.py are the access control until accounts exist'), it exists for DNS rebinding (guard.py:10-12 'A hostile name is made to resolve to the Mini ... The request then names that hostile domain in Host'), and a proxy that rewrites Host carries that name in X-Forwarded-Host (guard.py:124-125), so a POST with Host 127.0.0.1:8000, Origin http://rebind.evil.example.com and X-Forwarded-Host rebind.evil.example.com is answered 403 and a test holds it there"
echo "OBSERVED: head: the probe's POST /api/projects answered ${HEAD_STATUS:-?} (project made: ${HEAD_MADE:-?}) and the three test files exit $HEAD_RC ($(tail -1 "$T/tests-head.log")); with the check deleted: the same POST answered ${MUT_STATUS:-?} (project made: ${MUT_MADE:-?}), and the three test files exit $MUT_RC ($(tail -1 "$T/tests-mut.log"))"
if [ "$HEAD_STATUS" = 403 ] && [ "$HEAD_MADE" = no ] && [ "$MUT_STATUS" != 403 ] && [ "$MUT_MADE" = yes ] \
   && [ "$HEAD_RC" = 0 ] && [ "$MUT_RC" = 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
