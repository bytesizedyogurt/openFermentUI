# H2-01: one comparison row holds values in two units, its change reckoned across them

**Statement.** A comparison row labels every run's value of a name with the first run's unit, whatever
unit each run's `outputs.values` states, and reckons each run's relative change from the raw numbers,
so one product titre forecast once in g L-1 and once in mg L-1 shows a change of +99,899.98 %.

**Contract.** `docs/api/studies.md:140`, the comparison artifact's `rows`:

> `[{key, unit, values, change}]`: every output any run answers, each run's value (null for a run with
> no output of that key), and its relative change from the first run's. [...] a run of any other
> engine's are its outputs.values (`values.<name>`, each in its unit; `docs/api/runs.md`, Outputs)

and `docs/api/runs.md:23`, which those outputs point to: "each output as `{name, quantity}`, the
quantity in the unit the run's artifact states". The row has one `unit` field, so a value stands in
its own unit only when the row's unit is that value's unit; the relative change is a change of the
quantity, and the same titre in two units is a change of 0.

**Command** (from the repository root):

    bash bughunt/repro/H2-01/run.sh

It makes the database `bh_r_h2_01_cmp` fresh, starts the service keyless on the first free port of
9600 to 9609 (the proof's offline mode), makes one project, fits the same logistic readings twice
(`POST /api/fermos/fit`, the product series in g L-1, then the same numbers times 1000 in mg L-1),
forecasts each fit (`POST /api/fermos/forecast`), reads both runs (`GET /api/runs/{id}`), compares
the two forecast runs (`POST /api/studies/comparisons`), reads the export's `study.md`, prints
EXPECTED, OBSERVED and RESULT, and stops the service, drops the database and removes its scratch
files. About six seconds.

**Expected.** The row `values.finals.product` keeps each run's value in its own unit (a row a unit),
or holds both to one unit before the change: run 2's 19533.85 mg L-1 is 19.5338 g L-1, a change of
0 from run 1's 19.5338 g L-1.

**Observed** (both runs, `run1.log` and `run2.log`):

    GET /api/runs/77b2c4bb17cb986b: finals.product = 19.533849398401337 g L-1
    GET /api/runs/e123b1d660888267: finals.product = 19533.8458971344 mg L-1
    export study.md: | values.finals.product | g L-1 | 19.5338494 | 19533.8459 | +99899.98% |
    comparison row: key values.finals.product  unit 'g L-1'  values [19.533849398401337, 19533.8458971344]  change [0.0, 998.9998207589879]
    RESULT: DEFECT

The kept comparison artifact and the export's `study.md` table both state
run 2's milligram value under g L-1 and its change as +998.9998 (+99,899.98 %).

**Likely cause.** `core/openferment_core/studies/comparisons.py:135` takes the row's unit as the first
non-null unit of the runs (`unit = next((u for u in units if u is not None), None)`) and drops the
other runs' units, and `comparisons.py:137` reckons `_change(v, values[0])` over the raw values;
`_change` (`comparisons.py:74-77`) takes two numbers and no unit. `core/openferment_core/studies/exports.py:315`
prints the row's one unit and those changes into `study.md`. The repository's units engine
(`units.normalize`, used by `core/openferment_core/fermos.py:798-799`) could tell the two units apart
or hold them to one before the change.

**Severity.** S1: a wrong number shown as sound (a change of +99,899.98 % for one quantity, and a
milligram value labelled g L-1), carried into the kept artifact and the export.
