# H2-06: a configured plant's package-test read naming no configuration answers null

**Statement.** `GET /api/library/oilcane/regression` with no configuration answers `null`, while the
engine names `S1` as the configuration a run of oilcane takes when none is named, `GET
/api/library/oilcane/regression?configuration=S1` answers `test_oilcane_S1` with its 11 values, and
`POST /api/library/oilcane/run {}` runs in `S1` and is held to `test_oilcane_S1`; the reference page
`/p/:project/proforma/reference/oilcane`, before any run, then says in one card that
`test_oilcane_S1` "was not found in the installed package" while its header says the plant is held
to that same test in its default configuration, `S1`.

## Contract

- `core/openferment_core/api.py:1312-1313` (the route's own docstring, carried into the OpenAPI
  document): "The values the package's own test for this plant asserts, read from the installed
  file; null when it has none." oilcane has thirteen package tests installed, one a configuration,
  and the run naming no configuration is held to one of them.
- `docs/api/engines.md:629-631`: "A plant that takes a configuration, asked with none, runs in its
  default (`default_configuration` ...), and every door that reads its parameters reads them there".
  The list that follows (lines 632-633) names four parameter doors; the regression read stands
  outside that list, so this line gives the intent the regression read departs from, and the
  route's docstring is the words it breaks.
- `src/screens/ProformaReference.tsx:24` and `:28-34`, the page reading the route: "GET
  /api/library/{plant}/regression  the package test's values, before a run"; the header names "the
  package test the run is held to", and the card shows each value "from the artifact's `checks`
  (or, before a run, the service's `regression`)".

## Command

    bash bughunt/repro/H2-06/run.sh

From the repository root. It makes `bh_r_h2_06_svc` fresh, starts the head's service keyless on
127.0.0.1:9494 over the built app in `dist/`, makes a project, reads the shelf, the engines list and
the regression route twice, opens the reference page in headless Chromium (`screen.mjs`) before any
run, runs oilcane once naming no configuration (BioSTEAM in the worker, about two minutes), prints
EXPECTED, OBSERVED and RESULT, then stops the service and drops the database.

## Expected

The read naming no configuration answers the package test of the configuration a run naming none
takes, `test_oilcane_S1`, as the parameters read and the run both take the default; the page,
before a run, sets out that test's values.

## Observed (both runs)

- `GET /api/engines`: biosteam's oilcane runs, naming no configuration, in `S1`.
- `GET /api/library/oilcane/regression` -> `200 null`.
- `GET /api/library/oilcane/regression?configuration=S1` -> `200`, `test_oilcane_S1`, 11 values.
- `POST /api/library/oilcane/run {"by": ...}` -> configuration `S1`, the artifact's `regression.test`
  `test_oilcane_S1`, `outputs.regression` `{"within": 11, "of": 11}`.
- The page before a run: header "Held to biorefineries/tests/test_biorefineries.py::test_oilcane_S1 ·
  in its default configuration, S1"; card "The service read no package test for this plant
  (test_oilcane_S1 was not found in the installed package)."

See `run1.log` and `run2.log`.

## Likely cause

`core/openferment_core/api.py:1314-1315` passes the configuration as asked to
`library.regression(plant, configuration)`; with `None`, `library.package_test`
(`core/openferment_core/engine/library.py:148-154`) looks for `test_oilcane`, which the installed file
lacks, and answers `None`. The parameters route one screen above (`api.py:1300-1302`) resolves the
configuration first through `engine/biosteam.py` `default_configuration` (line 160); the regression
route does not. The client asks with no configuration (`src/lib/proforma.ts:113-114`), and the page
words a null answer as the test missing from the installed package
(`src/screens/ProformaReference.tsx:116-121`, the name from line 339).

Confidence: high. Fix size: small (resolve the configuration through `default_configuration` in the
route, as the parameters route does). Reach: the two reference cards Proforma lists (cornstover,
corn) take no configuration, so the main screen is untouched; a configured plant's page reached by
its address, and any caller of the route naming no configuration, meet it. Naming the configuration
(`?configuration=S1`) is the workaround on the route, and a kept run of the plant fills the card from
the run's own `regression`.
