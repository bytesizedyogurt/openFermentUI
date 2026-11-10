# H4-01: the composed cellulosic_ethanol_v0 at its default closes its cost card on the ethanol's set price

**Statement.** `cellulosic_ethanol_v0` at its default configuration (dilute acid, IB), run with no value set, is
cornstover's plant in every stream, unit, TEA total and solved price. Its build leaves the ethanol at the package
stream's set price of 0.7199 USD/kg (2.15 USD/gal). The package's own `Biorefinery` and the recipe's own `load()` each
set it to the price solved at the TEA's IRR, 0.6588 USD/kg. Its cost card therefore closes on 0.7199 USD/kg. Cornstover's card closes on 0.6588. The
Capital recovery line carries the whole 0.0610 USD/kg gap: 0.2860 against cornstover's 0.2249, for equal capital and
an equal IRR.

## What lies beyond the recorded debt

`docs/PROGRESS.md:631` (Left by decision) records: "A library run's TEA breakdown is read at the product's set price
(`workers/library_plants.py` `_Module.parts` passes no price), and a flowsheet's run reads it at the price it solved;
where a library run's overrides move the solved price, the lines sum to the set price." That row covers cornstover with
a person's feed price of 0.08 USD/kg, the candidate's first case, so this reproduction leaves that case out.

- **Capital recovery takes the whole gap.** This follows from the debt's own words and is covered by them.
  `capitalRecovery` is `sales - aoc` (`core/openferment_core/workers/proforma_worker.py:459`). It is the one line whose
  value moves with the product's price, so lines that sum to the set price put the whole gap on it. The run shows this
  (the gap and the line's excess agree to 1e-6), and the verdict rests on the next part.
- **The composed flowsheet at its default, with no override, closes on a card other than cornstover's.** This is
  beyond the debt's words. No override is set, so the debt's "where a library run's overrides move the solved price"
  does not apply. `cellulosic_ethanol_v0` is openFerment's own flowsheet, and the debt says "a flowsheet's run reads
  it at the price it solved". This one reads its card at the set price. The cause also lies outside the debt: the
  flowsheet's build leaves out the IRR price that the recipe's own `load()` sets on the ethanol. RESULT keys on this part.

## Contract

- `core/openferment_core/flowsheets/recipes/cellulosic_ethanol_v0/load.py:35-36`: "With dilute acid and IB the plant is
  the package's own cellulosic plant (`biorefineries.cellulosic.Biorefinery`), unit for unit."
- `core/openferment_core/flowsheets/recipes/cellulosic_ethanol_v0/load.py:174-175` and `:184`: `load()` builds "The package's
  own composition (dilute acid, IB), simulated, with the ethanol priced at the TEA's IRR as the package's `Biorefinery`
  prices it", followed by `ethanol.price = tea.solve_price(ethanol)`.
- `docs/PROGRESS.md:631`: "a flowsheet's run reads it at the price it solved".
- `core/openferment_core/workers/proforma_worker.py:509-513` (`tables`): "Where the flowsheet solved a price, the
  product carries it while every table is read, its stream row included ... (OF-BLD-019 §2.R: the row once showed the
  package's list price beside the price the run solved)".
- `core/openferment_core/workers/proforma_worker.py:427`: "Capital recovery", "TEA.sales less TEA.AOC: the return on
  and of the capital, and its tax". `src/components/figures/CostWaterfall.tsx:1`: "What the price is made of".
- `CLAUDE.md:69`: "BioSTEAM runs through one adapter (`engine/library.py`) for library plants and openFerment's
  flowsheets alike".

## Command

    bash bughunt/repro/H4-01/run.sh

The script makes a fresh database `bh_r_h4_01_card` and starts a keyless service on 127.0.0.1:10220 that serves the
built app. It makes project `h401` and calls `POST /api/library/cornstover/run` and
`POST /api/library/cellulosic_ethanol_v0/run` with no inputs. It compares the two runs' streams, units, TEA totals,
price blocks and `tea.lines`, then opens each run's page in Chromium and reads the cost card's rows and price note.
Afterwards it stops the service and drops the database. It takes about 30 s. The composed flowsheet's page is saved as
`screen-cellulosic_ethanol_v0.png`.

## Expected

The two plants are equal (118 streams, 68 units, FCI, TCI, FOC, IRR 0.1, solved price 0.658813642 USD/kg), so the two
cards are one card. Every line closes on the solved price 0.6588 USD/kg, and Capital recovery reads 0.2249 USD/kg on
both. This is what `cellulosic_ethanol_v0`'s card gives when it is read at its own solved price (solved price less the
other lines).

## Observed (run1.log, run2.log)

- Both runs set no overrides (`{}`). The plants are equal: 118 streams and 68 units equal, no TEA total differs, and
  both have an IRR of 0.1 and a solved price of 0.658813642.
- `packagePrice`: cornstover 0.658813642, cellulosic_ethanol_v0 0.7198608115. The price block's NPV is 0.0 for
  cornstover and 81,182,947.4 USD for the same plant as cellulosic_ethanol_v0. In the stream table the ethanol row's
  price is 0.658813642 for cornstover and 0.7198608115 for cellulosic_ethanol_v0.
- Cards (USD per kg): Main feedstock 0.2446, Other materials 0.2005, Utilities -0.0605 and Fixed operating 0.0493 are
  equal on both. Capital recovery is 0.2249 for cornstover and 0.2860 for cellulosic_ethanol_v0. The closing
  row is "Base-case price 0.6588" for cornstover and "Price the lines are read at 0.7199" for cellulosic_ethanol_v0.
- Both screens state "Base case, every input at its value: 0.6588 USD per kg of ethanol". The composed flowsheet's
  card adds the price note "The breakdown is read at the product's set price, 0.7199 USD per kg of the ethanol stream,
  and its lines sum to that price ...". Cornstover's card has no price note.

## Likely cause

- `core/openferment_core/flowsheets/cellulosic_ethanol_v0.py:92-110` (`build`): the plant is returned with the ethanol
  at the package stream's default price, `price=0.7198608114634679`
  (`biorefineries/cellulosic/streams.py:74`). The IRR price is never set. The package's
  `Biorefinery.__new__` sets it (`biorefineries/cellulosic/biorefinery.py:61`,
  `ethanol.price = self.tea.solve_price(ethanol)`), and so does the recipe's own `load()` (`load.py:184`). Cornstover
  is built through `Biorefinery`, so its set price is its solved price.
- With `core/openferment_core/workers/library_plants.py:786,818` (`"price": None`), `tea_breakdown` reads sales at that
  set price (`proforma_worker.py:439-459`), and `capitalRecovery = sales - aoc` carries the gap. This second half is
  the recorded debt.
- Confidence: high. Swapping in the IRR price gives the expected card exactly: 0.658814 less the other lines is
  0.224941.

Severity S2, kind Wrong number, fix small. One possible fix is for the flowsheet's build to price its ethanol as its
recipe's `load()` and the package's `Biorefinery` do. That fix moves the composed flowsheet's run output (its price
block's `packagePrice` and NPV, its tables), so a kept run of it would replay differently and needs a version.
