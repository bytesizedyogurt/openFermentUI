# Engine runs

A run is one computation of one engine in a project (execution prompt §7.4; ADR-004, ADR-003,
ADR-006, ADR-015). Every run the service keeps has the shape below, whichever engine made it:
`docs/api/engines.md` is the contract an engine is built to. The code is
`core/openferment_core/engine/runs.py`; BioSTEAM's computation is `engine/library.py`
(`library.run` artifacts) and its file `engine/sff.py`.

## The record

`EngineRun` (`core/openferment_core/models.py`), one row of the project's `runs` table:

| Field | What it is |
|---|---|
| `id` | The artifact id of the run's basis (`artifacts.artifact_id`): the first 16 hex characters of the sha256 of the UTF-8 canonical JSON (keys sorted, no spaces, every character outside ASCII kept as itself) of `{"tool", "toolVersion", "inputs"}`, each input `{"name", "value", "unit", "source"}`; `docs/api/engines.md` gives a contract engine's inputs in full. The same run asked twice is one row |
| `engine` | The engine that ran it, as it registered (`GET /api/engines`); the `runs.engine` column. A row kept before engines registered is `biosteam`'s |
| `plant`, `configuration` | What the engine ran and the configuration it ran in: for `biosteam` the plant on the shelf (`/api/library`), a flowsheet's default named; for another engine one of its things |
| `status` | `done`, or `refused` with the plant's own words in `refused` (a receipt: BioSTEAM's InfeasibleRegion naming its unit, a gate the values failed) |
| `inputs` | Every input of the basis as `{name, quantity}`, the quantity carrying its origin (ADR-006): `library-default` (the plant, the simulator, the settings, all read from the package), `person-assumption` (a value a named person set), `model-estimate` (a value a named model estimated), `convention` (a change the plant needs to build here, the precision kept) |
| `provenance`, `artifactId` | The `library.run` artifact and the provenance computed on its basis: `assumed` when any input is a person's assumption or a model's estimate. None for a refused run |
| `outputs` | The price block, a flowsheet's own outputs (its MESP and yields) and, for a run with no value of its own, how many of the package test's values it holds |
| `versions` | biosteam, thermosteam and biorefineries, as the basis names them |
| `sff` | The SFF file the run wrote: its flowsheet record (`run-<id>`, `docs/api/sff.md`), whether it validates, its completeness score and the tags it earns. `sffRefused` holds the words when no file could be written; the run stands |
| `by`, `at`, `durationMs` | Who asked for the run, when it was kept, how long its computation took |

The rows above describe a BioSTEAM run; a contract engine's run fills the same fields as the next
section says. The tables and the read-back stay in the artifact; a report reads the run, its
artifact and its SFF record together. A request refused before any plant is built (an unknown key,
a range, a scope the plant does not have, a value a person did not name) keeps nothing. A run
refused by its plant is answered from its receipt when asked again, without building the plant.

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
| `GET /api/runs/{id}` | `{run, artifact, flowsheet, parameters}`: one run's report; 404 for a run the project does not hold. `parameters` is the run's parameters as the parameter panel reads them (a `ParamScope` of kind `library`): each as its plant declares it, its value the run's, a person's assumption or a model's estimate where the run set one and the library's own default elsewhere, a value outside its bounds flagged (`outOfBounds`) and kept as set, built from the run's artifact alone (`engine/runs.py` `parameters_of`); null for a refused run and for a contract engine's run |
