# H2: runs and studies

Hunt H2 read engine/runs.py, engine/biosteam.py, engine/library.py, studies/*, proforma.py's run path, fermos_engine.py,
pureos/engine.py, artifacts.py, runbook_lock.py, project_state.py's lock and removal paths, the tools and the routes of
its area cold, against docs/api/runs.md, studies.md, engines.md, sff.md and ADR-015. Every claim below was run on test
databases (bh_h2_*) on ports 8820 to 8823, keyless, and each database is dropped and each service stopped.

## What was made and how

- A fresh database with two projects (h2a, h2b). In h2a: cornstover at its defaults; a measured study scenario on two
  deposited readings; ethanol_glucose_v0 as a Proforma run (20 and 500 samples), a kept Proforma scenario run through
  its route and run_flowsheet, a priceless run, the composite custom_train_v1 on a kept vessel and train run; a batch_v1
  simulation, two kinetic fits and their forecasts, a vessel design; a train made from the cornstover run through the
  Builder's routes (make_train.py) and run at three doors; receipts of the library, Proforma and kinetics engines;
  sample-engine runs through run_engine (contract_run.py).
- Every row checked field by field against runs.md (check_run.py recomputes the artifact id from the basis).
- The alpha 2.1 database copied by pg_dump into bh_h2_a21, migrated 0009 to 0010 with the head's migrations, served by
  the head, every kept thing read and every run and comparison replayed (read_kept.py).

## What held

- One shape and one row per request at every door, for every engine (the list is in candidates.json, `held`).
- Cross-project reads and writes refused in words at every door tried.
- The alpha 2.1 runs, comparisons, scenarios and runbook read and replay identically under the head.
- The export package opens under `python -I -S`; two exports differ in the manifest alone; the command line's equals
  the route's; each SFF file's sha256 is its record's.
- The lock digest's number writer agrees with node on 80008 numbers (fuzz_js_number.py); a moved prediction is refused.

## What broke (candidates.json)

- H2-01 (S1): a comparison row takes the first run's unit for every run's value of a name, and reckons the change across
  units: two forecasts of the same readings in g L-1 and mg L-1 show +99,900 %, and study_compare cites it.
- H2-02 (S2): a Proforma scenario run replays with one-ulp differences after the service restarts, against the rtol 0,
  atol 0 the engine states for scenario flowsheets; the library rounds its runs to ten digits for this drift, and a
  Proforma run keeps every digit BioSTEAM gives.
- H2-03, H2-04 (S3): a locked runbook's row takes a rewritten lockedAt and lockHash (the page then reads "lock broken"),
  and the row can be taken back whole while its lock stays; made again it answers unlocked.
- H2-05 (S3): the export leaves out the kinetic fits forecast runs rest on.
- H2-06 to H2-08 (S4): the regression read ignores a plant's default configuration; one run is two scenarios when one
  names the default; a title of spaces erases a kept comparison's title.

## Scripts (bughunt/notes/H2/scripts/)

api.py (the client), check_run.py, make_fit.py, make_train.py, read_kept.py, lock_probe.py, open_export.py,
fuzz_js_number.py, contract_run.py, repro_proforma_replay.sh (H2-02 from a fresh database), repro_fresh.sh (H2-01 and
H2-03 to H2-08 from a fresh database).
