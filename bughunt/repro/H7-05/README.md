# H7-05: an address naming a project the service does not hold reloads the page without end

**Statement.** Opening `/#/p/<id>/...` for an id the service holds no project under makes the page reload
again and again, each load asking `GET /api/projects`, and it never settles on a screen.

**Contract.** `docs/decisions/ADR-009-ui.md:19-22` (Implementation 7.1): "`/p/:project` is a project's home, and
`/p/:project/<path>` a module screen as a view inside the project: ... and an address naming another project opens
it (the page reloads in it, as a project switch does)." A project switch reloads the page once. The comment at `src/App.tsx:139` says the same: "A project's address opens the project (§8.5): the
page reloads in it."

**Command.** From the repository root:

    bash bughunt/repro/H7-05/run.sh

It makes a fresh database (`bh_r_h7_05_unknown`), starts the service on 127.0.0.1:9940 over the built app in
`dist/`, makes one project (`h7-05`) through the API, and runs `unknown.mjs` in Chromium: one fresh browser opens
`/#/p/h7-05/runbooks` (the control, a project the service holds), and a second fresh browser opens
`/#/p/nosuchproject/runbooks`. Each counts page loads and `GET /api/projects` over 10 s and then 2 s more. It
stops the service, drops the database and removes its data copy on the way out. Keyless, no model call.

**Expected.** The unknown address reloads once at most and then settles on one screen, as the held project's
address does (2 loads: the first and the one reload a project switch makes). A screen saying the service holds
no project of that id would be the natural one.

**Observed** (run1.log, run2.log). The held project's address: 2 loads, then still. The unknown address: 108 and 87
loads, with as many `GET /api/projects`, in 10.2 s on the two runs (about 9 to 11 a second), and 22 and 17 more
loads in the 2 s after, without end; the address
stays `#/p/nosuchproject/runbooks` and `localStorage['openferment.project']` reads `nosuchproject` between loads.
The Runbooks screen is drawn for a moment on each load and taken away by the next reload.

**Likely cause.**

- `src/App.tsx:140-142`: the effect opens `route.project` whenever it differs from the store's `projectId`.
- `src/store.ts:1016-1019`: `loadProjects` replaces an open id the list lacks with the only project held
  (or with null when several or none are held), and writes that to the store and to localStorage.
- `src/store.ts:1023-1027`: `openProject` writes the address's id to localStorage and reloads.

Each load starts with `projectId = 'nosuchproject'` (read back from localStorage), so the effect stays quiet until
the project list arrives; `loadProjects` then sets `projectId` to `h7-05`, the effect sees the address's id differ
and calls `openProject('nosuchproject')`, which stores it again and reloads. Nothing checks the address's id
against the list before opening it, so the cycle never ends. Any count of held projects shows it: one held gives
`h7-05`, two or none give `null`, and both differ from the address.

**Severity.** S3: an edge case (a mistyped id, a link from another database or instance) with a workaround
(edit the address to Home or to a held project's address, and the next load settles).
