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
| `plant`, `configuration` | What the engine ran and the configuration it ran in: for `biosteam` the plant on the shelf (`/api/library`), a flowsheet's default named; for another engine one of its things |
| `status` | `done`, or `refused` with the engine's own words in `refused` (a receipt: BioSTEAM's InfeasibleRegion naming its unit, a gate the values failed) |
| `tool`, `toolVersion` | The artifact tool its computation is kept and replayed as, and the tool's version: `library.run` and its version for a BioSTEAM run |
| `inputs` | Every input of the basis as `{name, quantity}`, the quantity carrying its origin (ADR-006): `library-default` (the plant, the simulator, the settings, all read from the package), `person-assumption` (a value a named person set), `model-estimate` (a value a named model estimated), `convention` (a change the plant needs to build here, the precision kept) |
| `provenance`, `artifactId` | The `library.run` artifact and the provenance computed on its basis: `assumed` when any input is a person's assumption or a model's estimate. None for a refused run |
| `outputs` | `values`: each output as `{name, quantity}`, the quantity in the unit the run's artifact states, its origin the artifact (Outputs, below); a library run also keeps its price block, a flowsheet's own outputs (its MESP and yields) and, for a run with no value of its own, how many of the package test's values it holds. A receipt computed nothing, and its `outputs` is `{}` |
| `versions` | The distributions it ran on: biosteam, thermosteam and biorefineries as a library run's basis names them; for a basis that names no simulator, the engine's own `version()` |
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

## Keeping a run

`keep_run(engine, thing, configuration, *, tool, version, basis, by, art | refused, flowsheet |
sff_refused, scenario_id, seed)` keeps one run of any engine's computation as its row, the one
public way a row is kept: the library path (`runs.run`) and every contract engine's run
(`run_engine`) keep theirs through it.

| Argument | What it is |
|---|---|
| `engine` | The engine that ran it: the engine itself, or its name. A name is `biosteam` or one the registry holds (`GET /api/engines` lists it); any other name is refused |
| `thing`, `configuration` | What it ran and the configuration it ran in: the row's `plant` and `configuration` |
| `tool`, `version`, `basis`, `seed` | The computation's tool, tool version, basis inputs and seed; the row's id is the artifact id of the four |
| `art` | The artifact the computation kept: the row is `done`, with the artifact's provenance, id and duration and its outputs read from it. It is the computation of this basis: keep_run refuses an artifact of any other basis |
| `refused` | The engine's words for values it refused inside its computation: the row is a receipt (`refused`, no artifact, no SFF file) the same request is answered from. A call gives `art` or `refused`, one of the two |
| `flowsheet`, `sff_refused` | For a run that computed, one of the two: the run's SFF record (`sff`), or the words for why none was written (`sffRefused`). A run with no plant passes its words. A receipt passes neither |
| `by`, `scenario_id` | Who asked (`this browser` when the request names no one), and the study scenario that asked for it |

A call outside these rules is refused (`ValueError`) and keeps nothing. The same run kept twice
is one row, answered as it was first kept: when the project holds the row already, done with its
SFF record or its words, or as a receipt, keep_run answers it from the store, writes nothing and
says nothing on the event stream, so its `by`, `at` and `scenarioId` stay the first asker's. The
row's `inputs` are the basis as quantities with their origins, and its `versions` the
distributions the basis names, or the engine's own `version()` (the registered engine's, for an
engine given by name) when the basis names no simulator. Keeping a computation publishes `job.done`
on the project's event stream; keeping a receipt publishes `job.failed` with `status` `refused` and
the engine's words. The run's caller publishes `job.queued` and `job.running` before it computes,
and `job.failed` with `status` `failed` for an error that keeps no row.

## Outputs

`outputs.values` holds a run's outputs as typed quantities, read from its artifact alone
(`values_of`): each `{name, quantity}`, the quantity's `unit` the one the artifact states and its
`origin` `{"kind": "artifact", "ref": "<the artifact's id>"}`.

| Tool | `outputs.values` | Beside it |
|---|---|---|
| `library.run` | `price.<key>` for each number of the price block whose unit `price.units` states, then `outputs.<key>` for each of a flowsheet's own outputs (a number or a word) whose unit `outputUnits` states, in the artifact's order | `price`, `outputs` and `regression`, as a library run has always kept them |
| `engine.<name>` | Each output the engine's worker answered, by its own name, in its unit and order | nothing |
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
