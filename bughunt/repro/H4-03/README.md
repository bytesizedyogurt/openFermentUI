# H4-03: a library run that sets any value is simulated a second time, so a value equal to the default moves the price in the fifth digit

**Statement.** A library run of cornstover that sets its feedstock price to the library's own default
(0.05158816935126135 USD/kg) is simulated a second time after the build's own simulation. It prices ethanol at
0.6588285541 USD/kg with an NPV of -20,477.5 USD. The run that sets nothing prices it at 0.658813642 USD/kg with an
NPV of 0. The two differ by 2.26e-5 relative, about 22,600 times the ten significant digits (`rtol` 1e-9) that both
runs' bases state.

## Contract

- `docs/api/engines.md:615-616`: "A library thing's precision is ten significant digits (`rtol` 1e-9) within the
  package test's absolute tolerance (`atol` 1e-8): a library run keeps those digits (`library.DIGITS`)."
- `core/openferment_core/engine/library.py:317-319`: each run's basis carries the input `precision`, "10
  significant digits", with the note "every number the run keeps is rounded so: BioSTEAM sums a set of units in an
  order that moves the last digits from one build to the next, and a replay compares the plant".
- `docs/decisions/ADR-004-biosteam-adapter.md:120-125` measures the spread itself on the composed flowsheet: "a
  fresh build prices ethanol at 0.6588136420 USD/kg; simulating the same plant again without settling it gives
  0.6588285541; a settled plant gives 0.6589116596 every time ... The spread (1.5e-4 relative) is where the
  wastewater recycle stops within the tolerance the package sets on it". It settles the composed flowsheet for the
  A→B→A gate. No record says that a run that sets a value reads a different simulation from a run that sets none.

## Command

From the repository root: `bash bughunt/repro/H4-03/run.sh`

It makes the database `bh_r_h4_03_feed` fresh and starts a keyless service on 127.0.0.1:10300. It makes a project,
reads the feedstock price's default from `GET /api/library/cornstover/parameters`, and runs cornstover twice through
`POST /api/library/cornstover/run`: run A sets nothing, and run B sets `stream.cornstover.price` to that default as a
person's assumption. Then it stops the service and drops the database. `check.py` sets the two runs side by side.

## Expected

Run B sets the plant to the values run A builds it with, so its numbers equal run A's to the ten significant digits
both bases state. Ethanol is 0.658813642 USD/kg, the NPV is 0, and the capital recovery is 41,575,770.25 USD/yr.

## Observed (run1.log, run2.log: the same on both)

| | A, nothing set (run `bfda026530692adc`) | B, the default set (run `fa7cc9f08dcd8c09`) | B/A - 1 |
|---|---|---|---|
| solved price, USD/kg | 0.658813642 | 0.6588285541 | 2.26e-5 |
| NPV at the set price, USD | 0.0 | -20,477.5 | |
| material cost, USD/yr | 82,272,670.8 | 82,276,393.43 | 4.52e-5 |
| utility cost, USD/yr | -11,189,195.65 | -11,190,187.86 | 8.87e-5 |
| capital recovery, USD/yr | 41,575,770.25 | 41,573,039.7 | -6.57e-5 |
| TCI, USD | 343,897,151.5 | 343,897,170.4 | 5.5e-8 |

Run B's basis holds the default exactly (0.05158816935126135), so the price it set moves the material cost by 0
USD/yr. The material cost moves by 3,722.63 USD/yr all the same, and the utility cost moves by 992.21 USD/yr, which no
feed price enters. The process state itself moved: run B's numbers come from a second simulation of the built plant.
B's solved price is ADR-004's "simulating the same plant again without settling it", to every digit.

## Likely cause

`core/openferment_core/workers/library_plants.py:779-784` (`run`): `build` returns a plant the package has already
simulated, and a run with any value calls `apply` and then `simulate(p)` again. A run with nothing set reads the
first simulation, and a run with values reads a second one. That second simulation starts its recycles from the
converged state for a library plant (`simulate` settles only a composed flowsheet, `:711-712`), and BioSTEAM's recycle
tolerance (ADR-004:123-124) lets it stop elsewhere. Confidence high. `export` (`:827-830`) does the same, so the SFF
file of run B rebuilds the same second simulation.

Settling alone would not close the gap. A side measurement on `cellulosic_ethanol_v0`, which does settle, set its
feedstock price to the same default: it priced ethanol at 0.6589116596 USD/kg against 0.658813642 with nothing set
(1.5e-4 relative). This is ADR-004's settled figure. The two runs differ because one reads the build's first
simulation and the other a later one. A study that moves a library input by a small step reads this spread as the
input's effect.
