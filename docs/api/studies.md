# Studies

A study is what a project asks of its plants and keeps of the answers (execution prompt §7.2,
§9.1 step 5). The code is `core/openferment_core/studies/`; a run is an engine run
(`docs/api/runs.md`).

## Scenarios

`StudyScenario` (`core/openferment_core/models.py`), a row of `scenarios` with kind `engine` (the
Proforma screens' rows in the same table are kind `proforma`):

| Field | What it is |
|---|---|
| `id` | `ssc-` and the first twelve hex of the sha256 of the plant, the configuration and the values: the same values on the same plant are one scenario |
| `title`, `note` | A person's words |
| `plant`, `configuration` | A plant on the library shelf (`/api/library`) and one of its configurations |
| `values` | `[{key, quantity}]`: each a parameter the plant reads back, in the parameter's own unit, one value (no range), its `quantity.origin` a `person-assumption` or a `model-estimate` with its author (`by`), its moment (`at`) and what it rests on (`note`) |
| `runIds` | The engine runs made of it, oldest first; a refused run's receipt among them |
| `by`, `at` | Who made it, when |

A scenario is checked against the plant's parameters when it is made: a key the plant does not
read back, a unit it does not use, a parameter it reads back in words, or a key set twice is
refused in words. Running it makes an engine run whose basis names each value's author; the run
is `assumed` and names the scenario (`scenarioId`).

| Route | What it does |
|---|---|
| `GET /api/studies/scenarios` | The project's scenarios, newest first |
| `POST /api/studies/scenarios` | `{title, plant, configuration?, values, note?, by}`: checked and kept |
| `GET /api/studies/scenarios/{id}` | One scenario; 404 for one the project does not hold |
| `POST /api/studies/scenarios/{id}/run` | `{by}`: the engine run's report (`{run, artifact, flowsheet}`); a plant's refusal 422 in its words, the receipt kept with the scenario |

## Comparisons

`StudyComparison`, a row of `comparisons` under the id of the `study.comparison` artifact that
computes it. Its inputs are the runs' artifacts, in the order given, so its provenance is the
weakest of theirs (`assumed` when any run rests on an assumption or an estimate) and it replays
from them; the same runs in the same order are one comparison. The artifact's output:

| Key | What it is |
|---|---|
| `runs` | Each run's artifact id, plant, configuration and provenance |
| `rows` | `[{key, unit, values, change}]`: every number of the price block (`price.<key>`, in BioSTEAM's TEA units) and of a flowsheet's outputs (`outputs.<key>`), each run's value, and its relative change from the first run's |
| `values` | `[{key, values: [{value, unit, origin, by}]}]`: every value any run set for itself, each run's value with its origin; a run that set none has the library's own default (`library-default`, `by` the package module) |

A run its plant refused has no artifact and is refused here in words; so are one run alone, a run
named twice, and a run the project does not hold.

| Route | What it does |
|---|---|
| `GET /api/studies/comparisons` | The project's comparisons, newest first |
| `POST /api/studies/comparisons` | `{title, runIds, by}`: two to twelve runs compared, kept; `{comparison, artifact}` |
| `GET /api/studies/comparisons/{id}` | One comparison with its artifact; 404 for one the project does not hold |
