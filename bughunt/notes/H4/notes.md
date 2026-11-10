# H4: independent numbers

Hunt H4 at 2047f5a. Services on 127.0.0.1:8840 (bh_h4_main) and 8841 (bh_h4_repro, made by repro.sh), both
stopped and both databases dropped. Keyless throughout; no model call. Every script is in `scripts/`;
`scripts/repro.sh <candidate|all>` reproduces every candidate from a fresh database (run once with `all`,
exit 0, log in the scratch directory as `repro-all.log`).

## 1. Library plants against biorefineries imported directly

`direct_plant.py` imports biorefineries in its own process (BioSTEAM 2.54.0), builds cornstover, corn (with the
SSF inlet change the adapter states) and `cellulosic.Biorefinery()`, and prints the TEA, the solved price, the
UnitGroup totals, every stream and every unit. `compare_plant.py` sets each against the service's
`POST /api/library/{plant}/run` answer. Held: every number agrees to ten significant digits (price block,
outputs.values, measured, utilities, TEA breakdown, 118/104/118 streams, 68/71/68 units). The composed
`cellulosic_ethanol_v0` (dilute acid, IB) equals cornstover in every stream and unit and in the solved price
0.658813642 USD/kg; it differs only in the ethanol's set price (0.7199, BioSTEAM's), which feeds H4-01.
ADR-013's two values are what the package's code measures here.

Found: the cost card of a library run is read at the set price (H4-01); a value set equal to its default moves
the price in the fifth digit (H4-03); the composed flowsheet's ethanol outputs are the denatured stream's (H4-06).

## 2. fermOS families against closed forms

`kinetics_cases.py` and `kinetics_more.py`: zero growth with a non-growth product, exponential growth (Ks 0)
with a growth-associated product, decay alone, maintenance alone, Monod at constant yield, chemostat steady
state and washout, fed-batch dilution, exponential feed at mu_set, aerobic OUR. Each matches its closed form to
the solver's tolerance, mass closes by hand (sugar used x yield = biomass and product formed), units are as
stated, and the kinetics engine's run is the route's artifact with the same outputs. A logistic fit of exact
data recovers its parameters and its forecast's median.

Found: the mass-balance check flags a no-uptake fed-batch as not closing (H4-04); a mu_max-zero batch is
refused with words that say its sugar never runs out (H4-05).

## 3. Train runs

`train_from_run.py` reads the ethanol_glucose_v0 run into a train and runs it; `train_balance.py` checks every
unit's inlets against its outlets by component, every stream's total, and the train's recovery, productOut,
productLost, overallRecovery, purity and outputs.values against the table. Everything closes. A train read
from the cornstover run builds with no refusal and cannot run (suspected).

## 4. The cost card

`costcard.mjs` renders `/#/p/h4p/proforma/runs/<id>` in Chromium and reads the waterfall rows, the closing row
and the notes. Held for cornstover, corn and ethanol_glucose_v0: lines sum to the closing row, per-unit values
are the annual amounts over basis flow times hours. Found: H4-01 (library runs close on the set price, and the
capital recovery line takes the NPV gap) and H4-02 (custom_train_v1 closes on a price per kg of stream while its
lines are per kg contained, and the note under it says two false things). H4-07 came from the scenario run's
read-back (beer 61.8 g/L under a titre of 70).

## Left

Aerobic vessel designs, the batch_v1 family fit, pureOS's in-house classes and proposer rules, the other
library plants, kept_references replays. Thermo properties refuse every cornstover stream (documented refusal;
listed as suspected).
