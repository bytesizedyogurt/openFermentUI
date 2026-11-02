# ADR-010 — Deletions

- **Status**: accepted (stage 1 executes it)
- **Date**: 2026-10-30

## Decision

Section 5 of the execution prompt is executed by `git rm` on `claude/alpha-2-foundation`, one
commit per subsection, after the `alpha-1.0` tag. Every deleted file stays reachable at
`alpha-1.0`. Tests that exist only to hold deleted content go with it. Seed content is nobody's
entry; a person's entry, decision or artifact on a live instance is never deleted by this build.

Deleted groups: the three programs and their content; the TypeScript seed and its projection; the
demo infrastructure; the bespoke retrieval stack; the file stores and the browser's scientific
state; guards that enforce retired rules and dead code; Dominion (seed-only; return condition: a
real patent or molecule data source connected through Intake); the instruction sprawl (moved to
`docs/history/`).

Kept from the seed: the ontology's field definitions and canonical units as
`core/openferment_core/schema/fields.yaml`, the unit engine's conversion tables (moved to Python),
and thread Q's source identifiers as `docs/corpus/ethanol-sources.txt`.

## Revisit condition

A deleted piece proves needed: restore it from `alpha-1.0` with a decision record.

## Evidence

- Commit list on `claude/alpha-2-foundation` (`alpha2: 1.x — …`), each naming what and why.
