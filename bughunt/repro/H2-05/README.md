# H2-05: the export package leaves out the kinetic fit a forecast run rests on

**Statement.** `study.json` carries each run's artifact and each comparison's and no artifact a kept basis
names beyond those, so a kinetics forecast run's basis names a kinetic fit (its parameters, covariance and
the readings it was fitted on) that no member of a package meant to open without the service holds.

**Contract.**

- `CLAUDE.md:8` (R): "every claim, number and result stays inspectable back to its source, its calculation
  and its assumptions".
- `docs/api/studies.md:234`: "The project's studies as one zip that opens with nothing of openFerment's".
- The module states the same aim for readings: `core/openferment_core/studies/exports.py:135-136`, "what a
  measured value rests on, so it can be read without the service".
- The narrower wording at `docs/api/studies.md:240` ("whole, the artifacts that computed the runs and the
  comparisons") reads as met: the `growth_forecast` artifact computed the run. The break is against the R
  line and the package's stated purpose. The fit is the forecast's only input, and its numbers are what the
  band is drawn from.

**Command.** `bash bughunt/repro/H2-05/run.sh` from the repository root. It makes the fresh database
`bh_r_h2_05_export`, starts the service on the first free port in 9980 to 9989 (keyless, fixtures on),
makes a project, posts one kinetic fit of logistic readings (`POST /api/fermos/fit`, kept as an artifact
with no runs row), forecasts it (`POST /api/fermos/forecast`, kept as a run of the kinetics engine), takes
`GET /api/studies/export`, and opens the zip under `python3 -I -S`. It then stops the service and drops
the database.

**Expected.** `study.json`'s `artifacts` hold the kinetic fit the forecast run's basis names (input
`kinetic fit`, source `{"kind": "artifact", "id": <fit>}`), so the forecast's band traces back to the
fitted parameters and the readings in the package alone.

**Observed (run1.log, run2.log, both RESULT: DEFECT).**

- The package holds `manifest.json`, `study.json`, `study.md` and `versions.json`. `study.json` has one run
  (engine `kinetics`, configuration `e79f2b2f29fbaba2`, the fit's id) and one artifact, the run's own
  `growth_forecast`.
- That artifact's whole basis is `('kinetic fit', 'e79f2b2f29fbaba2', {'kind': 'artifact', 'id':
  'e79f2b2f29fbaba2'})`. The fit it names is absent from `artifacts`. Its id appears nine times across
  `study.json` and `study.md`, each time as a reference.
- None of the nine fitted parameters the service kept (X0, mu, Xmax, P0, alpha, beta, S0, gamma, delta)
  appears anywhere in the package, written either as `study.json` writes a float or as `study.md` does.
- The service keeps the fit and the forecast draws on it (`fermos._fit_from` reads
  `artifacts.get(<fit>).output`), so a reader of the package sees the band with nothing it was computed
  from.

**Likely cause.** `core/openferment_core/studies/exports.py:97-102`: `study()` gathers the artifacts of the
runs (`rep.artifact`) and of the comparisons, and stops there. It never follows a gathered artifact's basis
inputs whose source is `kind: "artifact"`. A forecast's basis names its fit only that way
(`core/openferment_core/fermos.py:828-829`, `BasisInput(name="kinetic fit", value=fit_artifact, ...,
source=BasisSource(kind="artifact", id=fit_artifact))`), and a fit is kept as an artifact with no runs row
(`fermos.fit`, `core/openferment_core/fermos.py:636`). `_depositions` (`exports.py:132-141`) already
follows measurement refs out of the runs' inputs, which shows the shape the fix would take: follow artifact
sources the same way. Confidence: high for the forecast path shown here. The candidate's further case, a
Proforma run's chosen fit, was left unexercised here.

**Severity.** S3. The export works and every other check holds. The service still keeps the fit, so a
person can read it there. A kinetics forecast's package stands incomplete, against the package's purpose.
