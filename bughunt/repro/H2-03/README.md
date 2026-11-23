# H2-03: a locked runbook's row keeps a lock moment and digest of its own

**Statement.** After a lock, `PUT /api/state/runbooks/{id}` with the frozen predictions and measures and a
rewritten `lockedAt` and `lockHash` is kept (200, with no audit row), and `GET /api/studies/runbooks/{id}`,
the export package and the runbook's page then answer the row's moment and digest over the ones
`runbook_locks` keeps.

**Contract.**

- `docs/api/studies.md:170-175`: "Locking freezes the predictions and measures under the digest the
  browser's own code writes (...), with the moment: the lock is kept in `runbook_locks` and audited, then
  carried by the row. From then on the store (`project_state.py`) refuses a runbook row whose predictions
  or measures are not the ones frozen, from the page or the service alike; its status and stages still
  move."
- `docs/api/studies.md:184`: "`GET /api/studies/runbooks/{id}` | Any runbook of the project, a lock the row
  does not carry laid on"
- `core/openferment_core/runbook_lock.py:4-6`: "the service computes the same digest here, over the row as
  the project keeps it, so a runbook the service locks reads as intact on the runbook's page"
- `core/openferment_core/project_state.py:596`, the store's own words for a second lock: "a lock is kept as
  it was made"

**Command.** `bash bughunt/repro/H2-03/run.sh` from the repository root (a fresh database
`bh_r_h2_03_lock`, a keyless service on the first free port of 9680 to 9689, everything removed at the end).
It fits one kinetics model, forecasts it, makes a study runbook of the forecast's `values.finals.product`,
locks it, then sends the locked row back through the state door twice with the frozen predictions and
measures untouched:

- A. `lockedAt` 2020-01-01T00:00:00Z and `lockHash` 0000000000000000 (the candidate's case);
- B. `lockedAt` 2020-01-01T00:00:00Z with the frozen `lockHash` kept.

After each it reads the runbook, `GET /api/state`, and the page's verdict from the browser's own
`lockIntact` (`src/engine/lock.ts`, run under Node); at the end the audit rows and the export's `study.md`.

**Expected.** Each write refused in words, since a lock is kept as it was made; or the lock `runbook_locks`
keeps laid over the row's, so the runbook reads as locked at the lock's own moment under its own digest,
intact on its page.

**Observed** (run1.log and run2.log, the same both times):

- A: kept 200. `GET /api/studies/runbooks/{id}` answers `lockedAt` 2020-01-01T00:00:00Z and `lockHash`
  0000000000000000, while `GET /api/state` `runbookLocks` holds the lock's 2026-11-10T23:27:..Z and
  `40c4821139dbb97f`. The page's `lockIntact` reads the served row as "lock broken" over predictions that
  are the frozen ones.
- B: kept 200. The runbook answers `lockedAt` 2020-01-01T00:00:00Z under the frozen digest; the page reads
  it "locked", intact, six years before the lock was made; the export's `study.md` says
  "Locked 2020-01-01T00:00:00Z under `40c4821139dbb97f`."
- The audit holds `keep_runbooks` and `lock` alone: neither rewrite left a row.

RESULT: DEFECT in both runs.

**Likely cause.**

- `core/openferment_core/project_state.py:580-584`: a runbook write after a lock is held by `frozen_as`
  (`core/openferment_core/runbook_lock.py:116-122`), which compares the digest of the row's predictions and
  measures with the lock's and reads nothing of the row's `lockedAt` or `lockHash`.
- `core/openferment_core/studies/runbooks.py:67-71`: `_laid` lays the kept lock on only when the row carries
  no `lockedAt` (`not row.get("lockedAt")`), so any row with a moment of its own is served as it stands; the
  same rule in the page's `applyProjectState` (`src/store.ts:1142-1143`).
- `core/openferment_core/project_state.py:614`: a write to a runbook already held is audited only when the
  kind is a lock, so the rewrite leaves no trace.

A fix is small: the store refuses a locked runbook's row whose `lockedAt` or `lockHash` differs from
`runbook_locks`, or `_laid` lays the kept lock over the row whenever one is kept.
