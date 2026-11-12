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
| `values` | `[{key, quantity}]`: each a parameter the plant reads back, one value (no range), its `quantity.origin` a `person-assumption` or a `model-estimate` with its author (`by`), its moment (`at`) and what it rests on (`note`), the value in the parameter's own unit; or a `measurement`, a reading a person deposited at the bench (Measurements, below), its value and unit the reading's own and its origin `{kind: "measurement", ref: "<deposition id>/<entry id>"}`, kept with the reading's depositor (`by`) and time (`at`) |
| `runIds` | The engine runs made of it, oldest first; a refused run's receipt among them |
| `by`, `at` | Who made it, when |

A scenario is checked against the plant's parameters when it is made: a key the plant does not
read back, a unit it does not use, a parameter it reads back in words, a quantity carrying a
basis, or a key set twice is refused in words. A reading stands in its own unit where that unit
converts into the parameter's (Measurements, below), and the run sets it in the parameter's. Running it makes an engine run on the biosteam
engine's one path for a library plant (`engine/biosteam.py` `run_plant`, the path `POST
/api/library/{plant}/run` takes): each value is the typed input it was made with, checked against
the plant's parameters again and converted by `basis.override_of` into the plant's `Override`, so
the run's basis names each value's author or reading; the run is `assumed` when a value is a
person's or a model's, `measured` when its values are readings beside records and the package's
defaults, and names the scenario (`scenarioId`). A plant that takes a configuration, made with none, is checked against its
default's parameters (`engine/biosteam.py` `default_configuration`) and runs in its default, its
`configuration` kept as made. A kept value its plant's parameters refuse when it is run (a key
the plant no longer reads, a unit it no longer uses) is refused before anything runs, a 422 in
words at the route and the tool's refusal in words, and keeps nothing.

| Route | What it does |
|---|---|
| `GET /api/studies/scenarios` | The project's scenarios, newest first |
| `POST /api/studies/scenarios` | `{title, plant, configuration?, values, note?, by}`: checked and kept |
| `GET /api/studies/scenarios/{id}` | One scenario; 404 for one the project does not hold |
| `POST /api/studies/scenarios/{id}/run` | `{by}`: the engine run's report (`{run, artifact, flowsheet}`); a plant's refusal 422 in its words, the receipt kept with the scenario; a kept value the plant's parameters refuse 422 in words, nothing kept |

### Measurements

A value may be a reading a person deposited at the bench (ADR-006, the implementation note of
2026-11-03): `{"value", "unit", "origin": {"kind": "measurement", "ref": "<deposition id>/<entry
id>"}}`, the value and unit the reading's own. `study_scenario`'s quantity takes the same origin,
the reading alone in it (its kind and ref): a tool's caller who writes a depositor or a time
there is refused in words. Before anything runs, the service looks the reading up in the
project's depositions (`core/openferment_core/measurements.py`, through `basis.resolved`): every
door that takes values does so (a study scenario, fermOS, pureOS, Proforma, the library and the
contract engines), when a scenario is made and again when it runs.

| Rule | Refused in words when |
|---|---|
| Held | the project holds no deposition of that id, or the deposition no entry of that id |
| Confirmed | no person confirmed the entry's number at the bench |
| Standing | a later entry corrects it: on the same measure with no time of its own, for an entry with none; at its own time, for a reading in a series (each reading in a series is its own). A later entry still waiting to be read back corrects it too, and the refusal says the newer number waits |
| Named | the deposition was kept with no person's name (a browser with no name set in Settings keeps its rows as `this browser`), or under a placeholder name, as `biorepo.reviewer_refusal` holds a name |
| A number | the entry holds no number in a unit, or names no time it was taken (an ISO 8601 time) |
| Its own | the value or the unit sent differs from the entry's, or the quantity carries a low, a high or a basis |
| Its maker | the value names a depositor other than the person who kept the deposition, or a time other than the entry's; each is filled from the rows when the value leaves it out |
| Its unit | the entry's unit does not convert into the parameter's through `units.convert`, or converts to no finite number; one that converts is set in the parameter's unit, the conversion stated in the value's note |

A refusal is a 422 at a route and an error from a tool, and nothing runs. A run resting on
readings, records and the package's defaults is `measured`; one beside a person's assumption or
a model's estimate stays `assumed`. A record's class and an artifact computed with no assumption
beside a reading leave the run `measured` (ADR-006's note says what that ranks). Its basis names
each reading as a `deposition` source, its id the reading, its `by` the depositor and its note
the time it was taken (`basis.measurement_source`); `GET /api/runs/{id}` reads each back as a
`measurement` origin.

The service holds a reading's unit to the parameter's. Which measure stands for which parameter
is the scenario maker's choice, kept as the scenario's `by`: the run's basis names the reading,
and nothing in it checks that the reading measured the quantity the parameter is.

| Route | What it answers |
|---|---|
| `GET /api/depositions/readings` | The readings a run may take, the latest taken first (`DepositionReading`): each confirmed entry that stands for its measure, with its `ref`, the runbook and the measure it was recorded against (`runbookId`, `runbook`, `measureId`, `measure`), its own `value` and `unit`, the time it was taken (`at`), its depositor (`by`, the deposition row's maker) and, for a reading in a series, its `hours` into the run |
| `GET /api/depositions/readings?unit=<unit>` | Those whose unit is `<unit>` or converts into it, each with its value in `<unit>` (`inUnit`) and the conversion in words (`note`); an empty unit asks for what a unitless parameter takes. The lookup's own rules decide, so a reading listed is one a value may name |

The screens: a run's page opens NewScenarioDialog, which offers these readings beside a typed
value for each parameter a person sets, each said as what it measured and what it would set; the
run's page reads a measurement in words, linked to the deposition its reading was recorded in,
which opens at the reading, marked. A Proforma scenario's parameter panel offers them too (alpha
2.2 E.17): each numeric row whose rule takes a person's value lists, on asking, the readings in
its parameter's unit or one that converts into it (`GET /api/depositions/readings?unit=`), and a
chosen one is kept as the scope's override in the reading's own value and unit (`Override.unit`,
origin `measurement`, `ref` the reading, `by` its depositor, `at` the time it was taken and
`chosenBy` the person who chose it, the row's maker, each choice audited as `choose_reading`), sent
so by the panel's resolve, the run, the ceiling check and a tool's run of the kept scenario
(`project_state.run_request`, `proforma.inputs_of`), and set in the parameter's unit by the
lookup at each door, the conversion stated in the value's note. A typed value or the row's slider
replaces it with the person's own. The state door keeps a reading in its own unit on a Proforma
scenario's scope alone, and refuses one on any other scope in words. A deposition records
readings at the bench against a locked runbook's measures alone, with no protocol's steps
(RunbookDetail, *The readings alone*,
`/runbooks/depositions/<id>/bench`), once the person has set their name in Settings.

A reading's ref keeps naming one entry: each deposition, entry, observation and measured evidence
id is unique across page loads (`timeId`), and the service keeps a deposition the bench's way
(`project_state.deposition_refusal`): readings and observations appended, each kept with the
value, unit, time and words it was taken with, a read-back moving `confirmed` from false to true,
the state moving from staged to running to closed, and a reconciliation kept as made; closing
stops new readings, observations and sample times; every other write is refused in words, a 422
at `PUT /api/state/depositions/{id}`. A run looks its readings up again each time it runs, and
refuses in words one corrected since.

Each row a page keeps reads as its kind's model in `models.py` (alpha 2.2 E.0b): a deposition
as `Deposition` with its `DepositionEntry` readings, `DepositionObservation` observations and
`Reconciliation`, measured evidence as `MeasuredEvidence`, a Proforma scenario as
`ProformaScenario`, a saved train as `TrainMade`, an override as `Override`, a runbook as
`Runbook`. An override keeps a unit of its own for a deposition's reading alone, its value the
reading's own as deposited; a person's assumption or a model's estimate naming a unit is refused
in words. A write that does not read is a 422 naming the fields, nothing kept. `GET /api/state`
answers a `ProjectState`: each row as the page sent it, a field the page left out staying out (a
deposition, measured evidence, a scenario and a saved train keep the fields their models do not
name), and a row kept before its kind had a model that does not read named in `refused` with its
kind, its id and why, while every other row loads.

A scope's overrides are one row a key (bug hunt H7-04). A page writes a scope with
`PUT /api/state/overrides/{scope}`, `{by, value, base}`: `value` the scope's list as the page now
holds it, `base` the list the page's view stood on (`[]` for a scope it held none of). The service
lays the write on what it keeps key by key (`project_state._merged`): a key the page set or took
back is changed, a key the page left as it read it stays as kept (another page's keys among them),
and a key another page changed since the page read it, which this write changes too, refuses the
whole write, a 422 in words naming the key and who kept it, nothing kept. Two rows compare as the
`Override` model reads them, so `3` and `3.0` are one value. The answer's `value` is the scope as
it then holds, which the page shows; a page whose write was refused reads the project's overrides
again. A write without `base` replaces the scope whole, as every write did before; a write of
another kind naming a `base` is refused in words. Each key is written on its own, so a row the write
leaves as kept keeps its maker and its time. A list naming one key twice is refused in words.

## Comparisons

`StudyComparison`, a row of `comparisons` under the id of the `study.comparison` artifact that
computes it. Its inputs are the runs' artifacts, in the order given, so its provenance is the
weakest of theirs (`assumed` when any run rests on an assumption or an estimate; `computed` at
best, a comparison of measured runs included) and it replays
from them; the same runs in the same order are one comparison. Runs of any engine compare, one
engine's beside another's. Its version says what it read: `study comparison 1` for library runs
alone, read as they have been read since stage 5, and `study comparison 2` for a comparison that
holds a run of another engine (alpha 2.2 D3), a Proforma scenario's run among them, whose price
block it reads from its outputs.values. A value another engine's run names as a library run names
its own (`price.<key>`, `outputs.<key>`) shares that output's row: a Proforma run's solved price
(`price.solvedPrice`) and a library run's meet on one row with its change. A comparison kept at
version 1 over such a run replays at version 2, and its first difference names the two versions.
The artifact's output:

| Key | What it is |
|---|---|
| `runs` | Each run's artifact id, plant (a contract engine's run names its thing, a Proforma run its flowsheet), configuration and provenance |
| `rows` | `[{key, unit, values, change}]`: every output any run answers, each run's value (null for a run with no output of that key), and its relative change from the first run's. A library run's are every number of its price block (`price.<key>`, in BioSTEAM's TEA units) and of a flowsheet's outputs (`outputs.<key>`), read from its artifact as they have always been read; a run of any other engine's are its outputs.values (`values.<name>`, each in its unit; `docs/api/runs.md`, Outputs), a value named `price.<key>` or `outputs.<key>` in the library's row of that key |
| `values` | `[{key, values: [{value, unit, origin, by}]}]`: every value any run set for itself (`basis.is_set`: a person's assumption, a model's estimate, a deposition's reading; a contract engine's run's by its basis name, `value <key>`), each run's value with its origin, a reading's cell with its `ref` beside. At version 1, a run that set none has the library's own default (`library-default`, `by` the package module). At version 2, a library run that set none has that default where its plant declares the value, and every other cell of a value its run holds none of has `value`, `unit`, `origin` and `by` null: a contract engine's artifact keeps no default |

A run its plant refused has no artifact and is refused here in words; so are one run alone, a run
named twice, and a run the project does not hold.

| Route | What it does |
|---|---|
| `GET /api/studies/comparisons` | The project's comparisons, newest first |
| `POST /api/studies/comparisons` | `{title, runIds, by}`: two to twelve runs compared, kept; `{comparison, artifact}` |
| `GET /api/studies/comparisons/{id}` | One comparison with its artifact; 404 for one the project does not hold |

## Runbooks

A study's runbook is a row of the project's `runbooks` in the shape the runbook page keeps
(`Runbook` in `core/openferment_core/models.py`, which the browser reads as its generated twin in
`src/lib/studies.ts`), so it lists and opens there beside a person's. Made from one engine run
(`RunbookCreate`):

| Field | What it is |
|---|---|
| `id` | `rb-study-` and the first twelve hex of the sha256 of the run and the outputs it predicts, each key as asked: the same run and outputs asked again are the runbook kept already, as it stands (a person may have revised a draft), so a runbook of `price.<key>` or `outputs.<key>` keeps its id |
| `predictions` | One point per output asked, its value and unit the run's, `confidence` `low`, `basis` naming the run, its plant and configuration and its provenance, `artifactId` the run's artifact. An output is `values.<name>`, an entry of the run's outputs.values (`docs/api/runs.md`, Outputs), for a run of any engine; a library run also answers `outputs.<key>` of a flowsheet's outputs and `price.<key>` of the price, as it always has, and names the same numbers `values.price.<key>` and `values.outputs.<key>` |
| `measurementSchema` | One measure per prediction, in its unit, at `harvest` |
| `status`, `kind` | `draft`, `research` |
| `lockedAt`, `lockHash` | Null until locked |

An output the run answers with no number and unit, an output asked twice, a run its plant refused
and a run the project does not hold are refused in words.

Locking freezes the predictions and measures under the digest the browser's own code writes
(`core/openferment_core/runbook_lock.py`, a port of `src/engine/lock.ts`, held to the browser's
digests by `tests/test_runbook_lock.py`), with the moment: the lock is kept in `runbook_locks` and
audited, then carried by the row. From then on the store (`project_state.py`) refuses a runbook row
whose predictions or measures are not the ones frozen, from the page or the service alike; its
status and stages still move. A second lock, and a runbook with no prediction, are refused.

A row is answered as it is kept (`response_model_exclude_unset`): a prediction's field the row
leaves out stays out, because the digest reads an absent field and a null one differently.

| Route | What it does |
|---|---|
| `GET /api/studies/runbooks` | The runbooks studies made, newest first |
| `POST /api/studies/runbooks` | `{title, runId, predict: [{output, label}], by}`: made and kept as a draft |
| `GET /api/studies/runbooks/{id}` | Any runbook of the project, a lock the row does not carry laid on; 404 for one it does not hold |
| `POST /api/studies/runbooks/{id}/lock` | `{by}`: locked; 422 when locked already or empty, 404 for an unknown runbook |

## Protocols

A protocol is what the bench walks: a row of the project's `protocols` (migration 0010;
`core/openferment_core/protocols.py`; ADR-017), kept whole as `Protocol`
(`core/openferment_core/models.py`) and served whole. Its own fields are written when it is made;
each version is kept as it was kept, with who kept it (`by`) and when (`at`, ISO 8601 in UTC), the
service writing both, and `currentVersion` names the current one. Every keep is audited in the
keeper's name, a name held to the rule a person's recorded name keeps, and nothing takes a protocol
or a version out.

| Field | What it is |
|---|---|
| `id` | A letter or a digit first, then letters, digits, `.`, `_` or `-`, at most 80 characters, with no colon, since Practice names a step `<protocol>:<step>` |
| `title`, `purpose`, `provenanceNote` | Words: what it is called, what it is for and where it comes from |
| `category` | `media`, `culture`, `analytics`, `harvest`, `fermentation` or `sop` |
| `organisms`, `bsl` | The organisms it is written for, in words, and its biosafety level, 1 or 2 |
| `versions` | One or more `ProtocolVersion`s, each version held once |
| `currentVersion` | One of the versions |

A version (`ProtocolVersion`) holds its `version`, a `changelog`, the `baseBatch` its amounts are
written for (`{value, unit, label}`), its `materials`, `equipment` and `safety` notes, its `steps`,
its `estMinutes` (`{active, total}`) and its `references` (`{paperId, recordId, note}`). A material
(`Material`) holds its `name`, its `amount` and `unit` for the base batch, its `scaling`
(`per_batch_volume`, `fixed` or `per_unit_biomass`), the `precision` a scaled amount is rounded to,
a `stock` it is drawn from (`{conc, unit}`) and the `sourceRecordId` of a record it rests on. A
step (`Step`) holds its `id`, its `text`, with `{{qty:<material>}}` where a material's amount stands
and `{{stock:<material>}}` where the volume of its stock does, a timer (`timerSec`, `timerLabel`),
`multiCheck` items, a `note`, `refs` to records and papers, and the `skills` a person needs to do
it, by their ids in the project's skill catalogue. Every number is finite, `{{qty:...}}` names a
material of its version and `{{stock:...}}` one with a stock, and a version holds each step id and
each material name once; a protocol that breaks one of these is a 422 with a list of field errors.

| Route | What it does |
|---|---|
| `GET /api/protocols` | The project's protocols, by id, each whole |
| `GET /api/protocols/{id}` | One protocol; 404 in words for one the project does not keep |
| `POST /api/protocols` | `{protocol, by}`: a protocol made with its versions; 422 in words for an id the project keeps already (a new version is kept at the next route), a step needing a skill the skill catalogue does not hold, and a keep that names nobody or a placeholder |
| `POST /api/protocols/{id}/versions` | `{version, by}`: a new version, made the current one, and the protocol whole as it now stands; 422 in words for a version the protocol holds already, a step needing a skill the skill catalogue does not hold, and a keep that names nobody or a placeholder; 404 for a protocol the project does not keep |

The readers: Guild's ledger holds an entry recorded at a step to the skills the step needs in any
version of its protocol (`guild.step_skills`); Practice quotes, and a check's brief reads, the
current version of each protocol a step of which needs a skill, its steps in the words the bench
shows at the base batch (a material's amount rounded to its precision, the volume of its stock
rounded to a tenth); and the runbooks module's read lists each protocol with its versions.

## Exports

The project's studies as one zip that opens with nothing of openFerment's: the standard library
reads all of it (`tests/test_exports.py` opens it in `python -I -S`, which leaves every installed
package off the path). The code is `core/openferment_core/studies/exports.py`.

| File | What it holds |
|---|---|
| `study.json` | Every engine run (its inputs as quantities with their origins, its outputs, versions and SFF record), every study scenario, comparison and runbook (as kept), whole, the artifacts that computed the runs and the comparisons, and each deposition a run's or a scenario's reading rests on (`depositions`: `{id, depositedBy, record}`, the record as the bench kept it) |
| `study.md` | The same in words and tables: each run's inputs with their origins (a reading named beside its depositor, `<by>, reading <ref>`), its price in BioSTEAM's TEA units and a flowsheet's outputs in theirs, each scenario's values, each comparison's rows and changes, each runbook's predictions and lock, each deposition's readings with their words at the bench and their confirmations, and the versions |
| `sff/<run>.sff.json` | Each run's flowsheet, byte for byte as the project holds it (its sha256 is the record's) |
| `versions.json` | openFerment's own version and Python's; each run's tool with its simulator, property engine and package; each SFF file's toolkit and schema; each comparison's version; the lock digest's algorithm |
| `manifest.json` | The project, when the package was taken and by whom, and every other file's size and sha256 |

The same study gives the same `study.json`, `study.md`, `versions.json` and SFF files, byte for
byte, and the zip stamps every member alike; the manifest alone says when. A run its plant refused
is there as its receipt, with no artifact and no SFF file.

| Route or command | What it does |
|---|---|
| `GET /api/studies/export?by=` | The package, `application/zip`, named `<project>-studies.zip` |
| `python -m openferment_core.studies.exports OUT.zip` | The same for the project `OPENFERMENT_PROJECT` names, reading that name and the database address alone from `core/.env` when the environment does not set them (ADR-005) |

## Screens

The browser reads every list and report above and computes nothing of its own (`src/lib/studies.ts`).

| Path | Screen | What it shows |
|---|---|---|
| `#/proforma/studies` | `ProformaStudies.tsx` | The project's runs (two or more compared from here), scenarios (each run again from here), comparisons and study runbooks; the export package to download |
| `#/proforma/runs/{id}` | `ProformaRun.tsx` | One run: its parameters in the parameter panel, read-only (the values the run set first, all of them on asking), its basis with each origin, the package's own test, the `RunReport` sections over its artifact (a library run's as one case, a Proforma scenario's with its sensitivity and price distribution over its samples), a contract engine's run's outputs, its SFF file, and a runbook made from its numbers (a library run's `price.<key>` and `outputs.<key>`, any other run's `values.<name>`) |
| `#/proforma/comparisons/{id}` | `ProformaComparison.tsx` | The runs in order, each output's change from the first as a `Tornado` in the figure grammar's `FigureFrame` (the comparison's provenance on every bar), every number run by run, and the values the runs set with their origins |
| `#/runbooks/{id}` | `RunbookDetail.tsx` | A study's runbook beside a person's: each prediction links to the run it came from, and the page locks it under the same digest the service writes |
