# H2-07: one run of a plant's default configuration is kept as two study scenarios

**Statement.** A study scenario made with no configuration and one naming the plant's default (cane, `S1`)
with the same values get two ids and run as one runs row, whose `scenarioId` names the first alone, and
the second scenario's `runIds` list it too.

**Contract.**

- `docs/api/studies.md:14`: "`id` | `ssc-` and the first twelve hex of the sha256 of the plant, the
  configuration and the values: the same values on the same plant are one scenario".
- The module says the same: `core/openferment_core/studies/scenarios.py:27-29`, "its id is `ssc-` and the
  first twelve hex of the sha256 of its plant, configuration and values, so the same values on the same
  plant are one scenario".
- `docs/api/studies.md:30-32` sets what "the configuration" is for a scenario made with none: "A plant that
  takes a configuration, made with none, is checked against its default's parameters
  (`engine/biosteam.py` `default_configuration`) and runs in its default, its `configuration` kept as
  made." The two scenarios are checked against the same parameters and run in the same configuration.
- `docs/api/runs.md:16` ("The same run asked twice is one row") and `docs/api/runs.md:28` (`scenarioId`,
  "The study scenario that asked for it first") hold as written; they are why the second scenario's run is
  a row that names the first scenario.

**Command.** `bash bughunt/repro/H2-07/run.sh` from the repository root. It makes the fresh database
`bh_r_h2_07_scenarios`, starts the service on the first free port in 9790 to 9799 (keyless, fixtures on),
makes a project, reads cane's `defaultConfiguration` from `GET /api/engines`, posts three scenarios with one
`person-assumption` value (`tea.IRR` 0.12): A with no configuration, B naming the default, and A's ask again
as a control. It runs A and B (`POST /api/studies/scenarios/{id}/run`), reads `GET /api/runs`,
`GET /api/studies/scenarios` and B, then calls `scenarios.scenario_id` (read only) on A's kept values with
the configuration its run resolved to. It stops the service and drops the database.

**Expected.** Asked with no configuration and asked naming `S1`, the same values on cane are one scenario:
one id, one scenario listed, and the run's `scenarioId` that scenario.

**Observed (run1.log, run2.log, both RESULT: DEFECT).**

- cane's default on the biosteam engine is `S1`.
- A is `ssc-05e8da8f647f` (configuration `None`), B is `ssc-d32a80c42165` (configuration `S1`), the same plant
  and the same kept values. A's ask made again answers `ssc-05e8da8f647f`, so an identical ask is one
  scenario.
- Both run as the one row `882cd0100f8b6ea0`, configuration `S1`, `scenarioId` `ssc-05e8da8f647f`, status
  `done`. `GET /api/runs` holds that one row.
- `GET /api/studies/scenarios` lists two scenarios, each with `runIds` `['882cd0100f8b6ea0']`; B lists a
  run whose `scenarioId` names A.
- `scenario_id` on A's kept values gives `ssc-05e8da8f647f` with the configuration as made and
  `ssc-d32a80c42165`, B's id, with `S1`, the configuration A was checked against and ran in.

**Likely cause.** `core/openferment_core/studies/scenarios.py:148`, `sid = scenario_id(asked.plant,
asked.configuration, values)`, hashes the configuration as made. `_checked`
(`core/openferment_core/studies/scenarios.py:83`) reads the parameters of
`biosteam.default_configuration(asked.plant, asked.configuration)` and the run resolves it the same way
(`core/openferment_core/engine/biosteam.py:188`, `cfg = default_configuration(thing, configuration)`). The
runs row keeps its first asker's scenario (`core/openferment_core/engine/runs.py:467`). A fix keys the id
on the resolved configuration and keeps the `configuration` field as made, as `docs/api/studies.md:32`
asks; `core/tests/test_studies.py:188-204` holds the field as made and runs in the default, so it stands
under that fix.
