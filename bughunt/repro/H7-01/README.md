# H7-01: two tabs while the service is away, and tab A's queued reading is erased

**Statement.** With two tabs open on one project while the service does not answer, each tab saves its own queue
whole over the browser's one IndexedDB snapshot, so a reading recorded in tab A is erased when tab B saves, and once
both tabs close that reading never reaches the service.

**Contract.**

- `docs/decisions/ADR-014-durable-write-queue.md:20-22`: "Keep the queue in the Durable snapshot. A record the service
  holds is never kept there; a write the service has not yet acknowledged is, so a decision made while the service is
  away survives a reload and is sent when the service answers."
- `src/lib/projectState.ts:9-12`: "The browser keeps only the rows the service has not yet acknowledged: an outbox,
  saved with the preferences (durable.ts), so a deposition at the bench survives a reload while the service is away
  and is sent when it answers again."

**Command** (from the repository root): `bash bughunt/repro/H7-01/run.sh`

It makes a fresh database `bh_r_h7_01_twotabs` (bh_db_fresh, through bh_svc_start), starts the service on
127.0.0.1:9310 over the built app, makes project `h7-01` with one placeholder runbook (put through
`PUT /api/state/runbooks/...` and locked by `POST /api/studies/runbooks/.../lock`), then drives Chromium
(`twotabs.mjs`):

1. Tab A sets a reviewer name and begins a deposition (readings alone); tab B opens and begins its own. The service
   holds both, with no entries.
2. The service is stopped (`bh_svc_stop`).
3. Tab A records "tab A came in at 5.5 USD/kg"; tab B then records "tab B came in at 6.6 USD/kg". The snapshot is
   read from IndexedDB after each.
4. Both tabs close with the service still stopped; the snapshot is read from a blank page on the same origin.
5. The service starts again on the same database; one new tab opens on the project, which reads the snapshot and
   sends its queue. What the service holds of each deposition is read from `GET /api/state`.

Keyless and with no model call. The service is stopped, the database dropped and its data copy removed on exit.

**Expected.** Tab A's reading stays in the queue through tab B's save and both tabs closing, and the service holds
A's deposition with 5.5 USD/kg and B's with 6.6 USD/kg once it answers.

**Observed** (run1.log and run2.log). The snapshot's queue held A's deposition after A wrote, held B's alone after B
wrote, and held B's alone with both tabs closed. Once the service answered and a tab opened, the service held B's
deposition with 6.6 USD/kg (sent through the queue, since tab B had closed while the service was stopped) and A's with
no entries. Tab A had shown "1 measured" before it closed; the new tab said nothing of a dropped reading.

**Likely cause.**

- `src/lib/durable.ts:50`: `const KEY = 'snapshot';` one key for the whole browser, and `src/lib/durable.ts:277`
  `tx.objectStore(STORE).put(snapshot, KEY)` writes the snapshot whole.
- `src/store.ts:3669`: `saveDurable(snapshotOf(s));` on every change to the tab's queue, with `src/store.ts:3539`
  `outbox: s.stateOutbox,` writing this tab's in-memory queue as the whole outbox.
- `src/store.ts:2544`: the snapshot's outbox is read into a tab once, at hydrate
  (`stateOutbox: enqueue(snap.outbox ?? [], s.stateOutbox)`), so a tab open before another tab queued a row saves over
  that row.

By reading `snapshotOf` (`src/store.ts:3504-3555`), the same holds for every row kind in the queue (`OutboxEntry`),
and for the review decisions and Guild writes that ride in the same snapshot from each tab's own memory; the run shows
the deposition case alone.
