# H3-05: moving a correction's sample time makes the reading it corrected stand again

**Statement.** While a deposition is open, the service accepts a write that changes any entry's sample
time, and `corrected_by` finds a correction by matching the current sample times. So a write that moves a
correction to another hour, takes the corrected reading's hour away, or gives the correction alone its
first hour makes the mis-read it corrected stand again. The readings list then offers the mis-read, and
the lookup every door calls takes it as a confirmed `measurement`.

## Contract

- `docs/decisions/ADR-006-quantities-and-estimates.md:174-177`: "The entry is the reading that stands for
  its measure: a later entry on the same measure with no time of its own corrects an earlier one with
  none, and a reading in a series is its own, corrected by a later entry at its time alone".
- `docs/decisions/ADR-006-quantities-and-estimates.md:232-234`: "readings and observations are appended,
  each kept with the value, unit, time and words it was taken with (a correction is a new entry, keeping
  the time its reading was taken and saying when it was typed, `correctedAt`)".
- `docs/api/studies.md:58` (the Standing rule): "a later entry corrects it: on the same measure with no
  time of its own, for an entry with none; at its own time, for a reading in a series".
- `src/engine/readings.ts:7-9`: "The bench reads back the entries that stand, and the record says which
  entry corrects which, so the two pages and a run's lookup read one rule."
- `src/store.ts:2181-2183` (`amendEntry`): "A correction is the same reading: it keeps the time the reading
  was taken (`at`, the time a measurement names) and its sample time (§7.1)".
- `core/openferment_core/project_state.py:30`: "What a person made, locked, measured or asked stays".

The same records let an open deposition's sample times change: `project_state.py:296-297` ("give an open
deposition's readings their sample times") and ADR-006:236 ("closing stops new readings, observations and
sample times"). That permission and the correction rule share one key, the current sample time. Nothing
holds a correction to the reading it corrects once that key changes.

## Command

From the repository root:

    bash bughunt/repro/H3-05/run.sh

It makes a fresh database `bh_r_h3_05_svc` and starts a keyless service on the first free port of
10280..10289. It makes project p1, then runs `repro.py`, which sends these requests:

1. `PUT /api/state/runbooks/rb1`: one measure m1, the ethanol titre in g/L.
2. `PUT /api/state/depositions/dep9`, state running: s1 4.0 g/L (a mis-read), confirmed, `at` T0, sample
   time 5 h.
3. The same deposition with the bench's correction appended (the shape `correctionOf` and `amendEntry`
   write): s2 40.0 g/L, confirmed, the same `at`, `correctedAt` set, raw "4.0 g/L -> corrected to 40.0
   g/L", and the 5 h carried across to s2.
4. `POST /api/params/proforma:sc-h305/resolve` with titre 4.0 g/L, origin `measurement` `dep9/s1`. Then
   `GET /api/depositions/readings?unit=g L-1`.
5. The same deposition with `sampleTimes` `{s1: 5, s2: 6}`. Every entry is unchanged.
6. The resolve on `dep9/s1` again, and the readings list again.
7. The same deposition with s1's sample time taken away (`{s2: 6}`), and the resolve on `dep9/s1` again.
8. and 9. A second deposition dep10. s1 4.0 g/L is corrected by s2 40.0 g/L, and neither has a time. The
   resolve on `dep10/s1` is checked. Then a write gives s2 alone its 5 h, and the resolve runs again.

Steps 1 to 6 decide the result. Steps 7 to 9 are reported beside it. The service is then stopped, the
database dropped and the data copy removed. No worktree is needed, since nothing is mutated or built.

## Expected

Once s2 corrects s1, `dep9/s1` stays corrected whatever later writes do to the sample times while dep9 is
open. Two outcomes would hold the contract. The write in step 5 could be refused in words. Or the resolve
in step 6 could still be a 422 naming `dep9/s2`, with the readings list still leaving `dep9/s1` out.

## Observed (run1.log and run2.log, both RESULT: DEFECT)

- Step 4: the resolve is a 422, "titre: reading dep9/s1 was corrected by dep9/s2, the reading that stands
  for its measure now". The readings list offers `dep9/s2` 40.0 at 5 h alone.
- Step 5: the move of s2 to 6 h is a 200.
- Step 6: the resolve on `dep9/s1` is a 200. It sets the titre to 4.0 with origin `measurement`, source
  `deposition` `dep9/s1`. The readings list offers `dep9/s1` 4.0 g/L at 5 h beside `dep9/s2` 40.0 g/L at
  6 h.
- Step 7: taking s1's hour away is a 200, and `dep9/s1` is still taken (4.0, `measurement`).
- Steps 8 and 9: `dep10/s1` is refused while neither entry has a time. A write giving s2 alone its 5 h is
  a 200. After it, `dep10/s1` is taken as a 4.0 g/L `measurement` and offered untimed beside `dep10/s2` at
  5 h. That write is exactly the one the docstring allows ("give an open deposition's readings their
  sample times"). The bench captures readings with no sample time, and DepositionDetail's Time series
  panel then shows an hour box on every entry, the corrected one included.

## Likely cause

- `core/openferment_core/measurements.py:90-104` (`corrected_by`). The correction is found as a later
  entry on the same measure with `times.get(e.get("id")) == when` (line 103), read from the deposition's
  current `sampleTimes`. The record keeps no link from a correction to the entry it corrects, so a changed
  hour changes which entry stands.
- `core/openferment_core/project_state.py:321-327` (`deposition_refusal`). Sample times are held only once
  the deposition is closed (line 325). While it runs, any write to `sampleTimes` passes, including one
  that splits a correction from its reading.
- The client follows the same rule: `src/engine/readings.ts:13-22` (`correctedBy`), and
  `src/store.ts:2194-2204` (`setSampleTime`), which sets or deletes any entry's hour.
  `src/components/TimeSeriesPanel.tsx:72-83` offers the hour box on every entry of a running deposition.
