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

## Implementation 8 (stage 8 settles the list)

`package.json` `verify`, in order, sixteen stages: `check:secrets` (first), `typecheck`,
`gen:api --check`, `gen:components --check`, `check:plan`, `test:core`, `test:sim`, `test:lit`,
`check:licences`, `check:tools`, `check:guild`, `check:state`, `check:figures`, `build`, `smoke`
(the decision's `test:smoke`), `test:reconcile`. CI (`.github/workflows/verify.yml`) runs it with a
`pgvector/pgvector:pg17` service, then `pnpm prove`, every step of the proof with the UI walk
among them (acceptance A2).

Beyond the decision's list, five stages stay, each guarding a rule this build keeps:

- `gen:components --check`: `COMPONENTS.md` is what the package map writes (stage 8.3).
- `check:plan`: the hand-kept `src/data/types.ts` and the service's models name the same fields,
  and `PROVENANCE_RANK` holds the service's order; it goes when the screens read
  `src/api/types.gen.ts` alone (a debt in `docs/PROGRESS.md`).
- `check:state`: the browser's outbox of writes the service has not acknowledged (ADR-014).
- `check:figures`: every provenance draws its own mark, `assumed` among them (execution prompt §7.5).
- `test:reconcile`: the prediction kinds a deposition reconciles, the code the bench page draws from.

`check:tools` holds `docs/TOOLS.md` to the registry (rule 5), which covers what `gen:tools --check`
would. `pnpm record:fixtures` waits: no component test replays recorded responses yet, and the walk
and the smoke run against the real service (a debt in `docs/PROGRESS.md`).
