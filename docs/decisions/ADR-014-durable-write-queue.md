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
that never saw each other's both stay, oldest first, so a page that sends from the merged snapshot puts them to the
service in order: a deposition's later write that leaves out the other tab's reading is refused in words, and the
page says so. Tabs still open send their own queues, each on its own retry, in the order they come. A page that
writes a row again replaces the row's last queued write, the one its view stands on, and another tab's earlier write
of the row stays (`enqueue`).

Guild's owed writes are kept by project (`guildOwed`), since each project's ledger is its own, and the person a page
acts as is kept in the same block, so each project keeps its own. A page takes the block of the project it has open,
and every other project's block stays as stored; a block written before this note is read once as the open project's.
The page settles its project from the project list before it reads the snapshot, and keeps that project until it
reloads: choosing another project remembers the choice and reloads the page, so every save names the project its
writes were made in. A Guild write with no project open is refused in words. A person's owed write is named by its id
and the time of the change, so a later change of one person is another write; of two tabs' owed changes of one person
the later stands. The service keeps a change's own time, as the page stamped it, when that time runs no more than five
minutes ahead of the service's clock (`guild.py`, `_change_time`), and `syncGuild` sends an owed change only when the
service holds an older copy: its copy differs, and the change it holds was made before this one, as `syncDecisions`
reads a decision. A withdrawal the service already shows is not sent again. A review decision carries the project it
was made in: a page re-applies, shows and sends its own project's decisions alone, and one the service is found to
hold, or a later one, leaves the snapshot (`holdDecision`).

The read and the write run in one IndexedDB transaction, so two tabs' saves take turns; a stored value this browser
cannot read back is written over by the saving tab's snapshot. A save made as a tab goes away (`pagehide`) reads and
writes as every save does, and starts its transaction in the same task on the database the page already opened, so the
browser runs it as the page goes. A closing page may stop before the transaction ends; its changes from the last 400 ms,
the window a save waits to gather keystrokes, then stay unstored. A page that writes a row while a flush to the service
is out replaces the row's unsent write, so the page owes the row once.

A page that loads takes the whole outbox and the open project's Guild block at once, beside the tab that queued
them, and both may send a write. A row the service keeps whole takes it twice to the same end, and a second lock, a
second withdrawal or a second Guild entry is refused, which the page that sent it second shows. The Open table holds
what remains: a copy the loading page took can reach the service after the queuing tab's later write of the row, and
review decisions are keyed by record id alone in the snapshot. `check:state` and `check:guild` hold the merge and the
sends, and `bughunt/repro/H7-01/run.sh` holds the queue in Chromium.
