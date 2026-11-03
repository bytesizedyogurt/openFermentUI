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
  (`importlib.metadata.entry_points(group="openferment.engines")`) and loads each object once.
  The group is read once per process: install an engine, then restart the service.
- Two packages that register one name are both set aside, said in words; when one of them is
  the service's own distribution (`openferment-core`), its engine keeps the name and the other is
  set aside.
- The package installs into the service's Python environment, beside the service:
  `cd core && uv pip install -e <path to the package>`, then restart the service. `uv sync`
  keeps only what `core/uv.lock` names, so after a sync install it again; `uv run`, which every
  `pnpm` command uses, keeps it.
- A new version takes effect when the package is installed again: raise the version in the
  package's `pyproject.toml`, run `cd core && uv pip install -e <path to the package>` again, then
  restart the service. An installed package's version is the one its metadata recorded when it
  was installed, and an edit of its code alone leaves that version as it was.
- The module the entry point names is imported by the service process, during startup, with no
  time limit of its own: its import returns promptly and imports nothing heavy. An engine's
  computation happens in its **worker**, a process of its own. An entry module whose import brings
  into the service's process its worker module (or a module below it), a heavy module it declares,
  or one of `biosteam`, `thermosteam`, `biorefineries`, `pisces_sff` and `cobra` is set aside,
  those modules named. Discovery counts the modules an entry module's import adds to those the
  service had already imported; conformance check 6, in a process of its own, holds every one
  out.
- Installing an engine trusts its code with whatever the service's user can read, `core/.env`
  included: its entry module runs in the service's process, and its worker runs as the same user.
- The engines in the repository register the same way, from `core/pyproject.toml`: `biosteam`
  (the library plants and openFerment's composed flowsheet).

## What it declares

An engine from outside the core is built on `openferment_core.engine.WorkerEngine` (below), which
implements every method over four worker ops: the package declares the engine's name, its worker,
its distributions and the heavy modules its worker computes with (`heavy`, which conformance
check 6 holds), and writes the worker. The table lists what the service asks of every engine, the
core's own `biosteam` among them.

| Name | Type | What it is |
|---|---|---|
| `name` | `str` | Lowercase letters, digits and `-`, starting with a letter, at most 40 characters; the entry point's name, the `engine` column of every run it makes, and the `?engine=` filter |
| `worker` | `str` or `None` | The dotted module of the engine's worker: the service runs it as `python -m <worker>` would (The worker, below) and speaks the protocol of `docs/api/workers.md`. Heavy imports live here alone. `None` for an engine that computes in the service's own process with nothing heavy, whose `heavy` is then `()` |
| `heavy` | `tuple[str, ...]` | The modules the worker computes with, which the service keeps out of its process (conformance check 6); each name covers its module and every module below it (`a.b` covers `a.b` and `a.b.c`). `()` for an engine that computes with nothing heavy. The service keeps `biosteam`, `thermosteam`, `biorefineries`, `pisces_sff` and `cobra` out for every engine, whatever it declares |
| `version()` | `dict[str, str]` | The distributions the engine runs on, each with the version its installed metadata records: `{"openferment-engine-example": "0.1.0"}`; a distribution that is not installed reads `"not installed"`, and enters the version string so. It is the run's `versions`, and it enters every run's id. It changes whenever the engine's computation changes: an editable install keeps its version across edits of its code, so a new version goes with every change to what a run computes (installed again, as above), and the service then computes the request afresh |
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
- `id`: starts with a letter or a digit, then letters, digits, `.`, `_` and `-`, at most 80
  characters. A run names it as its `plant`.
- `configurations`: the configurations it runs in, each name 1 to 80 characters, or `[]` when it
  takes none. `defaultConfiguration` is one of them, or null.
- A request that names no configuration runs in `defaultConfiguration`. A thing with
  configurations and no `defaultConfiguration` is run with a configuration named, and a request
  naming none is refused in words; so is a configuration the thing does not name, and any
  configuration for a thing that takes none. The rule holds at every door: the run route, the
  parameters route and the engine tools, so the worker's `parameters` op receives the
  configuration a run would use.
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
 "origin": {"kind": "person-assumption", "by": "A. Person", "at": "2026-10-30",
            "note": "what it rests on"}}}
```

- The shape a run's inputs have (`RunInput`): `name` is a parameter's key; `quantity` is a typed
  value in that parameter's unit, carrying its origin: `person-assumption` (`by` the person) or
  `model-estimate` (`by` the model's id).
- `at` is the day the value was set, and every value carries one: a value without it is refused
  in words. The day enters the run's basis, and the service stamps no day of its own, so the same
  request is one run whatever day it arrives.
- A value set is checked against the thing's parameters before the worker sees it: a key the
  thing declares, set once, in the parameter's unit, a number for a number and one of `choices`
  for words, inside `min` and `max`. A key the thing lacks is refused with the number of its
  parameters and the few keys nearest to it. A value refused keeps nothing.
- A value a contract engine's run sets is its `value` and `unit` with its `origin`: a quantity
  that also carries `low`, `high` or `basis` is refused in words, since the worker receives the
  value and unit alone.
- BioSTEAM checks the key, the unit and the kind the same way (`runs.check_inputs`); a library
  plant's bounds are flagged by the library on the run's parameters (`ParameterValue.outOfBounds`),
  the value kept as set, never clamped. Its door passes `low` and `high` to the plant as the
  `Override`'s, which the library takes equal to the value (a range is a study's to sample), and
  refuses a `basis` in words.
- A number is accepted only inside a `quantity`. A bare JSON number anywhere in a request, a
  field the request or a quantity does not name, and a `value`, `low` or `high` that is `true` or
  `false` are each refused in words before the engine's worker is reached.

## The worker

The service starts the worker with the service's own interpreter through `SimWorker`
(`docs/api/workers.md`), on first use, with `core/` as its working directory: a launcher
(`workers.LAUNCH`) points descriptor 1 at stderr, then runs `<worker>` as `python -m <worker>`
would, so a library that prints, as the module is imported or while it serves, writes to stderr.
It reads one JSON request per line on stdin and writes one JSON response per line on stdout.

Its environment is the service's less every variable `workers.withheld` names: each whose name
begins `ANTHROPIC_` or `SCI_RAG_`, and each whose name holds `KEY`, `TOKEN`, `SECRET`,
`PASSWORD`, `PASSWD`, `DATABASE_URL` or `CREDENTIAL` anywhere, in any case. A setting the worker
needs, a solver's licence among them, reaches it under a name the rule passes, such as a variable
naming the path of the engine's own settings file.

`openferment_core.workers.serve` runs that loop. A worker module maps each op to a handler; each
handler takes the request's `args` as one dict and returns the result object, which `serve` writes
as JSON:

```python
from openferment_core.workers import serve


class Refused(Exception):
    """A request the engine refuses, said in its words."""


def things(args: dict) -> dict:
    return {"things": [...]}


def run(args: dict) -> dict:
    if args["thing"] not in ("a-thing",):
        raise Refused(f"the example engine runs no thing {args['thing']!r}")
    return {"outputs": [...]}


HANDLERS = {"things": things, "parameters": parameters, "run": run, "sff_export": sff_export}

if __name__ == "__main__":
    serve(HANDLERS, name="example")
```

`serve` answers `ping` itself. A handler refuses a request by raising an exception whose class is
named `Refused`; its words reach the person as they are written, with no traceback. Every op that
names a thing refuses one it does not run, by raising `Refused`. Any other exception is a failure
of the worker, said as `<ExceptionType>: <words>`.

### `WorkerEngine`

```python
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="example", worker="openferment_engine_example.worker",
                      distributions=("openferment-engine-example",),
                      heavy=("a_placeholder_library",), timeout_s=120.0)
```

`version()` reads each named distribution's installed version. `things()` asks the worker's
`things` op once per process and keeps its first answer; `parameters()` asks the `parameters` op;
`run()` asks `things`, `parameters`, `run` and `sff_export` in turn; `replay()` asks the `run` op
again through the run's artifact tool; `export_sff()` reads the record the run kept. `heavy` names
the modules the worker computes with (above). `timeout_s` is how long one op may take, 120 s by
default; a worker that takes longer is stopped, and the next call starts it again.

| Op | Request `args` | Result |
|---|---|---|
| `things` | `{}` | `{"things": [EngineThing, …]}` |
| `parameters` | `{"thing", "configuration"}`, the configuration a run would use | `{"parameters": [EngineParameter, …]}` |
| `run` | `{"thing", "configuration", "inputs": [{"name", "value", "unit"}, …]}` | `{"outputs": [{"name", "value", "unit"}, …]}`: every output a finite number or a string in a unit, each name its own and at most 200 characters, in the same order on every run of one request |
| `sff_export` | `{"thing", "configuration", "inputs": […]}` | `{"flowsheet": <an SFF document>}`, or `Refused: <words>` when the engine has no plant |

The worker receives the values a run sets, already checked against the parameters: each
`name` a key of the thing, each `unit` the parameter's, each number inside its bounds. A
parameter a run leaves alone is the worker's default. Every output is a function of the request
alone: the same request gives the same outputs, in the same order, within the precision the thing
states, since a replay compares the outputs in order. The service measures each run's
`durationMs` itself and keeps it beside the outputs.

A worker that answers outside this table (a result key missing, `outputs` that are no list, an
output that is no name, value and unit, a number that is NaN or infinite, two outputs of one name,
an output's name blank or longer than 200 characters, a flowsheet that is no JSON object) breaks
the contract: the service raises `EngineBroken`, keeps no runs row, says on the event stream that
the job failed, and answers 503 in words. A break in the `run` op keeps nothing, so the next ask
after the worker is mended computes afresh. A break in `sff_export` comes after the run's
computation is kept as its artifact: the next ask after the worker is mended answers the
computation from that artifact and asks `sff_export` for the file again.

## What the service does with an engine

- **Discovery.** At startup `engine/registry.py` loads every object of the group. An engine
  that fails to load (whatever its import raises, `SystemExit` included; a `KeyboardInterrupt`
  alone goes on and stops startup), whose object lacks a declared name or method or raises as one
  is read, or whose import brings its worker or a heavy module into the service's process is
  listed with its error in words, and the service keeps running. An entry module that asks the
  registry while it is imported is answered as though no engine were found yet: at once from its
  own thread, and after `registry.DISCOVERY_WAIT_S` (10 s) from a thread it starts and waits on.
  Discovery itself runs with no time limit.
- **`GET /api/engines`**: each engine's name, version, worker module and status, things, the
  error that keeps it from loading (when one does) and its last conformance verdict. The listing
  gives a cold worker 30 s to answer `things` first; an engine whose things fail or time out is
  listed with the words.
- **`GET /api/engines/{name}/parameters?thing=&configuration=`**: the thing's parameters, the
  configuration resolved as a run resolves it (`EngineThing` above).
- **`POST /api/engines/{name}/run`**: `{thing, configuration?, inputs?, by?}` runs one thing and
  answers the run's report (`RunReport`). A request the engine refuses is a 422 in its words; a
  refused run is kept as a receipt and answered from it when asked again. Every ask, a repeat
  included, first checks its values against the worker's `parameters` op, so a kept run or a
  receipt is answered while the worker answers.
- **What the two routes answer beside their result**, each in words (`docs/api/openapi.json`
  declares them): 404 for an engine not registered here, or a BioSTEAM plant its shelf does not
  hold; 422 for a request refused; 503 for an engine that cannot be used, a worker that cannot
  answer, or a worker that answers outside the protocol, with no run kept.
- **The run's row.** The run's id is `artifacts.artifact_id`: the first 16 hex characters of the
  sha256 of the UTF-8 bytes of the canonical JSON of `{"tool", "toolVersion", "inputs"}`, its keys
  sorted, no spaces (separators `,` and `:`), and every character outside ASCII kept as itself
  (`ensure_ascii` off; the version string holds `·`). `tool` is `engine.<name>`; `toolVersion` is
  the version string; `inputs` is the run's basis in order, each `{"name", "value", "unit",
  "source"}` and each source `{"kind", "id", "note", "by"}`, `null` where unset: `engine`,
  `thing`, `configuration` (when there is one), `precision.rtol` and `precision.atol` (numbers),
  each a source of kind `convention` with the note `engine/runs.py` writes, then `value <key>` for
  each value set, in key order, its source of kind `assumption` with `by` the person and the note
  `typed on <at>: <note>` (`typed on <at>` with no note); a model's estimate is of kind
  `model-estimate`, its note `estimated on <at>: <note>`. The version string is the contract's
  stem, the engine's name and every distribution with its version:
  `engine run 1 · example · openferment-engine-example 0.1.0`. The stem moves when the
  service changes how it keys a run or shapes its outputs; a run kept before then keeps its own
  id, and its replay names the version it was kept at (below). The same request twice is one
  row, answered as it was first kept: its `by` and `created_by` are the first asker's, whoever
  asks again. `created_by` is the request's person or model, and a request naming no `by` is kept
  as `this browser`. Provenance is computed from the inputs' origins (`basis.py`): `computed` for
  a run at the engine's own defaults, `assumed` when any input is a person's assumption or a
  model's estimate.
- **Outputs.** Each output is kept as a typed quantity, its origin the run's own artifact:
  `outputs.values` is `[{"name", "quantity": {"value", "unit", "origin": {"kind": "artifact",
  "ref": "<the run's artifact id>"}}}, …]`.
- **The SFF file.** After the run, the worker's `sff_export` is asked once. A document is
  validated and scored by the vendored toolkit in the service's own Proforma worker and kept as
  the flowsheet record `run-<id>` (`docs/api/sff.md`); words are kept as the run's `sffRefused`.
  Either way the run stands, and `export_sff(run)` answers the record or the words.
- **Replay.** `POST /api/biorepo/artifacts/{id}/replay` computes the run again from its basis,
  with the engine installed now, and holds every output, in order, within the stated precision
  (`withinTolerance`). When the version string moved since the run was kept, the first of its
  `differences` is `toolVersion`, the version it was kept at beside the one it ran at; the nightly
  checks (`nightly_checks.py`) report such a run as stale and replay it no further.
- **`GET /api/runs?engine=<name>`** lists one engine's runs; the Runs screen shows the engine of
  every run and filters by it, and a run's page shows each output with its origin.
- **Tools.** `engine_plants`, `engine_parameters`, `engine_run` and `engine_report` take `engine`
  (default `biosteam`), so Postdoc and any MCP client list, read and report every engine's things
  and runs the same way. `engine_run` runs a contract engine's thing at its own defaults; values
  are set through `POST /api/engines/{name}/run`, and a study scenario (`engine_run`'s `scenario`)
  runs on BioSTEAM. At the HTTP endpoint (`POST /api/tools/{name}`) a tool that writes,
  `engine_run` among them, names its caller with `?by=`, who is then the write's author; a call
  that names nobody is a 422 in words.
- **`pnpm ready`** prints one row per engine: its version, its worker and its conformance verdict.

## Conformance

`python -m openferment_core.engine.conform <name>` checks an installed engine against this page
and prints one row per check, on a database of its own that it drops after; it exits 1 when any
check fails, and keeps its verdict for `GET /api/engines`. `pnpm prove` runs it for every engine
registered.

- `--thing <id>`, as often as needed, narrows the checks to those things, in the order named;
  the first named is the one run, and an id the engine runs none of is refused in words. With
  none, every thing's parameters are read and the engine's first thing is run.
- `--inputs <file>` names a JSON list of `EngineInput`s the checked run sets, for a thing whose
  parameters leave a value to the run. With none, the run is made at the thing's own defaults.
- Each thing is checked in its default configuration, or in the first it names when it has no
  default.
- Check 3 holds the run's id to the artifact id of its basis. Check 6 imports the entry
  point's module in a process of its own and holds out of it the worker module, every module
  `heavy` covers, and the five libraries the service keeps out for every engine. Check 7 offers a
  WorkerEngine's worker the thing `conform-no-such-thing` as one of its own: the first ask reaches
  the worker's `run` op once, its `Refused` is kept as a receipt in its words, and the same request
  asked again is answered from the receipt with the worker's `run` op never asked; a hand-written
  engine (`biosteam`) refuses the unknown thing in words, keeping nothing. Check 8 asks a second
  run in a model's name, on a basis of its own: with no values set, through the `engine_run` tool
  on another thing checked, or else another configuration of the first; with values set, or with
  no second basis, through the run itself, the checked run's values (or the thing's first
  parameter at its own default) as the model's estimates, dated the day the check runs.

| # | Check |
|---|---|
| 1 | A JSON number outside a `quantity` is refused in words before the worker is reached |
| 2 | Every parameter of every thing carries an origin: `library-default` with `ref`, or `convention` with `note` |
| 3 | A run writes one `runs` row keyed by its basis, and the same request twice is that one row |
| 4 | A replay holds every output within the precision the thing states |
| 5 | The run's SFF file validates and scores, or `sffRefused` holds words |
| 6 | Importing the module the entry point names imports neither the worker module nor what the engine computes with |
| 7 | A request the engine refuses is kept as a receipt in its words, with no traceback |
| 8 | `created_by` on every run is the person or the model that asked for it |

## What is deliberately absent

- No socket for kinetic models beyond what an engine computes in its own worker.
- No scenario fields beyond parameters: a study scenario is one of BioSTEAM's plants, a
  configuration and values for its parameters (`docs/api/studies.md`); a contract engine's
  values are set on its run.
- No import of an SFF file into an engine: a file is a record, and an engine's recipe is code.
- No science on this page: every value is a placeholder.
