# The tools

<!-- Written by `pnpm gen:tools` (core/openferment_core/tools/reference.py) from the registry in
core/openferment_core/tools/. Edit a tool's registration, never this file: `pnpm check:tools` fails
when the two differ. -->

One registry, three callers: Postdoc's loop, the HTTP endpoints (`GET /api/tools`, `POST
/api/tools/{name}`) and the MCP server (`openferment`) run every tool through `tools.run`, so a rule
the registry holds, it holds for each of them.

- **Inputs** carry ids, words and quantities (ADR-006). A number stands only inside a quantity, an
  object of `value` and `unit` (and `low` and `high` for a range), where a tool asks for one; a
  number anywhere else, outside the count fields `k` and `limit`, refuses the call. The service
  writes each quantity's origin from who called: the answering model's estimate with its id, or the
  named person's assumption (`?by=` at the HTTP endpoint); a quantity nobody can be named for is
  refused.
- **Outputs** are a summary a model reads, at most 9,000 characters, and beside it what a
  claim may cite (records, passages, evidence, module rows); the whole of a large output travels in
  `data`, which no model reads.
- **Scope**: every tool acts in one project (ADR-005): the request's, the question's, or the one the
  MCP server was started in.
- **Writes**: a tool marked *writes* keeps something new in the project, audited as its caller's,
  through `tools/writes.py`; a read keeps nothing but the computations it caches.

43 tools.

## The registry

| Tool | Family | Kind | Scope |
|---|---|---|---|
| `search_records` | Records | read | project |
| `convert_units` | Units | read | project |
| `search_passages` | Literature | read | project |
| `yield_ceiling` | geneOS | read | project |
| `growth_forecast` | fermOS | read | project |
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

## Records

### `search_records`

*read · scope: project · strict*

Search the records Postdoc may cite: the candidates extracted from the project's documents that nobody rejected, gold or verified where a reviewer promoted one and unverified otherwise. Returns at most ten, best match first, each with its record id, paper, what was measured, its value and unit as the paper wrote them, the quoted sentence, the strain, the carbon source when the paper states one, and its provenance. Filter by an ontology field id and by a strain id, or pass null for no filter. Returns none when nothing matches.

| Field | Type | Required | What it is |
|---|---|---|---|
| `query` | string | yes | Words to search the records for: what was measured, the organism, the product, the feed. |
| `field` | string or null | yes | An ontology field id to keep only records of that field, or null for any field. |
| `organism` | string or null | yes | A strain id to keep only records on that strain, or null for any organism. |
| `limit` | integer | yes | How many records to return, at most 10. A count. |

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

List what the library shelf runs: the biorefineries plants with an entry point and openFerment's own flowsheets, each with its configurations, the configuration a run takes when none is named, and the package a flowsheet is composed from. Narrow by words. Returns ids and words, nothing to cite.

| Field | Type | Required | What it is |
|---|---|---|---|
| `words` | string | no | Words to narrow the shelf by: a product, a feedstock, a plant's name; empty for all. |
| `limit` | integer | no | How many rows at most. A count. |

### `engine_parameters`

*read · scope: project · loose*

A plant's parameters as the package builds it: each key with its label, its unit, its group and the library's default, and the bounds it is held to. A scenario sets a parameter by its key in that unit. Narrow by words. The first call builds the plant in the simulator and may take half a minute.

| Field | Type | Required | What it is |
|---|---|---|---|
| `plant` | string | yes | A plant's id, as engine_plants gives it. |
| `configuration` | string | no | One of the plant's configurations; empty for its own. |
| `words` | string | no | Words to narrow the parameters by; empty for all. |
| `limit` | integer | no | How many rows at most. A count. |

### `engine_run`

*writes · scope: project · loose*

Run a plant from the library shelf at the library's defaults, or a study scenario (by its id) with the values it sets, as an engine run: kept in the project, marked as yours, with the SFF file it writes. Returns the run's id, its artifact id, its provenance (assumed when a value it set is an estimate or an assumption), the values it set with their origins, and each number its price and its flowsheet's outputs hold as an evidence id to cite. The same plant and values asked again answer from the run kept. A plant that refuses the values is kept as a receipt and refused in the plant's words.

| Field | Type | Required | What it is |
|---|---|---|---|
| `plant` | string | no | A plant's id, run at the library's defaults; empty when a scenario is named. |
| `configuration` | string | no | One of the plant's configurations; empty for its own. |
| `scenario` | string | no | A study scenario's id (study_scenario returns it), run on its plant with its values. |
| `note` | string | no | Why the run is asked for, in words. |

### `engine_report`

*read · scope: project · loose*

Read a kept engine run by its id: what ran, the values it set with their origins, its provenance, and each number its price and its flowsheet's outputs hold as an evidence id to cite; for a refused run, the plant's own words.

| Field | Type | Required | What it is |
|---|---|---|---|
| `run` | string | yes | A kept run's id, as engine_run or study_read gives it. |

## Studies

### `study_scenario`

*writes · scope: project · loose*

Keep a study scenario on a plant from the library shelf: a title, the plant and its configuration, and the values it sets, each a parameter's key and a quantity (value and unit, the parameter's own unit) with a note saying in words what the value rests on. Each value is marked as your estimate, with your model id, and a run of the scenario is assumed. Checked against the plant's parameters: a key it does not read, a unit it does not use or a value of the wrong kind is refused before anything is kept. The same plant and values are one scenario. Run it with engine_run.

| Field | Type | Required | What it is |
|---|---|---|---|
| `title` | string | yes | What the scenario asks, in words. |
| `plant` | string | yes | A plant's id, as engine_plants gives it. |
| `configuration` | string | no | One of the plant's configurations; empty for its own. |
| `values` | list of `ScenarioValueIn` | yes | The parameters it sets, each a quantity in the parameter's own unit with a note saying what the value rests on; every other parameter keeps the library's default. |
| `note` | string | no | Why the scenario, in words. |

`QuantityIn`: A number you type: a value in a unit, and in words what it rests on. The service marks it with who typed it.

| Field | Type | Required | What it is |
|---|---|---|---|
| `value` | number | yes | A number of the quantity, marked as its caller's. |
| `unit` | string | yes | The value's unit, as the tool names it. |
| `note` | string | no | What the value rests on, in words. |

`ScenarioValueIn`

| Field | Type | Required | What it is |
|---|---|---|---|
| `key` | string | yes | The parameter's key, as engine_parameters gives it. |
| `quantity` | `QuantityIn` | yes | The value, in the parameter's own unit, with what it rests on. |

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

The minimum selling price the most recent kept run of one of the project's BioSTEAM scenarios produced, as one evidence id to cite: the median with its 5th to 95th percentile, the infeasible share, which inputs rest on an assumption, and what the flowsheet leaves out. Refuses when no run is on file, naming the inputs still waiting for a source and how a run is made. With proforma_benchmark it returns the stored benchmark instead: the NREL 2011 corn stover ethanol design's minimum ethanol selling price as biorefineries.cornstover computes it. It cannot run a scenario or make an assumption.

| Field | Type | Required | What it is |
|---|---|---|---|
| `scenarioId` | string | yes | The id of a BioSTEAM scenario the project keeps (proforma_read lists them), whose newest kept run it reads; or proforma_benchmark, the NREL 2011 corn stover ethanol design as biorefineries.cornstover builds it. |

### `run_flowsheet`

*writes · scope: project · loose*

Run one of the project's BioSTEAM scenarios as its page runs it, and keep the run: one artifact holding the minimum selling price across the inputs' ranges, the cost breakdown, the sensitivity and the base case's stream, unit and utility tables. Returns one evidence id to cite (the run's artifact id), the median price with its 5th to 95th percentile, how each input is bound and the cost lines. Takes a scenario id and nothing else: you never type an assumption, a value or a setting. The run reads the assumptions a named person set on the scenario's page and the fermOS fits chosen for it; an input that neither a record nor such an assumption binds waits, and the call then refuses and names the inputs that wait, and nothing runs. It spends no model money and is at no gate; the run is marked as yours in the audit log until a person promotes it. A run can take minutes.

| Field | Type | Required | What it is |
|---|---|---|---|
| `scenarioId` | string | yes | The id of a BioSTEAM scenario the project keeps; proforma_read lists them. Nothing else: no value, no assumption, no setting. |

### `stream_table`

*read · scope: project · loose*

Read the stream table a kept Proforma run holds: every stream of the base case with the unit it leaves and the unit it enters (none for a feed or a product), its phase, temperature, pressure, mass flow, price and largest components, as BioSTEAM held them after the run. Takes the run's artifact id and nothing else (a scenario's proforma.run artifact, or a reference biorefinery's proforma.reference artifact); you never type a number. The plant's feeds and products come first; a long table is cut to what a model may read and says how many streams it left out. Returns the run's evidence id to cite: a price, a cost or a recovery read from a run is cited by it. It runs nothing.

| Field | Type | Required | What it is |
|---|---|---|---|
| `artifactId` | string | yes | The artifact id of a kept Proforma run: a proforma.run artifact (a scenario's run, as run_flowsheet, selling_price or proforma_read return it) or a proforma.reference artifact (a reference biorefinery's run, as proforma_read lists it). Nothing else: no number, no stream, no setting. |

## fermOS

### `growth_forecast`

*read · scope: project · strict*

Forecast a run like a fitted one: biomass, product and substrate as bands for readings, from a kept kinetic fit's artifact id, under the fitted run's own starting values and length. Returns one evidence id to cite and the final values as intervals. A fit whose growth rate or ceiling was not identified is refused with what run would identify it.

| Field | Type | Required | What it is |
|---|---|---|---|
| `fitArtifactId` | string | yes | The artifact id of a kept kinetic fit (tool kinetic_fit). |

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
| `artifactId` | string | yes | A Proforma run's artifact id (tool proforma.run), with streamId; or an empty string. |
| `streamId` | string | yes | One stream of that run's stream table, by its id; or an empty string. |
| `preset` | string | yes | ethanol-water-azeotrope (the composition thermosteam's own vapour-liquid equilibrium gives), or beer-at-titre-of with recordId (water and ethanol at that record's titre); or an empty string when a stream is named. |
| `recordId` | string | yes | An ethanol titre record's id (field ethanol_titre), for beer-at-titre-of; or an empty string. |

## Runbooks

### `draft_runbook`

*read · scope: project · strict*

Draft a runbook from what this run found: a title, a product id and a strain id, items that each name one evidence id or a field with record ids returned earlier in this run, and measures (label, unit, one of start, mid-run, harvest, after recovery, and the item label they test). Send no numbers: the service writes each prediction's value and interval from the evidence and the records. A person adopts and locks it.

| Field | Type | Required | What it is |
|---|---|---|---|
| `title` | string | yes | What the runbook tests, in words with no number. |
| `productId` | string | yes | A product id. |
| `strainId` | string | yes | A strain id. |
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

Read Runbooks: the runbooks (their status, lock and what they predict) and the protocols (their versions). Kinds: runbook, protocol. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state. Read in part: the project's depositions and measurements are kept with it and shown on the Runbooks page; this read lists its runbooks and protocols.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `geneos_read`

*read · scope: project · loose*

Read geneOS: the hosts, the pathways, the genome-scale models on the shelf and the ceilings computed on them. Kinds: host, pathway, model, artifact. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `fermos_read`

*read · scope: project · loose*

Read fermOS: the growth fits and forecasts computed from deposited runs (kind artifact), the kept simulations of a model family (kind simulation: its family, strain, product and sugar, and what bound each parameter, in words; its numbers stay in the artifact, cited by the row's ref or the evidence id fermos_simulate returns), and the vessels BioSTEAM designed for kept simulations (kind vessel, read by the design's artifact id or the simulation's). Kinds: artifact, simulation, vessel. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state. Read in part: the project's depositions are kept with its runbooks; this read lists what the service computed: fits, forecasts, simulations and vessel designs.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `pureos_read`

*read · scope: project · loose*

Read pureOS: the downstream unit operations, by stage (each with the BioSTEAM classes it is), and the trains Proforma's runs simulated (kind train, one a scenario: read by the scenario id or the run's artifact id); kind train-unit is one unit of a train, in run order, with the product in and out and the recovery read from the run's stream table. Kind train also holds the trains a model built with pureos_build (read by the train's id: its product, inlet and units in words and ids, who made it, its runs' ids), and kind train-run is one kept run of such a train (pureos/train-run/<artifact id>, read by its id or its train's: its train, product, units and product stream in words; its numbers stay in the artifact, cited by the row's ref or the evidence id pureos_build returns). Kinds: unit-operation, train, train-unit, train-run. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `proforma_read`

*read · scope: project · loose*

Read Proforma: the cost scenarios and the runs kept as artifacts: each scenario's runs and the reference biorefineries' runs (stream_table reads a run's streams). Kinds: scenario, artifact. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `biorepo_read`

*read · scope: project · loose*

Read BioRepo: the records, the extractor's candidates, the computed artifacts and the Witness runs that score the extractor. Kinds: record, candidate, artifact, witness-run. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state. Read in part: review decisions a browser has not posted yet wait in that browser.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `guild_read`

*read · scope: project · loose*

Read Guild: the people on the ledger (name, role, whether active) and the competence checks on skills; no level is stored and none is read. Kinds: person, check. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `primer_read`

*read · scope: project · loose*

Read Primer: the lessons, by module, and the skills each counts toward. Kinds: lesson. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `intake_read`

*read · scope: project · loose*

Read Intake: the documents the project holds in its literature: title, year, where each came from, its licence class and passages. Kinds: source. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

### `home_read`

*read · scope: project · loose*

Read Home: what waits for a person: candidates awaiting review and open checks. Kinds: review, check, proposal. Pass ids or refs, words, a kind and a state to narrow; pass an empty list and empty strings to list the module. Returns at most 20 rows, each with its ref (cite it in moduleRefs), label, state (open, fenced, approved, locked, proposed, retired; computed by the service), the module's own status word and its provenance; and the count of every match by state.

| Field | Type | Required | What it is |
|---|---|---|---|
| `ids` | list of string | yes | Ids or refs (`<module>/<kind>/<id>`) to read, or an empty list. |
| `words` | string | yes | Words to search the module for, or an empty string for no word search. |
| `kind` | string | yes | One of the module's kinds, named in the tool's description, or an empty string for every kind. |
| `state` | one of empty, `open`, `fenced`, `approved`, `locked`, `proposed`, `retired` | yes | One of open, fenced, approved, locked, proposed, retired; or an empty string for every state. |
| `limit` | integer | yes | How many rows to return, at most 20. A count. |

## Module writes

### `runbooks_write`

*writes · scope: project · loose*

Write to Runbooks, through the module's own write function. Actions — draft: draft a runbook: use the draft_runbook tool, which writes the numbers from the evidence; lock: lock a runbook's predictions before a run (gated) [gated: lock a prediction a person will test; becomes a proposal a person carries out on Home]; deposit: start a deposition of a protocol on the bench (gated) (fields: protocolId) [gated: send a protocol to the bench; becomes a proposal a person carries out on Home]; run: send a runbook's protocol to the bench (gated) (fields: protocolId) [gated: send a protocol to the bench; becomes a proposal a person carries out on Home]; publish: publish a runbook and its ledger to the commons (gated) [gated: publish to the commons; becomes a proposal a person carries out on Home]; revise_protocol: draft a protocol revision (fields: protocolId, change). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `geneos_write`

*writes · scope: project · loose*

Write to geneOS, through the module's own write function. Actions — ceiling: compute and keep the yield ceiling of a model on a sugar (fields: modelId, product, substrate); frontier: compute and keep the growth–product frontier of a model on a sugar (fields: modelId, product, substrate); mix: compute and keep the ceiling across a mix of two sugars (fields: modelId, product, substrate, substrateB). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `fermos_write`

*writes · scope: project · loose*

Write to fermOS, through the module's own write function. Actions — forecast: forecast a run from a kept kinetic fit and keep it (fields: fitArtifactId); fit: fit a deposited run's series (fields: depositionId); simulate: simulate the model family named in target (batch_v1 and the rest) and keep the simulation, as fermos_simulate does: each parameter binds from a fit, the records, a kept simulation or a stated convention, and the call refuses naming each parameter nothing binds; records.<parameter key> names the record ids, comma-separated, that bind that parameter (fields: strain, product, sugar, fitArtifact, startFrom, durationPreset, records.<key>); design_vessel: design on BioSTEAM the vessel a kept simulation (or, anaerobic, a kept kinetic fit) needs and keep it, as fermos_vessel does; refused in words while its plant scale waits for a person (fields: simulationArtifact, fitArtifact, vesselType, klaMethod). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `pureos_write`

*writes · scope: project · loose*

Write to pureOS, through the module's own write function. Actions — new_train: start a train for a product (its id) from the inlet a kept artifact gives (inletRef: a kept simulation's artifact id, a kept vessel design's, or a kept run's stream as <artifact id>/<stream id>), kept on the service as the model's, as pureos_build's new does (fields: product, inletRef); add_unit: add a unit of a catalogue type to the train named in target, after the unit named (inlet for the first place; empty for the end) (fields: unitType, afterUnitId); remove_unit: take a unit out of the train named in target (fields: unitId); set_from_record: bind a unit's parameter to exactly the records named for it (records.<parameter key>, their ids separated by commas or spaces), each held to the parameter's field, the aggregate gate and its unit; refused naming a record that cannot bind and why (fields: unitId, records.<key>); run_train: run the train named in target in the Proforma worker as the service binds it and keep the run; refused naming each value that waits for a person's. pureOS's unit operations and its unit catalogue are curated (schema/vocabulary.yaml, core/openferment_core/pureos/catalogue.py); the service has no write function for them: every other call is refused in words. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `proforma_write`

*writes · scope: project · loose*

Write to Proforma, through the module's own write function. Actions — run: run the BioSTEAM scenario named in target as the service binds it and keep the run, as run_flowsheet does; refused naming the inputs that wait for a person's assumption; bind: bind an assumption to a scenario input (fields: key, value, basis). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `biorepo_write`

*writes · scope: project · loose*

Write to BioRepo, through the module's own write function. Actions — candidate: create an extraction candidate anchored to a sentence of a fetched paper (fields: paperId, sectionId, field, value, unit, quote, organism, carbonSource, method); decide: accept, reject or correct a record (fields: recordId); publish: publish records to the commons (gated) [gated: publish to the commons; becomes a proposal a person carries out on Home]. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `guild_write`

*writes · scope: project · loose*

Write to Guild, through the module's own write function. Actions — propose_check: propose a competence check on a person's skills (gated: a person asks for it) (fields: personId, skillIds) [gated: mark a personnel check; becomes a proposal a person carries out on Home]; record_check: mark a check's outcome (refused: an assessor runs a check at the bench) (fields: checkId); evidence: record evidence on the ledger (gated: a person signs it) (fields: personId, skillId, kind) [gated: sign a Guild entry; becomes a proposal a person carries out on Home]; person: add or change a person on the ledger (gated) (fields: personId, name) [gated: sign a Guild entry; becomes a proposal a person carries out on Home]; policy: change the lead's Guild policy (gated) (fields: criticality, mode) [gated: sign a Guild entry; becomes a proposal a person carries out on Home]. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `primer_write`

*writes · scope: project · loose*

Write to Primer, through the module's own write function. Actions — lesson: write or change a lesson (fields: lessonId). Primer holds no lessons yet, and the service has no write function for them: every other call is refused in words. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `intake_write`

*writes · scope: project · loose*

Write to Intake, through the module's own write function. Actions — fetch: collect the document target names (a PMCID, a DOI, PMID:..., OSTI:..., an osti.gov or yeastgenome.org address) into the project's literature; extract: extract candidates from the project's document whose documentId is target (spends on the model) [at the budget, gated: becomes a spend proposal a person carries out on Home]; add: add a new source to the corpus (fields: doi). Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

### `home_write`

*writes · scope: project · loose*

Write to Home, through the module's own write function. Actions — note: propose a notebook note a person accepts under their name (gated) [gated: write a note under a person's name; becomes a proposal a person carries out on Home]. Pass action, target (an id), fields (names to words) and note (why). What is written lands in the open lane marked as the model's, in the audit log, until a person promotes it; a refusal says why, and goes in gaps.

| Field | Type | Required | What it is |
|---|---|---|---|
| `action` | string | yes | One of the actions in the tool's description. |
| `target` | string | yes | The id or ref the action is on (a paper id, a scenario id, a runbook id), or an empty string. |
| `fields` | map to string | yes | What the action needs, by the names in the tool's description, as words and ids; a value copied from a quote is a string. Empty when the action takes none. |
| `note` | string | yes | Why, in your own words; kept on the audit line and the proposal. |

## The gates (OF-BLD-015 §7.4)

A write tool whose module and action a gate names writes nothing: the call becomes a proposal with `state: proposed`, and Home shows it with the one button a person presses (`tools/gates.py`).

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

`openferment` (`core/openferment_core/mcp_server.py`, started by `.mcp.json`) lists every tool above under its own name, description and input schema, and adds `ask_postdoc` and `get_artifact`: Postdoc's loop on a question, and a kept artifact by its id. It acts in one project, the one `--project` names or else `OPENFERMENT_PROJECT`, and a number an outside assistant types into a quantity is marked as an estimate by `an assistant over MCP`.
