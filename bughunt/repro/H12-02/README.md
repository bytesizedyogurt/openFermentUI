# H12-02: conformance checks 1, 3, 4, 5 and 8 can be made to hold whatever they read, and no test sees it

**Statement.** Five one-line mutations of `core/openferment_core/engine/conform.py`, each making one check hold
what it should fail (check 1 ignoring that the engine was reached, check 3 ignoring the row count, check 4
ignoring the replay, check 5 ignoring an SFF file that does not validate, check 8 ignoring the row's
`created_by`), each pass every suite test that reaches the mutated function, while a probe shows each mutated
check holding an engine or a service that breaks it.

## The contract it breaks

- `docs/api/engines.md:478-480`: "An engine that reports the time its computation took answers it as a diagnostic:
  an output that moves between two runs of one request, a clock reading among them, makes the replay differ and
  fails conformance check 4, and `pnpm prove` with it wherever the engine is installed."
- `core/openferment_core/engine/conform.py:67-78`, `CHECKS`: 1 "a JSON number outside a quantity is refused in
  words before the worker is reached"; 3 "a run writes one runs row keyed by its basis, and the same request twice
  is that one row"; 4 "a replay holds every output within the precision the thing states"; 5 "the run's SFF file
  validates and scores, or sffRefused holds words"; 8 "created_by on every run is the person or the model that
  asked for it".
- `CLAUDE.md:80`: every engine "each held by `conform`"; `docs/api/engines.md:799-801`: the command "exits 1 when
  any check fails ... `pnpm prove` runs it for every engine registered".
- `docs/decisions/ADR-011-guards.md:24-25` (the candidate's third citation) is a revisit condition: a retired guard
  "returns with a test that fails on the thing it guards (negative-tested, as before)". It states the project's
  convention for a guard; the binding words for these checks are the two above.

## Command

```
bash bughunt/repro/H12-02/run.sh
```

It makes a scratch worktree of `2047f5a` under `$BH_WORK/H12-02/` (conform's scratch prefix renamed to
`bh_r_h12_02_cf`, so every database made is `bh_r_h12_02_*`), a fresh configured database `bh_r_h12_02_cfg`
(the tests make and drop their own `bh_r_h12_02_t_*`), and runs keyless:

1. the six test files that read conform's checks (`test_engines`, `test_engine_diagnostics`, `test_measurements`,
   `test_train`, `test_pureos_build_tool`, `test_finite_inputs`) on the tree as it is, with a plugin
   (`h12_02_reached.py`) recording which tests reach each check function; then the five probes
   (`test_zz_h12_02_probe.py`) on the tree as it is;
2. each mutation in turn (`mutate.py`; the candidate's M50 to M54, and a control C2 of check 2), with the suite
   tests that reach the mutated function and that check's probe;
3. a read of `test_engines_sim.py` (marker `sim`, not run): its two conformance tests assert only that every
   check holds.

The worktree is removed and every `bh_r_h12_02_*` database dropped at the end. `run1.log` and `run2.log` hold the
two runs.

## The probes

Each is an engine or a service that breaks one check, on the sample engine the suite uses:

| check | mutation (conform.py line) | the break the probe shows the check |
|---|---|---|
| 1 | M52 (193): drops `not calls` | a tool door that asks the engine to compute before it refuses the stray number |
| 3 | M51 (452): drops `rows == 1` | a service that answers the run and keeps no `runs` row for it (`runs._put` stood in) |
| 4 | M50 (486): `four = (True, ...)` | a worker whose run answers a clock reading among its outputs (engines.md:479) |
| 5 | M53 (491): drops `run.sff.valid` | a worker whose `sff_export` writes a file the toolkit finds invalid, kept with its findings and a score (`sff.keep_run_file`) |
| 8 | M54 (504): drops `who == by` | a runs row whose `created_by` names someone other than the asker |

## Expected

Under each mutation some test that reaches the mutated function fails, as `core/tests/test_engines.py:571`
(`test_a_check_that_fails_says_which_and_why`) does for check 2 and `test_engines.py:955-1163` do for check 7.

## Observed (both runs)

- Unmutated: 365 passed, 0 failed over the six files; 5 of 5 probes pass (each check fails its break).
- M52 check 1: 15 suite tests reach `_bare_number`, 15 pass; the probe fails: "the route answered 422 and 422 ...
  the tool refused; the engine was reached; 0 run kept" and the check holds.
- M51 check 3: 18 reach `_run_twice`, 18 pass; the probe fails: "run e067248c61c709e3 of placeholder, asked twice,
  is 0 rows; engine sample, status done" and the check holds.
- M50 check 4: 15 reach `_replayed`, 15 pass; the probe fails: "outside the precision (rtol 0, atol 0);
  1 difference" and the check holds.
- M53 check 5: 15 reach `_replayed`, 15 pass; the probe fails: "record run-e067248c61c709e3: not valid,
  score 0.5" and the check holds.
- M54 check 8: 15 reach `_asked_by`, 15 pass; the probe fails: "created_by 'someone else', its by
  'conformance test', asked by 'conformance test'" and the check holds.
- Control C2 (check 2 holding whatever the origins are): 2 of 19 suite tests reaching `_origins` fail, among them
  `test_a_check_that_fails_says_which_and_why`; the selection does catch a mutation the suite has a test for.

`RESULT: DEFECT` in both runs.

## Likely cause

The suite reads these five checks only on engines that conform: `core/tests/test_engines.py:489-491`, `513-514`,
`1000-1002`, `1724-1726`, `2044-2046`, `core/tests/test_engine_diagnostics.py:178-179` and
`core/tests/test_engines_sim.py:40-42`, `102-104` assert `all(c.ok ...)`. The negative tests that exist cover
check 2 (`test_engines.py:571`), check 3's diagnostics (`test_engine_diagnostics.py:186`), check 6
(`test_engines.py:1205-1290`) and check 7 (`test_engines.py:955-1163`). No test feeds checks 1, 4, 5 or 8, or
check 3's row count, an engine or a service that breaks them. The code under the mutations is
`core/openferment_core/engine/conform.py:193, 452, 486, 491, 504`. The probes in `test_zz_h12_02_probe.py` are
the missing negative tests in draft.

## Notes on the candidate's claim

- M51 is described as "check 3 ignoring a second row". `(project_id, id)` is the `runs` table's key
  (`core/openferment_core/db/models.py:72-80`), so a second row of one id cannot exist, and two rows of two ids
  already fail `a.id == b.id`. The clause `rows == 1` is false only at zero rows: a run answered and kept by no row.
  The probe shows that case; the survivor stands with that reading.
- Checks 4 and 5 can be broken by any contract engine a stranger writes (a moving output; an invalid SFF file).
  Checks 1, 3 and 8 are broken by a regression in the service's own doors or rows, or by a hand-written engine
  that keeps its own row (`core/openferment_core/engine/runs.py:910-922`); for a contract engine the service writes
  `created_by` and the body's `by` from one value (`runs.py:463-490`).
- The hunt's 296 tests over five files become 365 here with `test_finite_inputs.py` added; its one conform test
  refuses an inputs file before any check runs.
