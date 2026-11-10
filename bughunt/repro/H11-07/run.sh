#!/usr/bin/env bash
# H11-07: test_host.py's test of the nightly's dump reads nightly.sh as text and looks for the substring
# `backup_database || status=$?`, so a nightly.sh whose dump line is commented out keeps every test green
# while the night makes no dump.
# usage, from the repository root: bash bughunt/repro/H11-07/run.sh
#
# Everything runs in a detached worktree of 2047f5a under $BH_WORK/H11-07/wt. The repository's core/.venv runs
# the worktree's tests through a symbolic link at wt/core/.venv, made for each test run and removed after it.
# The night itself runs on a copy of the worktree's scripts/host/ under $BH_WORK/H11-07/night, with stand-ins:
# brew answering a keg prefix, the keg's pg_dump writing a file and noting its call, and core/.venv/bin/python
# noting each module call and answering 0. No PostgreSQL tool, no network, no key is reached by the night.
# The defect needs no database; bh_r_h11_07_tests is made fresh and named as the tests' server prefix, so any
# session database the tests made would be bh_r_h11_07_tests_<pid>_<hex>, and every bh_r_h11_07_* is dropped.
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h11_07_tests
T=$BH_WORK/H11-07; WT=$T/wt; NIGHT=$T/night; OUT=$T/out
PY=$BH_ROOT/core/.venv/bin/python
TESTS=(tests/test_host.py tests/test_nightly_checks.py::test_the_nightly_job_checks_after_extraction)
DUMP_TESTS=(
  test_the_night_dumps_openferment_with_the_kegs_pg_dump_and_keeps_the_newest_seven
  test_a_failed_dump_keeps_the_kept_dumps_as_they_were
  test_the_nightly_dumps_before_the_nights_work_and_counts_a_failed_dump
)

cleanup() {
  [ -L "$WT/core/.venv" ] && rm -f "$WT/core/.venv"   # the link alone; the repository's venv is never written
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  git -C "$BH_ROOT" worktree prune >/dev/null 2>&1
  rm -rf "$NIGHT" "$OUT"
  local d
  for d in $(psql "$BH_SERVER/postgres" -XAtc "SELECT datname FROM pg_database WHERE datname LIKE 'bh\_r\_h11\_07\_%'" 2>/dev/null); do
    bh_db_drop "$d"
  done
  rmdir "$T" 2>/dev/null
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT"

echo "EXPECTED: test_host.py's docstring says 'the night's dump run[s] against stand-ins' (core/tests/test_host.py:5-7), and"
echo "EXPECTED: test_host.py:347 is named 'the nightly dumps before the night's work and counts a failed dump'; so a"
echo "EXPECTED: nightly.sh whose dump line (nightly.sh:33, 'backup_database || status=\$?') is commented out, which makes"
echo "EXPECTED: no dump, fails at least one test."

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || { echo "OBSERVED: could not add the worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: could not make $DB"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "setup: worktree at $(git -C "$WT" rev-parse --short HEAD); nightly.sh:33 reads: $(sed -n 33p "$WT/scripts/host/nightly.sh")"

# run_tests LABEL: test_host.py and the one other test that reads nightly.sh, on the worktree as it stands.
# Sets $summary (pytest's last line), $failed (the count) and $dump (each dump test's outcome).
run_tests() {
  local log="$OUT/tests-$1.log" t o
  ln -sfn "$BH_ROOT/core/.venv" "$WT/core/.venv"
  (cd "$WT/core" && bh_env OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$DB" "$PY" -m pytest -p no:cacheprovider -q -rA \
     "${TESTS[@]}") > "$log" 2>&1
  rm -f "$WT/core/.venv"
  summary=$(grep -E '^(=+ )?[0-9]+ (passed|failed|error)' "$log" | tail -1 | sed 's/^=* //; s/ =*$//')
  failed=$(grep -oE '[0-9]+ (failed|error)' <<<"$summary" | awk '{s+=$1} END {print s+0}')
  dump=""
  for t in "${DUMP_TESTS[@]}"; do
    o=$(grep -oE "^(PASSED|FAILED|ERROR) tests/test_host.py::$t" "$log" | head -1 | cut -d' ' -f1)
    dump="$dump ${o:-ABSENT}"
  done
  dump="${dump# }"
  echo "OBSERVED: [$1] pytest ${TESTS[*]}: $summary"
  echo "OBSERVED: [$1] the three dump tests (keeps-the-newest-seven, failed-dump-keeps, nightly-dumps-before): $dump"
  grep -E '^FAILED' "$log" | sed "s/^/OBSERVED: [$1]   /"
}

# night LABEL: the worktree's nightly.sh as launchd runs it (/bin/bash, a PATH and HOME alone) on stand-ins.
# Sets $night_exit, $pg_dumps (calls to pg_dump) and $kept (dump files in ~/openferment-backups).
night() {
  rm -rf "$NIGHT"; mkdir -p "$NIGHT/repo/scripts" "$NIGHT/repo/core/.venv/bin" "$NIGHT/bin" "$NIGHT/keg/bin" "$NIGHT/home" "$NIGHT/daemons"
  cp -R "$WT/scripts/host" "$NIGHT/repo/scripts/host"
  local calls="$NIGHT/calls"; : > "$calls"
  printf '#!/bin/bash\necho "brew $*" >> "%s"\n[ "$*" = "--prefix --installed postgresql@17" ] && echo "%s" && exit 0\nexit 1\n' \
    "$calls" "$NIGHT/keg" > "$NIGHT/bin/brew"
  printf '#!/bin/bash\necho "pg_dump $*" >> "%s"\nfor a in "$@"; do case "$a" in --file=*) out="${a#--file=}" ;; esac; done\nprintf dump > "$out"\n' \
    "$calls" > "$NIGHT/keg/bin/pg_dump"
  printf '#!/bin/bash\necho "python $*" >> "%s"\nexit 0\n' "$calls" > "$NIGHT/repo/core/.venv/bin/python"
  chmod 755 "$NIGHT/bin/brew" "$NIGHT/keg/bin/pg_dump" "$NIGHT/repo/core/.venv/bin/python"
  printf 'OPENFERMENT_DATABASE_URL=postgresql://stand-in@127.0.0.1:9779/openferment\nOPENFERMENT_PROJECT=ethanol\n' > "$NIGHT/repo/core/.env"
  env -i PATH="$NIGHT/bin:/usr/bin:/bin" HOME="$NIGHT/home" OPENFERMENT_LAUNCHD_DIR="$NIGHT/daemons" \
    /bin/bash "$NIGHT/repo/scripts/host/nightly.sh" > "$NIGHT/log" 2>&1
  night_exit=$?
  pg_dumps=$(grep -c '^pg_dump ' "$calls")
  kept=$(ls "$NIGHT/home/openferment-backups" 2>/dev/null | grep -c '^openferment-.*\.dump$')
  echo "OBSERVED: [$1] nightly.sh on stand-ins: exit $night_exit; pg_dump calls $pg_dumps; dumps in ~/openferment-backups $kept"
  echo "OBSERVED: [$1]   steps called: $(grep -E '^(pg_dump|python) ' "$calls" | sed -E 's/ --file=[^ ]*//; s/^python -m openferment_core\./python /' | paste -sd ';' -)"
  echo "OBSERVED: [$1]   log: $(grep -E 'dumped into|dump waits|failed|done, exit' "$NIGHT/log" | sed "s#$NIGHT#…#g" | paste -sd ';' -)"
}

# 1. The tree as it is: the tests pass and the night dumps.
run_tests "2047f5a as it is"; base_failed=$failed; base_summary=$summary
night "2047f5a as it is"; base_dumps=$pg_dumps; base_kept=$kept

# 2. Control: the dump line deleted. The substring is gone, so the third dump test should fail.
sed -i '33{/^backup_database || status=\$?$/d}' "$WT/scripts/host/nightly.sh"
echo "setup: control, the line deleted: $(git -C "$WT" diff --numstat -- scripts/host/nightly.sh) (added, removed, file)"
run_tests "control: line 33 deleted"; ctl_failed=$failed; ctl_dump=$dump
git -C "$WT" checkout -q -- scripts/host/nightly.sh

# 3. The mutation: the dump line commented out. The night stops dumping; the substring still stands in the comment.
sed -i '33s/^backup_database || status=\$?$/# backup_database || status=$?/' "$WT/scripts/host/nightly.sh"
echo "setup: mutation, nightly.sh:33 now reads: $(sed -n 33p "$WT/scripts/host/nightly.sh")"
git -C "$WT" diff -U0 -- scripts/host/nightly.sh | grep -E '^[-+][^-+]' | sed 's/^/setup:   diff /'
mutated=$(sed -n 33p "$WT/scripts/host/nightly.sh")
run_tests "mutation: line 33 commented out"; mut_failed=$failed; mut_summary=$summary; mut_dump=$dump
night "mutation: line 33 commented out"; mut_dumps=$pg_dumps; mut_kept=$kept; mut_exit=$night_exit
git -C "$WT" checkout -q -- scripts/host/nightly.sh

echo "OBSERVED: summary: as it is: tests '$base_summary', night pg_dump calls $base_dumps, dumps kept $base_kept;"
echo "OBSERVED: summary: control (deleted): failed $ctl_failed, dump tests $ctl_dump;"
echo "OBSERVED: summary: mutation (commented): tests '$mut_summary', night pg_dump calls $mut_dumps, dumps kept $mut_kept, exit $mut_exit"

if [ "$mutated" = '# backup_database || status=$?' ] && [ "$base_failed" = 0 ] && [ "$base_dumps" = 1 ] && [ "$base_kept" = 1 ] \
   && [ "$ctl_failed" -ge 1 ] && [ "$mut_failed" = 0 ] && [ "$mut_dump" = "PASSED PASSED PASSED" ] && [ "$mut_dumps" = 0 ] && [ "$mut_kept" = 0 ] && [ "$mut_exit" = 0 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
