# H1: the engine contract

Hunt H1 at 2047f5a. Sources read: docs/api/engines.md whole, docs/api/workers.md (Lines, Engine ops),
docs/api/runs.md, docs/BASE.md, the engine package, the workers package, fermos_engine.py,
pureos/engine.py, tools/engine.py, the engine routes in api.py, and the mirror under examples/.
Everything ran keyless on bh_h1_* databases, ports 8810-8815, from a worktree of H1's own at
2047f5a (removed at the end) or the head's own service. No file under core/, src/, scripts/ or
examples/ was touched; every database and service H1 made is gone.

## What was run

- **Conformance.** `conform` on mirror, biosteam, kinetics (`--inputs` from
  `write_placeholder_inputs`), train (`--project h1a`, a train made through from-run, check and
  `PUT /api/state/trains`), and the stand-in engine `probe`. Every refusal path of the command and
  its exit code. The four core and example engines hold all eight checks as documented.
- **A stand-in engine package** (`scripts/probe-engine`, installed only into H1's worktree venv):
  a worker written by hand that misbehaves one way a thing (no-JSON line, another request's id,
  silence, exit mid-run, a 10 MB line, JSON NaN, a stray field, infinite precision, duplicate
  things, a configuration with spaces, a flowsheet that is a list, a nondeterministic output, a
  slow run), and eleven entry points that fail to load, misname themselves, lack `replay`,
  claim `mirror` or `biosteam`, import cobra, call `sys.exit`, or ask the registry while
  imported.
- **Doors.** About sixty malformed and boundary bodies at `POST /api/engines/{name}/run`, the
  parameters route and the four engine tools (`scripts/doors.py`, `scripts/core_doors.py`).
- **Concurrency.** The same request four at once with different askers (mirror and kinetics);
  eight different requests at once.
- **Worker kills.** SIGKILL of the probe worker and of the Proforma worker while a run was in
  flight, then the answer, the rows and the next ask.
- **Lifecycle.** A version raised and reinstalled; the engine uninstalled; `pnpm ready --offline`
  rows; `check-licences` with the mirror installed.

## What held

The run id recomputes from the page's formula with no openFerment code. Every malformed request
was refused in words before the worker, and nothing was kept. Worker garbage answered 503 in
words with no row, and the next ask restarted the worker. A kill mid-run answered 503 and the
next ask computed. Discovery listed every broken entry point with its words and the service ran
on. Projects stayed apart. Replays named a moved version first. The audit rows of `engine_run`
read as the page says. The worker's environment held back every name `workers.withheld` covers.

## What broke

- **H1-01 (S2).** Identical requests at once: one row, its `created_by` the first insert's and its
  body `by` the last writer's; every asker told the run is its own. `keep_run` reads, then
  upserts. Seen on mirror and kinetics; the library and train paths share the code.
- **H1-02 (S3).** An entry module set aside for its name or a failed import leaves cobra in the
  service, and a later engine importing cobra loads with no word.
- **H1-03 (S2).** `conform biosteam --thing ethanol_glucose_v0 --inputs <file>`, the page's own
  command, stops with `ProjectRequired`; `_inside` asks `unready` before entering a project.
  Setting `OPENFERMENT_PROJECT` to any id lets it run.
- **H1-04 (S1).** Found through H1-03's workaround: a scenario flowsheet's first case after the
  worker builds it prices at 6.36 USD/kg, every later case of the same inputs at 7.37. A run
  with fixed values keeps both (base 6.36, every quantile 7.37), and its replay differs in 51
  places where the stated precision is exact. The flowsheet's comment says a case gives one
  answer whatever came first. Overlaps the Proforma hunt; reported here because engines.md
  states the replay holds identically and check 4 fails.
- **H1-05 (S3).** The biosteam doors build and keep receipts for a configuration and a plant the
  listing omits (`cellulosic_ethanol_v0` 'AFEX, IB', `lactic`).
- **H1-06 (S3).** An infinite precision in a things answer: listing serves `atol: null`, a run
  answers a plain 500.
- **H1-07, H1-08, H1-09, H1-10 (S4).** Two things of one id (the last one's precision used); a
  configuration listed with spaces that no door can reach; an output's stray number kept in the
  artifact; biosteam and train read `ready` with no Proforma worker alive.

## Scripts (all under bughunt/notes/H1/scripts/)

- `wt_env.sh`: H1's worktree helpers (`wt_svc_start`, `wt_conform`, `j`).
- `repro_h1_01.sh`, `repro_h1_03.sh`, `repro_h1_04.sh`, `repro_h1_09.sh`,
  `repro_h1_scenario_path.sh` (H1-04): each on the head's own service or venv and a fresh
  database, dropped after. Run `repro_h1_03.sh` before `repro_h1_scenario_path.sh` (it writes the
  inputs file).
- `repro_probe.sh [WORKTREE]`: H1-02, H1-05 to H1-09's stand-in findings; makes a worktree at
  2047f5a when none is named, installs `probe-engine` there, and removes what it made.
- `concurrent_same.py`, `concurrent_kinetics.py`, `concurrent_different.py`, `kill_midrun.sh`,
  `kill_proforma.sh`, `probe_things.sh`, `doors.py`, `core_doors.py`, `heavy_left.py`,
  `make_train.py`, `id_check.py`: the probes behind the findings and the held list.
- `probe-engine/`: the stand-in package. Its pyproject still claims `mirror` and `biosteam` (the
  duplicate-name probe); `repro_probe.sh` comments those two lines out in its own copy.

## Left

A run that sets a deposition's reading through a contract engine (needs a confirmed deposition);
a contract engine that answers a valid SFF document; `pnpm prove` steps 9 and 10; the science of
the Proforma, library, geneOS and SFF worker ops; the record-reader agent (read and left unrun).
