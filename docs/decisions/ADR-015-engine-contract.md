# ADR-015 — Engines register through Python entry points, behind one contract

- **Status**: accepted (the owner's authorization, alpha 2.2 execution prompt §3)
- **Date**: 2026-11-03

## Context

Through alpha 2.1 BioSTEAM was openFerment's one engine, reached through `engine/library.py` and
the Proforma worker (ADR-004), its runs kept as rows of `runs` (`docs/api/runs.md`). fermOS's
kinetics, pureOS's trains and Proforma's shelf flowsheets computed artifacts of their own, took
`Override`s, and kept no row (debt 3 in `docs/PROGRESS.md`).

Alpha 2.2 seals the base (`docs/BASE.md`): a person who has never spoken to the owner adds an
engine with zero edits to the core. That needs three things: a written contract a stranger builds
from (`docs/api/engines.md`), discovery that never names the engine in the core, and a check by
code that an engine keeps the contract.

## Options considered

1. **A class hierarchy in the core.** An abstract `Engine` base class in `openferment_core`, every
   engine a subclass, the list of engines an import list in the core. Each new engine edits that
   list, so the handoff test fails by construction.
2. **A registry by entry points.** A package declares
   `[project.entry-points."openferment.engines"]` in its `pyproject.toml`; the core reads
   `importlib.metadata.entry_points(group="openferment.engines")` at startup. Installing the
   package is the whole registration, and the core's own engines are declared the same way in
   `core/pyproject.toml`.
3. **A registry by configuration file.** A file the core owns (a TOML list, or a line of
   `core/.env`) names each engine's module. Installing an engine then edits that file, and the
   file drifts from what the environment holds.

## Decision

Option 2.

- `Engine` (`engine/__init__.py`) is the protocol: `name`, `worker`, `heavy`, `version()`,
  `things()`, `parameters(thing, configuration)`, `run(thing, configuration, inputs, by)`,
  `replay(run)`, `export_sff(run)`. `docs/api/engines.md` states each with its fields.
- `WorkerEngine` (`engine/contract.py`) implements the protocol over four ops of a worker of the
  engine's own (`things`, `parameters`, `run`, `sff_export`; `docs/api/workers.md`). An engine
  package is then a declaration and a worker module.
- `engine/registry.py` loads each entry point of the group once. A load error, an object whose
  `name` differs from its entry point's, a method missing, or two packages claiming one name is
  said in words; `GET /api/engines` lists the engine with that error, and the service runs on.
- `engine/runs.py` keeps every contract engine's run as one row of `runs`, of the shape a library
  run has. Its id is the artifact id over the tool `engine.<name>`, the engine's version string
  (the contract's stem, the engine's name and every distribution with its version:
  `engine run 1 · <name> · <distribution> <version> …`) and the basis: the engine, the thing, the
  configuration, the precision the thing states, and every value set with its origin and the day
  it was set. The same request twice is that row; a refusal is kept as a receipt; the SFF file
  the engine writes is validated and scored in the Proforma worker, or the engine's words for why
  none exists are kept as `sffRefused`. A worker that answers outside the protocol raises
  `EngineBroken`: nothing is kept, and the routes answer 503 in words.
- An engine's worker starts with the service's interpreter, `core/` as its working directory,
  and an environment less every variable named as a key, token, password or database address
  (`workers.withheld`).
- `python -m openferment_core.engine.conform <name>` makes the eight checks of
  `docs/api/engines.md` on a scratch database and keeps the verdict in `engine_checks`, where
  `GET /api/engines` and `pnpm ready` read it. `pnpm prove` runs the checks for every registered
  engine.
- Migration 0008 adds `runs.engine` (rows kept before it read `biosteam`); migration 0009 adds
  `engine_checks`.

## Consequences

- **`engine/library.py`** keeps every number and test: the A→B→A gate, the replay precision and
  ADR-013's package-test values stand as they were. `engine/biosteam.py` puts it behind the
  protocol, registered by `core/pyproject.toml` as
  `biosteam = "openferment_core.engine.biosteam:ENGINE"`. ADR-004's revisit condition, a second
  engine, is met here; its adapter is the `biosteam` engine.
- **fermOS** is registered as the engine `kinetics` through the same group, by
  `core/pyproject.toml` (`kinetics = "openferment_core.fermos_engine:ENGINE"`; stage C of alpha
  2.2). It wraps fermOS as fermOS computes: its things are the model families that simulate
  (`batch_v1`, `fedbatch_v1`, `chemostat_v1`, the light_v1 socket left out), a forecast whose
  configurations are the project's kept kinetic fits, and a vessel design whose configurations
  are the project's kept batch simulations, fits and forecasts, the last two things listed while
  the project holds one; its parameters are each thing's own scope, a convention's default and a
  vessel class's own each with its origin, and every other parameter with none; its runs are
  `fermos.simulate`, `fermos.forecast_run` and `vessel.design`, each of which keeps the run's row
  (`runs.compute_kept`), so fermOS's routes, its tools, MCP and the engine make one row for one
  request. Its integrators compute in the service process (`test_workers.py` allows SciPy in
  `kinetics.py` and `fermos.py`) and a vessel design runs on BioSTEAM in the Proforma worker, so
  its `worker` is `None` and its `heavy` `()`, which the contract allows for an engine with
  nothing heavy to keep out of the service. Its rows replay identically (precision rtol 0, atol
  0), and every trajectory stays bit for bit, with every artifact id but one
  (`core/tests/test_engine_pins.py`): D1's amendment at C.2 moves the id of the forecast that
  sets a start value, whose basis now names the day the value was set and the unit it is typed
  in, and its output hash holds. A run's id is fermOS's own artifact id, keyed by fermOS's tool
  version; `version()` names what the engine as a whole runs on (numpy, scipy, biosteam and
  thermosteam), and each row's versions what its thing ran on. A parameter with no default has
  `value` and `origin` null in the contract (`EngineParameter`), and a run that leaves one unset
  is refused in words, keeping nothing; conformance runs `kinetics` with `--inputs`, the file
  `fermos_engine.write_placeholder_inputs` writes, and the proof writes it in step 10.
  Conformance runs in a fresh project, so the forecast and the vessel, listed only while the
  project holds what they take, are held by `core/tests/test_engines.py`. fermOS's tools take ids
  and words, as rule E.4‴ has them: a person sets a fermOS value on the screens' routes or at
  the contract's run route.
- **pureOS** is registered as the engine `train` through the same group, by
  `core/pyproject.toml` (`train = "openferment_core.pureos.engine:ENGINE"`; stage C of alpha
  2.2). Its things are the project's own trains, each pureOS's Builder saved and each a model
  built, read afresh on every ask, none taking a configuration. A database made for the checks
  holds none, so the engine declares what its things are (`things_are`, listed by `GET
  /api/engines` as `thingsAre`) and conformance runs it in a project that holds a train
  (`conform train --project <id>`): one train, the first named or the first that runs, on a basis
  of the checks' own, so their rows and a person's keep apart. The production database is
  refused in words, and there `pnpm ready` says where the checks run. The proof makes a train from
  step 4's corn stover run through pureOS's from-run and checks it there in step 10: the tail of
  the read train after its last unit whose values wait (at these pins the four units from T701
  on, none of them a separation, which a debt in `docs/PROGRESS.md` holds). Its parameters are
  each place's values as a run resolves them, keyed `inlet.<key>` and `<unit id>.<key>`, each
  default with the origin its resolution names, so a default's origin widens to the five a
  project's thing holds (a library-default, a convention, a record, an artifact, a person's
  assumption), and check 2 holds each to what it names; a value the train fills itself when a run
  leaves it unset says so in its `note`. A run's values are `EngineInput`s named
  `<unit id>.<key>` or `inlet.<key>` at every door (`TrainRunRequest.inputs`), checked and
  converted at pureOS's own door through `basis.override_of` in each place's scope, every refusal
  at once by place in the same words at every door, so the train's artifact ids stand as pinned
  (`core/tests/test_engine_pins.py`).
  `train_spec.run_train` keeps the run's row (`runs.compute_kept`), so pureOS's routes, its tools,
  MCP and the engine make one row for one request: its outputs the values pureOS reads from the
  run's tables (registered with the tool, `artifacts.register`'s `values_of`, since the engine
  package reads no pureOS module), its SFF file asked of the Proforma worker from the run's basis.
  A train carries no TEA, and the schema the toolkit ships at its pinned commit requires every
  file's TEA year, which its exporter reads from the system's TEA, so the worker refuses a
  train's file in those words before it builds anything, and every train run keeps them as its
  `sffRefused`. Its rows replay exactly: a train run keeps every digit BioSTEAM gives, so the
  library run's last-kept-digit rule holds it at rtol 0, atol 0 (`train_spec.replay_precision`),
  as train runs replayed before they were rows. Its worker and its heavy modules are the
  biosteam engine's: a train builds and runs in the Proforma worker.
- The four engine tools (`engine_plants`, `engine_parameters`, `engine_run`, `engine_report`)
  take `engine`, `biosteam` by default; the tool registry keeps its 48 names.
- The package map (`core/tests/test_boundaries.py`) holds two exceptions for the conformance
  check: `engine → api` and `engine → tools`, the two doors a bare number is sent through.
- An engine's code runs in the service's process when its entry point loads, and its worker runs
  as the service's user: installing an engine trusts its code with whatever that user can read,
  `core/.env` included. The worker's environment carries no variable `workers.withheld` names
  (those beginning `ANTHROPIC_` or `SCI_RAG_`, and those whose name holds `KEY`, `TOKEN`, `SECRET`,
  `PASSWORD`, `PASSWD`, `DATABASE_URL` or `CREDENTIAL`). The registry and conformance check 6 keep
  the worker module, every module its `heavy` covers, and `workers.WORKER_LIBRARIES` out of the
  service's process for every engine. Installing a package into the environment is the host owner's
  act; the registry adds no network exposure, and the loopback bind and `guard.py` are as they
  were.
- An engine from outside the core is installed into core's environment with
  `cd core && uv pip install -e <path>`, and an exact `uv sync` (`scripts/session-start.sh`,
  `scripts/host/deploy.sh`) removes it; the service reads the group once, so an install is
  followed by a restart, and a new version of the package takes effect once it is installed again.
  The proof's install step for such a package, and the licence check of it
  (`pnpm check:licences` reads the packages `core/uv.lock` names), arrive with the handoff, stage D
  of alpha 2.2.
- Every contract engine's tool version begins with the contract's stem, `engine run 1`
  (`contract.CONTRACT_RUN`): a change to how `runs.run_engine` keys a run or shapes its outputs
  moves the stem, so a run kept before it keeps its own id, its replay names the version it was
  kept at (a `toolVersion` difference), and the nightly checks report it as stale.
- An engine's version changes whenever its computation changes: an editable install keeps its
  version across edits of its code, and a run's id holds the version, so a new version is what
  makes the service compute a request afresh.

## Revisit condition

A second scientific engine arriving beyond the three in the tree, or the SFF toolkit shipping an
importer (ADR-003).

## Evidence

- `core/tests/test_engines.py`: the registry, `GET /api/engines`, a run kept as one row, a value
  set with its origin and its own day, a bare number refused before the worker, values the
  parameters refuse, a receipt, a replay, the worker's environment, the four tools, and the eight
  checks on the contract's own sample engine (`engine/sample.py`); discovery that keeps running
  past an engine whose import exits, whose declaration raises, which asks the registry as it is
  imported, or which brings its worker or a heavy module into the service; a worker answering
  outside the protocol (`EngineBroken`, nothing kept, 503); the listing's short wait on a cold
  worker and its things kept once answered; BioSTEAM checking a value's unit before the plant
  runs; a write at the HTTP tool door naming its caller. After the review of B.6: every door
  resolving a thing's configuration as a run does, a configuration name of up to 80 characters at
  each of them, a value carrying a range or a basis refused, a dotted heavy name, an undeclared
  worker library and one heavy module two engines share each setting an engine aside, a thread an
  entry module starts answered, a replay naming the version a run was kept at, and check 7
  holding its first ask to one call of the worker's `run` op.
- `core/tests/test_workers.py`: a worker module that prints as it is imported, from Python and
  from C, leaves every response whole (`workers.LAUNCH`).
- `core/tests/test_boundaries.py`: `from X import y` read as the module `X.y` where y is one, so
  the engine's row refuses a worker module imported from its package.
- `python -m openferment_core.engine.conform biosteam`: the eight checks on BioSTEAM.
- `core/tests/test_engines.py` (stage C): `GET /api/engines` lists `kinetics` with no worker, and
  its forecast and vessel once the project keeps what they take; a run of each of its things is
  one row at every door, the same request twice that row, its versions what its thing ran on; a
  parameter that waits is refused with nothing kept; a refusal inside the integration is kept as
  a receipt; a vessel's refusals name its own scope's keys; a worker its computation calls that
  cannot answer is a 503 naming it; and `conform kinetics --inputs <file>` holds all eight checks
  on a scratch database. `pnpm prove` step 10 makes the eight checks on `kinetics` with the
  placeholders it writes.
- `core/tests/test_engines.py` and `core/tests/test_train.py` (stage C): `GET /api/engines` lists
  `train` with the project's trains, saved and built; its parameters carry each default's origin;
  a run is one row at every door (the pureOS route, the tools, the engine's route), the same
  request twice that row, created by the request's person or the tool's caller; a value that waits
  keeps nothing and the worker's refusal is a receipt; values are converted by place and refused
  by place together, with the train's own refusals, in one set of words at both doors; a row keeps
  its outputs and its file's words, a worker's failure keeping no row; a train run replays
  identically; a train stands on a library run; `conform train --project` holds all eight checks
  in a project with a train, beside a person's run of it and past a draft and a train that waits,
  and with no project names the command in words; `pnpm ready` on the production database says
  where the checks run. With the `sim` marker, a real train's row, its outputs, the worker's words
  and its identical replay, and the worker's file step building nothing while the toolkit's
  schema requires a TEA year. `core/tests/test_engine_pins.py` holds the train's artifact id
  through the inputs. `pnpm prove` step 10 makes the eight checks on `train` in the proof's
  project.
