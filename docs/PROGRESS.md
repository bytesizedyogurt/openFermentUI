# openFerment alpha 2.0 — progress

The resume point for every session of the alpha 2.0 foundation build. Keep it current at every
checkpoint. A fresh session continues from this file and `git log` alone.

## Resume

1. Branch: `claude/alpha-2-foundation` (cut from `main` at `d19224f`). `git fetch origin
   claude/alpha-2-foundation && git checkout claude/alpha-2-foundation`.
2. Environment:
   - `pnpm install --frozen-lockfile`
   - `cd core && uv sync --all-extras`
   - From stage 2 on: `pnpm db:up` (or a local PostgreSQL with pgvector), then `pnpm db:migrate`.
3. First tests to run: `pnpm test:core`, then `pnpm test:sim`.
4. **Next step: 1.1** — stage 1, delete section 5.1 (programs and their content). Before thread Q's
   list goes, write `docs/corpus/ethanol-sources.txt` from `src/data/corpus/threadQ.ts` and
   `docs/thread-q-include.txt` (stage 1, step 3).
5. Files in flight: none.

## Current stage

Stage 0 — baseline, tag, decisions: complete except the tag push (see Blockers).

## Last green runs

| When (UTC) | Suite | Result | Time | Commit |
|---|---|---|---|---|
| 2026-10-30 03:43 | `pnpm test:core` | 2165 passed, 1 skipped, 172 deselected | 5 min 35 s | `d19224f` (baseline) |
| 2026-10-30 03:48 | `pnpm test:sim` | 105 passed, 2233 deselected | 4 min 11 s | `d19224f` (baseline) |

## Decisions

| ADR | Decision | Status |
|---|---|---|
| [000](decisions/ADR-000-fresh-slate.md) | Fresh slate; every old rule classified | accepted |
| [001](decisions/ADR-001-postgresql.md) | PostgreSQL with pgvector is the one database | accepted, stage 2 |
| [002](decisions/ADR-002-sci-rag-kit.md) | Sci RAG Kit as an in-process library | accepted, stage 3 |
| [003](decisions/ADR-003-sff.md) | SFF is the flowsheet record | accepted, stage 4 |
| [004](decisions/ADR-004-biosteam-adapter.md) | BioSTEAM through one adapter | accepted, stage 4 |
| [005](decisions/ADR-005-projects.md) | Projects replace programs | accepted |
| [006](decisions/ADR-006-quantities-and-estimates.md) | Typed quantities with origins replace Rule 1 | accepted, stages 4 and 6 |
| [007](decisions/ADR-007-schema-source.md) | Types generated from OpenAPI | accepted, stage 7 |
| [008](decisions/ADR-008-postdoc-memory-routing.md) | Postdoc memory on the server; model routes | accepted, stage 6 |
| [009](decisions/ADR-009-ui.md) | The UI is kept and wired | accepted, stage 7 |
| [010](decisions/ADR-010-deletions.md) | Deletions | accepted, stage 1 |
| [011](decisions/ADR-011-guards.md) | Guards and verify stages | accepted, stages 1 and 8 |
| [012](decisions/ADR-012-licence-undecided.md) | Licence undecided | open (owner) |

## Departures from the execution prompt

| Where | Departure | Why |
|---|---|---|
| §10 stage 8.1 | The old `CLAUDE.md` moved to `docs/history/CLAUDE-2026-10-21.md` at stage 0, with a short interim `CLAUDE.md` | Claude Code injects `CLAUDE.md` into every new session as binding instructions; the old file (96,858 bytes) would direct a resuming session against this build. Stage 8 still writes the final file |
| §3.4 | Eighteen reference SFF files (`SF_BST_01` to `SF_BST_18`) at `e236e32`, where the prompt counted thirteen | Measured in the pinned tree (ADR-003) |
| §8.2 | The kit's alembic migrations are vendored from commit `26b3990` | The PyPI wheel carries `src/sci_rag` alone (ADR-002) |

## Blockers

| Since | Blocker | Next command |
|---|---|---|
| 2026-10-30 | The session's git relay refuses tag pushes (branch pushes work): `git push origin alpha-1.0` ends with "unexpected disconnect while reading sideband packet", lightweight and annotated alike. The tag exists in this container only. Commit `d19224f` stays reachable as an ancestor of `main` | On the owner's machine: `git fetch origin && git tag alpha-1.0 d19224ff0b6eb809b21492d1b7a2e8fd895a0f44 && git push origin alpha-1.0` |

## Owner questions (execution prompt §13) and the defaults taken

| # | Question | Default taken | Answered |
|---|---|---|---|
| 1 | PostgreSQL as the one database | yes | no |
| 2 | Kit in-process with a local FastEmbed embedder | yes | no |
| 3 | Delete thread Q's TypeScript list, keep `docs/corpus/ethanol-sources.txt` | yes | no |
| 4 | Delete Dominion, return condition recorded | yes | no |
| 5 | Rename `demo` → `assumed` | yes | no |
| 6 | Python pin 3.12 if the kit fails on 3.13 | yes (only if it fails) | no |
| 7 | Kit REST under `/rag` on the same port | yes | no |
| 8 | Licence | none added | no |
| 9 | Accounts: tables and a membership stub only | yes | no |

## Environment facts measured in this container (2026-10-30)

- Node 22.22.0, pnpm 10.33.0, uv 0.11.32, Python 3.13.17 (3.12 also present), 4 CPUs, 15 GB RAM.
- PostgreSQL 16.15 installed (Ubuntu noble); `postgresql-16-pgvector` 0.6.0 and
  `postgresql-server-dev-16` available from apt; Docker client present with no daemon.
- GitHub reachable for clones; PyPI and npm reachable; `sci-rag-kit` 0.5.0 is on PyPI.
- `OPENFERMENT_API_KEY` is set in the session environment (value never printed);
  `ANTHROPIC_API_KEY` unset, as it should be.

## Log

### Stage 0 — 2026-10-30

- 0.1 Branch `claude/alpha-2-foundation` from `main` (`d19224f`), pushed. Tag `alpha-1.0` made at
  `d19224f`; its push is blocked (Blockers). `pnpm install --frozen-lockfile` and
  `uv sync --all-extras` succeeded. Baseline `test:core`: 2165 passed, 1 skipped, 172 deselected
  in 5 min 35 s; `test:sim`: 105 passed in 4 min 11 s. Both match the prompt's counts.
- 0.2 Handoff documents copied to `docs/handoff/2026-10/`; text extracted with `pypdf` into
  `docs/handoff/2026-10/txt/` for grep (the PDFs were readable).
- 0.3 `docs/decisions/ADR-000` to `ADR-012` written.
- 0.4 This file; the old `CLAUDE.md` moved to `docs/history/`, interim `CLAUDE.md` written.
- 0.5 PostgreSQL 16 cluster started in the container with `postgresql-16-pgvector` 0.6.0 from apt
  (`pg_ctlcluster 16 main start`); a role `sci_rag` and database `sci_rag_test` exist for the kit's
  own integration tests. Container state, gone with the container.
