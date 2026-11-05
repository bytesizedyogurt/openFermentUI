# The tools

<!-- Written by `pnpm gen:tools` (core/openferment_core/tools/reference.py) from the registry in
core/openferment_core/tools/. Edit a tool's registration, never this file: `pnpm check:tools` fails
when the two differ. -->

One registry, three callers: Postdoc's loop, the HTTP endpoints (`GET /api/tools`, `POST
/api/tools/{name}`) and the MCP server (`openferment`) run every tool through `tools.run`
(`core/openferment_core/tools/__init__.py`), so a rule the registry holds, it holds for each of them.

**For a client.** [The MCP server](#the-mcp-server), at the end of this page, says how to start it
and the two ways it reaches a project, and [A client](#a-client) is the recipe: the SDK's names, the
environment to hand the server, the shape of every answer, and where a write's audit row is read.
What a module read answers, and what each kind of row holds, closes [Module reads](#module-reads).

- **Inputs** carry ids, words and quantities (ADR-006). A number stands only inside a quantity, an
  object of `value` and `unit` (and `low` and `high` for a range), where a tool asks for one; a
  number anywhere else, outside the count fields `k` and `limit`, refuses the call. A number is a
  JSON number: digits inside a string, an id or a name among them, are words. The service writes
  each quantity's origin from who called: the answering model's estimate with its id, an
  assistant's estimate under the name it declares (over MCP its `clientInfo`, at the HTTP endpoint
  the `X-OpenFerment-Assistant` header), or the named person's assumption (`?by=` at the HTTP
  endpoint); a quantity nobody can be named for is refused, and over MCP a client that declares no
  name is named `an assistant over MCP`.
- **Outputs** are a `summary` object a model reads, at most 9,000 characters as JSON, and
  beside it what a claim may cite: records (`recordIds`), passages, evidence and module rows
  (`rows`; `moduleRefs` are the module rows a claim of Postdoc's plan cites, each by its `ref`). The
  whole of a large output travels in `data`, which no model reads, and a refusal is `error`, in
  words. `auditIds` names each audit row the call wrote, oldest first, by the id `GET /api/audit`
  serves it under: a write names the row of what it kept, a gated write the row of its proposal,
  and a read names none.
- **Scope**: every tool acts in one project (ADR-005): the request's, the question's, or the one the
  MCP server was started in.
- **Writes**: a tool marked *writes* keeps something new in the project, audited as its caller's,
  through `core/openferment_core/tools/writes.py`; a read keeps nothing but the computations it
  caches. At the HTTP endpoint a write names its caller: a person with `?by=<their name>`, or an
  assistant with the `X-OpenFerment-Assistant` header (`<name>/<version>`, UTF-8 text), whose
  call runs in the model's lane under that name, as over MCP. A call that names nobody, or names
  both, is a 422 in words, with nothing run. A write of the model's lane names the door it came in by
  on its audit row (`detail.via`: `postdoc` for Postdoc's loop, `mcp` for the MCP server in its own
  process, `http` for the header), and only Postdoc's carries an `effort`. A write's row keeps the
  note its call carried as `detail.note` (a gated write's proposal keeps it), and the call's answer
  names the row in `auditIds`. The person named is the write's author: its audit row
  (agent `person`), a proposal it makes (which waits for a person to carry it out, as every
  proposal does) and what it keeps; pureOS's kept trains hold a model's work alone, and a person's
  call to keep one is refused in the store's words.
- *strict* or *loose* says how Postdoc's model is offered a tool: strict holds the model to the
  schema as it writes the call; the registry validates every caller's input alike, an MCP client's
  among them.

48 tools.

## The registry

| Tool | Family | Kind | Scope |
|---|---|---|---|
| `search_records` | Records | read | project |
| `convert_units` | Units | read | project |
| `search_passages` | Literature | read | project |
| `yield_ceiling` | geneOS | read | project |
| `growth_forecast` | fermOS | writes | project |
| `selling_price` | Proforma | read | project |
| `draft_runbook` | Runbooks | read | project |
| `runbooks_read` | Module reads | read | project |
| `geneos_read` | Module reads | read | project |
| `fermos_read` | Module reads | read | project |
| `pureos_read` | Module reads | read | project |
| `proforma_read` | Module reads | read | project |
| `biorepo_read` | Module reads | read | project |
| `guild_read` | Module reads | read | project |
| `primer_read` | Module reads | read | project |
| `intake_read` | Module reads | read | project |
| `home_read` | Module reads | read | project |
| `runbooks_write` | Module writes | writes | project |
| `geneos_write` | Module writes | writes | project |
| `fermos_write` | Module writes | writes | project |
| `pureos_write` | Module writes | writes | project |
| `proforma_write` | Module writes | writes | project |
| `biorepo_write` | Module writes | writes | project |
| `guild_write` | Module writes | writes | project |
| `primer_write` | Module writes | writes | project |
| `intake_write` | Module writes | writes | project |
| `home_write` | Module writes | writes | project |
| `thermo_props` | thermosteam | read | project |
| `run_flowsheet` | Proforma | writes | project |
| `stream_table` | Proforma | read | project |
| `fermos_simulate` | fermOS | writes | project |
| `fermos_vessel` | fermOS | writes | project |
| `pureos_build` | pureOS | writes | project |
| `pureos_propose` | pureOS | read | project |
| `engine_plants` | Engine | read | project |
| `engine_parameters` | Engine | read | project |
| `engine_run` | Engine | writes | project |
| `engine_report` | Engine | read | project |
| `study_scenario` | Studies | writes | project |
| `study_compare` | Studies | writes | project |
| `study_read` | Studies | read | project |
| `literature_sources` | Literature | read | project |
| `literature_document` | Literature | read | project |
| `flowsheet_library` | Flowsheets | read | project |
| `flowsheet_import` | Flowsheets | writes | project |
| `flowsheet_read` | Flowsheets | read | project |
| `catalogue_read` | Catalogues | read | project |
| `catalogue_write` | Catalogues | writes | project |

## Records

### `search_records`

*read · scope: project · strict*

Search by words the extractions from the project's documents that Postdoc may cite, its records and its candidates: a record is an extraction a reviewer verified against its document's own words, its provenance verified, or gold where the reviewer kept a gold value; a candidate is one no reviewer has verified yet, its provenance unverified, waiting for a reviewer; one a reviewer rejected leaves every read. biorepo_read lists them by the same rule, as its kinds record and candidate. Returns at most ten, best match first, each with its kind (record or candidate), its record id, paper, what was measured, its value and unit as the paper wrote them, the quoted sentence, the strain, the carbon source when the paper states one, and its provenance. Filter by an ontology field id and by a strain id, or pass null for no filter. Returns none when nothing matches.

| Field | Type | Required | What it is |
|---|---|---|---|
| `query` | string | yes | Words to search the records for: what was measured, the organism, the product, the feed. |
| `field` | string or null | yes | An ontology field id to keep only records of that field, or null for any field. |
| `organism` | string or null | yes | A strain id to keep only records on that strain, or null for any organism. |
| `limit` | integer | yes | How many records to return, at most 10. A count. |

## Catalogues

### `catalogue_read`

*read · scope: project · loose*

Read one of the project's catalogues: its strains (each with its species, the chemical set its trains use and the other names papers give it), its products (each with its class, where the cells leave it and a protein's sequence), Guild's skills (each with the policy a person wrote for it, when one did) or Primer's lessons (each with the skills it counts toward and the minutes it takes; its body, the blocks and the checkpoint a person writes, is left to the catalogues screen and Primer). Narrow by words. Returns {kind, matched, entries, note}: matched counts every entry the words match, and entries holds the first limit of them (20 when limit is left out, at most 40), in id order, each an entry with its fields as kept and its null fields left out: its kind, id, name and the fields of its kind, who kept it (by), the lane it was kept in (agent: person or model), the door a model's entry came in by (via: postdoc, mcp or http), where it came from (source) and when it was kept (at, ISO 8601 in UTC, as the audit writes its rows' times). A pureOS proposal's host is a strain read here.

| Field | Type | Required | What it is |
|---|---|---|---|
| `kind` | string | yes | Which catalogue: strain, product, skill or lesson. |
| `words` | string | no | Words to narrow the entries by: an id, a name, an alias; empty for all. |
| `limit` | integer | no | How many entries at most, 1 to 40, 20 when left out; a limit outside those bounds refuses the call. A count. |

### `catalogue_write`

*writes · scope: project · loose*

Keep one entry in the project's catalogue of strains, products, skills or lessons, marked as yours: a strain a document describes, with its species and the names papers give it; a product with its class; a skill or a lesson. Names and words only, never a measured value: a number a paper reports is a record. An entry you kept yourself under the id, in your own name and through the same kind of door (Postdoc's loop, or an outside assistant's: MCP or the HTTP endpoint's assistant header), is replaced; an entry a person or another caller kept under it stays as it is, and the call is refused in words naming the entry and who kept it, so keep yours under an id of its own, one that starts with your name, its / written as a dot (example-agent.0.1-a-skill for example-agent/0.1). Say in the note what the entry rests on. A strain's own fields are species, program and aliases; a product's are category (one of the classes pureOS's proposer reads), location, sequence and sequenceSource; a skill's are family and mastery; a lesson's is skills; every kind takes name, summary and note, and a field of another kind is refused in words. A skill kept here holds no policy, which a person writes on the catalogues screen, and Guild rates nobody on it until one does; a lesson kept here holds no body (its minutes, blocks and checkpoint), which a person writes there too. The result's summary is the entry as kept, its null fields left out and a protein's sequence left to catalogue_read: its kind, id, name and fields, its own note, by (the name you are kept under), agent (model), via (the door: postdoc, mcp or http), source and at, beside state (open) and meaning (the service's word on the keep). Its audit row names the module that reads the kind (geneos for a strain, pureos a product, guild a skill, primer a lesson), action catalogue_write, state open, target <kind>/<id>, the caller as agent and who, your note as detail.note and the door as detail.via; the result's auditIds names that row by its id.

| Field | Type | Required | What it is |
|---|---|---|---|
| `kind` | string | yes | Which catalogue: strain, product, skill or lesson. |
| `id` | string | yes | The entry's id: a letter or a digit first, then letters, digits, '.', '_', ':' or '-', at most 80 characters. |
| `name` | string | yes | Its name as a person reads it. |
| `species` | string | no | A strain's species. |
| `program` | string | no | A strain's chemical set, as pureOS names it. |
| `aliases` | list of string | no | A strain's other names, as papers give them. |
| `category` | string | no | A product's class, one of those pureOS's proposer reads: molecular_biology_enzyme, diagnostic, research_protein, food_protein, sweet_protein, structural_protein, industrial_enzyme, therapeutic_protein, hmo, terpene, glycoside, biopolymer. |
| `location` | string | no | Where the cells leave a product, as a document states it: secreted, or intracellular. |
| `sequence` | string | no | A protein product's sequence, one letter a residue. |
| `sequenceSource` | string | no | Where the sequence was read, in words; a sequence needs it. |
| `family` | string | no | A skill's family. |
| `summary` | string | no | What the entry is, in words; a skill's what the skill is. |
| `mastery` | list of string | no | What mastery of a skill means, a criterion an item. |
| `skills` | list of string | no | The skill ids a lesson counts toward. |
| `note` | string | no | What the entry rests on, in words: the document or record it came from. |

## Literature

### `search_passages`

*read · scope: project · strict*

Search the full text of the project's documents for passages that bear on a question. Returns up to six passages, best first, each with its passage id, paper, year, section heading and text. Quote a sentence from a passage by its passage id, copied exactly; a quote not in its passage discards the claim. Use it when a claim needs the context a record does not hold.

| Field | Type | Required | What it is |
|---|---|---|---|
| `query` | string | yes | Words to search the papers' text for. |
| `k` | integer | yes | How many passages to return, at most 6. A count. |

### `literature_sources`

*read · scope: project · loose*

List the documents the project holds: each one's id, title, year, the collector that brought it, its licence class and how many passages the literature index keeps of it. Narrow by words in the title. A document enters the project only when a person selects it.

| Field | Type | Required | What it is |
|---|---|---|---|
| `words` | string | no | Words to narrow by (a title's words); empty for all. |
| `limit` | integer | no | How many rows at most. A count. |

### `literature_document`

*read · scope: project · loose*

Read one document the project holds: its citation (title, authors, year, journal, DOI, licence class) and its sections in order; name a section by its heading to read its passages, each with a passage id a claim quotes by a whole sentence, as search_passages' passages are quoted.

| Field | Type | Required | What it is |
|---|---|---|---|
| `document` | string | yes | A document's id, as literature_sources gives it. |
| `section` | string | no | A section's heading as this tool lists it, whose passages to read; empty for the list of sections alone. |

## Units

### `convert_units`

*read · scope: project · strict*

Convert one record's own value into another unit with the platform's unit engine, which refuses a conversion that needs a quantity it does not have (a percentage of protein into a concentration, say) and says why. Returns one computed value with its basis, citable as evidence, or the refusal in words. Name the record by id and the unit in words; the value is read from the record.

| Field | Type | Required | What it is |
|---|---|---|---|
| `recordId` | string | yes | The id of the record whose value to convert. |
| `toUnit` | string | yes | The unit to convert it to, written as the records write units. |

## Engine

### `engine_plants`

*read · scope: project · loose*

List what the library shelf runs: the biorefineries plants with an entry point and openFerment's own flowsheets, each with its configurations, the configuration a run takes when none is named, and the package a flowsheet is composed from; or, with `engine`, that engine's things. Beside them, `engines` lists every engine registered here: its version, its worker and the worker's state, its last conformance verdict, and the ids of the project's runs it made, newest first (engine_report reads each). Narrow the things by words. Returns ids and words, nothing to cite.

| Field | Type | Required | What it is |
|---|---|---|---|
| `engine` | string | no | The engine whose things to list: biosteam, whose things are the library plants, openFerment's flowsheet and the shelf's scenario flowsheets, or any other the summary's `engines` names. Whichever is named, the summary lists every engine registered here with the ids of the project's runs each made. |
| `words` | string | no | Words to narrow the shelf by: a product, a feedstock, a plant's name; empty for all. |
| `limit` | integer | no | How many rows at most. A count. |

### `engine_parameters`

*read · scope: project · loose*

A plant's parameters as the package builds it: each key with its label, its unit, its group and the library's default, and the bounds it is held to. A scenario sets a parameter by its key in that unit. Narrow by words. The first call builds the plant in the simulator and may take half a minute.

| Field | Type | Required | What it is |
|---|---|---|---|
| `engine` | string | no | The engine to read (GET /api/engines names them): biosteam, whose things are the library plants, openFerment's flowsheet and the shelf's scenario flowsheets, or any other registered here. |
| `plant` | string | yes | A plant's id, as engine_plants gives it. |
| `configuration` | string | no | One of the plant's configurations; empty for its own. |
| `words` | string | no | Words to narrow the parameters by; empty for all. |
| `limit` | integer | no | How many rows at most. A count. |

### `engine_run`

*writes · scope: project · loose*

Run a plant from the library shelf at the library's defaults, or a study scenario (by its id) with the values it sets, as an engine run: kept in the project, marked as yours, with the SFF file it writes. Returns the run's id, its artifact id, its provenance (assumed when a value it set is an estimate or an assumption; measured when a value it set is a deposition's reading and none is either), the values it set with their origins (a reading with its ref), and each number its price and its flowsheet's outputs hold as an evidence id to cite. The same plant and values asked again answer from the run kept. A plant that refuses the values is kept as a receipt and refused in the plant's words.

| Field | Type | Required | What it is |
|---|---|---|---|
| `engine` | string | no | The engine to run (GET /api/engines names them): biosteam, whose things are the library plants, openFerment's flowsheet and the shelf's scenario flowsheets, or any other registered here, whose thing this tool runs at its own defaults. |
| `plant` | string | no | A plant's id, run at the library's defaults; empty when a scenario is named. |
| `configuration` | string | no | One of the plant's configurations; empty for its own. |
| `scenario` | string | no | A study scenario's id (study_scenario returns it), run on its plant with its values. |
| `note` | string | no | Why the run is asked for, in words. |

### `engine_report`

*read · scope: project · loose*

Read a kept engine run by its id: what ran, the values it set with their origins, its provenance, and each number its price block, its flowsheet's outputs and its TEA breakdown hold as an evidence id to cite; with words in `parameters`, the parameters the run read back from the plant (its feed's composition, moisture and price, the chemicals' prices, the finance terms), each as an evidence id with its origin. A run whose engine reports what its computation did (the time it took, say) names those diagnostics as words beside its outputs. For a refused run, the plant's own words.

| Field | Type | Required | What it is |
|---|---|---|---|
| `engine` | string | no | The engine that ran it, when you know it: a run of another engine is then refused. Left out, the run's own. |
| `run` | string | yes | A kept run's id, as engine_run or study_read gives it. |
| `parameters` | string | no | Words to read the parameters the run read back from the plant by (its feed, a unit, a price, a finance term): each one matched comes back as an evidence id with its value, its unit and its origin. Empty for none. |
| `limit` | integer | no | How many parameters at most. A count. |

## Flowsheets

### `flowsheet_library`

*read · scope: project · loose*

List the SFF toolkit's reference flowsheet files at the pinned commit (their ids, titles, the schema version each declares, the simulator model each comes from) and which this machine holds. Narrow by words. Returns ids and words; flowsheet_import brings one into the project.

| Field | Type | Required | What it is |
|---|---|---|---|
| `words` | string | no | Words to narrow the reference files by: a plant, a product, a file's id; empty for all. |
| `limit` | integer | no | How many rows at most. A count. |

### `flowsheet_import`

*writes · scope: project · loose*

Import one of the toolkit's reference SFF files into the project by its id: fetched at the pinned commit, its hash checked, checked by the toolkit against the schema it ships, drawn, and kept as a record marked as yours. Returns the record's id, whether the file is valid and what the checks found, the unit types its graph holds, its feeds and its products by name, and what the graph counts as evidence ids to cite. A file already kept answers from its record.

| Field | Type | Required | What it is |
|---|---|---|---|
| `file` | string | yes | A reference file's id, as flowsheet_library gives it (e.g. SF_BST_15). |
| `note` | string | no | Why it is imported, in words. |

### `flowsheet_read`

*read · scope: project · loose*

Read an SFF flowsheet record the project holds by its id (an imported file, or the one an engine run writes): what the file is, whether it is valid, the unit types its graph holds, its feeds and its products, and what the graph counts as evidence ids to cite. With no id, list the project's records, narrowed by words.

| Field | Type | Required | What it is |
|---|---|---|---|
| `record` | string | no | A kept record's id (flowsheet_import or engine_run gives it); empty to list them. |
| `words` | string | no | Words to narrow the list by, when no record is named. |
| `limit` | integer | no | How many rows at most. A count. |

## Studies

### `study_scenario`

*writes · scope: project · loose*

Keep a study scenario on a plant from the library shelf: a title, the plant and its configuration, and the values it sets, each a parameter's key and a quantity (value and unit, the parameter's own unit) with a note saying in words what the value rests on. Each value is marked as your estimate, with your model id, and a run of the scenario is assumed. A value may also be a deposition's reading that runbooks_read lists (kind reading): its value and unit as the reading gives them, in the reading's own unit, and origin {"kind": "measurement", "ref": "<the reading's id>"}; the service looks it up and marks it with who deposited it and when it was taken, and a run resting on readings and the library's defaults alone is measured. Checked against the plant's parameters: a key it does not read, a unit it does not use or a value of the wrong kind is refused before anything is kept, as is a reading the project does not hold, one nobody read back, one corrected since, or one in a unit that does not convert into the parameter's. The same plant and values are one scenario. Run it with engine_run.

| Field | Type | Required | What it is |
|---|---|---|---|
| `title` | string | yes | What the scenario asks, in words. |
| `plant` | string | yes | A plant's id, as engine_plants gives it. |
| `configuration` | string | no | One of the plant's configurations; empty for its own. |
| `values` | list of `ScenarioValueIn` | yes | The parameters it sets, each a quantity in the parameter's own unit with a note saying what the value rests on, or a deposition's reading in its own unit (runbooks_read, kind reading); every other parameter keeps the library's default. |
| `note` | string | no | Why the scenario, in words. |

`QuantityIn`: A number you type: a value in a unit, and in words what it rests on. The service marks it with who typed it. A value that is a reading a person deposited names the reading in `origin`, its value and unit the reading's own: the service looks the reading up and marks the value with the reading's depositor and time.

| Field | Type | Required | What it is |
|---|---|---|---|
| `value` | number | yes | A number of the quantity, marked as its caller's. |
| `unit` | string | yes | The value's unit, as the tool names it. |
| `note` | string | no | What the value rests on, in words. |
| `origin` | object or null | no | Leave it out for a value you type. For a deposition's reading: {"kind": "measurement", "ref": "<deposition id>/<entry id>"}, the value and unit then the reading's own, which the service checks. |

`ScenarioValueIn`

| Field | Type | Required | What it is |
|---|---|---|---|
| `key` | string | yes | The parameter's key, as engine_parameters gives it. |
| `quantity` | `QuantityIn` | yes | The value, in the parameter's own unit, with what it rests on; a deposition's reading in the reading's own unit, which the service converts into the parameter's where it converts. |

### `study_compare`

*writes · scope: project · loose*

Set two to twelve kept engine runs side by side as one comparison, kept in the project: every output the runs answer with each run's value and its change from the first run's, and every value any run set with its origin. Each later run's change from the first is an evidence id to cite; the comparison's provenance is the weakest of its runs'.

| Field | Type | Required | What it is |
|---|---|---|---|
| `title` | string | yes | What the comparison asks, in words. |
| `runs` | list of string | yes | Kept runs' ids, the first the one each change is reckoned from. |

### `study_read`

*read · scope: project · loose*

List the project's study scenarios (each with the values it sets, their origins and the runs made of it), its comparisons and the runbooks studies made. Narrow by kind and words. Returns ids and words to act on; a run's numbers are read with engine_report.

| Field | Type | Required | What it is |
|---|---|---|---|
| `kind` | one of `scenario`, `comparison`, `runbook`, empty | no | scenario, comparison or runbook; empty for every kind. |
| `words` | string | no | Words to narrow by; empty for all. |
| `limit` | integer | no | How many rows at most. A count. |

## Proforma

### `selling_price`

*read · scope: project · strict*

The minimum selling price the most recent kept run of one of the project's BioSTEAM scenarios produced, as one evidence id to cite: the median with its 5th to 95th percentile, the infeasible share, which inputs rest on an assumption and which on a deposition's reading, and what the flowsheet leaves out. Refuses when no run is on file, naming the inputs still waiting for a source and how a run is made. With a plant of the library shelf by its id (cornstover, the NREL 2011 corn stover design; corn, the dry-grind corn plant; any plant engine_plants lists) it reads that plant's newest kept run on its package's own values: the selling price its TEA solves, as the evidence id engine_report gives it, and how many of the package test's values the run holds. An id of a retired reference entry (proforma_benchmark, cornstover_benchmark, corn_drygrind) reads its library plant, or, when the project keeps no such run, the newest run the project kept from that entry, its price as the entry named it. It cannot run a scenario or make an assumption.

| Field | Type | Required | What it is |
|---|---|---|---|
| `scenarioId` | string | yes | The id of a BioSTEAM scenario the project keeps (proforma_read lists them), whose newest kept run it reads; or a plant of the library shelf by its id (engine_plants lists them: cornstover is the NREL 2011 corn stover design, corn the dry-grind corn plant), whose newest run on its package's own values it reads. |

### `run_flowsheet`

*writes · scope: project · loose*

Run one of the project's BioSTEAM scenarios as its page runs it, and keep the run: one artifact holding the minimum selling price across the inputs' ranges, the cost breakdown, the sensitivity and the base case's stream, unit and utility tables. Returns one evidence id to cite (the run's artifact id), the median price with its 5th to 95th percentile, how each input is bound and the cost lines. Takes a scenario id and nothing else: you never type an assumption, a value or a setting. The run reads the assumptions a named person set on the scenario's page and the fermOS fits chosen for it; an input that neither a record nor such an assumption binds waits, and the call then refuses and names the inputs that wait, and nothing runs. It spends no model money and is at no gate; the run is marked as yours in the audit log until a person promotes it. A run can take minutes.

| Field | Type | Required | What it is |
|---|---|---|---|
| `scenarioId` | string | yes | The id of a BioSTEAM scenario the project keeps; proforma_read lists them. Nothing else: no value, no assumption, no setting. |

### `stream_table`

*read · scope: project · loose*

Read the stream table a kept Proforma run holds: every stream of the base case with the unit it leaves and the unit it enters (none for a feed or a product), its phase, temperature, pressure, mass flow, price and largest components, as BioSTEAM held them after the run. Takes the run's artifact id and nothing else (a scenario's proforma.run artifact or a library plant's library.run artifact, the corn stover and dry-grind corn reference plants' among them, or a proforma.reference artifact kept from a retired reference entry); you never type a number. The plant's feeds and products come first; a long table is cut to what a model may read and says how many streams it left out. A scenario's run and a kept reference run return their evidence id to cite, the run's price; a library plant's numbers are cited by the evidence ids engine_report names for its outputs. It runs nothing.

| Field | Type | Required | What it is |
|---|---|---|---|
| `artifactId` | string | yes | The artifact id of a kept run: a proforma.run artifact (a scenario's run, as run_flowsheet, selling_price or proforma_read return it), a library.run artifact (a library plant's run, as engine_run, engine_report and proforma_read name it), or a proforma.reference artifact kept from a retired reference entry. Nothing else: no number, no stream, no setting. |

## fermOS

### `growth_forecast`

*writes · scope: project · strict*

Forecast a run like a fitted one: biomass, product and substrate as bands for readings, from a kept kinetic fit's artifact id, under the fitted run's own starting values and length. Returns one evidence id to cite and the final values as intervals. A fit whose growth rate or ceiling was not identified is refused with what run would identify it.

| Field | Type | Required | What it is |
|---|---|---|---|
| `fitArtifactId` | string | yes | The artifact id of a kept kinetic fit (the artifact tool kinetic_fit). |

### `fermos_simulate`

*writes · scope: project · loose*

Simulate a fermentation with one of fermOS's model families (batch with Monod growth, product and substrate inhibition and Luedeking–Piret production; fed-batch; chemostat) and keep it: one artifact holding the time course of cells, sugar and product, the oxygen uptake, the end state, the hour the sugar runs out, the mass balance and the product yield beside the geneOS ceiling. Each parameter binds from a fit you name, the records (the ones you name for it in recordsByParam, else those the rule finds for the strain and sugar), a kept simulation, or a stated convention, and the summary says what bound each one. You never type a number: name the family, the strain, the product, the sugar, record ids and artifact ids. A parameter nothing binds waits for a named person's assumption, typed in fermOS → Simulate; the call then refuses and names each parameter that waits and the field that would bind it, and nothing is kept. Returns one evidence id to cite (the simulation's artifact id): a titre, a yield or a productivity read from a simulation is cited by it and never stated. It spends no model money and is at no gate; the simulation is marked as yours in the audit log until a person promotes it. The parameters a record can bind, with the fields they bind from: mu_max (growth_rate_mu), ks (monod_ks), yxs (biomass_yield_substrate), alpha (ethanol_lp_alpha), beta (ethanol_lp_beta), yps (ethanol_yield_substrate), maintenance (maintenance_coefficient), p_max (ethanol_max_conc), ki_substrate (substrate_inhibition_ki), yxo (biomass_yield_oxygen), s0 (medium_component_conc), feed_conc (medium_component_conc; fedbatch_v1, chemostat_v1). light_v1 is declared and not built: it refuses in words.

| Field | Type | Required | What it is |
|---|---|---|---|
| `family` | string | yes | A model family's id (batch_v1, fedbatch_v1, chemostat_v1, light_v1); GET /api/fermos/families and fermOS → Simulate list them with their equations. |
| `strain` | string | no | A strain's id from geneOS's hosts (geneos_read, kind host), or an empty string: then the records of every strain bind. |
| `product` | string | no | The product's id (ethanol), or an empty string. |
| `sugar` | string | no | The sugar's carbon-source id (glucose), or an empty string. |
| `recordsByParam` | map to list of string | no | A parameter's key to the record ids that bind it, exactly those records (search_records returns them): each must be a record of a field the parameter binds from, kept by the aggregate gate. Ids only, never a value. An empty object, and the records the rule finds bind each parameter. |
| `fitArtifact` | string | no | A kept kinetic fit's or forecast's artifact id (fermos_read lists them), whose parameters bind first; or an empty string. |
| `startFrom` | string | no | records, fit (the fit named in fitArtifact), or simulation:<artifact id> (a kept simulation's values bind where no fit or record does). |
| `durationPreset` | one of `until-sugar-runs-out`, `fit-length` | no | until-sugar-runs-out (the run ends when the sugar runs out), or fit-length (as long as the fitted run, with a fit named). |

### `fermos_vessel`

*writes · scope: project · loose*

Design on BioSTEAM the vessel a kept fermOS simulation needs: BioSTEAM's AeratedBioreactor (a stirred tank or a bubble column) for an aerobic simulation, its NREL batch fermenter for an anaerobic one or a kept kinetic fit. Pass the simulation's artifact id (or the fit's), the vessel type and a kLa correlation by name, or empty strings; never type a number. The design needs a plant scale or a batch volume, which only a named person types in fermOS → Vessel: without one the tool refuses in words, and you say in gaps that the design waits for it. A design is kept as an artifact, marked as yours, and comes back as one evidence id (the artifact's) with the vessels, volumes, times, powers, kLa, oxygen balance, heat and cost read from it; cite them by that id.

| Field | Type | Required | What it is |
|---|---|---|---|
| `simulationArtifact` | string | yes | The artifact id of a kept fermOS simulation (fermos_read lists them), or an empty string when a fit is named. |
| `fitArtifact` | string | yes | The artifact id of a kept kinetic fit or forecast, for an anaerobic vessel (a fit gives no oxygen uptake), or an empty string. |
| `vesselType` | string | yes | stirred-tank or bubble-column for an aerobic simulation, or an empty string for BioSTEAM's own default; an anaerobic vessel takes none. |
| `klaMethod` | string | yes | A kLa correlation by the name BioSTEAM registers it (Riet for a stirred tank, Dewes for a bubble column), or an empty string for the class's own. |

## pureOS

### `pureos_build`

*writes · scope: project · loose*

Build a downstream train and run it on BioSTEAM, one action a call, from ids and words. new starts a train for a product (its id) from the inlet a kept artifact gives (inletRef: a kept simulation's artifact id, a kept vessel design's, or a kept run's stream as <artifact id>/<stream id>) and returns its trainId. add_unit adds a unit of a catalogue type (unitType: centrifugation, flash, distillation, molecular-sieve and the rest) after afterUnitId (inlet for the first place, empty for the end); remove_unit takes unitId out; set_from_record binds a parameter of unitId to exactly the record ids recordsByParam names for it (each must be a record of the field the parameter binds from, kept by the aggregate gate; one that cannot bind is refused naming the record and why); run runs the train in the Proforma worker as the service binds it; propose keeps the train the proposer's rules propose for the product (its id) made in host (a host strain id), its inlet a kept simulation's id, a kept run's stream or none (inletRef). You never type a number: every value binds from the records, the class's own default or a named person. A value nothing binds waits: the run then refuses naming each one, and nothing is kept; say in gaps that a person types it in pureOS → Builder. A run comes back as one evidence id (its artifact id) with each unit's recovery, the overall recovery and the product's share of the product stream read from it, and what bound each parameter in counts: cite a recovery or a purity by that id and never state it. The train is kept on the service as yours, every action marked so in the audit log; it spends no model money and is at no gate.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | one of `new`, `add_unit`, `remove_unit`, `set_from_record`, `run`, `propose` | yes | new, add_unit, remove_unit, set_from_record, run or propose. |
| `trainId` | string | no | The train's id, as new or propose returned it (pureos_read lists the trains a model built, kind train); empty for new and propose. |
| `unitType` | string | no | add_unit: a catalogue unit type's id (centrifugation, flash, distillation, molecular-sieve and the rest; GET /api/pureos/catalogue lists them). |
| `afterUnitId` | string | no | add_unit: the unit the new one follows, inlet for the first place, or an empty string for the end. |
| `unitId` | string | no | remove_unit and set_from_record: the unit acted on, by its id in the train. |
| `product` | string | no | new: the product the train recovers, by its id (ethanol); empty takes a simulation inlet's own product. propose: the product's id, required (the proposer reads its class from it). |
| `host` | string | no | propose: the host strain's id on geneOS's shelf of hosts, the cells the product is made in (the proposer's rules read where the product is made). |
| `inletRef` | string | no | new: the artifact the inlet is read from: a kept simulation's artifact id (its broth at harvest; its broth flow then waits for a person), a kept vessel design's artifact id (the harvest of the simulation it was designed for, the broth flow read from the design), or a kept run's stream as <artifact id>/<stream id> (stream_table lists a Proforma run's streams). propose: a kept simulation's artifact id (its broth at harvest) or a kept run's stream as <artifact id>/<stream id>, or empty for none (a person types the inlet in pureOS → Builder). |
| `recordsByParam` | map to list of string | no | set_from_record: a parameter's key on the unit (split.Ethanol, P, and the rest) to the record ids that bind it, exactly those records (search_records returns them); ids only, never a value. |

### `pureos_propose`

*read · scope: project · loose*

Propose a downstream train for a product made in a host, by written rules that each name the property they read: a small molecule lighter than water by thermosteam's boiling points is distilled, then dried on a molecular sieve where thermosteam finds an azeotrope with water; a secreted protein is clarified, concentrated by ultrafiltration, captured and polished by chromatography (keyed on ProtParam's isoelectric point and molecular weight) and spray-dried; an intracellular one is harvested and disrupted first. Ids and words in: a product id, a host strain id, and optionally an inlet (a kept simulation's artifact id, or <run artifact id>/<stream id>). Returns the units in order, each with its rule, property and artifact, every parameter left at its library default or waiting for a person; or what property is missing. Each property read is one evidence id to cite. Proposes only: nothing runs.

| Field | Type | Required | What it is |
|---|---|---|---|
| `product` | string | yes | The product's id: an entry of the products catalogue, or a product thermosteam's library is asked about by name (ethanol). |
| `host` | string | yes | The host strain's id on geneOS's shelf of hosts: the cells the product is made in. |
| `inletRef` | string | no | The train's inlet: a kept fermOS simulation's artifact id (its broth at harvest), or a kept run's artifact id and one of its streams as <artifact id>/<stream id>; an empty string for none (a person types the inlet). |

## geneOS

### `yield_ceiling`

*read · scope: project · strict*

The most product a published reaction network can make from one sugar, by flux balance analysis, kept as a computed value with its basis. Returns one evidence id to cite, the value in g per g and mol per mol, and the model it came from, a genome-scale network whose ceiling is the full network's. A sugar the model cannot take up, or a product it has no route to, comes back as a finding with no number.

| Field | Type | Required | What it is |
|---|---|---|---|
| `modelId` | string | yes | A model on geneOS's shelf, with the products it names a route to: iMM904 (ethanol); Yeast9 (ethanol). |
| `product` | string | yes | The product: ethanol. |
| `substrate` | string | yes | The sugar fed: glucose, fructose, xylose. |

## thermosteam

### `thermo_props`

*read · scope: project · loose*

Density, heat capacity, viscosity, and bubble and dew points of a mixture already on file, as thermosteam (BioSTEAM's property engine) computes them, kept as a computed value with its basis. Name a Proforma run's artifact id and one of its streams; or the preset ethanol-water-azeotrope; or beer-at-titre-of with an ethanol titre record's id (water and ethanol at that titre; the beer's cells and sugar are not in it). The service fills every number from what is on file. Returns one evidence id a property to cite. A chemical the library lacks is refused in words naming it.

| Field | Type | Required | What it is |
|---|---|---|---|
| `artifactId` | string | yes | A Proforma run's artifact id (the artifact tool proforma.run), with streamId; or an empty string. |
| `streamId` | string | yes | One stream of that run's stream table, by its id; or an empty string. |
| `preset` | string | yes | ethanol-water-azeotrope (the composition thermosteam's own vapour-liquid equilibrium gives), or beer-at-titre-of with recordId (water and ethanol at that record's titre); or an empty string when a stream is named. |
| `recordId` | string | yes | An ethanol titre record's id (field ethanol_titre), for beer-at-titre-of; or an empty string. |

## Runbooks

### `draft_runbook`

*read · scope: project · strict*

Draft a runbook from what this run found: a title, a product id and a strain id when it tests one the project's catalogues hold (both empty for a runbook of a plant's run), items that each name one evidence id or a field with record ids returned earlier in this run, and measures (label, unit, one of start, mid-run, harvest, after recovery, and the item label they test). Send no numbers: the service writes each prediction's value and interval from the evidence and the records. A person adopts and locks it.

| Field | Type | Required | What it is |
|---|---|---|---|
| `title` | string | yes | What the runbook tests, in words with no number. |
| `productId` | string | no | A product id from the project's catalogue; empty when the runbook tests a plant's run. |
| `strainId` | string | no | A strain id from the project's catalogue; empty when the runbook tests a plant's run. |
| `items` | list of `DraftItem` | yes | Each prediction: one evidence id, or a field with record ids this run returned. |
| `measures` | list of `DraftMeasure` | yes | What the bench records, each naming the item label it tests. |

`DraftItem`: One prediction the agent asks for: one computed evidence item, or records of one field. The pair it leaves unused is empty.

| Field | Type | Required | What it is |
|---|---|---|---|
| `label` | string | yes |  |
| `evidenceId` | string | no |  |
| `field` | string | no |  |
| `recordIds` | list of string | no |  |

`DraftMeasure`

| Field | Type | Required | What it is |
|---|---|---|---|
| `label` | string | yes |  |
| `unit` | string | yes |  |
| `timepoint` | one of `start`, `mid-run`, `harvest`, `after recovery` | yes |  |
| `itemLabel` | string | yes |  |

## Module reads

### `runbooks_read`

*read · scope: project · loose*

Read Runbooks: the runbooks (their status, lock and what they predict), the protocols (their versions), the depositions made at the bench (kind deposition: its runbook, state, how many readings it holds and how many a person confirmed, and the ids of the readings a run may take), each reading a run may take as a measurement (kind reading, read by its id <deposition id>/<entry id>: the measure it is of, its value and unit as the bench kept them, who deposited it and when it was taken; a scenario's value names it as {"value": <value>, "unit": "<unit>", "origin": {"kind": "measurement", "ref": "<its id>"}}), and the measured evidence a reconciliation released (kind measured-evidence: the prediction it tests, its value, unit and conditions). Kinds: runbook, protocol, deposition, reading, measured-evidence. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `geneos_read`

*read · scope: project · loose*

Read geneOS: the hosts, the pathways, the genome-scale models on the shelf and the ceilings computed on them. Kinds: host, pathway, model, artifact. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `fermos_read`

*read · scope: project · loose*

Read fermOS: the growth fits and forecasts computed from deposited runs (kind artifact), the kept simulations of a model family (kind simulation: its family, strain, product and sugar, and what bound each parameter, in words; its numbers stay in the artifact, cited by the row's ref or the evidence id fermos_simulate returns), the vessels BioSTEAM designed for kept simulations (kind vessel, read by the design's artifact id or the simulation's), and the depositions kept with the runbooks, whose series fermOS fits (kind deposition: its runbook, its readings and series, and the fits made from it). Kinds: artifact, simulation, vessel, deposition. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `pureos_read`

*read · scope: project · loose*

Read pureOS: the downstream unit operations, by stage (each with the BioSTEAM classes it is), and the trains Proforma's runs simulated (kind train, one a scenario: read by the scenario id or the run's artifact id); kind train-unit is one unit of a train, in run order, with the product in and out and the recovery read from the run's stream table. Kind train also holds the trains a model built with pureos_build (read by the train's id: its product, inlet and units in words and ids, who made it, its runs' ids), and kind train-run is one kept run of such a train (pureos/train-run/<artifact id>, read by its id or its train's: its train, product, units and product stream in words; its numbers stay in the artifact, cited by the row's ref or the evidence id pureos_build returns). Kinds: unit-operation, train, train-unit, train-run. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `proforma_read`

*read · scope: project · loose*

Read Proforma: the cost scenarios and the runs kept as artifacts: each scenario's runs, the library plants' runs, the corn stover and dry-grind corn reference plants among them, and the runs kept from the retired reference entries (a reference run, the benchmark), listed as kept (stream_table reads a run's streams; engine_report reads a library run's numbers as evidence ids). Kinds: scenario, artifact. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `biorepo_read`

*read · scope: project · loose*

Read BioRepo: the records and the extractor's candidates, by one rule (a record is an extraction a reviewer verified against its document's own words, its provenance verified, or gold where the reviewer kept a gold value; a candidate is one no reviewer has verified yet, its provenance unverified, waiting for a reviewer; one a reviewer rejected leaves every read; search_records names each hit's kind by it), the computed artifacts and the Witness runs that score the extractor. Kinds: record, candidate, artifact, witness-run. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest. Read in part: review decisions a browser has not posted yet wait in that browser.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `guild_read`

*read · scope: project · loose*

Read Guild: the people on the ledger (name, role, whether active) and the competence checks on skills; no level is stored and none is read. Kinds: person, check. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `primer_read`

*read · scope: project · loose*

Read Primer: the lessons, by module, and the skills each counts toward. Kinds: lesson. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `intake_read`

*read · scope: project · loose*

Read Intake: the documents the project holds in its literature: title, year, where each came from, its licence class and passages. Kinds: source. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### `home_read`

*read · scope: project · loose*

Read Home: what waits for a person: candidates awaiting review and open checks. Kinds: review, check, proposal. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows (a larger limit is read as 20), in the summary's rows and the result's rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance. The summary holds module, rows, count (every match), returned (the rows shown) and states (the count of every match by state), a note when rows were left out so that the result stays readable, and partial, a sentence naming what the read leaves out, when the module is read in part; narrow by ids, state or words to read the rest.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20; a larger limit is read as 20. A count. |

### What a module read answers

Each `<module>_read` answers its rows twice: as the result's `rows`, each a `ModuleRow` (`docs/api/openapi.json`), and inside its `summary`, a `ModuleRead`:

| Field | Type | Required | What it is |
|---|---|---|---|
| `module` | string | yes | The module, by the name the rail gives it (BioRepo, fermOS). |
| `count` | integer | yes | How many of the module's rows the read matches, every one. |
| `returned` | integer | yes | How many of those `rows` holds, the read's limit at most, in the order the read ranks them. |
| `states` | map to integer | yes | Every match counted by its state (open, fenced, approved, locked, proposed, retired); a state no match holds is left out. |
| `rows` | list of object | yes | The rows returned, each a ModuleRow with its module left out. |
| `note` | string or null | no | Present when rows were left out so that the result stays readable: a sentence saying so, and how to read the rest. |
| `partial` | string or null | no | Present when the read leaves part of the module out, in every read of that module: a sentence naming what the read leaves out and where that waits (module_stores.PARTIAL). BioRepo's read holds one. |

### What each kind's `detail` holds

A module row's `detail` holds the few named fields of its kind below, each text cut at 300 characters and each list at its first ten.

| Module | Kind | `detail` |
|---|---|---|
| `runbooks` | `runbook` | `kind` (industrial or research), `productId` and `strainId` (what it makes, and with which strain; null where it names none), `lockedAt` (when its predictions were locked; null while it stands open) and `predictions` (each prediction's label) |
| `runbooks` | `protocol` | `category`, `organisms` (the organisms it names), `currentVersion` and `versions` (each version it keeps) |
| `runbooks` | `deposition` | `runbookId` and `runbook` (the runbook it was deposited on, by id and title), `state` (staged, running or closed), `readings` and `confirmed` (how many readings it holds, and how many of them a person confirmed), `standing` (the readings a run may take, each as <deposition id>/<entry id>), `measures` (the measures its readings are of), `observations` (how many it holds), `startedAt`, `closedAt`, `depositedBy` (who deposited it) and `cite` |
| `runbooks` | `reading` | `reading` (its id, <deposition id>/<entry id>, the ref a measurement names), `depositionId` and `entryId`, `runbookId` and `runbook`, `measureId` and `measure` (the measure it is of, by id and label), `value` and `unit` (as the bench kept them), `at` (when it was taken), `hours` (its sample time; null for none), `depositedBy`, `deposition` (its deposition's ref) and `cite` (the quantity a run takes it as) |
| `runbooks` | `measured-evidence` | `depositionId`, `runbookId` and `runbook`, `predictionId` (the prediction it tests), `productId`, `label`, `value` and `unit`, `confirmed` (whether a person read its number back), `conditions` (what it holds true under), `deviations` (those logged beside it), `at` and `deposition` (its deposition's ref) |
| `geneos` | `host` | `bsl` (its biosafety level) and `badges` |
| `geneos` | `pathway` | `products` (what it makes) |
| `geneos` | `model` | `host` (the strain the model describes, by id) and `unavailable` (why it cannot be loaded here; null when it can) |
| `geneos` | `artifact` | `tool` (the tool that computed it), `createdAt` (when), `inputs` (its inputs given in words, each as name=value), `output` (the top-level values it computed, at most eight) and `cite` (how a claim cites its numbers) |
| `fermos` | `artifact` | `tool` (the tool that computed it), `createdAt` (when), `inputs` (its inputs given in words, each as name=value), `output` (the top-level values it computed, at most eight) and `cite` (how a claim cites its numbers) |
| `fermos` | `simulation` | `artifactId`, `family` and `title` (its model family), `strain`, `product` and `sugar`, `boundBy` (each parameter's key, grouped by what bound it), `aerobic`, `aboveCeiling` (whether its yield stands above the ceiling), `flagged` (whether it carries flags) and `cite`; its numbers stay in the artifact |
| `fermos` | `vessel` | `tool`, `createdAt`, `unitClass` (BioSTEAM's unit class) and `vesselType`, `source` and `sourceTool` (the simulation or fit it was designed for), `vessels` (how many), `volume` and `volumeUnit`, `installed` and `installedUnit` (its installed cost) and `cite` |
| `fermos` | `deposition` | `runbookId` and `runbook` (the runbook it was deposited on, by id and title), `state` (staged, running or closed), `readings` and `confirmed` (how many readings it holds, and how many of them a person confirmed), `standing` (the readings a run may take, each as <deposition id>/<entry id>), `measures` (the measures its readings are of), `observations` (how many it holds), `startedAt`, `closedAt`, `depositedBy` (who deposited it) and `cite`, with `series` (how many of its measures hold a series), `fits` (the fits made from it, by artifact id) and `keptWith` (its row in the runbooks module) |
| `pureos` | `unit-operation` | `stage`, `note` and `biosteamClasses` (the BioSTEAM classes it is) |
| `pureos` | `train` | A scenario's train, read from the scenario's newest run: `artifactId`, `scenarioId`, `flowsheet`, `product`, `productStream`, `productBasis`, `overallRecovery`, `units` (its units' ids, in run order), `runsOnFile`, `tablesSource`, `note` and `cite`. A train a model built: `trainId`, `name`, `program` (its chemical set), `product`, `inlet` (its kind, ref, stream and vessel), `units` and `unitTypes`, `recordsNamed` (each unit's parameters bound to records), `madeBy`, `agent`, `at`, `updatedAt`, `runs` (its runs' artifact ids, newest first) and `cite` |
| `pureos` | `train-unit` | `artifactId`, `unit`, `unitClass` and `operation` (the unit operation it is), `order`, `onPath` (whether the product's path passes through it), `product`, `productIn`, `productOut` and `productLost`, `lostTo` (the streams the lost product leaves by), `recovery` and `cumulative`, `massIn` and `massOut`, `note` and `unitOfMass` (the unit its masses are in) |
| `pureos` | `train-run` | `artifactId`, `tool`, `createdAt`, `trainId` and `trainName`, `product` and `productChemical`, `productStream`, `units` and `unitTypes`, `inletKind` and `inletRef`, `flagged` and `cite`; its numbers stay in the artifact |
| `proforma` | `scenario` | `kind` (the scenario's kind), `product` and `modelId` |
| `proforma` | `artifact` | `tool` (the tool that computed it), `createdAt` (when), `inputs` (its inputs given in words, each as name=value), `output` (the top-level values it computed, at most eight) and `cite` (how a claim cites its numbers) |
| `biorepo` | `record` | `paperId` (the document it was extracted from), `field` (the ontology field it measures) and `strainId` (its strain; null where its words name no strain the project holds) |
| `biorepo` | `candidate` | `paperId` (the document it was extracted from), `field` (the ontology field it measures) and `strainId` (its strain; null where its words name no strain the project holds) |
| `biorepo` | `artifact` | `tool` (the tool that computed it), `createdAt` (when), `inputs` (its inputs given in words, each as name=value), `output` (the top-level values it computed, at most eight) and `cite` (how a claim cites its numbers) |
| `biorepo` | `witness-run` | `outcomes` (how many of the run's candidates met each outcome), `falsePositives` (how many) and `models` |
| `guild` | `person` | `role` |
| `guild` | `check` | `skillIds` (the skills it checks) |
| `primer` | `lesson` | `skills` (the skills it counts toward), `minutes`, and `module` where the lesson names the module it sits in |
| `intake` | `source` | `collector` (the collector that brought it in), `licenceClass` and `passages` (how many it holds) |
| `home` | `review` | `paperId` (the document the candidate waiting for review was extracted from) |
| `home` | `check` | `skillIds` (the skills it checks) |
| `home` | `proposal` | `module` and `action` (what was asked for), `gate`, `how` (what the button does), `by` (who proposed it) and `at` |

## Module writes

### `runbooks_write`

*writes · scope: project · loose*

Write to Runbooks, through the module's own write function. Actions — draft: refused, every call (use the draft_runbook tool: it takes the evidence ids and record ids this run returned and writes every number from them); lock: lock a runbook's predictions before a run (gated) [gated: lock a prediction a person will test; becomes a proposal a person carries out on Home]; deposit: start a deposition of a protocol on the bench (gated) (fields: protocolId) [gated: send a protocol to the bench; becomes a proposal a person carries out on Home]; run: send a runbook's protocol to the bench (gated) (fields: protocolId) [gated: send a protocol to the bench; becomes a proposal a person carries out on Home]; publish: publish a runbook and its ledger to the commons (gated) [gated: publish to the commons; becomes a proposal a person carries out on Home]; revise_protocol: refused, every call (a protocol is revised by a person in the protocol editor; the service has no write function for protocols). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `geneos_write`

*writes · scope: project · loose*

Write to geneOS, through the module's own write function. Actions — ceiling: compute and keep the yield ceiling of a model on a sugar (fields: modelId, product, substrate); frontier: compute and keep the growth–product frontier of a model on a sugar (fields: modelId, product, substrate); mix: compute and keep the ceiling across a mix of two sugars (fields: modelId, product, substrate, substrateB). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `fermos_write`

*writes · scope: project · loose*

Write to fermOS, through the module's own write function. Actions — forecast: forecast a run from a kept kinetic fit and keep it (fields: fitArtifactId); fit: refused, every call (a person fits a deposition's series on fermOS's fit page, which sends it to POST /api/fermos/fit; no tool fits a kept deposition); simulate: simulate the model family named in target (batch_v1 and the rest) and keep the simulation, as fermos_simulate does: each parameter binds from a fit, the records, a kept simulation or a stated convention, and the call refuses naming each parameter nothing binds; records.<parameter key> names the record ids, comma-separated, that bind that parameter (fields: strain, product, sugar, fitArtifact, startFrom, durationPreset, records.<key>); design_vessel: design on BioSTEAM the vessel a kept simulation (or, anaerobic, a kept kinetic fit) needs and keep it, as fermos_vessel does; refused in words while its plant scale waits for a person (fields: simulationArtifact, fitArtifact, vesselType, klaMethod). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `pureos_write`

*writes · scope: project · loose*

Write to pureOS, through the module's own write function. Actions — new_train: start a train for a product (its id) from the inlet a kept artifact gives (inletRef: a kept simulation's artifact id, a kept vessel design's, or a kept run's stream as <artifact id>/<stream id>), kept on the service as the model's, as pureos_build's new does (fields: product, inletRef); add_unit: add a unit of a catalogue type to the train named in target, after the unit named (inlet for the first place; empty for the end) (fields: unitType, afterUnitId); remove_unit: take a unit out of the train named in target (fields: unitId); set_from_record: bind a unit's parameter to exactly the records named for it (records.<parameter key>, their ids separated by commas or spaces), each held to the parameter's field, the aggregate gate and its unit; refused naming a record that cannot bind and why (fields: unitId, records.<key>); run_train: run the train named in target in the Proforma worker as the service binds it and keep the run; refused naming each value that waits for a person's. pureOS's unit operations and its unit catalogue are curated (core/openferment_core/schema/vocabulary.yaml, core/openferment_core/pureos/catalogue.py); the service has no write function for them: every other call is refused in words. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `proforma_write`

*writes · scope: project · loose*

Write to Proforma, through the module's own write function. Actions — run: run the BioSTEAM scenario named in target as the service binds it and keep the run, as run_flowsheet does; refused naming the inputs that wait for a person's assumption; bind: refused, every call (a Proforma scenario's assumptions are a named person's, set on its page; a model's estimate enters a study scenario through study_scenario, with its origin). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `biorepo_write`

*writes · scope: project · loose*

Write to BioRepo, through the module's own write function. Actions — candidate: create an extraction candidate anchored to a sentence of a fetched paper (fields: paperId, sectionId, field, value, unit, quote, organism, carbonSource, method); decide: refused, every call (a review decision is a person's (biorepo.write refuses any other reviewer); say in gaps what you would decide and why); publish: publish records to the commons (gated) [gated: publish to the commons; becomes a proposal a person carries out on Home]. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `guild_write`

*writes · scope: project · loose*

Write to Guild, through the module's own write function. Actions — propose_check: propose a competence check on a person's skills (gated: a person asks for it) (fields: personId, skillIds) [gated: mark a personnel check; becomes a proposal a person carries out on Home]; record_check: refused, every call (a check is run by an assessor at the bench (/guild/checks/:id/run), one criterion at a time, and its entries are written in their name; a model may propose a check and never record one); evidence: record evidence on the ledger (gated: a person signs it) (fields: personId, skillId, kind) [gated: sign a Guild entry; becomes a proposal a person carries out on Home]; person: add or change a person on the ledger (gated) (fields: personId, name) [gated: sign a Guild entry; becomes a proposal a person carries out on Home]; policy: change the lead's Guild policy (gated) (fields: criticality, mode) [gated: sign a Guild entry; becomes a proposal a person carries out on Home]. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `primer_write`

*writes · scope: project · loose*

Write to Primer, through the module's own write function. Actions — lesson: refused, every call (a lesson is a catalogue entry kept with catalogue_write, and primer_write has no write function for one). primer_write keeps nothing and has no write function, since a lesson is a catalogue entry kept with catalogue_write: every other call is refused in words. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `intake_write`

*writes · scope: project · loose*

Write to Intake, through the module's own write function. Actions — fetch: collect the document target names (a PMCID, a DOI, PMID:..., OSTI:..., an osti.gov or yeastgenome.org address) into the project's literature; extract: extract candidates from the project's document whose documentId is target (spends on the model) [at the budget, gated: becomes a spend proposal a person carries out on Home]; add: refused, every call (a document enters the project's literature through intake_write fetch, by its identifier; a file or pasted text is added by a person on Intake). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `home_write`

*writes · scope: project · loose*

Write to Home, through the module's own write function. Actions — note: propose a notebook note a person accepts under their name (gated) [gated: write a note under a person's name; becomes a proposal a person carries out on Home]. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as its caller's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

## The gates (OF-BLD-015 §7.4)

A write tool whose module and action a gate names writes nothing: the call becomes a proposal with `state: proposed`, and Home shows it with the one button a person presses (`core/openferment_core/tools/gates.py`).

| Gate | Covers | Actions | The button |
|---|---|---|---|
| `publish` | publish to the commons | `biorepo publish`, `runbooks publish` | publish it from the module, in your name |
| `spend` | spend past the ask or the daily budget | `intake extract` | extract it when the budget allows |
| `lock` | lock a prediction a person will test | `runbooks lock` | open the runbook and press Lock predictions |
| `sign` | sign a Guild entry | `guild evidence`, `guild person`, `guild policy` | record it on Guild in your name |
| `personnel` | mark a personnel check | `guild propose_check` | ask for the check in your name |
| `bench` | send a protocol to the bench | `runbooks deposit`, `runbooks run` | start the deposition on the bench |
| `notebook` | write a note under a person's name | `home note` | accept the note; it is kept under your name |

## The MCP server

`openferment` (`core/openferment_core/mcp_server.py`, started by `.mcp.json`) lists every tool above under its own name, description and input schema, and adds `ask_postdoc` and `get_artifact`: Postdoc's loop on a question, and a kept artifact by its id. It acts in one project, the one `--project` names or else `OPENFERMENT_PROJECT`.

### `ask_postdoc`

Ask Postdoc a question. It runs its bounded loop over openFerment's tools and returns the plan: claims that carry no numbers of their own, each citing records, quoted sentences or computed values.

| Field | Type | Required | What it is |
|---|---|---|---|
| `question` | string | yes | The question, in words. |

### `get_artifact`

Read one kept artifact by its id: what was computed, from which inputs, with its provenance.

| Field | Type | Required | What it is |
|---|---|---|---|
| `id` | string | yes | The artifact's id, sixteen hex digits, as a tool's result names it (an artifactId). |

### Starting it

- Start it from the repository's root. `.mcp.json` names no project: a client appends `--project <id>` after the module, `uv run --project core --all-extras python -m openferment_core.mcp_server --project <id>` (the first `--project`, uv's, names the directory `core`), or sets `OPENFERMENT_PROJECT` in the server's environment.
- **Through a running service**: add `--service <origin>`, the running openFerment service's own address: `uv run --project core --all-extras python -m openferment_core.mcp_server --project <id> --service http://127.0.0.1:<port>`. The origin is `http://` or `https://`, the host `127.0.0.1`, `[::1]` or `localhost`, and an explicit port, with nothing after the port and no user or password: the service binds loopback, and the server sends to that address alone (`localhost` as `127.0.0.1`), through no proxy, following no redirect. Every call then goes to that service, in the project named: a tool above as `POST <origin>/api/tools/<name>` with the arguments as the client sent them, the project in `X-OpenFerment-Project` and the client's name in `X-OpenFerment-Assistant`; `ask_postdoc` as `POST <origin>/api/ask`; `get_artifact` as `GET <origin>/api/biorepo/artifacts/<id>`. In this mode the server opens no database, needs no `OPENFERMENT_DATABASE_URL`, and reads `core/.env` for `OPENFERMENT_PROJECT` alone, when `--project` names none. What it writes is what that service's `GET /api/audit` reads. An origin outside that rule is refused in words when the server starts, and every call then answers with those words; a service that does not answer is said in words at each call. A call waits up to 15 minutes for the service's answer, the longest one tool may take there, and `ask_postdoc` up to 21, Postdoc's whole loop; past that the call answers in words that the service did not answer, and the service may carry on with it.
- **In its own process**: with no `--service`, the server opens the database `OPENFERMENT_DATABASE_URL` names (its environment, then `core/.env`) at its first call, and runs every call there.
- With no project, or one its store does not hold, the server connects and answers every call with words saying which, and nothing is read or made; through a service, a project it does not hold comes back in the service's own words.
- In its own process it reads `OPENFERMENT_DATABASE_URL` and `OPENFERMENT_PROJECT` from its environment, else from `core/.env`, and `ask_postdoc` runs on the key its environment holds (`ANTHROPIC_API_KEY`); through a service, `ask_postdoc` runs on the service's own key. uv reads the proxy variables. A Python client hands the server its own environment with `VIRTUAL_ENV` taken out (`env = dict(os.environ); env.pop("VIRTUAL_ENV", None)`, then `StdioServerParameters(command="uv", args=[...], cwd=<root>, env=env)`): the SDK alone hands the server `HOME`, `PATH` and four names more, and a client run by `uv run <script>` holds its own environment's `VIRTUAL_ENV`, which the server's `uv run --project core` warns of at every start and leaves unused.
- In a fresh checkout the first start syncs core's environment with every extra from PyPI, which takes minutes; `uv sync --project core --all-extras` from the repository's root beforehand leaves a start of a few seconds. Once the environment is built the server answers `initialize` in a few seconds (about 4 s here) and opens nothing until its first call; it needs no key, and `ask_postdoc` alone spends.

### A client

- The server runs on `mcp` 2.3 (`core/uv.lock`). A client of that SDK imports `ClientSession` and `StdioServerParameters` from `mcp`, `stdio_client` from `mcp.client.stdio` and `Implementation` from `mcp.types`. It opens `stdio_client(params)` as `(read, write)` and `ClientSession(read, write, client_info=Implementation(name=..., version=...))` inside it, calls `await session.initialize()` first (2.3 sends the handshake there, and a call before it is refused as invalid request parameters), then `await session.list_tools()` and `await session.call_tool(<name>, <arguments>)`; a tool's JSON is `result.content[0].text`. 2.3 spells the SDK's fields in snake case: a result's `content`, `is_error` and `structured_content`, a listed tool's `input_schema`.
- A client runs in core's environment, `uv run --project core --all-extras python <script>` from the repository's root, or in one of its own naming `mcp>=2.3,<3` (a PEP 723 header and `uv run <script>`).
- Over MCP each tool answers one text block holding its result as JSON, its null fields left out: a tool above its ToolResult, `ask_postdoc` an `AnswerPlan`, `get_artifact` an `Artifact` (`docs/api/openapi.json` holds each schema). A tool's refusal is its ToolResult with `error` set, and `ask_postdoc`'s an `AnswerPlan` whose `declined` holds the words. A refusal the server writes itself (no project, a project its store lacks, an origin refused, a service that did not answer or refused the call, an artifact id of no artifact's shape) is `{"error": <words>}` alone for a tool and for `get_artifact`, and an `AnswerPlan` holding the question and `declined` for `ask_postdoc`, so a client reads every other key with a default. `is_error` stays false, and no `structured_content` is sent.
- A client is known by the name it declares when it connects: MCP's `clientInfo`, written `<name>/<version>`. A number it types into a quantity is that name's estimate, and every write it makes is audited under that name: the entry or the run it keeps names it as `by`, and the audit row as `who`, with agent `model`, the door in `detail.via` (`mcp` in the server's own process; `http` through a service, the door the service saw) and no `effort`, since no model of the service ran. A catalogue entry it keeps reads `<name>/<version>, over MCP` as its source in the server's own process and `<name>/<version>, at the HTTP endpoint` through a service. A client that declares no name, or only the SDK's own (`mcp` 0.1.0), is marked `an assistant over MCP`.
- No tool reads the audit: a client reads it at the service's `GET /api/audit` with the project header, the newest `limit` rows (200 unless asked, at most 500), newest last, narrowed by `action`, `target` and `who`, each matched exactly as a row names it (`?action=catalogue_write&target=skill/<id>&who=<name>/<version>`), so a write of any age is found by what it was. Each row carries its `id`, the id the write's answer named in `auditIds`; `who` is the client's `<name>/<version>` and `at` ISO 8601 in UTC, as a catalogue entry's `at` is. A row leaves its null fields out, as an answer over MCP does, so a client reads `target`, `askId` and `effort` with a default.
- An example client in this repository writes placeholder words alone: an entry named as a placeholder (`A placeholder skill`) with a note saying it is one. Its files and its writes name no real strain, species or product, since the repository ships software alone.
- The server has no offline stand-in: a client is checked against a migrated store, and `pnpm prove --keep` leaves one running behind a service, printing its address, project and database.
