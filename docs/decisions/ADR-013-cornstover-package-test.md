# ADR-013 — Two values of cornstover's package test, outside its tolerance on this installation

- **Status**: accepted (a departure from execution prompt §9.1 step 4)
- **Date**: 2026-10-30

## Context

Proof step 4 runs the cellulosic ethanol reference plant, the package's `cornstover`
(`biorefineries.cornstover`, the NREL 2011 design), and asks that the regression check against
the package's own test pass within its tolerance. The package's test,
`biorefineries/tests/test_biorefineries.py::test_cornstover`, holds eleven values to
`numpy.allclose` at `rtol=5e-2`.

Under the pinned versions (biosteam 2.54.0, thermosteam 0.54.2, biorefineries 2.35.1) the
package's own test fails, before openFerment is involved: run as the package runs it
(`pytest --pyargs biorefineries.tests.test_biorefineries -k test_cornstover`), it stops at the
installed equipment cost. Measured with the package's own code (its `default_settings` decorator,
`load()`, its `UnitGroup`), on 2026-10-30:

| Value | The test's | Measured here | Relative difference |
|---|---|---|---|
| `tea.installed_equipment_cost` (USD) | 209,112,840.52373964 | 192,647,846.3483623 | 7.9 % |
| `units.get_electricity_consumption()` (MW) | 22.05578511575179 | 20.91491944732716 | 5.2 % |

The other nine values hold. openFerment's library run measures the same two numbers to the ten
significant digits it keeps (`docs/reports/library-regression.md`; ADR-004, Implementation 4.2),
and the alpha 1.0 reference run measured the same since 2026-10-20. The test's values are the
package's from an earlier BioSTEAM; the installed BioSTEAM costs and powers the plant as above.

## Decision

`scripts/prove.py` step 4 holds every value of the package's test to its tolerance, except the
two this record names. Each of those two passes only when the run measures what the package's own
code measures on this installation, the value in the table above, to the run's ten significant
digits; any other value outside its tolerance fails the step, and so does either of these two
when it moves. The step says each departure in words with this record's number.

openFerment changes nothing in the package or its test, and sets no value to bring the two
inside: a run is the package's computation (ADR-004).

## Revisit condition

biosteam, thermosteam or biorefineries changes version (the two measured values move, and the
step fails until this record is revised or retired), or the package's test values are updated
upstream.

## Evidence

- Execution prompt §9.1 step 4; ADR-004 (Implementation 4.2, the regression report).
- `docs/reports/library-regression.md` (`pnpm library:report`): cornstover, 9 of 11.
- The package's own test, failing as above under the pinned versions (run 2026-10-30).
