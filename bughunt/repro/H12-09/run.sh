#!/usr/bin/env bash
# H12-09: no guard test can tell a public .net name from the owner's own names. guard.py:22-26 holds that the
# service answers to "an IP address, a name with no dot, a `.local` name (Bonjour), a `.ts.net` name (Tailscale's
# names for the owner's devices), or one listed in OPENFERMENT_ALLOWED_HOSTS", and that "a rebinding attack needs a
# public domain whose DNS the attacker answers". The hostile Hosts the tests send end in .com, .org and .example, and
# none in .net, so a guard that answers to every .net name (the hunt's M32) goes unseen. In a worktree of 2047f5a of
# this run's own (the repository's venv linked in) it runs:
#   1. a scan, by ast, of every Host a test in core/tests sends that the head's guard refuses;
#   2. the probe on the head: guard.refusal and POST /api/projects under Host and Origin rebind.evil.example.net;
#   3. a control: the same line answers to every .com name (control.patch), and test_request_guard.py should fail;
#   4. the mutation: the line answers to every .net name (mutation.patch, M32), and the candidate's three test files
#      (test_request_guard, test_key_override, test_projects) are run;
#   5. the probe again on the mutated tree.
# A fresh database of its own stands in OPENFERMENT_DATABASE_URL for each probe (bh_r_h12_09_head, bh_r_h12_09_mut),
# the tests' session databases are made under the prefix bh_r_h12_09_t; all are dropped, and the worktree removed,
# at the end.
#   bash bughunt/repro/H12-09/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
R=$BH_ROOT/bughunt/repro/H12-09
TPREFIX=bh_r_h12_09_t
S=$BH_WORK/H12-09; mkdir -p "$S"
WT=$S/wt-$$
T=$(mktemp -d "$S/run.XXXXXX")
cleanup() {
  for d in $(psql "$BH_SERVER/postgres" -XAtc "select datname from pg_database where datname like 'bh\_r\_h12\_09\_%'" 2>/dev/null); do
    bh_db_drop "$d"; done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$T" "$WT"; rmdir "$S" 2>/dev/null
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || fail "no worktree at 2047f5a"
ln -s "$BH_ROOT/core/.venv" "$WT/core/.venv"
# The fixtures the export scripts write (gitignored), as survivor.sh copies them.
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/"
echo "worktree $WT at $(git -C "$WT" rev-parse --short HEAD)"

wtpy() {   # the worktree's package, keyless, on database $1
  local db="$1"; shift
  (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$db" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TPREFIX" \
     PYTHONPATH="$WT/core" timeout 900 .venv/bin/python "$@" 2>&1)
}
wttest() { wtpy "$TPREFIX" -m pytest "$@" -q -p no:randomly -p no:cacheprovider -m "not live and not sim and not slow and not lit"; }
probe() {  # probe LABEL DB STEP: a fresh database, then the probe on the worktree as it stands
  bh_db_fresh "$2" || fail "bh_db_fresh $2"
  wtpy "$2" "$R/probe.py" > "$T/probe-$1.log"
  grep '^PROBE ' "$T/probe-$1.log" | sed "s/^PROBE /$3 $1: /"
}
status_of() { sed -n 's/^PROBE-STATUS //p' "$T/probe-$1.log"; }

echo "contract, core/openferment_core/guard.py:22-26:"
sed -n 22,26p "$WT/core/openferment_core/guard.py" | sed 's/^/  | /'
echo "the line under test, guard.py:78: $(sed -n 78p "$WT/core/openferment_core/guard.py" | sed 's/^ *//')"

# 1. The scan.
wtpy "$TPREFIX" "$R/scan.py" "$WT/core/tests" > "$T/scan.log"
grep '^SCAN ' "$T/scan.log" | sed 's/^SCAN /1. /'
REFUSED_NET=$(sed -n 's/^SCAN-REFUSED-NET \([0-9]*\) .*/\1/p' "$T/scan.log")
[ -n "$REFUSED_NET" ] || { tail -5 "$T/scan.log"; fail "the scan did not run"; }

# 2. The probe on the head.
probe head bh_r_h12_09_head 2.; HEAD_STATUS=$(status_of head)
[ -n "$HEAD_STATUS" ] || { tail -5 "$T/probe-head.log"; fail "the probe did not run on the head"; }

# 3. Control: the same line answers to every .com name.
(cd "$WT" && git apply "$R/control.patch") || fail "control.patch does not apply"
wttest tests/test_request_guard.py > "$T/control.log"; CONTROL=$?
(cd "$WT" && git apply -R "$R/control.patch") || fail "control.patch does not reverse"
echo "3. control (every .com name answered), test_request_guard.py: exit $CONTROL; $(grep -E '[0-9]+ (passed|failed)' "$T/control.log" | tail -1)"
grep '^FAILED' "$T/control.log" | sed 's/ - .*//; s/^/3.   /'

# 4. The mutation: the same line answers to every .net name (M32).
(cd "$WT" && git apply "$R/mutation.patch") || fail "mutation.patch does not apply"
echo "4. mutation applied: $(cd "$WT" && git diff -U0 -- core/openferment_core/guard.py | grep '^+ ' | sed 's/^+ *//')"
wttest tests/test_request_guard.py tests/test_key_override.py tests/test_projects.py > "$T/mutant.log"; MUTANT=$?
echo "4. mutated tree, test_request_guard.py test_key_override.py test_projects.py: exit $MUTANT; $(grep -E '[0-9]+ (passed|failed)' "$T/mutant.log" | tail -1)"
grep '^FAILED' "$T/mutant.log" | sed 's/ - .*//; s/^/4.   /'

# 5. The probe on the mutated tree.
probe mutant bh_r_h12_09_mut 5.; MUT_STATUS=$(status_of mutant)
(cd "$WT" && git apply -R "$R/mutation.patch") || fail "mutation.patch does not reverse"
[ -n "$MUT_STATUS" ] || { tail -5 "$T/probe-mutant.log"; fail "the probe did not run on the mutated tree"; }

echo "EXPECTED: a guard test sends a public name outside .local, .localhost and .ts.net that ends in .net (such as rebind.evil.example.net) and asserts a 403, so a guard that answers to every .net name fails a test, as the control's .com guard does"
echo "OBSERVED: the tests' refused Hosts number $(grep -c '^SCAN refused' "$T/scan.log"), $REFUSED_NET of them .net; the control's .com guard: pytest exit $CONTROL; the .net guard (M32): pytest exit $MUTANT ($(grep -E '[0-9]+ (passed|failed)' "$T/mutant.log" | tail -1)), and under it POST /api/projects with Host and Origin rebind.evil.example.net answered $MUT_STATUS (the head: $HEAD_STATUS)"
if [ "$REFUSED_NET" = 0 ] && [ "$CONTROL" != 0 ] && [ "$MUTANT" = 0 ] && [ "$HEAD_STATUS" = 403 ] && [ "$MUT_STATUS" != 403 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
