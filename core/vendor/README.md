# Vendored source

Code copied into the repository unmodified at a pinned commit, because it ships no packaging
metadata to install it from. Each directory keeps its own LICENSE, and `core/licences.toml`
records the source, the commit and what was left out (`[vendored.*]`); `pnpm check:licences`
holds the two together.

| Directory | Source | Commit | Licence |
|---|---|---|---|
| `pisces_sff/` | [pisces-standard-flowsheet-format](https://github.com/sustainability-software-lab/pisces-standard-flowsheet-format), the `pisces_sff` package (SFF schema 0.2.4) | `e236e32` | MIT |

`pisces_sff` imports BioSTEAM when it is imported (`export/_export.py`), so it runs in the
Proforma worker alone (`core/openferment_core/workers/sff_toolkit.py` puts this directory on the
worker's path). Its `export/exported_flowsheets/` and `export/models/` are left out: the reference
flowsheets and the model registry are fetched on demand from the same commit by
`core/openferment_core/engine/sff.py` and checked against `engine/sff_library.json`.

To move to a newer commit: copy the package directory over this one, leaving those two
directories out; update the commit in this file, in `core/licences.toml` and in
`engine/sff_library.json` (`python -m openferment_core.engine.sff manifest <clone>` rewrites the
manifest from a clone at the new commit); run `pnpm test:sim`.
