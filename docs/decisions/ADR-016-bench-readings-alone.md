# ADR-016 — The bench records a locked runbook's readings alone

- **Status**: accepted (a departure from the alpha 2.0 execution prompt's §11.5; the owner may
  reverse it)
- **Date**: 2026-11-04

## Context

Alpha 2.0's §11.5 keeps Guild, Primer, Deposition and the kinetics families as they are, beyond the
store and type changes that reach them, and `src/screens/Deposition.tsx` is the glove-tolerant
full-screen takeover a person deposits at (810 px portrait, 44 px targets, 7:1 step-text contrast,
no hover affordance). Until alpha 2.2 a deposition started from a protocol: the bench walked the
protocol's steps and recorded each measure the runbook named.

Alpha 2.2's §6.3 brings measured evidence into a run: a scenario value may name a bench reading by
its `measurement` origin, and the stage C gate asks the proof's walk to deposit a reading on a
locked runbook, make a scenario from it and run it. No store holds a protocol in this build:
nothing fills the project's protocols list, and RunbookDetail's chooser says that no protocol is
on file. So a deposition could not start from the screens at all, and no reading could exist for
a scenario to rest on.

## Options considered

1. **Keep the bench protocol-only** and leave the measurement origin reachable only through the
   API and the tests. The prompt's gate (a reading deposited at the bench, then a scenario made
   from it on the screens) would not hold.
2. **Seed a protocol** for the proof. A protocol is content the owner writes in Guild; the
   repository holds software alone (A4), so the proof could not type one either.
3. **Let the bench record a locked runbook's readings alone**: a deposition with no protocol,
   each entry a reading against one of the runbook's measures, under the bench's own constraints.

## Decision

Option 3. RunbookDetail offers *The readings alone* once the person has set their name in
Settings; the deposition it opens has `protocolId` null, and the bench
(`/runbooks/depositions/<id>/bench`, `src/screens/Deposition.tsx`) records each reading against
the runbook's measures with its raw words, its read-back confirmation and its time, as a protocol's
step does. A measured-evidence row made from it carries `conditions.protocolId` null. The screen
keeps every constraint its header comment names, and the comment says what the readings-alone mode
adds.

## Consequences

- A reading recorded this way is a measurement like any other: the service's lookup holds it to the
  project, a person's confirmation, its standing for its measure and a named depositor
  (`measurements.looked_up`; ADR-006, the C.5 note).
- A closed deposition's readings are append-only on the service, whichever way it was recorded.
- Guild's protocols, when a project keeps them, start a deposition as before; the readings-alone
  mode stands beside that path.

## Revisit condition

A project keeps protocols in its store (Guild's protocols reach the bench), or the owner asks for
the bench to stay protocol-only.
