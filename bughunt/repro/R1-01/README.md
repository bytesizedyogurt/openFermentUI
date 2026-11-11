# R1-01: a Departures row names `GET /api/artifacts`, a route the service does not serve

**Statement.** The alpha 2.2 D8 departure row in `docs/PROGRESS.md` says the reference screen reads the project's kept reference runs at `GET /api/artifacts`; the service serves no such route (the schema, the app's route table and a live request agree), and the screen reads `GET /api/biorepo/artifacts?tool=`.

**Contract it breaks.** `docs/PROGRESS.md:483`, the row on retiring `/api/proforma/benchmark` and `/api/proforma/reference/{id}`:

> the reference screen reads the library plant's runs (`GET /api/runs?engine=biosteam`) and the project's kept reference runs (`GET /api/artifacts`)

The record's own rule for routes is that `docs/api/openapi.json` is generated from the service and names every operation (CLAUDE.md, Communication contracts: "REST: FastAPI routes in `core/openferment_core/api.py`; `docs/api/openapi.json` is generated"). That schema and `api.py` hold `/api/biorepo/artifacts` and its four sub-paths, and no `/api/artifacts`.

**Command.** From the repository root: `bash bughunt/repro/R1-01/run.sh`

It reads the row, the generated schema, the app's live route table (`openferment_core.api:app.routes`, which counts routes outside the schema too), `api.py`'s decorators and the client's call. Then it starts the head's service on a fresh database `bh_r_r1_01_svc` on port 10930, makes a project and asks both paths. It stops the service and drops the database on exit.

**Expected.** The row names the route the screen reads: `GET /api/biorepo/artifacts?tool=` (`src/lib/proforma.ts:169-171`, `keptReferenceRuns`, called at `src/screens/ProformaReference.tsx:283`; the screen's header comment at `src/screens/ProformaReference.tsx:20` names it too).

**Observed** (run1.log, run2.log). The row names `GET /api/artifacts`. `openapi.json` and the app's 129 routes hold `/api/biorepo/artifacts` (with `/{artifact_id}`, `/checks`, `/replay`, `/tables`) and no `/api/artifacts`. No `api.py` decorator and no client file names `/api/artifacts`. Live, `GET /api/artifacts` answers 404, and `GET /api/biorepo/artifacts?tool=proforma.reference&tool=proforma_benchmark` answers 200.

**Likely cause.** The row was written at C.6 (`git log -S'(\`GET /api/artifacts\`)' -- docs/PROGRESS.md` names `f5405f8`) and the route was shortened in the prose. At `f5405f8` the schema already held `/api/biorepo/artifacts` alone. No check holds `docs/PROGRESS.md`'s route names to the schema. Location: `docs/PROGRESS.md:483`. Fix: one word, `GET /api/biorepo/artifacts?tool=`.

**Correction to the candidate.** The candidate gives `src/lib/artifacts.ts:67` (`listArtifacts`) as the screen's call. The reference screen calls `keptReferenceRuns` in `src/lib/proforma.ts:170-171`, which asks `/api/biorepo/artifacts?tool=proforma.reference&tool=proforma_benchmark`. Both name the same path, so the finding stands.

**Severity.** S4, drift in a record; the service and the screen behave correctly.
