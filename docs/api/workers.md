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
| `proforma` | `workers/proforma_worker.py` (with `flowsheets/`, `workers/sff_toolkit.py`, `vendor/pisces_sff`) | biosteam, thermosteam, biorefineries, the SFF toolkit | `benchmark`, `evaluate`, `grid`, `montecarlo`, `run`, `reference`, `thermo_props`, `volatility`, `vessel_specs`, `vessel_design`, `catalogue_specs`, `catalogue_unit_check`, `train_specs`, `flowsheet_unit_values`, `train_run`, `sff_export`, `sff_validate`, `sff_score` |
| `geneos` | `workers/geneos_worker.py` | cobra | `describe`, `ceiling`, `frontier`, `mix` |
| `echo` | `workers/echo_worker.py` | nothing heavy | the protocol's own tests |

Each module's docstring describes its ops; this page gives the SFF ops' requests and results in
full. The other ops' request and result schemas are written here as stage 4 reshapes them
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

A reference biorefinery (a flowsheet module with `load`) is built afresh inside
`package_defaults()`; any other is the worker's warm plant set to `base` and simulated, its
solved price on the product while the file is written. Result: `checked` (below) plus
`"simulator": "BioSTEAM <version>"`.

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
