# ADR-012 — The project licence is undecided

- **Status**: open question (the owner decides)
- **Date**: 2026-10-30

## Context

The repository declares no licence. The reference atlas names AGPL/ODbL as the brief's licensing
intent; the owner has said the licence is undecided; the development plan keeps software, database
contents, equipment designs, documentation and patent questions distinct and leaves the legal
mechanisms to the accountable steward.

## Decision

No LICENSE file is added. Dependencies keep their licences recorded in `core/licences.toml` and
`THIRD_PARTY.md`; this build adds no copyleft dependency. Vendored code (PISCES SFF, MIT; Sci RAG
Kit migrations, BSD-3-Clause) keeps its own LICENSE file beside it.

## Revisit condition

The owner adopts terms.

## Evidence

- Execution prompt §4.10 and §13 question 8; development plan §8 "Adopt public terms before public
  release".
