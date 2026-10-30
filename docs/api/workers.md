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
| `proforma` | `workers/proforma_worker.py` (with `flowsheets/`, `workers/library_plants.py`, `workers/sff_toolkit.py`, `vendor/pisces_sff`) | biosteam, thermosteam, biorefineries, the SFF toolkit | `benchmark`, `evaluate`, `grid`, `montecarlo`, `run`, `reference`, `thermo_props`, `volatility`, `vessel_specs`, `vessel_design`, `catalogue_specs`, `catalogue_unit_check`, `train_specs`, `flowsheet_unit_values`, `train_run`, `sff_export`, `sff_validate`, `sff_score`, `library_discover`, `library_parameters`, `library_run` |
| `geneos` | `workers/geneos_worker.py` | cobra | `describe`, `ceiling`, `frontier`, `mix` |
| `echo` | `workers/echo_worker.py` | nothing heavy | the protocol's own tests |

Each module's docstring describes its ops; this page gives the SFF and library ops' requests and
results in full. The other ops' request and result schemas are written here as stage 4 reshapes them
(`docs/PROGRESS.md`, Known debts).

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
