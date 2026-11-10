# H7-02: a reload while the service is away, and the queued reading waits for a second reload

**Statement.** A reload while the service does not answer leaves the project's rows unloaded, so the bench says the
project holds no such deposition while its reading sits in the browser's queue, and once the service answers again
nothing is sent until the page is reloaded a second time.

**Contract.**

- `docs/decisions/ADR-014-durable-write-queue.md:20-22`: "a write the service has not yet acknowledged is, so a
  decision made while the service is away survives a reload and is sent when the service answers."
- `src/lib/projectState.ts:9-12`: "The browser keeps only the rows the service has not yet acknowledged: an outbox,
  saved with the preferences (durable.ts), so a deposition at the bench survives a reload while the service is away
  and is sent when it answers again."
- `src/screens/Deposition.tsx:1086-1088`: "The deposition is the record, kept on the service as it changes, so the
  bench resumes after a reload".

**Command** (from the repository root): `bash bughunt/repro/H7-02/run.sh`

It runs one scenario per way of the service being away, each on a fresh database made by bh_db_fresh (through
bh_svc_start), with the service over the built app in `dist/`, project `h7-02` and one placeholder runbook (put
through `PUT /api/state/runbooks/...` and locked by `POST /api/studies/runbooks/.../lock`). Chromium
(`reload.mjs`) then:

1. sets a reviewer name and begins a deposition at the bench (readings alone) with the service answering;
2. takes the service away;
3. records "first came in at 4.4 USD/kg" (read back and confirmed) and one observation;
4. reloads the page with the service still away, reads the bench and the IndexedDB queue;
5. brings the service back and waits 45 s with no reload (the queue's retry is 15 s), reading `GET /api/state`;
6. reloads a second time and reads `GET /api/state` for up to 30 s.

The two ways of being away:

- `refuse` (127.0.0.1:9040, `bh_r_h7_02_refuse`): every `/api` request the page makes is refused at the browser,
  the candidate's own scenario. RESULT keys on this run.
- `dbaway` (127.0.0.1:9041, `bh_r_h7_02_dbaway`): the service keeps running and serving the page, and its database
  takes no connection (`ALTER DATABASE ... ALLOW_CONNECTIONS false`, its sessions ended), so every `/api` call
  answers 503. In the shipped deployment the service serves the page itself, so a reload with the service process
  stopped loads no page at all; this run shows the same defect through a door that deployment has.

Keyless, no model call. Services are stopped and both databases and their data copies dropped on exit.

**Expected.** After the reload with the service away, the bench shows the deposition with its queued reading laid
over it (and says the reading waits for the service); once the service answers, the queue is sent with no further
reload.

**Observed** (run1.log and run2.log, both scenarios, both runs). Before the reload the bench read "1 measured ·
1 observed" and the page held no words about a write waiting for the service. After the reload, service still away:
`data-state="missing"`, "Deposition not found This project holds no deposition dep-…, or its rows have not loaded
from the service yet.", while the IndexedDB queue held that deposition with `4.4 USD/kg` and 1 observation. For 45 s
after the service answered, with no reload, the service held the deposition with no entries, the bench still read
`missing` and the queue still held the entry. Within 30 s of a second reload the service held `4.4 USD/kg` and the
observation, and the queue was empty.

**Likely cause.**

- `src/store.ts:1047-1051`: `hydrateProjectState` catches the failed `GET /api/state`, sets `stateProblem` and
  returns, so it reaches neither the line that lays the queue over the held rows (`src/store.ts:1073`) nor
  `void get().flushProjectState();` (`src/store.ts:1083`).
- `src/App.tsx:378`: `hydrateProjectState` runs once per page load, and nothing calls it again when the service
  answers (`hydrateOverlay`, which sets `serviceUp`, also runs once, `src/App.tsx:375`).
- `src/store.ts:3632-3636`: the subscriber that queues and sends changes returns while `stateSeen` is null, and the
  timed retry (`src/store.ts:1182-1187`) is armed only by a flush that ran, so after the failed load no path calls
  `flushProjectState` before the next page load.
- `src/screens/Deposition.tsx:1099`: the bench's `loading` is false once `stateProblem` is set, so with the rows
  unloaded it shows "Deposition not found".
