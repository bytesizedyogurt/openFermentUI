# H5-05: a forecast of a fit the project does not hold answers HTTP 500

**Statement.** `POST /api/fermos/forecast` naming a `fitArtifactId` the acting project does not hold (an unknown
id, or another project's kept fit) raises `artifacts.ArtifactNotFound` unhandled, and the service answers
`500 Internal Server Error` with no words; the tool door `growth_forecast` refuses with the bare quoted id.

**Contract.**
- `core/openferment_core/api.py:208` (and `docs/api/openapi.json` `info.description`, line 18173):
  "A refusal is a status with its reason in `detail`, in words."
- `CLAUDE.md:87`: "a refusal is a 422 in words."
- `core/openferment_core/api.py:731-733`, the route's own docstring: "A refusal says which parameter the run did
  not identify, and what run would, or why a value set cannot stand."
- `core/openferment_core/fermos.py:928` holds the intended words, "there is no kept fit {fit_artifact}", which
  never reach the caller.

**Command** (from the repository root):

    bash bughunt/repro/H5-05/run.sh

It makes a fresh database `bh_r_h5_05_forecast`, starts a keyless service on the first free port of
127.0.0.1:10310-10319, makes two projects, keeps one kinetic fit in the first from a synthetic batch generated in
`forecast.py`, then asks the forecast door three ways and searches the service log. It stops the service, drops
the database and removes the data copy.

**Expected.** Each forecast of a fit the acting project does not hold answers a 404 or 422 whose `detail` names
the fit in words ("there is no kept fit 0123456789abcdef"), as the forecast scope's own read
`GET /api/params/fermos:forecast:<id>` does (404, "there is no kept kinetic fit 0123456789abcdef: fermOS keeps a
fit when it fits a deposited run"). The tool door refuses in the same words.

**Observed** (run1.log and run2.log, the same in both):
- `POST /api/fermos/forecast` in `h505-a`, `fitArtifactId` `0123456789abcdef`: `500 Internal Server Error`.
- `POST /api/fermos/forecast` in `h505-b`, naming `h505-a`'s own kept fit: `500 Internal Server Error`. Project
  scoping holds (B reads nothing of A's), and the refusal arrives as a crash.
- `POST /api/tools/growth_forecast` in `h505-a` with the unknown id: `error` is
  `growth_forecast refused: '0123456789abcdef'`, the `KeyError`'s quoted id and nothing more.
- Control: the same route in `h505-a` with its own fit answers 200 with a kept forecast.
- The service log shows `openferment_core.artifacts.ArtifactNotFound` raised from `fermos.py`, line 926, in
  `forecast_run`, through `api.py`, line 735, in `fermos_forecast`, once for each 500.
- After a 500 the server drops the kept-alive connection, so a client reusing it sees a connection reset on its
  next request (the first draft of `forecast.py` met this; the script now opens one connection a request).

**Likely cause** (high confidence).
- `core/openferment_core/fermos.py:927`: `except FileNotFoundError as e:` around `artifacts.get(fit_artifact)`.
  `artifacts.get` raises `ArtifactNotFound`, a `KeyError` (`core/openferment_core/artifacts.py:54`), so the
  `FitRefused` with the intended words is never raised. The file store this guard was written for is gone
  (ADR-010); the sibling `_fit_art` at `fermos.py:1704-1711` catches `ArtifactNotFound` and `ArtifactDamaged`.
- `core/openferment_core/api.py:737` catches `fermos.FitRefused` alone, so the `KeyError` reaches the server as a
  500.
- `core/openferment_core/tools/writes.py:341` catches `ArtifactNotFound` itself and formats it with `str(e)`,
  which for a `KeyError` is the quoted id alone.
- A damaged fit row (`ArtifactDamaged`, a `ValueError`) takes the same path to a 500 by reading of the code; this
  reproduction does not exercise it.

Fix size: small (catch `artifacts.ArtifactNotFound` and `artifacts.ArtifactDamaged` at `fermos.py:927`).
Severity S3: an edge case of the forecast door, with the workaround of naming a fit the project holds.
