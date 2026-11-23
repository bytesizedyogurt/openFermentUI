# R1-04: two Departures rows disagree on whether the browser keeps the lessons finished

**Statement.** The stage 2 row of `docs/PROGRESS.md`'s Departures table (line 543) says the browser keeps three
preferences, the third "the lessons finished here"; the E.12 row of the same table (line 502) says "The Durable
snapshot keeps no lesson", and the tree at 2047f5a writes no lesson into the snapshot: `learnProgress` is a legacy
member of `DurableSnapshot` that nothing reads and the next save leaves out.

Kind: Inconsistency. Severity: S4 (a record's words drift from the tree; no screen, number or row is wrong).

## Contract

- `docs/PROGRESS.md:543` (Departures, row "§5.5, stage 2"): "The browser keeps an outbox: review decisions, Guild
  changes and project rows the service has not yet acknowledged, saved in IndexedDB until sent; and three
  preferences, who is deciding, who is acting in Guild, and the lessons finished here".
- `docs/PROGRESS.md:502` (Departures, row "alpha 2.2 §6.5, E.12"): "The Durable snapshot keeps no lesson, ...: the
  modules slice, `learnProgress` and `completeLesson` leave the store, ...; a snapshot's older `learnProgress`
  loads, and the next save leaves it out (ADR-014's note of E.12)".
- `docs/decisions/ADR-014-durable-write-queue.md:13-14`, edited at E.12 to say the same: "besides the preferences
  (the reviewer's name, the Guild person the browser acts as, and until alpha 2.2 E.12 the lessons finished
  here)"; and its note, lines 39 and 43-44: "The snapshot keeps no lesson." "The preferences the snapshot keeps are
  the reviewer's name and the Guild person the browser acts as."
- The table keeps its rows current elsewhere: the stage 2 row at line 545 carries "(since alpha 2.2 E.0b ...)".

## Command

```
bash bughunt/repro/R1-04/run.sh
```

From the repository root. Keyless, no model call, read-only. The defect is static, so the script makes no database
and starts no service: it reads the four files at 2047f5a with `git show` into a temporary directory under
`$BH_WORK/R1-04/` (removed at the end), checks the checkout's copies are identical to them, reads the keys
`snapshotOf` returns with the TypeScript compiler's parser (`snapshot_keys.mjs`), and greps `src/` and `scripts/`
at 2047f5a for `learnProgress` and `completeLesson`.

## Expected

One account in the Departures table of what the browser's Durable snapshot keeps, true of the tree: two
preferences (who is deciding, `reviewerName`; who is acting in Guild, `guild.actingId`) and the writes the service
has not acknowledged, with no lesson, as line 502 and ADR-014 say.

## Observed (run1.log, run2.log: RESULT: DEFECT both times)

- Line 543, under "## Departures from the execution prompt", says "three preferences, who is deciding, who is
  acting in Guild, and the lessons finished here" and names no later step (no E.12, ADR-018, "since" or "until
  alpha 2.2").
- Line 502, in the same table, says "The Durable snapshot keeps no lesson".
- `src/store.ts` `snapshotOf` (line 3504), the whole object `flush()` puts in IndexedDB
  (`src/lib/durable.ts:277`), writes `version savedAt reviewDecisions reviewerName guild guild.pending
  guild.withdrawals guild.actingId outbox` and, while a pre-2.0 snapshot's rows wait, those nine legacy rows; no
  key names a lesson.
- `src/lib/durable.ts:142-148`: `learnProgress?` is documented "LEGACY, left where it lies ... nothing reads this,
  and the next save leaves it out." Of the two lines of `src/` and `scripts/` naming `learnProgress` or
  `completeLesson`, one is that type and the other is `scripts/check-guild.ts:404`, a check that the store keeps
  no lesson.

## Likely cause

E.12 (`c18c0e7`) added the row at `docs/PROGRESS.md:502` and edited `docs/decisions/ADR-014-durable-write-queue.md:14`
to "until alpha 2.2 E.12 the lessons finished here", and left `docs/PROGRESS.md:543` as stage 2 (`fa16892`) wrote
it. Confidence: high.
