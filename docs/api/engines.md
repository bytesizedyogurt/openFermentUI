# The engine contract

An engine is a package that computes runs for openFerment: it says what it can run, what each
thing it runs takes, and it runs one with typed values. The service keeps every run of every
engine as one row of one shape (`docs/api/runs.md`), replays it within the precision the engine
states, writes its SFF file where the engine has a plant (`docs/api/sff.md`), and shows it on the
Runs screen. ADR-015 records why the contract has this shape.

This page is enough to build an engine. It uses three more pages: `docs/api/workers.md` (the
JSON-lines protocol an engine's worker speaks), `docs/api/runs.md` (the row a run becomes) and
`docs/api/openapi.json` (the routes and every model by name). Every example value below is a
placeholder in a placeholder unit; an engine package carries no composition, yield, price, titre
or finding of a paper, as the service carries none.

## What an engine is

A Python package that registers **one object** under the entry-point group
`openferment.engines`. The entry point's name is the engine's name:

```toml
[project.entry-points."openferment.engines"]
example = "openferment_engine_example.engine:ENGINE"
```

- The service never imports an engine by name. At startup it reads the group
  (`importlib.metadata.entry_points(group="openferment.engines")`) and loads each object.
- The package installs into the service's Python environment, beside the service:
  `cd core && uv pip install -e <path to the package>`. `uv sync` keeps only what `core/uv.lock`
  names, so after a sync install it again; `uv run`, which every `pnpm` command uses, keeps it.
- The module the entry point names is imported by the service process. It must import nothing
  heavy: an engine's computation happens in its **worker**, a process of its own.
- The engines in the repository register the same way, from `core/pyproject.toml`: `biosteam`
  (the library plants and openFerment's composed flowsheet).

## What it declares

The object has these attributes and methods. `openferment_core.engine.WorkerEngine` (below)
implements every method over four worker ops, so an engine built on it declares the attributes
and writes the worker.

| Name | Type | What it is |
|---|---|---|
| `name` | `str` | Lowercase letters, digits and `-`, starting with a letter; the entry point's name, the `engine` column of every run it makes, and the `?engine=` filter |
| `worker` | `str` or `None` | The dotted module of the engine's worker: the service starts `python -m <worker>` and speaks the protocol of `docs/api/workers.md`. Heavy imports live here alone. `None` for an engine that computes in the service's own process with nothing heavy, whose `heavy` is then `()` |
| `heavy` | `tuple[str, ...]` | The modules the worker computes with, which the service process must never import (conformance check 6); `()` for an engine that computes with nothing heavy |
| `version()` | `dict[str, str]` | The distributions the engine runs on, each with its installed version: `{"openferment-engine-example": "0.1.0"}`. It is the run's `versions`, and it enters every run's id |
| `things()` | `list[EngineThing]` | What the engine can run, each with its configurations and its precision |
| `parameters(thing, configuration)` | `list[EngineParameter]` | What one thing takes: each parameter a `ParameterSpec` with its default and the default's origin |
| `run(thing, configuration, inputs, by)` | `EngineRun` | One run, kept as one `runs` row. `inputs` is a list of `EngineInput`, each a named `Quantity`; `by` names the person or the model asking |
| `replay(run)` | `ReplayResult` | The run computed again from its basis alone, each output held within the stated precision |
| `export_sff(run)` | `SFFFlowsheet` or words | The run's SFF file as its flowsheet record (`GET /api/flowsheets/{id}`), validated and scored, or the words that say why there is none |

### `EngineThing`

```json
{"id": "a-thing", "title": "A thing the engine runs", "kind": "placeholder",
 "configurations": ["one way", "another way"], "defaultConfiguration": "one way",
 "precision": {"rtol": 1e-12, "atol": 0}}
```

- The fields are those `GET /api/library` answers for a plant (`id`, `title`, `kind`,
  `configurations`, `defaultConfiguration`), with the thing's `precision`.
- `id`: letters, digits, `.`, `_` and `-`. A run names it as its `plant`.
- `configurations`: the configurations it runs in, or `[]` when it takes none. A run that names
  no configuration runs in `defaultConfiguration`.
- `precision`: how near a replay's numbers must come to the run's: within
  `atol + rtol·|stored|` for every output. It enters each run's basis as `precision.rtol` and
  `precision.atol`.

### `EngineParameter`

```json
{"key": "a-parameter", "label": "A placeholder parameter", "unit": "placeholder-unit",
 "value": 1.5, "origin": {"kind": "library-default", "ref": "openferment-engine-example@0.1.0"},
 "min": 0, "max": 10, "boundsReason": "why a run may set it only between these"}
```

```json
{"key": "a-setting", "label": "A placeholder setting", "unit": "", "value": "one",
 "choices": ["one", "another"], "boundsReason": "a setting chosen from its words, with no bounds",
 "origin": {"kind": "convention", "note": "what the setting is"}}
```

A `ParameterSpec` (the shape every parameter panel reads) with its default and the default's
origin:

- `key`, `label` and `unit` name it; `unit` is `""` for a share, a pure number or a choice.
- `value` is the default the engine uses when a run sets none: a number, or one of `choices` for
  a parameter chosen from words.
- `origin` says where the default comes from: `library-default` with `ref` naming the package
  and version it was read from, or `convention` with a `note` for a software setting (a step
  count, a tolerance). Every parameter carries one.
- `min` and `max`, when given, bound what a run may set; `boundsReason` says why, in words, and
  every parameter carries one, a parameter with no bounds included.
- The panel's other fields may be left out: `symbol`, `gloss`, `dimension`, `step`, `scale`
  (`linear` or `log`), `group` (`parameters`) and `note`. `sourceRule` defaults to the origin's
  kind.

### `EngineInput`

```json
{"name": "a-parameter", "quantity": {"value": 2.5, "unit": "placeholder-unit",
 "origin": {"kind": "person-assumption", "by": "A. Person", "note": "what it rests on"}}}
```

- The shape a run's inputs have (`RunInput`): `name` is a parameter's key; `quantity` is a typed
  value in that parameter's unit, carrying its origin: `person-assumption` (`by` the person) or
  `model-estimate` (`by` the model's id).
- A value set is checked against the thing's parameters before the worker sees it: a key the
  thing declares, set once, in the parameter's unit, a number for a number and one of `choices`
  for words, inside `min` and `max`. A value refused keeps nothing.
- A number is accepted only inside a `quantity`. A bare JSON number anywhere in a request is
  refused in words before the engine's worker is reached.

## The worker

The service starts the worker with the service's own interpreter, `python -m <worker>`, through
`SimWorker` (`docs/api/workers.md`), on first use. Its environment is the service's with every
key, token, password and database address removed: a worker never receives the model key or the
database. It reads one JSON request per line on stdin and writes one JSON response per line on
stdout.

`openferment_core.workers.serve` runs that loop. A worker module maps each op to a function of
its arguments and ends:

```python
from openferment_core.workers import serve

HANDLERS = {"things": things, "parameters": parameters, "run": run, "sff_export": sff_export}

if __name__ == "__main__":
    serve(HANDLERS, name="example")
```

`serve` answers `ping` itself. A function refuses a request by raising an exception whose class
is named `Refused`; its words reach the person as they are written, with no traceback. Any other
exception is a failure of the worker, said as `<ExceptionType>: <words>`.

### `WorkerEngine`

```python
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="example", worker="openferment_engine_example.worker",
                      distributions=("openferment-engine-example",))
```

`version()` reads each named distribution's installed version. Every other method calls one op
of the worker:

| Op | Request `args` | Result |
|---|---|---|
| `things` | `{}` | `{"things": [EngineThing, …]}` |
| `parameters` | `{"thing", "configuration"}` | `{"parameters": [EngineParameter, …]}` |
| `run` | `{"thing", "configuration", "inputs": [{"name", "value", "unit"}, …]}` | `{"outputs": [{"name", "value", "unit"}, …]}`: every output a number or a string in a unit |
| `sff_export` | `{"thing", "configuration", "inputs": […]}` | `{"flowsheet": <an SFF document>}`, or `Refused: <words>` when the engine has no plant |

The worker receives the values a run sets, already checked against the parameters: each
`name` a key of the thing, each `unit` the parameter's, each number inside its bounds. A
parameter a run leaves alone is the worker's default. The same request must give the same
outputs, within the precision the thing states.

## What the service does with an engine

- **Discovery.** At startup `engine/registry.py` loads every object of the group. An engine
  that fails to load, or whose object lacks a declared name or method, is listed with its error
  in words, and the service keeps running.
- **`GET /api/engines`**: each engine's name, version, worker module and status, things, the
  error that keeps it from loading (when one does) and its last conformance verdict.
- **`GET /api/engines/{name}/parameters?thing=&configuration=`**: the thing's parameters.
- **`POST /api/engines/{name}/run`**: `{thing, configuration?, inputs?, by?}` runs one thing and
  answers the run's report (`RunReport`). A request the engine refuses is a 422 in its words; a
  refused run is kept as a receipt and answered from it when asked again.
- **The run's row.** The run's id is the sha256 of the engine's tool name (`engine.<name>`), its
  version string (the engine's name and every distribution with its version) and the run's basis:
  the thing, the configuration, the precision and every input with its origin. The same request
  twice is one row. `created_by` is the request's person or model. Provenance is computed from the
  inputs' origins (`basis.py`): `computed` for a run at the engine's own defaults, `assumed` when
  any input is a person's assumption or a model's estimate.
- **Outputs.** Each output is kept as a typed quantity, its origin the run's own artifact:
  `outputs.values` is `[{"name", "quantity": {"value", "unit", "origin": {"kind": "artifact",
  "ref": "<the run's artifact id>"}}}, …]`.
- **The SFF file.** After the run, the worker's `sff_export` is asked once. A document is
  validated and scored by the vendored toolkit in the service's own Proforma worker and kept as
  the flowsheet record `run-<id>` (`docs/api/sff.md`); words are kept as the run's `sffRefused`.
  Either way the run stands, and `export_sff(run)` answers the record or the words.
- **Replay.** `POST /api/biorepo/artifacts/{id}/replay` computes the run again from its basis
  and holds every output within the stated precision (`withinTolerance`).
- **`GET /api/runs?engine=<name>`** lists one engine's runs; the Runs screen shows the engine of
  every run and filters by it.
- **Tools.** `engine_plants`, `engine_parameters`, `engine_run` and `engine_report` take `engine`
  (default `biosteam`), so Postdoc and any MCP client run every engine the same way.
- **`pnpm ready`** prints one row per engine: its version, its worker and its conformance verdict.

## Conformance

`python -m openferment_core.engine.conform <name>` checks an installed engine against this page
and prints one row per check, on a database of its own that it drops after; it exits 1 when any
check fails, and keeps its verdict for `GET /api/engines`. `pnpm prove` runs it for every engine
registered.

| # | Check |
|---|---|
| 1 | A JSON number outside a `quantity` is refused in words before the worker is reached |
| 2 | Every parameter of every thing carries an origin: `library-default` with `ref`, or `convention` with `note` |
| 3 | A run writes one `runs` row keyed by its basis, and the same request twice is that one row |
| 4 | A replay holds every output within the precision the thing states |
| 5 | The run's SFF file validates and scores, or `sffRefused` holds words |
| 6 | Importing the module the entry point names imports neither the worker module nor what the engine computes with |
| 7 | A request the engine cannot run is refused with a receipt in words, with no traceback |
| 8 | `created_by` on every run is the person or the model that asked for it |

## What is deliberately absent

- No socket for kinetic models beyond what an engine computes in its own worker.
- No scenario fields beyond parameters: a scenario is a thing, a configuration and values for its
  parameters (`docs/api/studies.md`).
- No import of an SFF file into an engine: a file is a record, and an engine's recipe is code.
- No science on this page: every value is a placeholder.
