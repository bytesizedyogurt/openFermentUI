# H14-04: Witness shows PRECISION 0.0% beneath its own words that precision is undefined without a gold set

**Statement.** With no gold value and one rejected candidate, the Witness screen draws PRECISION 0.0% on the gold
tick ("Gold · a value a reviewer typed") directly under the callout "Precision and recall are undefined without a
gold set", so one rejection reads as an extractor that is never right, while the reviewer accepted the other two
candidates as written.

**Contract.**

- `src/screens/Witness.tsx:569-576`, shown when `metrics.goldSize === 0`: title "No gold annotations yet", body
  "Precision and recall are undefined without a gold set. Flag records for gold in the review queue and this screen
  fills in."
- `core/openferment_core/witness.py:24-28`: "Candidates on an extracted paper for a field no reference covers are
  NEW records ... they are not scored: there is nothing to score them against until a reviewer types a value."
- `src/screens/Witness.tsx:172`: the undefined tile reads "—", titled "Undefined — the denominator is zero".

**Command** (from the repository root):

    bash bughunt/repro/H14-04/run.sh

It makes a fresh database `bh_r_h14_04_wit` and starts the service keyless on the first free port from 9084 within
9080-9089, in the proof's fixture mode: the extract route reads a written stand-in response and calls no model.
It pastes one document of three sentences, extracts three candidates from it (ethanol titre, yield, productivity),
accepts two as written, rejects one with a reason, reads `GET /api/witness/runs`, and opens
`/p/h14-04/biorepo/witness` of the built app in `dist/` in headless Chromium (`screen.mjs`). It stops the service,
drops the database and removes its data directory on exit.

**Expected.** With no value a reviewer typed (goldSize 0, `results` empty), the precision tile reads "—" as the
recall tile does, in agreement with the callout above it.

**Observed** (run1.log, run2.log, both `RESULT: DEFECT`):

- `GET /api/witness/runs`: run `claude-1`, 0 results, 1 false positive.
- The screen: callout "No gold annotations yet / Precision and recall are undefined without a gold set ...";
  precision tile "0.0%" with class `tick-gold` and the label "Gold · a value a reviewer typed."; recall tile "—";
  the line below reads "tp 0 · fp 1 · fn 0".

**Likely cause.**

- `src/screens/Witness.tsx:480`: `const precisionDefined = metrics.micro.tp + metrics.micro.fp > 0;` turns true
  from one rejection alone, with goldSize 0. The callout's condition (`metrics.goldSize === 0`, line 569) and the
  tile's condition read different counts.
- `src/engine/metrics.ts:28`: `prf` gives 0/(0+1) = 0, and line 74-77 adds each rejection to fp; acceptances of
  uncovered candidates add nothing to tp (by `witness.py:24-28`), so with no gold set the only number precision can
  take is 0.
- `src/screens/Witness.tsx:490`: the headline tick is `gold` for `claude-1` whatever the gold set's size.
- The metrics CSV (`src/screens/Witness.tsx:379`) uses the same `tp + fp > 0` test, so the export carries 0.0000
  for this state (read from the code; the repro does not export).
