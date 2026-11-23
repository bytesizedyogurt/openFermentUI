# H3-03: a released measured value is rewritten by a later write, unaudited, and served as measured

**Statement.** `PUT /api/state/measuredEvidence/me1` with the same id a second time replaces the released
value whole (40 g/L to 400 g/L, sent by another person) with a 200 and no audit row, and `GET /api/state`, the
runbooks module read and the deposition screen then serve 400 g/L as measured, while the deposition's own
reconciliation still says 40 g/L was observed.

## The contract it breaks

- `core/openferment_core/project_state.py:30-33`: "What a person made, locked, measured or asked stays: a
  deposition, a measurement, a lock and a conversation are never taken back through here. Making, locking and
  taking back are audited".
- `core/openferment_core/project_state.py:130`: "Whether a person may take a row back (a deposition, a
  measurement and a lock stay)." `:143` gives `measuredEvidence` `removable=False` as that measurement.
- `src/lib/projectState.ts:86-88`: "a deposition or a measurement is never taken back."
- `src/screens/DepositionDetail.tsx:541`, under the band it draws the released values in: "These are records
  with their conditions attached".

The hunt also cites `docs/decisions/ADR-006-quantities-and-estimates.md:231-238` and
`src/screens/DepositionDetail.tsx:46` ("The record is append-only: corrections add, nothing overwrites."). Both
speak of a deposition and its readings; the service holds a deposition to them, as step 3 below shows, and
the measured evidence a reconciliation releases from that deposition gets no such hold.

## Command

```
bash bughunt/repro/H3-03/run.sh
```

From the repository root. It makes the database `bh_r_h3_03_svc` fresh, starts a keyless service on the first
free port of 9903..9909 (then 9900..9902), makes project p1, and runs `repro.py`:

1. a runbook rb1;
2. a closed, reconciled deposition dep1 whose reading e1 is 40 g/L (its reconciliation observed 40 g/L);
3. the contrast: dep1 written again with e1 at 400 g/L by "Someone Else" (the service refuses it, 422);
4. the measured evidence me1 the reconciliation released, 40 g/L, by "Ada Lovelace";
5. me1 written again with 400 g/L by "Someone Else";
6. to 9. `GET /api/state`, `GET /api/audit?target=me1`, the `runbooks_read` tool on
   `runbooks/measured-evidence/me1`, and `DELETE` of me1;
10. `screen.cjs` opens `#/p/p1/runbooks/depositions/dep1` from the built `dist/` in Chromium and prints the
    "Released to BioRepo" band (screenshot `screen.png`).

It then stops the service, drops the database and removes the data copy. `RESULT: DEFECT` when step 5 answers
200, the state keeps 400 g/L, and the audit holds no row for the second write.

## Expected

The second write of me1, changing a kept measured value, is refused in words with a 422, as the deposition's
reading is at step 3 (`deposition_refusal`), or at the least it is audited with who made it. The reads keep
40 g/L, the value the deposition's reconciliation observed.

## Observed (both runs)

- Step 3: 422 "dep1: reading e1 keeps the value it was taken with (40.0), and this write sets 400.0; a
  correction is a new reading".
- Step 5: 200, value 400.0, provenance measured, confirmed true.
- `GET /api/state`: me1 at 400.0 g/L marked measured; dep1's reading e1 and its reconciliation still 40.0.
- `GET /api/audit?target=me1`: one row, `keep_measuredEvidence` by Ada Lovelace; nothing names Someone Else.
- `runbooks_read`: `runbooks/measured-evidence/me1` provenance `measured`, value 400.0 g/L.
- `DELETE me1`: 422 "a measuredEvidence is kept as it was made, and never taken back".
- The deposition screen: "Released to BioRepo 1 Measured · first-party ... Ethanol titre 400 g/L".

## Likely cause

- `core/openferment_core/project_state.py:143`: `measuredEvidence` is a `Kind` with `removable=False` and no
  write rule; `removable` is read by `remove` alone (`:667`).
- `core/openferment_core/project_state.py:586-592`: the held-row check (`deposition_refusal`, `:292`) runs for
  `kind == "depositions"` alone.
- `core/openferment_core/project_state.py:611`: every other kind goes to `rows.put`, which writes the row whole
  and replaces the body on conflict (`core/openferment_core/db/rows.py:59-66`, `on_conflict_do_update`).
- `core/openferment_core/project_state.py:614`: the audit row is written when the row did not exist before, so
  the second write leaves none.

The client writes a measured evidence once, at reconciliation (`src/store.ts:2449-2489`), and never rewrites
one, so a refusal of a changed body (or an insert-once write such as `rows.put_first`) would break no page.
