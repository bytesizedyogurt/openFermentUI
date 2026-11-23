# H4-06: cellulosic_ethanol_v0's ethanol outputs read the whole denatured product stream

**Statement.** A run of `cellulosic_ethanol_v0` reports `ethanolKgPerH` and `ethanolKgPerKgDryFeed` from the whole
mass of its product stream (Ethanol 21,314.6 + Denaturant 473.1 + Water 177.2 + NH3 13.4 = 21,978.4 kg/hr), which the
Comparison screen names "Ethanol made per hour" and "Ethanol per kg of dry feed", so the yield reads 0.2643 kg/kg
where the plant makes 0.2563 kg of ethanol per kg of dry feed (3.11 % high), and `ethanol_glucose_v0`'s output of
the same name reads the ethanol alone.

**Contract.**
- `src/screens/ProformaComparison.tsx:83`: `'outputs.ethanolKgPerH': 'Ethanol made per hour'`
- `src/screens/ProformaComparison.tsx:85`: `'outputs.ethanolKgPerKgDryFeed': 'Ethanol per kg of dry feed'`
- `core/openferment_core/flowsheets/cellulosic_ethanol_v0.py:325`: the outputs give "what the plant makes of its feed"
- `core/openferment_core/flowsheets/ethanol_glucose_v0.py:287`: the same key elsewhere,
  `"ethanolKgPerH": float(product.imass["Ethanol"])`, the ethanol in the product alone

**Command** (from the repository root): `bash bughunt/repro/H4-06/run.sh`

It makes a fresh database `bh_r_h4_06_run`, starts a keyless service on the first free port in 127.0.0.1:9710-9719,
makes one project, runs the library plant `cellulosic_ethanol_v0` once with no inputs (its default configuration,
"dilute acid, IB"), and sets the run's `outputs` beside its own `ethanol` stream; it reads the two screen words and
the two source lines from the tree. It then stops the service, drops the database and removes its data copy.
`judge.py` does the reading and prints EXPECTED, OBSERVED and RESULT.

**Expected.** "Ethanol made per hour" reads the ethanol in the product, 21,314.6 kg/hr, and "Ethanol per kg of dry
feed" 0.2563 kg/kg, as `ethanol_glucose_v0`'s `ethanolKgPerH` reads `product.imass["Ethanol"]`; or the two outputs
carry names and words for the denatured product stream they measure.

**Observed** (both runs, run `e7efa2505b4633de`). `outputs.ethanolKgPerH` 21,978.3753 kg/hr, the stream's whole
`massFlow`; `outputs.ethanolKgPerKgDryFeed` 0.264294 kg/kg over `dryFeedKgPerH` 83,158.8023; the stream's
`massFlows` Ethanol 21,314.5947, Denaturant 473.10, Water 177.23, NH3 13.45. Both outputs stand 3.11 % above the
ethanol the plant makes, and the screen names both "Ethanol".

**Likely cause.** `core/openferment_core/flowsheets/cellulosic_ethanol_v0.py:334` (`"ethanolKgPerH":
float(ethanol.F_mass)`) and `:336` (`float(ethanol.F_mass) / dry`), where `ethanol` is the package's product stream
after the ethanol-denaturant mixer M701. `float(ethanol.imass["Ethanol"])` gives the ethanol alone; the per-kg and
per-gallon prices stay on the product stream, the package's own basis.

**Logs.** `run1.log`, `run2.log`: each ends `RESULT: DEFECT`.
