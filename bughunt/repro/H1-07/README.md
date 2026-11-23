# H1-07: two things of one id are both listed, and a run of that id takes the last one's precision

**Statement.** A contract engine's worker whose `things` answer lists the id `dup` twice (the first
of precision rtol 0, atol 0, the second rtol 1, atol 1) is accepted: `GET /api/engines` lists both
with no word in `error`, and `POST /api/engines/{name}/run {"thing": "dup"}` keeps
`precision.rtol` 1 and `precision.atol` 1 in its basis, so the first thing listed can never be run
and a run of `dup` is held to the second thing's precision with no word said.

**Contract it breaks.**

- `docs/api/engines.md:229-230`: "`id`: starts with a letter or a digit, then letters, digits,
  `.`, `_` and `-`, at most 80 characters. A run names it as its `plant`." A run's `plant` picks
  one thing only while each id names one thing.
- `docs/api/engines.md:249-251`: "`precision`: how near a replay's numbers must come to the run's
  ... It enters each run's basis as `precision.rtol` and `precision.atol`." The listing shows two
  precisions for the one `plant` a run can name.
- `docs/api/workers.md:62-68`: "An answer outside the shapes below (... two outputs of one name,
  ...) breaks the contract: the service raises `EngineBroken`, keeps no runs row and answers 503
  in words." Names are held distinct among a run's outputs. The list names no rule for two things
  of one id, so this half of the claim rests on reading the id as what names a thing.

**Command** (from the repository root): `bash bughunt/repro/H1-07/run.sh`

The script registers the stand-in engine `h107` from `standin/` (its worker on the core's own
`workers.serve`, every value a placeholder) through a dist-info it writes in a scratch directory
put on `PYTHONPATH`. Nothing is installed into a venv and nothing in `core/` is edited. It starts
the repository's own service keyless on 127.0.0.1:9461 over a fresh database `bh_r_h1_07_svc`,
makes a project, lists the engines, asks a run of `dup` and a run of the control `single`, counts
the runs rows and greps the two readers of the listing. It then stops the service, drops the
database and removes its scratch directory. One run takes about six seconds.

**Expected.** A things answer listing two things of the id `dup` is refused as outside the
protocol (`EngineBroken`: `h107` listed with those words in `error`, a run answered 503 with no
runs row), or one thing of that id is listed and run.

**Observed** (run1.log and run2.log alike):

- `GET /api/engines`, h107's things: `dup` ('the first of two things of one id', precision 0, 0),
  `dup` ('the second of two things of one id', precision 1, 1), `single` (precision 0, 0);
  `error` empty.
- `POST /api/engines/h107/run {"thing": "dup"}`: 200, status `done`, run `1f2555fb673f9b79`, its
  basis `precision.rtol` 1.0 and `precision.atol` 1.0; one runs row kept.
- Control: `POST /api/engines/h107/run {"thing": "single"}`: 200, basis `precision.rtol` 0.0 and
  `precision.atol` 0.0, as listed.
- The two readers of one listing pick different things of the id: the service's
  `core/openferment_core/engine/runs.py:792` keeps the last (`{x.id: x for x in engine.things()}`),
  and Studies' run card `src/screens/ProformaStudies.tsx:275` finds the first
  (`things.find((t) => t.id === thingId)`), so the card shows the first thing and the service runs
  the second.

**Likely cause.**

- `core/openferment_core/engine/contract.py:161-167`: `WorkerEngine.things` keeps the answer as
  validated, thing by thing (`_listed`, `contract.py:135-144`), and checks no id against another.
  The same file's `_typed` (`contract.py:179-196`) holds a run's output names distinct.
- `core/openferment_core/engine/runs.py:792`: `thing_of` builds a dict by id, which keeps the last
  thing of each id; `run_engine` (`runs.py:842`, `853-856`) writes that thing's precision into the
  basis.

**Severity.** S3: it takes an engine whose worker answers two things of one id (an edge case), and
the engine's author has the workaround of distinct ids. No number from a record changes; one listed
thing cannot be run, and a run of the id is held to a precision the listing shows for the other
thing. A fix is small: `WorkerEngine.things` raising `EngineBroken` on a repeated id.
