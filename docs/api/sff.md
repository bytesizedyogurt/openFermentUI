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
| `origin` | `run` (exported by openFerment from a run of the project), `library` (the file's sha256 is one of the toolkit's reference flowsheets at the pinned commit, whichever route it came by), `imported` (any other file, uploaded or fetched by its address) |
| `title` | the file's `metadata.process_title`, else its named feedstocks and products (`Corn stover → Ethanol`), else the file's name |
| `source` | where the file came from, in words: a run's export says `exported from run <artifact id> of <flowsheet id>`, or `of train <train id>` for a train run; an uploaded file `the file <name>, imported`; a file fetched by its address `the file at <address>, imported`, with `served from <address>` before `imported` when a redirect led to another address; a reference flowsheet the toolkit's own words, followed by `fetched from <address>` (and `served from <address>`) when it came by its address |
| `sha256`, `bytes` | of the file as it came; the file is kept byte for byte (`GET …/file`) |
| `validation` | `valid` (no schema failure and no error-severity check failed), `summary` (every result counted by severity and status), `findings` (each result that did not pass: check id, severity, status, message, path) |
| `completeness` | the toolkit's completeness report: `score` (weighted over every scored criterion), `representableScore` (over the criteria the file's own version can state), per category and criticality, each criterion with what it found missing, the re-execution route it found, and the toolkit's text rendering |
| `tags` | each tag the toolkit knows: earned, declared, blocking. `reproducible` is never evaluated (`earned: null`): earning it runs the toolkit's conda harness, which openFerment does not run. openFerment's replay check is the verification that counts (ADR-003) |
| `graph` | what the UI draws (below); left out of a listing |
| `runArtifactId`, `libraryId` | the run a `run` record was exported from; the reference id (`SF_BST_15`) of a `library` record |
| `url` | the https address a file fetched by its address came from, as the person named it (below); null for every other door |

A file that fails validation is kept, with its findings. Seventeen of the toolkit's eighteen
reference flowsheets declare SFF 0.0.3 and fail the 0.2.4 schema gate; refusing them would
refuse the toolkit's own corpus. A file is refused only when no graph can be read from it: not
UTF-8, not JSON, or not an object with a list of units and a list of streams (422), or larger
than 16 MB (413).

## A file by its address

`POST /api/flowsheets/import-url` takes `{"url", "by"}`: the public https address of an SFF file
and the person who names it (`engine/sff.py` `import_url`). This route is the one door that
fetches a flowsheet by its address: the address is a person's to name (the prompt's §3), and the
`flowsheet_import` tool takes a reference file's id alone, so no model, over the loop or MCP, has
the service fetch an address. The service fetches the file the way Intake fetches a document
(`literature/collectors.py` `fetch_file`), with the collectors' manners: the throttle (at most two
requests a second, shared with every collector), the User-Agent naming the project and, when
`OPENFERMENT_CONTACT` is set, somebody to write to, a timeout of 20 s on connecting and on each
read, and one retry on a 5xx. The whole exchange, from the host's resolution through the TLS
handshake and the headers to the file's last byte, is held to 120 s. Each of these is a setting.

- **https alone.** The address must be https and name a host; one that names a user or a password
  is refused too, since the record keeps the address as its source. A redirect is followed to
  another https address alone, held to every rule here, at most five times.
- **A public address alone** (D10's amendment at C.6). Before connecting, and again for each
  redirect's address, the host is read as an address when it names one by its digits (a dotted
  quad, an IPv6 address, or a short or numeric form such as `127.1` or `2130706433`, read as the
  system reads it), and resolved otherwise. The fetch is refused when any address the host names
  is loopback, private, link-local, multicast, reserved, unspecified or otherwise outside the
  public internet, as Python's `ipaddress` module decides, IPv4 and IPv6 alike, an IPv4-mapped
  IPv6 address read as its IPv4. The request then goes to a checked address by its digits, with
  the host's name in its Host header and as the TLS server name its certificate is checked
  against, so a second resolution cannot move it; the service connects itself, with no proxy.
  This narrows what the service reaches and adds no host to any list.
- **Streamed under the size an import takes.** The body is read as it arrives and refused once it
  passes 16 MB (for an uncompressed body, as soon as the host states a larger length), before the
  rest is read; a compressed body is held to the size it decompresses to.
- **Fixture mode.** With `OPENFERMENT_FIXTURES` set the network is refused, as every collector
  refuses it there, in the collectors' words.
- **Kept as an uploaded file is.** The bytes are read, checked by the toolkit in the worker, drawn
  and kept byte for byte with their sha256, under the same rules: `origin` is `imported`, or
  `library` when the file hashes as one of the reference flowsheets; `source` names the address
  (for a reference flowsheet, its own words followed by `fetched from <address>`) and `url` holds
  it. The address is kept whole, its query included, in `source` and in `url`, so a person names
  an address that carries no secret. The same file kept again is the record
  already held, whichever address served it, so the same address serving the same bytes twice is
  one record; of two imports of one file in flight together, the first keeps its record and the
  second answers with it.

Each refusal is said in words a person reads: 413 for a file past the size; 422 for an address
that is not https, that names a user or a password, or that names an address outside the public
internet (a redirect to any of these included), for the network refused in fixture mode, and for
a file no graph can be read from (the check's words, or, when the address served something that
is no JSON, what it served: `the address served an HTML page (text/html), and an SFF file is
JSON`); 502 when the host name could not be found, the host refused the connection, could not be
reached, or was not read in time, or it answered an error; 503 when the worker could not check
the file. The log keeps each failure's exception in its own words. A refused request keeps
nothing. The guard's list of hosts the service answers to is unchanged: the fetch is outbound.

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

A pureOS train run's block names its train in that place:
`"train": "the id of the train whose run was written"`, and its file's process title is the
train's name.

The export writes the run's base case: a shelf flowsheet's warm plant set to the run's base
values (with the price the run solved on its product), a library plant built afresh and set as
its run set it, or a pureOS train rebuilt from the `train_run` request its run's basis gives and
simulated whole as its run simulated it (`docs/api/workers.md`, `sff_export`). A run kept from
one of the shelf's two retired reference entries (a `proforma.reference` or `proforma_benchmark`
artifact, alpha 2.2 D8) writes no file of its own: the library plant it built (`cornstover`,
`corn`) writes the same package's plant from its run, and the export is refused in words naming
it. A train
carries no TEA. The schema the toolkit ships at `e236e32` requires every file's
`metadata.TEA_year` (`sff_schema.json`), the year its costs are reported in, which the exporter
reads from the system's TEA (`tea.duration[0]`, `export/_export.py`), and a train run computes
no TEA and no TEA year. While the schema requires the year, the worker refuses a train's file in
those words before it builds anything; a train run keeps them as its `sffRefused`
(`docs/api/runs.md`, A train run), and the record waits on the schema leaving the year to a file
whose system no TEA prices. It does not write the grid or the samples. A file openFerment imports
is kept as it came; nothing is added to it.

A run of openFerment's own flowsheet (`cellulosic_ethanol_v0`) also carries its recipe, embedded
as the toolkit's runner embeds a model's: `metadata.reproducibility` holds the recipe's `load.py`,
its `environment.yaml` and its `extended_metadata.yaml`, each with its sha256, the simulator and
flowsheet packages pinned in that environment, and what ran (Python, platform, package versions);
the recipe's authored metadata (source DOI, designers, the organism) is written beside it. The
toolkit's checks find the recipe present and its digests valid. `exported-from-simulator` is still
not earned: one warning-severity check (UNIT-07, two of the package's facilities attached to no
stream) blocks it, and the `reproducible` tag is never evaluated.

One adaptation, for openFerment's exports alone: the toolkit's design-spec registry names design
inputs whose values are thermosteam objects (`NRELEthanolFermentation`'s `fermentation_reaction`
and `cell_growth_reaction`, `MassBalance`'s stream lists), and its JSON writer refuses them, so at
`e236e32` it could not write the sugarcane, lipidcane, oilcane and cane plants. While openFerment
exports, the writer also writes a reaction as thermosteam writes it (equation, reactant,
conversion and basis) and a stream by its id; anything else still fails closed, and the vendored
files are unchanged (`workers/sff_toolkit.py`, `_writes_objects`). To be offered upstream.

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
| `POST /api/flowsheets/import-url` | `{"url", "by"}`: the file a public https address serves, fetched as Intake fetches a document and kept as an uploaded file is, the address its source (above). 413, 422, 502, 503 |
| `GET /api/flowsheets/library` | the reference flowsheets and which are fetched here; fetches nothing |
| `POST /api/flowsheets/library/{id}` | `{"by"}`: fetched (or found here), hash checked, checked in the worker, kept with origin `library`. 404, 502 (fetch or hash), 503 |
| `POST /api/flowsheets/export` | `{"artifactId", "by"}`: a kept run (a shelf run, a library run or a pureOS train run) exported, checked and kept with origin `run`. 404, 409 in the worker's words (the run's base case cannot be built; for a train run, the toolkit wrote no file, at `e236e32` for want of a TEA year), 422 (no run, or a run kept from a retired reference entry, the refusal naming its library plant), 503 |

## Measured (2026-10-30, BioSTEAM 2.54.0, biorefineries 2.35.1)

- The corn stover reference plant, measured at alpha 2.0's step 4.1 through the retired
  `cornstover_benchmark` entry's export (that path now refuses; the library plant's run writes
  its own file): export 0.3 s, validation 0.1 s, completeness scoring 2.0 s,
  tags 0.1 s after the plant is built; valid; completeness 0.741, representable 0.851 (system and
  TEA settings, 0.157, are the weakest category). `exported-from-simulator` is not earned without
  a reproducibility recipe (MET-07) and is blocked by UNIT-07.
- The reference corpus: `SF_BST_01` (SFF 0.2.3, corn dry-grind) valid, completeness 0.805; the
  seventeen at 0.0.3 invalid under 0.2.4 (the schema gate, among 4 to 10 error findings each),
  completeness 0.627 to 0.734. Every one draws: 54 to 133 units; four (`SF_BST_02` to `05`) carry
  one stream into a unit the file does not list.
