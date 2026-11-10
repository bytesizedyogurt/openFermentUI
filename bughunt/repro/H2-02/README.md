# H2-02: a Proforma scenario run replays outside the exact precision its engine states once the service restarts

**Statement.** A `proforma.run` artifact of `ethanol_glucose_v0`, kept by a worker that built the corn stover
library plant before it built the scenario plant, replays identically in that worker and, after the service
restarts over the same database, with last-digit differences (relative 1e-16) in nine TEA and utility numbers,
so the replay answers `identical` false and `withinTolerance` false against the `rtol` 0, `atol` 0 the
biosteam engine states for the flowsheet.

## Contract

- `docs/api/engines.md:616-618`: "A scenario flowsheet's is `rtol` 0, `atol` 0: `proforma.run` registers no
  tolerance, so its replay holds every output identically."
- `docs/api/runs.md:229-231`: "A Proforma run registers no tolerance either: its replay is `identical` or names
  its differences, and the biosteam engine's scenario flowsheets state rtol 0, atol 0."
- `core/openferment_core/workers/proforma_worker.py:88-95`: "THE WARM WORKER KEEPS NO PLANT'S SETTINGS. [...]
  Every plant therefore builds inside `package_defaults()`, as it would in a worker that had built nothing
  before".
- `core/openferment_core/proforma.py:1517-1518` (`thing_list`): "proforma.run registers no replay tolerance, so
  each replays identically: its precision is rtol 0, atol 0."

## Command

    bash bughunt/repro/H2-02/run.sh

From the repository root. It makes the database `bh_r_h2_02_rep` fresh, starts the service on the first free
port in 9020 to 9029 (keyless, offline fixtures), makes a project, runs the corn stover library plant, runs an
unsaved scenario of `ethanol_glucose_v0` (six person-assumption inputs, 20 samples), replays the kept artifact,
stops and starts the service over the same database, replays it again and reads `GET /api/engines`. It stops
the service and drops the database at the end, and exits 0.

## Expected

The engine states `precision {rtol 0.0, atol 0.0}` for `ethanol_glucose_v0`, and the docs say the replay holds
every output identically, so both replays answer `identical` true (or the thing states the precision its
numbers keep, as a library thing states ten digits).

## Observed (run1.log and run2.log, the same both times)

- Replay in the worker that ran it: `identical` true, 0 differences.
- Replay after the service restarts: `identical` false, `withinTolerance` false, `tolerance` None, 9
  differences: `tea.FCI` 21777995.078954738 replayed 21777995.078954734, `tea.TCI`,
  `tea.installedEquipmentCost`, `tea.lines[2].perUnit`, `tea.lines[2].usdPerYear`, `tea.purchaseCost`,
  `tea.utilityCost`, `utilities.electricityConsumption`, `utilities.heating`, each a relative 1e-16 to 2e-16.
- `nightly_checks.replay_newest` counts such a replay a problem: "replays differently"
  (`core/openferment_core/nightly_checks.py:95`).

The worker's history decides it. Without the library run first, the same request keeps `tea.FCI`
21777995.078954734 (the fresh worker's digits) and replays identically after a restart. A run kept in a fresh
worker and replayed after a library run in that same worker also replays identically, because the worker keeps
the scenario plant it built (`_BUILT`). The stored digits move when the scenario plant is built after
another plant in the same worker.

## Likely cause

- `core/openferment_core/workers/proforma_worker.py:192-198`: the scenario plant is built inside
  `package_defaults()` "as it would be in a worker that had built nothing before", and the build still carries
  last-digit state from the corn stover plant the worker built first (BioSTEAM's summation order, which
  `core/openferment_core/engine/library.py:68-74` names as the reason a library run keeps `DIGITS = 10`).
- `core/openferment_core/proforma.py:808-809` registers `proforma.run` with no `tolerance_of`, and its output
  keeps every digit BioSTEAM gives; `core/openferment_core/proforma.py:1521` states
  `EnginePrecision(rtol=0.0, atol=0.0)` for every scenario flowsheet.

Confidence: high on the behaviour (reproduced twice from fresh databases); medium on which piece of the worker's
state carries over into the build.
