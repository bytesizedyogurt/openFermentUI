# H3-14: the Released to BioRepo band draws a value nobody read back as measured

**Statement.** After a reconciliation on the deposition screen, the "Released to BioRepo" band draws every
released value under a "Measured · first-party" badge with a `tick-measured` tick (screen-reader label
"Measured · first-party."), the one nobody read back included, while the runbooks module read marks that same
row `unverified`.

**Contract.**

- `docs/decisions/ADR-006-quantities-and-estimates.md:242-243`: "and the measured evidence a reconciliation
  released (kind `measured-evidence`, marked `unverified` where nobody read its number back)".
- `docs/decisions/ADR-006-quantities-and-estimates.md:21-22`: "Provenance is computed from origins by code
  (`basis_provenance`, `weakest_provenance`, the client's display of the server's answer), never set by a model
  or a person."
- `core/openferment_core/module_stores.py:469-471` (`_measured_row`): "Marked as the bench marks it
  (`measured`) where a person read its number back, and `unverified` where nobody did, as the lookup takes no
  unconfirmed number as a measurement."

**Command** (from the repository root; exits 0 either way):

    bash bughunt/repro/H3-14/run.sh

It makes a fresh test database `bh_r_h3_14_released`, starts the keyless service on the first free port in
10000-10009 over the built `dist/`, makes project `h3-14` with one runbook (two predictions, each tested by one
measure) and one closed deposition (reading `e1` read back, reading `e2` never read back), opens
`#/p/h3-14/runbooks/depositions/dep1` in Chromium and presses the screen's own "Record as inconclusive" button.
The browser releases two measured values to the service. The script then asks `POST /api/tools/runbooks_read`
for both rows, reloads the screen, reads the band's badge, each item's tick class and screen-reader label, and
stops the service and drops the database. `screen.cjs` holds the browser steps; `screen.png` is the last run's
page.

**Expected.** The released value nobody read back drawn with the class the service gives it: `runbooks_read`
answers `unverified` for it, so a `tick-unverified` tick ("Extracted · unverified"), as the same screen's
Measured band and reconciliation panel already warn of an unconfirmed reading. The read-back value stays
`measured`.

**Observed** (run1.log and run2.log, both `RESULT: DEFECT`):

    SERVICE: runbooks_read runbooks/measured-evidence/me-…-1 provenance=measured confirmed=true
    SERVICE: runbooks_read runbooks/measured-evidence/me-…-2 provenance=unverified confirmed=false
    SCREEN: band badge "Measured · first-party"
    SCREEN: "Titre read back" tick=tick-measured sr="Measured · first-party." …
    SCREEN: "Titre never read back" tick=tick-measured sr="Measured · first-party." … caption="with no protocol’s steps · unconfirmed"

The caption carries " · unconfirmed" for the unread value; its badge, tick colour, tooltip and screen-reader
label say measured, first-party.

**Likely cause** (confidence high).

- `src/screens/DepositionDetail.tsx:511` `<ProvenanceBadge p="measured" />` and `:516` `<Tick p="measured">`:
  the class is fixed for every released value, whatever `e.confirmed` holds; `:534` adds the caption's " · unconfirmed".
- Contributing: `src/store.ts:2458` (`reconcileDeposition`) writes `provenance: 'measured'` on every released
  value, `confirmed: delta.confirmed` beside it, so the kept row's own `provenance` field says `measured` for
  the unread one too (the table read in the logs shows `me-…-2 | this browser | false | measured`). The module
  read computes `unverified` from `confirmed` (`core/openferment_core/module_stores.py:475-476`).

**Severity** S3 (Inconsistency, fix small): the provenance class on the screen disagrees with the service's
answer for an unconfirmed released value; the caption's " · unconfirmed", the screen's Measured band and the
module read each still say what the value is.
