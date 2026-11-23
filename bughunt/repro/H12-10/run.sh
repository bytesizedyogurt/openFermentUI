#!/usr/bin/env bash
# H12-10: no test reaches keep_run's branch for a held row that is done with neither its SFF record nor its
# words. engine/runs.py:435-446 holds that such a row "is written whole again with its first asker's `by`, `at`
# and scenario", and that "a held row's own [diagnostics] stand when it has some, so the same request again is the
# run with its first computation's diagnostics" (lines 467 and 477 carry it out). In a worktree of 2047f5a of this
# run's own (the repository's venv linked in, the conformance checks' scratch prefix renamed to bh_r_h12_10_conform
# so every database made is a bh_r_h12_10_* one, and the one test that asserts the old prefix left out) it runs:
#   1. the probe (test_h12_10_probe.py: it plants such a row and keeps the run again as a second asker) on the head;
#   2. M21 (line 467 takes the second asker's by, at and scenario): the five test files the hunt named, then the probe;
#   3. M24 (line 477 takes the second computation's diagnostics): the five test files, then the probe.
# OPENFERMENT_DATABASE_URL names a fresh database of this run's own (bh_r_h12_10_cfg), the tests' session databases
# are made under the prefix bh_r_h12_10_t; all are dropped, and the worktree removed, at the end.
#   bash bughunt/repro/H12-10/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
R=$BH_ROOT/bughunt/repro/H12-10
CFG=bh_r_h12_10_cfg
TPREFIX=bh_r_h12_10_t
S=$BH_WORK/H12-10; mkdir -p "$S"
WT=$S/wt-$$
T=$(mktemp -d "$S/run.XXXXXX")
FILES=(tests/test_runs.py tests/test_engines.py tests/test_engine_diagnostics.py tests/test_proforma_runs.py tests/test_events.py)
cleanup() {
  for d in $(psql "$BH_SERVER/postgres" -XAtc "select datname from pg_database where datname like 'bh\_r\_h12\_10\_%'" 2>/dev/null); do
    bh_db_drop "$d"; done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$T" "$WT"; rmdir "$S" 2>/dev/null
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || fail "no worktree at 2047f5a"
ln -s "$BH_ROOT/core/.venv" "$WT/core/.venv"
# The fixtures the export scripts write (gitignored), as the hunt's survivor.sh copies them.
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/"
(cd "$WT" && git apply "$R/scratch-name.patch") || fail "scratch-name.patch does not apply"
cp "$R/test_h12_10_probe.py" "$WT/core/tests/"
bh_db_fresh "$CFG" || fail "bh_db_fresh $CFG"
echo "worktree $WT at $(git -C "$WT" rev-parse --short HEAD); a fresh database $CFG"

wtpy() {   # the worktree's package, keyless
  (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$CFG" OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TPREFIX" \
     PYTHONPATH="$WT/core" timeout 900 .venv/bin/python "$@" 2>&1)
}
wttest() { wtpy -m pytest "$@" -q -p no:randomly -p no:cacheprovider -m "not live and not sim and not slow and not lit"; }
summary() { grep -E '[0-9]+ (passed|failed)' "$1" | tail -1 | sed 's/=//g; s/^ *//; s/ *$//'; }
WHERE=$(wtpy -c 'import openferment_core.engine.runs as r; print(r.__file__)')
case "$WHERE" in "$WT"/*) ;; *) fail "the package resolves outside the worktree: $WHERE";; esac

echo "contract, core/openferment_core/engine/runs.py:433-446:"
sed -n 433,446p "$WT/core/openferment_core/engine/runs.py" | sed 's/^/  | /'
echo "line 464: $(sed -n 464p "$WT/core/openferment_core/engine/runs.py" | sed 's/^ *//')"
echo "line 467: $(sed -n 467p "$WT/core/openferment_core/engine/runs.py" | sed 's/^ *//')"
echo "line 477: $(sed -n 477p "$WT/core/openferment_core/engine/runs.py" | sed 's/^ *//')"
echo "tests in core/tests that write a runs row through runs._put: $(grep -l 'runs\._put\|_put(' "$WT"/core/tests/test_*.py | grep -vc h12_10)"

probe() {  # probe LABEL: the probe on the worktree as it stands
  wttest -s tests/test_h12_10_probe.py > "$T/probe-$1.log"; local rc=$?
  grep '^PROBE ' "$T/probe-$1.log" | sed "s/^PROBE /  $1 probe: /"
  grep '^FAILED' "$T/probe-$1.log" | sed 's/ - .*//; s/^/  '"$1"' probe /'
  echo "  $1 probe: exit $rc; $(summary "$T/probe-$1.log")"
  return $rc
}
mutant() {  # mutant LABEL PATCH: the five files and then the probe on the tree with PATCH applied
  (cd "$WT" && git apply "$R/$2") || fail "$2 does not apply"
  echo "$1 applied, line $3 now: $(sed -n "$3"p "$WT/core/openferment_core/engine/runs.py" | sed 's/^ *//')"
  wttest "${FILES[@]}" -k "not sigterm_ends_the_command" > "$T/files-$1.log"; local rc=$?
  echo "  $1 five files: exit $rc; $(summary "$T/files-$1.log")"
  grep '^FAILED\|^ERROR' "$T/files-$1.log" | sed 's/ - .*//; s/^/  '"$1"' /'
  eval "FILES_$1=$rc"
  probe "$1"; eval "PROBE_$1=$?"
  (cd "$WT" && git apply -R "$R/$2") || fail "$2 does not reverse"
}

echo "1. the head"
probe head; PROBE_head=$?
[ -s "$T/probe-head.log" ] && grep -q 'PROBE ' "$T/probe-head.log" || { tail -20 "$T/probe-head.log"; fail "the probe did not run on the head"; }
echo "2. M21"
mutant M21 m21.patch 467
echo "3. M24"
mutant M24 m24.patch 477
M21_PROBE_FAIL=$(grep -c '^FAILED.*first_askers_by_at_and_scenario' "$T/probe-M21.log")
M24_PROBE_FAIL=$(grep -c '^FAILED.*keeps_its_own_diagnostics' "$T/probe-M24.log")

echo "EXPECTED: a test plants a done runs row with neither sff nor sffRefused and keeps the run again, so M21 (the second asker's by, at and scenario written over the first's) and M24 (the second computation's diagnostics over the row's own) each fail a test among test_runs, test_engines, test_engine_diagnostics, test_proforma_runs and test_events, as each fails the probe"
echo "OBSERVED: the probe on the head: exit $PROBE_head ($(summary "$T/probe-head.log")); M21: the five files exit $FILES_M21 ($(summary "$T/files-M21.log")), the probe exit $PROBE_M21 ($(summary "$T/probe-M21.log"); $(sed -n 's/^PROBE by-at-scenario //p' "$T/probe-M21.log")); M24: the five files exit $FILES_M24 ($(summary "$T/files-M24.log")), the probe exit $PROBE_M24 ($(summary "$T/probe-M24.log"); $(sed -n 's/^PROBE diagnostics //p' "$T/probe-M24.log"))"
if [ "$PROBE_head" = 0 ] && [ "$FILES_M21" = 0 ] && [ "$FILES_M24" = 0 ] && [ "$M21_PROBE_FAIL" = 1 ] && [ "$M24_PROBE_FAIL" = 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
