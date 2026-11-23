# ADR-017 — A project keeps its protocols

- **Status**: accepted (alpha 2.2 E.12a, ADR-016's revisit condition; the owner may reverse it)
- **Date**: 2026-11-05

## Context

Alpha 2.0 deleted the TypeScript protocols with the seed (ADR-010). Since then no store has held a
protocol: the browser's list of protocols starts empty and stays so, Guild's projection holds no
step, so `guild.step_skills` answers that no step exists and an entry recorded at a protocol's
step is refused, Practice has no step to build a scenario on, and a check's brief names none.
ADR-016 let the bench record a locked runbook's readings alone for that reason, and named a
project keeping its protocols as its revisit condition.

Alpha 2.2's §6.5 moves every screen onto the generated types and asks Guild's protocol steps to
name skills from the skills catalogue, which E.8 gave each skill's policy. A step's skills are
held to that catalogue only where the service holds the step, and a screen reading the generated
types reads a schema the service serves.

## Options considered

1. **Protocols in the page alone.** The protocol types stay the page's own shape in
   `src/lib/protocols.ts` (a departure from §6.5's rule), kept in the browser's snapshot. Guild's
   ledger still finds no step, so a run's entry at a step is refused, and Practice has nothing to
   quote.
2. **A fifth catalogue kind.** A person's keep replaces a catalogue entry whole, and the
   catalogue holds names and words alone (ADR-006): a protocol's kept versions would go with each
   keep, and its amounts would be refused.
3. **A table of the project's own.** One row a protocol in `protocols` (migration 0010), kept
   whole as the Pydantic `Protocol`, each version appended and kept as it was kept, read and
   written through four routes, and read by Guild, Practice and the module reads.

## Decision

Option 3.

- `models.py` holds `Protocol`, `ProtocolVersion`, `Step`, `Material` with `MaterialStock`,
  `BaseBatch`, `EstMinutes` and `ProtocolReference`, written from the page's hand shapes in
  `src/data/types.ts`: a protocol's category and a material's scaling are Literals, every number
  is finite, a step's placeholders (`{{qty:<material>}}`, `{{stock:<material>}}`) bind materials
  its version holds, and a version holds each step id and each material name once.
- `protocols.py` is the store. `POST /api/protocols` makes a protocol once under its id, with
  its versions; `POST /api/protocols/{id}/versions` adds a version under a version of its own
  and makes it the current one; a version the protocol holds already is refused in words, so a
  kept version stays as it was kept. `GET /api/protocols` and `GET /api/protocols/{id}` serve
  each protocol whole. The service writes each version's keeper and time (`by`, `at`), holds the
  keeper's name to the rule a person's recorded name keeps, and audits each keep in that name
  (module `runbooks`). Nothing takes a protocol or a version out.
- Every skill a step names is one the project's skill catalogue holds at the keep; a step naming
  one it does not hold is refused in words naming the step and the skill.
- `guild.projection()` reads the steps from the store: every version's steps with their skills
  (`guild.step_skills`), and the current version of each protocol a step of which needs a skill,
  its steps in the words the bench shows at the base batch (`protocols.as_quoted`), which
  Practice quotes and a check's brief reads. The runbooks module's read lists each protocol.
- A protocol's numbers are its own writing for its base batch, kept as a person wrote them; a
  material that rests on a record names it (`sourceRecordId`). No tool writes a protocol.

## Consequences

- The repository ships no protocol (A4): every protocol enters through the route in a person's
  name, and the tests write placeholders.
- ADR-016's readings-alone mode stands beside a protocol's steps: a deposition opened from a kept
  protocol walks its steps, and one opened with none records the runbook's readings alone.
- A protocol's own fields (its title, category, organisms, BSL, purpose and provenance note) are
  written when it is made, and this build changes them nowhere.
- The browser's store reads the protocols, and the protocol screens and Guild read the generated
  types, in E.12.
- Guild's projection reads the project's stores, so it is read before a transaction begins:
  `checks._propose` and `guild.write_check_entries_in` take the skills their callers read, since
  `db.run` refuses to run on the database's own thread.

## Revisit condition

The owner declines it (the protocol types then stay the page's own shape in
`src/lib/protocols.ts`, a departure from §6.5's rule, and Guild's steps name no skill); a protocol
needs a review state before a version becomes current; or a protocol's own fields need to change
after it is made.
