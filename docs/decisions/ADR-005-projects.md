# ADR-005 — Projects replace programs

- **Status**: accepted (requirement: the owner named projects as the organizing object)
- **Date**: 2026-10-30

## Context

At `alpha-1.0` three programs (casein A–O, PHA P, yeast ethanol Q) partition the seed by thread
letter, with one archive switch (`showArchived`) threaded through every list, request and tool
context (`programs.ts`, `programs.py`, `programOf`, `HiddenByArchive`, `ArchivedBanner`,
`includeArchived`, `OPENFERMENT_INCLUDE_ARCHIVED`).

## Decision

A **Project** scopes documents, records, flowsheets, runs, artifacts, runbooks, depositions,
conversations and Guild entries. Literature is stored only when a project selects a document for
ingestion. Every table carries `project_id`; every API route is project-scoped; the MCP server
takes a project. The program machinery is deleted with the programs. Accounts are designed for and
stubbed (`project_members`), with no login: the loopback bind and `guard.py` stay the access
control.

## Consequences

- Home opens on the person's projects; module screens become views inside a project (ADR-009).
- The `includeArchived` parameter disappears from requests and tool contexts.

## Revisit condition

Accounts and multi-user access (a later build).

## Evidence

- Execution prompt §4.5; development plan §1 ("a conversation with Postdoc inside a chosen
  project").
