# H12-06: no test keeps biorefineries out of the service process

**Statement.** A function-level `import biorefineries` in `proforma.retired_entry_of`, a service module the run
readers, the Proforma tools and pureOS call, passes `test_workers.py`, `test_boundaries.py`, `test_proforma.py`,
`test_proforma_runs.py` and `test_engines.py`, and leaves biorefineries, BioSTEAM and thermosteam loaded in the
service's own process.

**Contract.**

- `CLAUDE.md:41`: "R: BioSTEAM, thermosteam, biorefineries, the vendored SFF toolkit and cobra run in worker
  processes (`core/openferment_core/workers/`), one JSON request a line; the service process imports none of them
  (§7.1; `core/tests/test_boundaries.py`)."
- `core/tests/test_boundaries.py:16-19`, the test the rule cites, hands the rule on: "BioSTEAM, thermosteam and
  biorefineries: the worker's side alone (workers/, flowsheets/, the vendored SFF toolkit and the pureOS functions
  that run in the worker; test_workers.py names each file)".
- `COMPONENTS.md:18-19` (generated from the package map) repeats it: "The rows the boundary test holds by other
  means (the worker's side by `test_workers.py`, ...)".

**Command.** From the repository root: `bash bughunt/repro/H12-06/run.sh` (exits 0 either way; makes its own
worktree of 2047f5a and its own databases `bh_r_h12_06_*`, and removes both).

What it does, in a worktree of 2047f5a with the repository's venv linked in:

1. reads, by `ast`, the libraries test_workers.py's grep holds (`ALLOWED`) and the packages test_boundaries.py
   holds from `SIMULATION` (`NEVER`);
2. a probe (`probe.py`) imports the service as uvicorn does (`openferment_core.api`), calls
   `proforma.retired_entry_of` on a kept reference run, and lists the worker libraries
   (`workers.WORKER_LIBRARIES`) then in `sys.modules`;
3. a control (`control.patch`): the same line in `retired_entry_of` imports biosteam, and
   `test_workers.py -k heavy_libraries` is run;
4. the plant (`mutation.patch`, the hunt's N09): the line imports biorefineries, and the five test files the
   candidate names are run (test_engines with `-k "not sigterm_ends_the_command"`, as the hunt ran it; conform's
   scratch prefix renamed in the worktree so its databases are `bh_r_h12_06_cf_*`);
5. the probe again on the planted tree.

**Expected.** A service module importing biorefineries fails a boundary test, as the control's `import biosteam` at
the same line fails test_workers.py's grep; the service process holds none of the worker libraries.

**Observed** (both runs, `run1.log` and `run2.log`).

- test_workers.py `ALLOWED`: `['biosteam', 'cobra', 'pisces_sff', 'scipy', 'thermosteam']`, biorefineries absent;
  test_boundaries.py `NEVER`: `['db', 'engine', 'literature', 'projects', 'studies']`, top-level modules absent.
- Head probe: the service imported and `retired_entry_of` called, worker libraries loaded `[]`.
- Control: `test_workers.py -k heavy_libraries` exit 1, "biosteam is imported outside its worker: ['proforma.py']".
- Plant: the five files exit 0 (RESULT_COUNTS); the planted probe lists RESULT_SEEN in the service process after
  `retired_entry_of`.

**Likely cause** (confidence high).

- `core/tests/test_workers.py:133-157`: `ALLOWED`, which drives the parametrized grep
  `test_heavy_libraries_are_imported_in_their_worker_alone` (`core/tests/test_workers.py:162-176`), has rows for
  cobra, biosteam, thermosteam, scipy and pisces_sff and none for biorefineries, so the grep never looks for it.
- `core/tests/test_boundaries.py:44-50`: `NEVER` holds `SIMULATION` (which names biorefineries) for `db/`,
  `projects/`, `literature/`, `engine/` and `studies/` alone, so a top-level service module (`proforma.py`,
  `api.py`, `composite.py`) or `pureos/` is held by neither file.
- `core/tests/test_boundaries.py:198-230` defers the core's own engines to "test_workers' grep", and the runtime
  subprocess checks (`test_workers.py:196-213`, `test_train.py:1092-1112`, `test_custom_train.py:382-395`) list
  `sys.modules` after paths that never reach `retired_entry_of`.

The fix is small: a `"biorefineries"` row in `ALLOWED` naming `workers/library_plants.py` (the one worker module
importing it at the top today), with `flowsheets/` skipped as biosteam's row skips it.

**Severity.** S3: a hollow guard on an R rule; the tree at 2047f5a imports no biorefineries in the service, and a
break would cost the service a cold BioSTEAM import (about 31 s) on a read path and the process isolation §7.1
asks for.
