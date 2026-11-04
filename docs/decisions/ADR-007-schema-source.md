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
