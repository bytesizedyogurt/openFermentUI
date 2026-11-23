# H7, the client: notes

Commit 2047f5a, the built app in dist/ served by the head's service. Every database was bh_h7_*, every port 8870-8873,
no model call, no key. Scripts are under `scripts/`; `scripts/repro.sh <scenario>` rebuilds a seeded copy of
openferment_dev (read with pg_dump), serves it on 8873 and runs one scenario, then removes both.

## States made

- Empty: a fresh database with one project, `empty` (8870).
- Full: openferment_dev copied with pg_dump/pg_restore to bh_h7_full (Ethanol, 22 documents, 6 runs, 3 comparisons,
  35 conversations), seeded through the API with placeholder rows so detail pages have something to open
  (`scripts/seed_full.py`: a locked runbook, a strain, a product, a skill, a lesson, a protocol, a Guild person) (8871).
  A second copy, bh_h7_ob, served on 8872 for the queue experiments.
- Stopped: the full service with every `/api` request refused in the browser context (Playwright route abort), and,
  for the queue, the service really stopped and started (`bh_svc_stop`, `bh_svc_start`).

## The walk (scripts/walk_all.mjs)

74 addresses: the 12 rail entries, every sub-view in src/data/nav.ts and every address case in Screen() (detail
pages with real ids in the full state and missing ids in the empty one, the three takeovers last), in all three
states. Captured console errors, page errors (uncaught and unhandled rejections), failed requests, 4xx/5xx from
/api, the screen boundary, the not-found page, and every in-app anchor's href.

Held: no uncaught error or unhandled rejection anywhere; no screen boundary; no not-found page; the only console
errors were Chromium's "Failed to load resource" lines for a 404 on a missing id (empty state) and for refused
connections (stopped state). Every anchor on every page kept `#/p/<project>/` except the rail's logo (H7-08).

## The store and the pending-writes queue (scripts/outbox.mjs)

- stop (held): readings recorded on a live page after the service was stopped were kept in the IndexedDB outbox,
  retried every 15 s, and sent once, in order (1.1, 2.2, 3.3 USD/kg and the observation), within the retry after
  the service started again, with no reload. Nothing on the bench said they waited (folded into H7-02).
- reload: H7-02.
- twotabs (service away): H7-01, the one silent loss of a bench reading.
- sameonline (service up, one deposition in two tabs): H7-03.
- overrides (scripts/overrides_twotabs.mjs): H7-04.
- ids across reloads (held for rows): deposition, entry, observation, scenario, runbook and train ids carry the
  time (store.ts timeId) and stay unique across reloads; a protocol run's id `run-N` restarts at each load, which
  only matters for a run's address after a reload (suspected list).
- The open project is held per tab in memory (lib/project.ts), so two tabs on two projects each name their own
  in X-OpenFerment-Project (held, by reading; a reload adopts localStorage's, which the address then corrects).
- An address naming a project the service does not hold: H7-05 (scripts/unknown_project.mjs).

## Generated types, casts and non-null assertions

- `scripts/answers_vs_types.py` held 49 GET answers of the full project to docs/api/openapi.json (the source of
  src/api/types.gen.ts): no field the schema requires was absent and no non-null field came null. The schemas served
  with exclude_unset (AS_KEPT) were compared against /api/state's rows: optional fields stay optional in the types.
- `scripts/casts.mjs` lists the 200 `as` casts (other than `as const`) and 60 non-null `!` under src/ by parsing each
  file with TypeScript (list in the scratch log casts.txt). The `!` sites that read a Map or a find were each read
  and are guarded by a preceding has/some/filter (Settings.tsx:1283, Runbooks.tsx:116, ProformaComparison.tsx:188,
  PureOS.tsx:386, StrainPage.tsx:595). The widening casts (Home.tsx ProvKind, figure records) cannot fail. The
  casts of untyped artifact output (ProformaComparison, Dossier, GeneOSModel) rendered on every kept artifact of the
  full project with no error; an artifact written by an older tool was not available to test.

## Deposition at 810x1080 (scripts/deposition_a11y.mjs)

Views measured: a protocol's staged run, step 1 (gate held), its preview and read-back, the timed step before and
after Start timer, the step list, the skip modal; the bench staged, running, its preview, read-back and close
modal. Held: the step text is on ink at 14.9:1 (13.7:1 in the step list); no horizontal scroll at 810 px; the
bench has no target under 44 px. H7-07 names the two targets under 44 px and the hover-only underline. The
secondary texts under 7:1 are listed there too; the R line holds the step text, which passes.

## Words with the service stopped (scripts/stopped_words.mjs)

18 pages read with the service up and with it refused: H7-06.

## Left for others or for a live model

Review decisions made while the service is away were not exercised: the full project holds candidates and no
records. Postdoc's own writes (conversations through the queue) need a model. The trace cards' event stream was
seen only reconnecting while refused.
