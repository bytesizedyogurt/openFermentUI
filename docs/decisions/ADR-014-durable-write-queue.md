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
A Guild write with no project open is refused in words. A person's owed write is named by its id and the time of the
change, so a later change of one person is another write; of two tabs' owed changes of one person the later stands.
The service keeps a change's own time, as the page stamped it, when that time runs no more than five minutes ahead of
its clock (`guild.py`, `_change_time`), and a person added and changed while the service was away, who arrives as one
add carrying the change, keeps the change's maker and time when its maker is a lead the ledger holds by then;
`syncGuild` sends each person after the people who added and changed them (`byMakers`), so a lead added offline is
held first. The ledger's first person stays active: an offline change that leaves them inactive would leave no lead to
add anyone, and is not taken. Of two changes of one person the service keeps the later, whichever arrives last: a
change made before the one it holds leaves the ledger as it is. `syncGuild` sends an owed change unless the service's
copy says the same or holds a change made at or after it; a copy held as an add alone carries no change, so the change
is sent. A withdrawal the service already shows is not sent again. When the ledger cannot be read again after a sync,
the page shows each person and entry as the service answered its post. A run the service refuses goes as a deviation,
and a deviation the service went away before taking is owed in the run's place.

A review decision carries the project it was made in, and the snapshot keys it by its project and its record
(`decisionKey`), since a record id is made from a paper and its words and one paper may be held by two projects: each
project's offline decision on a record of one id stays, and a page re-applies, shows and sends its own project's
decisions alone (`decisionsIn`). A decision kept by its record alone, as a snapshot before this kept it, is read as
the loading page's when it names no project or names the page's, and leaves once the page saves it under its project;
one naming another project waits for a page open on that project. An undo that takes a record back to undecided after
a decision the service holds is owed like any decision, and is kept until it is sent. One the service is found to
hold, or a later one, leaves the snapshot (`holdDecision`).

The address names the project a page loads in (`#/p/<id>/...`; `lib/project.ts`), and an address that names none opens
the one this browser last opened. The page's first read of the project list settles its project before it reads the
snapshot, and a call made while that read is out waits for it: the address's project when the service holds it, else
the one remembered, else the only one held, and the browser remembers it. The page keeps that project until it
reloads, so every save names the project its writes were made in. Choosing another project writes its address and
reloads, so the choice lands whether or not this browser can remember it (site data blocked); a reload the person
stays from (a run is going) leaves the page in its project, its address with it, and a project made there joins the
page's list once the address is the page's own again. A project an address names that the page's list leaves out is
looked for once more on the service (one made since in another tab opens); a project the service does not hold opens
nothing, and the page says so and stays in its own, as it does when that second read goes unanswered. A page whose
list the service has never answered since it loaded leaves the address to say: it opens the project the address names,
as a load of the address does, and remembers nothing a list has not confirmed.

The read and the write of a save run in one IndexedDB transaction, so two tabs' saves take turns; a stored value this
browser cannot read back is written over by the saving tab's snapshot. A page that is closing or reloading runs no
event after its own, so its save (`pagehide`) cannot read first: it writes the tab's last snapshot and the owed writes
it has held under a key of its own (`parting:` and the tab's id), which no other tab writes, and commits the
transaction at once (`flushDurable`); a tab whose last save has landed leaves nothing. The next page to load folds
every such record into the snapshot, oldest first, and deletes it (`foldParting`, in `loadDurable`'s one transaction):
the owed writes as the tab's own save would have merged them, and what a save takes whole from whichever of the
snapshot and the record was saved later: who is reviewing and the rows kept before alpha 2.0 by the save's time, the
person acted as in a project by the time that project's block was written (each block carries its own). The page takes
the fold as its own once that transaction has committed; one that rolled back leaves the page the snapshot as stored,
and the records for the next load. A tab that lives on deletes its own record on its next save. Clearing this
browser's data clears them too. In Chromium a write placed at `pagehide` and left to commit on its own did not land
before the page went; committed at once, it does.

A page that writes a row while a flush to the service is out replaces the row's unsent write, so the page owes the row
once. A flush whose every write the service refused goes round again for what was made while it ran. Clearing this
browser's data ends a flush, a Guild sync or a decision sync still running: what it had not sent by then is not sent,
and nothing it took is put back. A Guild row still owed leaves the page's ledger at the clear, and a sync the clear
stopped reads the ledger again.

A page that loads takes the whole outbox and the open project's Guild block at once, beside the tab that queued them,
and both may send a write. A row the service keeps whole takes it twice to the same end, and a second lock, a second
withdrawal or a second Guild entry is refused, which the page that sent it second shows. The Open table holds what
remains: a copy a loading page took, or what a closing tab left, can reach the service after another page's later
write of the row. `check:state` and `check:guild` hold the merge and the sends, and `bughunt/repro/H7-01/run.sh` holds
the queue in Chromium.

A write of a scope's overrides names the rows the page's view stood on (`base`), and the service lays it on what it
keeps key by key (bug hunt H7-04; `docs/api/studies.md`). An owed write the outbox carries keeps the rows its view
stood on: a later write of the scope that replaces it stands on them too, a write made while the scope's write was out
stands on what that write sent, and a write an older page queued with none replaces the scope whole, as it was made
to. So an older copy of a scope's write changes the keys it changed alone, and one that meets a key another page
changed since is refused in words, after which the page reads the project's overrides again. A row the service keeps
whole (a scenario, a train) still takes whichever copy reaches it last (the Open table).
