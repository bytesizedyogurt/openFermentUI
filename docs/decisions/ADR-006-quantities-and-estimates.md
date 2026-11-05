# ADR-006 — Typed quantities with origins replace Rule 1

- **Status**: accepted (requirement: the owner reopened Rule 1 and asked for labelling)
- **Date**: 2026-10-30

## Context

Rule 1 at `alpha-1.0` forbids any number of model origin: `validate_plan` drops a claim whose text
holds a digit, prompt rules 5, 8, 9, 12 and 15–17 forbid numbers and estimates, and
`tools.numbers_in` refuses any JSON number in a tool input outside `k` and `limit`. The revised
white paper and the development plan allow a clearly identified estimate whose origin and limits
stay visible.

## Decision

Every number a model, a person or a library supplies enters as
`Quantity {value, unit, basis?, low?, high?, origin}` with
`Origin {kind: record | artifact | person-assumption | model-estimate | measurement | library-default | convention, ref, by, at, note}`
(`measurement`, a deposition's reading, joined the list on 2026-11-03: the implementation note of that day).

- Provenance is computed from origins by code (`basis_provenance`, `weakest_provenance`, the
  client's display of the server's answer), never set by a model or a person.
- A model-originated number is an estimate: it carries the model id; it makes any result that rests
  on it `assumed` (the old `demo` code, renamed); it never enters a record store; it is never
  averaged into evidence; it is marked wherever it appears.
- Claims carry numbers only in a typed `values` list. Text with a bare number is still dropped and
  counted.
- Tool inputs carry numbers only inside `Quantity` objects.

## Consequences

- `PROVENANCE_ORDER` renames `demo` to `assumed`; `basis_provenance` treats `model-estimate` like
  `assumption`; `binding.exclusion` keeps estimates and computed values out of aggregates; the
  figure encoding gains the `assumed` mark.
- A negative test plants a model estimate at each record-store boundary and watches the refusal
  (acceptance A6).
- Evaluations check the distinction between a labelled estimate and a number presented as a
  measurement.

## Revisit condition

A task needs a formal decision rule or uncertainty method; it is justified and evaluated for that
task (development plan §8).

## Evidence

- `core/openferment_core/postdoc_agent.py`, `validate.py`, `tools/__init__.py` (`numbers_in`) at
  `alpha-1.0`; development plan §2 "A conflict we need to resolve deliberately" and §8 "Make
  estimates useful and honest".

## Implementation

### 4.4 (2026-10-30): `demo` renamed `assumed`

- The class is renamed everywhere it is written: `Provenance` and `PROVENANCE_ORDER` in
  `models.py` (still ninth and weakest), `weakest_provenance`'s answer for a class it does not
  know, `basis_provenance`, and on the browser's side the `Provenance` union, `PROVENANCE_RANK`,
  the tick (`tick-assumed`), the legend, the figure encoding (`ENCODING.assumed`, still amber,
  hollow and short-dashed, and one of the two classes in `NEVER_EVIDENCE`), the CSV disclosure
  and every screen that names it. The label reads *Assumed · not measured*. `check:plan` holds
  the two vocabularies equal and `check:figures` holds the encoding.
- Rows already stored are rewritten by migration 0003 (`db/alembic/versions/0003_assumed.py`):
  every text column named `provenance`, and in every JSON column of the schema the value of
  every key named `provenance`; nothing else in a row changes. An artifact whose output named
  the class has its output hash computed again over the output as rewritten, so a replay
  compares like with like; artifact ids hash the inputs, which name no provenance, and runbook
  lock hashes cover predictions' values and measures, which name none, so both stay. The
  downgrade renames it back. `test_db.py` moves a database from 0002 to 0003 and back.
- Alpha 1.0's files say `demo`: `import_alpha1` reads every `provenance` through
  `models.renamed_provenance` (the map `RENAMED_PROVENANCE`) before a model checks it, and gives
  an artifact whose output changed the hash of its output as read, as the migration does.
- The lesson embed `chip-demo` (a demonstration of a citation chip), the `demo.py` the tests'
  stand-ins came from and the kit's demo corpus keep their names: none is the class.

### 4.4 (2026-10-30): quantities with origins, a model's estimate, the record stores' refusal

- `models.Origin {kind, ref, by, at, note}` with the six kinds this record names: a
  person-assumption or a model-estimate names its author (`by`), a record, an artifact or a
  library default names what it was read from (`ref`). `Quantity` gains `basis`, `low`, `high` and
  `origin`, all optional; a quantity with none of them is written exactly as before (a wrap
  serializer drops them), so stored outputs keep their hashes and stored records their rows. The
  browser's `Quantity`, `Origin`, `OriginKind` and `OverrideOrigin` mirror them (`check:plan`
  pairs `Origin`).
- A basis source may be a `model-estimate` (`basis.estimate_source`: the model's id in `by`, the
  moment in its note). `basis_provenance` makes anything resting on one `assumed`, as it does an
  `assumption` (`ASSUMED_KINDS`); `basis.origin_of` reads any basis source as its origin, the day
  stamped in its note included.
- An `Override` carries `origin`: `person-assumption` (the default, as every override was) or
  `model-estimate`, whose `by` names the model. `params.checked` holds a person's name to the
  reviewer rule and a model's to one line; `_from_override` and the library runner take their
  source from `basis.override_source`; the panel's chip reads `model-estimate` (`ParamOrigin`), and
  every reader of a run's basis (Proforma's sampling, fermOS's and pureOS's read-back, the vessel
  design, the composite, the tools' words) reads an estimate where it reads a person's value. The
  sourceRule entry `assumption` (a value set for the run may set this parameter) admits both.
- `binding.exclusion` (and the browser's `aggregateExclusion`) keeps an `assumed` value out of
  every aggregate.
- No record store takes an estimate: `basis.refuse_estimates` finds an origin or a source of kind
  `model-estimate`, or a provenance `assumed`, anywhere in what a store is asked to keep, and
  BioRepo (`WriteRefused` rule `estimate`, a dry run included), the candidates store and a
  project's depositions and measurements (`StateRefused`) refuse it before writing.
  `test_estimates.py` plants one at each and watches the refusal (A6), and shows an estimate
  reaching a library run (whose basis names the model and which is `assumed`), a parameter panel
  and a scenario's overrides.
- Unchanged on purpose: `BasisSource` and `BasisInput` gain no field, so every artifact id stays
  what it was (§7.4); ParamOrigin and the sourceRule keep the word `assumption` for a person's
  value, the name ADR-006 gives it being `person-assumption` in `Origin`.

### 6.2 (2026-10-30): numbers in claims and in tool inputs

- A claim carries its numbers in `values` (`models.ClaimValue`: a label in words, a `Quantity`
  with its origin, and the id it was read from). The plan names each value's one source: a computed
  value a tool returned (`evidenceId`), a record a tool returned (`recordId`), or the answering
  model's estimate (`estimate`: a finite value, a unit, a low and a high when it has a range, and
  in `basis` what it rests on, in words). `validate.claim_values` reads the number of an evidence or
  a record from it, never from the plan, writes an estimate's origin as `model-estimate` with the
  model that wrote the plan and the moment, and cites the evidence or record a value is read from
  with the claim. A claim stating an estimate is `assumed`. A value with no single source, an id no
  tool returned, a label or a basis holding a number, or an estimate outside its own range drops
  its claim, counted with its reason; text with a bare number is dropped as before.
- A tool's input carries a number only inside a quantity, an object of `value` and a string
  `unit` (and `low` and `high`), standing where the tool's input schema asks for one
  (`tools.quantity_paths`; `study_scenario`'s values alone today): `tools.numbers_in` lets those
  through and refuses every other number but `k` and `limit`, so a module write's `fields` that
  hold a value and a unit in words stay words. The registry writes each quantity's origin from who called
  (`ToolContext.author`, `tools.stamped`): the answering model's estimate with its id, the person
  `POST /api/tools/{name}?by=` names, or, over MCP, an estimate by `an assistant over MCP`; it keeps
  the note the caller wrote and nothing else of what the caller put there, and refuses a quantity
  nobody can be named for. A study scenario's values arrive this way (`study_scenario`).
- The prompt's rules say so (5, 8, 9, 18 to 20), the plan schema carries `values`, and the answer
  screen shows each value with where it came from, an estimate under the assumed mark with the
  model that made it and what it rests on (`AnswerPlanView`'s `ClaimValues`).
- `check:tools` rule 6 holds every tool's input schema to the same line: a number at the count
  fields or a quantity's value and range, and none at all in a fermOS or pureOS tool (E.4‴).

### 8.5 (2026-10-31): a review decision's provenance is computed

- `biorepo.provenance_of` computes the class a decision gives its record from what the decision
  is: `gold` for a verified decision with a gold value, `verified` for any other verified one, and
  `unverified` for a rejection, a withdrawal or a correction left unverified. `biorepo.write`
  stores that class whatever label the request carried, a dry run answers with it, and
  `import_alpha1` computes it for every decision it carries from alpha 1.0.
- The evidence pool (`evidence_pool.candidate_record`) gives a decided candidate the computed
  class, the corrected value and the re-anchored sentence, so an accepted record reaches Postdoc
  and Home as `verified`. Before 8.5 it reached them as the extractor wrote it, `unverified`.
- The browser's `provenanceOf` reads a decided record by the same rule; `test_evidence_pool.py`
  holds the service's.

### Alpha 2.2 C.4 (2026-11-03): a Proforma run bases a model's estimate as an estimate

- A Proforma run's value whose origin is `model-estimate` binds as the model's estimate: its
  basis source is `model-estimate`, the model's id its `by` and the day it was estimated in its
  note (`basis.estimate_source`), and the run's sensitivity reads the input's source kind as
  `model-estimate`. Until C.4 the binding based it as a person's assumption naming the model
  (`basis.assumption_source`). Either way the run is `assumed`. A run a model set a value of is
  therefore kept afresh under a new id when asked again, its output moving where the sensitivity
  reads the kind; the earlier artifact stands and replays as it was (`docs/PROGRESS.md`,
  Departures). A model's id on two lines is refused in words at Proforma's door, a blank one by
  the request's own origin (`core/tests/test_proforma_overrides.py`).

### Alpha 2.2 C.5 (2026-11-03): the measurement origin

- `OriginKind` gains `measurement` (the alpha 2.2 prompt's §6.3): a reading a person deposited at
  the bench, its `ref` the reading's id (`<deposition id>/<entry id>`), its `at` the time the
  reading was taken and its `by` the person who deposited it. `Origin`'s validator requires the
  ref in that form and the time; a request form (`EngineInput`, `ScenarioValue`, a tool's
  quantity) may leave the time and the depositor to the service, which fills both from the
  deposition. `OverrideOrigin` and `ParamOrigin` gain it and `Override` gains `ref`, so a reading
  travels through every resolver as a person's value does, and every door that takes values
  admits it: a study scenario (`study_scenario`'s quantity among them), fermOS, pureOS, Proforma,
  the library and the contract engines.
- The lookup (`measurements.py`, reached through `basis.resolved`: `basis.override_of` calls it for
  each value it converts, a contract engine's run and a study scenario for theirs) reads the
  project's depositions rows before anything runs and holds a reading to its rules. The
  deposition and its entry are the project's own. A person confirmed the entry's number. The entry
  is the reading that stands for its measure: a later entry on the same measure with no time of
  its own corrects an earlier one with none, and a reading in a series is its own, corrected by a
  later entry at its time alone; a later entry still waiting to be read back corrects it too, and
  the refusal says the newer number waits. The deposition names the person who deposited it: a
  browser with no name set in Settings keeps its rows as `this browser`, and a reading kept so, or
  under a placeholder name (`biorepo.reviewer_refusal`), is no measurement. The entry holds a
  number in a unit and the time it was taken. The value and unit sent are the entry's own, with no
  low, high or basis. The depositor and the time are the row's maker and the entry's, filled where
  the value leaves them out and refused where it names others; at the tool door a caller names the
  reading alone, and a depositor or a time written in its origin is refused in words. The entry's
  unit is the parameter's, or converts into it through `units.convert` to a finite number, the
  conversion stated in the value's note. Each refusal is in words, a 422 at a route and an error
  from a tool, and nothing runs.
- A reading's basis source is a `deposition` naming it (`basis.measurement_source`): its id the
  ref, its `by` the depositor and its note `measured on <at>` with any conversion.
  `basis.origin_of` reads it back as a `measurement`. A deposition source naming a whole series
  (the readings a kinetic fit is made on) reads back as the bench's record, as it did, and the
  fit's provenance stays what it was.
- Provenance (`basis.basis_provenance`): `assumed` when any input is a person's assumption or a
  model's estimate, or rests on one; else `measured` when any input is a measurement; else the
  weakest of its sources' classes, as before. The package's own run carries neither label: it is
  `computed`. This follows the plan's D7 and the prompt's §6.3 (no input a person's assumption or
  a model's estimate), and it has a consequence the owner should see: a reading beside a record of
  a weaker class (`unverified`, `user`, `industry-estimate`) or beside an artifact computed with no
  assumption leaves the run `measured`, the first class of `PROVENANCE_ORDER`, so a claim citing
  such a run ranks above gold while an unverified record stands in its basis; the basis keeps each
  record with its class for a reader to weigh (`core/tests/test_basis.py` holds the rule). The prompt's §3 words a measured
  run as one resting on "measurements and records alone"; the owner may settle that wording
  against §6.3's, and the rule moves with a new note (`docs/PROGRESS.md`, Departures).
- `basis.SET_KINDS` names the source kinds of a value a run sets: a person's assumption, a model's
  estimate and a deposition, of which the one a run sets is a reading (a deposition naming a whole
  series is the record a kinetic fit rests on); every reader asks `basis.is_set`, which holds a
  deposition to being a reading (`is_measurement`). `SET_ORIGINS` and `SET_PARAM_ORIGINS` name the
  same three as an origin and a parameter's value name them. Every reader of "a value this run set"
  reads them: the values a library run hands its worker, its regression gate and its SFF file, a
  run's parameters, the comparisons, Proforma's sampling, fermOS's, pureOS's and the vessel's
  read-back, the composite and the tools' words. `engine_report`'s parameter evidence reads each
  parameter's own origin word, so a person's value there is `assumed` and a reading `measured`.
- The service holds a reading's unit to the parameter's, and nothing in the run checks that the
  reading measured the quantity the parameter is: which measure stands for which parameter is the
  scenario maker's choice, kept as the scenario's `by` (the proof's walk pairs a placeholder
  reading with a placeholder parameter by unit alone). A later pass may tie a runbook's measure to
  the parameters it may set.
- No artifact id moves: a basis that names no reading is written as it was
  (`core/tests/test_engine_pins.py`).
- What a person chooses from: `GET /api/depositions/readings?unit=` lists the readings the
  lookup's rules let a run take in that unit, each with the runbook and the measure it was
  recorded against, its value and unit, the time it was taken and its depositor, its value in the
  asked unit beside its own (`measurements.readings`). NewScenarioDialog, opened from a run's page,
  offers them beside a typed value for each parameter a person sets and sends a chosen one as
  `{kind: measurement, ref}`; a run's page reads a measurement in words, linked to the deposition
  its reading was recorded in, and the parameter's chip says measured. No store holds a protocol
  in this build, so the bench also records readings against a locked runbook's measures alone,
  with no protocol's steps (`DepositionBench`, `/runbooks/depositions/<id>/bench`), once the person
  has set their name in Settings. The proof's walk deposits a reading there on step 5's locked
  runbook, makes a scenario on it alone and reads its run `measured`.
- A reading's ref keeps naming one entry. A deposition's, an entry's, an observation's and a
  measured evidence's id is unique across page loads (`timeId`). The service keeps a deposition
  the bench's way (`project_state.deposition_refusal`): readings and observations are appended,
  each kept with the value, unit, time and words it was taken with (a correction is a new entry,
  keeping the time its reading was taken and saying when it was typed, `correctedAt`); a read-back
  moves `confirmed` from false to true; the state moves from staged to running to closed; a
  reconciliation stays as made; and closing stops new readings, observations and sample times.
  Every other write is refused in words, and every write a closed deposition accepts is audited.
  A run looks its readings up again each time it runs, and refuses in words one corrected since.
- The module reads list what a run may take: the runbooks read holds each deposition (its
  `standing` refs, the lookup's own rules deciding, `measurements.held_readings`), each reading
  that stands as a row of its own (kind `reading`, read by its id, with its measure, value, unit,
  time and depositor, marked `measured`), and the measured evidence a reconciliation released
  (kind `measured-evidence`, marked `unverified` where nobody read its number back), so
  `module_stores.PARTIAL` holds no runbooks line. Postdoc's rule 18 says how a scenario's value
  names a reading it read there.

### Alpha 2.2 D.0 (2026-11-04): an assistant's estimate at the HTTP door

- `POST /api/tools/{name}` with `X-OpenFerment-Assistant: <name>/<version>` runs the call in the
  model's lane under that name, so a number it types into a quantity is `model-estimate` by that
  name, as an MCP client's is in the server's own process (ADR-008, Implementation 12). The MCP
  server's `--service` mode sends its client's declared name there, and the estimate keeps the
  same origin whichever way the server reaches the project.

### Alpha 2.2 E.15 (2026-11-05): the browser's quantity types are generated

- The browser's `Quantity`, `Origin`, `OriginKind` and `OverrideOrigin` are the service's own,
  generated into `src/api/types.gen.ts`, and `check:plan`'s pairs, `Origin` among them, retired with
  `src/data/types.ts` (ADR-007's note of E.15). The 4.4b note above stands as written then.
