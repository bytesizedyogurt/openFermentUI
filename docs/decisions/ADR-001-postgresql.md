# ADR-001 — PostgreSQL with pgvector is the one database

- **Status**: accepted (provisional choice; stage 2 implements it)
- **Date**: 2026-10-30

## Context

At `alpha-1.0` every record lives in a JSON file under `core/data/` (`biorepo.json`,
`artifacts/<hash>.json`, `guild.json`, `checks.json`, `practice.json`, `proposals.json`,
`spend.json`, `audit.jsonl`, `candidates/`, `live/`, `pureos-trains.json`, `index/`), written through
`atomic.write_text` under thread and file locks. A git merge driver reconciles `biorepo.json`
between machines and an orphan branch (`openferment-data`) carries live-run output. Browser state
(IndexedDB, `src/lib/durable.ts`) holds depositions, decisions, locks, overrides, fits, scenarios,
runs, pins, trains and conversations, so two devices disagree about the same project.

Sci RAG Kit (ADR-002) stores documents, chunks and its concept graph in PostgreSQL with pgvector.
The owner's stated end state (one lab group first, cloud-ready, accounts, private work until
published) needs a real database.

## Options

1. Keep the JSON stores and add PostgreSQL for the kit alone: two persistence models, the merge
   driver stays, browser state stays unsynchronized.
2. SQLite with a vector extension: one file per host; the kit does not support it.
3. One PostgreSQL instance with pgvector, two schemas.

## Decision

Option 3. One PostgreSQL instance, two schemas: `sci_rag` (the kit's tables, migrated by the kit's
alembic scripts) and `openferment` (ours, migrated by our alembic). SQLAlchemy 2 async for both.
Local install on the always-on host (Homebrew or Postgres.app), a `pgvector/pgvector:pg17` service
container in CI, `docker compose` as the developer default, and the distribution's packages where
neither exists (this build container).

Store modules keep their function names (`artifacts.compute`, `biorepo.write`,
`guild.write_evidence`, …) and swap their bodies to sessions; row locks and transactions replace
`_WRITE_LOCK`, file locks and atomic writes. `atomic.py` stays for export files. Artifact ids keep
the sha256-of-canonical-inputs scheme so replay works unchanged.

Schema separation (provisional, confirmed at stage 2): our tables declare `schema="openferment"`
explicitly; the kit's models declare no schema, so the kit connects as a role whose `search_path`
is `sci_rag, public`, which places its tables in `sci_rag` without patching the kit. The `vector`
extension is created once in `public` by the migrate step.

## Consequences

- `pnpm verify` needs a reachable PostgreSQL; tests use a disposable database
  (`OPENFERMENT_TEST_DATABASE_URL`) created per session with rollback per test.
- The merge driver, `data-sync.sh`, `data-prepare.sh`, `decisions-push.sh`, `sync_decisions.sh`
  and the `openferment-data` convention are deleted (ADR-010).
- The browser's Durable tier keeps UI preferences only.
- `ready.py` gains database, schema, pgvector and embedder rows; `install.sh` and `deploy.sh` gain
  the PostgreSQL steps and the alembic upgrade.

## Revisit condition

Never for the store itself. The schema split, if the two migration trees fight.

## Evidence

- `core/openferment_core/atomic.py`, `biorepo.py` (`_WRITE_LOCK`), `scripts/host/merge_biorepo.py`,
  `scripts/data-sync.sh` at `alpha-1.0`.
- Measured 2026-10-30 in the build container: PostgreSQL 16.15 installed (`/usr/lib/postgresql/16`),
  `postgresql-16-pgvector` 0.6.0 available from Ubuntu noble, no Docker daemon. The kit's
  `chunks.embedding` HNSW index needs pgvector 0.5.0 or later.
- Sci RAG Kit `src/sci_rag/db/engine.py`: one engine from `SCI_RAG_DATABASE_URL`, no connect
  arguments, hence the role-level `search_path`.
