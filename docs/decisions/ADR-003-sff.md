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
