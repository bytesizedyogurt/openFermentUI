# H1-05: the biosteam engine builds, and keeps a receipt for, a configuration its listing omits

**Statement.** `GET /api/engines` lists `cellulosic_ethanol_v0` in the four configurations it built in
here; `POST /api/engines/biosteam/run` builds it in `AFEX, IB`, a fifth the listing omits, and keeps a
refused `runs` row for it, and `GET /api/engines/biosteam/parameters` builds it in `AFEX, IB` too.

**Contract.**

- `docs/api/engines.md:242-248`: "a request naming none is refused in words; so is a configuration the
  thing does not name, and any configuration for a thing that takes none. The rule holds at every door:
  the run route, the parameters route and the engine tools, so the worker's `parameters` op receives the
  configuration a run would use. BioSTEAM's library plants follow it at their own doors too".
- `docs/api/engines.md:611`, the biosteam thing's configurations: "those it built in here".

The thing the run and parameters routes act on is the engine's `EngineThing`, whose `configurations`
the listing serves; for `cellulosic_ethanol_v0` that is `dilute acid, IB`, `dilute acid, SCF`,
`hot water, IB`, `hot water, SCF`.

**Command** (from the repository root): `bash bughunt/repro/H1-05/run.sh`

It makes a fresh test database `bh_r_h1_05_svc`, starts the head's service keyless on a port of
9360-9369, makes a project, reads `GET /api/engines`, sends a control run naming `dilute acid, SSCF`,
then a run and a parameters read naming `AFEX, IB`, then a run of `lactic`, and lists `GET /api/runs`.
It stops the service and drops the database on exit.

**Expected.** A run and a parameters read naming `AFEX, IB` are each a 422 naming the four listed
configurations, said before anything is built, and the run keeps no row.

**Observed** (`run1.log`, `run2.log`, the same in both):

- The listing: `['dilute acid, IB', 'dilute acid, SCF', 'hot water, IB', 'hot water, SCF']`.
- The run route: HTTP 422 after 16 to 19 s on a cold worker, in BioSTEAM's words from a build
  ("cellulosic_ethanol_v0 AFEX, IB is infeasible here (BioSTEAM's InfeasibleRegion): <Mixer: M207>
  conversion of 'NH3' is over 100%"), and a refused row `a9c4e1880088113d` kept with configuration
  `AFEX, IB`.
- The parameters route: HTTP 422 in the same BioSTEAM words, its worker building the plant again.
- The control `dilute acid, SSCF` is refused before any build, in words naming the shelf's eight
  configurations (`AFEX, IB`, `AFEX, SCF`, `alkaline, IB` and `alkaline, SCF` among them), which shows the
  door holds a configuration to the shelf's list of every configuration the package names.

Beside it, outside the verdict: a run of `lactic`, which the listing omits, builds, is refused in the
library's words ("biorefineries.lactic could not be built under biosteam 2.54.0: IndexError") and keeps
the refused row `eaf032f1c7918eaa`. `docs/api/engines.md:639-643` makes the shelf the test for a thing at
these doors ("A thing neither on the library's shelf nor provided is refused in words naming every
thing the engine runs ... A plant on the library's shelf that runs nothing (a subsystem) is refused in
the library's own words"), and `lactic` is on the shelf, so this half meets the contract's letter.

**Likely cause.**

- `core/openferment_core/engine/biosteam.py:160` `default_configuration` passes any configuration a
  request names; the engine's `run` (`biosteam.py:277`) and `parameters` (`biosteam.py:265`) hand it to
  `run_plant` and `_library_parameters` unchecked against the engine's own thing.
- `core/openferment_core/engine/library.py:121` (`_runnable`) checks a configuration against
  `p.configurations`, the shelf's list of every configuration the package names, eight for this
  flowsheet; the engine's thing lists the four it built in (`biosteam.py:129-130`).
- `core/openferment_core/engine/runs.py:784` `thing_of` holds the listing's rule, and `runs.py:814` and
  `runs.py:916` apply it to contract engines alone (`is_contract`, `runs.py:778`); the biosteam engine
  is not one, so its doors take the library's check.

`core/tests/test_runs_sim.py:74-78` keeps an `AFEX, IB` receipt through `runs.run`, the library's own
path; a grep of `core/tests` finds no test holding the engine's run or parameters route to the listing's
configurations.

**Severity** S3: an edge case reached by naming a configuration the listing does not offer; the answer is a 422 in true words, and a refused row is kept.
