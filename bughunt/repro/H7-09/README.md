# H7-09: a deposition's timers and deviation notes end on a reload that Settings says they survive

**Statement.** Settings' Storage row and durable.ts's header say a deposition at hour 14 with timers running cannot
be lost to a page reload, while a deposition's run at the bench keeps its step, its timers and its deviation notes in
page memory alone, and one reload ends the run and loses them.

**Kind and severity.** Inconsistency, S4 (wording and drift). The run screens say what happens (a run lives for the
session, and a leave-page prompt warns), so the defect is the two sentences that promise otherwise.

## Contract

- `src/screens/Settings.tsx:1254-1256`, the Storage row under Settings > About, as the built app shows it: "This
  browser keeps its preferences and the writes the service has not yet acknowledged, in IndexedDB, because a
  deposition at hour 14 with timers running cannot be lost to a page reload; they are sent when the service answers."
- `src/lib/durable.ts:6-8`, the Durable tier's header: "A fermentation at hour 14 with timers running and deviations
  logged cannot be lost to a page reload."

The tree's own run screens give the other account:

- `src/screens/Deposition.tsx:297-298`: "This run is no longer active" / "A run at the bench lives in this page's memory,
  so a reload ends it".
- `src/screens/ProtocolDetail.tsx:1264`: "Deposition records step completions, deviations and timers for this session
  only."

## Command

    bash bughunt/repro/H7-09/run.sh        (from the repository root)

It greps the four sentences and the store's snapshot, makes a fresh database `bh_r_h7_09_reload`, starts a keyless
service on 127.0.0.1:9213 over the built app in `dist/`, puts one project, one placeholder locked runbook and one
placeholder three-step protocol (step 2 timed) through the API, and drives Chromium at 810x1080 (`reload.mjs`). The
browser reads Settings' Storage row, starts a deposition from the runbook with the protocol, records a deviation note,
starts step 2's timer, reads the browser's IndexedDB snapshot, reloads once with the leave-page prompt accepted, and
reads the screen and the snapshot again. Then the script reads `GET /api/state`. No model call. It prints EXPECTED:,
OBSERVED: and RESULT: lines, exits 0, and stops the service and drops the database on the way out.

## Expected

One account of a deposition across a reload. Either the run comes back after one reload with its running timer and
its deviation note, as Settings and durable.ts say, or Settings and durable.ts say what Deposition.tsx and
ProtocolDetail.tsx say: a run lives for the session.

## Observed (run1.log and run2.log, both RESULT: DEFECT)

- The built app's Storage row reads "... because a deposition at hour 14 with timers running cannot be lost to a page
  reload; ...".
- Before the reload: the bench at `#/p/h7-09/runbooks/protocols/h7-09-protocol/run/run-2` shows the deviation note and
  the running timer "placeholder wait" with its Pause button. The IndexedDB snapshot holds the keys `guild`, `outbox`,
  `reviewDecisions`, `reviewerName`, `savedAt` and `version`; it carries no run, no note and no timer.
- The reload raises one `beforeunload` prompt, accepted.
- After the reload, at the same address: "This run is no longer active. A run at the bench lives in this page's memory,
  so a reload ends it; ...". The note, the timer and its Pause button are gone, and the snapshot still holds no note.
- The service keeps the project's one deposition, the record itself, and neither the note nor the timer appears
  anywhere in its state.

## Likely cause

The words were carried from OF-BLD-006 §4.6 into the Settings row and the durable.ts header. The behaviour they
describe was never wired to a run:

- `src/store.ts:1506-1527` `startRun`, `src/store.ts:1575-1580` `addDeviation` and `src/store.ts:1582` `addTimer` keep the
  run, its deviations and its timers in `s.runs`, in page memory.
- `src/store.ts:3504-3555` `snapshotOf` writes no `runs` and no `activeRunId` into the Durable snapshot, and the save
  subscription at `src/store.ts:3655-3670` watches no `s.runs`, so a run change never reaches IndexedDB.
- The same drift sits in two comments: `src/lib/durable.ts:285-287` ("a running deposition mutates on every keystroke
  and every timer tick") and `src/store.ts:3671` ("A tab closing mid-run must not lose the last few hundred
  milliseconds").

A small fix is the wording: Settings' Storage row and the durable.ts header say a run at the bench lives for the
session, as Deposition.tsx and ProtocolDetail.tsx do.
