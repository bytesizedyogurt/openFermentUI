# ADR-014 — The Durable tier keeps preferences and the writes not yet acknowledged

- **Status**: accepted (a departure from execution prompt §5.5 and A3; the owner may reverse it)
- **Date**: 2026-10-30

## Context

The execution prompt says the browser's Durable snapshot keeps UI preferences only: "durable.ts
keeps theme, density, panel state and the last-open project" (§5.5), and A3 holds the snapshot to
"UI preferences only". Since stage 2 every scientific record lives on the service, in its
project: review decisions, Guild's ledger, depositions, measured evidence, runbooks and their
locks, overrides, fits, scenarios, trains and conversations (`lib/projectState.ts`). What the
snapshot still writes, besides the preferences (the reviewer's name, the Guild person the
browser acts as, the lessons finished here), is a queue: review decisions, Guild entries and
project rows made while the service did not answer, each removed once the service acknowledges
it, and the rows a browser from before alpha 2.0 kept, until a project takes them.

## Decision

Keep the queue in the Durable snapshot. A record the service holds is never kept there; a write
the service has not yet acknowledged is, so a decision made while the service is away survives a
reload and is sent when the service answers. Without it, a reviewer's decision made during an
outage is lost on the next reload, the safety problem OF-BLD-006 §4.6 kept Durable for.

## Consequences

- A3 reads: the snapshot holds preferences and the writes the service has not acknowledged, never
  a record the service holds. `check:state` holds the queue to that (a write leaves it when the
  service answers).
- The rows of a browser from before alpha 2.0 leave the snapshot once a project takes them.

## Revisit condition

The owner asks for the queue to go, or accounts (after alpha 2.0) give a person's pending writes a
home on the service.
