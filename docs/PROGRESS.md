# openFerment alpha 2.0 — progress

The resume point for every session of the alpha 2.0 foundation build. Keep it current at every
checkpoint. A fresh session continues from this file and `git log` alone.

## Resume

1. Branch: `claude/alpha-2-foundation` (cut from `main` at `d19224f`). `git fetch origin
   claude/alpha-2-foundation && git checkout claude/alpha-2-foundation`.
2. Environment:
   - `pnpm install --frozen-lockfile`
   - `cd core && uv sync --all-extras`
   - From stage 2 on, PostgreSQL: `pnpm db:up` (compose.yaml), or a local PostgreSQL 16 or later
     with pgvector and a role that may create databases. `OPENFERMENT_DATABASE_URL` in `core/.env`
     (`core/.env.example` has the development address), then `pnpm db:migrate`. The tests make a
     database of their own on the server `OPENFERMENT_TEST_DATABASE_URL` names; the default is the
     compose role on 127.0.0.1:5432.
3. First tests to run: `pnpm test:core`, then `pnpm test:sim`.
4. **Next step: stage 3, step 3.3** — BioRepo → Search over the kit (`kit.retrieve`, cited
   answers through `ProjectService.answer_stream`), PaperReader over a held document's passages
   (it reads the overlay's papers today), the retrieval report from the kit's evaluation
   harness, and the stage 3 gate: `pnpm test:lit` over the demo corpus
   (`core/tests/fixtures/kit-demo/`): ingest, search with citations, answer with citations,
   extraction anchored, decision accepted, the project scope filtering results.
5. Files in flight: none.

## Current stage

Stage 3 — Sci RAG Kit — is under way: 3.1 (the kit wired in, the collectors, Intake, `/rag`, the
kit's MCP server) and 3.2 (extraction, anchoring, BioRepo and Witness over the kit's text) are
done; 3.3 is next. Stage 2 is complete: 2.1 to 2.4 put every store on
PostgreSQL, scope every request to a project, move the browser's scientific state to the service,
and passed the gate in a clean worktree. Stages 0 and 1 are complete (the tag push waits on the
owner; see Blockers).

## Last green runs

| When (UTC) | Suite | Result | Time | Commit |
|---|---|---|---|---|
| 2026-10-30 03:43 | `pnpm test:core` | 2165 passed, 1 skipped, 172 deselected | 5 min 35 s | `d19224f` (baseline) |
| 2026-10-30 03:48 | `pnpm test:sim` | 105 passed, 2233 deselected | 4 min 11 s | `d19224f` (baseline) |
| 2026-10-30 04:08 | `test:core` in a clean worktree | 2083 passed, 1 skipped, 170 deselected | 4 min 44 s | `20bd36d` (1.1) |
| 2026-10-30 04:12 | `test:sim` in a clean worktree | 103 passed, 2151 deselected | 3 min 44 s | `20bd36d` (1.1) |
| 2026-10-30 05:39 | `typecheck`, `build`, `test:core` in a clean worktree | 1929 passed, 2 skipped, 128 deselected | 4 min 28 s | `b24e997` (1.2) |
| 2026-10-30 05:44 | `test:sim` in a clean worktree | 102 passed, 1957 deselected | 4 min 9 s | `b24e997` (1.2) |
| 2026-10-30 05:43 | `test:core` with 1.3 | 1888 passed, 2 skipped, 128 deselected | 4 min 12 s | 1.3 |
| 2026-10-30 06:10 | Stage 1 gate in a clean worktree: `typecheck`, `build`, `test:core` | 1888 passed, 2 skipped, 128 deselected | 4 min 7 s | 1.6 |
| 2026-10-30 06:10 | Stage 1 gate: `test_no_seed.py`, `test:sim`, `pnpm smoke` | 45 passed; 102 passed, 1916 deselected; 11 of 11 rail entries open | 4 s; 3 min 59 s; 22 s | 1.6 |
| 2026-10-30 06:25 | `test:core` with 2.1 | 1905 passed, 2 skipped, 128 deselected | 4 min 33 s | 2.1 |
| 2026-10-30 07:16 | `test:core` with 2.3 | 1947 passed, 2 skipped, 128 deselected | 4 min 25 s | 2.3 |
| 2026-10-30 07:43 | Stage 2 gate in a clean worktree: `test:core`; the store rules with the restart test; `test:sim` | 1952 passed, 2 skipped, 128 deselected; 258 passed; 102 passed, 1980 deselected | 4 min 28 s; 28 s; 4 min 0 s | 2.4 |
| 2026-10-30 07:43 | Stage 2 gate: secrets, typecheck, plan, licences, tools, guild, state, figures, build, `pnpm smoke`, reconcile | all passed; 11 of 11 rail entries open in the project | | 2.4 |
| 2026-10-30 06:47 | `test:core` with 2.2; `check:tools`; `pnpm smoke` (own database, project made through the API) | 1920 passed, 2 skipped, 128 deselected; passed; 11 of 11 rail entries open in the project | 4 min 26 s | 2.2 |

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
| §8.2, ADR-002 | The kit's migrations live in `core/openferment_core/literature/kit_alembic/` (with its licence), where ADR-002's consequences said `core/vendor/sci_rag_migrations/`; `pnpm db:migrate` runs them through `python -m openferment_core.migrations`, which replaces `python -m openferment_core.db` | In the package beside `kit.py`, the deployed tree finds them where the code is; `db` may import nothing of the service (§7.2), so the command that runs both histories lives outside it |
| §8.2 | `/rag` serves the kit's REST routes without its `/mcp` endpoint; the kit's MCP server runs over stdio from `.mcp.json` (`sci-rag`) | Starlette does not run a mounted app's lifespan, which the kit's streamable HTTP endpoint needs; stdio is how `.mcp.json` starts a server |
| §8.2 | `/rag` asks for `OPENFERMENT_RAG_KEY` (`core/.env`), and with none set refuses every request | The kit runs open when given no keys; a key the owner sets is how a program outside the app reaches it |
| §8.2, stage 3.1 | Intake kept the corpus-paper fetch (`intake.fetch_paper`, `/api/intake/{paperId}/fetch`) and the full-text cache beside collection into the kit for one step; 3.2 removed both | Extraction read the cache until 3.2 moved it onto the kit's text, and every commit stays green |
| §8.2, stage 3.2 | Extraction anchors to the kit's chunks as passages (`p<index>`), a candidate's `sectionId` naming one; neighbouring passages of a section share the kit's overlap, so a sentence may stand in two and either anchors | The kit's chunks are its text; rebuilding sections from them would undo the overlap by guesswork, since the overlap's whitespace is the kit's own |
| §6.2, stage 3.2 | Witness scores a run against the values reviewers typed (a gold value or a correction on a decision), where alpha 1.0 scored it against the seed's curated records | The seed is gone (ADR-010); a value a person typed is independent of the extractor, and one accepted as the extractor wrote it is not |
| stage 3.2 | The overlay carries every held document's passages on every load, as the fetched papers' sections were | The reader, the review card and Witness read a paper's sections from the store today; reading them on demand is stage 7's |
| §10 stage 1.1 | Section 5 runs in the order 5.4 + 5.3 (one commit), 5.1, 5.2, 5.5, 5.6, 5.7 | `demo.py`, `retrieve.py` and `rageval.py` were the heaviest users of the program machinery and build their fixtures through each other; deleting them first spares edits to files deleted one step later, and a commit between 5.4 and 5.3 could not be green |
| §5.3 | `demo.py`'s stand-in evaluator and stand-in records moved to `core/tests/standins.py` (test-only) | Thirteen kept test files (Proforma, fermOS, params, pureOS, tools) test binding, override, ceiling and run-contract rules on them. Stage 4 replaces them with fixtures read from library plants (debt recorded below) |
| §5.4 | `search_passages` stays registered, with one seam (`tools/passages.py: search`) that answers "no literature index exists yet" | Postdoc's quote validation and its tests keep the passage contract; stage 3 fills the seam with Sci RAG Kit. The whole-sentence rule moved to `quotes.py` |
| §10 stage 1.1 | 5.1, 5.2, Dominion and the retired guards (from 5.6) are one commit, 1.2 | The program machinery, the seed and Dominion share the store, the types, `module_stores` and `models`, and the retired guards import the seed: no commit between them could be green |
| §5.2 | Tests that held seeded content were deleted with it; rule tests that only used it as material now run on fictional fixtures: `core/tests/fixtures/test-corpus.json` (placeholder papers and records, the `test_corpus` fixture), placeholder Guild skills and protocols in the alpha 1.0 shape, small fictional projections inside tests, and a test-only categorical field | A4 forbids seeded values under `core/`; the rules (anchoring, review decisions, retrieval, coverage, Guild) stay tested |
| §5.2 | Eval set O (`evalo.py`, `pnpm eval:o`) and the identifier tooling (`identifiers.py`, `scripts/resolve-identifiers.py`, `pnpm ids:*`) are deleted | Eval set O's ten questions named the seed; the identifier tooling patched DOIs into the TypeScript seed |
| §5.5, §10 stage 1 | Stage 1 deletes the merge driver, the data-sync, data-prepare and decisions-push scripts, `sync_decisions.sh` and the `openferment-data` branch convention. The file stores (`core/data/*.json`, `audit.jsonl`, `artifacts/`, `candidates/`, `live/`) and the browser's Durable scientific state stay until stage 2 replaces each with its PostgreSQL store, as stage 2 step 2 says; `core/data/biorepo.json` stays tracked until then | Untracking `biorepo.json` would make the live Mini's next pull delete the review decisions people made there (§11.1); stage 2 imports them into PostgreSQL |
| §7.4 | Tables `overrides`, `fits`, `trains` and `practice_scenarios`, and `projects.settings`, beyond the list; each table keeps its lookup keys as columns and the rest of a row as `body`, the Pydantic model as JSONB | §5.5 moves those browser states to the server; the Pydantic models stay the one description of content (ADR-001, Implementation) |
| §5.5, stage 2 | The fetched full texts (`core/data/fulltext/`) and the fetched genome-scale models (`core/data/models/`) stay files | They are caches of documents fetched from outside, fetched again when gone; stage 3 hands documents to Sci RAG Kit's tables |
| §5.5, stage 2 | The browser keeps an outbox: review decisions, Guild changes and project rows the service has not yet acknowledged, saved in IndexedDB until sent; and three preferences, who is deciding, who is acting in Guild, and the lessons finished here | A deposition at the bench must survive a reload while the service is away (the reason Durable state existed); the outbox holds nothing the service already has |
| §7.4, stage 2 | A Live conversation is kept whole in `conversations.body`; `turns` and `tool_calls` wait for stage 6 | Stage 6 gives Postdoc its memory on the server and fills them |
| §7.4, stage 2 | `project_state.py` checks a page's row for kind, id and shape, and keeps its content as sent | The content's rules run where they always ran; stage 7 generates the page's types from Pydantic models |
| §5.5, stage 2 | `core/data/biorepo.json` stays tracked, and nothing reads it | Removing it from git would delete a live instance's working copy on its next pull, decisions and all, before they could be carried into a project (§11.1). `pnpm db:import-alpha1` carries it; it leaves git once the owner says the live instance's import read right |
| §4, §5.2 | The record fields, the vocabulary (carbon sources and unit operations) and the unit tables live in `core/openferment_core/schema/` (`fields.yaml`, `vocabulary.yaml`, `units.json`), with no range and no example value; `src/data/ontology.ts` and `vocabulary.ts` mirror them, held equal by `test_schema.py` through the fixture `pnpm export:unit-fixtures` writes. BioRepo's typed-value refusal is renamed `range` → `unit`; `pyyaml` is a direct dependency | The service needs the fields without the TypeScript seed; a range is a number about a field (ADR-010) |

## Blockers

| Since | Blocker | Next command |
|---|---|---|
| 2026-10-30 | Owner action, before the first alpha 2.0 deploy on the live Mini: its records are files under `core/data/` until carried into a project. Nothing is lost by waiting: the service no longer writes them | On the Mini: `brew install postgresql@17 pgvector && brew services start postgresql@17`; `scripts/host/install.sh` (makes the database `openferment` and names it in `core/.env`; when `core/data/biorepo.json` holds uncommitted decisions, the old deploy asks to commit and push them first, which keeps them); then `pnpm db:import-alpha1 --name "Alpha 1.0 records" --by "<your name>"`, and `OPENFERMENT_PROJECT=<the id it prints>` in `core/.env` for the nightly extraction |
| 2026-10-30 | The session's git relay refuses tag pushes (branch pushes work): `git push origin alpha-1.0` ends with "unexpected disconnect while reading sideband packet", lightweight and annotated alike. The tag exists in this container only. Commit `d19224f` stays reachable as an ancestor of `main` | On the owner's machine: `git fetch origin && git tag alpha-1.0 d19224ff0b6eb809b21492d1b7a2e8fd895a0f44 && git push origin alpha-1.0` |

## Known debts (each names the stage that pays it)

| Debt | Paid at |
|---|---|
| `core/tests/standins.py` carries invented stand-in records (on real strain ids) and a closed-form evaluator for rule tests | stage 4: fixtures from `biorefineries` library plants |
| `program` survives as pureOS's chemical-set key (`TrainSpec.program`), and as a field of `FlowsheetInfo`, `VesselSummary`, `TrainSummary` and `TrainProposal`; the UI no longer shows or filters by it; projects (stage 2) took the scoping, so what remains is the chemical-set key | stage 4 (the adapter) |
| Proforma tool rules that need a successful run of a seed scenario (`run_flowsheet` keeps one run and audits it; `stream_table` on a scenario's run) lost their tests with the seed scenarios | stage 5, when scenarios live in projects |
| The vessel's organism check reads the yeast program's species from a strain catalogue that is empty; its test supplies one | stage 3 (strains with a project's records) or stage 4 |
| `test_proforma_slow.py` and `flowsheets/cornstover_benchmark.py` still state the benchmark price this build once measured (1.968 USD per gallon); the browser no longer shows it | stage 4: the adapter holds a library plant to its package's own test values |
| `units.json` maps `wt%` and `% (w/w)` to `% CDW`, aliases written for the PHA program | the vocabulary review at stage 3 |
| `docs/TOOLS.md` was edited by hand to remove Dominion and the program switch | stage 6 regenerates it (A5) |
| `src/engine/geneos/enumeration` (Dominion era) still serves RunbookDetail's funnel | stage 7 |
| Dead service paths the deletions left: the storage machinery (`kinetics.py`'s N and Q states, `fermos._no_broth_product`'s store-in-cells branch, `proforma.fit_info`'s store branch), `proforma._strain_labels`' program map, `proforma.basis_inputs`' `cap` and the yield cap in `_specs`; `fermos.NAMED_NOTE` still says "program" (its text is hashed into every simulation's basis) | stage 4, with the adapter |
| Catalogues that left with the seed are empty in production and supplied by fixtures in tests: held scenarios, the strain catalogue and its aliases, the proposer's products and hosts. Until a project's records carry them, every pureOS proposal is refused for want of a host on file. Stage 2 gave each project its tables; what fills them is the literature | stage 3 (records), stage 5 (scenarios) |
| No offline test computes on a published genome-scale model (Yeast9 and iMM904 need their fetched files); a model add-on applied in the worker, and a metabolite-defined product's demand through the worker, are untested | stage 4 |
| `test_proforma.py` holds the package's own regression values and this build's benchmark price to test the parser | stage 4 (A4 review) |
| `core/tests/standins.py` keeps a closed-form ethanol evaluator, stand-in yeast records and `STANDIN_THEORETICAL` | stage 4 (with the row above on stand-ins) |
| `pnpm smoke` opens the rail entries and checks nothing more; alpha 1.0's smoke also walked review, deposition, the runs and the redirects against the service double | stage 7 extends it over the real service |
| `test_biorepo.py::test_the_committed_file_is_the_model_and_starts_empty` holds the shape of a tracked file nothing reads | when `core/data/biorepo.json` leaves git (owner action above) |
| The host scripts' PostgreSQL steps (`ensure_database`, the migration in `deploy.sh`, the nightly's settings) have run only as `bash -n` here: this container is not a Mac | the owner's first install on the Mini |
| `pnpm db:up` (compose.yaml, `pgvector/pgvector:pg17`) has never run: this container has no Docker daemon, so stages 2 and 3 run on the distribution's PostgreSQL 16 with pgvector 0.6.0. CI's verify runs the same image as a service from 3.1 on (the workflow had no database through stage 2, so verify failed in CI on the stage 2 pushes) | the first CI run of 3.1, or the owner's machine |
| The kit's MCP server (`literature_mcp.py`) has run only as an import here: the session's MCP clients start from `.mcp.json` at session start | the next session, or the owner's Claude Code |
| `src/data/nav.ts` still calls the rail "THE TWELVE" and exports `ELEVEN` (ten destinations since Dominion left) | stage 7 |

## Owner questions (execution prompt §13) and the defaults taken

| # | Question | Default taken | Answered |
|---|---|---|---|
| 1 | PostgreSQL as the one database | yes | no |
| 2 | Kit in-process with a local FastEmbed embedder | yes | no |
| 3 | Delete thread Q's TypeScript list, keep `docs/corpus/ethanol-sources.txt` | yes | no |
| 4 | Delete Dominion, return condition recorded | yes | no |
| 5 | Rename `demo` → `assumed` | yes | no |
| 6 | Python pin 3.12 if the kit fails on 3.13 | no pin: the kit's suite passed on 3.13.17 (1584 passed, 31 skipped) | measured |
| 7 | Kit REST under `/rag` on the same port | yes, behind `OPENFERMENT_RAG_KEY` | no |
| 8 | Licence | none added | no |
| 9 | Accounts: tables and a membership stub only | yes | no |

## Environment facts measured in this container (2026-10-30)

- Node 22.22.0, pnpm 10.33.0, uv 0.11.32, Python 3.13.17 (3.12 also present), 4 CPUs, 15 GB RAM.
- PostgreSQL 16.15 installed (Ubuntu noble); `postgresql-16-pgvector` 0.6.0 and
  `postgresql-server-dev-16` available from apt; Docker client present with no daemon.
- GitHub reachable for clones; PyPI and npm reachable; `sci-rag-kit` 0.5.0 is on PyPI.
- `OPENFERMENT_API_KEY` is set in the session environment (value never printed);
  `ANTHROPIC_API_KEY` unset, as it should be.
- Stage 2: a role `openferment` (password `openferment`, may create databases) and a database
  `openferment_dev` on the local cluster, for the development address and the tests' default.
  Container state, gone with the container.

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

### Stage 1 — 2026-10-30

- 1.1 (`20bd36d`) Sections 5.3 and 5.4 in one commit: `demo.py` and the demo scripts, fixtures
  and shots; the bespoke retrieval (`passages.py`, `retrieve.py`, `embed.py`, `rerank.py`,
  `expand.py`, `rageval.py`, `helper_cache.py`, the `/api/rag/*` routes, `src/lib/rag.ts`,
  `RetrievalScorecard`). `search_passages` keeps one seam for stage 3; the whole-sentence rule
  moved to `quotes.py`; the stand-in evaluator and records moved to `core/tests/standins.py`. The
  browser's six service clients share `src/lib/http.ts`. Python's 3.13 kept (Q6).
- 1.2 Sections 5.1 and 5.2, with Dominion and the retired guards from 5.6, in one commit
  (Departures). The program machinery, the TypeScript seed and its projections, Dominion, the
  PHA draft flowsheet, PHB in geneOS, the storage family, the authored cost surfaces, eval set O,
  the identifier tooling and the demo leftovers the double served (`fixtures/prototype`) are
  gone; `docs/corpus/ethanol-sources.txt` keeps thread Q's identifiers. The record fields, the
  vocabulary and the unit tables live in `core/openferment_core/schema/`, mirrored by the
  browser and held equal by `test_schema.py`. Tests of deleted content went with it; rule tests
  run on fictional fixtures; `test_no_seed.py` holds A4. Four helper agents fixed the screens
  (by group) and two the Proforma and geneOS test families in parallel, each on its own files.
- 1.3 Section 5.5's git-borne data movement: the record-level merge driver (`merge_biorepo.py`,
  `merge-biorepo`, `.gitattributes`, `register-merge-driver.mjs`, the `prepare` script), the
  `openferment-data` branch and its `data-sync.sh`, `data-prepare.sh`, `decisions-push.sh` and
  `scripts/host/sync_decisions.sh` (`deploy.sh --keep-decisions` with it), and their tests.
  `session-start.sh` no longer pulls or prepares data. The stores stay for stage 2 (Departures).
- 1.4 The rest of section 5.6: `react-router-dom` and `recharts` (`check:figures` now refuses any
  recharts import), `src/engine/retrieval.ts`, the offline ingest timer and the job clock it ran
  on (`ingestPaperScripted`, `tickJobs`, `ui.simSpeed`, `Job.real`), the unread store fields
  (`ui.bannerDismissed`, `checkpointAnswers`, `collections` with BioRepo's collection filter),
  the stream replay the deleted service double sent, the clearance, collection and authored
  scenario types, and every client export nothing referenced.
- 1.5 Section 5.7: `STATE.md`, `README.md`, `COMPONENTS.md`, `THIRD_PARTY.md` (its 2026-10-21
  listing; the licence check regenerates the live one at the root), `BUILD-SPEC.md`,
  `docs/build/`, `docs/OF-COR-001.md` and `docs/DEMO.md` moved to `docs/history/` with 2026-10-21
  in their names, beside `CLAUDE-2026-10-21.md` from stage 0. An interim `README.md` points at
  this file, the decisions and `CLAUDE.md` until stage 8 writes the replacements.
- 1.6 The stage 1 gate. `scripts/smoke.ts` (`pnpm smoke`, in `verify` after the build) starts the
  real service on loopback with `dist/` mounted and a temporary data directory, opens each of
  the eleven rail entries in Chromium, and fails on a console error, an uncaught exception, the
  screen boundary's card, the not-found page, a near-empty main region or a 500 from the
  service. It calls the project's Python directly when `core/.venv` exists (from a second
  worktree, `uv run` would re-point the shared editable install) and launches the installed
  Chromium when the repository's Playwright expects another build. The gate ran in a clean
  worktree of the commit's tree: all green (Last green runs). Sections 10.1.3 (the thread Q list)
  and 10.1.4 (the kit's suite, the Python pin) were done at 1.2 and stage 0.

### Stage 2 — 2026-10-30

- 2.1 `core/openferment_core/db/`: one async engine over asyncpg reached by synchronous callers
  through one owned event loop (`db.run`, `db.arun`), one transaction per top-level call
  (`db.session`), a transaction-scoped advisory lock (`db.lock`), 30 tables (the 26 of §7.4 and
  four more, Departures) as SQLAlchemy Core with a JSONB `body` (ADR-001, Implementation), alembic `0001_initial`, and
  `python -m openferment_core.db migrate | reset NAME | revision` behind `pnpm db:migrate` and
  `pnpm db:reset`; `compose.yaml` and `pnpm db:up` for a developer's PostgreSQL 17. The tests make
  one database per session on first use and roll every test back (`conftest.py`); `test_db.py`
  holds the migration equal to the models, the rollback, the joined sessions, the lock under
  eight concurrent writers, and the refusals. Dependencies: `sqlalchemy[asyncio]`, `asyncpg`,
  `alembic` (greenlet's `MIT AND PSF-2.0` joins the allowed licence strings). `check:secrets`
  refuses a database address in the browser and a database password in a tracked file for a host
  off loopback.
- 2.2 Projects (ADR-005, Implementation): the `projects` package (`current()`, `using()`, create,
  get, list; ids made from names), `/api/projects`, and a middleware that sets each request's
  project from `X-OpenFerment-Project` or `?project=` (404 for one the database does not hold,
  422 for a malformed one, 503 in words when the database does not answer; health and the
  project routes act in none). The audit log is the `audit` table (`audit.append` and `read`
  keep their names, scoped to the current project); making a project is audited. The MCP server
  reads `OPENFERMENT_PROJECT` and the database address from the environment or `core/.env` by
  name. The client remembers the last-open project, names it on every call, opens the only one
  held, and shows a chooser in the top bar and a notice above every screen while none is open.
  `pnpm smoke` now makes a database of its own, makes a project through the API, checks every
  screen opens inside it, and drops the database; `check:tools` runs its gated writes on a
  database and project of its own. Threads take their project with them (the ask stream copies
  its request's context; a thread a test starts finds `OPENFERMENT_PROJECT`). `test_projects.py`
  holds the scoping rules. Migration 0001 was edited before any instance ran it: rows are timed
  by `clock_timestamp()`, so the rows of one transaction keep their order.
- 2.3 Every store on its table, function names and refusals kept: spend (the machine's day across
  projects, a reservation a row until it settles; a database that does not answer closes the
  gate as `SpendUnknown`; live tests charge the real database), BioRepo's decisions (one row per
  decision in order, an undo a row too, `read()` replaying the rows; the decided candidate kept
  with its decision), the extraction candidates (`model` and `hand` rows per paper), artifacts,
  Guild's ledger (policy in `projects.settings`) and checks, Practice, proposals (with
  `audit.add` in the store's transaction), and pureOS's kept trains. Three helper agents ported
  Guild and checks, Practice and proposals, and artifacts and kept trains in parallel, each on
  its own files; each lock-held read-check-write has a test with writers on separate
  connections. `db/rows.py` holds the row reads and writes the stores share. Content columns
  are `json` (key order is kept: a simulation's curves are drawn in it). `ready.py`'s data row
  reports the database (set, answering, at head, what it holds). The browser's scientific state
  moved to the service (`project_state.py`, `GET/PUT/DELETE /api/state`): depositions,
  measured evidence, adopted runbooks and locks, overrides, fits, scenarios, trains made and Live
  conversations load when a project opens; every change is diffed into an outbox kept in
  IndexedDB until the service acknowledges it (`src/lib/projectState.ts`, `pnpm check:state`);
  a snapshot from before alpha 2.0 is carried to the open project once; a browser reset never
  takes back a row on the service. `check:tools` reads row writes as it read file writes.
- 2.4 The gate's pieces. `test_restart.py`: a real service process on a committed database makes a
  project, keeps a train, a lock and a Guild lead through the API, stops; a second process serves
  every row as it was (11 s). `import_alpha1.py` (`pnpm db:import-alpha1 --name --by [--data]`)
  carries an alpha 1.0 data directory into a new project, read and checked first, written in one
  transaction, the files left in place; `test_import_alpha1.py`. Host scripts: `lib.sh` gains
  `env_setting` (reads `core/.env` by name, never the key) and `ensure_database`; `install.sh`
  makes the database and names it; `deploy.sh` migrates on every deploy and sends decisions
  still in `core/data/biorepo.json` to the import; `nightly.sh` reads the database and the
  project, and extraction waits when no project is named. `session-start.sh` names the
  development database when PostgreSQL answers, and migrates.

### Stage 3 — 2026-10-30

- 3.1 Sci RAG Kit wired in (ADR-002, Implementation). The `lit` extra (`sci-rag-kit==0.5.0`,
  `fastembed==0.9.0`; the old `rag` extra goes) and `python-multipart` for uploads.
  `literature/`: `kit.py` (settings from openFerment's values alone, the kit's factories answering
  with FastEmbed and `llm.kit_client`, a pooled engine on the database loop installed as the
  kit's own, an engine without a pool for `/rag` and MCP, `ProjectService` narrowing every read
  to the current project, `ingest`, `retrieve`, `document`, `documents`, `stats`, `rest_app`),
  `collectors.py` (the fetchers and splitters moved out of `intake.py`, plus JATS citation
  metadata, Markdown with tables as pipe tables, licence classes failing closed, OSTI records,
  `by_identifier`, uploads and pasted text), `fastembed.py` (a lasting model cache),
  `domain/` and `kit_alembic/env.py`. `migrations.py` runs both histories behind `pnpm
  db:migrate` and `db:reset`. Intake: `POST /api/intake/collect`, `/upload`, `/paste`, `GET
  /api/literature/documents`, `/stats`, and the "Add to this project" card on the Intake screen.
  The kit's REST app at `/rag` behind `OPENFERMENT_RAG_KEY` and the project header; its MCP server
  in `.mcp.json` (`sci-rag`). `pnpm ready` gains `literature`, `embedder` and `rag` rows. The
  `lit` marker and `pnpm test:lit` (in verify); outside it the kit embeds with its local
  deterministic embedder. Tests: `test_collectors.py`, `test_literature_kit.py` (stored once,
  held by each project that collects it; scoped retrieval, documents, stats, answers; settings
  and factories; `/rag` with and without its key and project), `test_fastembed.py` (`lit`: the
  kit's embedding contract), the Intake API tests. CI: a `pgvector/pgvector:pg17` service and the
  FastEmbed model cache.
- 3.2 Extraction and anchoring over the kit's text. `kit.passages` (a document's chunks in order,
  `p<index>`, the breadcrumb taken off) and `kit.held` (every held document with its passages, in
  three reads); `extract.passages` serves extraction and BioRepo, refusing a document the project
  does not hold (`NothingToAnchor`, 422 at the endpoint); `extract_all` runs over the project's
  documents. BioRepo's `fulltext` rule reads the kit's passages and its `paper` rule accepts a
  document the project holds. Witness scores against `reference_records`: what reviewers typed,
  and a corpus file's curated records where a test holds one. The full-text cache, `fetch_paper`,
  the corpus fetch and status routes, the nightly fetch batch, `pnpm intake:fetch`, `IntakeStatus`
  and the store's timed ingest go; the overlay's papers are the project's documents with their
  citations, from which the store makes its papers (`Paper.held`); Intake's screen is the
  collection card beside the project's documents with Extract. The Intake tool's `fetch` collects
  by identifier (`intake.collect`); Intake's module rows are the project's documents. Tests: the
  `held_documents` fixture serves passages to rule tests; `test_literature_kit.py` extracts over
  the kit's own passages, takes a gold decision and has Witness score the run.

