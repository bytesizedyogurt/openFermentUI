# H1-06: a thing stating an infinite precision is listed with atol null and its run answers 500

**Statement.** A contract engine's worker whose `things` answer gives a thing the precision
`{"rtol": 0, "atol": Infinity}` passes the service's shape check: `GET /api/engines` lists that
atol as `null` against the schema's `number`, and `POST /api/engines/{name}/run` for the thing
answers a plain-text `500 Internal Server Error` from a `ValueError` raised in `json.dumps`.

**Contract it breaks.**

- `docs/api/workers.md:62-68`: "An answer outside the shapes below (... a number that is NaN or
  infinite, ...) breaks the contract: the service raises `EngineBroken`, keeps no runs row and
  answers 503 in words."
- `docs/api/engines.md:517-520`: "What the two routes answer beside their result, each in words
  ...: ... 503 for an engine that cannot be used, a worker that cannot answer, or a worker that
  answers outside the protocol, with no run kept."
- `docs/api/openapi.json`, `EnginePrecision.atol`: `"type": "number", "minimum": 0.0`; JSON's
  numbers hold no infinity.

**Command** (from the repository root): `bash bughunt/repro/H1-06/run.sh`

The script registers two stand-in engines from `standin/` (`h106` and the control `h106neg`)
through a dist-info it writes in a scratch directory put on `PYTHONPATH`. Nothing is installed
into a venv and nothing in `core/` is edited. It starts the repository's own service keyless on
127.0.0.1:9660 over a fresh database `bh_r_h1_06_svc`, makes a project, lists the engines, asks
three runs, counts the runs rows and reads the service log. It then stops the service, drops the
database and removes its scratch directory. One run takes about six seconds.

**Expected.** The things answer of `h106`, which holds an infinite atol, is refused as outside
the protocol (`EngineBroken`): `h106` is listed with those words in `error`, as the control
`h106neg` is for its atol of -1, and `POST /api/engines/h106/run` answers 503 in words with no
runs row kept.

**Observed** (run1.log and run2.log alike):

- `GET /api/engines`: `h106: things=[('fine', {'rtol': 0.0, 'atol': 0.0}), ('infprec', {'rtol': 0.0, 'atol': None})] error=''`.
- `POST /api/engines/h106/run {"thing": "infprec"}`: `500 text/plain; charset=utf-8 Internal Server Error`.
  No runs row is kept. The service log ends in `ValueError: Out of range float values are not
  JSON compliant: inf`, raised at `openferment_core/artifacts.py` line 148 (`artifact_id`) and
  line 130 (`canonical`).
- Control, the same engine: `POST /api/engines/h106/run {"thing": "fine"}` answers 200 with a run.
- Control, the shape check working: `h106neg` (atol -1) is listed with `EngineBroken: ... precision.atol:
  Input should be greater than or equal to 0`, and its run answers
  `503 {"detail": "the h106neg worker's things op answered things outside their shape: ..."}`.

**Likely cause.**

- `core/openferment_core/models.py:4504-4509`: `EnginePrecision` declares `rtol` and `atol` as
  `float = Field(ge=0)`, and pydantic's float admits `inf` (infinity is `>= 0`). The worker
  protocol reads `Infinity` and `1e999` as `inf` (`json.loads` at
  `core/openferment_core/workers/__init__.py:215`), and `WorkerEngine._listed`
  (`core/openferment_core/engine/contract.py:135-144`) holds the things to the model's bounds alone.
  `WorkerEngine._typed` (`contract.py:185-186`) holds a run's outputs to the finite check that the
  things answer lacks.
- `core/openferment_core/engine/runs.py:853-865`: `run_engine` puts `precision.atol` into the run's
  basis and calls `artifacts.artifact_id`, whose `canonical`
  (`core/openferment_core/artifacts.py:128-130`) dumps with `allow_nan=False` and raises
  `ValueError`. `engine_run` (`core/openferment_core/api.py:1410-1424`) maps `EngineRefused`,
  `EngineBroken` and the worker errors, so the `ValueError` reaches the server as a 500.
- The listing serializes the kept `inf` through pydantic's JSON mode, which writes it as `null`.

**Severity.** S3: a misbehaving third-party worker (one that writes its JSON lines by hand, since
`workers.serve` dumps with `allow_nan=False`) meets a plain 500 and a listing that shows `null`
for a number. No run is kept and no number reaches a record; a fix in `EnginePrecision`
(`allow_inf_nan=False`, or a finite check beside `ge=0`) is small.
