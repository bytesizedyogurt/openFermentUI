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
- **fermOS** registers its families as the engine `kinetics` through the same group (stage C of
  alpha 2.2). Its integrators compute in the service process (`test_workers.py` allows SciPy in
  `kinetics.py` and `fermos.py`), so its `worker` is `None`, which the contract allows for an
  engine with nothing heavy to keep out of the service. Every trajectory stays bit for bit.
- **pureOS** registers `train` over `train_run` through `train_spec.py` (stage C), with the unit
  types and record ids it takes today.
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
