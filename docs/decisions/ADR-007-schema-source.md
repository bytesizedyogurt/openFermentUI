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
