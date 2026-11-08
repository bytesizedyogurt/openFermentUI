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

Two adaptations, both meant to be offered upstream:

1. A local embedder on FastEmbed (already the project's `rag` extra). The kit's settings accept
   `embedding_provider` in `{"google", "local-hash"}` only, and its `Retriever` takes an
   `embedder` argument. openFerment therefore builds its `FastEmbedProvider` and passes it to every
   kit object it constructs, and installs it as the kit's `get_embedder` answer inside the
   openFerment process. The upstream pull request would add `fastembed` to the setting and to
   `get_embedder`, with its contract test; no draft of it was ever committed to this tree (its
   history holds no `docs/upstream/`, read 2026-11-05).
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

## Implementation (stage 3, 2026-10-30)

- **Where the kit lives.** `core/openferment_core/literature/`: `kit.py` builds the kit's objects
  once per process; `collectors.py` turns what openFerment fetches or is given into the kit's
  corpus entries; `fastembed.py` is the embedder; `domain/` is openFerment's domain profile with
  the kit's fifteen prompts; `kit_alembic/` holds the kit's six migrations from the pinned commit
  with its licence, and an `env.py` of ours. They sit in the package beside `kit.py`, so the
  deployed tree finds them where the code is (Departures, §8.2, records the move from
  `core/vendor/`).
- **Settings.** Importing `openferment_core` writes the kit's `SCI_RAG_EMBEDDING_*` and
  `SCI_RAG_DOMAIN_DIR` into the environment first, because `sci_rag.db.models` sizes its vector
  column when first imported; `kit.py` refuses to load if the kit was imported with another
  dimension. The `Settings` object openFerment hands the kit reads only the values given and the
  kit's defaults: neither `SCI_RAG_*` names in the environment nor a `.env` in the working
  directory reach it.
- **Embedder and model.** FastEmbed with `BAAI/bge-small-en-v1.5` (384 dimensions), version
  `fastembed:BAAI/bge-small-en-v1.5@384`, its model file cached in `FASTEMBED_CACHE_PATH` or
  `~/.cache/fastembed`. Every kit object is handed it; `sci_rag.embed.get_embedder` and
  `sci_rag.llm.get_llm` (and the names the kit's modules imported) answer with openFerment's
  embedder and model client for any kit path that asks them. The model client is
  `llm.kit_client`, installed by the composition root (`api.py`, `literature_mcp.py`): every
  generation the kit makes (answers, HyDE, a document's graph) is a call through `llm.call`, under
  the day's cap, with the key read in one place. The kit's roles read our routes by family
  (`llm.KIT_ROLES`, since ADR-008's 6.3): `answer` reads `explain`, `extraction` reads `index`
  and `judge` reads `judge`. A model key of a caller's own (the kit's `byo_llm`) is refused
  everywhere.
- **The project is the scope.** A document is stored once (the kit's content hash) with source
  `project:<id>:<collector>`; `documents_link` holds a row per project that holds it, with the
  selection (collector, identifier, licence as stated, reason, who). `kit.ProjectService`, the
  kit's `RagService` with every read narrowed to the current project, serves the in-process
  calls, `/rag` and the MCP server alike: the sources of the project's documents go to the kit
  as its `sources` allowlist and the other documents of those sources as
  `exclude_document_ids`, so a shared document is visible to each project that linked it and to
  no other. Which documents a project holds is read through openFerment's own session, the one
  a test's transaction binds. The kit keeps one concept graph for the instance, one entity row a
  name; a project builds it over its own passages and reads it through `literature/graph.py`
  (Implementation F), and the community layer is off for every scoped request, as the kit makes
  it.
- **Engines.** asyncpg ties a connection to its loop. The calls openFerment makes run on the
  database loop through a pooled engine whose connections put `sci_rag, public` on the search
  path; it is installed as the kit's own engine, so `ingest_entries` uses it. `/rag` and the MCP
  server use an engine that keeps no connection between sessions.
- **Migrations.** `python -m openferment_core.migrations` (`pnpm db:migrate`, `pnpm db:reset`)
  runs our history and then the kit's, each version table in its own schema. The kit's `env.py`
  makes the `vector` extension in `public` first; a database whose owner may not make it gets it
  from its template or from a superuser (`pnpm ready` says which).
- **Collectors.** Europe PMC (a PMCID, a DOI or `PMID:<id>`; JATS split by section, a table as a
  pipe table so the kit keeps it as one block), OSTI (`OSTI:<id>` or an osti.gov address; the PDF
  a page a section, the record for the citation), SGD (a yeastgenome.org address), an upload (PDF,
  JATS XML, Markdown, HTML, text) and pasted text. A bare number is refused, since a PMID and an
  OSTI id look alike. The licence the source states maps to the kit's classes and fails closed
  (`collectors.licence_class`); for an upload or a paste the person chooses the class.
- **Surfaces.** `POST /api/intake/collect`, `/api/intake/upload`, `/api/intake/paste`, `GET
  /api/literature/documents`, `/api/literature/stats`; the Intake screen's "Add to this project"
  card. The kit's REST app is mounted at `/rag` with its key check on: the key is
  `OPENFERMENT_RAG_KEY` in `core/.env`, and with none set a key made in memory and never shown
  stands in, so `/rag` refuses every request; the kit, given no keys, would run open. Its CORS origins are empty, a `/rag` request names its project as an `/api` request does,
  and the kit's `/mcp` endpoint is left out of the mount. The MCP server runs over stdio
  (`.mcp.json`: `sci-rag`, `python -m openferment_core.literature_mcp`), reading the database
  address and the project from `core/.env` as openFerment's own MCP server does.
- **Tests.** Outside the `lit` marker the kit embeds with its deterministic local embedder, so
  test:core needs no model file; `pnpm test:lit` runs the tests marked `lit` with FastEmbed. CI's
  verify gets a `pgvector/pgvector:pg17` service and the model file from a cache.
- **Extraction over the kit's text (3.2).** A document's passages are its chunks in order,
  `p<index>`, each under its section path with the kit's breadcrumb taken off (`kit.passages`);
  extraction cites them, anchoring checks a quote verbatim in the passage cited, BioRepo's
  promotion rule reads them, and Witness scores a run against the values reviewers typed. The
  overlay carries the project's documents with their citations and passages, from which the
  browser makes its papers.
- **Search, answers and the report (3.3).** `kit.search` (the project's passages for a question,
  each with its passage id; `interactive` asks no model) serves BioRepo → Search, `GET
  /api/literature/search` and Postdoc's `search_passages` tool, whose seam it fills; `kit.answer`
  streams the kit's cited answer (`POST /api/literature/answer`, server-sent events, one model
  call through llm.py). The reader opens a held document at a passage. `pnpm lit:report` runs the
  kit's retrieval evaluation over its demo corpus and seed questions (vendored with the corpus)
  in a database of its own, in the configurations that ask no model, and writes
  `docs/reports/literature-retrieval.md` and `.json`. The stage 3 gate is
  `core/tests/test_literature_demo.py` under `pnpm test:lit`.
- **`pnpm ready`** adds three rows: `literature` (the vector extension, the kit's revision, the
  column's dimension, the domain profile, chunks embedded by another model), `embedder` (the
  model file cached) and `rag` (whether a key is set).

## Implementation 8 (the kit's MCP server, checked over stdio)

Called over stdio as `.mcp.json` starts it (2026-10-30), the kit's MCP server answered
`corpus_stats` with "Error executing tool corpus_stats" and nothing more: it had started with no
project, the kit's service refuses with its REST `ApiError`, and the MCP SDK (2.3) hands a client
only that line for an exception other than its `ToolError`. The kit's `stats` also query the
database before they ask for a project, so with the database down the same line came back.
`literature_mcp.py` now wraps the service as openFerment's own server answers: each call asks for
a project first, and each refusal or failure reaches the client as a `ToolError` in its words (no
project named, a document the project does not hold, a database that does not answer); it takes
`--project` as that server does. The
kit's `search_entities` and `get_entity_relationships` read the concept graph whole, every
project's entities, relationships and evidence quotes, so the server leaves them off; nothing in
openFerment builds the graph yet, and scoping them is a debt. Checked over stdio on a proof
database: with no project, a refusal in words; with `--project`, the project's 5 documents and 34
chunks, a search with its hits, an unknown document refused in words; with the database down, the
refusal with no project and, with one, the connection's failure, each in words
(`test_literature_mcp.py`).

## Implementation F (alpha 2.2 F.5: the concept graph a project builds and reads)

- **The build reads the project's chunks alone.** The kit's `extract_graph` reads every chunk of
  the store that no build has read, with no document filter. `literature/graph.py`'s `build`
  selects the project's unread chunks in the kit's order (the document's content hash, then the
  chunk's index) and hands them to the kit's own batch step ten to a batch within one document
  (`graph.batches`; `sci_rag.graph.extractor._extract_with_recovery`, underscore-private in 0.5.0,
  its signature pinned by a test): one call on the client the caller hands in, the kit's
  `extraction` role and so the `index` route, an answer it cannot read halved down to one chunk, a
  batch that fails left unstamped for the next build. A batch ends where its document ends
  (landing review, 8 November): the kit writes one description a name from the whole batch and
  files each entity and edge against the passage numbers the model names, so a batch that mixed a
  document two projects hold with one project's own could carry that project's words into the
  other's reads, wherever the model filed them against the shared passage. A batch of one document
  keeps its answer inside a document that each project holding any of its passages holds whole. A
  document shorter than ten passages takes a call of its own, so a build makes more calls than its
  passages divided by ten, and the dry run counts them. A chunk of a document two projects hold is
  read once and serves both. A batch the index route's model declines is a batch that fails: on
  the default route, Haiku alone (ADR-008, Implementation 17), it stays unstamped and is read
  again, on Haiku, by every later build, counted in `chunks_left` each time; `OPENFERMENT_ROUTES`
  naming a second index model reads it (Sonnet answered each of F.1's declines). `stop`, read
  after each batch, ends the build in its words (no key, the account's usage limit, the day's cap).
  `literature/` imports no `llm`: the command hands in the client and the stop.
- **A scoped read shows what the project's own passages prove**, by the rule the kit's retrieval
  seeds its graph walk by under a scope (`retrieve/stages/graph.py`: a name and a passage compared
  in lower case, each run of other characters one space). An entity is the project's when one of
  its evidence chunks is a passage of a document the project holds and that passage names it; a
  name the kit holds as an alias finds nothing. A description stands where a model wrote one and
  every document the entity is named in is the project's, since the kit keeps the first
  description a model wrote for the name; an entity listed with no description carries one note,
  the same whichever left it out (`graph.DESCRIPTION_NOTE`), so the note tells a project nothing
  of the documents it does not hold. A description a project once read leaves its reads when
  another project's build names the entity in a document of its own; a description kept per
  project would keep it. An edge is the project's when its evidence chunk is the project's and
  that passage names both its ends, with its document and passage id; its quote is withheld with
  a note where its words do not stand in that passage. The kit matches each name a build extracts
  against every entity's aliases across the store, so a name another project's build kept as an
  alias joins that entity at build time; where the project's passage holds that name alone, its
  reads list neither the name nor the edges that passage states of it, and the other project's
  name for the entity stays out of them. A count counts the project's passages alone.
  `ProjectService.search_entities` and `entity_relationships` read so; `stats` counts the
  project's entities and relationships and 0 communities; `fingerprint` states the project's
  corpus for a report. A read of a project that holds no passage says its documents enter on
  Intake (`graph.NO_PASSAGES`), and a read of one whose passages no build has read says which
  command builds its graph (`graph.NO_GRAPH`).
- **Communities and entity resolution stay off.** The kit reads no community under a scope, and
  resolution merges rows every project reads.
- **The graph tools are back on the `sci-rag` server (F.5.3).** `literature_mcp.build` removes the
  kit's `search_entities` and `get_entity_relationships`, which query the store whole, and adds
  openFerment's own under the same names and argument schemas, each calling the service's scoped
  read through `InWords` (the project asked for first, every failure in words) and each
  description naming the domain's types; a graph tool asked of a project that holds no passage is
  refused in `NO_PASSAGES`' words, and one asked of a project no build has read in `NO_GRAPH`'s.
  The kit's `answer_question` and `list_sources` are served as the kit wrote them, with
  descriptions in openFerment's words (`literature_mcp.DESCRIBED`). `docs/TOOLS.md` lists the server's tools from its own listing
  (`tools/reference.py`, over `literature_mcp.Unopened`, a service that opens nothing).
  Implementation 8's debt is paid.
- **The report's project lanes (F.5.4).** `pnpm lit:report --project <id>` runs
  `literature_live.py report` (the demo corpus stays `pnpm lit:report` alone, offline). Its ground
  truth is built by code from the project's kept candidates at run time (`report.truth`): a
  candidate counts when its passage is the project's, its quote stands in that passage
  (whitespace aside) and its field is the ontology's; one question a group by document, passage
  and field, its words the field's name with the organism and feed the group names, its evidence
  the group's quotes, its relevant passage their chunk, tagged `from-candidates` (a model's
  extraction no person has reviewed). No model writes or reads a question, so the kit's question
  drafter stays unused and openFerment names no role for it. Retrieval runs in `interactive`,
  `vector_only`, `keyword_only`, `full_deep`, `no_graph` and `no_hyde`, each question scored under
  the kit's rule and under the passage rule (the candidates' own chunk), with the graph and HyDE
  stages' statuses counted; `no_retracted` and `with_citations` are refused by name, since the
  first carries a scope of its own and the second follows citations outside the project. With
  `--judge`, the `judge` route grades each question's top ten in `interactive` and `full_deep`, 0
  to 2, and the kit's answer through each, on `explain`, is graded blind for grounding by the
  `judge` route; each answer and each judgement is counted under its own tally (`llm.tally`,
  handed in by the command), so it carries the model that gave it. No migration and no table: the
  run whole goes to a file under the service's data folder, outside git, and `report.public` keeps
  its numbers alone (scores with their intervals, counts, question ids, model ids, USD, seconds),
  which `--render` sets beside the demo in `docs/reports/literature-retrieval.md` and `.json`;
  `--from` rebuilds that part from a kept run whole (`report.public`), filed under the run's own
  project, so the committed report holds the numbers `public` keeps alone. `--limit` counts one
  at least. The command reads `core/.env` through `extract.load_env` (`override=False`), installs
  `llm.kit_client` where it asks a model (a build, a run; the dry run and `--from` install none),
  reads its stop from its own tally (the first call no model answered) and audits each build and
  run. `pnpm prove` step 3 lists the sci-rag server's tools over stdio in
  the proof's project and reads a graph tool's refusal, offline. F.5's offline run (8 November) measured the three
  configurations that ask no model over the Ethanol project, each question under both rules, and the graph build's
  dry run (`docs/reports/literature-retrieval.md`); `full_deep`, `no_graph`, `no_hyde`, the judge's grading and the
  answer lane wait on the account (`docs/PROGRESS.md`, Blockers).

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
