# ADR-014 — The Durable tier keeps preferences and the writes not yet acknowledged

- **Status**: accepted (a departure from execution prompt §5.5 and A3; the owner may reverse it)
- **Date**: 2026-10-30

## Context

The execution prompt says the browser's Durable snapshot keeps UI preferences only: "durable.ts
keeps theme, density, panel state and the last-open project" (§5.5), and A3 holds the snapshot to
"UI preferences only". Since stage 2 every scientific record lives on the service, in its
project: review decisions, Guild's ledger, depositions, measured evidence, runbooks and their
locks, overrides, fits, scenarios, trains and conversations (`lib/projectState.ts`). What the
snapshot still writes, besides the preferences (the reviewer's name, the Guild person the
browser acts as, and until alpha 2.2 E.12 the lessons finished here), is a queue: review decisions, Guild entries and
project rows made while the service did not answer, each removed once the service acknowledges
it, and the rows a browser from before alpha 2.0 kept, until a project takes them.

## Decision

Keep the queue in the Durable snapshot. A record the service holds is never kept there; a write
the service has not yet acknowledged is, so a decision made while the service is away survives a
reload and is sent when the service answers. Without it, a reviewer's decision made during an
outage is lost on the next reload, the safety problem OF-BLD-006 §4.6 kept Durable for.

## Consequences

- A3 reads: the snapshot holds preferences and the writes the service has not acknowledged, never
  a record the service holds. `check:state` holds the queue to that (a write leaves it when the
  service answers).
- The rows of a browser from before alpha 2.0 leave the snapshot once a project takes them.

## Revisit condition

The owner asks for the queue to go, or accounts (after alpha 2.0) give a person's pending writes a
home on the service.

## Implementation note (alpha 2.2 E.12, 2026-11-05)

The snapshot keeps no lesson. The lessons are the project's lesson catalogue (ADR-018), and a lesson shows passed
from the ledger's entries for whoever is learning: passing its checkpoint writes a knowledge entry for each skill
it counts toward, which waits in the queue like any other Guild write while the service is away. A snapshot that
holds the lessons finished in a browser before this commit (`learnProgress`) still loads; nothing reads that field,
and the next save leaves it out. The preferences the snapshot keeps are the reviewer's name and the Guild person the
browser acts as.

## Implementation note (alpha 2.2 E.19, 2026-11-05)

The screens say where a project's rows are kept. Postdoc's empty list of conversations said they were kept in this
browser, across reloads; the service has kept each conversation with the project since alpha 2.0's stage 6.1
(`docs/api/postdoc.md`), and the list says so. The same search found the words that gave a browser or a session a
row the service keeps: pureOS's trains of this browser and a train run built in another browser, Guild's ledger this
browser holds, a lesson the store holds, and the words of the review queue, Witness, Intake, the protocol compare
and the lesson embeds that held the project's records, decisions, gold set and versions in this session. Each now
names the project; a decision made while the service is away says it waits in this browser and when it is sent, and
Home's list of activity, the page's own, says what happened since the page opened. `pnpm check:state` reads every
sentence under `src/` (a string, a template, a JSX attribute's words, or one element's text with the strings of its
expressions) and holds it to this record: a sentence that keeps something in this browser names a write that waits
for the service or a preference, a browser owns no row, and a session holds what it loaded and what lives on the
page alone. `pnpm smoke` reads Postdoc's empty list on the screen.

## Implementation note (the bug hunt's fix run, 2026-11-11)

Every tab of a browser saves under the one key, and each tab held its own copy of the queue, so the tab that saved
last set the queue for the whole browser: a reading queued at the bench in one tab during an outage was erased by a
second tab's save and never reached the service (the bug hunt's H7-01). A save now merges (`durable.ts`,
`mergeSnapshot`): it keeps what this tab owes now and, from the snapshot already stored, every owed write this tab
has never held, which is another tab's. A write this tab held and no longer holds was answered by the service or
replaced by this tab's own later write of the same row, so the merge leaves it out. Two writes of one row from tabs
that never saw each other's both stay, oldest first, so the service rules on them in order as it would on two tabs
online: a deposition's later write that leaves out the other tab's reading is refused in words, and the page says
so. Guild's owed writes are kept by project (`guildOwed`), since each project's ledger is its own: a page takes the
block of the project it has open, and every other project's block stays as stored; a block written before this note
is read once as the open project's. A person's owed write is named by its id and the time of the change, so a later
change of one person is another write. A review decision the service is found to hold, or a later one, leaves the
snapshot (`holdDecision`). The read and the write run in one IndexedDB transaction, so two tabs' saves take turns;
a stored value this browser cannot read back is written over by the saving tab's snapshot.

A page that loads takes every owed write in the snapshot at once, beside the tab that queued it, and both may send
it. The service keeps a write it is sent twice as it kept the first, apart from one case the Open table holds: a
copy the loading page took can reach the service after the queuing tab's later write of the same row, and a row the
service replaces whole then takes the older copy. `check:state` holds two tabs saving in turn during an outage to
both tabs' writes reaching the service, and `bughunt/repro/H7-01/run.sh` holds it in Chromium.
