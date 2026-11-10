# H5-04 (with H2-04): a locked runbook is taken back through the state door, its lock left behind

**Statement.** A study runbook locked through `POST /api/studies/runbooks/{id}/lock` is removed by
`DELETE /api/state/runbooks/{id}` (200, `removed: true`): `GET /api/studies/runbooks/{id}` answers 404,
the listing drops it, and the lock row stays in `runbookLocks` pointing at no runbook; the same run and
outputs made again through `POST /api/studies/runbooks` then answer `lockedAt: null, lockHash: null`,
while `GET` and the listing of the same id answer it locked under the old lock.

## Contract

- `core/openferment_core/project_state.py:30-31`: "What a person made, locked, measured or asked stays:
  a deposition, a measurement, a lock and a conversation are never taken back through here."
- `docs/api/studies.md:170-175`: "Locking freezes the predictions and measures under the digest ...
  From then on the store (`project_state.py`) refuses a runbook row whose predictions or measures are
  not the ones frozen, from the page or the service alike; its status and stages still move."
- `core/openferment_core/studies/runbooks.py:21-22`: "A locked runbook is never edited; a change is a
  new runbook."
- `core/openferment_core/db/rows.py:92-93` (`drop`, which `_remove` calls): "Only for what a person's own
  undo takes back; a record of what was decided or done is never removed."
- For part 2, `docs/api/studies.md:184`: "`GET /api/studies/runbooks/{id}` | Any runbook of the project,
  a lock the row does not carry laid on", and `core/openferment_core/studies/runbooks.py:104-107`
  (`make`): "The same run and outputs asked again are the runbook kept already, as it stands ... and a
  locked one is frozen."

How far the words reach: the lock row itself does stay, as line 31 lists, and a PUT under the id with a
moved prediction is still refused after the DELETE (the run shows a 422). What goes is the runbook the
lock froze: its predictions and measures leave every read, which is what "what a person ... locked
stays" and "a locked runbook is never edited" rule out.

## Command

```
bash bughunt/repro/H5-04/run.sh
```

It makes a fresh database `bh_r_h5_04_locked`, starts a keyless service on the first free port in
127.0.0.1:9630-9639, makes project `h504-a`, runs the `kinetics` engine's `batch_v1` on nine person
assumptions (no model, no network), makes a study runbook predicting `values.end.P` and locks it. Then
it sends `DELETE /api/state/runbookLocks/{id}` (the refusal a lock gets at the same door),
`DELETE /api/state/runbooks/{id}`, reads `GET /api/studies/runbooks/{id}`, the listing and
`GET /api/state`, tries a PUT with a moved prediction, makes the same runbook again, reads it and the
listing, and reads the audit. It stops the service, drops the database and removes the service's data
copy. `run1.log` and `run2.log` hold two runs.

## Expected

1. `DELETE /api/state/runbooks/{id}` of a locked runbook refused in words with a 422, as
   `DELETE /api/state/runbookLocks/{id}` is, and the runbook still served with its frozen predictions.
2. A make of the same run and outputs answers the runbook with its lock laid on, as the reads do.

## Observed (both runs)

- `DELETE /api/state/runbookLocks/rb-study-cc42c7ff6fb1`: 422 "a runbookLock is kept as it was made,
  and never taken back".
- `DELETE /api/state/runbooks/rb-study-cc42c7ff6fb1`: 200 `{"kind": "runbooks", "id": ..., "removed": true}`.
- `GET /api/studies/runbooks/rb-study-cc42c7ff6fb1`: 404 "the project holds no runbook ..."; the listing
  is empty; `GET /api/state` holds no runbook row and still holds
  `runbookLocks[rb-study-cc42c7ff6fb1] = {lockedAt, lockHash a09f34dfc59233bc}`.
- `POST /api/studies/runbooks` again: 200, id `rb-study-cc42c7ff6fb1`, `lockedAt None`, `lockHash None`;
  `GET` of the same id and the listing then answer `lockedAt` of the first lock and `lockHash a09f34dfc59233bc`.
- The audit for the id reads `keep_runbooks`, `lock`, `remove_runbooks`, `keep_runbooks`.

`RESULT: DEFECT` in both runs.

## Likely cause

- `core/openferment_core/project_state.py:144`: `Kind("runbooks", t.runbooks, "runbooks")` keeps the
  default `removable=True` whatever the runbook's lock.
- `core/openferment_core/project_state.py:662-670` (`remove`): it refuses the lock kind, the
  conversation kind and the kinds marked unremovable, and reads no lock for a runbook.
- `core/openferment_core/project_state.py:646-660` (`_remove`): it drops the row (`rows.drop`, line 655)
  without asking `_frozen` (line 534), the lock lookup `_put` makes for the same kind.
- Part 2: `core/openferment_core/studies/runbooks.py:119-140` (`make`): once the row is gone `_held` finds
  nothing, so `make` builds a fresh draft, keeps it, and answers the `Runbook` it built (line 140, with
  `lockedAt=None`); the reads lay the surviving lock on through `_laid` (line 71).
