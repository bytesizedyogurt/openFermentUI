# H1-03: the documented conform command for a scenario flowsheet stops with ProjectRequired

**Statement.** `python -m openferment_core.engine.conform biosteam --thing ethanol_glucose_v0 --inputs <file>`
stops with `ProjectRequired: This names no project` and keeps no verdict, with every value the flowsheet waits
for set in the file and with none set; the same command with `OPENFERMENT_PROJECT` set to any id makes the
eight checks and keeps the verdict.

## The contract it breaks

- `docs/api/engines.md:660-664`: "A scenario flowsheet's inputs wait in a project that holds no record, so a
  check that names one sets its values with `--inputs`, a JSON list of `EngineInput`s, each a person's
  assumption in its parameter's unit".
- `docs/api/engines.md:670-672`: "`python -m openferment_core.engine.conform biosteam --thing ethanol_glucose_v0
  --inputs <file>`. Named with a value it waits for left unset, the thing cannot run as it stands (the engine's
  `unready`), and the command refuses it in words before anything is made, keeping no verdict."
- `docs/BASE.md:44-45`: "`biosteam --thing <a scenario flowsheet> --inputs <file>`, the values a scenario
  flowsheet waits for".
- `core/openferment_core/engine/conform.py:19`: the checks "run in a project made for them, so nothing a person
  keeps is touched". No document asks for `OPENFERMENT_PROJECT` here: `core/.env.example:18-23` lists the
  commands that read it, and conform is absent from that list.

## Command

```
bash bughunt/repro/H1-03/run.sh
```

From the repository root. It makes a fresh database `bh_r_h1_03_verdict` for the verdict and a private copy of
the data caches, runs the head's own venv keyless with every proxy variable on a closed port, and drops both at
the end. The command under test makes and drops its own scratch database (`openferment_conform_*`), as it always
does. About 20 s.

## Expected

- A, the documented command with a file setting all six values (`feed_glucose_conc`, `titre`, `yield`,
  `productivity`, `plant_scale`, `glucose_price`): the eight check rows printed and one `engine_checks` row kept
  for `biosteam`.
- B, the documented command with no file: a refusal in words naming the six values that wait, nothing kept.

## Observed (run1.log, run2.log)

- A: `✗ the checks could not be made on biosteam: openferment_core.projects.ProjectRequired: This names no
  project. A request sends the X-OpenFerment-Project header (or ?project= on an event stream); a command sets
  OPENFERMENT_PROJECT.`, exit 1, one row printed, 0 verdict rows kept.
- B: the same `ProjectRequired` words, exit 1.
- C, the control, B with `OPENFERMENT_PROJECT=any-id` (an id no database holds): the documented words,
  `ethanol_glucose_v0 waits for 6 values its parameters give no default, which a run sets: feed_glucose_conc,
  glucose_price, plant_scale, productivity, titre, yield; set its values with --inputs <file>`.
- `control-with-project.log`, made once by hand: A with `OPENFERMENT_PROJECT=any-id` ran all eight checks in
  52 s (seven held, check 4 failed on replay) and kept the verdict row (`biosteam|f`). So the project is the
  one thing missing.

## Likely cause

`core/openferment_core/engine/conform.py:1048-1050`: `_inside` asks the engine's `unready(first[0], values)`
before it makes the checks' own project and enters it at `conform.py:1054-1055`
(`projects.create(...)`, `with projects.using(made.id):`). For a scenario flowsheet,
`BiosteamEngine.unready` (`core/openferment_core/engine/biosteam.py:284-305`) reads the thing's parameters at
`biosteam.py:296`, and the Proforma provider reads the project's kept scenarios on the way
(`params.py:698` `proforma.held_scenarios()` > `proforma.py:1097` > `project_state.py:458`
`projects.current()`), which raises `ProjectRequired` with no project entered. The frames, as run.sh prints them:

```
engine/biosteam.py:296 unready > engine/biosteam.py:259 parameters > openferment_core/proforma.py:1490 thing_parameters
> openferment_core/params.py:262 scope > openferment_core/params.py:244 _provided > openferment_core/params.py:698 _proforma
> openferment_core/proforma.py:1097 held_scenarios > openferment_core/project_state.py:458 kept > projects/__init__.py:58 current
```

A library plant's `unready` returns before it reads anything (`biosteam.py:291-292`), so `conform biosteam` with no
`--thing` (the proof's step 10) never reaches this path, and no test or proof step runs the documented
scenario-flowsheet form. Moving the `unready` question inside `projects.using(made.id)`, after the project is
made, is the small fix; the documented refusal then still comes before any check runs.
