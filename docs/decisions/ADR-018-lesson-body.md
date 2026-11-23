# ADR-018 — A lesson keeps its body in the lesson catalogue

- **Status**: accepted (alpha 2.2 E.12a; the owner may reverse it)
- **Date**: 2026-11-05

## Context

Primer's lessons were the TypeScript seed's, each with the minutes it takes, its blocks (prose and
the embeds its page draws) and its checkpoint, and they went with the seed (ADR-010). Alpha 2.1
D.1 gave a project a lesson catalogue (`kind: lesson`): an id, a name and the skills a lesson
counts toward, which Guild reads when a passed lesson writes a knowledge entry. Primer's lesson
page draws a lesson's minutes, its blocks and its checkpoint, which it grades in any unit of an
answer's family, and §6.5 asks Primer's screens to read their lessons from the service.

## Options considered

1. **The catalogue as it stands.** Primer shows a lesson's name, its note and its skills, and a
   learner reads no lesson and answers no checkpoint.
2. **A table of lessons of their own**, as ADR-017 gives protocols. A lesson's author replaces its
   body whole, as a person's keep replaces a catalogue entry, and a lesson keeps no versions, so
   the table would hold what the catalogue holds.
3. **The lesson kind gains its body**: `minutes`, `blocks` and `checkpoint` on the lesson's
   catalogue entry, each written by a person.

## Decision

Option 3.

- `minutes`: how long the lesson takes, a whole number from 1 to 600.
- `blocks`: the lesson's body in order, each a run of prose in Markdown (`{kind: "prose", md}`) or
  one of the nine embeds Primer's page draws (`{kind: "embed", embed, arg}`: `chip-demo`,
  `record-card`, `mini-queue`, `metrics-tiles`, `strip-plot`, `protocol-card`, `ask-prompt`,
  `scenario-widget`, `skill-steps`), with the id or the words it is drawn on.
- `checkpoint`: the questions a learner answers to pass the lesson, each with an id of its own in
  the lesson. A multiple-choice question names two options or more and the index of the one that
  answers it. A numeric question's answer is a value, a unit and a tolerance in percent of the
  value (0 to 100), each written by a person: the unit is empty for a pure number, else one the
  unit converter reads (`units.normalize`), so an answer in any unit of its family grades.
- The three are the lesson kind's own: any other kind refuses them in words, and a question that
  does not stand is refused in words naming it. The route and a JSON file take them.
  `catalogue_write` keeps a lesson with no body (the registry refuses a number typed into a
  tool's input, and the tool's input holds no blocks), and `catalogue_read` lists a lesson with its
  skills and minutes, its body left to the catalogues screen and Primer.

## Consequences

- A checkpoint's answer is teaching material its author writes, which Primer's grading alone
  reads: no record, run or claim reads it (ADR-006).
- The repository ships no lesson (A4); the tests write placeholders, and a unit they need is read
  from the converter's own table at run time.
- Primer's screens read lessons from `GET /api/catalogues/lesson` in E.12, as one flat list, and
  the Durable snapshot keeps no lesson.
- The module read for Primer lists each catalogue lesson with its skills and minutes.

## Revisit condition

The owner declines it (Primer then shows a lesson's name, note and skills); a lesson needs a block
beyond the nine embeds; or lessons need an order and a grouping of their own.
