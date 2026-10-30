# Engine runs

An engine run is one run of a library plant or of an openFerment flowsheet in a project
(execution prompt §7.4; ADR-004, ADR-003, ADR-006). The code is
`core/openferment_core/engine/runs.py`; the computation is `engine/library.py` (`library.run`
artifacts) and the file `engine/sff.py`.

## The record

`EngineRun` (`core/openferment_core/models.py`), one row of the project's `runs` table:

| Field | What it is |
|---|---|
| `id` | The artifact id of the run's basis (sha256 over the tool, its version and the inputs). The same run asked twice is one row |
| `plant`, `configuration` | The plant on the shelf (`/api/library`) and the configuration it ran; a flowsheet's default is named |
| `status` | `done`, or `refused` with the plant's own words in `refused` (a receipt: BioSTEAM's InfeasibleRegion naming its unit, a gate the values failed) |
| `inputs` | Every input of the basis as `{name, quantity}`, the quantity carrying its origin (ADR-006): `library-default` (the plant, the simulator, the settings, all read from the package), `person-assumption` (a value a named person set), `model-estimate` (a value a named model estimated), `convention` (a change the plant needs to build here, the precision kept) |
| `provenance`, `artifactId` | The `library.run` artifact and the provenance computed on its basis: `assumed` when any input is a person's assumption or a model's estimate. None for a refused run |
| `outputs` | The price block, a flowsheet's own outputs (its MESP and yields) and, for a run with no value of its own, how many of the package test's values it holds |
| `versions` | biosteam, thermosteam and biorefineries, as the basis names them |
| `sff` | The SFF file the run wrote: its flowsheet record (`run-<id>`, `docs/api/sff.md`), whether it validates, its completeness score and the tags it earns. `sffRefused` holds the words when no file could be written; the run stands |
| `by`, `at`, `durationMs` | Who asked for the run, when it was kept, how long its computation took |

The tables and the read-back stay in the artifact; a report reads the run, its artifact and its
SFF record together. A request refused before any plant is built (an unknown key, a range, a
scope the plant does not have, a value a person did not name) keeps nothing. A run refused by its
plant is answered from its receipt when asked again, without building the plant.

## Replay

`POST /api/biorepo/artifacts/{id}/replay` runs a run's artifact again from its basis alone. A
library run states its precision (`precision`, ten significant digits), and the replay holds each
number to it: within `atol + rtol·|stored|`, `rtol` one unit in the last kept digit and `atol` the
package test's absolute tolerance (1e-8). `ReplayResult.identical` says whether the output hashes
the same; `withinTolerance` whether every difference is a number within that tolerance;
`tolerance` says what was held.

## Routes

| Route | What it does |
|---|---|
| `POST /api/library/{plant}/run` | `{configuration?, overrides?, by?}`: one engine run, kept; answers the run's report. Values the plant refuses: 422 in its words, the receipt kept |
| `GET /api/runs` | The project's runs, newest first |
| `GET /api/runs/{id}` | `{run, artifact, flowsheet}`: one run's report; 404 for a run the project does not hold |
