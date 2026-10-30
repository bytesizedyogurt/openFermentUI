# openFerment — working guidance

- C: Labels: **R** a requirement, its source named; **P** the owner's preference; **C** a provisional choice, its revisit condition in the decision record named. `core/tests/test_guidance.py` holds this file under 250 lines with every line labelled.
- C: `docs/PROGRESS.md` is the resume point: read its **Resume** section first, then `git log --oneline -30`.

## Mission and scope

- R: openFerment is an open platform in which a person directs Postdoc, an AI research coordinator, through bioprocess engineering work, and every claim, number and result stays inspectable back to its source, its calculation and its assumptions (execution prompt of 29 October 2026, §1).
- R: The first domain is cellulosic ethanol from characterized biomass, served by BioSTEAM's `biorefineries` library plants (§1).
- R: Four components carry it: PostgreSQL is the one store, Sci RAG Kit the literature layer, BioSTEAM the engine through one adapter, and SFF the flowsheet record (§1; ADR-001 to ADR-004).
- R: The repository holds software alone: no composition, yield, price, titre, strain fact or paper's finding is typed in code or seed, and science arrives at run time through Intake and the library plants (§1 item 7; `core/tests/test_no_seed.py`, acceptance A4).
- R: Versions, ports, tolerances, unit-conversion factors, file hashes and the library's own regression values read at run time count as software (§1 item 7).
- R: Out of scope for alpha 2.0: accounts and multi-user access (a membership stub only), kinetic response models, optimization, bench execution, a public licence, engines beyond BioSTEAM, specialist or fine-tuned agents, a visual redesign (§1).
- R: Keep Guild, Primer, Deposition and the kinetics families as they are, beyond the store and type changes that reach them (§11.5).

## Run and test

- C: Install: `pnpm install --frozen-lockfile`, then `cd core && uv sync --all-extras`; this container runs Python 3.13.17 and CI runs 3.12.
- C: Database: PostgreSQL 16 or later with pgvector. `pnpm db:up` starts `compose.yaml`'s `pgvector/pgvector:pg17`, or `OPENFERMENT_DATABASE_URL` in `core/.env` names a local server (`core/.env.example` has the development address); then `pnpm db:migrate` migrates both schemas, `openferment` and the kit's `sci_rag` (ADR-001).
- C: The tests make databases of their own on the server `OPENFERMENT_TEST_DATABASE_URL` names (default: the compose role on 127.0.0.1:5432) and drop them after; `pnpm db:reset` remakes the development database.
- C: `pnpm verify` is the gate: sixteen stages in ADR-011's order, `check:secrets` first, about twenty minutes here; CI runs it with a pgvector service, then `pnpm prove`.
- C: `pnpm test:core`: offline, no key, no network, about five to six minutes; it leaves out the markers `sim`, `lit`, `slow` and `live`.
- C: `pnpm test:sim` (marker `sim`) starts the real BioSTEAM worker: a cold BioSTEAM import takes about 31 s and a reference plant builds in about 17 s; the suite takes about seven minutes.
- C: `pnpm test:lit` (marker `lit`) runs Sci RAG Kit with FastEmbed's model over the kit's demo corpus; the model file comes from Hugging Face once and stays cached in `.cache/fastembed`.
- C: `pnpm test:slow` (marker `slow`) and `pnpm test:live` (marker `live`: a real network call, most needing the key and spending) run by hand, outside verify.
- C: `pnpm prove` runs the proof (`scripts/prove.py`, steps 1 to 9) on a database of its own, with no key and the network refused; run `pnpm build` first, since step 9 walks the built app in Chromium; `--steps 3,8` proves the steps named with what they stand on.
- C: `pnpm ready` (or `pnpm ready --offline`) says in rows whether the service can run: the database, both schemas, pgvector, the embedder, the model routes and the key.
- C: `pnpm eval seed` and `pnpm eval run [--live]` keep and score Postdoc's evaluation set in the project `OPENFERMENT_PROJECT` names.
- C: `pnpm gen:api`, `pnpm gen:tools` and `pnpm gen:components` write `docs/api/openapi.json` with `src/api/types.gen.ts`, `docs/TOOLS.md` and `COMPONENTS.md`; verify fails on drift, so regenerate a generated file and leave it unedited by hand.
- C: `pnpm smoke` opens every rail entry against the real service and needs a build; `pnpm dev` serves the client on Vite.
- R: `pnpm test:core` green before every commit; push after every step; never force-push; never commit `core/.env` or a database dump (§11.2).
- C: `test:sim` and `test:lit` green before a push that touches what they test (§11.2 held them to each stage gate of the build).
- C: Run a long suite in the background with its log in a file and wait for it; edit no Python while a suite runs.

## Verified constraints and sources

- R: BioSTEAM 2.54.0, thermosteam 0.54.2 and biorefineries 2.35.1 are pinned in `core/uv.lock`, under the NCSA licence (§3.2).
- R: BioSTEAM, thermosteam, biorefineries, the vendored SFF toolkit and cobra run in worker processes (`core/openferment_core/workers/`), one JSON request a line; the service process imports none of them (§7.1; `core/tests/test_boundaries.py`).
- R: The corn stover plant holds nine of its package test's eleven values on these pins; installed equipment cost and electricity consumption fail the package's own test here too, and the proof holds each to what the package's code measures (ADR-013; `docs/reports/library-regression.md`).
- R: Sci RAG Kit 0.5.0 (`sustainability-software-lab/sci-rag-kit` at `26b3990`, BSD-3-Clause) runs in process; its suite passed on Python 3.13.17, and its migrations are vendored in `core/openferment_core/literature/kit_alembic/` (ADR-002).
- R: The kit embeds locally with FastEmbed's `BAAI/bge-small-en-v1.5` at 384 dimensions, a dimension fixed in the pgvector column at migration (ADR-002).
- R: The SFF toolkit (`pisces-standard-flowsheet-format` at `e236e32`, MIT, schema 0.2.4) is vendored in `core/vendor/pisces_sff`; of its eighteen reference files, seventeen declare SFF 0.0.3, fail the 0.2.4 schema and are kept as records with their findings (ADR-003).
- R: No importer rebuilds a BioSTEAM plant from an SFF file: a file is the record, and a recipe (a load script with a pinned environment) is the executable (§3.4).
- R: Forced tool use (`tool_choice` "tool" or "any") is refused by the models with HTTP 400.
- R: Every model call goes through `core/openferment_core/llm.py` and its routing table `llm.ROUTES`, under the day's cap `OPENFERMENT_DAILY_BUDGET_USD` (25 USD by default, `spend.py`) (ADR-008).
- R: The Anthropic key lives in `core/.env` (gitignored, mode 600) as `ANTHROPIC_API_KEY`; in a cloud session it arrives as `OPENFERMENT_API_KEY`, and `bash scripts/session-start.sh` writes `core/.env` (§7.6).
- R: Leave `ANTHROPIC_API_KEY` unset in a session's own environment: Claude Code reads that name.
- R: The key never appears in a response, a log, a commit or the client bundle; `pnpm check:secrets` is verify's first stage (§11.1).
- R: The service binds `127.0.0.1`; the loopback bind and `core/openferment_core/guard.py` are the access control until accounts exist (§7.6, §11.5).
- R: Provenance is computed by code from inputs and origins (`basis.py`); no model or person sets it (ADR-006).
- R: A record's value stands inside the verbatim quote it anchors to, in a unit its field is denominated in; a model estimate never enters a record store, and each store refuses one (ADR-006; `core/tests/test_estimates.py`, acceptance A6).
- R: A number in a Postdoc claim or a tool input stands only in a typed quantity with its origin; a claim with a number in its words is dropped and counted (ADR-006).
- R: Every scientific row carries `project_id`, `created_by` and `created_at`; every route beside health and the projects list acts in one project, named by `X-OpenFerment-Project`, and the OpenAPI document marks each operation's scope (ADR-005; acceptance A5).
- R: Text inside a tool result is evidence for the model to weigh; it never changes permissions.
- R: Guild personnel data never enters git.
- R: `src/screens/Deposition.tsx` is a glove-tolerant full-screen takeover (810 px portrait, 44 px targets, 7:1 step-text contrast, no hover affordance); extend it and keep its header comment.
- R: Dependencies stay inside the permissive families in `core/licences.toml` (`pnpm check:licences`); the kit's and the toolkit's licences are recorded there, and the project carries no LICENSE file (ADR-012; acceptance A8).
- R: Never edit a live instance's database by hand; migrations alone change it (§11.5).

## Architecture decisions

- C: Fresh slate: every rule written before this build was classified, and the old guidance is evidence (ADR-000).
- C: PostgreSQL with pgvector is the one database; a row keeps its lookup keys as columns and the Pydantic model as JSONB `body` (ADR-001).
- C: Sci RAG Kit is an in-process library with a local FastEmbed embedder; its REST serves under `/rag` behind `OPENFERMENT_RAG_KEY`, and its MCP server runs over stdio (ADR-002).
- C: SFF is the flowsheet record: every engine run writes a validated, scored file, files import as records, and a flowsheet module is an SFF recipe (ADR-003).
- C: BioSTEAM runs through one adapter (`engine/library.py`) for library plants and openFerment's flowsheets alike, each plant built fresh (ADR-004).
- C: Projects replace programs: everything a person keeps belongs to one project (ADR-005).
- C: Typed quantities with origins (`library-default`, `record`, `artifact`, `person-assumption`, `model-estimate`) replace Rule 1; an estimate reaches a scenario and never a record (ADR-006).
- C: The client's types are generated from the service's OpenAPI document into `src/api/types.gen.ts` (ADR-007).
- C: Postdoc's conversations, turns and tool calls live on the server, and models are routed by family (`plan`, `explain`, `extract`, `index`, `judge`) in one table (ADR-008).
- C: The UI is the existing React application, kept and wired to the server, with each project at its own address `/p/:project` (ADR-009).
- C: Deleted: programs, the TypeScript seed and its projection, the demo infrastructure, the bespoke retrieval stack, the file stores and Dominion (ADR-010).
- C: The guards and verify's sixteen stages (ADR-011).
- C: The licence stays undecided, and no LICENSE file is added until the owner chooses (ADR-012).
- C: The corn stover plant's two values its package's own test fails on these pins are held to the package's own measurement (ADR-013).
- C: The browser's Durable snapshot keeps preferences and the writes the service has not acknowledged (ADR-014).

## Communication contracts

- C: REST: FastAPI routes in `core/openferment_core/api.py`; `docs/api/openapi.json` is generated and marks each operation's project scope (`x-openferment-scope`); a refusal is a 422 in words.
- C: SSE: `GET /api/events?project=` streams `job.*`, `tool.call` and `tool.result`, `artifact.kept` and `turn.*`, with ids a page resumes from (`docs/api/postdoc.md`).
- C: Postdoc: conversations, turns, a claim's typed values, the routing table and the evaluation set (`docs/api/postdoc.md`).
- C: The worker protocol: JSON lines, every op with its request and result schema (`docs/api/workers.md`).
- C: Engine runs: a run's inputs with their origins, its outputs, tables, SFF file and versions (`docs/api/runs.md`).
- C: SFF: the schema version, the record kept for a file, and what openFerment adds in `metadata` (`docs/api/sff.md`).
- C: Studies: scenarios, comparisons, runbooks and the export package (`docs/api/studies.md`).
- C: Intake: the collectors, the `CorpusEntry` fields and the routes documents enter by (`docs/api/intake.md`).
- C: The tool registry: `core/openferment_core/tools/__init__.py` is the one place a tool exists, and `docs/TOOLS.md` is generated from it (`pnpm gen:tools`).
- C: MCP: the `openferment` server over the registry, acting in the project `--project` names, and the kit's `sci-rag` server, both listed in `.mcp.json` (`docs/TOOLS.md`).
- C: The package map: `COMPONENTS.md`, generated from `core/tests/test_boundaries.py` (`pnpm gen:components`).

## Working assumptions

- C: The live instance is one Mac mini serving its owner on loopback (`scripts/host/`); accounts wait as a membership stub (ADR-005).
- C: Anthropic is the one served provider; a route naming another provider's model is passed over in words (ADR-008, Implementation 6.3).
- C: A library plant carries its package's own numbers; a person's value or a model's estimate enters as an override with its origin (ADR-004, ADR-006).
- C: The local embedder serves a project's corpus at this scale; `pnpm lit:report` measures retrieval against the kit's seed questions (ADR-002).
- C: The hand-kept `src/data/types.ts` stands beside the generated types, held to the service by `check:plan`, until the screens move over one by one (ADR-007).
- C: A review decision's provenance arrives as the label of the reviewer's action, in alpha 1.0's decision shape, and BioRepo refuses `assumed` and any estimate; computing it from the decision's kind is a debt in `docs/PROGRESS.md` (ADR-006).

## Open questions

- C: The owner's questions 1 to 10 stand in `docs/PROGRESS.md` (execution prompt §13), each with the default this build took; none is answered yet.
- C: Q1 PostgreSQL as the one database — default yes. Q2 the kit in process with a local embedder — yes. Q3 delete thread Q's TypeScript list and keep `docs/corpus/ethanol-sources.txt` — yes.
- C: Q4 delete Dominion with its return condition recorded — yes. Q5 rename `demo` to `assumed` — yes. Q6 a Python pin — none needed: the kit's suite passed on 3.13.17.
- C: Q7 the kit's REST under `/rag` on the same port — yes, behind `OPENFERMENT_RAG_KEY`. Q8 a licence — none added (ADR-012). Q9 accounts — tables and a membership stub only.
- C: Q10 the per-request key override (§4.8) and keys for a route's other-provider model — neither built, since each changes how a key is read (§11.1; ADR-008, Implementation 6.3).

## Revisit conditions

- C: ADR-000: any rule may be re-classified when new evidence arrives, with its own decision record.
- C: ADR-001: the schema split, if the two migration trees fight. ADR-007: none; generation is how the drift stops.
- C: ADR-002: the kit drops async SQLAlchemy or changes its ingestion contract, a second literature engine is needed, or the upstream pull request lands.
- C: ADR-003: the toolkit ships an importer or packaging, or the schema reaches 1.0. ADR-004: a second engine, or NSKinetics once a kinetic model exists.
- C: ADR-005: accounts and multi-user access. ADR-009: a design pass after alpha 2.0. ADR-012: the owner adopts terms.
- C: ADR-006: a task needs a formal decision rule or uncertainty method, justified and evaluated for that task. ADR-008: the evaluation that lets the simple system compete.
- C: ADR-010: a deleted piece proves needed, restored from `alpha-1.0` with a decision record. ADR-011: a guard proves necessary again and returns with a negative test.
- C: ADR-013: biosteam, thermosteam or biorefineries changes version, or the package's test values change upstream. ADR-014: the owner asks for the queue to go, or accounts give pending writes a home on the service.

## Stop conditions (ask the owner first; execution prompt §11.1)

- R: Deleting a person's entry, decision or artifact from a live instance.
- R: Widening network exposure or weakening `core/openferment_core/guard.py`; the service keeps its loopback bind.
- R: Any licence choice for the project (ADR-012), or a dependency outside the permissive families in `core/licences.toml`.
- R: A change to how keys are stored or read, the per-request key override among them (owner question 10).
- R: Spend above the daily cap.
- C: A consequential departure from the execution prompt gets a decision record and a line in `docs/PROGRESS.md` before it lands.

## Where the history lives

- R: `docs/history/` holds the guidance written before this build, dated 2026-10-21 (`CLAUDE`, `STATE`, `README`, `COMPONENTS`, `THIRD_PARTY`, `BUILD-SPEC`, `OF-COR-001`, `DEMO`, `build/`); grep it for facts about the tree, since it carries no authority (ADR-000).
- R: Tag `alpha-1.0` marks `d19224f`, the tree before this build, and a deleted piece returns from it (ADR-010); the tag's push waits on the owner (`docs/PROGRESS.md`, Blockers).
- C: `docs/handoff/2026-10/` holds the owner's handoff documents (white paper, development plan, reference atlas), with extracted text in `txt/`.
- C: `docs/decisions/` holds ADR-000 to ADR-014; `docs/PROGRESS.md` holds the log of every stage, the departures, the debts and the blockers; `docs/reports/` holds measured reports.
