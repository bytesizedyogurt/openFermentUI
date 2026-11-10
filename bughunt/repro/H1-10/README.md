# H1-10: GET /api/engines says the Proforma worker is ready after it died

**Statement.** Once the Proforma worker has answered, `GET /api/engines` lists the `workerStatus`
of `biosteam` and `train` as `ready` whatever becomes of the process: after the worker is killed no
Proforma worker lives and both still read `ready` (`GET /api/proforma/status` says `ready` too),
where a `WorkerEngine` whose worker died reads `cold`.

**Contract it breaks.**

- `core/openferment_core/engine/contract.py:104-106`, `WorkerEngine.status`: "`ready` while the
  worker's process answers, `cold` before its first use", computed from `self._sim.alive`. This is
  the meaning the same field carries for every contract engine built on `WorkerEngine`.
- `core/openferment_core/engine/simulator.py:7-8`, the simulator the two engines read: "`status()`
  says where it is: `cold`, `starting`, `ready` or `failed`".
- `core/openferment_core/engine/registry.py:246`, `status_of`, which fills the listing's field:
  "The engine's worker: `ready`, `cold`, `starting`, `failed`, or `none` for an engine with no
  worker."
- `core/openferment_core/api.py:919`, `GET /api/proforma/status`: "Where the BioSTEAM worker is
  (§8.1): cold, starting, ready or failed."
- `docs/api/engines.md:504-505`: `GET /api/engines` lists each engine's "`worker` and
  `workerStatus`".

**Command** (from the repository root): `bash bughunt/repro/H1-10/run.sh`

The script starts the repository's own service (core/ at 2047f5a, read and run, never edited)
keyless on 127.0.0.1:10360 over a fresh database `bh_r_h1_10_svc`, with
`OPENFERMENT_WARM_PROFORMA=1` so the service starts the Proforma worker itself with one ping and
builds no plant. It waits for `GET /api/proforma/status` to read `ready`, counts the live Proforma
workers under the service and reads `GET /api/engines`, sends SIGKILL to the worker, then counts
the workers again and reads `GET /api/engines` and `GET /api/proforma/status`, and counts once more
to show the reads start no worker. The control is a `WorkerEngine` over the tree's echo worker,
read through `registry.status_of` as the listing reads it, before its first use, after an answer
and after its worker is killed. The script stops the service, drops the database and removes its
scratch directory. One run takes about 23 seconds.

**Expected.** With no Proforma worker alive, `biosteam` and `train` read `cold` (or `failed`), as
the `WorkerEngine` control reads `cold` once its worker is killed.

**Observed** (run1.log and run2.log alike):

- Before the kill: 1 Proforma worker alive; `biosteam=ready train=ready`.
- After the kill: 0 alive; `GET /api/engines` lists `biosteam=ready train=ready`;
  `GET /api/proforma/status` answers `ready`; 0 alive after both reads.
- Control: `before first use=cold after an answer=ready after its worker was killed=cold`.
- `RESULT: DEFECT` in both runs.

**Likely cause** (high confidence).

- `core/openferment_core/engine/simulator.py:43-44`: `status()` answers `dict(_STATE)`, the last
  state kept, and nothing reads `worker().alive`. `_STATE` becomes `ready` in `_warm` (line 50) and
  no path sets it back: `call` (line 87) passes `worker().call` through and keeps the state as it
  was, even when that call raises `WorkerCrashed`.
- `core/openferment_core/engine/biosteam.py:228-230` and `core/openferment_core/pureos/engine.py:222-224`
  read that kept state as the engine's `status`.
- `core/openferment_core/workers/__init__.py:186-189`: the next call restarts a dead worker in
  silence (a cold BioSTEAM import, 15 s here), and the status reads `ready` through that start, the
  very wait `starting` exists to show.
