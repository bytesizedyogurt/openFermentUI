# H12-10: keep_run's branch for a held row with neither file nor words is untested

**Statement.** No test plants a runs row held `done` with neither its SFF record nor `sffRefused` and keeps the
run again, so two breaks of keep_run's branch for such a row (M21: the second asker's `by`, `at` and scenario
written over the first's; M24: the second computation's diagnostics taken over the row's own) pass
`test_runs.py`, `test_engines.py`, `test_engine_diagnostics.py`, `test_proforma_runs.py` and `test_events.py`.

**Contract.** `core/openferment_core/engine/runs.py:435-437` (keep_run's docstring):

> A held row with neither is written whole again with its first asker's `by`, `at` and scenario.

and `core/openferment_core/engine/runs.py:443-446`:

> kept on a row that is done: a held row's own stand when it has some, so the same request again is the run
> with its first computation's diagnostics.

`docs/api/runs.md:167` says the same of `diagnostics`.

**Command** (from the repository root; about two minutes; exits 0 either way):

    bash bughunt/repro/H12-10/run.sh

In a worktree of 2047f5a of its own, with the repository's venv linked in, it applies `scratch-name.patch` (the
conformance checks' scratch prefix becomes `bh_r_h12_10_conform`, so every database the tests make is a
`bh_r_h12_10_*` one; the one test that asserts the old prefix, `test_sigterm_ends_the_command_...`, is left out
with `-k`). It makes the fresh database `bh_r_h12_10_cfg` for `OPENFERMENT_DATABASE_URL`, and the tests make
their session databases under `bh_r_h12_10_t`. Then:

1. On the head it runs the probe, `test_h12_10_probe.py`, copied into the worktree's `core/tests`. The probe
   plants the row the docstring speaks of (done, `sff` and `sffRefused` both None, kept by `First Person` at
   `2026-11-01T00:00:00Z` for `first-scenario`, with one diagnostic `time taken` 1.0) and keeps the same run again
   as `Second Person` for `second-scenario` with `time taken` 9.0.
2. With `m21.patch` (line 467 becomes `first, when, asked = (who, _now(), scenario_id)`) it runs the five test
   files, then the probe.
3. With `m24.patch` (line 477 becomes `reported = (None if False else`) it runs the five test files, then the
   probe.

It drops every `bh_r_h12_10_*` database and removes the worktree at the end. `run1.log` and `run2.log` hold two
runs, each from fresh databases.

**Expected.** A test plants a done row with neither and keeps the run again, so M21 and M24 each fail a test
among the five files, as each fails the probe.

**Observed** (both runs):

- the probe on the head: 2 passed. The row is written again with `sffRefused` filled in, `by='First Person'`,
  `at='2026-11-01T00:00:00Z'`, `scenarioId='first-scenario'` and diagnostics `[('time taken', 1.0, ...)]`. The
  head keeps the contract.
- M21: the five files give `208 passed, 1 deselected`, exit 0. The probe's by-at-scenario test fails: the row now
  reads `by='Second Person'`, `at` the moment of the second keep, `scenarioId='second-scenario'`.
- M24: the five files give `208 passed, 1 deselected`, exit 0. The probe's diagnostics test fails: the row now
  reads `[('time taken', 9.0, 'placeholder-ms')]`.
- No test in `core/tests` writes a runs row through `runs._put`. Every test that keeps a run twice keeps it
  first with `sffRefused` set: the second keep returns at line 464 (`test_runs.py:318`, `test_engines.py:429`), or
  the caller answers the held row at line 870 before keep_run is called (`test_engine_diagnostics.py:55`). The read of
  the tests and the two survivors agree: no test keeps a run again over a held row with neither.

**Likely cause.** Lines 467 and 477 of `core/openferment_core/engine/runs.py` carry the contract, and no test
plants the row that reaches them. keep_run itself refuses to keep a done row with neither (lines 455-457). Each
caller (`run_engine` at line 551, `run` at line 591, the contract engine's run at line 870) also answers a held
row with a file or words before calling keep_run. So only a row kept by older code reaches the branch, such as
the bodies `test_db.py:271` seeds for migration 0008, and the suite has no such row. A fix is a test in
`test_runs.py` that plants one (as the probe does) and asserts both clauses.

**Severity.** S4. The code keeps the contract today, and the gap is a test that cannot catch a break of it.
