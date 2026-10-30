# SFF in openFerment

The PISCES Standard Flowsheet Format (SFF) is how a flowsheet travels in and out of openFerment
(ADR-003). This page is the contract: the schema version, the record openFerment keeps for a
file, what openFerment adds to a file it writes, and the routes. The code is
`core/openferment_core/engine/sff.py` (the service) and
`core/openferment_core/workers/sff_toolkit.py` (the toolkit, in the Proforma worker).

## The toolkit and the schema

- The toolkit is vendored unmodified at `core/vendor/pisces_sff/`, commit
  `e236e3250414f45cf9fd7b8b854f1afc67fc2cad` of
  [pisces-standard-flowsheet-format](https://github.com/sustainability-software-lab/pisces-standard-flowsheet-format)
  (MIT), recorded in `core/licences.toml` (`[vendored.pisces_sff]`).
- **Schema 0.2.4.** openFerment writes files at 0.2.4 and checks every file against the 0.2.4
  schema and the toolkit's semantic checks (`core/vendor/pisces_sff/validate/sff_checks.md`),
  whatever version the file declares. A record keeps both: `sffVersion` (what the file says) and
  `validation.schemaVersion` (what it was checked against).
- The toolkit imports BioSTEAM, so it runs in the Proforma worker alone. Validation, scoring and
  export are worker ops (`docs/api/workers.md`); reading a file's graph is plain JSON, in the
  service.

## The record

`SFFFlowsheet` (`core/openferment_core/models.py`). Every field below the file is computed:

| Field | What it is |
|---|---|
| `id` | `run-<artifact id>` for a run's export; `sff-<first 16 hex of the file's sha256>` for any other file. The same file kept twice is one record; a run exported twice is one record |
| `origin` | `run` (exported by openFerment from a run of the project), `library` (the file's sha256 is one of the toolkit's reference flowsheets at the pinned commit, whichever route it came by), `imported` (any other file) |
| `title` | the file's `metadata.process_title`, else its named feedstocks and products (`Corn stover → Ethanol`), else the file's name |
| `source` | where the file came from, in words |
| `sha256`, `bytes` | of the file as it came; the file is kept byte for byte (`GET …/file`) |
| `validation` | `valid` (no schema failure and no error-severity check failed), `summary` (every result counted by severity and status), `findings` (each result that did not pass: check id, severity, status, message, path) |
| `completeness` | the toolkit's completeness report: `score` (weighted over every scored criterion), `representableScore` (over the criteria the file's own version can state), per category and criticality, each criterion with what it found missing, the re-execution route it found, and the toolkit's text rendering |
| `tags` | each tag the toolkit knows: earned, declared, blocking. `reproducible` is never evaluated (`earned: null`): earning it runs the toolkit's conda harness, which openFerment does not run. openFerment's replay check is the verification that counts (ADR-003) |
| `graph` | what the UI draws (below); left out of a listing |
| `runArtifactId`, `libraryId` | the run a `run` record was exported from; the reference id (`SF_BST_15`) of a `library` record |

A file that fails validation is kept, with its findings. Seventeen of the toolkit's eighteen
reference flowsheets declare SFF 0.0.3 and fail the 0.2.4 schema gate; refusing them would
refuse the toolkit's own corpus. A file is refused only when no graph can be read from it: not
UTF-8, not JSON, or not an object with a list of units and a list of streams (422), or larger
than 16 MB (413).

## The graph

`SFFGraph`: units as nodes, streams as edges, read from the file. `"None"` in a stream's
`source_unit_id` or `sink_unit_id` is the toolkit's boundary sentinel (check C-01).

- `nodes`: every unit, with its `unit_type`, the simulator class the file names
  (`design_simulation_method` up to " on "), and `rank`, its column when drawn left to right: a
  depth-first walk from the units the feeds enter sets aside the streams that close a recycle,
  and each unit stands one column right of the furthest unit feeding it.
- `edges`: every stream from one listed unit to another, with its total mass flow.
- `feeds` and `products`: every stream entering from or leaving to the boundary, with the unit it
  enters or leaves, the display name the metadata gives it (feedstocks and products named in
  `metadata`), its mass flow and its price.
- `dangling`: streams that name a unit the file does not list; counted, never drawn. A stream with
  both ends at the boundary is neither drawn nor counted (the toolkit holds its flows at zero).
- Units: mass flow in kg/hr, price in USD/kg, read in either style a file writes them (a bare
  number under `quantity_units_global`, or an inline `{value, units}` in files of SFF 0.0.6 and
  before). A value stated in any other unit is left out, never converted.

## What openFerment adds to a file it writes

A run's export carries one extra block in `metadata`, which the schema admits
(`metadata.additionalProperties` is true) and no check reads:

```json
"openferment": {
  "project_id": "the project the run belongs to",
  "run_artifact_id": "the run's artifact id",
  "origin": "run",
  "flowsheet": "the shelf flowsheet whose base case was written"
}
```

The export writes the run's base case: a reference biorefinery built afresh inside
`package_defaults()` as its reference run builds it, or a shelf flowsheet's warm plant set to
the run's base values (with the price the run solved on its product). It does not write the
grid or the samples. A file openFerment imports is kept as it came; nothing is added to it.

## The reference flowsheets

The toolkit's eighteen exported BioSTEAM flowsheets (`SF_BST_01` to `SF_BST_18`) and its model
registry are never committed. `core/openferment_core/engine/sff_library.json` names each file at
the pinned commit with its sha256, size, title, declared version and paired model. `fetch` brings
one from `raw.githubusercontent.com` at that commit into `core/data/sff-library/<commit>/`
(`OPENFERMENT_SFF_LIBRARY` moves it; git ignores it), and refuses a file that does not hash as
pinned, setting it aside as `<name>.mismatch`. The toolkit's verdict on a fetched file is kept
beside it (`<name>.checked.json`), keyed by its hash and the schema, so a file is checked once.

```
python -m openferment_core.engine.sff fetch              every reference file, checked against its hash
python -m openferment_core.engine.sff manifest <clone>   the manifest rewritten from a clone at a new commit
```

## Routes

All act in the project the request names (ADR-005).

| Route | What it does |
|---|---|
| `GET /api/flowsheets` | the project's records, newest first, without graphs |
| `GET /api/flowsheets/{id}` | one record with its graph; 404 when the project holds none |
| `GET /api/flowsheets/{id}/file` | the file as held (`application/json`, as an attachment) |
| `POST /api/flowsheets/import` | multipart: `file`, `by`. Checked in the worker, drawn, kept. 413, 422, 503 |
| `GET /api/flowsheets/library` | the reference flowsheets and which are fetched here; fetches nothing |
| `POST /api/flowsheets/library/{id}` | `{"by"}`: fetched (or found here), hash checked, checked in the worker, kept with origin `library`. 404, 502 (fetch or hash), 503 |
| `POST /api/flowsheets/export` | `{"artifactId", "by"}`: a kept run (a shelf run, a reference run or the benchmark) exported, checked and kept with origin `run`. 404, 409 (the base case cannot be built), 422, 503 |

## Measured (2026-10-30, BioSTEAM 2.54.0, biorefineries 2.35.1)

- The corn stover reference plant: export 0.3 s, validation 0.1 s, completeness scoring 2.0 s,
  tags 0.1 s after the plant is built; valid; completeness 0.741, representable 0.851 (system and
  TEA settings, 0.157, are the weakest category). `exported-from-simulator` is not earned without
  a reproducibility recipe (MET-07) and is blocked by UNIT-07.
- The reference corpus: `SF_BST_01` (SFF 0.2.3, corn dry-grind) valid, completeness 0.805; the
  seventeen at 0.0.3 invalid under 0.2.4 (the schema gate, among 4 to 10 error findings each),
  completeness 0.627 to 0.734. Every one draws: 54 to 133 units; four (`SF_BST_02` to `05`) carry
  one stream into a unit the file does not list.
