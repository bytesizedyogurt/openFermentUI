# Engine runs

A run is one computation of one engine in a project (execution prompt §7.4; ADR-004, ADR-003,
ADR-006, ADR-015). Every run the service keeps has the shape below, whichever engine made it, and
one function keeps it (`keep_run`, below): `docs/api/engines.md` is the contract an engine is built
to. The code is `core/openferment_core/engine/runs.py`; BioSTEAM's computation is
`engine/library.py` (`library.run` artifacts) and its file `engine/sff.py`.

## The record

`EngineRun` (`core/openferment_core/models.py`), one row of the project's `runs` table:

| Field | What it is |
|---|---|
| `id` | The artifact id of the run's basis (`artifacts.artifact_id`): the first 16 hex characters of the sha256 of the UTF-8 canonical JSON (keys sorted, no spaces, every character outside ASCII kept as itself) of `{"tool", "toolVersion", "inputs"}`, with `"seed"` beside them when the computation takes one, each input `{"name", "value", "unit", "source"}`; `docs/api/engines.md` gives a contract engine's inputs in full. The same run asked twice is one row |
| `engine` | The engine that ran it, as it registered (`GET /api/engines`); the `runs.engine` column. A row kept before engines registered is `biosteam`'s |
| `plant`, `configuration` | What the engine ran and the configuration it ran in: for `biosteam` the plant on the shelf (`/api/library`), a flowsheet's default named; for `kinetics` a family, `forecast` with the kept fit it drew from, or `vessel` with the kept simulation, fit or forecast it was designed for; for another engine one of its things |
| `status` | `done`, or `refused` with the engine's own words in `refused` (a receipt: BioSTEAM's InfeasibleRegion naming its unit, a gate the values failed) |
| `tool`, `toolVersion` | The artifact tool its computation is kept and replayed as, and the tool's version: `library.run` and its version for a BioSTEAM run; `fermos.simulation`, `growth_forecast` or `fermos.vessel` at the artifact's own version for a kinetics run |
| `inputs` | Every input of the basis as `{name, quantity}`, the quantity carrying its origin (ADR-006): `library-default` (the plant, the simulator, the settings, all read from the package), `person-assumption` (a value a named person set), `model-estimate` (a value a named model estimated), `convention` (a change the plant needs to build here, the precision kept) |
| `provenance`, `artifactId` | The artifact the run's own tool kept (`library.run` for a BioSTEAM run, `engine.<name>` for a contract engine's, fermOS's for a kinetics run) and the provenance computed on its basis: `assumed` when any input is a person's assumption or a model's estimate. A row held done follows its artifact's provenance when a record the basis rests on is reviewed or demoted since (Keeping a run, below). None for a refused run |
| `outputs` | `values`: each output as `{name, quantity}`, the quantity in the unit the run's artifact states, its origin the artifact (Outputs, below); a library run also keeps its price block, a flowsheet's own outputs (its MESP and yields) and, for a run with no value of its own, how many of the package test's values it holds. A receipt computed nothing, and its `outputs` is `{}` |
| `versions` | The distributions it ran on: biosteam, thermosteam and biorefineries as a library run's basis names them; for a kinetics run, what its thing ran on (A kinetics run, below); for a basis that names no simulator, the engine's own `version()` |
| `sff` | The SFF file the run wrote: its flowsheet record (`run-<id>`, `docs/api/sff.md`), whether it validates, its completeness score and the tags it earns. `sffRefused` holds the words when no file could be written; the run stands |
| `by`, `at`, `durationMs` | Who asked for the run first, when it was first kept, how long its computation took |
| `scenarioId` | The study scenario that asked for it first (`docs/api/studies.md`); null for a run asked for directly |

Where a row above names BioSTEAM, a contract engine's run fills it as the next section says. The
tables and the read-back stay in the artifact; a report reads the run, its artifact and its SFF
record together. A request refused before any plant is built (an unknown key, a range, a scope the
plant does not have, a value a person did not name) keeps nothing. A run refused by its plant is
answered from its receipt when asked again, without building the plant.

## A contract engine's run

An engine built on `WorkerEngine` (`docs/api/engines.md`) keeps each run as a row of the same
`EngineRun`; these fields read so (`engine/runs.py` `run_engine`):

| Field | What it is |
|---|---|
| `engine`, `plant`, `configuration` | The engine's name, the thing it ran and the configuration it ran in |
| `tool` | `engine.<name>`, the artifact tool its runs are computed and replayed as |
| `toolVersion` | The engine's version string: the contract's stem, the engine's name and every distribution it runs on with its version (`engine run 1 · example · openferment-engine-example 0.1.0`) |
| `inputs` | `engine`, `thing`, `configuration` (when the thing takes one), `precision.rtol` and `precision.atol` (the precision the thing states), each a `convention`, then `value <key>` for each value the run sets, its origin the person's assumption or the model's estimate with its day |
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

## Keeping a run

`keep_run(engine, thing, configuration, *, tool, version, basis, by, art | refused, flowsheet |
sff_refused, scenario_id, seed, versions)` keeps one run of any engine's computation as its row,
the one public way a row is kept: the library path (`runs.run`), every contract engine's run
(`run_engine`) and the kinetics engine's computations (`compute_kept`, below) keep theirs through
it.

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

`compute_kept(engine, thing, configuration, *, tool, basis, refusal, sff_refused, by, seed,
records_by_id, scenario_id, versions)` is the library path's shape for an engine that computes in
the service's process (the kinetics engine): a receipt the project holds for the basis is
answered without computing, raising `refusal` in the receipt's words; a row held done answers
its artifact, whose provenance `artifacts.compute` brings up to date when a record the basis rests
on was reviewed or demoted since, and the row's provenance follows it, with nothing else written
and nothing said; otherwise the job is said queued and running, the computation runs through
`artifacts.compute`, a refusal of `refusal`'s kind raised inside it is kept as a receipt and raised
again, any other error says the job failed and keeps no row, and the computation is kept with
`sff_refused` and `versions`. A refusal it raises carries the receipt's id as `run_id`. It answers
the artifact.

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
| any other tool | an empty list | nothing |

A row kept before `values` existed lacks the key, and so does a receipt (`outputs` `{}`); a reader
reads its absence as no outputs. A comparison sets runs' outputs side by side, and a runbook
predicts an entry by `values.<name>` (`docs/api/studies.md`).

## Replay

`POST /api/biorepo/artifacts/{id}/replay` runs a run's artifact again from its basis alone. A
library run states its precision (`precision`, ten significant digits), and the replay holds each
number to it: within `atol + rtol·|stored|`, `rtol` one unit in the last kept digit and `atol` the
package test's absolute tolerance (1e-8). A contract engine's run is held to the precision its
thing states (`precision.rtol` and `precision.atol` in its basis). `ReplayResult.identical` says
whether the output hashes the same; `withinTolerance` whether every difference is a number within
that tolerance; `tolerance` says what was held. A replay computes with the tool registered now:
when its version differs from the one the run was kept at, the first of `differences` is
`toolVersion`, the kept version beside the one the replay ran at, an identical output included.
Lists are compared in order.

## Routes

| Route | What it does |
|---|---|
| `POST /api/library/{plant}/run` | `{configuration?, overrides?, by?}`: one engine run, kept; answers the run's report. Values the plant refuses: 422 in its words, the receipt kept |
| `POST /api/engines/{name}/run` | `{thing, configuration?, inputs?, by?}`: one run of any registered engine's thing, kept; answers the run's report (`docs/api/engines.md`) |
| `GET /api/runs` | The project's runs, newest first; `?engine=<name>` the runs one engine made |
| `GET /api/runs/{id}` | `{run, artifact, flowsheet, parameters}`: one run's report; 404 for a run the project does not hold. `parameters` is a library run's parameters as the parameter panel reads them (a `ParamScope` of kind `library`): each as its plant declares it, its value the run's, a person's assumption or a model's estimate where the run set one and the library's own default elsewhere, a value outside its bounds flagged (`outOfBounds`) and kept as set, built from the run's artifact alone (`engine/runs.py` `parameters_of`); null for a refused run and for a run of any other tool |
