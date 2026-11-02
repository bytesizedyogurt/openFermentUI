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
