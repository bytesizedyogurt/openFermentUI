# H1-04: a scenario flowsheet run keeps a base price its own samples contradict, and its replay differs

**Statement.** A biosteam run of `ethanol_glucose_v0` with six fixed values prices its base case
(the first case the Proforma worker evaluates after it builds the plant) at 6.360 USD/kg and every
one of its 500 samples of the same six inputs at 7.372 USD/kg, and a replay of the kept artifact in
the same service answers 7.372 with 51 differences, where the thing's stated precision is `rtol` 0,
`atol` 0.

## Contract

- `docs/api/engines.md:616-618`: "A scenario flowsheet's is `rtol` 0, `atol` 0: `proforma.run`
  registers no tolerance, so its replay holds every output identically."
- `docs/api/engines.md:936` (conformance check 4): "A replay holds every output within the
  precision the thing states".
- `core/openferment_core/proforma.py:1517-1518`: "proforma.run registers no replay tolerance, so
  each replays identically: its precision is rtol 0, atol 0."
- `core/openferment_core/flowsheets/ethanol_glucose_v0.py:220-224`: "The recycle (the sieves'
  regenerate back to the rectifier) converges from where the last case left it, so the answer
  would depend on what ran before. Empty it, so a case gives one answer whatever came first".

## Command

From the repository root:

    bash bughunt/repro/H1-04/run.sh

It makes the test database `bh_r_h1_04_svc` fresh, starts the head's own service keyless on a free
port of 9000-9009, makes a project, asks `POST /api/engines/biosteam/run` for `ethanol_glucose_v0`
with six `person-assumption` values and no range (so every sample is `fixed` at the base case's
inputs), replays the kept artifact in the same service, then restarts the service over the same
database and replays it once more in a fresh worker. It stops the service and drops the database
on exit. About 75 s.

## Expected

Every sample of the six fixed inputs prices as the base case does (each quantile equal to
`basePrice`), and a replay is identical (`identical` true, no differences).

## Observed (run1.log and run2.log, the same both times)

- Stated precision, as `GET /api/engines` serves it: `{'rtol': 0.0, 'atol': 0.0}`.
- Run `4f2ccc41f73b2f66`, 500 samples, 500 feasible: `basePrice` 6.36040554632803 USD/kg;
  quantiles p5, p25, p50, p75 and p95 all 7.371976772110385.
- Replay in the same service: `identical` false, `withinTolerance` false, 51 differences,
  `basePrice` 6.36040554632803 -> 7.371976772110385, `baseCostLines.capex` 1.1304 -> 1.2981,
  `baseCostLines.labor` 2.3553 -> 2.7371.
- Replay after a restart (the replay's base case is again the first a fresh worker evaluates):
  `identical` true, no differences. The answer a person gets for one artifact thus depends on
  whether the service's Proforma worker has built the plant before.
- RESULT: DEFECT on both runs.

## Likely cause

- `core/openferment_core/workers/proforma_worker.py:191-202` keeps one built plant per flowsheet
  (`_BUILT`), and `run` (`proforma_worker.py:539-558`) evaluates the base case, the grid and every
  sample on it in turn, so the base case of a run in a fresh worker is the plant's first case and
  every sample a later one.
- `core/openferment_core/flowsheets/ethanol_glucose_v0.py:225-227` empties the recycles and
  simulates under BioSTEAM's default recycle tolerances, which this build leaves as BioSTEAM sets
  them (`molar_tolerance` 1 kmol/h, `relative_molar_tolerance` 0.01, measured on the built
  system). At 1000 t/yr the sieves' recycle `s9` carries about 1.0 to 1.2 kmol/h, inside that
  tolerance, so the loop `SYS4` stops early: two iterations on the first case after a build
  (its streams still at 101325 Pa), one on every later case. The supporting probe
  `mass_balance.py` shows the later cases leave the recycle out of the balance: the fermenter
  makes 126.263 kg/h of ethanol, 105.904 kg/h leaves the plant, and the 20.358 kg/h in `s9` never
  reaches the mixer's outlet `s5` (125.585 kg/h, the distilled beer's own).
- Confidence: high on the numbers (two runs, identical); high on the cause. A probe that sets the
  system's and its subsystems' `molar_tolerance` to 1e-6 and `relative_molar_tolerance` to 1e-9
  gives 6.196322 USD/kg on every case, the fresh build's first included, so both the base price
  6.360 and the samples' 7.372 are prices of an unconverged recycle (2.6 % and 19 % above it).
- Reach: the same probe at 10000 t/yr gives 2.031950 on the first and the second case (a
  repeatable answer) with 1.979942 converged; at 100000 t/yr, the scale `test_proforma.py`'s
  `ETHANOL_STANDIN` runs at, all three agree at 1.460135. The suite's replay test therefore runs
  at a scale where the recycle sits far above the tolerance.

## Files

- `run.sh`: the reproduction. `run1.log`, `run2.log`: its two runs.
- `mass_balance.py`: the supporting probe of the cause (the worker's own `evaluate` twice in one
  process, keyless, no database), run with
  `source bughunt/lib/env.sh; bh_py ../bughunt/repro/H1-04/mass_balance.py`.
