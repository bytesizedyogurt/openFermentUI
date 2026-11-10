# H14-05: Home's BioRepo destination says "gold set not yet annotated" beside a Gold set tile that counts one

**Statement.** The BioRepo destination's state line on Home is fixed text, so once a record is flagged gold the same
page counts one gold value on its Gold set tile and says, on the BioRepo card, that the gold set is not yet annotated.

**Contract.**
- `src/screens/Home.tsx:235-238` (the comment over `Counted` and `stateOf`): "What each destination actually has,
  right now (§7). Counted from the store's lists where there is something to count, and stated as "nothing" where
  there is not."
- `src/screens/Home.tsx:781-782` (the destinations band): "the whole navigation, laid out once with an honest current
  state per entry."
- The Gold set tile on the same page (`src/screens/Home.tsx:570-587`) counts `records.filter((r) => r.gold)`.

The candidate cited `src/screens/Home.tsx:490-495` ("The tiles below wear the dominant tick of the data behind them").
That sentence governs the vitals tiles' provenance ticks; the two comments above govern the destinations' words and
carry the contract this line breaks.

**Command** (from the repository root):

    bash bughunt/repro/H14-05/run.sh

It makes a fresh database `bh_r_h14_05_home`, starts the service keyless on the first free port in 9780-9789,
pastes one document, writes one candidate by hand through `POST /api/tools/biorepo_write` (no model), promotes it
through `POST /api/biorepo/decisions` with provenance `gold` and a gold value, reads Home of the built app (`dist/`)
in headless Chromium (`screen.mjs`), prints the source line, and cleans up.

**Expected.** With one gold value on the Gold set tile, the BioRepo destination line counts the gold values (for
example "1 paper · 1 gold value") or leaves the gold set out of its line.

**Observed** (run1.log and run2.log, the same both times):

    Gold set tile:            GOLD SET | 1 | across 1 paper · the evaluation baseline
    BioRepo destination line: 1 paper · gold set not yet annotated
    RESULT: DEFECT

**Likely cause.** `src/screens/Home.tsx:284` writes the words for every count:

    BioRepo: { now: `${n.papers} paper${n.papers === 1 ? '' : 's'} · gold set not yet annotated`, built: true },

`Counted` (`src/screens/Home.tsx:244-256`) carries no gold count, and `stateOf` is built at `src/screens/Home.tsx:366-379`
from the lists alone, while `goldRecords` (`src/screens/Home.tsx:402`) is computed a few lines later for the tile. A
small fix passes `goldRecords.length` into `Counted` and words the line from it.

**Severity.** S4 (wording on one screen; the Gold set tile beside it shows the right count).
