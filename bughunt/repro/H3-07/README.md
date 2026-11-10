# H3-07: the unit engine folds an upper-case SI prefix onto the lower-case one

**Statement.** `units.normalize` lower-cases a spelling before its alias lookup and compares it case-blind against every table key, so `Mg` (megagram, the tonne biomass papers write) and `MG` read as `mg`, `ML` (megalitre) as `mL`, `Mm` and `MM` as millimolar, `S` (siemens) as seconds and `G` as grams; `convert(1, 'Mg', 'kg')` answers `1e-06` (a megagram is 1000 kg), the lesson catalogue keeps a numeric answer of 2 Mg, and the Primer grades "2000 kg" wrong and "2 mg" correct against it. The browser's `normalizeUnit` folds the same seven spellings the same way.

## Contract

- `core/openferment_core/units.py:24-27`: "Raises rather than guesses. An unknown unit is `UnitError`, an incompatible pair is `UnitError`, and a pair the engine refuses on principle (`% TSP` to `g/L`) is `UnitError` carrying the recorded reason. Nothing here invents a conversion factor."
- `core/openferment_core/catalogues.py:143-146`, the lesson answer's own field: "its unit (empty for a pure number, else one the unit converter reads, so an answer in any unit of its family grades)". A 2 Mg answer grades against milligrams.

The table holds no megagram, megalitre, megametre, megamolar, siemens or gauss key, and the engine refuses `Mg/d` and `ML/d` as unknown. `Mg`, `ML`, `Mm`, `S` and `G` are therefore unknown units under the contract, and the fold that answers `1e-06` for a megagram in kilograms applies a factor the table never states (off by 10⁹).

The case-blind step is designed: `units.py:123-128` names "a superscript-blind, middot-blind, case-blind comparison against every key", and the fixture's inputs fold `'G L-1'` and `'KDa'` on purpose (`scripts/export-unit-fixtures.ts:84` and `:99`, "wrong case"). Those two land where the other case spells no SI unit. In SI the case carries the unit: `M` is mega and `m` milli, and `S` and `G` name units of their own, so the same fold over `Mg`, `ML`, `Mm`, `S` and `G` lands on a unit 10⁹ or 10⁻⁹ away, or in another dimension.

## Command

```
bash bughunt/repro/H3-07/run.sh
```

From the repository root. It makes a fresh test database `bh_r_h3_07_svc` (migrated to head), starts the service on 127.0.0.1:9390 over it, keyless and with no worker, and makes the project `h3-07`. `repro.py` runs with the repository's Python: part A asks `units.normalize`, `units.family`, `units.convert` and `units.quantity_equals` about seven probe spellings beside eleven controls; part B keeps a lesson whose numeric answer is 2 Mg through `POST /api/catalogues/lesson`, reads it back, and sends a 2 Mg/d answer as the control. `browser.ts` runs `src/engine/units.ts` under `tsx` on the same spellings and makes the Primer's grading call (`parseQuantity`, then `quantityEquals`, as `src/screens/PrimerLesson.tsx:51-54` does). On exit the service stops, the database is dropped and the data copy is removed.

## Expected

`normalize` returns None for `Mg`, `MG`, `ML`, `Mm`, `MM`, `S` and `G`, as it does for `Mg/d`, `ML/d` and `furlongs`; `convert(1, 'Mg', 'kg')` and `convert(1, 'ML', 'L')` raise `UnitError` ("Unknown unit"); the lesson door refuses a 2 Mg answer with a 422, as it refuses 2 Mg/d. Were megagram held, `convert(1, 'Mg', 'kg')` would answer 1000.0 and "2000 kg" would grade as 2 Mg.

## Observed (both runs, `run1.log` and `run2.log`)

- Controls held: `mg`, `mL`, `mm`, `s`, `g` and `t d⁻¹` read as themselves; `Mg/d`, `ML/d` and `furlongs` read as None; the designed folds `G L-1` and `KDa` read as `g L⁻¹` and `kDa`.
- Seven of seven probes fold onto another unit: `Mg` and `MG` to `mg` (mass), `ML` to `mL` (volume), `Mm` and `MM` to `mmol L⁻¹` (molar), `S` to `s` (time), `G` to `g` (mass).
- `convert(1, 'Mg', 'kg') = 1e-06`; `convert(2, 'Mg', 'g') = 0.002`; `convert(1, 'ML', 'L') = 0.001`; `convert(1, 'Mg/d', 'kg d⁻¹')` raises "Unknown unit: Mg/d".
- `quantity_equals((2000, 'kg'), (2, 'Mg'), 5)` is False and `quantity_equals((2, 'mg'), (2, 'Mg'), 5)` is True.
- `POST /api/catalogues/lesson` keeps the 2 Mg answer (HTTP 200) and the read-back holds unit `'Mg'`; the 2 Mg/d answer is refused (HTTP 422, "the converter reads no 'Mg/d'").
- The browser's `normalizeUnit` folds the same seven probes to the same keys, its `convert` gives 0.000001 and 0.001 for the same two pairs, and the Primer's grading call marks "2000 kg" wrong and "2 mg" correct against the 2 Mg answer.

## Likely cause

`core/openferment_core/units.py:135-139`: `lower = t.lower()` reaches the lower-case aliases `"ml": "mL"` and `"mm": "mmol L⁻¹"` (`schema/units.json:511` and `:506`) for `ML`, `Mm` and `MM`. `units.py:140-143` then compares `_strip(t)` against `_strip(key)` for every key, and `_strip` ends in `.lower()` (`units.py:117`), so `Mg`, `MG`, `S` and `G` meet the keys `mg`, `s` and `g`. The browser holds the same steps at `src/engine/units.ts:377-379` and `:384-389`. The callers trust the answer: the lesson answer's validator (`catalogues.py:156-161`) asks only that `normalize` names a key, and the measurement lookup converts a reading's unit through `units.convert` (`measurements.py:204`). A small fix in both files: skip the lower-cased alias and the case-blind comparison for a spelling that opens with an upper-case SI prefix or unit symbol (`M`, `G`, `S`), with fixture pairs for `Mg`, `ML`, `Mm`, `S` and `G` each reading None.
