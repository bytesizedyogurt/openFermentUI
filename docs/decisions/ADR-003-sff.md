# ADR-003 — SFF is the flowsheet record; a flowsheet module is an SFF recipe

- **Status**: accepted (provisional choice; stage 4 implements it)
- **Date**: 2026-10-30

## Context

The PISCES Standard Flowsheet Format toolkit
(`sustainability-software-lab/pisces-standard-flowsheet-format`, MIT) exports a BioSTEAM system to
a JSON file, validates it against its schema, scores its completeness and evaluates tags. It ships
no `pyproject.toml` and no importer that rebuilds a plant from a file: a file is the record, a
recipe (a `load.py` plus a pinned environment) is the executable.

## Options

1. Keep openFerment's own run tables as the only flowsheet record.
2. Depend on the toolkit by git URL: impossible without packaging metadata.
3. Vendor the toolkit at a pinned commit and make SFF the exchange record.

## Decision

Option 3. Vendor the package code at commit `e236e32` under `core/vendor/pisces_sff/` with its
LICENSE (schema, `export/design_specs/`, `tags/`, `completeness/criteria.yaml`, `validate/`),
record the commit and schema version in `core/licences.toml`, add `jsonschema` and `pyyaml` to the
`sim` extra. The exported reference flowsheets and the model registry are fetched on demand from
the pinned commit and hashed, never committed.

Every engine run writes an SFF file (validated; completeness and tags stored beside it). An
`SFFFlowsheet` record holds the file, its validation, its completeness report and its origin
(exported from a run, imported from a file, loaded from the toolkit's reference corpus). Each
flowsheet module gains the model-directory shape (`load.py`, `metadata.yaml`, an environment pin).
Earning the toolkit's `reproducible` tag through its conda harness is optional and off by default;
openFerment's own replay check (re-run within tolerance) is the verification that counts.

## Consequences

- Worker ops `sff_export`, `sff_validate`, `sff_score`; `engine/sff.py` with `import_sff` and
  `library_flowsheets`; the UI draws the SFF graph (units as nodes, streams as edges).
- `docs/api/sff.md` names the schema version and what openFerment adds in `metadata`.

## Implementation

### 4.1 (2026-10-30)

- `core/vendor/pisces_sff/` holds the package at `e236e32` with its LICENSE, unmodified, without
  `export/exported_flowsheets/` and `export/models/`; `core/vendor/README.md` says how to move it
  to a newer commit. `core/licences.toml` records it under `[vendored.pisces_sff]` (licence,
  source, commit, schema 0.2.4, directory, what was left out, why); `pnpm check:licences` holds
  the directory, its LICENSE and an allowed licence to the entry and lists it in THIRD_PARTY.md.
  `jsonschema` and `pyyaml` are in the `sim` extra.
- The toolkit imports BioSTEAM when imported, so it is imported in `workers/sff_toolkit.py` alone
  (`test_workers` holds it there), which puts `core/vendor` on the worker's path. The Proforma
  worker answers `sff_export`, `sff_validate` and `sff_score` (`docs/api/workers.md`).
- The export is an op of its own, which rebuilds the run's base case from the run's basis
  (`proforma.plant_of`), and is not folded into the `run` and `reference` ops. A replay must
  change nothing stored, and a run's artifact output must replay to its hash; the file's
  floating-point tail, and a record written as a side effect, would break both. The cost is one
  more base case per export (about a second for a reference plant after BioSTEAM is loaded,
  less for a warm shelf plant), measured against the run's own stream table in the sim tests.
- `engine/sff.py` keeps a record per project in `flowsheets` (migration 0002 adds `origin`,
  `sha256` and `document`, the file as text, byte for byte as it came). A file that fails
  validation is kept with its findings: seventeen of the eighteen reference files declare SFF
  0.0.3 and fail the 0.2.4 schema gate. A file is refused only when no graph can be read from it.
  Origin is computed from the file: `library` when its sha256 is a reference file's, whichever
  route it came by. The record's graph (nodes with a left-to-right rank, edges, feeds, products,
  dangling streams) is read in the service from the JSON; the toolkit's verdicts come from the
  worker.
- The reference corpus: `engine/sff_library.json` (written by `python -m
  openferment_core.engine.sff manifest <clone>`) names the eighteen flowsheets and the model
  registry at the commit with their sha256 and size; `fetch` brings a file from
  raw.githubusercontent.com into `core/data/sff-library/<commit>/` and refuses one that does not
  hash as pinned. `library_flowsheets()` loads them as records with origin `library`, kept in no
  project; `import_library` keeps one in the project.
- The Proforma worker's manager (start, status, call) moved from `proforma.py` to
  `engine/simulator.py`, so the engine reaches the worker without importing `proforma`;
  `proforma.py` re-exports its names. Engine functions take the project id from their caller
  rather than importing `projects` (§7.2 lists what the engine imports).
- What stage 4 still owes here: every run writes its SFF file when runs move to the `runs` table
  (4.4); the flowsheet modules' recipe directories (4.3); the UI's graph view is stage 7's.

### 4.2 (2026-10-30)

- The toolkit's design-spec registry names design inputs whose values are thermosteam objects
  (`NRELEthanolFermentation`'s two reactions, `MassBalance`'s stream lists), and its JSON writer
  fails closed on them, so it could not write the sugarcane, lipidcane, oilcane and cane plants.
  `workers/sff_toolkit.py` teaches the writer, for openFerment's exports alone, to write a reaction
  as thermosteam writes it and a stream by its id, and puts the toolkit's own writer back after;
  the vendored files are unchanged. With it, all nine buildable library plants export valid files
  (completeness 0.74 to 0.81). To be offered upstream.
- A library run exports through `sff_export` with `library` (the plant rebuilt and set as its run
  set it).

### 4.3 (2026-10-30)

- The flowsheet module has the model-directory shape (`flowsheets/recipes/cellulosic_ethanol_v0/`:
  `load.py`, `environment.yaml` pinned from `core/uv.lock`, `extended_metadata.yaml`), and a run's
  SFF file embeds it through the toolkit's own `build_reproducibility`; the toolkit finds the
  recipe present and its digests valid. Earning `reproducible` through the conda harness stays off.

## Revisit condition

The toolkit ships an importer or packaging; the schema reaches 1.0.

## Evidence

- Commit `e236e32` (2026-10-19): `pisces_sff/schema/sff_schema.json` declares `"version": "0.2.4"`;
  `pisces_sff/_version.py` reads the package version from it; no `pyproject.toml` or `setup.py`.
- Measured at that commit: **eighteen** exported BioSTEAM flowsheets
  (`export/exported_flowsheets/bioindustrial_park/SF_BST_01.json` … `SF_BST_18.json`, about 12 MB)
  and one model recipe (`export/models/biosteam_models/M_BST_01`). The execution prompt counted
  thirteen; the tree at the pinned commit wins.
- Package code without the exported flowsheets is about 0.8 MB.
