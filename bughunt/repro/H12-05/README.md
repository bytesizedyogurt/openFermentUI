# H12-05: test_no_seed.py passes with typed science in the service and in src/data/

**Statement.** `core/tests/test_no_seed.py`, the test CLAUDE.md and ADR-011 name as the hold on "no composition, yield, price, titre, strain fact or paper's finding is typed in code or seed", passes with a service module typing a titre, a yield, a composition and a price and with a `src/data/` file exporting a yield table by strain; `test_boundaries.py` and `test_guidance.py` pass beside it.

## Contract

- `CLAUDE.md:11`: "R: The repository holds software alone: no composition, yield, price, titre, strain fact or paper's finding is typed in code or seed, and science arrives at run time through Intake and the library plants (§1 item 7; `core/tests/test_no_seed.py`, acceptance A4)."
- `docs/decisions/ADR-011-guards.md:16-17`: "`test_no_seed.py` holds acceptance A4."
- `docs/PROGRESS.md:510` (the A4 row): "`test_no_seed.py` holds what A4 names (each deleted module absent, no `.ts` under `src/data/` exporting content, the shipped stores empty)".
- The test's own docstring, `core/tests/test_no_seed.py:4-8`: "no file under src/data/ exports records, papers, products, strains, scenarios, protocols, runbooks or lessons".

## Command

From the repository root:

```
bash bughunt/repro/H12-05/run.sh
```

It makes a worktree of `2047f5a` under `bh/work/H12-05/`, links the repository's venv, makes the fresh database `bh_r_h12_05_db` (the tests' own session databases take the prefix `bh_r_h12_05_t`), and runs `test_no_seed.py` three ways:

1. the tree as it is (the baseline);
2. a control: `src/data/control.ts` exports `RECORDS`, a name the test's `SEEDED_NAMES` reads;
3. the plant: `core/openferment_core/typical_values.py` (`ETHANOL_TITRE_G_PER_L = 92.0`, `ETHANOL_YIELD_G_PER_G = 0.48`, `CORN_STOVER_GLUCAN_FRACTION = 0.35`, `ENZYME_PRICE_USD_PER_KG = 4.24`) and `src/data/yields.ts` (`export const TYPICAL_YIELDS = [{ strain, product, gPerG: 0.48, titreGPerL: 92, paper }]`), run alone and then with `test_boundaries.py` and `test_guidance.py`.

It removes the worktree and drops every database it made. Keyless, no service, no network.

## Expected

`test_no_seed.py` fails on the planted service module and on the `src/data/` file exporting a yield table by strain, as it fails on the control's `RECORDS` export.

## Observed (run1.log, run2.log)

- Baseline: 47 passed.
- Control: 1 failed, 46 passed (`AssertionError: ['src/data/control.ts: RECORDS']`), so the test runs on the worktree and its name pattern works.
- Plant: 47 passed for `test_no_seed.py`, and 69 passed for it with `test_boundaries.py` and `test_guidance.py`.

Both runs end `RESULT: DEFECT`.

## Likely cause

`core/tests/test_no_seed.py` holds the stage 1 deletion alone:

- `:24-68` lists deleted paths, and `:73` lists the three projection file names;
- `:75-78` and `:95-103`: a `src/data/` export fails only when its name matches `SEEDED_NAMES` (`RECORDS|PAPERS|PRODUCTS|STRAINS|...`) or its annotation names a seed type (`ExtractionRecord[]`, `Strain[]`, ...), so `TYPICAL_YIELDS`, untyped, passes;
- `:80` and `:116-124`: the one pattern read across the app and the service is the alpha 1.0 record id `r-X00-n`.

A number rule is held file by file elsewhere (`core/tests/test_proforma_ethanol.py:103-110` holds the Proforma flowsheet file to the numbers 0 and 1), and no test reads a typed number, a unit-bearing constant or a new export name across `core/openferment_core/` or `src/`, so a module added beside the named files goes unread. A4's clause on the service's code was measured once by hand with `rg` at stage 8 (`docs/PROGRESS.md:510`: "`src/` and the service's code hold none"), and nothing repeats it. The current tree types no such value (H12 grepped the service and found none), and a value typed later would reach the tree with every one of these tests green.

Confidence: high. Fix size: medium. A scan of numeric literals beside unit or science words in the service and the client needs an allowance for what `CLAUDE.md:12` counts as software (versions, ports, tolerances, unit-conversion factors, file hashes, the library's regression values read at run time).
