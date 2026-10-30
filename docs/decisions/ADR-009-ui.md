# ADR-009 — The UI is kept and wired

- **Status**: accepted (requirements: nothing hidden behind many buttons; something on screen at
  the earliest moment; visibly alive while work runs)
- **Date**: 2026-10-30

## Decision

React 18, TypeScript, Vite, Tailwind, zustand, the hash router, `ui.tsx`, the figure grammar,
`ParameterPanel`, the run report, the Deposition takeover, Guild and Primer stay. Home opens on the
person's projects and a Postdoc conversation; module screens become views inside a project; the
Durable tier keeps UI preferences only; the trace is the result surface, every artifact an
inspectable card; the SFF graph renders in the run report and the flowsheet page.

## Implementation

### 7.1 (2026-10-30)

- `/p/:project` is a project's home, and `/p/:project/<path>` a module screen as a view inside the
  project: the router reads the prefix off (`Route.project`), so every screen reads the path it
  always read, a navigation or a link from inside a project stays inside it (`inProject`), and an
  address naming another project opens it (the page reloads in it, as a project switch does).
- Home opens on the person's projects, a form to make one, Postdoc's ask box (it asks in the open
  project's conversation screen), the open project's recent conversations, and what runs in it
  now as live cards (`HomeStart`). The project home is the conversation on the left, the live trace
  on the right, and the project's views one click away (`ProjectHome`).
- The trace cards (`TraceCards`, `lib/events.ts`): the project's event stream, one card an event
  at once: a worker job with its state and its clock, a Postdoc turn with each tool it called and
  how much came back (`tool.result` gains `hits`), an artifact kept with its provenance; each card
  links to the record the tables keep. Nothing on them computes a number.
- The SFF graph (`SffGraph`): the service's graph of a file, each unit in its column, a stream that
  closes a recycle dashed, feeds and products named at the boundary; in the run report's SFF card
  and on a flowsheet's page (`/flowsheets/:id`, `FlowsheetPage`).
- A claim's typed values render in the answer (6.2), an estimate under the assumed mark.
- The Durable tier keeps preferences and the writes the service has not acknowledged
  (ADR-014, a departure).
- `pnpm gen:api` writes `docs/api/openapi.json` (each route's project scope on it, A5) and
  `src/api/types.gen.ts` (openapi-typescript); verify runs `gen:api --check`. The hand-kept
  `src/data/types.ts` and `check:plan`'s pairs stay until every screen reads the generated types.

### 7.2 (2026-10-30)

- The UI walk (`scripts/walk.ts`, Chromium through the built app against a real service): Home,
  the project at its own address with its trace open, a document pasted in and searched, a run's
  report and its SFF graph drawn, the conversation of the proof's step 6 with its estimate marked,
  a runbook. It is the proof's step 9 and runs in CI after verify.

## Revisit condition

A design pass after alpha 2.0.

## Evidence

- Execution prompt §4.9 and §8.5; development plan §1 ("The Home experience should be a
  conversation with Postdoc inside a chosen project").
