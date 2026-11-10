# H1-08: a configuration listed with spaces around its name can never be run or read

**Statement.** A contract engine's thing whose configurations are `["one", " two "]` passes the
service's shape check and is listed so by `GET /api/engines`, and every door (the run route, the
parameters route and the `engine_run` tool) strips the configuration a request names, then
refuses `'two'` as none of the thing's configurations, so `" two "` is never run and never read.

**Contract it breaks.**

- `docs/api/engines.md:231-232`: "`configurations`: the configurations it runs in, each name 1 to
  80 characters, or `[]` when it takes none." `" two "` is five characters, and the service's own
  shape (`core/openferment_core/models.py:4487`, `ConfigurationName`) accepts it.
- `docs/api/engines.md:242-248`: "a request naming none is refused in words; so is a configuration
  the thing does not name, and any configuration for a thing that takes none. The rule holds at
  every door: the run route, the parameters route and the engine tools". `" two "` is a name the
  thing gives, and all three doors refuse it.
- `docs/api/workers.md:62-68` lists the things answers that break the contract (`EngineBroken`,
  503 in words); a configuration name with spaces around it is none of them, so the listing
  rightly holds no error, and the thing stays listed in a configuration nothing can reach.

**Command** (from the repository root): `bash bughunt/repro/H1-08/run.sh`

The script registers the stand-in engine `h108` from `standin/` (written by hand for this
reproduction: one thing `cfg`, configurations `"one"` and `" two "`, default `"one"`) through a
dist-info it writes in a scratch directory put on `PYTHONPATH`. Nothing is installed into a venv
and nothing in `core/` is edited (`PYTHONDONTWRITEBYTECODE=1` keeps bytecode out too). It starts
the repository's own service keyless on 127.0.0.1:9760 over a fresh database `bh_r_h1_08_svc`,
makes a project, lists the engines, asks a run in `"one"` (the control), a run in `" two "` and in
`"two"`, the parameters in `" two "`, and `engine_run` in `" two "`; the stand-in worker logs each
`run` and `parameters` op it receives with its configuration. The script then stops the service,
drops the database and removes its scratch directory. One run takes about seven seconds.

**Expected.** Either the things answer naming `" two "` is refused as outside the shape (the
engine listed with that in words), or `" two "`, a name the thing lists, runs at
`POST /api/engines/h108/run`, is read at `GET /api/engines/h108/parameters` and runs through the
`engine_run` tool, the worker receiving `" two "`.

**Observed** (both runs, `run1.log` and `run2.log`):

- `GET /api/engines`: `h108: things=[('cfg', ['one', ' two '], 'one')] error=''`.
- Control, run in `"one"`: 200, a `done` run with `configuration: "one"`.
- Run in `" two "`: `422 {"detail":"cfg runs in one,  two ; 'two' is none of them"}`.
- Run in `"two"`: the same 422, so neither spelling reaches the configuration.
- Parameters in `" two "`: the same 422.
- `engine_run` in `" two "`: `error: engine_run refused: cfg runs in one,  two ; 'two' is none of them`.
- The worker received `[('parameters', 'one'), ('run', 'one')]` alone; the one runs row is the
  control's (`one:done`).

**Likely cause.** `core/openferment_core/engine/runs.py:797`,
`cfg = (configuration or "").strip() or found.defaultConfiguration`, strips the name a request
gives and then tests it against `found.configurations` as listed (`runs.py:801`), while
`core/openferment_core/models.py:4487`,
`ConfigurationName = Annotated[str, Field(min_length=1, max_length=CONFIGURATION_MAX)]`, holds a
thing's configuration names to a length alone, so a name with spaces around it (or of spaces
alone) passes the shape and can never equal a stripped request. The tool door strips once more
first (`core/openferment_core/tools/writes.py:478`, `configuration.strip() or None`). Either
`EngineThing` refuses a configuration name that differs from its stripped self (`EngineBroken`,
as a title of spaces alone is refused), or `thing_of` matches the name as given. Confidence high.

**Severity.** S3: an edge case with a workaround. No engine in the tree lists such a name
(biosteam's, kinetics' and train's names carry no surrounding spaces), and an engine author who
lists the name without them reaches it.
