# H1-01: identical runs asked at once keep one row whose `by` and `created_by` name different askers

**Statement.** When the same engine run request arrives from several askers at the same moment, every
ask passes the held-row check and computes, and the one `runs` row keeps the first insert's
`created_by` column beside the last writer's body `by`, so the row names two askers and the service
serves the one the column does not hold.

**Contract.** `docs/api/engines.md:541-544`:

> The same request twice is one row, answered as it was first kept: its `by` and `created_by` are
> the first asker's, whoever asks again. `created_by` is the `runs` table's column for the asker,
> the request's person or model, served on every run as `EngineRun.by`, and check 8 reads both

**Command** (from the repository root):

    bash bughunt/repro/H1-01/run.sh

It starts the head's own service on 127.0.0.1:9610 over a fresh database `bh_r_h1_01_svc`
(keyless, no model call), makes the project `h101`, writes conform's kinetics placeholder inputs,
runs one plain kinetics run to warm the worker, then for five values of `mu_max` sends four
identical `POST /api/engines/kinetics/run` requests (`batch_v1`) behind a thread barrier, each with
its own `by` (`asker-0` to `asker-3`). For each value it prints what each asker was answered, the
row's `created_by` column beside its body `by` (psql), what `GET /api/runs/{id}` serves, and how
many `job.running` events the project's event stream holds for the run. It stops the service and
drops the database at the end.

**Expected.** One row a value whose `created_by` column and body `by` name the same asker, served
as that name by `GET /api/runs/{id}`, every asker answered with that name, and one computation.

**Observed** (run1.log, run2.log). One row id a value, as the contract says, but on most values the
row's names disagree: for example `created_by 'asker-3', body by 'asker-1'`, with
`GET /api/runs/{id}` serving `asker-1`, so the column check 8 reads and the `EngineRun.by` the page
shows name different people. Every value shows four `job.running` events for its one run id: each
of the four asks passed the held check and ran the job. On some values the askers are answered
with different names for the one row (`asker-0` told `asker-0`, `asker-1` told `asker-1`).

**Likely cause.**

- `core/openferment_core/engine/runs.py:463-467` and `:484` (`keep_run`): the held row is read
  with `_get`, `first` is taken from it or from this asker when none is held, and the row is
  written with `_put`, which calls `rows.put`.
- `core/openferment_core/db/rows.py:49-66` (`rows.put`): an `INSERT ... ON CONFLICT DO UPDATE`
  that keeps the first insert's `created_by` and replaces the body, so of several writers that
  each read no held row, the column keeps the first and the body the last. `rows.put_first`
  (`rows.py:69`), an insert-once write, sits beside it unused here.
- The check-then-compute window: `runs.py:546-559` (`compute_kept`, the kinetics path through
  `fermos_engine.py:303` and `:347`) and `runs.py:867-874` (`run_engine`, contract engines such
  as mirror). Nothing holds a lock between the read of the held row and the write.
- The kinetics askers' answers come from `run_with` re-reading the row (`report(kept.id)`,
  `runs.py:918-921`), so they mostly name the last body writer; a contract engine answers
  `keep_run`'s own report, so each asker can be told its own name.
