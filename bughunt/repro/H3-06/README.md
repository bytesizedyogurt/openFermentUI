# H3-06: a kept run on a reading reads `measured` after the reading is corrected

**Verdict: not reproduced as a defect.** The behaviour the candidate saw is real, and it is the behaviour
the contract's words describe.

## Statement (the candidate's)

A run measured on a reading keeps the label `measured` on `GET /api/runs/{id}` and the runs list after that
reading is corrected, while every door now refuses the reading as corrected, and a run on a record follows
that record's demotion.

## The contract it was said to break

- `docs/api/runs.md:22`: "A row held done follows its artifact's provenance when a record the basis rests on
  is reviewed or demoted since (Keeping a run, below)."
- `docs/decisions/ADR-006-quantities-and-estimates.md:238` (and `docs/api/studies.md:106-107`, word for
  word): "A run looks its readings up again each time it runs, and refuses in words one corrected since."

What those lines say, read closely:

- `runs.md:22` names a *record* reviewed or demoted. The line before it, `runs.md:21`, sets the two apart:
  "`deposition` naming one reading is `measurement` and a series `record`". A single reading that a later
  entry corrects is a `measurement`, and no record is reviewed or demoted. `runs.md:149-180` (Keeping a run)
  also places the follow at the moment the run is asked again (`compute_kept`: "a row held done answers its
  artifact, whose provenance `artifacts.compute` brings up to date when a record ... was reviewed or demoted
  since"). A plain `GET /api/runs/{id}` reads the stored row for a record's run as well
  (`core/openferment_core/engine/runs.py:316-320`, `387-394`).
- ADR-006:238 promises the refusal "each time it runs". A `GET` of a kept row is no run. The run asked
  again is refused in words (step 5 below).
- The provenance rule itself (`ADR-006:193-195`, `runs.md:22`): "`measured` when any input is a
  measurement". The kept row's input is still the reading depK/k0 a named person deposited and confirmed,
  and the label states that basis truthfully. No line in `runs.md`, `studies.md`, `engines.md` or ADR-006
  names a label, or a mark, for a kept run whose reading a later entry has corrected.

## Command

```
bash bughunt/repro/H3-06/run.sh
```

It makes a fresh database `bh_r_h3_06_svc`, starts a keyless service on the first free port of 9090..9099,
makes project p1 and runs `repro.py`. The kinetics engine computes in the service's process, so no worker
starts and no model is called. When it finishes it stops the service, drops the database and removes the
service's data copy. It needs no worktree, since nothing is mutated or built.

Steps:
1. Deposit depK with nine confirmed readings by Ada Lovelace. Run kinetics `batch_v1` on all nine
   (`POST /api/engines/kinetics/run`).
2. Read the kept row (`GET /api/runs/{id}` and `GET /api/runs`).
3. Correct depK/k0 (0.0125 min⁻¹) with a later entry depK/k0fix (0.00125 min⁻¹, `correctedAt`), the
   bench's correction.
4. Read the kept row again.
5. Ask for the same run again, the same request.
6. Send depK/k0 to the Proforma resolve door, then fetch the readings list in h⁻¹.

## Expected (by the contract's words)

The same run asked again after the correction is a 422 in words naming the correction (ADR-006:238). The
other doors refuse depK/k0, and the readings list leaves it out. No line moves the kept row's label on a
reading's correction.

## Observed (run1.log, run2.log)

- Before the correction, the kept row 90e308503f0ddc1c reads `measured` on `GET /api/runs/{id}` and in
  the runs list. Its mu_max input's origin is `measurement depK/k0`.
- After the correction the kept row still reads `measured`, in both places, with the same origin. This
  matches what the candidate saw.
- The same run asked again: `422 {"detail":"mu_max: reading depK/k0 was corrected by depK/k0fix, the
  reading that stands for its measure now"}`.
- The Proforma resolve door on depK/k0: the same 422 words. The readings list offers `['depK/k0fix']` alone.
- `RESULT: NO-DEFECT` on both runs.

## The code the candidate named

`core/openferment_core/artifacts.py:298-309` recomputes a stored artifact's provenance when the computation
is asked again (records and artifacts). `core/openferment_core/basis.py:277-278` gives a `deposition` source
`measured` whatever the reading's standing now. The standing is checked at the lookup
(`core/openferment_core/measurements.py:172-177`), before anything runs, which is what ADR-006:238 asks
for. The asymmetry the candidate describes follows from that design. A run on a record can be asked again
after a demotion, and `engine/runs.py:553-554` then moves its row. A run on a corrected reading is refused
when asked again, so its row keeps the label its basis earned. This is a design gap the owner may want to
close, for example by marking a run whose reading no longer stands. That would be a new rule in ADR-006, and
the current contract carries no such rule.
