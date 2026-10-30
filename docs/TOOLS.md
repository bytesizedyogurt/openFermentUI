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
and no model reads. The registry holds thirty-six names (OF-BLD-020 §3.4
added `fermos_simulate`, §4.2 `fermos_vessel`, §5.4 `pureos_build` and §7.2
`pureos_propose`); `test_tools.NAMES` is the one literal list of them in the
tests, and every other count there is derived from `WHITELIST`.

The names below are the registry's. The build document writes `runbooks.read`;
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
| `selling_price` | a seed BioSTEAM scenario's id (none since alpha 2.0 deleted the seed; stage 5 keeps scenarios), or `proforma_benchmark` | the newest kept run's price as one evidence id (the run's artifact id), with what its flowsheet leaves out; with no run on file, which inputs wait for a source as the service binds them and how a run is made; never runs a scenario |
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
The service holds no person's assumption (they are typed into Proforma's
parameter panel and kept in the browser's Durable tier; *A person's value*,
below), so the model never supplies one: an input no record binds waits, and
the call refuses naming it. A scenario made with New
scenario lives in the browser that made it and is refused in words. The run
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
reference biorefinery's (§2.2) read alike; anything else is refused in words.
Each summary row names the stream,
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

## fermOS simulates (OF-BLD-020 §3.4)

| Tool | In | Out |
|---|---|---|
| `fermos_simulate` | a model family's id (`batch_v1`, `fedbatch_v1`, `chemostat_v1`; `light_v1` refuses in words), a strain, a product and a sugar by their ids (each may be empty), `recordsByParam` (a parameter's key to the record ids that bind it, exactly those records), a kept kinetic fit's or forecast's artifact id (`fitArtifact`), `startFrom` (`records`, `fit` or `simulation:<artifact id>`) and `durationPreset` (`until-sugar-runs-out` or `fit-length`) | runs `fermos.simulate` as the service binds the family's parameters, keeps one `fermos.simulation` artifact and returns its evidence id (the artifact id; its value the product's titre at harvest), what bound each parameter in words and counts (never the value, which the artifact holds), the end state, the ceiling rows beside Yp/s in words, and the flags (a value outside its bounds by its key alone, the value and its bounds left to the artifact; a long flag cut at a sentence or clause and said to be cut; each ending at a full stop, OF-BLD-020 §3.R); or refuses with `fermos.simulate`'s own words (the 422's) naming each parameter that waits and the field that would bind it |

Offered loose, as the module tools are. Ids and words only (D13): a JSON
number anywhere refuses the call, as for every tool, and no field of its
schema is numeric (E.4‴, below). A parameter named in `recordsByParam` binds
to exactly those records: each must be in the evidence pool the switch shows,
a record of a field the parameter binds from (`ethanol_yield_substrate` for
`yps`, say; the product's own field for another product), kept by the
aggregate gate and in a unit `units.py` converts into the parameter's; one
that is not refuses the call, naming the record and why. Named records bind
ahead of a fit or a kept simulation (a person's override still wins, in the
browser), their value is Proforma's statistic over them, the basis names
each as a `record` input and says beside the value (`<key> origin`,
`records named`) that they were named. The same field rides on
`POST /api/fermos/simulate` (`SimulationRequest.recordsByParam`).

It is a free write: compute, no model money, and **at no gate** (`gates.py`
is unchanged, as for a flowsheet run). The integration is scipy's, in the
service itself (`kinetics.py`: an open-source numerical library steps the
family's rate equations forward in time), so it starts no worker; README.md
(*fermOS simulates on scipy*) has the families and where each value comes
from. It is audited like every module write,
`agent: model` with the model id, the effort and the ask id, `module:
fermos`, `action: simulate`, the family as target and the tool's name in
`detail`. The service holds no person's assumption (they are typed in fermOS →
Simulate and kept in the browser's Durable tier), so the model never supplies
one: a parameter nothing binds waits, and the call refuses naming it. The run is
`tools/writes.py`'s `run_simulation`, the same function `fermos_write`'s
`simulate` calls, so `check:tools` reads the one call to `fermos.simulate`
there.

A simulation is cited like any computed value: the tool returns it as one
`Evidence` whose id is the artifact's, so it enters `SeenSet` and a claim
citing it is kept; a claim citing a simulation no tool returned in this
conversation is dropped. `SeenSet.runs` learns every kept simulation a tool
returned, from that `Evidence` and from a `fermos_read` row
(`validate.KEPT_RUNS`): a simulation a read returned only as a row is cited by
its ref in `moduleRefs`, and a claim citing it by evidence id is dropped with
words that say so. Postdoc's prompt (rule 15) says a simulation's numbers are
read from its artifact and never stated, and the simulation is cited by its
artifact id.

**Rule 2b and E.4‴** (`check:tools`). Rule 2b's kept runs grow from
Proforma's to a `fermos.simulation`, a `fermos.vessel` and a
`pureos.train_run` artifact: every function that keeps one is found by the
same call-graph walk, never listed, and no tool file but `tools/writes.py`
reaches one. A tool file may not reach a module by name at run time either:
`__import__`, `importlib`, `sys.modules`, `vars()`, `globals()`, `locals()`
or a module's `__dict__` each fail the rule (OF-BLD-020 §3.R). Rule 6 is E.4‴: no tool named `fermos_*` or `pureos_*` has a
numeric field (`number` or `integer` anywhere in its input schema, a numeric
`enum` or `const` included); the registry's two count fields, `k` and
`limit`, at the top of an input stand aside, as `tools.numbers_in` lets them
(`fermos_read` and `pureos_read` take `limit`). `core/tests/test_check_tools.py`
plants each way round.

## fermOS's vessel (OF-BLD-020 §4.2)

| Tool | In | Out |
|---|---|---|
| `fermos_vessel` | a kept simulation's artifact id (`simulationArtifact`) or, for an anaerobic vessel, a kept kinetic fit's or forecast's (`fitArtifact`); `vesselType` (`stirred-tank` or `bubble-column`, or empty for BioSTEAM's own); `klaMethod` (a kLa correlation by the name BioSTEAM registers it and its class runs for the design, `Riet` or `Dewes`, or empty) | designs the vessel on BioSTEAM through `vessel.design` (the Proforma worker), keeps one `fermos.vessel` artifact and returns it as one evidence id (the artifact id): the vessels, volumes, times, powers, kLa, the oxygen balance in brief, heat (BioSTEAM's duty with how it found it, and the cross-check on the oxygen the simulation took up, each in the service's words) and cost with BioSTEAM's cost index, who assumed what, and the flags; or refuses in `vessel.design`'s own words |

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
design's id or the simulation's). A design is a kept run as a simulation is
(`validate.KEPT_RUNS` maps `fermos.vessel` to the `vessel` row): `SeenSet.runs`
learns it from the `Evidence` and from the row, so a design a read returned
only as a row is cited by its ref in `moduleRefs`, and a claim citing it by
evidence id is dropped with words that say so. Postdoc's prompt (rule 16)
says a vessel's numbers are read from its artifact, never stated.

The `Evidence`'s value is the number of vessels BioSTEAM sized; every other
number stays in the artifact, which the MCP server's `get_artifact` reads
whole. The design itself is BioSTEAM's, made in the Proforma
worker, and spends no model money; what it computes, and where BioSTEAM
overruled the build document, are in README.md (*fermOS sizes the vessel on
BioSTEAM*).

## pureOS builds a train (OF-BLD-020 §5.4)

| Tool | In | Out |
|---|---|---|
| `pureos_build` | `action` (`new`, `add_unit`, `remove_unit`, `set_from_record`, `run` or `propose`) and the fields that action takes, every one a string, a list of strings or a word: `product` (the product's id, `ethanol`; for `new` empty takes a simulation inlet's own product, for `propose` it is required) and `inletRef` for `new` (a simulation, a vessel design or a run's stream) and for `propose` (a simulation or a run's stream, or empty for none); `host` for `propose`; `trainId` for every other action; `unitType` (a catalogue unit type's id) and `afterUnitId` (`inlet` for the first place, empty for the end) for `add_unit`; `unitId` for `remove_unit` and `set_from_record`; `recordsByParam` (a parameter's key on the unit to the record ids that bind it, exactly those records) for `set_from_record` | `new`, `add_unit`, `remove_unit`, `set_from_record` and `propose`: the train as kept, in ids and words (its id, product, program, inlet, each unit's id, type, class and routing, how many records are named for each key, who made it, when) and `toRun`, what a run of it would refuse now in the run's own words (`train_spec.check_train`: the validation's refusals, then each value that waits and each need of a unit; empty when the run would go), with `toRunNote` saying the values were not checked, and why, when the Proforma simulator cannot answer. `run`: the run as one evidence id (the `pureos.train_run` artifact's id; its value the overall recovery of the product to the product stream), each unit's recovery and the overall to four significant digits, the product's share of the product stream, what bound each parameter counted by origin (never a value), the flags and notes cut; the whole run in `ToolResult.data`, which no model reads. A refusal is in the service's words |

The inlet a model names for `new` (`inletRef`): a kept simulation's artifact
id (its broth at harvest, D10; its broth flow then waits for a person's
value), a kept vessel design's (the harvest of the simulation it was designed
for, the broth flow read from the design), or a kept run's stream as
`<artifact id>/<stream id>` (a `proforma.run`, `proforma.reference` or
`pureos.train_run`; `stream_table` lists a Proforma run's streams). For
`propose` it is what the proposer takes (OF-BLD-020 §5.R, findings 19 and
32): a kept simulation's id or a run's stream, or empty for an inlet a person
types; a vessel design's id is refused there, and `propose` names its
product, never empty. The train
belongs to its inlet's program, else to the one active program, said so; only
the yeast program has a chemical set, and a product thermosteam's `CHEMICALS`
does not name is refused. A unit a model adds takes the catalogue's own
routing (its onward port on, every other outlet to waste) and an id of its
type's first letter and the smallest free count (`C1`, `D2`). D13 names seven
inputs; the tree adds `unitId`, the unit `remove_unit` and `set_from_record`
act on, since `afterUnitId` names where a unit goes, and `host` for `propose`
(the proposer reads where the product is made). A field the action does
not take is refused in words.

`set_from_record` binds a parameter of a unit to exactly the records named
for it, through the run's own check (`pureos.train_spec.unit_scope`): each
must be in the evidence pool the switch shows, a record of the field the
parameter's source rule names, on the train's program's papers, kept by the
aggregate gate, naming the unit's step where its field says nothing of one
(`step_recovery`, `product_purity`), in a unit the parameter reads, and, for a
per-component key, the product's own component; a record that cannot bind
refuses the call, naming it and why, and nothing changes. The check reads the
class's parameters in the Proforma worker with the store let go, and the train
is kept only if it did not change meanwhile.

`run` runs the train through `pureos.train_spec.run_train`, in the Proforma
worker, with no person's value: the service holds none, so a value nothing
binds (a flash's two settings, a column's keys, a broth flow) waits, and the
call returns the run's refusal (the 422's words) naming each one; a person
types it in pureOS → Builder. `propose` keeps the train OF-BLD-020 §7.2's
rules propose (`pureos.propose`, for `product` made in `host`, a geneOS host
id) under an id of its own, with the proposer's reasons; a proposal that
proposes nothing is refused in the words naming each missing property.

**Where a model's train lives.** A person's trains stay in their browser
(D9). A model builds across tool calls, and an outside assistant over MCP has
no ask to hold a draft, so the service keeps a model's train in
`core/data/pureos-trains.json` (`KeptTrain`: the train as data, `agent:
model`, `madeBy` the model id, `effort`, `askId`, `at`, `updatedAt`),
gitignored, on this machine alone and not on the data branch, written through
`pureos.kept.keep_train` alone: every read-modify-write under the store's
thread lock and file lock, through `atomic.write_text`.
`GET /api/pureos/trains-kept` lists them, the most recently changed first.
pureOS's index
lists them under *Made by Postdoc* (name, product, units, the model, when,
and the newest run joined by its `trainId`), and **Open a copy** opens one in
the Builder as a new train of that browser (`/pureos/build/new?copy=<id>`):
the kept train stays the model's (OF-BLD-020 §5.R).

It is a free write: BioSTEAM's compute, no model money, **at no gate**
(`gates.py` is unchanged), every action audited like every module write
(`agent: model`, the model id, the effort, the ask id, `module: pureos`, the
action as `new_train`, `add_unit`, `remove_unit`, `set_from_record`,
`run_train` or `propose_train`, the train's id as target, the tool's name in
`detail`). Each action is one function in `tools/writes.py`, the same one
`pureos_write`'s action of that name calls (below), so `check:tools` reads the
calls to `pureos.kept.keep_train` and `pureos.train_spec.run_train` there
(both in `ALLOWED_WRITES`, `pureos.kept` and `pureos.train_spec` among the
stores rule 2 polices). Rule 2b finds the kept store's writer from its file
name (`KEPT_STORES`): every function of a module naming `pureos-trains.json`
that writes through `atomic`, every function anywhere that writes through
`atomic` and names the store by its module's path function or constant
(`kept.path()`, `kept.FILE`; OF-BLD-020 §5.R, finding 18), and every function
reaching one, which no tool file but `writes.py` may reach. A tool file
writes no file itself: it may not reach `atomic.write_text` or `write_bytes`,
nor call a path's or a handle's write, a dump, a file made, moved or taken
away, or `open` with a mode that writes. Postdoc's loop never serves `pureos_build` or
`pureos_write` from its per-question cache (`postdoc_agent.UNCACHED`): a
train changes between calls, and its run is of the train as it stands. After
either goes through, the question's reads read the kept trains and the
artifacts afresh and no module read cached before it is served again
(`postdoc_agent.CHANGES_ROWS`, `module_stores.Stores.forget`; OF-BLD-020
§5.R, finding 21), so `pureos_read` finds the train and its run as they stand.

A run is cited like any computed value: its `Evidence` id is the artifact's,
so `SeenSet` keeps it, and a claim citing a run no tool returned in this
conversation is dropped. A train run is a kept run (`validate.KEPT_RUNS` maps
`pureos.train_run` to the `train-run` row): `SeenSet.runs` learns it from the
`Evidence` and from `pureos_read`'s row, so a run a read returned only as a row
is cited by its ref in `moduleRefs`, and a claim citing it by evidence id is
dropped with words that say so. Postdoc's prompt (rule 17) says a train's
numbers are read from its run's artifact and never stated.

## pureOS proposes a train (OF-BLD-020 §7.2)

| Tool | In | Out |
|---|---|---|
| `pureos_propose` | a product's id (`product`: a products seed entry, or a product thermosteam's library is asked about by name, ethanol); a host strain's id on geneOS's shelf (`host`); and optionally the train's inlet (`inletRef`: a kept fermOS simulation's artifact id, or a kept run's artifact id and one of its streams as `<artifact id>/<stream id>`; empty for none) | a train proposed by written rules (`pureos/proposer.py`): its units in order, catalogue types, each with the rule, the property it read and the artifact that holds it, in words with no number; every parameter left at its library default or waiting for a person; or nothing proposed and each missing property named. Each property read is its own evidence id (`<artifact id>:<property>`); the whole proposal is in `data` |

Offered loose, as the module tools are; every field is a string, and E.4‴
holds the schema to no numeric field. It is a read: it keeps nothing but the
property artifacts it reads (`volatility` from thermosteam in the Proforma
worker, `protparam` from Biopython's ProtParam on the sequence a products
seed entry carries, OF-BLD-020 §7.1), writes no audit line and starts no run;
the proposal goes to a person, who fills what waits in pureOS's Builder. The
rules, each with its basis, are in `proposer.py`'s docstring: a small
molecule lighter than water by thermosteam's boiling points is distilled
(`distillation`), then dried on a `molecular-sieve` where thermosteam finds a
minimum-boiling azeotrope with water; one heavier than water is extracted
(`lle`); a secreted protein is clarified (`centrifugation`), concentrated
(`uf-df`), captured and polished (`chromatography` twice, keyed on ProtParam's
isoelectric point and molecular weight, the mode waiting while the inlet
carries no pH) and spray-dried (`spray-dry`); an intracellular protein is
harvested, disrupted and clarified first; an intracellular polymer is
harvested, digested, washed and dried (`drying-drum`). The class is the
products seed's `category`, or, for a product the seed holds no entry for,
thermosteam's normal boiling point; whether a product is secreted is the
entry's `location`, which no entry carries yet, so a protein says it is
missing, as it says a sequence is. `POST
/api/pureos/propose` answers the same, and pureOS's **Propose a train** shows
it with each unit's reason beside it and keeps it under a new train id, which
the Builder opens.

## A person's value (OF-BLD-020 Phase 2)

A number a person sets for a model reaches a run one way, and no tool is on it.

1. The service declares the parameter (`params.py`) and serves it in a scope:
   `GET /api/params/{scope}` gives its value and where the value came from.
2. A person types a value into the parameter panel, under their reviewer
   name. It is an `Override` (scope, key, value, low, high, by, at, note),
   kept in that browser's Durable tier (`parameterOverrides`). The service
   keeps none. `POST /api/params/{scope}/resolve` shows what it would change
   and keeps nothing.
3. The browser sends the scope's overrides with the run, as `overrides` in the
   body of `POST /api/proforma/run`, `POST /api/fermos/vessel` or
   `POST /api/fermos/simulate`. `GET /api/proforma/bind`, the ceiling check
   and `GET /api/fermos/bind` take them as `?overrides=`. A logistic fit's
   forecast scope (`fermos:forecast:<fit id>`) travels as the forecast's own
   fields on `POST /api/fermos/forecast`: its start values, its length, and
   who typed each (`changedBy`, `durationBy`). Proforma still reads the older
   field, `assumptions`, the same way for one release.
4. The service checks each one (a real name, when it was typed, a number or
   one of the offered words, a parameter whose rule takes a person's value, a
   value inside its own low and high) and refuses one that fails, in words. A
   person's value wins over the records and any fit for its parameter. The
   run's basis names it as an `assumption` by that person, so the run is
   `demo`.

No tool takes a person's value, and no tool input carries an override: tool
inputs carry ids and words. `run_flowsheet`, `proforma_write`'s `run`,
`fermos_simulate`, `fermos_write`'s `simulate`, `fermos_vessel`,
`fermos_write`'s `design_vessel`, `pureos_build`'s `run` and `pureos_write`'s
`run_train` run as the service binds the scenario, the simulation, the design
or the train, with no person's value, so an input that waits for one refuses
the call, naming it. `proforma_write`'s `bind` is refused (the
table below).

## The read tools (OF-BLD-015 §7.2)

One a module: `runbooks_read`, `geneos_read`, `fermos_read`,
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

**fermOS reads its simulations** (OF-BLD-020 §3.4). `fermos_read` holds three
kinds: `artifact` (the growth fits and forecasts), `simulation`, one row a
kept `fermos.simulation`, ref `fermos/simulation/<artifact id>`, labelled with
its family and strain, `open` and `computed`, its mark worked out from its
inputs when it is read, and a `detail` of words, ids and flags alone (its
family, title, strain, product and sugar, which keys each source bound, whether
it is aerobic, whether its Yp/s is above a ceiling): its numbers stay in the
artifact; and `vessel` (§4.2), one row a kept `fermos.vessel` design, ref
`fermos/vessel/<artifact id>`, found by its own id or its simulation's,
labelled with BioSTEAM's class and the vessel type, `open` and `computed`, its
mark worked out from its inputs when it is read; its `detail` names the class,
the vessel type and the source, and copies from the artifact the number of
vessels, each vessel's volume and the installed cost.

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
row. This is a kind of the existing read, not a tool of its own. Since
OF-BLD-020 §5.4 kind `train` also holds the trains a model built with
`pureos_build` (`pureos/train/<train id>`, found by the train's id or a run's:
its product, program, inlet, units and the keys records are named for, in ids
and words, who made it and when, and its runs' ids; no mark, since a train is
data), and kind `train-run` is one kept `pureos.train_run`
(`pureos/train-run/<artifact id>`, found by its own id or its train's),
labelled with its train's name and product, `open` and `computed`, its mark
worked out from its inputs when it is read, and a `detail` of words, ids and
flags alone: its numbers stay in the artifact. Proforma's
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
| `open` | free to use, read or make | a draft or running runbook; a host, pathway, model or unit operation in the catalogue; an artifact, a kept simulation, and a train or a unit of one read from a run; a train a model built, and a run of one; an active person; a scheduled check |
| `fenced` | held back | a runbook `blocked_unverified`; a fetch that failed; a model not fetched |
| `approved` | a person or a source stands behind it | a record `measured`, `gold`, `verified` or `curated`; a protocol's current version; a lesson; a paper fetched with full text |
| `locked` | frozen for a test | a runbook with `lockedAt`; a check run |
| `proposed` | waits for a person | a candidate `unverified`; a runbook `needs_review` or `awaiting_budget`; a check proposed; a proposal at a gate; a paper waiting to be fetched |
| `retired` | withdrawn | a record rejected; a person inactive; a check dismissed |

Read in part: depositions, runbooks adopted or locked in a browser, and
review decisions not yet posted stay in that browser. The footer names the
modules it holds for.

## thermosteam answers property questions (OF-BLD-019 §4.2)

The thirtieth name, added by the build document's authority (OF-BLD-019
Part C.8 and §4.2), before Proforma's two (§6.1), which brought the registry
to thirty-two (OF-BLD-020 §3.4's `fermos_simulate` is the thirty-third,
§4.2's `fermos_vessel` the thirty-fourth, §5.4's `pureos_build` the
thirty-fifth and §7.2's `pureos_propose` the
thirty-sixth);
`check:tools` (rule 5) fails when a name in `WHITELIST` has no tool registered
or no mention here.

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
computed value. `POST /api/thermo/props` asks and
`GET /api/thermo/props` reads the stored answer to the same question (or
`{"artifact": null}`), starting no simulator; pureOS → Train and fermOS show
it in a **Properties** card.

## The write tools (OF-BLD-015 §7.3)

The pair of each read: `runbooks_write` … `home_write`. One input for all:
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
| `fermos_write` | `simulate` | simulates the model family named in `target` as the service binds it, the same run as `fermos_simulate` (`run_simulation`); `fields` carry `strain`, `product`, `sugar`, `fitArtifact`, `startFrom`, `durationPreset` and `records.<parameter key>` (record ids, separated by commas or spaces), any other field refused; refuses naming each parameter that waits | `fermos.simulate` |
| `fermos_write` | `design_vessel` | designs the vessel a kept simulation (or, anaerobic, a kept fit) needs on BioSTEAM, the same design as `fermos_vessel` (`design_vessel`); fields `simulationArtifact` or `fitArtifact`, `vesselType`, `klaMethod`; refuses in words while no plant scale (or, aerated, one vessel's batch volume) is given, which only a named person types in fermOS → Vessel | `vessel.design` |
| `pureos_write` | `new_train`, `add_unit`, `remove_unit`, `set_from_record`, `run_train` | builds and runs a train as `pureos_build`'s `new`, `add_unit`, `remove_unit`, `set_from_record` and `run` do, the same function an action; the train in `target` (empty for `new_train`), the rest in `fields`: `product` and `inletRef`; `unitType` and `afterUnitId`; `unitId`; `unitId` and `records.<parameter key>` (record ids, separated by commas or spaces); any other field refused; a run refuses naming what waits | `pureos.kept.keep_train`, `pureos.train_spec.run_train` |
| `proforma_write` | `run` | runs the BioSTEAM scenario named in `target` as the service binds it, the same run as `run_flowsheet` (`run_scenario`); refuses naming what waits, an empty target, or a scenario the service does not hold | `proforma.run` |
| `proforma_write` | `bind` | refused: an assumption is a named person's, typed into the parameter panel and kept in the browser's Durable tier (*A person's value*, above) | — |
| `biorepo_write` | `candidate` | anchors a candidate to a sentence of a fetched paper, `unverified`, in the review queue; id `mw1-…`, kept in `candidates/hand/` apart from the extractor's file, so it never counts as an extraction; fields the action lists only, `negativeResult` and `isPrimary` as the word true or false | `extract.add_candidate` (§2.4's rules) |
| `biorepo_write` | `decide` | refused: a decision is a person's | — |
| `intake_write` | `fetch` | fetches and prepares a corpus paper's full text | `intake.fetch_paper` |
| `intake_write` | `extract` | extracts a fetched paper; at the budget, a `spend` proposal | `extract.extract_paper` |
| `intake_write` | `add` | refused: a source enters through a person's approval | — |
| `runbooks_write` | `draft` | refused: use `draft_runbook` | — |
| `runbooks_write` | `revise_protocol` | refused: protocols are seed, revised in the browser | — |
| `guild_write` | `record_check` | refused: an assessor runs a check at the bench, criterion by criterion | — |
| `guild_write`, `home_write`, `runbooks_write` | gated actions | a proposal (below) | `proposals.propose` |
| `primer_write` | any | refused: no write function | — |
| `pureos_write` | any other | refused: the unit operations and the unit catalogue are curated (`src/data/vocabulary.ts`, `pureos/catalogue.py`), no write function | — |

A refusal is a result Postdoc reports in `gaps`.

## The gates (OF-BLD-015 §7.4)

The table is `core/openferment_core/tools/gates.py`; this is the same table
for a person. An action here writes nothing: the call becomes a proposal
(`core/data/proposals.json`, `GET /api/proposals`) with `state: proposed`,
and Home shows it as a card with one button. Adding a gate is a row in both
places.

| Gate | Covers | Actions | The button |
|---|---|---|---|
| `publish` | publish to the commons | `biorepo publish`, `runbooks publish` | takes the person to the module to publish in their name |
| `spend` | spend past the ask or the daily budget | `intake extract` when the budget refuses | the server extracts when the budget allows |
| `lock` | lock a prediction a person will test | `runbooks lock` | takes the person to the runbook to press Lock predictions |
| `sign` | sign a Guild entry | `guild evidence`, `guild person`, `guild policy` | takes the person to Guild to record it in their name |
| `personnel` | mark a personnel check | `guild propose_check` | the server asks for the check in the person's name, by the Guild person the browser acts as (`checks.request`) |
| `bench` | send a protocol to the bench | `runbooks deposit`, `runbooks run` | takes the person to the protocols to start the deposition |
| `notebook` | write a note under a person's name | `home note` | the server keeps the note under the person's name (the notebook itself lands with OF-BLD-017 §5.3) |

No gate covers a Proforma run (OF-BLD-019 §6.1): `run_flowsheet` and
`proforma_write`'s `run` keep one `proforma.run` artifact in the open lane and
spend no model money, so `gates.py` and this table are unchanged by them. Nor
a simulation (OF-BLD-020 §3.4): `fermos_simulate` and `fermos_write`'s
`simulate` keep one `fermos.simulation` artifact the same way. Nor a vessel
design (§4.2): `fermos_vessel` and `fermos_write`'s `design_vessel` keep one
`fermos.vessel` artifact the same way, and BioSTEAM's design spends no model
money. Nor a train (§5.4): `pureos_build` and `pureos_write`'s train actions
keep a model's train on the service and its runs as `pureos.train_run`
artifacts, spending no model money.

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
thirty-eight in all. `test_mcp` counts them from `WHITELIST`, and holds
`run_flowsheet`, `stream_table`, `fermos_simulate` and `pureos_propose` to the
registry's own descriptions and schemas.
