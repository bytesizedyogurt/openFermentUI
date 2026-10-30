# ADR-011 — Guards and the verify stage list

- **Status**: accepted (stage 1 removes, stage 8 settles the list)
- **Date**: 2026-10-30

## Decision

Guards that enforce retired rules go: `check-seed.ts` (twelve-entry rail, forbidden words, seed
holders), `check-anchors.mjs`, `check-lock.ts` with `seed-lock-digests.json`, `check-reference.ts`,
`check-biorepo.mjs`, `check-store.ts` (Durable round-trips), `check-capture.ts`, `check-figures.ts`'s
seed-sample part, `test-export.mjs`, `check-durable.mjs`, `check-deposition.mjs` and
`check-reconcile*` where they read seed.

Survivors and newcomers, in verify order: `check:secrets` (first), `typecheck`, `gen:api --check`,
`test:core` (with the disposable database), `test:sim`, `test:lit`, `check:licences`,
`check:tools` (revised), `check:guild` (ladder from code), `build`, `test:smoke` (rewritten over the
new routes). `test_no_seed.py` holds acceptance A4.

The service double survives only as a replay of recorded real responses, recorded by
`pnpm record:fixtures` with the recording's versions in a header.

## Revisit condition

A guard proves necessary again: it returns with a test that fails on the thing it guards
(negative-tested, as before).

## Evidence

- `package.json` `verify` at `alpha-1.0` (24 stages).
