# H3-08: the labelled-mass-ratio rule reads gallons and gram-moles as grams

**Statement.** `units.normalize` takes any word that starts with `g` as a labelled gram, so `g/gal`, `gal/g`, `g/gmol`, `gmol/g`, `g gal-1`, `gal g-1`, `g/gallon`, `gpm/gpm` and `g/gpm` all normalise to the yield unit `g g⁻¹` and convert 1:1 into `kg kg⁻¹` (1000:1 into `mg g⁻¹`), and a candidate of 0.45 on "0.45 g/gal" anchors as an ethanol yield of 0.45 g g⁻¹ (`valueBasis 'exact'`) and is stored `verified` by `biorepo.write`; the browser's `normalizeUnit` holds the same two patterns.

## Contract

- `core/openferment_core/units.py:24-27`: "Raises rather than guesses. An unknown unit is `UnitError`, an incompatible pair is `UnitError`, and a pair the engine refuses on principle (`% TSP` to `g/L`) is `UnitError` carrying the recorded reason. Nothing here invents a conversion factor."
- `core/openferment_core/units.py:104-105`, the rule's own scope: "Grams per gram with each gram labelled by what it weighs: g EtOH/g glucose, gx/g, gDW gglucose⁻¹, g biomass [g glucose]⁻¹."
- `src/engine/units.ts:363-366`, the browser's twin: "Grams per gram with each gram labelled by what it weighs ... Each gram must stand alone after its separator".
- `CLAUDE.md:54` (R): "A record's value stands inside the verbatim quote it anchors to, in a unit its field is denominated in".
- `core/openferment_core/schema/fields.yaml:200-201`, `biomass_yield_substrate`: "a yield per mole or per C-mole, belong to no field." `g/gmol` is a per-mole quantity, and the engine files it under `yield`.

The engine holds no gallon, gram-mole or gallons-per-minute unit: `normalize('gal')`, `normalize('gmol')` and `normalize('gpm')` each return None, and `g mol-1` reads as `g mol⁻¹` in the family `molarMass`. A spelling built from them is therefore an unknown unit under the contract, and the 1:1 factor `convert` applies to it is one the engine invents.

## Command

```
bash bughunt/repro/H3-08/run.sh
```

From the repository root. It makes a fresh test database `bh_r_h3_08_units` (migrated to head) and drops it on exit; no service, no model call, no network. `repro.py` runs with the repository's Python, keyless: part A asks `units.normalize`, `units.family` and `units.convert` about nine probe spellings beside nine controls; part B sends 0.45 `g/gal` for `ethanol_yield_substrate` through `validate.anchor_candidate`, beside a `g/furlong` control; part C keeps the anchored candidate in a project of the fresh database and sends a reviewer's accept through `biorepo.write`, then reads the `openferment.records` row back. `browser.ts` runs `src/engine/units.ts` under `tsx` on the same spellings.

## Expected

The rule's own examples (`g/g`, `g EtOH/g glucose`, `gx/g`, `gDW gglucose⁻¹`, `g biomass [g glucose]⁻¹`) normalise to `g g⁻¹`. Each spelling holding gallons, gram-moles or gallons per minute returns None, as `gal`, `gmol`, `gpm` and `g/furlong` do; `convert` raises `UnitError` ("Unknown unit") for `g/gmol`, `gal/g` and `g/gal`; anchoring refuses 0.45 `g/gal` for `ethanol_yield_substrate` on rule `unit`, as it refuses 0.45 `g/furlong`.

## Observed (both runs, `run1.log` and `run2.log`)

- Controls held: the five labelled grams read as `g g⁻¹`; `gal`, `gmol`, `gpm` and `g/furlong` read as None.
- Nine of nine probes normalise to `g g⁻¹`, family `yield`: `g/gal`, `gal/g`, `g/gmol`, `gmol/g`, `g gal-1`, `gal g-1`, `g/gallon`, `gpm/gpm`, `g/gpm`.
- `convert(180.16, 'g/gmol', 'g g⁻¹') = 180.16`; `convert(1, 'gal/g', 'kg kg⁻¹') = 1.0`; `convert(1, 'g/gal', 'mg g⁻¹') = 1000.0`.
- 0.45 `g/gal` on "The broth held 0.45 g/gal of residual ethanol at harvest." ANCHORED as 0.45 g g⁻¹ with `valueBasis 'exact'`; the `g/furlong` control is refused on rule `unit` ("does not normalise").
- `biorepo.write` stored the accept with provenance `verified`; the row reads `ethanol_yield_substrate | 0.45 | g g⁻¹ | verified | The broth held 0.45 g/gal of residual ethanol at harvest.`
- The browser's `normalizeUnit` names `g g⁻¹` for nine of nine probes, and its `convert` gives 180.16 and 1 for the same two pairs.

## Likely cause

`core/openferment_core/units.py:108-111`: each gram in `LABELLED_MASS_RATIO` is `g(?:\s*[a-z]+)?`, so a label may join the `g` with no space, and `gal`, `gallon`, `gmol` and `gpm` each match as `g` plus a label (`al`, `allon`, `mol`, `pm`). `units.py:144-145` then returns `g g⁻¹` for the whole spelling. The browser holds the same two patterns at `src/engine/units.ts:369-372`, read at `:390`. A small fix: keep a label joined with no space from spelling a unit word (`al`, `allon`, `mol`, `pm` among them), in both files, with a fixture pair for each.
