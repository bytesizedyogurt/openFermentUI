# H11-07: the nightly's dump test passes with nightly.sh's dump line commented out

**Statement.** `test_the_nightly_dumps_before_the_nights_work_and_counts_a_failed_dump` reads `scripts/host/nightly.sh`
as text and looks for the substring `backup_database || status=$?`, so a nightly.sh whose dump line reads
`# backup_database || status=$?` keeps it green; the other two dump tests call lib.sh's `backup_database` directly, and
no test fails when the night stops dumping.

**Contract.**

- `core/tests/test_host.py:5-7`, the file's docstring: "lib.sh's reading of core/.env, its database step and the
  night's dump run against stand-ins for Homebrew and the PostgreSQL tools."
- `core/tests/test_host.py:347`, the test's name: `test_the_nightly_dumps_before_the_nights_work_and_counts_a_failed_dump`
  ("the nightly dumps before the night's work and counts a failed dump").
- `docs/PROGRESS.md:3593-3595` records what the three tests hold: "Three tests in `core/tests/test_host.py` on
  stand-ins: the keg's tool called once, seven kept and a file of another name left as it was; a failed dump keeping
  the kept files; the dump ahead of the night's work."

**Command.** From the repository root: `bash bughunt/repro/H11-07/run.sh`. It exits 0 either way, makes its own
detached worktree of 2047f5a under `$BH_WORK/H11-07/wt`, and removes it after. The defect needs no database or
service. The script makes `bh_r_h11_07_tests` fresh and names it as the tests' server prefix, so any session database
the tests made would carry the `bh_r_h11_07_` prefix. At the end it drops every `bh_r_h11_07_*` database.

What it does:

1. On the worktree as it is, runs `tests/test_host.py` plus
   `tests/test_nightly_checks.py::test_the_nightly_job_checks_after_extraction`, the one other test that reads
   nightly.sh. It runs them with the repository's `core/.venv`, linked into the worktree for the run and unlinked
   after. Then it runs the worktree's nightly.sh as launchd does (`/bin/bash`, a PATH and HOME alone) on stand-ins,
   from a copy of `scripts/host/`:
   - `brew` answers a keg prefix;
   - the keg's `pg_dump` notes its call and writes the file;
   - `core/.venv/bin/python` notes each module call and answers 0.
2. Control: deletes line 33 (`backup_database || status=$?`) and runs the same tests.
3. Mutation: comments line 33 out (`# backup_database || status=$?`), runs the same tests, and runs the night again on
   the stand-ins.

**Expected.** Commenting out the dump call in nightly.sh, which leaves the night making no dump, fails at least one
test, as the docstring's "the night's dump run[s] against stand-ins" and the test's name promise.

**Observed** (both runs, `run1.log` and `run2.log`):

- As it is: 53 passed. The night calls the keg's `pg_dump` once, keeps one dump in `~/openferment-backups`, then runs
  extract, nightly_checks, checks propose and checks brief, and exits 0.
- Control, line 33 deleted: 1 failed, 52 passed. The failure is
  `test_the_nightly_dumps_before_the_nights_work_and_counts_a_failed_dump`, so the tests can see the line's absence.
- Mutation, line 33 commented out: 53 passed, and all three dump tests are PASSED. The mutated night makes no
  `pg_dump` call, leaves `~/openferment-backups` without a dump, prints no "dumped into" line, still runs the four
  other steps, and exits 0, so its log reads `done, exit 0`.

**Likely cause.** `core/tests/test_host.py:348-350` asserts on the script's text:

```python
text = (HOST_DIR / "nightly.sh").read_text()
assert "backup_database || status=$?" in text
assert text.index("backup_database ||") < text.index("openferment_core.extract")
```

A comment holds both substrings, and nightly.sh's own comment at line 31 names `backup_database` too. The two other
dump tests (`test_host.py:319` and `:339`) source lib.sh and call `backup_database` themselves (`_lib(tmp_path,
"backup_database", ...)`), so they never run nightly.sh. No test runs nightly.sh on stand-ins and looks for the keg's
`pg_dump` call; that is the check the docstring describes, and `bughunt/notes/H11/scripts/nightly-cases.sh` shows it
can be done on Linux. The fix is small: run nightly.sh on the stand-ins of `_dump_stand_ins` with a stand-in
`core/.venv/bin/python`, then assert the `pg_dump` call comes before the extract call and that a failed dump makes
the exit non-zero.

**Severity.** S4, a hollow test. Today's nightly.sh dumps, as the "as it is" run shows. The test lets a later edit
turn the dump off without a failure, and the owner learns of it only from a missing file in `~/openferment-backups`.
