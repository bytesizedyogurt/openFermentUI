# The engine contract

An engine is a package that computes runs for openFerment: it says what it can run, what each
thing it runs takes, and it runs one with typed values. The service keeps every run of every
engine as one row of one shape (`docs/api/runs.md`), replays it within the precision the engine
states, writes its SFF file where the engine has a plant (`docs/api/sff.md`), and shows it on the
Runs screen. ADR-015 records why the contract has this shape.

This page and the three it names are enough to build an engine with no plant that takes typed
values: `docs/api/workers.md` (the JSON-lines protocol an engine's worker speaks),
`docs/api/runs.md` (the row a run becomes) and `docs/api/openapi.json` (the routes and every model
by name). An engine that writes SFF files also reads `docs/api/sff.md`; a run that takes a bench
reading, `docs/api/studies.md` (Measurements); and the tools' inputs are in `docs/TOOLS.md` and
`GET /api/tools`. A whole engine, short, stands at the end (A skeleton: the placeholder engine
`example`). Every example value below is a placeholder in a placeholder unit; an engine package
carries no composition, yield, price, titre or finding of a paper, as the service carries none.

The modules this page names are under `core/openferment_core/`: `engine/registry.py` is
`openferment_core.engine.registry`; `EngineBroken` and `EngineRefused` are
`openferment_core.engine`'s; `WorkerEngine`, written in `engine/contract.py`, is imported from
`openferment_core.engine`. An engine package's modules import `openferment_core.workers.serve` and
`openferment_core.engine.WorkerEngine` alone, and its handlers return plain JSON objects; its tests
may also import `SimWorker` and `WorkerError` from `openferment_core.workers`, and `EngineRefused`
and `EngineBroken` from `openferment_core.engine` (An engine's own tests, below).

A request for an engine may name the contract in words of its own, which read here so:

- "Installable with `pip install -e`": a PEP 660 editable install into the service's
  environment, the install of What an engine is, below (`uv pip install -e`, held to
  `core/uv.lock`'s versions).
- "Given typed quantities, it returns them": a run hands the worker the values it sets for the
  parameters the thing declares, each as a name, a value and a unit, in key order (The worker,
  below); a parameter the run leaves alone reaches the worker as nothing, and the worker's own
  default stands for it, so a run on the engine's own defaults hands the worker no values (the
  skeleton's run then answers its default). Every parameter carries a default, since the proof
  runs every thing with no value set (What an engine is, `pnpm prove`).
- "Returns them as typed outputs": the worker answers each output's name, value and unit, and the
  service keeps each as a typed quantity whose origin is the run's artifact, each value the run
  set keeping its own origin in the run's `inputs` (What the service does with an engine,
  Outputs).
- "Their count", or any other count a worker answers: a pure number, its unit `""`, as every pure
  number's is (EngineParameter, below), and what it counts is the engine's to say in the output's
  name; a request's "every example value a placeholder in a placeholder unit" reads as every value
  with a unit, so a count keeps `""`.
- "The time it took": the service measures every run's `durationMs`, and a worker that reports
  its own computation's time answers it as a diagnostic beside its outputs (The worker), since a
  replay compares every output and a clock reading moves on every run.
- "Tests that run with `pytest` from the package's directory": `<repository>/core/.venv/bin/python
  -m pytest` there, the service's interpreter, which holds pytest and `openferment_core`, or
  `pytest` with `core/.venv/bin` first on `PATH`; a `pytest` of another environment holds no
  `openferment_core`, and its tests stop at their first import (An engine's own tests, below).
- "Replays identically": the thing states its precision as `{"rtol": 0, "atol": 0}`, which holds
  a replay to the outputs it was kept with, and every output is a function of the request alone,
  so the same request answers the same outputs in the same order (The worker, below); the
  package's own tests hold that at the worker, and conformance check 4 at the service.
- "The project's `CLAUDE.md` ... as house rules": its working rules (`docs/PROGRESS.md` read
  first, `pnpm test:core` green before every commit, a push after every step) hold for the
  repository's own work. A builder working from a request in a worktree of its own follows the
  request: it reads the files the request names, keeps its package under `examples/`, commits and
  pushes nothing, and holds the package with the package's own tests, which need no database and
  no `node_modules` (An engine's own tests, below). Every other rule of `CLAUDE.md`, its
  constraints and stop conditions among them, holds for the builder's work too.

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
- The package installs into the service's Python environment, beside the service, as a PEP 660
  editable install, then the service restarts (in bash or zsh, which read `<(…)`):

  ```bash
  cd core && uv pip install --python .venv/bin/python \
    -c <(uv export --frozen --all-extras --no-hashes --no-emit-project --quiet) \
    -e <path to the package>
  ```

  `--python .venv/bin/python` names the service's environment, whatever environment the shell
  has activated. `-c` holds every package `core/uv.lock` pins at its locked version (BioSTEAM,
  thermosteam and biorefineries among them), so a package whose dependencies would move one is
  refused in uv's words and installs nothing; a dependency the lock does not name installs beside
  it. `scripts/engines-local.sh` and `pnpm prove` install the same way. `core/.venv` is uv's and
  holds no pip, so the command is uv's; a bare `pip install -e` installs into the environment that
  pip belongs to, which the service never reads. A shell or a harness that reads no `<(…)` writes
  the constraints to a file first, with the same effect:

  ```bash
  cd core && uv export --frozen --all-extras --no-hashes --no-emit-project --quiet --output-file <a file>
  uv pip install --python .venv/bin/python -c <a file> -e <path to the package>
  ```
- An engine package lists no dependency on `openferment-core`: it installs into the service's
  environment, where `uv sync` installed the core from this repository, and its entry module and
  worker import `openferment_core` from there.
- Any build backend that makes an editable install serves, setuptools or hatchling:
  `uv pip install -e` fetches it once from PyPI or uv's cache, and a package whose backend is
  setuptools also installs offline with `--no-build-isolation` added to the install above, from
  the setuptools `core/.venv` holds. An editable install with setuptools writes
  `<module>.egg-info/` into the package's directory, the install's own record, which git ignores.
- In a fresh checkout make the service's environment first, `cd core && uv sync --all-extras`
  (uv on PATH, PyPI reachable once), then install the engine. The `pnpm` commands need
  `pnpm install --frozen-lockfile` first. The service needs `OPENFERMENT_DATABASE_URL` (the
  environment, then `core/.env`) naming a migrated database, and `conform` the PostgreSQL server
  that address names, keeping its verdict once the named database is migrated (Conformance,
  below); an engine's own tests need neither (An engine's own tests, below). A database of your own
  is made and migrated with `pnpm db:reset <name>` on the server `OPENFERMENT_DATABASE_URL` names
  (the production database, `openferment`, is refused), which the service and `conform` read once
  `OPENFERMENT_DATABASE_URL` names it, and dropped with `cd core && uv run python -m
  openferment_core.migrations drop <name>`; `pnpm db:migrate` against a database the server does
  not hold says so in words and names that command.
- `uv sync` keeps only what `core/uv.lock` names, so it takes an installed engine out; `uv run`,
  which every `pnpm` command uses, keeps it. `pnpm session:start`, `pnpm prototype:up` and a
  host's deploy (`scripts/host/deploy.sh`) each sync, then run `scripts/engines-local.sh`, which
  installs again each package directory `core/engines.local` names, as the install above does,
  held to the lock's versions: one a line, relative to `core/` or absolute, a line beginning `#` a
  comment; git ignores the file. Name a package there to keep it installed across a sync. To take
  an engine out, delete its line and run `cd core && uv pip uninstall <distribution>`.
- Start the service with `cd core && uv run uvicorn openferment_core.api:app --host 127.0.0.1
  --port 8000`. It reads `OPENFERMENT_DATABASE_URL` (the environment, then `core/.env`) naming a
  migrated database, and after `pnpm build` it serves the app at the same address: the project's
  runs at `http://127.0.0.1:8000/#/p/<project>/proforma/studies` and a run at
  `http://127.0.0.1:8000/#/p/<project>/proforma/runs/<id>`. A project is made with
  `POST /api/projects` `{name, by}`. The group is read once per process: stop the service and
  start it again after an install.
- A new version takes effect when the package is installed again: raise the version in the
  package's `pyproject.toml`, run the install above again, then restart the service. An installed
  package's version is the one its metadata recorded when it was installed, and an edit of its
  code alone leaves that version as it was.
- The module the entry point names is imported by the service process, during startup, with no
  time limit of its own: its import returns promptly and imports nothing heavy. An engine's
  computation happens in its **worker**, a process of its own. An entry module whose import brings
  into the service's process its worker module (or a module below it), a heavy module it declares,
  or one of `biosteam`, `thermosteam`, `biorefineries`, `pisces_sff` and `cobra` is set aside,
  those modules named. Discovery counts the modules an entry module's import adds to those the
  service had already imported; conformance check 6, in a process of its own, holds every one
  out.
- Installing an engine trusts its code with whatever the service's user can read, `core/.env`
  included. The install runs the package's build backend in the installing shell's environment,
  every variable of it, a key among them. Its entry module runs in the service's process, with the
  service's key in reach. Its worker runs as the same user, with the variables `workers.withheld`
  names left out of its environment (The worker, below), and the same files in reach.
- A package under `examples/` is the project's own and declares no licence (ADR-012: a licence for
  the project is the owner's choice). Installed beside the service, an engine is listed by
  `pnpm ready`, held by `core/tests/test_boundaries.py` to the heavy modules it declares, and
  conformed by `pnpm prove` step 10, so an engine that fails to load or fails a check fails the
  proof. `pnpm check:licences` reads every distribution installed in `core/.venv` that registers
  an engine and that `core/uv.lock` does not name: one installed from under this checkout's own
  `examples/` passes declaring no licence and fails in words declaring one, and any other (one
  installed from another checkout's `examples/` among them), with each dependency it brings that
  the lock does not name, is held to `core/licences.toml` as any dependency is.
  `test_no_seed` scans `src/` and `core/openferment_core/`, and `pnpm check:secrets` reads every
  tracked file, `examples/` among them. The core's own tests hold with an engine installed beside
  the core.
- `pnpm prove` installs every package directory under `examples/engines/` (one holding a
  `pyproject.toml`) before its service starts, as the install above does, held to the lock's
  versions, each said with the engines its `pyproject.toml` registers. A package that leads
  outside `examples/engines/` (a symbolic link elsewhere), one whose `pyproject.toml` cannot be
  read and one that fails to install each fail the proof in words. The proof names no engine of
  `examples/`: a package placed there is picked up as it stands.
- **Every thing of an engine under `examples/engines/` runs on its own defaults, with no value
  set, so every parameter of every thing carries a default.** The walk (step 9) runs the first
  thing of each such engine from the Runs screen, the engine chosen on Studies' run card, and
  reads the run's provenance, outputs and diagnostics on its page. Step 10 conforms every engine
  the service lists, an engine of `examples/` with no `--inputs` and no `--project`: checks 3, 4
  and 5 run its first thing at its defaults, and check 8 runs a second thing or configuration at
  its defaults, or the first thing with one of its defaults set as a model's estimate
  (Conformance, below). A thing with a parameter that waits for a run's value is refused in words
  naming the parameter (EngineParameter, below), and the walk and step 10 fail in those words.
- The proof leaves core's environment as it found it, however it ends (a failure, Ctrl-C,
  `SIGTERM`), one line a package: a package it installed is uninstalled at its end, unless the
  environment held its distribution before the proof began (a person's install, or one
  `core/engines.local` names, which keeps an engine installed beside the service); one held from
  another directory is installed from there again. With `--keep` each stays installed while the
  kept service runs, said with the command that takes it out.
- The engines in the repository register the same way, from `core/pyproject.toml`: `biosteam`
  (the library plants, openFerment's composed flowsheet and the shelf's scenario flowsheets),
  `kinetics` (fermOS's model families, its forecasts of a kept fit and its vessel designs) and
  `train` (pureOS's trains, each a project's own). The sections The core's `biosteam`, The core's
  `kinetics` and The core's `train`, below, describe those engines' runs.

## What it declares

An engine from outside the core is built on `openferment_core.engine.WorkerEngine` (below), which
answers `version()` from installed metadata and `export_sff()` from the record the run kept, and
every other method over four worker ops: the package declares the engine's name, its worker,
its distributions and the heavy modules its worker computes with (`heavy`, which conformance
check 6 holds), and writes the worker. The table lists what the service asks of every engine, the
core's own `biosteam`, `kinetics` and `train` among them. A package whose things are a project's
own declares `things_are`, `rests_on` and `unready` as attributes and methods of the engine
object, which runs in the service's process.

| Name | Type | What it is |
|---|---|---|
| `name` | `str` | Lowercase letters, digits and `-`, starting with a letter, at most 40 characters; the entry point's name, the `engine` column of every run it makes, and the `?engine=` filter |
| `worker` | `str` or `None` | The dotted module of the engine's worker: the service runs it as `python -m <worker>` would (The worker, below) and speaks the protocol of `docs/api/workers.md`. Heavy imports live here alone. `None` for an engine that computes in the service's own process with nothing heavy, whose `heavy` is then `()`, as the core's `kinetics` is; `GET /api/engines` lists its worker's status as `none`. Such an engine's computation may call a worker of the core's own (the kinetics engine's vessel design runs in the Proforma worker), and a route that worker cannot answer is a 503 naming the worker its computation called |
| `heavy` | `tuple[str, ...]` | The modules the worker computes with, which the service keeps out of its process (conformance check 6); each name covers its module and every module below it (`a.b` covers `a.b` and `a.b.c`). `()` for an engine that computes with nothing heavy. The service keeps `biosteam`, `thermosteam`, `biorefineries`, `pisces_sff` and `cobra` out for every engine, whatever it declares |
| `version()` | `dict[str, str]` | The distributions the engine runs on, each with the version its installed metadata records: `{"openferment-engine-example": "0.1.0"}`; a distribution that is not installed reads `"not installed"`, and enters the version string so. It is the run's `versions`, and it enters every run's id. It changes whenever the engine's computation changes: an editable install keeps its version across edits of its code, so a new version goes with every change to what a run computes (installed again, as above), and the service then computes the request afresh |
| `things()` | `list[EngineThing]` | What the engine can run, each with its configurations, the words naming each where the engine gives them, and its precision. The service asks it afresh on every listing and every run, in the request's project, so an engine may list what the project holds: the kinetics engine lists its forecast while the project keeps a fit, and the train engine lists each train the project holds. A `WorkerEngine` answers every ask from its worker's first answer, kept for the life of the process (below) |
| `things_are` | `str`, optional | Words saying what the engine's things are, declared by an engine every one of whose things is a project's own: the train engine's are `a project's trains, each saved in pureOS's Builder or built by a model`. `GET /api/engines` lists them as `thingsAre`, so a project that holds none of the things says what one would be. A database made for the checks holds none of them, so such an engine is checked in a copy of a project the command names (`--project`, Conformance, below), and `pnpm ready` names that command on every database, the production one among them. An engine that declares none is checked on a database of its own |
| `rests_on()` | `dict[str, dict[str, list[str]] \| None]`, required beside `things_are` | What the current project's things rest on, as rows by table. Each key is a table of the `openferment` schema that holds a project's rows, one with a `project_id` column (`core/openferment_core/db/models.py`); its value is `None` for every row of the project in the table, or the columns that pick the rows, each with the values it holds (`{"id": [...]}`). Conformance copies those rows into a database of its own, the project's own row always among them (Conformance, below). It reads the store and writes nothing. An engine that declares `things_are` with no `rests_on` loads and runs; conformance refuses it in words, and `pnpm ready` says those words in its row |
| `unready(thing, inputs)` | `str` or `None`, optional, beside `things_are` | Why a thing cannot be checked as it stands, in words saying what it is, or `None` when a run of it with `inputs` would compute; it runs nothing and keeps nothing. Conformance leaves out each thing it gives words for, and lists the thing with them; with no `unready`, every thing is checked. The train engine says `a saved draft, which cannot be built as it stands`, with its validation's words; `a train whose values wait for a source`, with the words of its run's check; or `a train whose run is refused before it computes`, with the run's words |
| `parameters(thing, configuration)` | `list[EngineParameter]` | What one thing takes: each parameter a `ParameterSpec` with its default and the default's origin, or with none for a parameter a run sets |
| `run(thing, configuration, inputs, by)` | `EngineRun` | One run, kept as one `runs` row. `inputs` is a list of `EngineInput`, each a named `Quantity`; `by` names the person or the model asking |
| `replay(run)` | `ReplayResult` | The run computed again from its basis alone, each output held within the stated precision |
| `export_sff(run)` | `SFFFlowsheet` or words | The run's SFF file as its flowsheet record (`GET /api/flowsheets/{id}`), validated and scored, or the words that say why there is none |

### `EngineThing`

```json
{"id": "a-thing", "title": "A thing the engine runs", "kind": "placeholder",
 "configurations": ["one way", "another way"], "defaultConfiguration": "one way",
 "configurationTitles": {"another way": "The placeholder thing's second way, in words"},
 "precision": {"rtol": 1e-12, "atol": 0}}
```

- The fields are those `GET /api/library` answers for a plant (`id`, `title`, `kind`,
  `configurations`, `defaultConfiguration`), with the thing's `precision` and, where the engine
  gives them, `configurationTitles`.
- `id`: starts with a letter or a digit, then letters, digits, `.`, `_` and `-`, at most 80
  characters. A run names it as its `plant`.
- `configurations`: the configurations it runs in, each name 1 to 80 characters, or `[]` when it
  takes none. `defaultConfiguration` is one of them, or null.
- `configurationTitles`, optional: the words a person reads for a configuration, by its name,
  each title 1 to 200 characters; left out, it reads `{}`. Studies' run card shows a
  configuration by its title beside its name, on its chooser and on the line for the run it
  made, and by its name where the engine gives none. A title is words alone: a run, its basis,
  its id and its replay name the configuration by its name, so a title the engine changes moves
  no run. A key outside `configurations`, or a title of spaces alone, breaks the contract
  (`EngineBroken`), as a `defaultConfiguration` outside them does. The kinetics engine titles
  each configuration with the kind of artifact it names and when the project kept it (The core's
  `kinetics`, below).
- A request that names no configuration runs in `defaultConfiguration`. A thing with
  configurations and no `defaultConfiguration` is run with a configuration named, and a request
  naming none is refused in words; so is a configuration the thing does not name, and any
  configuration for a thing that takes none. The rule holds at every door: the run route, the
  parameters route and the engine tools, so the worker's `parameters` op receives the
  configuration a run would use. BioSTEAM's library plants follow it at their own doors too
  (The core's `biosteam`, below).
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

```json
{"key": "a-parameter-a-run-sets", "label": "A placeholder with no default", "unit": "placeholder-unit",
 "value": null, "origin": null, "min": 0, "boundsReason": "why a run may set it only above this"}
```

A `ParameterSpec` (the shape every parameter panel reads) with its default and the default's
origin:

- `key`, `label` and `unit` name it; `unit` is `""` for a share, a pure number or a choice.
- `value` is the default the engine uses when a run sets none: a number, one of `choices` for a
  parameter chosen from words, or a convention's words in a unit for a term the default leaves
  off (the kinetics engine's `ki_substrate` is `off` in g L⁻¹), which a run replaces with a
  number in that unit.
- `origin` says where the default comes from, and every default carries one of five
  (`models.DEFAULT_ORIGINS`). A worker's are two: `library-default` with `ref` naming the package
  and version it was read from, or `convention` with a `note` for a software setting (a step
  count, a tolerance). An engine's own default is a `library-default` whose `ref` is
  `<distribution>@<installed version>`, read with `importlib.metadata.version` so it follows each
  new version, or a `convention` whose `note` says what the setting is; check 2 holds that `ref`
  or `note` to be non-empty. A thing the project holds (The core's `train`, below) has defaults
  the project holds too: `record` with `ref` naming the records that bound it, its `sourceRule`
  naming the field it binds from (`record:<field id>`); `artifact` with `ref` naming the run,
  simulation, fit or design it was read from; `person-assumption` with `by` naming the person who
  typed it into the thing, and `at` the day. A model's estimate and a deposition's reading reach a
  run as values the run sets (`EngineInput`, below), each with its origin on the run's `inputs`,
  and a parameter whose default names either is refused as it is read.
- A parameter with no default has `value` and `origin` null, and its `sourceRule` names
  `assumption` (given when the parameter names no rule): a run sets it, the engine binds it
  from what the project holds (the kinetics engine binds a family's parameter from the project's
  records, or from the fit or the simulation a configuration names), or the thing fills it
  itself when a run leaves it unset, which the parameter's `note` then says with the reason
  (the train engine's: a value the unit's class decides at run time, a component the inlet
  does not carry, a split left to the class). A run that leaves unset a parameter none of
  these gives is refused in words and keeps nothing.
- For an engine built on `WorkerEngine`, a parameter with no default is one every run sets: the
  service refuses in words, before the worker is asked, a run that leaves it unset
  (`docs/api/workers.md`, `run`), whatever its `note` says. Binding a value from what the project
  holds and filling it in the thing are ways of the core's own engines (The core's `kinetics`,
  The core's `train`). An engine under `examples/engines/` gives every parameter a default (What
  an engine is, `pnpm prove`).
- `min` and `max`, when given, bound what a run may set; `boundsReason` says why, in words, and
  every parameter carries one, a parameter with no bounds included.
- The panel's other fields may be left out: `symbol`, `gloss`, `dimension`, `step`, `scale`
  (`linear` or `log`), `group` (`parameters`) and `note`. `sourceRule` defaults to the rule
  entry the origin's kind stands for (`assumption` for a person's), and a record's default
  names it (`record:<field id>`). Leave `sourceRule` out, and the service writes the entry the
  default's origin stands for; a rule a worker writes names entries from `fit`, `record:<field
  id>`, `artifact`, `simulation`, `assumption`, `convention` and `library-default`, and any other
  entry breaks the contract (`EngineBroken`), so every `parameters` read and every run of the
  thing answers 503. `convention` holds a stated convention for a parameter whose
  source rule names `convention`, its reason in `note`; a contract engine leaves it out, its
  default carried by `value` and `origin`.

### `EngineInput`

```json
{"name": "a-parameter", "quantity": {"value": 2.5, "unit": "placeholder-unit",
 "origin": {"kind": "person-assumption", "by": "A. Person", "at": "2026-10-30",
            "note": "what it rests on"}}}
```

- The shape a run's inputs have (`RunInput`): `name` is a parameter's key; `quantity` is a typed
  value in that parameter's unit, carrying its origin: `person-assumption` (`by` the person) or
  `model-estimate` (`by` the model's id). A value may also be a reading a person deposited at
  the bench, `{"kind": "measurement", "ref": "<deposition id>/<entry id>"}`, its value and unit
  the reading's own: the service looks it up in the project's depositions before the worker
  sees anything, fills its depositor (`by`) and its time (`at`), and sets it in the parameter's
  unit where the reading's converts, the conversion stated in its note (`docs/api/studies.md`,
  Measurements). A reading the project does not hold, one no person confirmed, one corrected
  since, a value or unit other than the reading's, or a unit that does not convert into the
  parameter's is refused in words, and nothing runs.
- `at` is the day the value was set, and every value carries one, a reading's from its
  deposition: a value without it is refused in words. The day enters the run's basis, and the
  service stamps no day of its own, so the same request is one run whatever day it arrives.
- A value set is checked against the thing's parameters before the worker sees it: a key the
  thing declares, set once, in the parameter's unit, a number for a number and one of `choices`
  for words, inside `min` and `max`. A parameter takes words when it has `choices`, or when its
  default is words in no unit; every other parameter takes a number, one with no default among
  them, and one whose default is a convention's words in a unit (a term left off). A key the
  thing lacks is refused with the number of its parameters and the few keys nearest to it. A
  value refused keeps nothing, and so does a run that leaves a parameter with no default unset.
- A value a contract engine's run sets is its `value` and `unit` with its `origin`: a quantity
  that also carries `low`, `high` or `basis` is refused in words, since the worker receives the
  value and unit alone.
- BioSTEAM checks a library plant's key, unit and kind the same way (`runs.check_inputs`), on
  one path from every door (The core's `biosteam`, below); a library plant's bounds are flagged
  by the library on the run's parameters (`ParameterValue.outOfBounds`), the value kept as set
  and flagged. Its door passes `low` and `high` to the plant as the `Override`'s, which the
  library takes equal to the value (a range is a study's to sample), and refuses a `basis` in
  words. A scenario flowsheet's values are checked and converted at Proforma's own door, and
  their `low` and `high` are the range the run's samples draw over; its `min` and `max` are the
  flowsheet's to hold inside the run, so a value past them reaches the worker, whose refusal of
  it is kept as the run's receipt (The core's `biosteam`, below). The kinetics engine checks
  its values the same way, and keeps a range in the run's basis as `<key> low` and `<key> high`
  beside the value, which the run integrates at (The core's `kinetics`, below).
- A number that is NaN or infinite, as Python reads `NaN`, `Infinity` and a number past a
  float's range from JSON, is refused in words at every door that takes a run's values (this
  engine's run route, the library's, Proforma's, pureOS's and fermOS's, a study scenario, the
  tools, `conform --inputs`), and nothing runs: the worker receives finite numbers alone.
- A number is accepted only inside a `quantity`. A bare JSON number anywhere in a request, a
  field the request or a quantity does not name, and a `value`, `low` or `high` that is `true` or
  `false` are each refused in words before the engine's worker is reached.
- A request whose own fields are refused (a bare number, a stray field, a wrong type, a number
  that is NaN or infinite) answers 422 with FastAPI's list of field errors
  (`HTTPValidationError`), each echoing the input it refused, a number JSON cannot carry written
  as its words; every other refusal answers `{detail: <words>}` (`Refusal`). A quantity or an
  origin holding a field it does not name, and a value whose origin has no `at`, are refused in
  words, rules `docs/api/openapi.json`'s schemas leave unstated.

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
of the worker, said as `<ExceptionType>: <words>`. `serve(handlers, *, name='worker', stdin=None,
stdout=None)` answers one request a line, skips a blank line and returns when stdin closes, so the
worker's process ends with its input; `name` is what `ping` answers as `worker`, and a test may
hand it text streams for `stdin` and `stdout`. A test hands it both: with `stdout` left out,
`serve` points the calling process's descriptor 1 at stderr and sets `sys.stdout` to
`sys.stderr`, as a worker's own process needs, so a test that hands it `stdin` alone moves its own
output.

### `WorkerEngine`

```python
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="example", worker="openferment_engine_example.worker",
                      distributions=("openferment-engine-example",),
                      heavy=("a_placeholder_library",), timeout_s=120.0)
```

`WorkerEngine(*, name, worker, distributions=(), heavy=(), timeout_s=120.0)` takes these five by
keyword; `name` is the entry point's name, or the registry sets the engine aside in words; the
object reads them back as attributes, beside `status` (`cold` or `ready`). Importing the entry
module runs the package's `__init__.py` first, so that file imports neither the worker nor anything
heavy.

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
| `run` | `{"thing", "configuration", "inputs": [{"name", "value", "unit"}, …]}` | `{"outputs": [{"name", "value", "unit"}, …], "diagnostics": [{"name", "value", "unit"}, …]}`: every output a finite number or a string in a unit (`""` for a pure number or for words, as a parameter's is), each name its own and at most 200 characters, in the same order on every run of one request; `diagnostics` in the same shape, at most 50, which a worker may leave out (The worker, above) |
| `sff_export` | `{"thing", "configuration", "inputs": […]}` | `{"flowsheet": <an SFF document>}`, or `Refused: <words>` when the engine has no plant |

The worker's `run` and `sff_export` receive `inputs` in key order, the order the run's basis keeps
them, each number as a JSON float (a value typed `2` arrives as `2.0`), on the first run and on
every replay.

The worker receives the values a run sets, already checked against the parameters: each
`name` a key of the thing, each `unit` the parameter's, each number inside its bounds. A worker
may check them again, in its own words; the service's check stands either way. A parameter a
run leaves alone is the worker's default. Every output is a function of the request
alone: the same request gives the same outputs, in the same order, within the precision the thing
states, since a replay compares the outputs in order. The service measures each run's
`durationMs` itself and keeps it beside the outputs: the run's `durationMs` on `GET
/api/runs/{id}` and on its artifact, and a replay's own on its `ReplayResult`.

A value the computation reports about itself, the time it took or the iterations it made, is a
**diagnostic**: the `run` op answers it in `diagnostics` beside its `outputs`, `[{"name",
"value", "unit"}, …]`, at most 50, each a finite number or words in a unit, each name its own
among them and at most 200 characters. The service keeps them on the run (`EngineRun.diagnostics`)
and shows them on the run's page under its outputs, and `engine_report` names them as words; the
run's id, its artifact, its outputs and its replay stand without them, so a replay compares the
outputs alone. An engine that reports the time its computation took answers it as a diagnostic:
an output that moves between two runs of one request, a clock reading among them, makes the
replay differ and fails conformance check 4, and `pnpm prove` with it wherever the engine is
installed. The same request asked again is the kept run, with its first computation's
diagnostics.

A worker that answers outside this table (a result key missing, `outputs` that are no list, an
output that is no name, value and unit, a number that is NaN or infinite, two outputs of one name,
an output's name blank or longer than 200 characters, `diagnostics` outside the outputs' shape or
more than 50 of them, a flowsheet that is no JSON object) breaks the contract: the service raises
`EngineBroken`, keeps no runs row, says on the event stream that the job failed, and answers 503
in words. A break in the `run` op keeps nothing, so the next ask
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
- **`GET /api/engines`**: each engine's `name`, `entryPoint`, `version`, `worker` and
  `workerStatus`, `heavy`, `things`, `thingsAre` (for an engine whose things are a project's own),
  `conformance` (its last verdict) and `error` (what keeps it from use, when something does), as
  `EngineInfo`. The things are read in the request's project, afresh on each listing. The listing gives a cold worker
  30 s to answer `things` first; an engine whose things fail or time out is listed with the
  words.
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
  each a source of kind `convention` with the note `engine/runs.py` writes: `engine` (unit `""`,
  note `the engine that ran it`), `thing` (unit `""`, note `what the <name> engine ran`),
  `configuration` (unit `""`, note `the configuration it ran in`), `precision.rtol` (unit `1`, note
  `the relative precision the engine states for the thing`) and `precision.atol` (unit `1`, note
  `the absolute precision the engine states, in each output's unit`), each source `{"kind":
  "convention", "id": null, "note": <note>, "by": null}`; then `value <key>` for
  each value set, in key order, its source of kind `assumption` with `by` the person and the note
  `typed on <at>: <note>` (`typed on <at>` with no note); a model's estimate is of kind
  `model-estimate`, its note `estimated on <at>: <note>`; a deposition's reading is of kind
  `deposition`, its `id` the reading, `by` the depositor and its note `measured on <at>: <note>`. The version string is the contract's
  stem, the engine's name and every distribution with its version:
  `engine run 1 · example · openferment-engine-example 0.1.0`. The stem moves when the
  service changes how it keys a run or shapes its outputs; a run kept before then keeps its own
  id, and its replay names the version it was kept at (below). The same request twice is one
  row, answered as it was first kept: its `by` and `created_by` are the first asker's, whoever
  asks again. `created_by` is the `runs` table's column for the asker, the request's person or
  model, served on every run as `EngineRun.by`, and check 8 reads both; a request naming no `by`
  is kept as `this browser`. A run's diagnostics stay out of its basis, so they move no id. Provenance is computed from the inputs' origins (`basis.py`): `computed` for
  a run at the engine's own defaults, `assumed` when any input is a person's assumption or a
  model's estimate, `measured` when the values it sets are readings and none is a person's or a
  model's.
- **Outputs.** A worker answers each output's name, value and unit; the service keeps each as a
  typed quantity, its origin the run's own artifact: `outputs.values` is `[{"name", "quantity":
  {"value", "unit", "origin": {"kind": "artifact", "ref": "<the run's artifact id>"}}}, …]`. Each
  value a run sets keeps its own origin in the run's `inputs` (`GET /api/runs/{id}`). A run's
  `diagnostics` stand beside its outputs, as the worker answered them, and no reader of
  `outputs.values` (a comparison, a runbook, a tool's evidence) reads them.
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
  and runs the same way. The tools name a thing `plant`: `engine_run` takes `{engine, plant,
  configuration, scenario, note}`, `engine_parameters` `{engine, plant, configuration, words,
  limit}`, `engine_report` `{engine, run, parameters, limit}` and `engine_plants` `{engine, words,
  limit}`; `GET /api/tools` serves every tool's input schema. `engine_report` and `engine_run`
  name a run's diagnostics as words (`diagnostics`: how many, each name, value and unit, and what
  they are), and cite its outputs alone. Whichever engine it is asked for, `engine_plants` lists every engine
  registered here (`engines`): its version, its worker and the worker's state, its last
  conformance verdict, and the ids of the project's runs it made, newest first (`runs` counts
  them, `runIds` names the newest twenty); a project's runs of an engine registered here no longer
  are listed under its name with those words. `engine_report` and `engine_run` name the engine and
  the artifact tool of the run they answer (`engine`, `tool`). `engine_run` runs a contract
  engine's thing at its own defaults; values are set through `POST /api/engines/{name}/run`, and a
  study scenario (`engine_run`'s `scenario`) runs on BioSTEAM. A kinetics family runs with values
  no default gives, so `engine_run` on one answers its refusal naming each parameter that waits; a
  person sets those values on fermOS's screens or at `POST /api/engines/kinetics/run` (The core's
  `kinetics`, below). At the HTTP endpoint (`POST /api/tools/{name}`) a tool that writes,
  `engine_run` among them, names its caller with `?by=`, a person who is then the write's author,
  or with the `X-OpenFerment-Assistant` header, an assistant's `<name>/<version>`, the call then
  running in the model's lane under that name; a call that names nobody, or names both, is a 422
  in words. A run through `engine_run` keeps one audit row (`GET
  /api/audit`): module `proforma`, action `engine_run`, state `open` (`refused` for a receipt),
  target the run's id, `agent` and `who` the caller, the call's note as `detail.note`, and for a
  caller of the model's lane the door it came in by in `detail.via` (`postdoc`, `mcp` or `http`);
  the tool's answer names the row by its id in `auditIds`. A run through `POST
  /api/engines/{name}/run` keeps none, and its row's `by` names who asked.
- **`pnpm ready`** prints one row per engine: its version, its worker and its conformance verdict.

## The core's `biosteam`

`openferment_core.engine.biosteam:ENGINE`, registered by `core/pyproject.toml`, is BioSTEAM behind
the contract: its worker is the Proforma worker, and `heavy` names what that worker computes with
(`biosteam`, `thermosteam`, `biorefineries`, `pisces_sff`). Its things are of two kinds, the
library's own and the shelf's flowsheets a Proforma scenario runs (`flowsheets/shelf.py`, the
ones `proforma.runnable` takes: every one on the shelf, and no toy), each read afresh in the
request's project on every listing. The engine package imports no Proforma module
(`core/tests/test_boundaries.py`): Proforma gives the engine its scenario flowsheets through a
provider it registers as it is imported (`engine/biosteam.py` `provide`, `Provider`), which lists
them, reads their parameters and runs them. The service's app imports Proforma through its
tools, and conformance reads an engine as the app holds it (`conform.as_served`), so every door
lists the same things.

| Thing | Configurations | A run of it |
|---|---|---|
| Each plant and composed flowsheet the library shelf found buildable here (`GET /api/library`), kind `plant` or `flowsheet` | those it built in here; its default the shelf's own, else the first it built in | `engine/biosteam.py` `run_plant`, then `runs.run`; the tool `library.run` |
| Each shelf flowsheet a scenario runs with no part named (`ethanol_glucose_v0`), kind `scenario` | none | the run of an unsaved scenario of it, named by the flowsheet's own id (`proforma.run_thing`); the tool `proforma.run` |
| `custom_train_v1`, kind `scenario`, built from a kept vessel design and a kept train run; listed while the project keeps a scenario of it whose parts stand (`composite.parts_of`) | `vessel <id>, train run <id>`, one for each pair the project's scenarios of it name, and no default | the same, built from the two its configuration names |

- A library thing's precision is ten significant digits (`rtol` 1e-9) within the package test's
  absolute tolerance (`atol` 1e-8): a library run keeps those digits (`library.DIGITS`). A
  scenario flowsheet's is `rtol` 0, `atol` 0: `proforma.run` registers no tolerance, so its
  replay holds every output identically.
- `parameters(thing, configuration)` for a library thing is what the package builds it with,
  each default read back from a fresh build (`library-default`, its `ref` naming the package and
  version). For a scenario flowsheet it is the inputs a scenario of it binds, as `GET
  /api/proforma/bind` binds one with no scenario (the `proforma:<flowsheet id>` scope resolved
  with nothing set): each default with its origin, the records of the evidence pool that bound it
  (`record`, its `ref` naming them), a fermOS fit or the vessel design (`artifact`), the stated
  convention (`convention`, its note), a composite's Finance group at the package's own defaults
  (`library-default`, its `ref` naming biorefineries); an input nothing binds has no default, and
  a run sets it.
- A library plant's run takes one path from every door (`run_plant`): this engine's run route,
  `POST /api/library/{plant}/run`, a study scenario's run and the tools. A plant that takes a
  configuration, asked with none, runs in its default (`default_configuration`: the shelf's own,
  else the first it built in here), and every door that reads its parameters reads them there:
  `GET /api/engines/biosteam/parameters`, `GET /api/library/{plant}/parameters` (whose answer
  names the configuration), `engine_parameters`, and `POST /api/studies/scenarios`, which checks
  a scenario naming no configuration against the default's parameters. `engine_plants` gives
  each plant's row the configuration a run takes when none is named. A quantity carrying a
  `basis` is refused before the plant's parameters are read; each value is then checked against
  them (`runs.check_inputs`, a value outside its bounds kept and flagged) and converted by
  `basis.override_of` into the plant's `Override`, before the plant is built.
- A thing neither on the library's shelf nor provided is refused in words naming every thing
  the engine runs, scenario flowsheets among them (`unknown`, as `runs.thing_of` words it for a
  contract engine): a 422 at the run and parameters routes, the tools' refusal in words, and
  check 7's. A plant on the library's shelf that runs nothing (a subsystem) is refused in the
  library's own words.
- A scenario flowsheet's run is the run of an unsaved scenario of it, its scenario id the
  flowsheet's own, so the same request is one row; it runs at a scenario run's own settings (its
  samples, its seed). Its values are checked and converted at Proforma's door
  (`proforma.overrides_of`): a key the flowsheet takes no value for, a convention, a value in
  another unit, words for a number and a value naming no one are refused in words, each said
  whole at every door, and keep nothing; so does a run whose inputs wait for a source. A value
  past a parameter's `min` or `max` reaches the worker: the flowsheet holds its bounds inside the
  run, and a refusal the Proforma worker gives there is kept as a receipt. The row is the one
  `POST /api/proforma/run` keeps for a scenario (`docs/api/runs.md`, A Proforma run): engine
  `biosteam`, tool `proforma.run`, its SFF file written as it is kept. A run whose samples held
  no price is kept done, its `outputs.values` empty: the engine's route answers 200 with that
  row, and `POST /api/proforma/run` answers 422 naming it.
- `version()` names biosteam, thermosteam and biorefineries as their installed metadata records
  them. A library run's row names the versions its basis names; a Proforma run's, whose basis
  names no simulator, the engine's `version()`.
- Conformance (below) on `biosteam` reads every thing's parameters in check 2, and runs its first
  thing (a library plant) in checks 3, 4, 5 and 8; the proof's step 10 makes them so. A scenario
  flowsheet's inputs wait in a project that holds no record, so a check that names one sets its
  values with `--inputs`, a JSON list of `EngineInput`s, each a person's assumption in its
  parameter's unit:

  ```json
  [{"name": "<a parameter's key>", "quantity": {"value": 1, "unit": "<that parameter's unit>",
    "origin": {"kind": "person-assumption", "by": "<a person's name>", "at": "<the day it was set>"}}}]
  ```

  `python -m openferment_core.engine.conform biosteam --thing ethanol_glucose_v0 --inputs <file>`.
  Named with a value it waits for left unset, the thing cannot run as it stands (the engine's
  `unready`), and the command refuses it in words before anything is made, keeping no verdict.
  Check 3 says so when a run it makes answers no output (a run whose samples priced nothing).

## The core's `kinetics`

`openferment_core.fermos_engine:ENGINE`, registered by `core/pyproject.toml`, puts fermOS behind
the contract as fermOS computes: `worker` is `None` and `heavy` is `()`, since fermOS integrates
with SciPy in the service's process and a vessel design runs on BioSTEAM in the Proforma worker
the simulator starts; a vessel's route that worker cannot answer is a 503 naming it.

| Thing | Configurations | A run of it |
|---|---|---|
| Each family that simulates: `batch_v1`, `fedbatch_v1`, `chemostat_v1` (the light_v1 socket stays out) | none | `fermos.simulate`, the family with the run's inputs and `by`; the tool `fermos.simulation` |
| `forecast`, listed while the project keeps a kinetic fit a forecast draws from (logistic_v0) | those fits' artifact ids, newest first, each titled `a kinetic fit, kept <YYYY-MM-DD HH:MM> UTC`, and no default | `fermos.forecast_run` of the fit; the tool `growth_forecast` |
| `vessel`, listed while the project keeps a batch_v1 simulation, a kinetic fit a forecast draws from, or a forecast | those artifacts' ids, newest first, each titled with its kind and when the project kept it (`a batch_v1 simulation, kept …`, `a kinetic fit, kept …`, `a forecast, kept …`), and no default | `vessel.design` for the simulation, the fit or the forecast; the tool `fermos.vessel` |

- Each thing's precision is `rtol` 0 and `atol` 0: fermOS replays a computation identically.
- `parameters(thing, configuration)` is the thing's own parameter scope (`fermos:family:<id>`,
  `fermos:forecast:<fit id>`, `fermos:vessel:<id>`) resolved with nothing set: a convention keeps
  its default (origin `convention`, with its note), a vessel class's own default keeps it (origin
  `library-default`, its `ref` naming BioSTEAM), and every other parameter has no default.
- The things are read afresh in the request's project on every listing, from the artifact
  store's tool column. A run names its thing and its configuration, and reads the one artifact the
  configuration names; a configuration the thing cannot take is refused naming those it lists.
- A run's values are checked before anything runs (`runs.check_inputs`; a value outside its
  bounds is kept and flagged on the artifact, as fermOS has always flagged one). A design's
  values are held by the vessel's own scope, whose keys are those of its kind (an anaerobic
  design takes a plant scale and no batch volume) and whose choices follow the vessel type the
  run chooses: a key the scope lacks is refused in words, naming the scope's own keys or saying
  why its kind takes none (an anaerobic vessel's type). A range on a value is kept in the run's
  basis as `<key> low` and `<key> high` beside it, and the run integrates at the value.
- A run's id is its fermOS artifact's: the artifact's tool at fermOS's own tool version
  (`kinetics <family> 2 · scipy <version>` for a simulation, `fermos-1` for a forecast,
  `vessel 3 · biosteam <version> · thermosteam <version>` for a design) over fermOS's basis, so a
  change to fermOS's computation moves the tool version and the id. A forecast's basis names a
  start value it sets `start X0`, `start S0` or `start P0`, in the unit of the fitted run's
  series, and a length it sets `duration`, in hours.
- `version()` names what the engine as a whole runs on: numpy and scipy, and biosteam and
  thermosteam, each as its installed metadata records it, the versions a vessel design's tool
  version names. The conformance verdict's version is the contract's version string over it
  (`engine run 1 · kinetics · …`); the stem's rules (The run's row, above) are the contract
  engines' own. Each row's `versions` names what its thing ran on: numpy and scipy for a
  family's simulation and a forecast; biosteam and thermosteam, as the design's tool version
  names them, and biorefineries, the package its chemicals are read from, for a vessel design.
- fermOS's own doors keep the same row: `POST /api/fermos/simulate`, `POST /api/fermos/forecast`
  (a kept fit's forecast; the sample run's keeps nothing) and `POST /api/fermos/vessel`, and the
  tools `fermos_simulate`, `growth_forecast`, `fermos_vessel` and `fermos_write`, each in the name
  of the person the request names or the caller the tool names. The tools take ids and words
  (`docs/TOOLS.md`): a person sets a value on fermOS's screens, through the routes above, or at
  `POST /api/engines/kinetics/run`, each value carrying the day it was set (`at`). The row's id is
  the artifact id, so the same request at any door is one row. A parameter that waits refuses
  the run in words and keeps nothing; a refusal inside the computation (the integration, the
  forecast's draws, BioSTEAM's refusal of a design) is kept as a receipt. A kinetics run writes no
  SFF file, and `sffRefused` says why. `docs/api/runs.md` gives the outputs each tool keeps.

## The core's `train`

`openferment_core.pureos.engine:ENGINE`, registered by `core/pyproject.toml`, puts pureOS's
trains behind the contract as pureOS runs them. `worker` and `heavy` are the biosteam engine's: a
train is built and run in the Proforma worker, and importing the module imports neither. Every
thing is a project's own, so the engine declares `things_are`, `rests_on` (the rows a train's
resolution reads, Conformance, below) and `unready`.

| Thing | Configurations | A run of it |
|---|---|---|
| Each train the project holds: each pureOS's Builder saved (the project's `trains` rows, `PUT /api/state/trains/{id}`, `kind` `made`) and each a model built (`pureos_build`, `kind` `kept`), its id the train's and its title the train's name, a model's train naming who built it | none | `pureos/train_spec.run_train`, the train with the run's inputs and `by`; the tool `pureos.train_run` |

- The things are read afresh in the request's project on every listing and every run, and none
  is kept: a project that holds no train lists none. A run names a train the project holds, and
  one it lacks is refused naming those it holds; a train takes no configuration, and a
  configuration named is refused in words.
- Each thing's precision is exact (`rtol` 0, `atol` 0; `train_spec.replay_precision`). The
  library run's rule holds a run to one unit in the last digit it keeps; a library run rounds
  its outputs to the digits its `precision` input states, and a train run keeps every digit
  BioSTEAM gives, so its replay is identical, as train runs have replayed since they were kept
  (`docs/api/runs.md`, Replay).
- `parameters(thing)` is each place's values as a run of the train resolves them with nothing set
  (`train_spec.resolved`): the inlet's, then each unit's in the train's order, keyed `inlet.<key>`
  and `<unit id>.<key>`. Each default carries the origin its resolution names: a unit class's own
  (`library-default`, its `ref` naming BioSTEAM), a shelf flowsheet's own unit (`library-default`,
  its `ref` naming the package), the inlet's T and P from thermosteam's Stream defaults
  (`library-default`, its `ref` naming thermosteam), a convention (its note), the records that
  bound it (`record`, its `ref` naming them), the inlet's run, simulation or design (`artifact`,
  its `ref` naming it), or a value a person typed into the train (`person-assumption`, naming
  the person and the day). A train's own values are a person's: a typed value names its person
  and its day and no origin of its own, so the Builder's train and a model's (which holds ids
  and words, `pureos_build`) hold no model's estimate and no reading, and those two reach a
  train's run as values the run sets. A resolution handing in one as a default is refused in
  words (`pureos/engine.py` `DEFAULT_OF`, the five a default may rest on).
- A parameter with no default is one of two. A value that waits for what would bind it: a run
  sets it, or the run is refused naming what would bind it. A value the train fills itself when
  a run leaves it unset: one the unit's class decides at run time (a flash's temperature beside
  its pressure and vapour fraction), a component a typed inlet does not carry, a split of a
  component the train leaves to the class; its `note` ends `A run may leave it unset, and the
  train then fills it itself (<the resolution's reason>).`
- A run's values are checked and converted at pureOS's own door, the same at every door (the
  engine's run route, `POST /api/pureos/train/run` and `/check`, the tools): each through
  `basis.override_of` in its place's scope (`pureos:unit:<train>:<unit id>` or
  `pureos:unit:<train>:inlet`, `train_spec.converted`), the one converter every door shares. A
  name of neither form, a place the train lacks, a key its place lacks, a key set twice and a
  value its parameter cannot take (another unit, words for a number, a choice not offered, an
  origin that is no person's, no model's and no deposition's reading; a reading in a unit that
  converts is set in the parameter's) are refused together with everything else the run would
  refuse, the inputs' refusals first, each in words by its place, and keep nothing. A value
  outside its bounds is kept as set and flagged on the run, as pureOS has always flagged one.
- A run's id is its `pureos.train_run` artifact's (`train run 2 · biosteam <version> · thermosteam
  <version> · biorefineries <version>` over pureOS's basis), so the same train with the same values
  is one row at every door: `POST /api/pureos/train/run`, the tools `pureos_build` and
  `pureos_write`, MCP, and `POST /api/engines/train/run`. Each keeps the row in the name of the
  person the request names (`by`) or the caller the tool names. A value that waits refuses the run
  in words naming what would bind it, and keeps nothing; the Proforma worker's refusal of a train
  BioSTEAM cannot build or run is kept as a receipt in its words.
- `version()` names the simulator's distributions (biosteam, thermosteam, biorefineries) as their
  installed metadata records them, and the train run's own version (`train run`), and starts no
  worker. Each row's `versions` names what its basis names, the versions the worker ran.
- The run's SFF file is asked of the Proforma worker from the run's own basis (`sff_export`,
  `docs/api/sff.md`), and kept as `run-<id>`. A train carries no TEA, and the schema the toolkit
  ships at its pinned commit requires every file's `metadata.TEA_year`, which its exporter reads
  from the system's TEA (`tea.duration[0]`, `export/_export.py`). While the schema requires the
  year, the worker refuses a train's file in those words before it builds anything, each train
  run keeps them as `sffRefused`, and check 5 holds by them; once the schema leaves the year to
  the file, the worker rebuilds the train from the run's basis, simulates it and writes it as a
  library plant's is. `docs/api/runs.md` (A train run) gives the row and the outputs a train run
  keeps.

## Conformance

`python -m openferment_core.engine.conform <name>` checks an installed engine against this page
and prints one row per check, on a database of its own that it drops after; it exits 1 when any
check fails, and keeps its verdict for `GET /api/engines`. `pnpm prove` runs it for every engine
registered. Run it as `cd core && uv run python -m openferment_core.engine.conform <name>`. It
makes its database on the PostgreSQL 16 or later server with pgvector that
`OPENFERMENT_DATABASE_URL` names (the environment first, then `core/.env`), needs no running
service and no key, and keeps its verdict in that address's database's `engine_checks`, with
`--project` or without, once that database is migrated (`pnpm db:migrate`); a verdict it cannot
keep is printed with the words why. With no address set, or a server that does not answer, it
says so in words naming `OPENFERMENT_DATABASE_URL`, and exits 2.

- `--thing <id>`, as often as needed, narrows the checks to those things, in the order named;
  the first named is the one run, and an id the engine runs none of is refused in words. With
  none, every thing's parameters are read and the engine's first thing is run. With `--project`
  (below), each thing named is run. An option given with no value is refused in words naming
  what it takes (`--project needs a project's id`).
- `--inputs <file>` names a JSON list of `EngineInput`s the checked run sets, for a thing whose
  parameters leave a value to the run. With none, the run is made at the thing's own defaults.
  Every kinetics family waits for values no default gives:
  `openferment_core.fermos_engine.write_placeholder_inputs(path, by=...)` writes the file for
  the first family, each parameter with no default at 1 in its own unit, the product's start
  value at 0 and a parameter chosen from words at its first choice, each a person's assumption
  dated `at`, or the day the file is written; `conform kinetics --inputs <file>` makes the eight
  checks with it, and `pnpm prove` writes the file for it in step 10.
- The checks run in a project of their own, made fresh on their own database, so a thing an
  engine lists only while the project holds what it takes is left out of them: the kinetics
  engine's `forecast` and `vessel`, whose parameters and runs `core/tests/test_engines.py`
  holds.
- `--project <id>` checks the things that project of the configured database (`core/.env`)
  holds, for an engine whose things are a project's own (`things_are`): the train engine's things
  are a project's trains, so `conform train --project <id>` checks the trains that project holds.
  The checks read the project and run on a copy of it:
  - **What is read.** The project's own row, and the rows the engine's `rests_on()` names, each
    whole, read from the configured database, where the checks write their verdict alone. The
    train engine names every train the project holds; each artifact a train's inlet reads, by its
    id, with its run's row where the project keeps one (a simulation and its vessel design, a
    run's artifact, a scenario's newest run); the scenarios a run-stream inlet names; the evidence
    pool whole, every candidate and every decision, since a value binds the records of its field
    that the pool holds and its words count each record the value leaves out; and every strain the
    project keeps, since a simulation names its strain, and pureOS reads that strain's species, and
    the one species of its chemical set, from all of them; and every deposition the project keeps,
    since a value a run of a train sets may be a deposition's reading, which the run looks up in
    them (`measurements.py`). The pool also reads the titles of the
    project's documents for its search; the copy leaves them out, and every value and every word of
    a train reads the same in the copy as in the project.
  - **Where the checks run.** A database of the checks' own, made on the configured server and
    migrated, holds those rows under the same ids in a project of the same id; every session of
    the checks is a savepoint of one transaction there. The database is dropped when the checks
    end, however they end: a check that raises, Ctrl-C, `SIGTERM` or `SIGHUP`. A process killed
    outright (`SIGKILL`, a machine that stops) leaves it on the server, named
    `openferment_conform_<engine>_<eight hex digits>` and holding the migrated schema and no row,
    since every row the checks write stays in a transaction they never commit; `cd core && uv run
    python -m openferment_core.migrations drop <name>` drops it, and `pnpm prove` asks a run that
    outlives its time to end (`SIGTERM`) before it kills it. A runs row of the engine being
    checked is left out of the copy, so every runs row of a thing there is one the checks made, in
    their name or check 8's model's: a person's earlier run of a train changes nothing, and the
    checks' run of a train at the values a person's run set keeps that run's id, its row the
    checks' own. An artifact is copied as its id is named: a train run that another train's inlet
    reads is copied as its artifact, so the checks' run of the first train at that run's values is
    answered from that artifact, and check 4's replay computes it again.
  - **What is checked.** Each thing `--thing` names, in order, as named; else each thing the
    copy holds that can run. The values `--inputs` names are set on every thing checked. A thing
    the engine says cannot run as it stands (`unready`: a saved draft, a train whose values wait
    for a source, a train whose run is refused before it computes) is left out, and listed with
    its words: a train that lacks a place a value names is refused that way, so `--thing` narrows
    the file's values to the trains they fit. Checks 3, 4, 5 and 8 run on every thing checked,
    each holding when it holds on every one, its words each thing's in turn; check 2 reads the
    parameters of every thing checked; checks 1, 6 and 7 run once for the engine, check 1 on the
    first thing. Check 3's words end with where the checks ran and how many rows were copied, then
    the things left out, each numbered, with its words.
  - **What is written.** The verdict alone, one row of the configured database's `engine_checks`,
    replacing the engine's last; `GET /api/engines` and `pnpm ready` read it there. The row is the
    machine's, no project's, so the verdict it keeps gives counts in each check's words (the things
    checked and the things left out), naming no project, thing or run; the command's own table
    gives each thing's words. Each command keeps one verdict for the engine, so a project whose
    trains wait for different values is held by its last command's verdict.
- The production database (`openferment`) is read as any other: the live host checks its own
  projects' trains with the same command, and `pnpm ready` names it there. A project the database
  does not hold is refused in words, and so is a project that holds no thing that can run: one
  that holds none of the engine's things is told what they are, and one whose every thing is left
  out is given the list, each with its words, and the ways on (make a thing that runs, set the
  values a waiting thing needs with `--inputs <file>`, or name one with `--thing <id>` to check
  it as it stands). Either refusal exits 2, keeps nothing, and leaves the engine's last verdict
  standing. An engine that declares `things_are` with no `rests_on` is refused the same way, with
  or without `--project`, and an engine that declares no `things_are`, asked with `--project`, is
  told it is checked with none. An engine that declares `things_are`, checked with no
  `--project`, is refused in words saying what its things are and naming the command, and exits
  2. `pnpm prove` step 10 makes a train in the proof's own project and checks the train engine
  with `--project` there.
- Each thing is checked in its default configuration, or in the first it names when it has no
  default. No check reads a configuration's title, which is words for a person. A `things`
  answer outside `EngineThing`'s shape, a title for a configuration the thing lists none of among
  them, stops the checks before the first: the command says the engine's words, exits 1 and
  keeps no verdict, while `GET /api/engines` lists the engine with those words and its
  parameters and runs answer 503.
- Check 1 needs nothing of the engine beyond a first thing: its numbers stand where the route's
  and the tool's own fields refuse them. Check 2 holds every default to an origin naming what it
  rests on, one of the five a default may rest on (a library-default, a record or an artifact its
  `ref`, a convention its `note`, a person's assumption its `by`), and every
  parameter with no default to a source rule naming `assumption`: it takes a run's value, which a
  run sets, the engine binds or the thing fills itself (`EngineParameter`); for an engine built
  on `WorkerEngine`, a run sets it. Check 3 holds the
  run's id to the artifact id of its basis (its seed joining it where the computation takes
  one); a run that answers no output holds it, its words saying the outputs are empty; and a run
  that answers diagnostics holds it when they stand in their shape on its row and nowhere in its
  artifact, the same request again answering the first computation's, its words naming each.
  Check 6 imports the entry point's module in a
  process of its own and holds out of it the worker module, every module `heavy` covers, and the
  five libraries the service keeps out for every engine, an engine whose worker is `None` among
  them. Check 7 offers a
  WorkerEngine's worker the thing `conform-no-such-thing` as one of its own, standing in for the
  engine's `things` and `parameters` in the service's process (the thing listed, with no
  parameters), so the worker's `run` op alone meets it: the first ask reaches the worker's `run`
  op once, its `Refused` is kept as a receipt in its words, and the same request asked again is
  answered from the receipt with the worker's `run` op never asked. At the routes the service
  refuses an unknown thing from the worker's `things` answer before any other op is asked, and
  the worker's own refusal in `parameters` and `sff_export` is reached when a test calls them. A hand-written
  engine (the core's three, `biosteam`, `kinetics` and `train`) computes in code of its own, with
  no `compute` the check can offer a thing to, so check 7 holds the refusal it reaches there: the
  unknown thing refused in words before any run, keeping nothing, and its words say so. A refusal
  inside such an engine's own computation is the receipt its own run keeps, which the engine's
  own tests hold (for the core's three, `core/tests/test_engines.py` and
  `core/tests/test_runs.py`). Check 8 asks a second
  run in a model's name, on a basis of its own: with no values set, through the `engine_run` tool
  on another thing checked, or else another configuration of the first; with values set, with
  no second basis, or with every thing checked (`--project`: check 3 has run each thing already),
  through the run itself, the checked run's values as the model's estimates, or, with none set,
  one parameter at its own default: the first whose source rule takes a run's value
  (`assumption`), else the first with a default. Each estimate is dated the day the check runs. A
  thing with one configuration or none, no second thing and no default holds check 8, its words
  saying the model's path had nothing to set.

| # | Check |
|---|---|
| 1 | A JSON number outside a `quantity` is refused in words before the worker is reached |
| 2 | Every default carries an origin naming what it rests on (`library-default`, `record` or `artifact` with `ref`, `convention` with `note`, `person-assumption` with `by`), and a parameter with none takes a run's value |
| 3 | A run writes one `runs` row keyed by its basis, and the same request twice is that one row, with its diagnostics in their shape when it reports some |
| 4 | A replay holds every output within the precision the thing states |
| 5 | The run's SFF file validates and scores, or `sffRefused` holds words |
| 6 | Importing the module the entry point names imports neither the worker module nor what the engine computes with |
| 7 | A request the engine refuses is kept as a receipt in its words, with no traceback |
| 8 | `created_by` on every run is the person or the model that asked for it |

## An engine's own tests

An engine's tests need neither the service nor its database. `openferment_core.workers` and
`openferment_core.engine` import with no `core/.env`; `ENGINE.version()` reads installed
metadata; `ENGINE.things()` and `ENGINE.parameters(<thing id>, <configuration or None>)` start the
worker and answer `EngineThing` and `EngineParameter` (`openferment_core.models`), the thing named
by its id; `serve(HANDLERS, name=..., stdin=..., stdout=...)` answers the text streams a test hands
it (both of them, The worker, above); and `SimWorker('<worker module>',
withhold_secrets=True).call(op, args)` speaks to the worker as the service does, a refusal raising
`WorkerError` whose words are the worker's answer's `error` as it stands, `Refused: <the
handler's words>` for a refusal. The models `ENGINE.things()` and `ENGINE.parameters()` answer
carry their fields under the names the JSON gives them (`thing.id`, `thing.precision.rtol`,
`parameter.origin.ref`), each number as the model types it (a precision of `0` reads `0.0`). Through `ENGINE`, a worker's refusal raises
`EngineRefused` (`openferment_core.engine`) in the words after `Refused: `, and an answer outside
the protocol raises `EngineBroken`. `WorkerEngine` has no method that stops its worker: the worker
`ENGINE` starts runs until the test's process ends and its input closes, and a test that wants it
gone uses `SimWorker` and its `close()`. `run()`, `replay()` and `export_sff()` keep or read the
store, and `conform` holds them.

An engine's own tests hold its replay at the worker: the same `run` request asked twice answers the
same outputs in the same order. The service's replay, held to the thing's precision, is
conformance check 4's, and `conform` needs a PostgreSQL server (Conformance, below); a builder
working from a request that names no database address leaves `conform` to the base, which runs it
on the base's own server, as `pnpm prove` step 10 does.

Install the package first (What an engine is, above), so its entry point and its version stand and
its worker's module imports in a process of its own. Then run its tests from the package's
directory with the service's interpreter, `<repository>/core/.venv/bin/python -m pytest`, which
holds pytest and `openferment_core`. `[tool.pytest.ini_options]` with `testpaths = ["tests"]` in
the package's `pyproject.toml` has `python -m pytest`, run in the package's directory, collect
`tests/`; `core/tests/conftest.py` lies outside the package's directory tree, so pytest loads none
of the core's conftest files there. `uv run` in the package's directory makes an environment of the
package's own, which holds no `openferment_core`.

## A skeleton: the placeholder engine `example`

A whole engine in four files, every value a placeholder in a placeholder unit: one thing, one
parameter with its default, two outputs, the time its run took as a diagnostic, and no plant. Its
one parameter carries a default, so its run on the engine's own defaults computes, as the proof's
walk and checks ask (What an engine is, `pnpm prove`). The core's three (above) are this page's
other examples.

```
openferment-engine-example/
  pyproject.toml
  openferment_engine_example/__init__.py      empty
  openferment_engine_example/engine.py        the object the entry point names
  openferment_engine_example/worker.py        the four ops and serve
  tests/test_worker.py                        the worker driven as the service drives it
```

`pyproject.toml`: the entry point in the group, a backend that makes an editable install, and
where pytest collects. It declares no licence, as a package under `examples/` declares none. An
editable install with setuptools writes `openferment_engine_example.egg-info/` beside these files,
the install's own record, which git ignores.

```toml
[build-system]
requires = ["setuptools>=70"]
build-backend = "setuptools.build_meta"

[project]
name = "openferment-engine-example"
version = "0.1.0"
description = "A placeholder engine for openFerment's engine contract"
requires-python = ">=3.12"

[project.entry-points."openferment.engines"]
example = "openferment_engine_example.engine:ENGINE"

[tool.setuptools]
packages = ["openferment_engine_example"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`openferment_engine_example/engine.py`: the engine, its worker and the distribution its version is
read from; it computes with nothing heavy, so `heavy` is left at `()`.

```python
"""The example engine: the one object its entry point names."""
from openferment_core.engine import WorkerEngine

ENGINE = WorkerEngine(name="example", worker="openferment_engine_example.worker",
                      distributions=("openferment-engine-example",))
```

`openferment_engine_example/worker.py`: each op a handler taking the request's `args`, a refusal
in the engine's words, the default's origin naming the installed distribution and version, and the
time the run took answered as a diagnostic beside the outputs.

```python
"""The example engine's worker: its four ops over placeholders, one JSON request a line."""
import time
from importlib.metadata import version

from openferment_core.workers import serve

THINGS = [{"id": "a-thing", "title": "A placeholder thing", "kind": "placeholder", "configurations": [],
           "precision": {"rtol": 0, "atol": 0}}]


class Refused(Exception):
    """A request the example engine refuses, said in its words."""


def _thing(args):
    if args.get("thing") not in {t["id"] for t in THINGS}:
        raise Refused(f"the example engine runs no thing {args.get('thing')!r}")


def things(args):
    return {"things": THINGS}


def parameters(args):
    _thing(args)
    ref = f"openferment-engine-example@{version('openferment-engine-example')}"
    return {"parameters": [
        {"key": "a-parameter", "label": "A placeholder parameter", "unit": "placeholder-unit", "value": 1.5,
         "origin": {"kind": "library-default", "ref": ref}, "min": 0, "max": 10,
         "boundsReason": "placeholder bounds, so a value outside them is refused"}]}


def run(args):
    started = time.perf_counter()
    _thing(args)
    given = {v["name"]: v["value"] for v in args["inputs"]}
    outputs = [{"name": "a-placeholder-output", "value": given.get("a-parameter", 1.5), "unit": "placeholder-unit"},
               {"name": "values set", "value": len(given), "unit": ""}]
    took = (time.perf_counter() - started) * 1000
    return {"outputs": outputs, "diagnostics": [{"name": "time taken", "value": took, "unit": "ms"}]}


def sff_export(args):
    _thing(args)
    raise Refused("the example engine has no plant, so it writes no SFF file")


HANDLERS = {"things": things, "parameters": parameters, "run": run, "sff_export": sff_export}

if __name__ == "__main__":
    serve(HANDLERS, name="example")
```

`tests/test_worker.py`: one test, the worker started and asked as the service asks it, with no
database.

```python
"""The worker driven as the service drives it: SimWorker, one JSON request a line."""
import pytest

from openferment_core.workers import SimWorker, WorkerError


@pytest.fixture
def worker():
    w = SimWorker("openferment_engine_example.worker", withhold_secrets=True)
    yield w
    w.close()


def test_the_worker_answers_its_four_ops_as_the_service_asks_them(worker):
    (thing,) = worker.call("things", {})["things"]
    (parameter,) = worker.call("parameters", {"thing": thing["id"], "configuration": None})["parameters"]
    assert parameter["origin"] == {"kind": "library-default", "ref": "openferment-engine-example@0.1.0"}
    asked = {"thing": thing["id"], "configuration": None,
             "inputs": [{"name": "a-parameter", "value": 2.0, "unit": "placeholder-unit"}]}
    answer = worker.call("run", asked)
    assert answer["outputs"] == [{"name": "a-placeholder-output", "value": 2.0, "unit": "placeholder-unit"},
                                 {"name": "values set", "value": 1, "unit": ""}]
    assert [d["name"] for d in answer["diagnostics"]] == ["time taken"]
    with pytest.raises(WorkerError, match="^Refused: the example engine has no plant"):
        worker.call("sff_export", asked)
    with pytest.raises(WorkerError, match="^Refused: the example engine runs no thing 'nothing'"):
        worker.call("run", {**asked, "thing": "nothing"})
```

Install it with the install of What an engine is (above), its path
`<path to openferment-engine-example>`, and restart the service; run its test from its directory
with `<repository>/core/.venv/bin/python -m pytest`; and check it with `cd core && uv run python -m
openferment_core.engine.conform example` on a PostgreSQL server (Conformance), whose eight checks
hold, check 3 naming its one diagnostic and check 4 its replay identical.

## What is deliberately absent

- No kinetics socket: the kinetics engine runs the families fermOS builds, and the light_v1
  socket fermOS declares stays out of its things.
- No scenario fields beyond parameters: a study scenario is one of BioSTEAM's plants, a
  configuration and values for its parameters (`docs/api/studies.md`); a contract engine's
  values are set on its run.
- No import of an SFF file into an engine: a file is a record, and an engine's recipe is code.
- No science on this page: every value is a placeholder.
