# H3-04: measured evidence for a deposition the project does not hold is kept and read as measured

**Statement.** The service keeps a measured-evidence row whose `depositionId` names no deposition of the
project, with the value, the provenance `measured` and the `confirmed: true` the page sent. The runbooks
module read then marks the row `measured`, and Postdoc's validator grades a claim that cites it `measured`,
the strongest class in `PROVENANCE_ORDER`.

## Contract

- `CLAUDE.md:53`: "Code alone computes provenance, from inputs and origins (`basis.py`; ADR-006)."
- `docs/decisions/ADR-006-quantities-and-estimates.md:21-22`: "Provenance is computed from origins by code
  (`basis_provenance`, `weakest_provenance`, the client's display of the server's answer), never set by a
  model or a person."
- `docs/decisions/ADR-006-quantities-and-estimates.md:242-243` (the C.5 note) describes the row as "the
  measured evidence a reconciliation released (kind `measured-evidence`, marked `unverified` where nobody
  read its number back)". Here no reconciliation of the project released it, and no deposition holds it.

## Command

From the repository root:

    bash bughunt/repro/H3-04/run.sh

It makes a fresh database `bh_r_h3_04_svc` and starts a keyless service on the first free port of
9920..9929. It makes project p1, which holds nothing at the bench. Then it runs `repro.py`, which takes
these steps:

1. It reads p1's depositions, runbooks and readings. All three are empty.
2. It sends `PUT /api/state/measuredEvidence/me2` with `depositionId` `nope`, `runbookId` `nope`, 999 g/L,
   `provenance` `measured` and `confirmed` `true`.
3. It reads the row back with `GET /api/state`.
4. It reads the row with `POST /api/tools/runbooks_read`, ids `runbooks/measured-evidence/me2`.
5. It runs `validate_plan` in process, with no model and no network, on one claim whose `moduleRefs` cite
   that row. The claim's words hold no number.

The service is then stopped, the database dropped and the data copy removed. No worktree is needed, since
nothing is mutated or built.

## Expected

The write of me2 is refused in words with a 422, because p1 holds no deposition `nope` (and no runbook
`nope`). A measured-evidence row is held to a deposition, an entry and a reconciliation the project keeps,
and code computes its mark from that deposition's confirmed readings.

## Observed (run1.log and run2.log, both RESULT: DEFECT)

- `PUT` answers 200.
- `GET /api/state` keeps me2 at 999.0 g/L, provenance `measured`, confirmed `true`, depositionId `nope`.
  The same read shows p1 holding no depositions.
- `runbooks_read` returns `runbooks/measured-evidence/me2` with provenance `measured`, value 999.0 g/L,
  label "Ethanol titre, measured in deposition nope".
- `validate_plan` keeps the claim with provenance `measured`.

## Likely cause

- `core/openferment_core/module_stores.py:475-476`. The mark is the row's own field:
  `own = m.get("provenance") if m.get("provenance") in ("measured",) else None` and
  `mark = own if m.get("confirmed") is True else "unverified"`. Both inputs come from the page.
- `core/openferment_core/project_state.py:214` (`_checked`) and `:573` (`_put`). The write is read as
  `MeasuredEvidence` and passed through `refuse_estimates` alone. Nothing looks up `depositionId`,
  `runbookId` or a reconciliation in the project. The deposition branch at `:586-592` has no
  measured-evidence counterpart.
- The page sets the mark itself: `src/store.ts:2458` (`provenance: 'measured'`) and `:2465`
  (`confirmed: delta.confirmed`). The service keeps it as sent.
- `core/openferment_core/validate.py:469` carries the row's mark into a claim's class.
