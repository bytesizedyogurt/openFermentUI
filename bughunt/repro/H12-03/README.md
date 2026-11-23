# H12-03: spend's check-and-hold lock can go, the cap is overrun, and every test stays green

**Statement.** With the day's advisory lock deleted from `spend._reserve` (`core/openferment_core/spend.py:156`), two reservations at once each see room that only one of them has, and a $1.00 cap holds $1.20 in 20 of 20 rounds; `test_spend.py`, `test_phase3_review.py` (its race test "R5c" among them), `test_llm.py` and `test_ready.py` all pass, 175 of 175.

## Contract

- `core/openferment_core/spend.py:175-177`, `reserve`'s docstring: "Check and hold are one step under the day's lock, so two calls at once cannot each see room that only one of them has (§3.R)."
- `core/openferment_core/spend.py:7-9`, the module docstring: "The cap is the machine's, across every project and process (the nightly job is a second process), so the check and the hold run under one advisory lock on the day."
- `CLAUDE.md:140`, a stop condition: "R: Spend above the daily cap." and `CLAUDE.md:48`: "Every model call goes through `core/openferment_core/llm.py` ... under the day's cap `OPENFERMENT_DAILY_BUDGET_USD`".
- The test that says it holds the race, `core/tests/test_phase3_review.py:1-2`: "What the review of Phase 3 found (OF-BLD-014 §3.R). Each test failed before its fix." and `:96`: "R5c — check and charge are one step: concurrent calls cannot each pass."

## Command

From the repository root:

```
bash bughunt/repro/H12-03/run.sh
```

It makes a worktree of `2047f5a` under `bh/work/H12-03/`, links the repository's venv, puts the worktree's `core/` first on the path, and runs two passes:

1. head: `probe.py` over a fresh database `bh_r_h12_03_db` (each round, two threads behind a barrier ask `spend.reserve("plan", 0.60)` against a $1.00 cap, each on a connection of its own; a round where both are held is an overrun; 20 rounds), then `tests/test_spend.py`, `tests/test_phase3_review.py`, `tests/test_llm.py` and `tests/test_ready.py`, their session databases under the prefix `bh_r_h12_03_t`;
2. the mutation: the one line `await db.lock(s, "spend", day.isoformat())` deleted from `_reserve`, then the probe over `bh_r_h12_03_db` made fresh again, and the same four test files.

It drops every database it made and removes the worktree. Keyless, no service, no network, no model call.

## Expected

With the lock gone, the probe overruns the cap, and a test fails: `test_concurrent_reservations_cannot_together_pass_the_cap` (`core/tests/test_phase3_review.py:97-117`) first, since ten threads there each ask for $0.30 against $1.00 and it asserts three are granted.

## Observed (run1.log, run2.log)

| | probe: rounds with both held, of 20 | most held at once | the four test files | the R5c race test |
|---|---|---|---|---|
| head, run 1 | 0 | $0.60 | 175 passed | PASSED |
| lock deleted, run 1 | 20 | $1.20 | 175 passed | PASSED |
| head, run 2 | 0 | $0.60 | 175 passed | PASSED |
| lock deleted, run 2 | 20 | $1.20 | 175 passed | PASSED |

The probe sees the race on real connections (two earlier trial runs of the same mutation gave 19 and 18 of 20), and the tests that hold the spend gate pass with the lock and without it. Both runs end `RESULT: DEFECT`.

## Likely cause

Every test runs under the autouse fixture `core/tests/conftest.py:217-236`, which binds every session to one connection (`db.Binding`), and `core/openferment_core/db/session.py:99` (`async with binding.turn:`) makes each session wait on one asyncio lock before it touches that connection; the module says so at `session.py:9-11`: "The tests bind every session to one connection inside an outer transaction (`Binding`) ... and the sessions take turns on the one connection." So the ten threads of `test_phase3_review.py:97-117` reserve one after another whatever `_reserve` does, and the advisory lock at `spend.py:156` decides nothing in any test. `test_spend.py:58` and `:112` reserve one at a time, and `test_spend.py:88` races charges under the same binding. The one path in the tests where spend leaves the binding is `spend._ENGINE` (`spend.py:38-42`, `_session` at `:92-99`), set by `conftest.py:30-50` for live tests alone.

Confidence: high. The lock is present at the head and the probe shows it working (0 overruns), so the service holds its cap today; the defect is a guard on a stop condition that no test would see go.

Fix size: small. A test that points `spend._ENGINE` at an engine of its own on the session's test database (as `conftest.py:47-48` does for live tests), races two or more threads through `spend.reserve` behind a barrier, asserts the cap holds, and deletes the day's committed rows after.
