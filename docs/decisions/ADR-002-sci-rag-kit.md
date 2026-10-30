# ADR-002 — Sci RAG Kit is the literature layer, used as a library

- **Status**: accepted (provisional choice; stage 3 implements it)
- **Date**: 2026-10-30

## Context

At `alpha-1.0` openFerment has its own retrieval stack (`passages.py`, `retrieve.py`, `embed.py`,
`rerank.py`, `expand.py`, `rageval.py`, `helper_cache.py`, `core/data/index/`): a chunker, five
fused lanes, a model reranker and a scorecard. Sci RAG Kit
(`sustainability-software-lab/sci-rag-kit`, BSD-3-Clause) does the same work with section-aware
parsing, PostgreSQL storage, five retrieval stages, a concept graph, cited answers, an evaluation
harness and REST and MCP surfaces from one `RagService`.

## Options

1. Keep the bespoke stack.
2. Run the kit as a separate service and call it over REST.
3. Import the kit in-process as a library, and also mount its REST and MCP surfaces.

## Decision

Option 3. openFerment imports `sci_rag` in-process (ingester, `RagService`, graph builder,
evaluation harness) behind `literature/kit.py`. The kit's REST app mounts under `/rag` of the same
FastAPI app; its MCP server is listed in `.mcp.json`. The bespoke stack is deleted (ADR-010).
Generation runs on the kit's `anthropic:` and `openai-compatible:` model specs so a person's own
key or a local model serves it, configured from `llm.ROUTES` (ADR-008).

Two adaptations, both offered upstream:

1. A local embedder on FastEmbed (already the project's `rag` extra). The kit's settings accept
   `embedding_provider` in `{"google", "local-hash"}` only, and its `Retriever` takes an
   `embedder` argument. openFerment therefore builds its `FastEmbedProvider` and passes it to every
   kit object it constructs, and installs it as the kit's `get_embedder` answer inside the
   openFerment process. The upstream pull request (kept under `docs/upstream/sci-rag-kit/`) adds
   `fastembed` to the setting and to `get_embedder`, with its contract test.
2. A corpus collector turning openFerment's fetchers (Europe PMC JATS, OSTI PDFs, SGD entries,
   uploads, pasted text) into the kit's `CorpusEntry` rows; project scope is written into
   `CorpusEntry.source` as `project:<id>:<collector>` and passed as the `sources` filter.

## Consequences

- Dependency `sci-rag-kit==0.5.0` from PyPI under a `lit` extra, with `fastembed`.
- The kit's alembic scripts are absent from its wheel (the wheel packages `src/sci_rag` alone;
  `sci-rag` migrations walk up to the repository's `alembic.ini`). openFerment vendors the six
  migration files and their `env.py` from the pinned commit under `core/vendor/sci_rag_migrations/`
  with the kit's LICENSE, and `pnpm db:migrate` runs them.
- `SCI_RAG_EMBEDDING_DIM` is fixed to the FastEmbed model's dimension before the first migration.
- BioRepo → Search, PaperReader and the retrieval report read the kit.

## Revisit condition

The kit drops async SQLAlchemy or changes its ingestion contract; a second literature engine is
needed; the upstream pull request lands (then the in-process registration goes).

## Evidence

- PyPI `sci-rag-kit` 0.5.0, licence BSD-3-Clause, `requires-python >=3.11` (queried 2026-10-30).
- Repository at `26b3990`: `pyproject.toml` (`packages = ["src/sci_rag"]`), `alembic.ini`
  (`script_location = migrations`), `migrations/versions/0001…0006`, `src/sci_rag/config.py`
  (`embedding_provider: Literal["google", "local-hash"]`, `embedding_dim` default 1536),
  `src/sci_rag/embed/__init__.py` (`get_embedder`), `src/sci_rag/retrieve/retriever.py`
  (`embedder or get_embedder(...)`).
- The kit's test suite under the project's Python: run at stage 1 (result in `docs/PROGRESS.md`).
