# The worker protocol

BioSTEAM, thermosteam, biorefineries, the vendored SFF toolkit and cobra run in worker processes
(execution prompt §7.1, §7.3): a cold BioSTEAM import takes about thirty seconds, and the
service stays light. The service's side is `SimWorker` (`core/openferment_core/workers/__init__.py`);
the worker's side is `serve`. The Proforma worker is reached through
`core/openferment_core/engine/simulator.py`, which starts it on first use (or with the service
when `OPENFERMENT_WARM_PROFORMA=1`) and reports `cold`, `starting`, `ready` or `failed`.

## Lines

One JSON request per line on the worker's stdin, one JSON response per line on its stdout:

```
in   {"id": 1, "op": "sff_validate", "args": {"path": "/tmp/…/flowsheet.json"}}
out  {"id": 1, "ok": true, "result": {…}, "ms": 112}
out  {"id": 1, "ok": false, "error": "Refused: there is no flowsheet x; there are …", "ms": 3}
```

- `ping` is answered by `serve` in every worker: `{"worker": "<name>", "pid": <pid>}`.
- An unknown op, a handler that raises, or a result JSON cannot hold (NaN, infinity) is an error
  response, `"<ExceptionType>: <words>"`, and the worker answers the next request. A request the
  worker refuses in words raises `Refused`, so its error begins `Refused: `.
- Only responses reach stdout: descriptor 1 is pointed at stderr while the worker serves, so a
  library that prints cannot corrupt the stream.
- A request that takes longer than the call's timeout kills the process; the next call starts a
  new one. A crash reports the tail of the worker's stderr. No worker stops in a debugger
  (`PYTHONBREAKPOINT=0`).

## Workers

| Worker | Module | Imports | Ops |
|---|---|---|---|
| `proforma` | `workers/proforma_worker.py` (with `flowsheets/`, `workers/library_plants.py`, `workers/sff_toolkit.py`, `vendor/pisces_sff`) | biosteam, thermosteam, biorefineries, the SFF toolkit | `benchmark`, `evaluate`, `grid`, `montecarlo`, `run`, `reference`, `thermo_props`, `volatility`, `vessel_specs`, `vessel_design`, `catalogue_specs`, `catalogue_unit_check`, `train_specs`, `flowsheet_unit_values`, `train_run`, `sff_export`, `sff_validate`, `sff_score`, `library_discover`, `library_parameters`, `library_run`, `library_cases` |
| `geneos` | `workers/geneos_worker.py` | cobra | `describe`, `ceiling`, `frontier`, `mix` |
| `echo` | `workers/echo_worker.py` | nothing heavy | the protocol's own tests |

Each module's docstring describes its ops; this page gives every op's request and result.

## Proforma's flowsheet ops (Proforma worker; OF-BLD-014 §8, OF-BLD-019 §2, `proforma.py`)

A flowsheet is an id in `flowsheets.KNOWN`: the shelf's ids and the test-only `toy`. Every op that
names a `flowsheet` refuses an id outside it with the words of `flowsheets.load`'s `KeyError`,
which `str()` quotes: `Refused: 'there is no flowsheet x; there are …'`. The toy,
`ethanol_glucose_v0` and `custom_train_v1` run case by case: the worker builds each once inside
`package_defaults()` and keeps it warm, and each case sets its inputs on the built objects and
simulates again. A scenario flowsheet prices every case on BioSTEAM's default utility prices and
plant cost index. `custom_train_v1` is built from a `structure`, `{"fermenter", "train", "finance",
"financeKeys"}` as `composite.structure_of` reads it from the run's basis, and the worker keeps its
four newest structured builds (`STRUCTURES_KEPT`). A structure `custom_train_v1` cannot build (a
TEA parameter the corn plant's TEA does not take, a train unit whose id clashes with the
flowsheet's own, say) is refused in that module's words, through its own `Refused`. The reference
biorefineries (`cornstover_benchmark`, `corn_drygrind`) run whole through `reference`.
`evaluate`, `grid`, `montecarlo` and `run` refuse a reference biorefinery, `custom_train_v1`
without a `structure`, and any other flowsheet given one.

### `benchmark`

The benchmark (OF-BLD-014 §8.2): `biorefineries.cornstover`'s plant built afresh inside
`package_defaults()`, its ethanol price solved by the package's TEA
(`flowsheets/cornstover_benchmark.run`). Request `{}`; the handler reads no field. Result
`{"package", "biosteam", "mespUsdPerGal", "mespUsdPerKg", "ethanolDensityKgPerGal", "settings":
{"rateOfReturn", "operatingDays", "incomeTax", "startYear", "endYear"}, "references": [string,
…]}`. `proforma.py` keeps it as one `proforma_benchmark` artifact and cites `mespUsdPerGal`.

### `evaluate`

One case. Request `{"flowsheet", "values": {input key: number}, "structure"}`: `values` sets the
inputs the flowsheet's module lists in `INPUTS` (the toy takes its own default for a key left out,
and the other two need every input), and `structure` is `custom_train_v1`'s. Result: the outputs
of the module's `evaluate`, a key per output. The toy gives `topEthanol`, `topWater` and
`bottomTotal` (kg h-1); `ethanol_glucose_v0` gives `pricePerKgEthanol`, `ethanolKgPerH`,
`costLines` and `readBack`; `custom_train_v1` gives `pricePerKgProduct`, `productKgPerH`,
`costLines` and `readBack`. `costLines` is `{"media", "utilities", "labor", "downstream", "other",
"capex"}`, USD per kg of product, and the lines sum to the price; `readBack` holds what the case
gave and every setting its inputs leave to the package or to BioSTEAM, read from the objects. A
`values` key the flowsheet does not take is refused, and so is an input its own checks reject (a
missing input, a value out of its range), in its words. A case the flowsheet cannot hold raises its
`Infeasible`, whose `reason` is `yield`, `concentration`, `convergence` or (for `custom_train_v1`)
`product`, so the error begins `Infeasible: `; `grid`, `montecarlo` and `run` catch it and record
it with the case.

### `grid`

Request `{"flowsheet", "axes": {input key: [number, …]}, "base": {input key: number}}`, with one
to three axes; each cell is `base` with one value of each axis set over it. Result `{"axes",
"base", "cells": [{"at": {input key: number}, "outputs", "infeasible"}, …]}`, the cells in
`itertools.product` order over the axes as given. `outputs` is `evaluate`'s result, null for a case
the flowsheet cannot hold. `infeasible` is null for a case that ran and `{"reason", "detail"}` for
one that did not: `reason` is the flowsheet's `Infeasible.reason`, or `error` for any other
exception, whose `detail` is then `"<ExceptionType>: <words>"`. The handler passes no
`structure`, so `custom_train_v1` is refused here. Fewer than one axis or more than three is
refused, and a refusal in any case ends the op.

### `montecarlo`

Request `{"flowsheet", "specs": {input key: spec}, "n" (default 500), "seed" (default 0), "base":
{input key: number}}`. A spec is `{"kind": "fixed", "value"}`, `{"kind": "uniform", "low",
"high"}` or `{"kind": "triangular", "low", "mode", "high"}`. The `n` samples are a Latin hypercube
over the spec keys (`scipy.stats.qmc.LatinHypercube`, seeded with `seed`); each sample's inputs
are `base` with every spec's draw set over it. Result `{"n", "seed", "samples": [{"inputs",
"outputs", "infeasible"}, …]}`, with `outputs` and `infeasible` as `grid`'s cells hold them. A
spec of another kind is refused. The handler passes no `structure`, and a refusal in any sample
ends the op.

### `run`

One whole run (OF-BLD-019 §2.1), which `proforma.py` keeps as one `proforma.run` artifact. Request
`{"flowsheet", "base", "specs", "samples" (default 0), "seed" (default 0), "axes", "diagram",
"structure"}`: `base`, `specs` and `axes` as `evaluate`, `montecarlo` and `grid` take them (`axes`
null for no grid), `samples` the number of samples, `diagram` what the run's basis says of its
diagram (true asks for it, false asks for none, null draws it where Graphviz's `dot` is on the
path), and `structure` for `custom_train_v1`. The base case runs first, and its tables are read
before any other case moves the objects; the grid runs next, then the samples. Result `{"base",
"baseInfeasible", "tables", "grid", "montecarlo"}`. `base` is the base case's outputs, null when
it failed, and `baseInfeasible` is then `"<ExceptionType>: <words>"`; `tables` (below) is null
when the base case failed; `grid` is `grid`'s result, null without `axes`; `montecarlo` is
`montecarlo`'s result, `{"n": 0, "seed", "samples": []}` when `samples` is 0.
`proforma._run_scenario` reads `base`'s price output (the shelf's `priceOutput`), `costLines` and
`readBack`; each sample's `inputs`, price output and `infeasible.reason`; each cell's price output
and `costLines`; and every key of `tables`. A refusal in any case ends the run.

### `reference`

A reference biorefinery run whole on its package's defaults (OF-BLD-019 §2.2): built afresh inside
`package_defaults()` and read before the worker's settings go back. Request `{"flowsheet",
"digits" (1–17, default 17), "diagram"}`; `proforma.py` sends the digits the basis states
(`REFERENCE_DIGITS`, 10) and `diagram` as `run` takes it. Result, every float rounded to `digits`
significant digits: `{"flowsheet", "simulator": "biosteam <version>", "measured": {expression:
number}, "readBack"}`, with the module's `outputs()` and the run's tables (below) beside them.
The outputs are `cornstover_benchmark`'s `package`, `mespUsdPerGal`, `mespUsdPerKg`,
`ethanolDensityKgPerGal`, `settings` and `references`, or `corn_drygrind`'s `package`,
`ethanolPriceUsdPerKg`, `IRR`, `ethanolKgPerH`, `cornKgPerH` and `references`. `measured` holds
the quantities the package's test asserts, keyed by the expression the test writes: `tea.IRR`,
`feedstock.price`, `product.price`, `tea.sales`, `tea.material_cost`,
`tea.installed_equipment_cost`, `tea.utility_cost`, `units.get_heating_duty()`,
`units.get_cooling_duty()`, `units.get_electricity_consumption()` and
`units.get_electricity_production()`. `readBack` is the module's `read_back()`, every input the
shelf lists for `corn_drygrind`, and `{}` for `cornstover_benchmark`, which has none.
`proforma.py` adds `regression` and `checks` before it keeps the `proforma.reference` artifact. A
flowsheet with no `load` (one run case by case) is refused, and so are `digits` outside 1–17.

### `tables`

What `run` returns as `tables`, and what `reference` and `library_run` return beside their other
keys: every table of the base case, read from the objects it left (`tables()` in
`proforma_worker.py`). Where the flowsheet solved a price, the product stream carries it while the
tables are read.

```
{"tablesSource": "BioSTEAM <version>, thermosteam <version>",
 "tea": {"teaClass", "product", "feedstock", "productPrice", "basisFlow", "basis",
         "operatingHours", "sales", "materialCost", "feedstockCost", "otherMaterialCost",
         "utilityCost", "purchaseCost", "installedEquipmentCost", "FCI", "TCI", "FOC", "laborCost",
         "capitalRecovery", "coproductCredits", "IRR", "incomeTax",
         "lines": [{"key", "label", "usdPerYear", "perUnit", "reads"}, …]} | null,
 "streams": [{"id", "source", "sink", "phase", "T", "P", "massFlow",
              "massFlows": {chemical: kg/hr}, "price"}, …],
 "units": [{"id", "unitClass", "line", "order", "ins", "outs", "installedCost", "purchaseCost",
            "heatingDuty", "coolingDuty", "power"}, …],
 "utilities": {"group", "heating", "heatingUnit", "cooling", "coolingUnit",
               "electricityConsumption", "electricityConsumptionUnit",
               "electricityProduction", "electricityProductionUnit"},
 "diagram": SVG text | null, "diagramNote": string | null,
 "unitOrder": [unit id, …], "tableUnits": {key: unit}}
```

`tea` is the TEA object's own numbers (`tea_breakdown`), null for a flowsheet with no TEA or no
product (the toy). Its `lines` are `feedstock`, `otherMaterials`, `utilities`, `otherVariable`,
`fixedOperating`, `capitalRecovery` and `coproductCredits` (`LINE_WORDS` names what each reads);
`otherVariable` and `coproductCredits` are left out when they lie within the float's own noise of
zero (`NOISE`). A line's `perUnit` is its `usdPerYear` over `basisFlow` (kg/hr) times
`operatingHours`: per unit of the price's `basis`. Streams and units come in run order
(`units_in_order`). A stream BioSTEAM left unnamed has an id in BioSTEAM's notation, `U1-2` for
outlet 2 of U1 and `0-U1` for inlet 0; a feed has a null `source` and a product a null `sink`;
`price` is null for a stream with no price. `heatingDuty`, `coolingDuty` and `power` are null for
a unit with none. `utilities` is BioSTEAM's `UnitGroup` over the units the TEA costs (every unit of
the system when there is no TEA), each total with the unit the UnitGroup module states for it
(`DUTY_UNITS`, `ELEC_UNITS`). `diagram` is the flowsheet as SVG text, drawn when the basis asks for
it and Graphviz's `dot` is on the path; `diagramNote` says why a run has none. `tableUnits` is
`flowsheets/shelf.py`'s `TABLE_UNITS`: `T` K, `P` Pa, `massFlow` kg/hr, `price` USD/kg, `cost`
USD, `duty` kJ/hr, `power` kW, `annual` USD/yr, `perUnit` USD per unit of the price's basis.

## SFF ops (Proforma worker; ADR-003, `docs/api/sff.md`)

Paths are absolute paths on the machine the service and the worker share; the service writes and
removes them.

### `sff_export`

A run's base case written as an SFF file (schema 0.2.4) at `path`, then checked.

Request:

| Field | Type | |
|---|---|---|
| `flowsheet` | string | a shelf flowsheet id (`flowsheets.KNOWN`) |
| `path` | string | where the file is written |
| `base` | object, key → number | a flowsheet run case by case: the run's base values. Left out for a reference biorefinery |
| `structure` | object | a structured flowsheet (`custom_train_v1`): what it is built from |
| `metadata` | object | written as `metadata.openferment` in the file |
| `title` | string or null | written as `metadata.process_title` |
| `library` | string | in place of `flowsheet` for a library run: the `biorefineries` plant, with `configuration` and `overrides` as `library_run` takes them |

A reference biorefinery (a flowsheet module with `load`) is built afresh inside
`package_defaults()`; any other is the worker's warm plant set to `base` and simulated, its
solved price on the product while the file is written; a library plant is built afresh and
set as its run set it. The toolkit's JSON writer is taught, for the export alone, to write a
thermosteam reaction in its own words and a stream by its id (`docs/api/sff.md`). Result:
`checked` (below) plus `"simulator": "BioSTEAM <version>"`.

### `sff_validate`

Request `{"path"}`. Result:

```
{"path", "sha256", "valid": bool, "schemaVersion": "0.2.4",
 "summary": {severity: {status: count}},
 "findings": [{"checkId", "severity", "status", "message", "path"}, …]}
```

`findings` lists each result that did not pass. A path that is not an absolute path to a file is
an error.

### `sff_score`

Request `{"path"}`. Result:

```
{"path", "sha256",
 "completeness": {"score", "representableScore", "categories", "criticalities",
                  "criteria": [{"id", "category", "criticality", "weight", "representable",
                                "status", "score", "message", "missing"}, …],
                  "sffVersion", "recipe", "report"},
 "tags": {tag: {"earned": bool | null, "declared": bool, "blocking": [string, …]}, …}}
```

`reproducible.earned` is always null: the toolkit's conda harness never runs.

### `checked`

What `sff_export` returns beside `simulator`: `{"path", "sha256", "bytes", "validation"
(as sff_validate's, without path and sha256), "completeness", "tags", "toolkit": "pisces_sff 0.2.4"}`.

## Library ops (Proforma worker; ADR-004, `engine/library.py`)

A plant is a subpackage of the installed `biorefineries`; `configuration` is one of the names the
package gives it (null for a plant built in one configuration, its own). Every build is fresh,
inside `package_defaults()`. A refusal (a plant that is not one, a configuration it does not
name, a build the package itself cannot finish under the pinned BioSTEAM, a parameter it does not
read back, a value of the wrong kind) is an error beginning `Refused: `.

### `library_discover`

Request `{"builds": bool}`. Result: `{"package", "simulator", "thermosteam", "testFile",
"testTables", "plants": [plant, …]}`, each plant `{"id", "module", "kind": "plant" | "subsystems" |
"none" | "unimportable", "title", "readme", "entry", "parameters", "processModel", "scenario",
"requiresConfiguration", "configurations", "configurationsFrom", "takesCache", "tests",
"testNames", "compat": [{"change", "why"}], "factories", "error"}` and, when `builds` is true,
`"builds": [{"configuration", "ok", "units", "priced", "error"}]`. `engine/library_shelf.json` is
this result with builds (`pnpm library:discover`).

### `library_parameters`

Request `{"plant", "configuration"}`. Result `{"plant", "configuration", "found": {part: how it
was found}, "parameters": [{"key", "label", "group", "unit", "value", "note", "kind": "number" |
"text"}], "simulator", "package"}`. Keys: `stream.<id>.F_mass`, `stream.<id>.price`,
`tea.<attribute>`, `utility.CEPCI`, `utility.electricity_price`, `utility.<agent>.<price>`,
`unit.<id>.<design input>` (as the SFF toolkit's design-spec registry names a unit's inputs). A
`text` parameter is read back and never set.

### `library_run`

Request `{"plant", "configuration", "overrides": {key: number}, "digits": 1–17}`. Result, every
float rounded to `digits` significant digits: `{"plant", "configuration", "simulator",
"package", "found", "price": {"priced", "teaClass", "IRR", "sales", "material_cost",
"utility_cost", "installed_equipment_cost", "TCI", "FCI", "FOC", "VOC", "NPV", "product",
"packagePrice", "solvedPrice", "feedstock", "feedstockKgPerH"}, "measured": {the package test's
expressions}, "parameters" (read back after the values were set), "libraryDefaults": {key:
value as built}, "overrides"}` and the run's tables (`tablesSource`, `tea`, `streams`, `units`,
`utilities`, `diagramNote`, `unitOrder`, `tableUnits`). A plant whose TEA BioSTEAM cannot break
down (an agile system) has `"tea": null` and a `teaNote` saying why.

openFerment's composed flowsheets run through the same ops: `plant` is `cellulosic_ethanol_v0`,
`configuration` one of its eight (`"dilute acid, IB"` when null), and its own parameters come first
(`feed.moisture`, `feed.dry.<component>`, `unit.<id>.solids_loading`, `unit.<id>.tau…`,
`rxn.<unit>.<set>.<index>`). A run of it adds `readBack` (each process unit's mode, temperature,
residence times, vessel count and reaction sets; the organism the recipe declares; the TEA's
settings; the utility prices and cost index; the versions) and `outputs` (`mespUsdPerKg`,
`mespUsdPerGal`, `ethanolKgPerH`, `dryFeedKgPerH`, `ethanolKgPerKgDryFeed`). Its gates refuse in
words before it runs: dry shares that do not sum to one, a moisture outside [0, 1), a reactant's
conversions summing past one; a case BioSTEAM finds infeasible is refused with its
`InfeasibleRegion` words. Its export embeds the recipe (`metadata.reproducibility`).

### `library_cases`

Request `{"plant", "configuration", "cases": [{key: number}, …], "digits"}`. One warm build; each
case sets every settable parameter to its library default and then its own values, settles the plant
(recycles emptied, the TEA's sales guess cleared) and runs. Result: one entry per case, `{"values",
"price", "outputs"}` or `{"values", "refused"}`, rounded to `digits`. The A→B→A gate runs here.

## Thermo ops (Proforma worker; OF-BLD-019 §4.2, OF-BLD-020 §7.1, `thermo.py`)

The worker looks up each chemical in thermosteam's library by its name and makes one property
package per set of names, kept for the worker's life. A question naming a chemical the library
lacks, or cannot build, is refused in words naming it, and so is a set of chemicals thermosteam
cannot make one property package of. A property the library cannot compute is null, with the
library's reason in `notes`. A `T`, `P` or phase the request leaves out is the library's own
Stream default, read from its signature. Temperatures are in K and pressures in Pa. `thermo.py`
keeps each answer as one artifact (`thermo_props`, `volatility`).

### `thermo_props`

One mixture's properties (D9). Request `{"components": {chemical: number}, "T", "P", "phase",
"solve"}`. `components` holds mass flows or fractions by the library's chemical names, and their
ratios set the mixture; an entry at or below zero is left out. `phase` is `l`, `g` or `s`. `solve`
asks for a composition, and the solve's two chemicals then make the mixture: `{"kind": "titre",
"solute", "solvent", "kgPerM3"}` is the solute's mass fraction at which its mass per volume of the
mixture, at the mixture's own density, is `kgPerM3` (kg m⁻³), a fixed point from the pure solvent;
`{"kind": "azeotrope", "light", "heavy"}` is `light`'s mole fraction in the liquid whose first
bubble at `P` has the liquid's own composition, scanned on 99 mole fractions from 0.01 to 0.99 and
then halved 60 times. `thermo.py` asks about a run's stream (`components` and `phase`), the
ethanol–water azeotrope (`solve` azeotrope) or beer at a record's titre (`solve` titre). Result:

```
{"library": "thermosteam <version>", "T", "P", "phase", "TSource", "PSource",
 "massFractions": {chemical: kg/kg}, "density", "Cp", "viscosity",
 "bubblePoint", "vapourAtBubble": {chemical: mol/mol} | null, "dewPoint",
 "units": {key: unit}, "solved": {…} | null, "notes": [string, …]}
```

`TSource` and `PSource` are `"given"` or `"thermosteam's Stream default"`. `density`, `Cp` and
`viscosity` are the Stream's `rho`, `Cp` and `mu`; `bubblePoint` and `dewPoint` are temperatures
at `P`, and `vapourAtBubble` is the first bubble's composition (null when the library cannot
compute the bubble point); `units` names each key's unit as thermosteam's `stream_units_of_measure`
gives it. `solved` is `{"kind": "titre", "solute", "solvent", "kgPerM3", "iterations", "how"}` or
`{"kind": "azeotrope", "light", "heavy", "moleFraction", "P", "how"}`. The op refuses a phase other
than `l`, `g` or `s`; a `solve` kind other than `titre` or `azeotrope`; a mixture whose every flow
is zero; a titre not below the density thermosteam gives the mixture, or one whose mass fraction
does not settle in 100 steps; and a pair with no azeotrope at `P`.

### `volatility`

A chemical's volatility beside a partner (D12). Request `{"chemical", "partner", "P"}`: two
different chemicals of the library, by name, and the pressure (the library's Stream default when
null). `thermo.py` sends the product's chemical (`thermo.CHEMICALS`), `Water` as the partner, and
`P` null. Result:

```
{"library", "chemical", "partner", "P", "PSource",
 "boilingPoint", "partnerBoilingPoint", "lighter",
 "azeotrope": true | false | null, "azeotropeMoleFraction", "azeotropeMassFraction",
 "azeotropeT", "searched": {"of", "from", "to", "points", "halvings"} | null,
 "how", "notes": [string, …], "units": {key: unit}}
```

`boilingPoint` and `partnerBoilingPoint` are each chemical's `Tb` as the library holds it, null
when it holds none. `lighter` is the one that boils lower; the search scans its mole fraction
(`searched`: 99 points from 0.01 to 0.99, then 60 halvings). `azeotrope` is true when the library's
own vapour-liquid equilibrium gives the pair a minimum-boiling azeotrope at `P`, false when the
scan finds none, and null when the search did not run (a boiling point is missing, or the library
could not compute the bubble points the search reads); `notes` says why. `azeotropeMoleFraction`
and `azeotropeMassFraction` are `chemical`'s fractions in that liquid, and `azeotropeT` is its
bubble point at `P`. `units` gives K for the temperatures, Pa for `P`, and mol/mol and kg/kg for
the fractions. The op refuses a missing `chemical` or `partner`, and the two the same.

## Vessel and catalogue ops (Proforma worker; OF-BLD-020 §4.1, §5.1, `vessel.py`, `pureos/catalogue.py`)

`vessel_specs` and `catalogue_specs` read what BioSTEAM alone knows of a unit class: its defaults
(from its signatures, class attributes and a probe instance), the choices its tables and setters
list, and what its setters refuse. `vessel_design` and `catalogue_unit_check` build a unit and
simulate it. Every build is fresh, inside `package_defaults()`, on the yeast program's chemicals
(`biorefineries.corn.create_chemicals`). The service keeps each `*_specs` answer for its process's
life (`vessel.worker_specs`, `catalogue.worker_specs`).

### `vessel_specs`

What fermOS's vessel class takes and its own defaults (`flowsheets/vessel.py` `specs`). Request
`{"kind": "aerobic" | "anaerobic"}`. Result `{"kind", "unitClass", "parameters": {name:
{"default", "from"}}, "refuses": {name: {"atOrBelow", "from"}}, "biosteam", "thermosteam",
"biorefineries", "chemicals", "operatingHours", "operatingHoursFrom", "costIndex",
"costIndexYear"}`, and an aerobic vessel adds `"designs": {design: {"method", "optimize_power",
"kW_per_m3", "runs", "solvesPower", "registered"}}`, `"defaultDesign"`, `"choices":
{"vessel_material", "vessel_type", "heat_exchanger_configuration"}`, `"heatPerO2"`,
`"heatPerO2From"`, `"aerationFloorMolPerS"` and `"aerationFloorFrom"`. `unitClass` is
`AeratedBioreactor` for an aerobic vessel and `NRELAnaerobicBatchBioreactor` for an anaerobic one.
`parameters` holds each parameter of the class's `_init` (the aerated class's with the stirred-tank
family's) with its default and where it was read; `refuses` holds the value at or below which the
class's setter refuses `N` or `V_max`. `designs` is keyed by BioSTEAM's design names
(`Stirred tank`, `Bubble column`), each with the kLa method a unit of that design takes when
nothing else is set, its `optimize_power` and `kW_per_m3`, the methods `get_kLa` runs (`runs`) and
`get_agitation_power` solves (`solvesPower`), and every method BioSTEAM registers for it.
`operatingHours` is the operating days of `biorefineries.corn`'s TEA (`default_tea_parameters`) in
hours; `costIndex` is BioSTEAM's plant cost index, and `costIndexYear` the year BioSTEAM's source
gives for its default index (null when the index is not that default); `heatPerO2` (kJ/kmol) is
`biorefineries.cane`'s `Q_O2_consumption` default; `aerationFloorMolPerS` is the oxygen uptake
(mol/s) at or below which `AeratedBioreactor` sizes no air, read from its `_run` (null when the
worker finds no such test there). A `kind` other than `aerobic` or `anaerobic` is refused.

### `vessel_design`

One vessel designed for a fermOS simulation or kinetic fit (D7; `flowsheets/vessel.py` `design`):
built afresh inside `package_defaults()` on BioSTEAM's default utility prices and cost index,
simulated, and read. An aerated vessel is designed once on its balanced reaction, its reaction's
oxygen is scaled so the uptake BioSTEAM sizes for is `ourTarget`, and it is designed again.
`vessel.py` builds the request from a design's basis (`worker_request`) and keeps the answer as one
`fermos.vessel` artifact. Request:

```
{"kind": "aerobic" | "anaerobic", "design": "Stirred tank" | "Bubble column" | null,
 "start": {chemical: g L⁻¹}, "made": {chemical: g L⁻¹}, "used": g L⁻¹, "tau": h,
 "scale": {"plantScale", "batchVolume", "productTitre"},
 "params": {parameter: value},
 "our": {"t": [h, …], "value": [g O₂ L⁻¹ h⁻¹, …]}, "ourTarget", "oxygenBasis", "ourPeak"}
```

`start` is the batch at its start by chemical (`vessel.py` sends `Glucose`, `Yeast` and
`Ethanol`), `made` what the batch made (`Yeast`, `Ethanol`), and `used` the glucose it used. `tau`
is the reacting time. `scale` gives `plantScale` (tonnes of product a year) or `batchVolume` (one
vessel's working volume, m³), and `productTitre` (kg m⁻³), which sizes a plant scale. `params`
holds the class's parameters by BioSTEAM's own names (`T`, `tau_0`, `V_wf`, `V_max`, `N`,
`loading_time`, `kW_per_m3`, `Q_O2_consumption`, …); a parameter left out takes the class's own
default. An aerobic design adds the simulation's oxygen uptake (`our`), the uptake the air is sized
for (`ourTarget`, g O₂ L⁻¹ h⁻¹: the simulation's peak or its batch average), `oxygenBasis` (`peak`
or `batch-average`) and the peak the simulation states (`ourPeak`, or null). Result:

```
{"unitClass", "unitId": "R1", "aerobic": bool,
 "design": [{"label", "value", "unit", "readFrom"}, …],
 "designResults": {name: value}, "auxiliaries": {name: class}, "used": {attribute: value},
 "coolingAgents": [agent id, …],
 "cost": {"purchase", "installed", "byItem": {item: {"purchase", "installed"}}, "utility",
          "costIndex", "costIndexYear", "note"},
 "versions": {"biosteam", "thermosteam", "biorefineries"}, "chemicals", "dutyRead",
 "scale": {…}, "reaction": {…}, "oxygen": {…} | null, "warnings": [string, …],
 "utilitySettings": {…}, "designNotes": [string, …],
 "heat": {"bst", "method", "consumedKmolPerH", "convention", "oxygenKmolPerH", "conventionNote"}}
```

`design` is the design table, each row a value BioSTEAM holds with its unit and where it was read.
`designResults` is BioSTEAM's `design_results`, and `used` holds each attribute the built unit
holds (`T`, `P`, `tau`, `tau_0`, `V_wf`, `V_max`, `N`, `loading_time`, `kW_per_m3`, …). `scale` is
`{"operatingHours", "operatingHoursFrom", "productKgPerH", "how"}` for a plant scale and
`{"cycleH", "how"}` for a batch volume. `reaction` is `{"equation", "stoichiometry",
"glucoseUsedShare", "impliedYxo", "notes"}` for the aerated vessel's one reaction and
`{"equation", "fermentationShare", "growthShare", "theoreticalEthanolYield", "notes"}` for the NREL
vessel's two. `oxygen` is null for an anaerobic vessel; an aerobic vessel's is:

```
{"t", "our", "unit": "mmol L⁻¹ h⁻¹", "oxygenBasis", "balancedUptake", "scale",
 "reactionO2KmolPerH", "targetUptake", "scaledO2KmolPerH", "simulatedO2KmolPerH",
 "floorKmolPerH", "aerated", "otr", "kLa", "kLaUnit": "h⁻¹", "kLaNeededAtPeak", "method",
 "short": [[start, end], …], "sized", "cStar", "cL", "drivingForce"}
```

The uptakes (`our`, `balancedUptake`, `targetUptake`, `sized`) and `otr` are in `unit`, `cStar`,
`cL` and `drivingForce` in mmol L⁻¹, and the oxygen flows (`…KmolPerH`) in kmol/hr. `scale` is the
factor on the reaction's oxygen; `aerated` is false when BioSTEAM sized no air; `short` lists the
hours, start to end, in which the simulated uptake rises above what the vessel transfers.
`heat.bst` is BioSTEAM's duty (kJ/hr), found by `heat.method`, `heats-of-formation` or
`forced-per-oxygen`; `heat.convention` is D7's cross-check, the heat per oxygen times the oxygen
the simulation took up (`oxygenKmolPerH`), null when there is no uptake to apply it to
(`conventionNote` says why). `utilitySettings` is `flowsheets.utility_settings` over the vessel:
`cepci`, `electricityPrice`, and each agent's regeneration price, heat transfer price and
temperature. `vessel.py` turns `reaction.notes`, `designNotes`, `warnings` and the `oxygen` fields
into the design's flags. The op refuses, in `flowsheets/vessel.py`'s words (its own `Refused`, so
the error begins `Refused: `): a `kind` other than `aerobic` or `anaerobic`; neither or both of
`plantScale` and `batchVolume`; a plant scale with no product titre; a batch volume for an
anaerobic vessel, with `N`, or without `loading_time`; a start whose solids and solutes fill a litre
of broth, or feed water that does not settle; a batch with no glucose at the start, or glucose used
that is none or more than the start held; an aerobic batch whose products close the atomic balance
with no oxygen consumed, or with carbon dioxide or water consumed; an anaerobic batch whose ethanol
and cells need more glucose than it used; and a vessel BioSTEAM cannot build or design, in
BioSTEAM's words.

### `catalogue_specs`

What one of pureOS's unit types takes, read from its class's code (`pureos/catalogue.py`
`read_class`). Request `{"type"}`, a catalogue id. Result:

```
{"type", "unitClass", "module", "signature": {parameter: default},
 "constructor": {parameter: {"value", "from"}}, "attributes": {attribute: {"value", "from"}},
 "defaults": {key: {"value", "from"}}, "choices": {key: [word, …]},
 "refuses": {key: {"atOrBelow", "from"}}, "chemicals": [chemical id, …],
 "versions": {"biosteam", "thermosteam"}}
```

The class is BioSTEAM's or an in-house one (`pureos/inhouse.py`). `signature` and `constructor`
are keyed by the class's own parameter names, and `defaults`, `choices` and `refuses` by the
catalogue's keys. A value is plain: null, a number as a float, a bool as `"true"` or `"false"`, and
anything else as its text. A per-component split the class fills itself adds `byComponent`
(`{chemical: share}`) to its `defaults` entry. `chemicals` is the yeast program's chemical IDs.
`catalogue.specs_of` serves the answer as `UnitSpecs`. An unknown type is an error
`CatalogueUnknown: there is no unit type …`.

### `catalogue_unit_check`

One unit of a type built alone on given inlets and values, simulated and read, inside
`package_defaults()` on BioSTEAM's default utility prices and cost index (`catalogue.build_unit`,
`catalogue.unit_report`). The catalogue's sim test (`core/tests/test_catalogue.py`) is its one
caller. Request `{"type", "ins": [inlet, …], "values": {key: value}, "hold": [attribute, …]}`. An
inlet is `{"flows": {chemical: kg/hr}, "phase", "T", "P"}` (`phase` is `l` when not given),
`{"byPhase": {phase: {chemical: kg/hr}}, "T", "P"}` for a stream of several phases, or `{}`, an
empty inlet the unit may fill; `T` (K) and `P` (Pa) are set where given. `values` are by catalogue
key, as `catalogue.kwargs_of` turns them
into the class's arguments and attributes; `hold` names the attributes to read back. The unit is
`U1`, its inlets `in0`, `in1`, … and its outlets `out0`, `out1`, …, one for each outlet the entry
lists. Result `{"unitClass", "ins": [stream, …], "outs": [stream, …], "design": {name: value},
"purchaseCost", "installedCost", "utilityCost", "power", "heatDuties": [number, …], "held":
{attribute: value}}`, each stream `{"id", "massFlow", "phase", "massFlows": {chemical: kg/hr}}`.
Costs are in USD, `utilityCost` in USD/hr, `power` in kW and each heat duty in kJ/hr. `held` gives
each attribute as the built unit holds it, or `"unreadable: <ExceptionType>"`. The op raises no
`Refused`: an unknown type is `CatalogueUnknown: …`, and a unit that cannot be built or simulated
is the class's own exception and words.

## pureOS train ops (Proforma worker; OF-BLD-020 §5.2, `pureos/train_spec.py`)

A train is an inlet and an ordered list of catalogue units. The service resolves and names every
value (`pureos/train_spec.py`); the worker builds the BioSTEAM objects (`flowsheets/train.py`) and
reads them.

### `train_specs`

What a train builds on. Request `{}`; the handler reads no field. Result
`{"chemicals": [chemical id, …], "T", "P", "phase", "from", "versions": {"biosteam",
"thermosteam", "biorefineries"}}`: the yeast program's chemical IDs, and the temperature (K),
pressure (Pa) and phase thermosteam gives a Stream nobody set them on, read from the Stream's
signature (`from` says so).

### `flowsheet_unit_values`

A shelf flowsheet's own units read by catalogue key, as its package builds them (a train unit's
`readFrom`). Request `{"flowsheet", "units": [{"unit", "type"}, …]}`: a flowsheet run case by
case, and each unit by its ID with its catalogue type; `train_spec.flowsheet_unit` sends one unit
a call. The worker reads the units of its warm build of the flowsheet and simulates nothing
(`flowsheets/train.read_unit`). Result `{"flowsheet", "units": {unit id: {"unitClass", "values":
{key: value}, "unread": {key: why}}}, "versions": {"biosteam", "thermosteam", "biorefineries"}}`.
A per-component parameter comes per chemical as `<key>.<chemical>`, the light and heavy keys come
from `LHK`, an evaporator's pressures come as `P.<n>` with `effects`, and a bool comes as `"true"`
or `"false"`. `unread` names, with why, each parameter the unit holds as None or as something
other than a number or a word; the class's own default stands for it. The op refuses
`custom_train_v1` (its units are the fermenter's and a train run's own), a reference biorefinery,
a unit ID the flowsheet lacks, and a unit that is not an instance of the catalogue type's class.

### `train_run`

One train built from its plain spec (`flowsheets/train.Built`) and simulated whole with its
recycles, inside `package_defaults()` on the yeast program's chemicals, BioSTEAM's default utility
prices and cost index, and a fresh flowsheet. `train_spec.py` builds the request from a run's basis
(`_run_train`) and keeps the answer as one `pureos.train_run` artifact. Request:

```
{"system", "product", "diagram",
 "inlet": {"flows": {chemical: kg/hr} | null, "concentrations": {chemical: g L⁻¹} | null,
           "brothFlow": m³/hr | null, "balance": chemical | null, "T", "P", "phase"},
 "units": [{"id", "type", "values": {key: value},
            "outlets": {port: "onward" | "waste" | "recycle:<unit id>"},
            "sides": {port: {chemical: kg/hr}}}, …]}
```

`system` names the system and its flowsheet (`train_spec.py` sends `pureos_<train id>`). With
`flows`, the inlet carries those flows. With `concentrations` and `brothFlow`, it carries each
concentration over the broth flow, and the `balance` chemical (`Water` when null) at the mass that
brings the mixture's volume, as thermosteam computes it at the inlet's `T` and `P`, to
`brothFlow`. The units are built in order. Each unit's first inlet is the onward outlet of the unit
before it (the train's inlet for the first); an outlet routed `recycle:<unit id>` joins the inlet
from upstream of the unit it names; a side port takes the flows `sides` gives it; a port the unit
sizes itself is an empty stream; and every outlet is a stream named `<unit id>_<port>`. `diagram`
is as `run` takes it. `train_spec.py` also sends `product`, the chemical the train traces; the
handler does not read it, and the product stream is the last unit's onward outlet. Result
`{"tablesSource", "streams", "units", "utilities", "diagram", "diagramNote", "unitOrder",
"tableUnits"}` as the tables (above) hold them, with no `tea`, `utilities` over every unit of the
train and `unitOrder` the system's units; and beside them `"inlet": {"flows", "T", "P", "phase",
"volume", "water", "waterNote"}`, `"productStream"`, `"outlets": {unit id: {port: stream id}}`,
`"costs": [{"unit", "unitClass", "purchaseCost", "installedCost", "items": {item: USD},
"utilityCost"}, …]`, `"utilitySettings"` and `"versions"`. `inlet` is the inlet as built, with its
`volume` in m³/hr, `water` the balance's mass in kg/hr (null for given flows) and `waterNote` how
it was found. The op refuses, in `flowsheets/train.py`'s words (its own `Refused`): an inlet whose
other components take the whole broth flow, or whose balance chemical cannot fill it; a unit that
cannot be built (`unit <id> (<type>, <class>) could not be built: BioSTEAM said: …`); a unit that
does not converge; and a train that does not converge as a whole.

## geneos ops (geneos worker; OF-BLD-014 §6.2, §6.3, `geneos.py`)

Every request names a model, `{"modelId", "path"}`: `modelId` is a model on the shelf
(`geneos_models.SHELF`) or `toy`, the hand-worked test network, and `path` is the local file of a
fetched model, which `geneos.model_args` sends (a model bundled with cobra needs none). The worker
loads each model once and keeps it, with any add-on route its shelf entry names and a demand on
each product defined by a metabolite; each request works on a fresh copy, so the solver starts
cold. `ceiling`, `frontier` and `mix` close every uptake whose metabolite carries carbon or has no
formula, and open the substrate's at `geneos_models.UPTAKE` (10, `UPTAKE_UNIT` mmol gDW-1 h-1);
the request carries no uptake. A substrate the model has no uptake reaction for, or a product it
has no route to, is a finding with no number: `{"finding", "modelId", "substrate"}` or
`{"finding", "modelId", "product"}`. Every op refuses a `modelId` the shelf lacks, a fetched model
with no `path`, a file whose mapped exchanges no longer carry the names the shelf maps them by,
and an add-on that does not balance; `ceiling`, `frontier` and `mix` also refuse a product or
substrate the shelf does not know.

### `describe`

Request `{"modelId", "path"}`. Result `{"modelId", "reactions", "metabolites", "genes",
"added": [reaction id, …], "growthReaction", "substrates": {substrate: bool}, "products":
{product: bool}, "cobra"}`. The counts are the file's as it publishes them, read before the
worker adds anything; `added` names the reactions the worker added; `growthReaction` is the
reaction the file sets as its objective; `substrates` says, for each of the shelf's sugars, whether
the model has an uptake reaction for it, and `products`, for each product, whether the model has a
route to it; `cobra` is cobra's version. An objective that is not one reaction is refused.
`geneos.py` reads `substrates` and `products` before every `ceiling`, `frontier` and `mix`, and
answers a finding in words from them without calling the op.

### `ceiling`

The most product from one feed (Appendix 2's procedure). Request `{"modelId", "path", "product",
"substrate"}`. Result `{"modelId", "product", "substrate", "exchange", "uptake", "flux",
"molPerMol", "gPerG", "solver", "status"}`: `exchange` is the substrate's exchange reaction, `flux`
the most flux through the product's reaction (the exchange it is secreted by, or the demand on its
metabolite), `molPerMol` that flux over `uptake`, `gPerG` grams of product per gram of substrate,
`solver` the solver interface's name and `status` the solver's status. A solve that is not optimal
is refused. `geneos.py` cites `gPerG`.

### `frontier`

The production envelope over growth. Request `{"modelId", "path", "product", "substrate"}`.
Result `{"modelId", "product", "substrate", "exchange", "uptake", "growthReaction",
"points": [{"growth", "flux", "gPerG"}, …]}`: cobra's `production_envelope` over the growth
reaction at `geneos_models.FRONTIER_POINTS` (12) growth rates, from zero to the most the model
allows, sorted by growth; each point holds the most product flux at that growth (`flux_maximum`)
and its grams per gram. An objective that is not one reaction is refused. `geneos.py` cites the
point with the highest `gPerG`.

### `mix`

The ceiling across mixtures of two sugars at equal carbon. Request `{"modelId", "path", "product",
"a", "b"}`. Result `{"modelId", "product", "a", "b", "carbon", "points": [{"shareA", "uptakeA",
"uptakeB", "flux", "gPerG"}, …]}`. `carbon` is `uptake` times `a`'s carbons; the
`geneos_models.MIX_POINTS` (11) points run from all of that carbon fed as `a` (`shareA` 1) to all
of it fed as `b` (`shareA` 0), each with the two uptakes, the most product flux, and grams of
product per gram of the two sugars fed. A solve that is not optimal is refused. `geneos.py` refuses
a mix of one sugar with itself before it calls, and cites the point with the lowest `gPerG`.
