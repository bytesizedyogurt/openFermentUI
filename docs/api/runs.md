# Engine runs

A run is one computation of one engine in a project (execution prompt §7.4; ADR-004, ADR-003,
ADR-006, ADR-015). Every run the service keeps has the shape below, whichever engine made it, and
one function keeps it (`keep_run`, below): `docs/api/engines.md` is the contract an engine is built
to. The code is `core/openferment_core/engine/runs.py`; BioSTEAM's computation is
`engine/library.py` (`library.run` artifacts) for a library plant and `proforma.py`
(`proforma.run` artifacts) for a Proforma scenario, and its file `engine/sff.py`.

## The record

`EngineRun` (`core/openferment_core/models.py`), one row of the project's `runs` table:

| Field | What it is |
|---|---|
| `id` | The artifact id of the run's basis (`artifacts.artifact_id`): the first 16 hex characters of the sha256 of the UTF-8 canonical JSON (keys sorted, no spaces, every character outside ASCII kept as itself) of `{"tool", "toolVersion", "inputs"}`, with `"seed"` beside them when the computation takes one, each input `{"name", "value", "unit", "source"}`; `docs/api/engines.md` gives a contract engine's inputs in full. The same run asked twice is one row |
| `engine` | The engine that ran it, as it registered (`GET /api/engines`); the `runs.engine` column. A row kept before engines registered is `biosteam`'s |
| `plant`, `configuration` | What the engine ran and the configuration it ran in: for `biosteam` the plant on the shelf (`/api/library`), a flowsheet's default named, or a Proforma scenario's flowsheet (A Proforma run, below); for `kinetics` a family, `forecast` with the kept fit it drew from, or `vessel` with the kept simulation, fit or forecast it was designed for; for `train` the train's id, with no configuration; for another engine one of its things |
| `status` | `done`, or `refused` with the engine's own words in `refused` (a receipt: BioSTEAM's InfeasibleRegion naming its unit, a gate the values failed) |
| `tool`, `toolVersion` | The artifact tool its computation is kept and replayed as, and the tool's version: `library.run` and its version for a library plant's run, `proforma.run` and its own for a Proforma scenario's, both BioSTEAM's; `fermos.simulation`, `growth_forecast` or `fermos.vessel` at the artifact's own version for a kinetics run; `pureos.train_run` at its own version for a train run |
| `inputs` | Every input of the basis as `{name, quantity}`, the quantity carrying its origin (ADR-006): `library-default` (the plant, the simulator, the settings, all read from the package), `person-assumption` (a value a named person set), `model-estimate` (a value a named model estimated), `measurement` (a reading a person deposited at the bench: `ref` the reading, `<deposition id>/<entry id>`, `by` the person who deposited it, `at` the time it was taken, and in `note` any conversion into the parameter's unit; `docs/api/studies.md`, Measurements), `convention` (a change the plant needs to build here, the precision kept) |
| `provenance`, `artifactId` | The artifact the run's own tool kept (`library.run` for a library plant's run and `proforma.run` for a Proforma scenario's, both BioSTEAM's, `engine.<name>` for a contract engine's, fermOS's for a kinetics run, pureOS's for a train run) and the provenance computed on its basis: `assumed` when any input is a person's assumption or a model's estimate, or rests on one; else `measured` when any input is a measurement; a run at the package's own settings is `computed`. A row held done follows its artifact's provenance when a record the basis rests on is reviewed or demoted since (Keeping a run, below). None for a refused run |
| `outputs` | `values`: each output as `{name, quantity}`, the quantity in the unit the run's artifact states, its origin the artifact (Outputs, below); a library run also keeps its price block, a flowsheet's own outputs (its MESP and yields) and, for a run with no value of its own, how many of the package test's values it holds. A receipt computed nothing, and its `outputs` is `{}` |
| `versions` | The distributions it ran on: biosteam, thermosteam and biorefineries as a library run's basis names them; for a kinetics run, what its thing ran on (A kinetics run, below); for a train run, the versions its basis names, the worker's (A train run, below); for a basis that names no simulator, the engine's own `version()` |
| `sff` | The SFF file the run wrote: its flowsheet record (`run-<id>`, `docs/api/sff.md`), whether it validates, its completeness score and the tags it earns. `sffRefused` holds the words when no file could be written; the run stands |
| `by`, `at`, `durationMs` | Who asked for the run first, when it was first kept, how long its computation took |
| `scenarioId` | The study scenario that asked for it first (`docs/api/studies.md`), or the Proforma scenario a Proforma run belongs to (A Proforma run, below); null for a run asked for directly |

Where a row above names BioSTEAM, a contract engine's run fills it as the next section says. The
tables and the read-back stay in the artifact; a report reads the run, its artifact and its SFF
record together. A request refused before any plant is built (an unknown key, a scope the plant
does not have, a value a person did not name, and for a library plant a range, which is a
study's to sample) keeps nothing. A run refused by its plant is answered from its receipt when
asked again, without building the plant.

## A contract engine's run

An engine built on `WorkerEngine` (`docs/api/engines.md`) keeps each run as a row of the same
`EngineRun`; these fields read so (`engine/runs.py` `run_engine`):

| Field | What it is |
|---|---|
| `engine`, `plant`, `configuration` | The engine's name, the thing it ran and the configuration it ran in |
| `tool` | `engine.<name>`, the artifact tool its runs are computed and replayed as |
| `toolVersion` | The engine's version string: the contract's stem, the engine's name and every distribution it runs on with its version (`engine run 1 · example · openferment-engine-example 0.1.0`) |
| `inputs` | `engine`, `thing`, `configuration` (when the thing takes one), `precision.rtol` and `precision.atol` (the precision the thing states), each a `convention`, then `value <key>` for each value the run sets, its origin the person's assumption or the model's estimate with its day, or the deposition's reading with its depositor and time, set in the parameter's unit before its bounds are checked |
| `outputs` | `values`: each output as `{name, quantity}`, the quantity in the output's unit, its origin the run's artifact (`{"kind": "artifact", "ref": "<artifact id>"}`) |
| `versions` | The engine's `version()`: each distribution it runs on, with its installed version |
| `sff`, `sffRefused` | The file the engine's `sff_export` wrote, validated and scored in the Proforma worker, or the engine's words for why it wrote none |
| `status`, `refused` | `done`, or `refused` with the engine's own words (a receipt the same request is answered from) |

## A kinetics run

The kinetics engine (`core/openferment_core/fermos_engine.py`; `docs/api/engines.md`, The core's
`kinetics`) keeps each simulation, each forecast of a kept fit and each vessel design as a row of
the same `EngineRun`, whichever door asked for it (its routes, its tools, MCP or the engine):

| Field | What it is |
|---|---|
| `engine`, `plant`, `configuration` | `kinetics`; the family simulated with no configuration, `forecast` with the fit's artifact id, or `vessel` with the simulation's, the fit's or the forecast's |
| `id`, `artifactId` | The fermOS artifact's id: the same request at any door is one row |
| `tool`, `toolVersion` | The artifact's own: `fermos.simulation` (`kinetics <family> 2 · scipy <version>`), `growth_forecast` (computed with its seed), or `fermos.vessel` |
| `inputs` | The artifact's basis as quantities with their origins: each parameter's value and source, the records each rests on, the solver's settings, as fermOS writes its basis. A forecast names a start value it sets `start X0`, `start S0` or `start P0`, in the unit of the fitted run's series, and a length it sets `duration`, in hours; a range set on a value adds `<key> low` and `<key> high` beside it |
| `outputs` | `values`, read from the artifact (Outputs, below) |
| `versions` | What its thing ran on, each as its installed metadata records it: numpy and scipy for a family's simulation and a forecast; biosteam and thermosteam as a vessel design's tool version names them, and biorefineries, the package its chemicals are read from, for a design |
| `sff`, `sffRefused` | No file: `sffRefused` says why (a kinetics family is no plant) |
| `status`, `refused` | `done`, or `refused` with fermOS's words for a refusal inside its computation: the integration's, the forecast's draws', BioSTEAM's refusal of a design |
| `by` | The person the route's request names (`by`), or the caller the tool names (`tools/writes._actor`: the model answering, or the person `?by=` names); `this browser` for a request naming no one |

A request fermOS refuses before it computes (a parameter that waits, a value a parameter cannot
take, a fit a forecast cannot draw from, a design with no scale) keeps nothing. The sample run's
forecast keeps nothing. A fermOS artifact kept before its runs were rows has none of its own; the
same request asked again keeps its row.

## A train run

The train engine (`core/openferment_core/pureos/engine.py`; `docs/api/engines.md`, The core's
`train`) keeps each run of a pureOS train as a row of the same `EngineRun`, whichever door asked
for it (`POST /api/pureos/train/run`, the tools `pureos_build` and `pureos_write`, MCP, or `POST
/api/engines/train/run`); `pureos/train_spec.run_train` keeps it, through `compute_kept`:

| Field | What it is |
|---|---|
| `engine`, `plant`, `configuration` | `train`; the train's id; no configuration |
| `id`, `artifactId` | The `pureos.train_run` artifact's id: the same train with the same values at any door is one row |
| `tool`, `toolVersion` | `pureos.train_run` at its own version (`train run 2 · biosteam <version> · thermosteam <version> · biorefineries <version>`) |
| `inputs` | The artifact's basis as quantities with their origins: the train as data, the program and the chemical traced, the inlet with every source (`inlet.<key>`), and each unit's type, class, outlets and every parameter with its source (`<unit id>.<key>`), a value a request set among them (`inputs` named `<unit id>.<key>` or `inlet.<key>`, converted at pureOS's door into the Override of the place's scope) |
| `outputs` | `values`, pureOS's own reading of the run's tables (Outputs, below) |
| `versions` | biosteam, thermosteam and biorefineries as the run's basis names them: the versions the Proforma worker ran |
| `sff`, `sffRefused` | The file asked of the Proforma worker from the run's own basis (`docs/api/sff.md`), kept as `run-<id>`; or the worker's words for why it has none. A train carries no TEA, and the schema the toolkit ships at its pinned commit requires every file's `metadata.TEA_year`, which its exporter reads from the system's TEA, so a train run keeps those words, the reason first, and the worker builds nothing for the file |
| `status`, `refused` | `done`, or `refused` with the Proforma worker's words for a train BioSTEAM cannot build or run (a unit that does not converge, a balance the inlet cannot meet), a receipt the same request is answered from |
| `by` | The person the route's request names (`by`), or the caller the tool names (`tools/writes._actor`); `this browser` for a request naming no one |

A request pureOS refuses before anything runs (an input that names no place or no parameter, a
value its parameter cannot take, the validation's refusals, a value that waits naming what would
bind it, a unit's needs) keeps nothing. A train run kept before its runs were rows has none of its
own; the same request asked again keeps its row.

## A Proforma run

A Proforma scenario's run (`proforma.py`; alpha 2.2 D6) is a run of the `biosteam` engine, kept
as a row of the same `EngineRun` whichever door asked for it: `POST /api/proforma/run`, the tools
`run_flowsheet` and `proforma_write`, MCP, or `POST /api/engines/biosteam/run` on one of the
shelf's scenario flowsheets (`docs/api/engines.md`, The core's `biosteam`). `proforma.keep_run`
keeps it, through `compute_kept`:

| Field | What it is |
|---|---|
| `engine`, `plant`, `configuration` | `biosteam`; the scenario's flowsheet; no configuration, or for a flowsheet built from a vessel and a train (`custom_train_v1`) the two it was built from, `vessel <id>, train run <id>` |
| `id`, `artifactId` | The `proforma.run` artifact's id, over its basis and its seed: the same request at any door is one row |
| `tool`, `toolVersion` | `proforma.run` at `shelf run 2 · biosteam <version> · biorefineries <version>` |
| `inputs` | The artifact's basis as quantities with their origins: the flowsheet, the scenario, the packages the flowsheet borrows, the samples and whether the diagram is drawn, each record a binding rests on, each fit's value and band, and each value a request set with its low and high (`inputs`, converted at Proforma's door into the Override of `proforma:<scenario id>`), a composite's parts and its Finance group beside them |
| `outputs` | `values`: the run's price block (Outputs, below), its solved price named as a library run names its own (`price.solvedPrice`) |
| `versions` | The biosteam engine's `version()`: biosteam, thermosteam and biorefineries as installed, the distributions the Proforma worker ran on (the basis names no simulator) |
| `sff`, `sffRefused` | The base case's file, written by the Proforma worker as the run is kept, from the run's basis alone (`proforma.plant_of`, `docs/api/sff.md`), and kept as `run-<id>`; or the words for why it has none (a base case that could not run has no plant to write) |
| `status`, `refused` | `done`, or `refused` with the Proforma worker's words for a run it refused, a receipt the same request is answered from |
| `scenarioId` | The scenario the run belongs to: a kept scenario's id, an unsaved one's, or, at the engine's door, the scenario flowsheet's own id |
| `by` | The person the route's request names (`ProformaRunRequest.by`), or the caller the tool names (`tools/writes._actor`); `this browser` for a request naming no one |

A request with many cases, a grid over the flowsheet's grid inputs and a Monte Carlo sample of the
inputs' ranges, is one run: one row, whose artifact carries every case; the row holds the price
block. A run whose samples hold no price is kept done, its `values` empty where nothing priced:
`POST /api/proforma/run` answers 422 in words naming it, the engine's route 200 with the row, and
the Runs screen says the run holds no price. A request Proforma refuses before anything runs (an
input that waits for a source, a value its input cannot take, a part of a composite that cannot
stand) keeps nothing.

A run that sets a value writes one convention more in its basis, `assumptions read from:
overrides`, in the words the parameter panel's overrides wrote before a run took typed inputs:
an artifact's id hashes its basis, so a run a person makes through the panel keeps the artifact
id its overrides gave it (alpha 2.2 D6, the amendment at C.4), a Finance value of a composite's
among its values. A Proforma run kept before its runs were rows has none of its own; the same
request asked again finds its artifact and keeps its row. Two kinds of run kept before C.4 are
kept afresh when asked again, under a new id, each earlier artifact standing and replaying as it
was: a run sent through the older `assumptions` field, which retired at C.4 and whose basis
carried no such line, and a run a model's estimate set a value of, which based the estimate as a
person's assumption naming the model and now bases it as the model's estimate (ADR-006), its
output moving with it where the sensitivity reads the estimate's kind.

## Keeping a run

`keep_run(engine, thing, configuration, *, tool, version, basis, by, art | refused, flowsheet |
sff_refused, scenario_id, seed, versions)` keeps one run of any engine's computation as its row,
the one public way a row is kept: the library path (`runs.run`), every contract engine's run
(`run_engine`), the kinetics engine's computations, the train engine's runs and Proforma's
scenario runs (`compute_kept`, below) keep theirs through it.

| Argument | What it is |
|---|---|
| `engine` | The engine that ran it: the engine itself, or its name. A name is `biosteam` or one the registry holds (`GET /api/engines` lists it); any other name is refused |
| `thing`, `configuration` | What it ran and the configuration it ran in: the row's `plant` and `configuration` |
| `tool`, `version`, `basis`, `seed` | The computation's tool, tool version, basis inputs and seed; the row's id is the artifact id of the four |
| `art` | The artifact the computation kept: the row is `done`, with the artifact's provenance, id and duration and its outputs read from it. It is the computation of this basis: keep_run refuses an artifact of any other basis |
| `refused` | The engine's words for values it refused inside its computation: the row is a receipt (`refused`, no artifact, no SFF file) the same request is answered from. A call gives `art` or `refused`, one of the two |
| `flowsheet`, `sff_refused` | For a run that computed, one of the two: the run's SFF record (`sff`), or the words for why none was written (`sffRefused`). A run with no plant passes its words. A receipt passes neither |
| `by`, `scenario_id` | Who asked (`this browser` when the request names no one), and the study scenario that asked for it |
| `versions` | What the thing's computation ran on, when the keeper names it (the kinetics engine names each thing's); otherwise the distributions the basis names, or the engine's own `version()` |

`compute_kept(engine, thing, configuration, *, tool, basis, refusal, sff_refused | write_sff, by,
seed, records_by_id, scenario_id, versions)` is the library path's shape for an engine that
computes in the service's process (the kinetics engine) or through a worker of the core's own (the
train engine, Proforma's runs): a receipt the project holds for the basis is
answered without computing, raising `refusal` in the receipt's words; a row held done answers
its artifact, whose provenance `artifacts.compute` brings up to date when a record the basis rests
on was reviewed or demoted since, and the row's provenance follows it, with nothing else written
and nothing said; otherwise the job is said queued and running, the computation runs through
`artifacts.compute`, a refusal of `refusal`'s kind raised inside it is kept as a receipt and raised
again, any other error says the job failed and keeps no row, and the computation is kept with
its SFF file and `versions`. The file is one of two: a thing that is no plant gives `sff_refused`,
its words; a thing that is a plant gives `write_sff(art, project_id, by)`, which writes and keeps
the record `run-<id>`, the toolkit's or the worker's refusal kept as `sffRefused` and any other
failure (a worker that crashed or timed out) said as the job failed and raised with no row kept, so
the next ask answers the computation from its artifact and writes the file again. A refusal it
raises carries the receipt's id as `run_id`. It answers the artifact.

A call outside these rules is refused (`ValueError`) and keeps nothing. The same run kept twice
is one row, answered as it was first kept: when the project holds the row already, done with its
SFF record or its words, or as a receipt, keep_run answers it from the store, writes nothing and
says nothing on the event stream, so its `by`, `at` and `scenarioId` stay the first asker's. The
row's `inputs` are the basis as quantities with their origins, and its `versions` those the keeper
names, else the distributions the basis names, or the engine's own `version()` (the registered
engine's, for an engine given by name) when the basis names no simulator. Keeping a computation
publishes `job.done` on the project's event stream; keeping a receipt publishes `job.failed` with
`status` `refused` and the engine's words. The run's caller publishes `job.queued` and
`job.running` before it computes, and `job.failed` with `status` `failed` for an error that keeps
no row.

## Outputs

`outputs.values` holds a run's outputs as typed quantities, read from its artifact alone
(`values_of`): each `{name, quantity}`, the quantity's `unit` the one the artifact states and its
`origin` `{"kind": "artifact", "ref": "<the artifact's id>"}`.

| Tool | `outputs.values` | Beside it |
|---|---|---|
| `library.run` | `price.<key>` for each number of the price block whose unit `price.units` states, then `outputs.<key>` for each of a flowsheet's own outputs (a number or a word) whose unit `outputUnits` states, in the artifact's order | `price`, `outputs` and `regression`, as a library run has always kept them |
| `engine.<name>` | Each output the engine's worker answered, by its own name, in its unit and order | nothing |
| `fermos.simulation` | `end.<state>` for each state of the end state in the unit `units` states for it, and `end.t`, the last hour, in hours; then `harvestH` and, where the sugar runs out, `sugarRunsOutH`, in hours | nothing |
| `growth_forecast` | `finals.<role>` for each final of the band (biomass, product, substrate): its median as the value, its 5th and 95th percentiles as `low` and `high`, in the series' unit | nothing |
| `fermos.vessel` | `design.<label>` for each row of the design table holding a number or words, in BioSTEAM's unit for it; a label two rows share carries its unit too (`design.<label> (<unit>)`) | nothing |
| `proforma.run` | The price block: `price.solvedPrice`, the base case's price solved at its TEA's IRR, named as a library run names its own, then `quantiles.p5`, `quantiles.p25`, `quantiles.p50`, `quantiles.p75` and `quantiles.p95`, the price over the samples that held one, each in the unit the artifact states for a price (`tableUnits.price`) and on the basis its TEA states (`tea.basis`, what one unit of the price is of) as the quantity's `basis`; none where the base case or the samples held no price | nothing: the grid, the samples, the sensitivity and the tables stay in the artifact |
| `pureos.train_run` | pureOS's reading of the run's tables, by pass (`pureos.train_of`), registered with the tool (`artifacts.register`'s `values_of`), since the engine package reads no pureOS module: `recovery.<unit id>` for each unit whose recovery is read and `overallRecovery`, each a share with no unit; `productOut`, the product the train delivers, in the stream table's unit of mass flow; then for each stream `massFlow.<stream id>` in that unit, and `purity.<stream id>`, its product share by mass, for each stream that carries product (a share above zero) | nothing |
| any other tool | an empty list, or what the module that registered the tool reads (`values_of`) | nothing |

A row kept before `values` existed lacks the key, and so does a receipt (`outputs` `{}`); a reader
reads its absence as no outputs. A comparison sets runs' outputs side by side, and a runbook
predicts an entry by `values.<name>` (`docs/api/studies.md`).

## Replay

`POST /api/biorepo/artifacts/{id}/replay` runs a run's artifact again from its basis alone. A
library run states its precision (`precision`, ten significant digits), and the replay holds each
number to it: within `atol + rtol·|stored|`, `rtol` one unit in the last kept digit and `atol` the
package test's absolute tolerance (1e-8). A train run keeps every digit BioSTEAM gives and states
no precision, so the same rule holds it exactly: its tool registers no tolerance, a replay of it is
`identical` or names its differences, and the train engine's things state rtol 0, atol 0
(`train_spec.replay_precision`). A contract engine's run is held to the precision its thing states
(`precision.rtol` and `precision.atol` in its basis). A Proforma run registers no tolerance either:
its replay is `identical` or names its differences, and the biosteam engine's scenario flowsheets
state rtol 0, atol 0. `ReplayResult.identical` says
whether the output hashes the same; `withinTolerance` whether every difference is a number within
that tolerance; `tolerance` says what was held. A replay computes with the tool registered now:
when its version differs from the one the run was kept at, the first of `differences` is
`toolVersion`, the kept version beside the one the replay ran at, an identical output included.
Lists are compared in order.

## Routes

| Route | What it does |
|---|---|
| `POST /api/library/{plant}/run` | `{configuration?, inputs?, by?}`, its fields alone: one engine run of a library plant, kept, on the biosteam engine's own path (`engine/biosteam.py` `run_plant`: a plant that takes a configuration, asked with none, runs in its default; each value checked against the plant's parameters before the plant is built); answers the run's report. A value refused before anything runs: 422 in words, nothing kept. Values the plant refuses: 422 in its words, the receipt kept |
| `POST /api/proforma/run` | `{scenarioId, inputs?, by?, flowsheet?, host?, fits?, samples?, seed?, vessel?, trainRun?}`, its fields alone: one Proforma scenario's run, kept as a row of the biosteam engine (A Proforma run, above); answers the run (`ProformaRunResult`) |
| `GET /api/proforma/scenarios` | Every BioSTEAM scenario the project keeps, each with its inputs bound to records as its run binds them, keeping nothing (alpha 2.2 D9): a `custom_train_v1` scenario binds with the vessel design and the train run it names, and a scenario whose binding is refused, or whose flowsheet the shelf no longer holds (a retired entry's id, D8), is listed with the refusal in words (`refused`, its `inputs` empty), where one such scenario once answered 500 for the whole list; `?host=` is passed to each binding as `GET /api/proforma/bind` takes it |
| `GET /api/proforma/bind`, `GET /api/proforma/ceiling-check` | Two reads that bind a scenario's inputs as its run binds them, keeping nothing: `?inputs=` carries the values a person sets as a run's request carries them, converted at Proforma's door (the binding on the flowsheet's own scope, `proforma:<flowsheet id>`); the retired `?overrides=`, and `?assumptions=` at the ceiling check, are refused in words naming `?inputs=` |
| `POST /api/engines/{name}/run` | `{thing, configuration?, inputs?, by?}`: one run of any registered engine's thing, kept; answers the run's report (`docs/api/engines.md`) |
| `POST /api/pureos/train/run` | `{train, inputs?, by?}`: one run of a train, kept as a row of the engine `train`; answers the train run (`TrainRun`) |
| `GET /api/runs` | The project's runs, newest first; `?engine=<name>` the runs one engine made |
| `GET /api/runs/{id}` | `{run, artifact, flowsheet, parameters}`: one run's report; 404 for a run the project does not hold. `parameters` is a library run's parameters as the parameter panel reads them (a `ParamScope` of kind `library`): each as its plant declares it, its value the run's, a person's assumption, a model's estimate or a deposition's reading where the run set one and the library's own default elsewhere, a value outside its bounds flagged (`outOfBounds`) and kept as set, built from the run's artifact alone (`engine/runs.py` `parameters_of`); null for a refused run and for a run of any other tool |
