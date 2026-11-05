# ADR-007 — One schema source for the two sides

- **Status**: accepted (provisional choice; stage 7 completes it)
- **Date**: 2026-10-30

## Context

At `alpha-1.0` every Pydantic model in `models.py` is mirrored by hand in `src/data/types.ts`, and
`scripts/check-plan.mjs` diffs field lists as text from a hand-kept `PAIRS` list. A model missing
from `PAIRS` is guarded by nothing.

## Decision

`core/openferment_core/models.py` (Pydantic) is the source. TypeScript types are generated from the
FastAPI OpenAPI document by `openapi-typescript` into `src/api/types.gen.ts` (`pnpm gen:api`),
committed, and checked in verify (`gen:api --check`). The OpenAPI document is committed at
`docs/api/openapi.json`. `src/data/types.ts` and `PAIRS` retire once every used type is generated.

## Revisit condition

Never; this is how the drift stops recurring.

## Evidence

- `scripts/check-plan.mjs` and `src/data/types.ts` at `alpha-1.0`.

## Implementation notes

### Alpha 2.2, E.0a (2026-11-04): the service's answers say what it writes

- Every JSON route declares the model it writes, and its handler returns that model; FastAPI
  validates the answer against it and writes every field. Thirty-five routes gained a model here
  (Proforma's, fermOS's, pureOS's, the parameter panel's, the stored answers of thermosteam,
  ProtParam and volatility, the catalogue's file intake, the literature's counts and health), and
  two reads are new: `GET /api/biorepo/artifacts/{id}/tables` (`ProformaTables`) and
  `GET /api/biorepo/artifacts/{id}/checks` (a list of `RegressionCheck`). The routes that answer
  something besides a JSON model are the three event streams, a flowsheet's own file and a
  study's export; the project state's three routes (`GET`, `PUT` and `DELETE /api/state`) take
  their models with the row models in the commit after this one. `core/tests/test_route_models.py`
  holds the list.
- `api._scoped_openapi` writes the rule into the document. A component schema reached from a
  success response and from no request body or parameter (`api.response_only`) lists every
  property as required, in the order of its properties (`_required_as_written`), so
  openapi-typescript writes each such field as one the browser receives. A schema a request takes
  keeps Pydantic's required list, where a field with a default is one a request may leave out.
- `api.AS_KEPT` keeps Pydantic's lists for the runbook family: `Runbook`, `RunbookStage`,
  `Prediction`, `Measure` and `Range`, served with `response_model_exclude_unset` for the lock's
  digest, and `RunbookDraft`, which a page keeps as a runbook. A model with a serializer of its
  own keeps its list as well: `Quantity` leaves an unset basis, range and origin out of what it
  writes, and every such model is one a request takes today, which the test holds.
- openapi-typescript's own handling of defaults stays as it is: on the stage's scratch documents,
  turning it off added thirteen typecheck errors and removed three.
- Measured on the document this commit writes: 255 schemas, 66 of them new, 177 marked, none split
  into `-Input` and `-Output`, and the client typechecks against it with no file of its own changed.
- Consequences: an answer that does not fit its model is a 500 whose log names the field, so a
  handler returns the model itself; a response-only model a request later takes keeps Pydantic's
  list from then on, which `pnpm gen:api --check` shows as drift in the generated files.

### Alpha 2.2, E.0b (2026-11-04): the rows a project keeps of its pages

- Each kind of row a page writes through `PUT /api/state/{kind}/{id}` has its model in
  `models.py`: `Deposition` (with `DepositionEntry`, `DepositionObservation`, `Reconciliation`,
  `ReconciliationDelta`), `MeasuredEvidence` (with `MeasuredConditions`), `ProformaScenario`,
  `TrainMade` and `RunbookLock` are new, and `Runbook`, `Override` and `LiveConversation` read as
  they stood. Each new one is written from the page's hand type, its required fields the hand
  type's, and a row of one keeps the fields its model does not name (`extra="allow"`, written into
  the generated type as an index signature beside the named fields; alpha 1.0's `dims`, `point`
  and `assumptions` of a scenario among them). A field a row may leave out defaults to None or to
  an empty collection, so the generated type names it as optional: openapi-typescript writes a
  field with any other default as one the answer holds.
- `GET /api/state` answers a `ProjectState` with `response_model_exclude_unset`: each row read as
  its kind's model one at a time (`project_state.state`) and served as the page sent it, a field
  it left out staying out of the answer; a row kept before its kind had a model, that does not
  read, is left out and named in `refused` (`RefusedRow`: kind, id, why), and the rest load. The
  rows' schemas join `api.AS_KEPT`, so each keeps Pydantic's required list. A Live conversation is
  read from the whole of what Postdoc keeps, every field set, so it is served whole and its family
  stays marked; `core/tests/test_route_models.py` names it in `SERVED_WHOLE`, and a schema an
  as-kept route serves is in AS_KEPT, keeps Pydantic's list, or is in that family.
- A write is read as its kind's model before it is kept, and refused in words naming the fields
  (`project_state._reads_as`), after the checks that were there. `PUT` answers `StateKept` and
  `DELETE` `StateTakenBack`, so every JSON route answers a model; the test's waiting set is gone.
- The rows come back byte for byte as the page writes JSON (`JSON.stringify`): an integral
  number in a float field is written with a point by the service and read back by the page as the
  number it sent, so the lock's digest over a row read back is the digest over the row sent.
- Measured on the document this commit writes: 270 schemas, 15 of them new, 182 marked, none
  split; the client typechecks against it, reading `refused` alone (the store names each refused
  row in its activity feed and says so once).

### Alpha 2.2, E.1 (2026-11-04): the screens read the generated types through their libs

- Each `src/lib` module names the generated schemas of the answers it reads
  (`export type X = components['schemas']['X']`), and a screen or a component imports a name from
  the lib that answers it: `lib/studies.ts` a run and what it rests on (`EngineRun`, `RunReport`,
  `RunDiagnostic`, `Artifact`, `ComputedBasis`, `BasisInput`, `BasisSource`, `Quantity`, `Origin`,
  `EngineInput`, `Provenance`), the studies and the SFF record; `lib/params.ts` the parameter
  panel's (`ParameterSpec`, `ParameterValue`, `Override`, `ParamScope` and the resolve's pair);
  `lib/proforma.ts` Proforma's (`Scenario`, the generated `ProformaScenario`; the shelf, the
  binding, the run with its tables, grid and package test, the ceiling check, `SimulatorStatus`,
  `ScenarioRunsResponse`, and the fits, vessels and train runs a composite scenario names). A name
  whose lib moves in a later commit is read from `src/api/types.gen.ts` where it is used
  (`Dossier`'s `Band`, `lib/params.ts`'s `TrainSpec`). `Provenance` is the union every schema
  writes, read from `Artifact`.
- The sliders' grid (`CostLine`, `SensitivityRow`, `ResultGrid`) is the browser's own and lives in
  `lib/proforma.ts`; `src/data/types.ts` re-exports it until the file goes.
- openapi-typescript writes a field with a default as one every request body carries; a body that
  leaves such a field to the service's default is typed `Body<T, K>` (`lib/proforma.ts`), the
  fields `K` optional: `runBody` leaves `samples` to the service.
- openapi-typescript writes a field with a default as one an answer holds, and an answer served as
  kept leaves out a field its row never set: the generated types name `Override.origin`,
  `Runbook.note` and `Runbook.progressPct` as present. A runbook a study makes or a page adopts
  writes its note and its progress; the page kept every change before this commit with no origin,
  so an override read back may carry none (Known debts). The page writes a person's change with
  its origin from here on, and `inputsOf` reads a change with none as a person's assumption, as the
  service does; `pnpm check:state` holds it.

### Alpha 2.2, E.3 (2026-11-04): Postdoc's lib, and the seam where a draft becomes a runbook

- `lib/postdoc.ts` names the generated schemas of Postdoc's answers: the health (`Health`, where
  the hand-kept `PostdocHealth` stood, its fallback model always written and the service's name
  beside it), the question (`AskRequest`, `PriorTurn`), the plan and what it rests on
  (`AnswerPlan`; `AnswerPlanUsage`, the generated `Usage`; `Claim`, `ClaimValue`, `PassageRef`,
  `Passage`, `Evidence`, `ModuleRow`, `CoverageMap`, `RunbookDraft`, `TraceStep`; `StopReason`,
  read from `AnswerPlan['stopped']`) and the conversation (`LiveConversation`, `LiveTurn`). The
  Postdoc screen, PlanTrace, PassageQuote, AnswerPlanView and EvidenceCard read them there,
  EvidenceCard its `BasisInput` from `lib/studies.ts`; the store, the Durable snapshot, the project
  state and check:state read the conversation's.
- A question sends `by` with every ask, empty when nobody is named, which is the service's
  default. A turn the page begins writes its asker (null when nobody is named) and its artifacts
  (none yet), every field the generated `LiveTurn` holds.
- One seam stands until E.11 moves the store's runbooks: `store.adoptRunbookDraft` takes the
  generated `RunbookDraft` and writes the store's hand-kept `Runbook`, its predictions and
  measures copied as the service wrote them under one type assertion, since lock.ts and
  runbook_lock.py read a field left out and a null apart (Known debts).
- Each reader keeps its default for a field older plans lack (`claim.values ?? []`,
  `plan.stopped ?? 'done'` and their kin): a browser's snapshot from before alpha 2.0 lays such
  plans on the page until a load from the service answers them whole.

### Alpha 2.2, E.4 (2026-11-04): the review family, and a record's field held to the ontology

- `lib/review.ts` names the generated schemas of the review: `Candidate`, `ReviewDecision`,
  `DecisionCheck`, `RecordStatus` and `ExtractorRun` (read from the candidate), `RunOutput` (the
  generated `ExtractRun`), `Overlay` and `OverlayPaper`. `lib/literature.ts` names the collection's
  and the search's (`CollectOutcome`, `CollectRequest`, `PasteRequest`, `LiteratureDocument`,
  `SearchResponse`), and `lib/artifacts.ts` `ReplayResult`, beside the `Artifact` and `BasisSource`
  that `lib/studies.ts` names. BioRepo, BioRepoSearch, BioRepoArtifacts, PaperReader, Witness,
  CollectCard and the run metrics read them there; the store, the Durable snapshot, `lib/intake.ts`
  and every screen that names a record, a paper or a decision check read the record and the paper
  from `lib/review.ts`.
- The record (`ExtractionRecord`) is the store's own shape of a candidate: the generated
  `Candidate` with the review layer over it, the decision's gold, correction and reviewer typed from
  the generated `ReviewDecision`, its audit trail (`AuditLine`, the generated `AuditEvent` with
  `from` and `to` written only when a value changed), what it was published as and whether the
  current run reads it. The service writes a candidate's field as a string. A candidate enters the
  store as a record when the ontology names its field (`recordOf`, through the guard `isFieldId`
  beside `ONTOLOGY`, which test_schema.py holds to fields.yaml); the store names a candidate on any
  other field once in its activity and a toast, and every reader of a record indexes the ontology
  by its field as before. A run's false positive keeps the service's string, and `fieldName` names
  a field the ontology does not hold by its id.
- The paper (`Paper`) is the overlay's entry under its id, titled by the id when the kit holds no
  title, with the service's names (`journal`, `url`, `source`, `reason`). The hand-kept paper's
  organisms, topics and abstract were filled empty by the store, its held flag was set on every
  paper, and its source type, open-access flag and PMID were read by no screen; they go, with
  BioRepo's Organism and Topic columns, filters and CSV fields, PaperReader's chips and abstract,
  and the attribution of a record to a strain through its paper (Departures).
- The Durable tier's decision reads each field's type from the generated `ReviewDecision`, a null
  kept as null, so a decision made offline and one the service answers stay the same object
  (`DecisionMirror`); a decision with no reject reason gives its record a null one.
- The browser's own types move to their owners: `FieldId`, `ParameterFamily` and `ParameterDef` to
  `data/ontology.ts`, and `Job` and `JobStage` to `store.ts`. `src/data/types.ts` re-exports each
  until E.15, and a file a later commit moves reads them there until then.

### Alpha 2.2, E.6 (2026-11-04): fermOS's lib, and thermosteam's answer as a pair

- `lib/fermos.ts` names the generated schemas fermOS answers and takes: a fit and its series
  (`FermosSeries`, `FitParam`, `UnidentifiedReason`, read from the parameter's `unidentifiedBy`,
  `KineticFit`, `FermosFitResponse`), a forecast (`Band`, `ForecastResult`), a family, a binding,
  a simulation with its steady state, the kept simulations, a harvest and a vessel (`FamilyInfo`,
  `FermosBinding`, `SimulationResult`, `SteadyState`, `SimulationSummary`, `FermosHarvest`,
  `VesselRequest`, `VesselDesign`). `lib/thermo.ts` names thermosteam's (`ThermoPropsRequest`,
  `ThermoProps`, `ThermoPropsAnswer`, `ThermoPropsStored`). The four fermOS views, PropertiesPanel
  and the figures TimeCourse, TrajectoryBand and OxygenBalance read them there, Dossier its `Band`
  and the store its kept fits; a deposition and its runbook stay the store's hand-kept shapes until
  E.11, and a train until E.7.
- `POST /api/thermo/props` answers `ThermoPropsAnswer`: the `thermo_props` artifact beside what it
  holds, read by the service as `ThermoProps`, the pair `GET /api/thermo/props` answers as
  `ThermoPropsStored` once the answer is stored. A page reads each property as typed, and the cast
  of an artifact's output (`propsOf`) goes.
- A fit and its series go back to the service in a forecast's and a fit's request, so the
  generated `KineticFit`, `FermosSeries`, `FitParam` and `SeriesFitQuality` keep Pydantic's
  required lists (E.0a's rule) and name each field with a default as one a request may leave out.
  The service writes every field of a fit it answers; the readers default the ones a request may
  leave out (a fit's parameters and quality, a series' points, a quality's residuals), nine reads.

### Alpha 2.2, E.7 (2026-11-04): pureOS's lib, and a train's units read as a request may leave them

- `lib/pureos.ts` names the generated schemas pureOS answers and takes: a run's train and its units
  (`Train`, `TrainUnit`), a proposal (`ProposeRequest`, `TrainProposal`, `ProposalReason`,
  `ProposalMissing`), the catalogue (`UnitType`, `UnitSpecs`), a train as data (`TrainSpec`,
  `TrainUnitSpec`, `TrainParam`) with its validation, check and run (`TrainValidation`,
  `TrainRunRequest`, `TrainRun`, `StreamPurity`), a train read from a run (`TrainFromRunRequest`,
  `TrainFromRun`) and a train a model kept (`KeptTrain`); it reads a stream, a train on file and a
  vessel (`StreamRow`, `TrainSummary`, `VesselSummary`) from `lib/proforma.ts`, which names them
  for Proforma's pages. `lib/proposals.ts` names a gate's `Proposal` and a person's act on it,
  `ProposalAction`; the Guild person acting stays on the hand-kept types until Guild's lib moves
  (E.12). pureOS's four screens, ProposedTrain, ProposalsCard and the figures PurityByStream and
  RecoveryByUnit read every name there, `lib/thermo.ts` its `Train`, `lib/params.ts` its
  `TrainSpec` (the alias E.1 left goes), and the store its saved trains, its proposals and what the
  Builder showed.
- A train goes to the service in a request (a validation, a check, a run), so the generated
  `TrainSpec` keeps Pydantic's required list (E.0a's rule) and names its units as a field a request
  may leave out. The service writes every train it answers whole, and the page makes every train
  with its units; each reader takes a train's units through `unitsOf`, which reads a train sent with
  none as a train of no unit.
- The Builder's saved train in the Durable snapshot, `TrainMade`, is the generated row of E.0b,
  where a hand mirror stood in `lib/durable.ts`.
- The vocabulary's own types (`UnitOperationStage`, `UnitOperation`, `CarbonSource`) move to
  `data/vocabulary.ts` beside its lists; `src/data/types.ts` re-exports them until E.15.

### Alpha 2.2, E.8 (2026-11-05): the catalogues' lib, born on the generated types

- `lib/catalogues.ts` names the generated schemas of a project's catalogues: an entry
  (`CatalogueEntry`), a keep (`CatalogueKeep`) and what a file came to (`CatalogueIntake`), with a
  product's class, where the cells leave it and a skill's criticality read from the entry's own
  fields. The catalogues screen reads every shape there and names no hand-kept type.
  `data/labels.ts`' class labels read the generated union, the twelve classes pureOS's proposer
  reads, beside the labels of a location and a criticality. The stage plan gave `ProductCategory`
  to E.9, and it moves here with its first generated reader, the screen; StrainPage and Runbooks
  read the labels with the hand-kept class, whose eleven classes are among the twelve.
- A keep sends the entry as the catalogue answers one (`CatalogueKeep.entry` takes the entry's
  model), so the generated `CatalogueEntry` keeps Pydantic's required list (E.0a's rule) and names
  each field with a default as one a reader may find absent. The service writes every field of an
  entry it answers; the screen reads a list field through `?? []` and a word through `?? ''`, and a
  keep sends `by` and `at` empty for the service to write.

### Alpha 2.2, E.9 (2026-11-05): geneOS's lib, and a strain and a product as catalogue entries

- `lib/geneos.ts` names the generated schemas of geneOS's answers: a model on the shelf
  (`GeneosModelInfo`) and a ceiling, a frontier or a sugar mix (`GeneosResult`); it reads a field's
  types (`FieldId`, `ParameterDef`) from `data/ontology.ts`. GeneOSModel, Organisms and the figures
  Frontier, MixLine, CeilingGap and EvidenceStrip read every name there or in `lib/studies.ts`
  (`ComputedBasis`, `Provenance`), and EvidenceCard, whose geneOS helpers took the hand-kept types
  through the lib, finishes.
- A strain and a product are the project's catalogue entries: `lib/catalogues.ts` names `Strain`
  and `Product` as the generated `CatalogueEntry` of their kind, and the store fills its `strains`
  and `products` from the two catalogues (`listStrains`, `listProducts`) as the page opens and again
  after the catalogues screen keeps an entry or takes in a file; `cataloguesRead` and
  `cataloguesProblem` say where the read stands, and a reset of the browser's data keeps them, the
  service's as the overlay is. A strain's binomial reads the entry's `species`, its designation its
  `name` and its description its `note`. The alpha 1.0 fields no entry keeps leave with their reads,
  each of which read an empty list until now: a strain's taxonomy, badges, biosafety level and
  notes; a product's default host, unit operations, process code, routes, regulatory ids, tags,
  value band and its two provenance labels. StrainPage keeps the hand-kept `Protocol` until E.12.
- A strain is named in a chooser or a label by `strainWords` (its species, then its name), and a
  scenario links to a strain by any name its entry keeps (`strainNames` and `namesStrain`, which
  moved from StrainPage into `lib/geneos.ts`).

### Alpha 2.2, E.11 (2026-11-05): the runbook family and the bench's record, read as a row served as kept

- `lib/studies.ts`, which named `Runbook` since E.1, names the rest of the runbook family (`RunbookStatus`,
  `RunbookStage`, `RunbookStageStatus`, `Prediction`, `Measure`) and the bench's record (`Deposition`,
  `DepositionEntry`, `SeriesRole`, `MeasuredEvidence`). `lib/projectState.ts`'s `ProjectState` is the generated
  answer of `GET /api/state` with its `RefusedRow`, where a hand mirror stood, and `ProjectRows` the kinds of rows a
  page compares and sends. Runbooks, RunbookDetail, RunbookLedger, Depositions, DepositionDetail and the bench
  (Deposition, its own `Step` on the hand-kept types until E.12), RunbookBits, DepositionPanel, TimeSeriesPanel,
  ProcessTrain (its `UnitOperation` from `data/vocabulary.ts`), the figure IntervalLedger, the engine modules a
  runbook and a deposition pass through (ledger, lock, readings, reconcile, series, capture), `lib/fermos.ts`,
  `lib/practice.ts`, `lib/durable.ts`, `data/labels.ts`, the store, check:state, check-reconcile-kinds and
  export-lock-fixtures read them there.
- A runbook is served as kept (`api.AS_KEPT`, E.0a), so a row leaves out every field it never set. A reader takes a
  runbook's stages, predictions, measures and outputs through `stagesOf`, `predictionsOf`, `measuresOf` and
  `outputsOf` (the engine modules through `?? []`, which keeps `lib/studies.ts` out of their imports); a runbook with
  no lock time is unlocked and one with no price unpriced (`== null`), and a measure that names no prediction is
  context nobody predicted. The document names a runbook's note and its progress as present for their defaults, and
  their readers read each as a row may leave it out: the note card says the runbook keeps no note, and the progress
  stands at none.
- The seam of E.3 goes: `store.adoptRunbookDraft` copies a draft's predictions and measures as the service wrote
  them, with no type assertion, and every reader passes a prediction's kind, interval, artifact and records on as
  they arrived; the lock digests the browser writes hold byte for byte (`core/tests/fixtures/lock-digests.json`).

### Alpha 2.2, E.12 (2026-11-05): Guild, the protocols and Primer, a skill and a lesson as the project's catalogue entries

- `lib/guild.ts` names the ledger (`Guild`, `GuildPerson`, `GuildRole`, `GuildEvidence`, `EvidenceKind`,
  `EvidenceSource`, `GuildWithdrawal`, `GuildPolicy`, `GateMode`), `lib/checks.ts` the checks, and `lib/practice.ts`
  Practice's scenarios and sessions. A new `lib/protocols.ts` names a project's protocols (ADR-017: `Protocol`,
  `ProtocolVersion`, `Step`, `Material` and the rest, `ProtocolCategory` and `ScalingClass` read off their fields) with
  their four routes, and `lib/catalogues.ts` a skill and a lesson as the catalogue's own entries
  (`CatalogueEntry & { kind: 'skill' }` and `{ kind: 'lesson' }`), with a lesson's blocks and checkpoint (ADR-018).
  Guild's screens, the protocol screens, Primer's, GuildBits, GuildGate, LessonEmbeds, the bench (Deposition and
  BenchCheck), StrainPage, the engine modules competence, checks, path, diff and scale, `lib/proposals.ts`, the
  store, the Durable snapshot, check:guild and the competence fixture's scripts read them there. The client's own
  `RunState`, `TimerState` and `Deviation` live in the store and `SkillFamily` in `data/skillFamilies.ts`.
- The store reads the project's skills and lessons with its strains and products (`hydrateCatalogues`) and its
  protocols from `GET /api/protocols` (`hydrateProtocols`), each as the page opens; the editor keeps a version on
  the service in the reviewer's name (`keepProtocolVersion`, `POST /api/protocols/{id}/versions`) and lays the
  protocol the service answers in its place.
- A protocol is served whole, so every field arrives and an absent one as null; the generated types name a list a
  keep's body may leave out as optional, so a reader takes a version's steps, materials, equipment, safety notes and
  references with `?? []` (or `stepsOf` and its kin in `lib/protocols.ts`), and tests a step's timer with `!= null`,
  where the hand-kept shape left a timer absent.
- A catalogue skill's policy may be absent. `src/engine/competence.ts` leaves a skill kept with no policy out of every
  level (`rated`, and a status's `unrated`), as `competence.unrated` does on the service: nobody holds it, the
  ranking proposes no check on it, a path shows it waiting for its policy, and a skill that needs it is held at
  Learning. `core/tests/fixtures/competence-unrated.json` holds the two equal on such a skill, and
  `competence.json` is byte for byte what it was. The ledger the service answers always keeps a policy
  (`Guild.policy`); a ledger a check builds for itself may leave it to the default (`Ledger`).

### Alpha 2.2, E.14 (2026-11-05): the last readers, and the browser's own types with their owners

- Provenance, TraceCards and check:figures read the provenance class from `lib/studies.ts`, QuantityField a record's
  field from `data/ontology.ts`, JobsTray a job from the store, and the store a project from `lib/project.ts`, which
  names the generated `Project`. No file imports `src/data/types.ts`; check:plan reads its pairs there by text until
  E.15 deletes it.
- The browser's own types finish moving to their owners: a line of the page's recent activity (`ActivityEvent`) to
  the store, and a Proforma assumption as a snapshot written before the parameter panel keeps it (`InputAssumption`)
  to `lib/durable.ts`, with the seven fields the browser wrote; the store reads each as a person's assumption.
  `src/data/types.ts` re-exports `ActivityEvent` until E.15 and keeps its own `InputAssumption`, check:plan's twin of
  the model the service binds a scenario's values with, its origin and reading among its fields; no route serves it.
