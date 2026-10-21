# The tools

One registry (`core/openferment_core/tools/__init__.py`), three callers:
Postdoc's loop, `GET /api/tools` and `POST /api/tools/{name}`, and the MCP
server (`core/openferment_core/mcp_server.py`). A tool is in `WHITELIST` or
it does not exist. Every input carries ids and words: a JSON number anywhere
outside `k` and `limit` refuses the call, and every refusal is a result with
`error` set. A summary over 9,000 characters is replaced by an error, and
`data` is emptied with it; a tool whose whole output is longer
(`stream_table`) cuts its own summary, says how much it left out, and carries
the whole in `ToolResult.data`, which the endpoint and the MCP server return
and no model reads. The registry is closed at thirty-three names;
`test_tools.NAMES` is the one literal list of them in the tests, and every
other count there is derived from `WHITELIST`.

The names below are the registry's. The build document writes `dominion.read`;
the Messages API refuses a dot in a tool name, so the registry uses an
underscore.

## The seven (OF-BLD-014)

| Tool | In | Out |
|---|---|---|
| `search_records` | words, a field id, a strain id, a limit | records Postdoc may cite |
| `convert_units` | a record id, a unit | a computed value, kept as an artifact |
| `search_passages` | words, k | up to six passages, each citable by a whole sentence |
| `yield_ceiling` | a model on geneOS's shelf, a product, a sugar | one evidence id, or a finding in words |
| `growth_forecast` | a kept kinetic fit's artifact id | one evidence id and the final values as intervals |
| `selling_price` | a seed BioSTEAM scenario's id the switch shows (`sc-yeast-1`; `sc-pha-1` too with it on), or `proforma_benchmark` | the newest kept run's price as one evidence id (the run's artifact id), with what its flowsheet leaves out; with no run on file, which inputs wait for a source as the service binds them and how a run is made; never runs a scenario |
| `draft_runbook` | a title, a product, a strain, items by evidence or field, measures | a draft whose numbers the service wrote |

## Proforma's two (OF-BLD-019 §6.1)

| Tool | In | Out |
|---|---|---|
| `run_flowsheet` | a scenario id, nothing else | runs the scenario as the service binds it through `proforma.run`, keeps one `proforma.run` artifact and returns its evidence id (the artifact id), the median price with its 5th to 95th percentile, each input's binding and the cost lines; or refuses with `proforma.run`'s own words (the 422's) naming the inputs that wait |
| `stream_table` | a run's artifact id (`proforma.run` or `proforma.reference`) | the base case's stream table, the plant's feeds and products first, cut to the cap with the number of streams left out; the whole table in `ToolResult.data`; the run's evidence id |

Both go out loose, as the module tools do. `run_flowsheet` is a free write:
it spends no model money, and **it is at no gate** (`gates.py` is unchanged:
a run keeps one artifact in the open lane, as a ceiling does). It is audited
like every module write, `agent: model` with the model id, the effort and the
ask id, `module: proforma`, `action: run`, and the tool's name in `detail`.
The service holds no person's assumption (they are typed in Proforma and kept
in the browser's Durable tier), so the model never supplies one: an input no
record binds waits, and the call refuses naming it. A scenario made with New
scenario lives in the browser that made it and is refused in words, as is an
authored cost surface and, with the switch off, an archived scenario. The run
is `tools/writes.py`'s `run_scenario`, the same function `proforma_write`'s
`run` calls, so `check:tools` reads the one call to `proforma.run` there; its
rule 2b fails when any other tool file reaches what keeps a Proforma run or
writes an audit line itself. What does is found, not listed (§6.R): every
function of the service that calls `artifacts.compute` for a `proforma.run`,
`proforma.reference` or `proforma_benchmark` artifact (or for a tool the check
cannot name) or `audit.append`, and every function that reaches one of those,
followed through imports as rule 2 follows them; `proforma.run_flowsheet`,
the run endpoints and `proposals.propose` are among them. A tool file may
also not call `artifacts.compute` for a run, hand a store module around bare
or import by name at run time. `core/tests/test_check_tools.py` plants each
way round in a copy of the package.

`selling_price` reads, and never runs: the newest kept run of a seed BioSTEAM
scenario (`proforma.latest_run`), cited by its artifact id, with what the
run's flowsheet leaves out read from the shelf. With no run on file it names
the inputs that wait as `proforma.bound` binds them now and says a person
makes the run in Proforma (or `run_flowsheet`, when nothing waits). An
authored cost surface keeps no run, an id the seed lacks lives in the browser
that made it, and a reference biorefinery's run is read through
`proforma_read` and `stream_table`; each is refused in words that say so.

`stream_table` reads through `proforma.tables_of`, so a scenario's run and a
reference biorefinery's (§2.2) read alike; anything else is refused in words,
as is an archived run with the switch off. Each summary row names the stream,
the unit it leaves and the unit it enters (none for a feed or a product), its
phase, T, P, mass flow, price and largest components, to four significant
digits; `data` holds every number as the run kept it.

A run is cited like any computed value: both tools return it as one
`Evidence` whose id is the artifact's (a scenario's run is its median price,
a reference run the price its package gives on its own defaults), so it
enters `SeenSet` and a claim citing it is kept, and a claim citing a run no
tool returned in this conversation is dropped. Postdoc's prompt (rule 8)
says a price, a cost or a recovery read from a run cites that run's evidence
id.

## fermOS's vessel (OF-BLD-020 §4.2)

| Tool | In | Out |
|---|---|---|
| `fermos_vessel` | a kept simulation's artifact id (`simulationArtifact`) or, for an anaerobic vessel, a kept kinetic fit's or forecast's (`fitArtifact`); `vesselType` (`stirred-tank` or `bubble-column`, or empty for BioSTEAM's own); `klaMethod` (a kLa correlation by the name BioSTEAM registers it and its class runs for the design, `Riet` or `Dewes`, or empty) | designs the vessel on BioSTEAM through `vessel.design` (the Proforma worker), keeps one `fermos.vessel` artifact and returns it as one evidence id (the artifact id): the vessels, volumes, times, powers, kLa, the oxygen balance in brief, heat and cost with BioSTEAM's cost index, who assumed what, and the flags; or refuses in `vessel.design`'s own words |

Offered loose, as the module tools are; every field is a string, an empty
one meaning "none", and E.4‴ holds the schema to no numeric field. It is a
free write at no gate, audited like every module write (`agent: model`,
`module: fermos`, `action: design_vessel`, the tool's name in `detail`), and
it is `tools/writes.py`'s `design_vessel`, the function `fermos_write`'s
`design_vessel` action calls, so the one call to `vessel.design` stays where
`check:tools` reads it (`vessel.design` is in `ALLOWED_WRITES`, and `vessel`
among the stores rule 2 polices). A design needs a plant scale or one
vessel's batch volume, a named person's assumption typed in fermOS → Vessel;
the service holds none, so without one the tool returns the refusal's words
and Postdoc says in gaps that the design waits for a person. The vessel type
and the kLa correlation a call names are conventions of that request, named
in the basis; a person's choice of either in the panel is an assumption by
them, and the two must agree. A design is cited like any computed value: its
`Evidence` id is the artifact's, so `SeenSet` keeps it, and a claim citing a
design no tool returned in this conversation is dropped. `fermos_read`'s kind
`vessel` lists the kept designs (`fermos/vessel/<artifact id>`, read by the
design's id or the simulation's). Postdoc's prompt (rule 15) says a vessel's
numbers are read from its artifact, never stated.

## The read tools (OF-BLD-015 §7.2)

One a module: `dominion_read`, `runbooks_read`, `geneos_read`, `fermos_read`,
`pureos_read`, `proforma_read`, `biorepo_read`, `guild_read`, `primer_read`,
`intake_read`, `home_read`. One input for all: `ids` (ids or refs), `words`,
`kind` (one of the module's kinds, or empty), `state` (one of the enum, or
empty), `limit` (at most 20). One output, `ModuleRow`: `ref`
(`<module>/<kind>/<id>`, what a claim cites in `moduleRefs`), `label`,
`state`, `status` (the module's own word), `provenance` (the mark, or null),
`detail`. The count of every match by state rides on the summary, and a
module read in part says so. An artifact row's `provenance` is worked out
when the row is read, by `basis_provenance` over its inputs as they stand
then, never copied from the stored file: a record rejected since it was
computed brings the row, and a claim citing it, down with it.

**pureOS reads trains** (OF-BLD-019 §4.1). `pureos_read` holds three kinds:
`unit-operation` (the vocabulary, each with the BioSTEAM classes that perform
it), `train` (the newest Proforma run of a scenario, one row a scenario, its
id the scenario's, or the run's artifact id when no scenario claims the run)
and `train-unit` (one unit of a train, id `<train>:<unit>`, in run order).
A read by a scenario id or a run's artifact id returns the train and every
unit of it; `kind: train-unit` narrows to the units. Every number in a train
row's `detail` (product in and out, what is lost and to which outlet, the
recovery, the cumulative share still on the path) is read by
`pureos.train_of` from the run artifact's stream table, never typed and never
simulated again; the row's mark is the run's, worked out as for any artifact
row. This is a kind of the existing read, not a tool of its own. Proforma's
rows list every scenario's runs and, since §6.1, the reference biorefineries'
runs (`proforma.reference`). `GET /api/pureos/trains` and
`GET /api/pureos/train/{key}` serve the same reading to the browser, the
mark worked out the same way (§4.R). A unit whose passes BioSTEAM keeps
apart (an `HXprocess`) is credited only on the pass that carries the product
on, and product that enters a unit on the path and leaves by no outlet is
lost there.

Before round one, `module_stores.coverage` sweeps every module for what the
question names and hands the model the map. A follow-up is swept with the
earlier questions it reads (at most four), never with the earlier answers,
which are the model's words, and the map then says what the conversation
names.

`state` is one enum, computed by `module_stores.py` from the module's own
word and never by a model:

| State | Means | Computed from |
|---|---|---|
| `open` | free to use, read or make | a clearance of `clear-expired` or `clear-none`; a draft or running runbook; a host, pathway, model or unit operation in the catalogue; an artifact, and a train or a unit of one read from a run; an active person; a scheduled check |
| `fenced` | held back | a clearance of `watch-*`, `blocked` or `unknown` (Dominion's action for it is to run clearance first); a runbook `blocked_unverified`; a fetch that failed; a model not fetched |
| `approved` | a person or a source stands behind it | a record `measured`, `gold`, `verified` or `curated`; a protocol's current version; a lesson; a paper fetched with full text |
| `locked` | frozen for a test | a runbook with `lockedAt`; a check run |
| `proposed` | waits for a person | a candidate `unverified`; a runbook `needs_review` or `awaiting_budget`; a check proposed; a proposal at a gate; a paper waiting to be fetched |
| `retired` | withdrawn | a record rejected; a person inactive; a check dismissed |

Read in part: depositions, runbooks adopted or locked in a browser, and
review decisions not yet posted stay in that browser. The footer names the
modules it holds for.

## thermosteam answers property questions (OF-BLD-019 §4.2)

The thirtieth name, added by the build document's authority (OF-BLD-019
Part C.8 and §4.2), before Proforma's two (§6.1), which close the registry at
thirty-two; `check:tools` (rule 5) fails when a name in `WHITELIST` has no
tool registered or no mention here.

| Tool | In | Out |
|---|---|---|
| `thermo_props` | a Proforma run's artifact id and one of its stream ids; or the preset `ethanol-water-azeotrope`; or `beer-at-titre-of` with an ethanol titre record's id (every field a string, an empty one meaning "not this") | one evidence id a property thermosteam answered (density, heat capacity, viscosity, bubble point, dew point), the mixture's mass fractions and conditions, and the library's version; a chemical the library lacks refused in words |

Offered loose, as the module tools are. A question carries ids and words;
the service fills every number (`core/openferment_core/thermo.py`): a
stream's composition, temperature, pressure and phase are its row of the
run's stream table, and the run is a source of the answer; the azeotrope is
the composition at which the library's own vapour-liquid equilibrium gives a
vapour of the liquid's composition, at the library's default pressure; a
beer is water and ethanol at the record's titre, read through `units.py` into
kg m⁻³ and solved in the worker for the mass fraction that holds that much
ethanol in a cubic metre of the mixture at its own density (the beer's cells,
residual sugar and dissolved CO2 are not in it, and the answer says so). A
temperature or pressure nobody gave is the library's own Stream default,
said so. The Proforma worker asks thermosteam (op `thermo_props`); the answer
is one `thermo_props` artifact whose basis names the library and its version,
with provenance from `basis_provenance`: `computed` for the azeotrope, the
weakest of that and the record's or the run's otherwise (`demo` for a run
resting on an assumption). Each property is its own `Evidence`, id
`<artifact id>:<property>`, which `SeenSet` keeps and a claim cites like any
computed value. With the switch off, a run of an archived program is refused
as its train is hidden. `POST /api/thermo/props` asks and
`GET /api/thermo/props` reads the stored answer to the same question (or
`{"artifact": null}`), starting no simulator; pureOS → Train and fermOS show
it in a **Properties** card.

## The program switch (OF-BLD-016 §2.3, §3.3)

Casein (threads A–O) and PHA (thread P) are archived programs; yeast ethanol
(thread Q) is active (`src/data/programs.ts`, `programs.py`). Whether a run
sees the archived two is not a tool input, and no model sets it. It rides in
`ToolContext.include_archived`, set by whatever started the run:

| Caller | Where the switch comes from |
|---|---|
| Postdoc's loop | `AskRequest.includeArchived` on `/api/ask` and `/api/ask/stream`; the browser sends Settings → Programs' switch with every question |
| `POST /api/tools/{name}` | the query parameter `?includeArchived=true`; the body is the tool's input, and no input carries the switch |
| the MCP server | `OPENFERMENT_INCLUDE_ARCHIVED` in its environment (unset: off), never a client |

Off is the default everywhere. A tool input that names `includeArchived`
(`geneos_read` sent it, say) is refused like any field the tool does not
take. With the switch off:

- `search_records` reads an evidence pool with every record and candidate
  on a thread A–P paper left out, counted in `EvidencePool.hidden`.
- `search_passages` drops archived passages from each ranking before
  fusion, reading past `DEPTH` so a ranking still holds `DEPTH`.
- Every read tool's rows are tagged in the store with the program they
  belong to (`module_stores.Row.program`, as the browser's `programOf`
  resolves it; an artifact by what its inputs name: a record's paper, a
  model's host, a product), and archived rows are left out. A row asked for
  by id says which archived program holds it. A Proforma run (a scenario's
  or a reference biorefinery's) belongs to its scenario's program, its
  flowsheet's on the shelf and what its basis names, an archived one winning
  (`module_stores.artifact_program`, which asks `pureos.program_of`; §6.R).
  It is one rule for every reader of a run: `proforma_read`, `biorepo_read`,
  `GET /api/biorepo/artifacts`, pureOS's trains, `stream_table` and
  `thermo_props` (the last two refuse it by id through
  `module_stores.hidden_run_refusal`), so a PHA run that bound no record is
  PHA's everywhere. The MCP server's own `get_artifact` is outside the rule:
  it reads any kept artifact by its id, whatever the switch says.
- The coverage pass before round one fills `CoverageMap.archived` when the
  question names something archived; the trace reads *found in archived
  program PHA (hidden)*, no hidden row's ref reaches the model, and the
  code writes a gap naming the switch.
- With the switch off, `yield_ceiling`, `selling_price`, `run_flowsheet`,
  `stream_table` and `draft_runbook` refuse an archived model, product,
  scenario, run or strain with *archived (hidden)* and name Settings →
  Programs, and no tool's description or schema
  names an archived model, product or scenario (`programs.archived_target`,
  `offered`; §2.R). `growth_forecast` reads the browser's run and the write
  tools are filtered by nothing beyond the pool they read.

**Examples.** A seed runbook, protocol, scenario or lesson that describes a
run nobody made carries `example: true` in its row's `detail`. The browser
hides examples with the archived programs, and so do the read tools: with the
switch off no read returns an example row (§4.R); with it on, a read returns
them marked, so it can say a runbook is an example. The coverage pass does not
count an example as an archived program's row.

## The write tools (OF-BLD-015 §7.3)

The pair of each read: `dominion_write` … `home_write`. One input for all:
`action`, `target` (an id), `fields` (names to words), `note` (why). A write
tool never touches a store: each action calls the module's own write
function, where the module's rules live, and `check:tools` fails when this
file reaches a file or a store function `ALLOWED_WRITES` does not name. It
reads `writes.py` as parsed Python and follows every name through its import,
aliases included, so `from ..biorepo import write as keep` is caught as
`biorepo.write`; a store module handed around bare, `getattr` on one, and
`importlib` or `__import__` fail too. Every write that goes through lands in the open lane
and is appended to the audit log (`core/data/audit.jsonl`, `GET /api/audit`)
with `agent: model`, the model id (the one answering the run, after any
fallback), the effort and the ask id. A call from `POST /api/tools/{name}` or
the MCP server belongs to no ask, and its line carries `askId: null`. A
person's carry-out or dismissal is appended the same way. A geneOS write that
ends in a finding (a feed the model cannot take up) keeps nothing and is
audited as `finding`.

| Tool | Action | What happens | Through |
|---|---|---|---|
| `geneos_write` | `ceiling`, `frontier`, `mix` | computes and keeps an artifact; returns an evidence id | `geneos.ceiling` and kin |
| `fermos_write` | `forecast` | forecasts from a kept fit and keeps it | `fermos.forecast_run` |
| `fermos_write` | `fit` | refused: a deposition's series lives in the browser | — |
| `fermos_write` | `design_vessel` | designs the vessel a kept simulation (or, anaerobic, a kept fit) needs on BioSTEAM, the same design as `fermos_vessel` (`design_vessel`); fields `simulationArtifact` or `fitArtifact`, `vesselType`, `klaMethod`; refuses in words while the plant scale waits for a person | `vessel.design` |
| `proforma_write` | `run` | runs the BioSTEAM scenario named in `target` as the service binds it, the same run as `run_flowsheet` (`run_scenario`); refuses naming what waits, an empty target, or a scenario the service does not hold | `proforma.run` |
| `proforma_write` | `bind` | refused: an assumption is a named person's, in the Durable tier | — |
| `biorepo_write` | `candidate` | anchors a candidate to a sentence of a fetched paper, `unverified`, in the review queue; id `mw1-…`, kept in `candidates/hand/` apart from the extractor's file, so it never counts as an extraction; fields the action lists only, `negativeResult` and `isPrimary` as the word true or false | `extract.add_candidate` (§2.4's rules) |
| `biorepo_write` | `decide` | refused: a decision is a person's | — |
| `intake_write` | `fetch` | fetches and prepares a corpus paper's full text | `intake.fetch_paper` |
| `intake_write` | `extract` | extracts a fetched paper; at the budget, a `spend` proposal | `extract.extract_paper` |
| `intake_write` | `add` | refused: a source enters through a person's approval | — |
| `runbooks_write` | `draft` | refused: use `draft_runbook` | — |
| `runbooks_write` | `revise_protocol` | refused: protocols are seed, revised in the browser | — |
| `guild_write` | `record_check` | refused: an assessor runs a check at the bench, criterion by criterion | — |
| `guild_write`, `home_write`, `runbooks_write` | gated actions | a proposal (below) | `proposals.propose` |
| `dominion_write`, `pureos_write`, `primer_write` | any | refused: curated seed, no write function | — |

A refusal is a result Postdoc reports in `gaps`.

## The gates (OF-BLD-015 §7.4)

The table is `core/openferment_core/tools/gates.py`; this is the same table
for a person. An action here writes nothing: the call becomes a proposal
(`core/data/proposals.json`, `GET /api/proposals`) with `state: proposed`,
and Home shows it as a card with one button. Adding a gate is a row in both
places.

| Gate | Covers | Actions | The button |
|---|---|---|---|
| `publish` | publish to the commons | `biorepo publish`, `dominion publish`, `runbooks publish` | takes the person to the module to publish in their name |
| `spend` | spend past the ask or the daily budget | `intake extract` when the budget refuses | the server extracts when the budget allows |
| `lock` | lock a prediction a person will test | `runbooks lock` | takes the person to the runbook to press Lock predictions |
| `sign` | sign a Guild entry | `guild evidence`, `guild person`, `guild policy` | takes the person to Guild to record it in their name |
| `personnel` | mark a personnel check | `guild propose_check` | the server asks for the check in the person's name, by the Guild person the browser acts as (`checks.request`) |
| `bench` | send a protocol to the bench | `runbooks deposit`, `runbooks run` | takes the person to the protocols to start the deposition |
| `notebook` | write a note under a person's name | `home note` | the server keeps the note under the person's name (the notebook itself lands with OF-BLD-017 §5.3) |

No gate covers a Proforma run (OF-BLD-019 §6.1): `run_flowsheet` and
`proforma_write`'s `run` keep one `proforma.run` artifact in the open lane and
spend no model money, so `gates.py` and this table are unchanged by them.

A proposal is carried out or dismissed by a named person (the reviewer name
in Settings; placeholders are refused), and each carries their name and the
time. `POST /api/proposals/{id}/carry-out` and `/dismiss` take `{person,
reason, actingId}`: `actingId` is the Guild person the browser is acting as,
and a check is asked for by them, because Guild knows people by id and the
reviewer name is words; with none, a check proposal is refused in words. The
model may propose a check and may never record or sign one: no gate's server
action signs anything, and `guild record_check` is refused. A server gate is
marked done only when its server action ran; one with none is refused and
stays open to be dismissed. The store's locks are let go while the action
runs (the proposal is marked running in the service), so a long extraction
never holds up another proposal.

The rules a proposal holds to (OF-BLD-016 §1.R, as `proposals.propose`, `_held_to_rule_one` and
`shown` have them on 2026-10-20):

- **Rule 1.** Its note, target, field values, title and why hold no number
  (`validate.find_number`), and its target is one id or none. A write that
  breaks either is refused whole, never repaired, and the model reports the
  refusal in `gaps`. The title is the code's words and the target's id; a
  spend proposal's why is the code's words, not the budget's figures.
- **One of a kind.** One ask makes one open proposal per module, action and
  target; a second (a restart, a call worded otherwise) is refused naming
  the one waiting. Once it is carried out or dismissed, the ask may propose
  it again.
- **Who a check names is never shown before it is run.** A Guild proposal's
  title names nobody. `GET /api/proposals` (`proposals.listed`) and
  `home_read` serve it without its note, why and target, and keep its field
  ids, as Guild's checks serve theirs; the store keeps every word. Home shows
  it to the lead and assessors alone (`mayQueue`), never to the person it
  names (`shownTo`), through `shownProposals` in `src/lib/proposals.ts`.
- **Not filtered by program.** A proposal is work waiting for a person, so
  Home's card lists every open one whatever the program switch says (the
  service double's lock proposal names `rb-brazzein`, an example runbook).

## The MCP server

`core/openferment_core/mcp_server.py` lists `tools.infos()` and calls
`tools.run`, so every tool above, with its marks, refusals and gates, is what
Claude Desktop or Claude Code sees, plus `ask_postdoc` and `get_artifact`:
thirty-five in all. `test_mcp` counts them from `WHITELIST`, and holds
`run_flowsheet` and `stream_table` to the registry's own descriptions and
schemas.
