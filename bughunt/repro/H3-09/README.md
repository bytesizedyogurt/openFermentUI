# H3-09: the percent family converts percentages of different denominators 1:1

**Statement.** The unit table files `%`, `% DW`, `% v/v`, `% of native sites`, `% sedimentable`, `% of total expressed` and `% of total protein` in one family, `percent`, each at factor 1. Each therefore converts into every other 1:1 with no reason given. The table's own refusal row says two percentages of different denominators are a category error to compare. So a value quoted as 42 `% DW` (or `% v/v`, or `% of native sites`) anchors for `disruption_protein_yield`, a field denominated in `% of total protein`, is stored `verified` by `biorepo.write`, and reads back through `to_canonical` as 42 % of total protein. The same table refuses 42 `% TSP` for the same field, giving that reason.

## Contract

- `core/openferment_core/schema/units.json:558`, the refusal row `proteinShare` / `percent`: "Both are percentages but of different denominators — % of total soluble protein is not % of dry weight or % of native phosphorylation sites. Comparing them directly is a category error." (Mirrored at `src/engine/units.ts:152-155`.) The row names dry weight and native phosphorylation sites as two denominators, distinct from each other and from total soluble protein. By the row's own rule, % DW against % of native sites is a category error too.
- `core/openferment_core/units.py:24-27`: "Raises rather than guesses. An unknown unit is `UnitError`, an incompatible pair is `UnitError`, and a pair the engine refuses on principle (`% TSP` to `g/L`) is `UnitError` carrying the recorded reason. Nothing here invents a conversion factor." Between a volume fraction (`% v/v`) and a share of dry weight (`% DW`), a factor of 1 is invented: the two differ by the densities of what is measured.
- `CLAUDE.md:54` (R): "A record's value stands inside the verbatim quote it anchors to, in a unit its field is denominated in". `core/openferment_core/schema/fields.yaml:115-116`, `disruption_protein_yield`: "Protein released as a percentage of total cellular protein", `canonicalUnit: '% of total protein'`.

## Command

```
bash bughunt/repro/H3-09/run.sh
```

Run it from the repository root. It greps the table rows and makes a fresh test database, `bh_r_h3_09_units`, migrated to head and dropped on exit. It starts no service, calls no model and uses no network. `repro.py` runs with the repository's Python, keyless:

- Part A asks `units.convert`, `units.explain_refusal` and `units.quantity_equals` about six pairs of percentages with different denominators. It runs them beside the `% TSP` against `% DW` control the refusal row is written for.
- Part B sends 42 for `disruption_protein_yield` through `validate.anchor_candidate` in five units: `% of total protein`, `% DW`, `% v/v`, `% of native sites` and `% TSP`.
- Part C keeps the `% DW` candidate in a project of the fresh database and sends a reviewer's accept through `biorepo.write`. It then reads the record back and calls `units.to_canonical` on it.
- Part D prints the `wt%` alias.

`browser.ts` runs `src/engine/units.ts` under `tsx` on the same pairs.

## Expected

The table's own rule refuses these pairs. `convert` raises `UnitError` with a reason for `% DW` against `% of native sites`, for `% v/v` against `% DW`, and for the other pairs of different denominators, as it does for `% TSP` against `% DW`. `quantity_equals((5, '% DW'), (5, '% of native sites'))` is False. Anchoring refuses 42 `% DW`, `% v/v` and `% of native sites` for `disruption_protein_yield` on rule `unit`, as it refuses 42 `% TSP`.

## Observed (both runs, `run1.log` and `run2.log`, identical)

- Control: `convert(5, '% TSP', '% DW')` raises `UnitError`, and its reason is the category-error sentence of `units.json:558`.
- All six pairs return `5.0`, and `explain_refusal` gives None for each:
  - `% DW` to `% of native sites`
  - `% v/v` to `% DW`
  - `% DW` to `% of total protein`
  - `% of native sites` to `% of total protein`
  - `% sedimentable` to `% v/v`
  - `% v/v` to `% of total expressed`
- `quantity_equals((5, '% DW'), (5, '% of native sites'))` is True. This is the test Witness applies to a claim against a record (`witness.py:85`, `:117`).
- `disruption_protein_yield` anchored 42 in `% of total protein`, `% DW`, `% v/v` and `% of native sites`, each with `valueBasis 'exact'`. It refused 42 `% TSP` on rule `unit`, with the category-error reason.
- `biorepo.write` stored the `% DW` accept with provenance `verified`. The row reads `disruption_protein_yield | 42 | % DW | verified | Bead milling for 10 min gave a value of 42 % DW in the lysate.`, and `to_canonical(42.0, '% DW', 'disruption_protein_yield')` returns `42.0` (% of total protein).
- The browser's `convert` gives 5 for six of six pairs, with `explainRefusal` null for each, and `quantityEquals` is true.
- Part D: `wt%` and `% (w/w)` normalise to `% CDW` (family `percentCdw`), and `convert(35, 'wt%', '% DW')` raises with no reason. `docs/PROGRESS.md:614` already records this alias as an open debt, so the RESULT line leaves it out.

## Likely cause

`core/openferment_core/schema/units.json:123-137` (`%`, `% DW`, `% v/v`) and `:286-305` (`% of native sites`, `% sedimentable`, `% of total expressed`, `% of total protein`) give every one of these units `"family": "percent"` and `"factor": 1`. `units.convert` (`core/openferment_core/units.py:198-204`) refuses only across families, so units in one family convert by their factors. The refusal at `units.json:555-559` guards one family boundary (`proteinShare` / `percent`), and the denominators inside `percent` have no boundary. The browser holds the same rows at `src/engine/units.ts:51-53` and `:87-90`.

A small fix: give each denominator its own family, as `% TSP` and `% CDW` already have. Keep the bare `%` as the family of a field that takes the measure the paper names (`product_purity`, `step_recovery`). Add refusal rows in the words of `:558`, change both files, and add a fixture pair for each.

Confidence: high that the engine converts and anchors as shown. Medium that the owner wants each denominator split out, since no test or fixture pins a conversion inside `percent` either way.
