# H1-09: an output carrying a stray number is accepted and kept in the run's artifact

**Statement.** A contract engine's `run` op that answers the output `{"name": "x", "value": 1.0, "unit": "u", "stray": 42}`
is accepted as in shape: the run is kept `done`, and its artifact keeps the stray number in its output, in its
output hash and in what its replay compares.

**Contract.**

- `docs/api/workers.md:62-68`: "An answer outside the shapes below (a result key missing, outputs that are no list
  of names, values and units, …) breaks the contract: the service raises `EngineBroken`, keeps no runs row and
  answers 503 in words."
- `docs/api/workers.md:93-94` and `docs/api/engines.md:456`: the `run` op's result is
  `{"outputs": [{"name", "value", "unit"}, …], …}`.
- `docs/api/engines.md:549`: "A worker answers each output's name, value and unit; the service keeps each as a
  typed quantity".
- `core/openferment_core/engine/contract.py:173-176` (the code's own docstring): "each a name, a finite number or a
  string, and a unit … any other shape breaks the contract (EngineBroken)."

**Command** (from the repository root): `bash bughunt/repro/H1-09/run.sh`

The script registers a stand-in engine `h109` (`standin/`, written by hand) through a dist-info on PYTHONPATH,
starts the repository's own service keyless on 127.0.0.1:10060 over a fresh database `bh_r_h1_09_svc`, and runs
two things:

- `nounit` (the control) answers `{"name": "x", "value": 1.0}`;
- `extra` answers `{"name": "x", "value": 1.0, "unit": "u", "stray": N}`, where N is 42 on the worker's first run
  of `extra` and 43 on its next run.

It then reads the artifact back, recomputes its hash with the service's own `artifacts.output_hash` over the
output as kept and with the `stray` key taken out, and replays the artifact. Finally it stops the service and drops
the database.

**Expected.** The output with a fourth key is refused as outside the shape (EngineBroken, 503, no runs row), or kept
as its name, value and unit alone, with no stray number in the artifact, its hash or its replay.

**Observed** (run1.log and run2.log, both `RESULT: DEFECT`):

- control: `nounit` → 503 "the h109 worker's run op answered an output that is no name, value and unit, outside
  the protocol", and no runs row is kept;
- `extra` → 200, run `done`, one runs row `extra:done`;
- the artifact keeps `output.values` `[{"name": "x", "value": 1.0, "unit": "u", "stray": 42}]`;
- the kept `outputHash` is `output_hash` of the output with the stray key in it (`91028a8d56cd4be9`). With the key
  taken out the hash is `09e61125e93b5153`;
- replay: `identical=False withinTolerance=False differences=[('values[0].stray', 42, 43)]`. The output's value
  `x = 1.0` is the same both times, and the replay fails over the stray number alone;
- the run's typed `outputs.values` (from `runs.values_of`) holds `x` with `value`, `unit` and `origin` alone, so the
  stray number lives in the artifact, its hash and its replay.

**Likely cause.** `core/openferment_core/engine/contract.py:172-197`: `_typed` checks only that `name`, `value` and
`unit` are present and well typed, and then returns `items` whole (`return items`, line 197) with every other key
still in it. `core/openferment_core/engine/runs.py:647` keeps that list as the artifact's `values`, and
`core/openferment_core/artifacts.py:151-152` (`output_hash`) and `artifacts.py:367-402` (`_diff`, `_within`) hash
and compare it whole. One fix is for `_typed` to refuse a key beyond the three. Another is for it to return
`{"name", "value", "unit"}` alone. The same `_typed` reads diagnostics, so a stray key on a diagnostic is kept on the
run's row too (this reproduction does not exercise that path).

**Severity.** S4: a laxer shape check than the documented contract. The stray number never reaches the run's typed
outputs, so no reader of `outputs.values` shows it. It shows only in the artifact's raw output and in a replay that
fails over it.
