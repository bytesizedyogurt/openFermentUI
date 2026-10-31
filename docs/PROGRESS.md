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
4. **Next step: the owner's.** The alpha 2.0 foundation build is complete (stages 0 to 8), and its
   pull request, [#15](https://github.com/bytesizedyogurt/openFermentUI/pull/15), carries the
   completion report. What waits is the owner's: owner questions 1 to 10
   below, the tag push and the live Mini's first alpha 2.0 install (Blockers), then the review. A
   session that continues the work starts from the Known debts, each naming what pays it, and runs
   `pnpm verify` and `pnpm build && pnpm prove` first; `pnpm prove --live` needs the key in
   `core/.env` (`bash scripts/session-start.sh` writes it from `OPENFERMENT_API_KEY`).
5. Files in flight: none.

## Current stage

The alpha 2.0 foundation build is complete: stages 0 to 8. Stage 8 reconciled the guidance
(`CLAUDE.md`, 134 lines, every line labelled, held by `test_guidance.py`; `README.md`;
`COMPONENTS.md` written by `pnpm gen:components` from the package map; `docs/api/intake.md`),
settled verify's sixteen stages (ADR-011, Implementation 8) and finished the proof: step 3 takes the
kit's demo corpus in through Intake, searches it, anchors a stand-in's candidate to the stored text
and accepts it into BioRepo, and `pnpm prove --live` runs the proof with the key, the ethanol
sources and the routed models. The live run found two faults the offline suites could not see, both
fixed here: Intake refused the `SGD:<id>` form the sources file uses, and the API refused every
Postdoc request once the plan schema's typed values joined seven strict tools (ADR-008,
Implementation 8).

After the pull request, step 8.5 swept out what alpha 1.0 left behind (Log, stage 8): `corpus.py`
and every reader of a projection of the deleted seed, which a checkout that ran alpha 1.0 still
holds on disk; `single` mode, the corpus fields of health and ready, and `ask-batch`; program-era
dead code in the service and the client; and words on screen that described the simulated
prototype. Two faults it found are fixed with it: an accepted candidate reached Postdoc as
`unverified` (the pool now applies the decisions, and a decision's provenance is computed), and a
concurrency test had skipped on every run since stage 1. Its second half found three more, each
work stage 2 moved to the service that a reader still looked for in the browser or the seed:
Postdoc's Proforma tools refused every scenario a project made, the module reads listed none of
its runbooks, and the review queue hid, and never posted, a decision on a document with no PMCID,
DOI or PMID. Each now reads the project's rows.

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
| 2026-10-30 08:23 | `test:core` with 3.1; `test:lit`; `pnpm smoke` | 2007 passed, 2 skipped, 133 deselected; 5 passed; 11 of 11 rail entries open | 5 min 8 s | 3.1 |
| 2026-10-30 08:51 | `test:core` with 3.2; `test:lit`; `pnpm smoke` | 2003 passed, 2 skipped, 133 deselected; 5 passed; 11 of 11 | 5 min 5 s | 3.2 |
| 2026-10-30 09:16 | Stage 3 gate in a clean worktree: `test:core`; `test:lit` (the demo corpus gate); `test:sim` | 2008 passed, 2 skipped, 138 deselected; 10 passed; 102 passed, 2046 deselected | 5 min 37 s; 15 s; 4 min 37 s | 3.3 |
| 2026-10-30 09:16 | Stage 3 gate: secrets, typecheck, plan, licences, tools, guild, state, figures, build, `pnpm smoke`, reconcile; no full-text cache left | all passed; 11 of 11 rail entries open | | 3.3 |
| 2026-10-30 09:22 | `test_sff_sim.py` (`sim`: a reference run and a shelf run exported, validated and scored; two reference files fetched from the pin, imported and drawn) | 5 passed | 40 s | 4.1 |
| 2026-10-30 09:43 | `test:core` with 4.1 | 2038 passed, 2 skipped, 143 deselected | 5 min 23 s | 4.1 |
| 2026-10-30 09:48 | `test:sim` with 4.1 | 107 passed, 2076 deselected | 4 min 31 s | 4.1 |
| 2026-10-30 10:35 | `test:sim` with 4.2 (the library sim tests among them) | 119 passed, 2102 deselected | 4 min 46 s | 4.2 |
| 2026-10-30 10:40 | `test:core` with 4.2 | 2064 passed, 2 skipped, 155 deselected | 5 min 10 s | 4.2 |
| 2026-10-30 11:08 | `test:sim` with 4.3 (the composed flowsheet's sim tests among them) | 126 passed, 2112 deselected | 5 min 6 s | 4.3 |
| 2026-10-30 11:14 | `test:core` with 4.3 | 2074 passed, 2 skipped, 162 deselected | 5 min 19 s | 4.3 |
| 2026-10-30 11:31 | `test:core` with 4.4 (the rename); `typecheck`, `check:plan`, `check:figures`, `check:tools`, `check:state`, `check:guild`, `check:secrets` | 2076 passed, 2 skipped, 162 deselected; all passed | 5 min 16 s | 4.4 (rename) |
| 2026-10-30 11:48 | `test:core` with 4.4 (origins); `typecheck`, `check:plan`, `check:figures` | 2090 passed, 2 skipped, 162 deselected; all passed | 4 min 59 s | 4.4 (origins) |
| 2026-10-30 12:04 | `test:core` with 4.4 (runs); `test_runs_sim.py` (`sim`); `typecheck`, `check:plan` | 2100 passed, 2 skipped, 166 deselected; 4 passed; all passed | 5 min 29 s; 48 s | 4.4 (runs) |
| 2026-10-30 12:05 | Stage 4 gate in a clean worktree at `309e8ab`: `test:core`; `test:lit`; `test:sim` (the library plants with their regression, the composed flowsheet, A→B→A, SFF export, import and drawing, engine runs and replay within tolerance) | 2112 passed, 2 skipped, 166 deselected; 10 passed; 130 passed, 2150 deselected | 5 min 46 s; 14 s; 6 min 44 s | 4.4 (gate) |
| 2026-10-30 12:05 | Stage 4 gate, the same worktree: secrets, typecheck, plan, licences, tools, guild, state, figures, build, `pnpm smoke`, reconcile; the worktree left clean | all passed; 11 of 11 rail entries open | | 4.4 (gate) |
| 2026-10-30 12:22 | `test:core` with the CI fixes; `test_cellulosic.py`; `test_proforma_worker.py` (`sim`) | 2112 passed, 2 skipped, 166 deselected; 7 passed; 7 passed | 5 min 19 s | `49b8eac` |
| 2026-10-30 13:35 | `test:core` with 5.1 (scenarios, fresh builds, comparisons); the studies `sim` test | 2133 passed, 2 skipped, 167 deselected; 1 passed | | `99b6e62` |
| 2026-10-30 14:03 | `test:core` with 5.1 (runbooks); the studies `sim` test with a runbook locked | 2166 passed, 2 skipped, 167 deselected; 1 passed | 6 min 37 s; 49 s | `7347bde` |
| 2026-10-30 14:14 | `test:core` with 5.1 (exports); the studies and runs `sim` tests | 2172 passed, 2 skipped, 167 deselected; 5 passed | 5 min 54 s | `074ab2b` |
| 2026-10-30 15:03 | `test:core` with 5.2 (screens, stream prices); typecheck, plan, figures, secrets | 2173 passed, 2 skipped, 168 deselected; all passed | 5 min 30 s | `a965984` |
| 2026-10-30 15:25 | Stage 5 gate in a clean worktree at `f612377`: `test:core`; `test:lit`; `test:sim` (the flowsheet identical after sugarcane among them) | 2174 passed, 2 skipped, 168 deselected; 10 passed; 132 passed, 2212 deselected | 5 min 33 s; 10 s; 6 min 9 s | 5.2 (gate) |
| 2026-10-30 15:25 | Stage 5 gate, the same worktree: secrets, typecheck, plan, licences, tools, guild, state, figures, build, `pnpm smoke`, reconcile, `pnpm prove` (steps 1, 2, 4, 5, 7, 8); the worktree left clean | all passed; 12 of 12 screens open; 34 of 34 checks hold | 1 min 56 s (prove) | 5.2 (gate) |
| 2026-10-30 16:04 | `test:core` with 6.1 (conversations, events); typecheck, plan, secrets, state, guild, figures | 2193 passed, 2 skipped, 168 deselected; all passed. The run before it failed one test that read the ask stream's first event as a step (now `turn`) | 4 min 56 s | 6.1 |
| 2026-10-30 16:40 | `test:core` with 6.2 (typed values, the study tools, the generated reference); `check:tools`, `gen:tools --check`, typecheck, plan, secrets | 2216 passed, 2 skipped, 168 deselected; all passed. The run before it failed seventeen tests: a module write's fields of a value and a unit in words were read as a quantity, so quantities now stand only where a tool's schema asks for one | 5 min 33 s | 6.2 |
| 2026-10-30 16:52 | `test:core` with 6.3 (the routing table, the final turn kept back); secrets | 2231 passed, 2 skipped, 168 deselected; passed | 5 min 21 s | 6.3 |
| 2026-10-30 17:00 | `pnpm prove --steps 6` (steps 1, 2, 6), the real worker | 14 of 14 checks hold | 1 min 18 s | 6.4 |
| 2026-10-30 17:06 | `test:core` with 6.4 (the evaluation set) | 2234 passed, 2 skipped, 168 deselected | 5 min 27 s | 6.4 |
| 2026-10-30 17:24 | Stage 6 gate in a clean worktree at `9663dc3`: `test:core`; `test:lit`; `test:sim` | 2234 passed, 2 skipped, 168 deselected; 10 passed; 132 passed | 5 min 58 s; 12 s; 7 min 2 s | 6.4 (gate) |
| 2026-10-30 17:24 | Stage 6 gate, the same worktree: secrets, typecheck, plan, licences, tools, `gen:tools --check`, guild, state, figures, build, `pnpm smoke`, reconcile, `pnpm prove` (steps 1, 2, 4, 5, 6, 7, 8); the worktree left clean | all passed; 43 of 43 checks hold | 2 min 38 s (prove) | 6.4 (gate) |
| 2026-10-30 17:39 | `pnpm prove --steps 9` (steps 1, 2, 5, 6, 9), the walk in Chromium through the built app | 33 of 33 checks hold | 2 min 3 s | 7.2 |
| 2026-10-30 17:45 | `test:core` with stage 7; typecheck, plan, secrets, `gen:api --check`, `gen:tools --check`, `pnpm smoke` | 2236 passed, 2 skipped, 168 deselected; all passed; 12 of 12 screens | 5 min 28 s | 7.2 |
| 2026-10-30 18:12 | `pnpm prove --steps 3,8` (steps 1, 2, 3, 8), offline: the kit's demo corpus, a stand-in's candidate anchored, refused and accepted | 21 of 21 checks hold; the proof's spend table holds no call | 60 s | 8.4 |
| 2026-10-30 18:58 | `test:core` with stage 8 (the guidance test, the SGD form, the grammar fix, OSTI's rate limit) | 2250 passed, 2 skipped, 168 deselected | 5 min 17 s | 8.4 |
| 2026-10-30 18:39 | `pnpm prove --live` (steps 1 to 8): 22 of 22 ethanol sources, 814 chunks; PMC4842200 extracted by `claude-haiku-5-5` (8 candidates kept, 2 refused); the evaluation set answered live | 46 of 46 checks hold; 10 calls, $0.0163 from the proof's spend table | 7 min 21 s | 8.4 |
| 2026-10-30 19:13 | Stage 8 gate in a clean worktree at `7e513d9`, no key: `pnpm verify`, all sixteen stages; `test:core`; `test:sim`; `test:lit`; `smoke` | every stage green; 2250 passed, 2 skipped, 168 deselected; 132 passed; 10 passed; 12 of 12 screens open | 13 min 33 s (verify) | 8.4 (gate) |
| 2026-10-30 19:16 | Stage 8 gate, the same worktree: `pnpm prove`, steps 1 to 9 offline (1: 4 checks, 2: 1, 3: 9, 4: 7, 5: 10, 6: 9, 7: 3, 9: 9, 8: 10, the spend: 1); the worktree left clean | 63 of 63 checks hold; the proof's spend table holds no call | 2 min 47 s | 8.4 (gate) |
| 2026-10-31 01:39 | `test:core` with 8.5's second half (the project's scenarios and runbooks read, the review path, the words) | 2257 passed, 1 skipped, 168 deselected | 4 min 55 s | `5287542` |
| 2026-10-31 01:56 | 8.5 gate on `74381fb`, no key: `pnpm verify`, all sixteen stages (`test:core` 2257 passed, 1 skipped; `test:sim` 132 passed; `test:lit` 10 passed; `smoke` 12 of 12 screens); `pnpm prove`, steps 1 to 9 offline | every stage green; 63 of 63 checks hold, no call in the proof's spend table | 11 min 42 s (verify); 2 min 24 s (prove) | `74381fb` (8.5 gate) |
| 2026-10-31 01:58 | On the proof's kept service: a document pasted in (no DOI, no PMCID), a stand-in candidate on it, the default review queue in Chromium, Accept; both MCP servers over stdio on the proof's database | the candidate listed and accepted, the service keeping the decision `verified` under the reviewer's name, no console error; `openferment` 45 tools, `runbooks_read` lists the proof's locked study runbook, `selling_price` refuses an unknown id in words; `sci-rag` refuses with no project, serves the project's 7 documents in 36 chunks and refuses an unknown document in words | | `74381fb` (8.5 gate) |
| 2026-10-31 02:00 | `pnpm test:slow` (by hand, outside verify), on the 8.5 gate's head | 8 passed, 2418 deselected | 1 min 55 s | `74381fb` (8.5 gate) |
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
| [011](decisions/ADR-011-guards.md) | Guards and verify stages | accepted, stages 1 and 8 (Implementation 8: sixteen stages) |
| [012](decisions/ADR-012-licence-undecided.md) | Licence undecided | open (owner) |
| [013](decisions/ADR-013-cornstover-package-test.md) | The corn stover plant's two values its package's own test fails, held to the package's measurement | accepted, stage 5 |
| [014](decisions/ADR-014-durable-write-queue.md) | The Durable snapshot keeps the writes the service has not acknowledged | accepted, stage 7 (a departure) |

## Departures from the execution prompt

| Where | Departure | Why |
|---|---|---|
| A4, stage 8 | `test_no_seed.py` holds what A4 names (each deleted module absent, no `.ts` under `src/data/` exporting content, the shipped stores empty), and an `rg` over `core/tests/` still finds test values: `standins.py` (stand-in records on real strain ids, a closed-form ethanol evaluator with the theoretical yield on glucose; 27 test files use it) and `test_proforma_slow.py` (the benchmark price this build once measured). `src/` and the service's code hold none | The stand-ins carry rule tests (binding, overrides, ceilings, run contracts) that stage 4's library fixtures were to replace; that work did not fit stages 4 to 8 (a debt below) |
| §5.5, A3, stage 7.1 | The Durable snapshot keeps the writes the service has not acknowledged (review decisions, Guild entries, project rows), beside the preferences; a record the service holds is never kept there (ADR-014) | Without the queue, a reviewer's decision made while the service is away is lost on the next reload |
| §4.8, §11.1, stage 6.3 | The per-request key override and a route's non-Anthropic model are not built; each would change how a key is read, which the owner decides (owner question 10; ADR-008, Implementation 6.3) | §11.1 asks the owner before a change to how keys are stored or read |
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
| §8.3, stage 4.1 | `sff_export` is an op of its own that rebuilds a run's base case from the run's basis, where "every engine run writes an SFF file" could fold it into the run | A replay changes nothing stored and must reproduce the run's output hash; a file written inside the run would do neither (ADR-003, Implementation) |
| §8.3, stage 4.1 | A file that fails validation under schema 0.2.4 is kept as a record with its findings; only a file with no readable graph is refused | Seventeen of the toolkit's eighteen reference files declare SFF 0.0.3 and fail the 0.2.4 schema gate |
| §7.2, stage 4.1 | The Proforma worker's manager moved from `proforma.py` to `engine/simulator.py` (re-exported by `proforma`); engine functions take the project id from their caller | The engine reaches the worker without importing `proforma`, and imports what §7.2 lists, `projects` not among them |
| §8.3, stage 4.2 | For openFerment's exports, the SFF toolkit's JSON writer also writes a thermosteam reaction in its own words and a stream by its id (vendored files unchanged) | Its design-spec registry names design inputs that hold such objects and its writer refused them, so four of the nine buildable library plants could not be exported (ADR-003, Implementation 4.2) |
| §4.4, stage 4.2 | `ethanol` and `biodiesel`, which the prompt lists among the plants, are on the shelf as packages of subsystem factories: the installed package gives them no plant entry point. LAOs, fattyalcohols, lactic and gas_fermentation are on the shelf and refused at build with the package's own error | Measured under biosteam 2.54.0 and biorefineries 2.35.1 (ADR-004, Implementation 4.2) |
| §9 step 4, stage 4.2 | The corn stover plant (the NREL cellulosic ethanol design) holds nine of its package test's eleven values on the pinned versions, not all; the run's checks say which. `scripts/prove.py` step 4 holds each of the two to what the package's own code measures on this installation, to the run's ten digits, and fails on any other value outside (ADR-013) | Measured, as its reference run has since 2026-10-20: installed equipment cost −7.9 %, electricity consumption −5.2 % (`docs/reports/library-regression.md`). The package's own `test_cornstover` fails the same way under biosteam 2.54.0 (run 2026-10-30) |
| §8.4, stage 4.2 | `engine/library.py` imports the shelf's package-test reader (`flowsheets/shelf.py`) and, where a run is kept, `artifacts` | Both belong to the engine by §7.2's table and still live outside `engine/`; the boundary test at the stage 4 gate decides their place |
| §8.3, stage 4.3 | The recipe's authored file is `extended_metadata.yaml`, where the prompt wrote `metadata.yaml` | The SFF toolkit's runner reads that name (`load_extended_metadata`) |
| §8.4, stage 4.3 | The composed flowsheet runs through the library adapter (kind `flowsheet` on the library shelf, `library.run` artifacts), and runs the package's own composition body (`SystemFactory.f`) with its pretreatment and fermentation factories chosen | One adapter for every plant (§2 item 3); the package's own system factory checks that dilute acid's inlets are used and cannot take another pretreatment, and its body keeps every number the package's (ADR-004, Implementation 4.3) |
| §8.4, stage 4.3 | The organism is declared in the recipe (`extended_metadata.yaml`: Zymomonas mobilis) and is not a configuration | A BioSTEAM system names no host, as the toolkit's own recipes say; the package holds one organism's reaction sets, so a choice would have one entry |
| §8.4, stage 4.3 | AFEX and alkaline pretreatment are on the shelf and refused: AFEX with BioSTEAM's `InfeasibleRegion` in its ammonia mixer, alkaline with a chemical alias the cellulosic chemicals lack | Measured: the package's factories, composed on its corn stover feed and chemicals |
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
| §5.4, stage 8.5 | The evidence pool keeps BM25 as its ranker: it loads the project's candidates and decisions from PostgreSQL and ranks them in memory for one question, with the coverage rule, the filters and the cap of ten | A project's records are few, and the ranking rules are tested on their own (`test_evidence_pool.py`); a ranking in SQL would change what Postdoc cites without a measurement to say it is better |
| §6.2, stage 8.5 | `src/engine/units.ts` stays the browser's unit engine, mirroring `units.py` on the same tables (`schema/units.json`), held equal by the fixture `pnpm export:unit-fixtures` writes and `test_units.py` asserts | Every screen formats and converts with it; serving each conversion from the service is a change to every caller, after alpha 2.0 |
| §4, §5.2 | The record fields, the vocabulary (carbon sources and unit operations) and the unit tables live in `core/openferment_core/schema/` (`fields.yaml`, `vocabulary.yaml`, `units.json`), with no range and no example value; `src/data/ontology.ts` and `vocabulary.ts` mirror them, held equal by `test_schema.py` through the fixture `pnpm export:unit-fixtures` writes. BioRepo's typed-value refusal is renamed `range` → `unit`; `pyyaml` is a direct dependency | The service needs the fields without the TypeScript seed; a range is a number about a field (ADR-010) |

## Blockers

| Since | Blocker | Next command |
|---|---|---|
| 2026-10-30 | Owner action, before the first alpha 2.0 deploy on the live Mini: its records are files under `core/data/` until carried into a project. Nothing is lost by waiting: the service no longer writes them | On the Mini: `brew install postgresql@17 pgvector && brew services start postgresql@17`; `scripts/host/install.sh` (makes the database `openferment` and names it in `core/.env`; when `core/data/biorepo.json` holds uncommitted decisions, the old deploy asks to commit and push them first, which keeps them); then `pnpm db:import-alpha1 --name "Alpha 1.0 records" --by "<your name>"`, and `OPENFERMENT_PROJECT=<the id it prints>` in `core/.env` for the nightly extraction |
| 2026-10-31 | Owner decision: the live instance's PostgreSQL has no backup. `pnpm ready` used to say a git push "backs up" Guild's decisions, which stopped being true when they moved into the database at stage 2; the row is gone (8.5). Guild's ledger is personnel data and never enters git | Choose where a dump of the database goes, then add it to the nightly (`scripts/host/nightly.sh`): `pg_dump openferment` to that place |
| 2026-10-30 | The session's git relay refuses tag pushes (branch pushes work): `git push origin alpha-1.0` ends with "unexpected disconnect while reading sideband packet", lightweight and annotated alike. The tag exists in this container only. Commit `d19224f` stays reachable as an ancestor of `main` | On the owner's machine: `git fetch origin && git tag alpha-1.0 d19224ff0b6eb809b21492d1b7a2e8fd895a0f44 && git push origin alpha-1.0` |

## Known debts (each names the stage that pays it)

| Debt | Paid at |
|---|---|
| `core/tests/standins.py` (27 test files use it) keeps stand-in records on real strain ids, a closed-form ethanol evaluator and `STANDIN_THEORETICAL`, the theoretical yield on glucose; `test_proforma_slow.py`, `test_proforma.py` and `flowsheets/cornstover_benchmark.py` keep the benchmark price this build once measured (1.968 USD per gallon) and the package's regression values to test the parser. A4's `rg` clause finds them (a departure above) | stage 4 (fixtures read from the library plants); still open: after alpha 2.0 |
| Postdoc's scripted stand-in model and the test pool still speak of PHB, casein and xylose hydrolysate (`test_tools.py`, `test_postdoc_agent.py` and the tests that import their fixtures); §5.3 wants them to speak only of library plants and the kit's demo corpus. The words are test material, and no value of them reaches the service | after alpha 2.0, with the stand-ins above |
| pureOS's chemical-set key is still called `program` (`TrainSpec.program`, and `FlowsheetInfo`, `Train`, `TrainSummary`, `TrainProposal`); kept trains and train runs validate on that name, and its texts ("the yeast program's chemicals", `PROGRAM_CHEMICALS`, `fermos.NAMED_NOTE`'s "program filter", the kinetics settings' notes) are hashed into artifact ids, so renaming them shifts the id of every new computation. The refusals and descriptions of pureOS, the vessel and the shelf still say "the yeast program" beside the key, and fermOS's note on every fit's deposition input ("the readings as the browser sent them; the service cannot see the deposition itself"), hashed the same way, is untrue since stage 2. The screens no longer say "program" | one stage that renames the key with a before-validator for stored rows and accepts the id shift |
| `kinetics.py` keeps the storage machinery of the deleted `storage_v1` family (the N and Q states, `Mode.storing`, the N event, the Storage group); no family sets `has_N` or `has_Q`, so none of it runs. §11.5 keeps the kinetics families untouched, and dropping the state slots changes LSODA's finite-difference Jacobian, which a replay compares exactly | the next change to the kinetics families, with every family's trajectories held bit for bit |
| `proforma._strain_labels`' per-program species map serves the vessel's organism check; with no catalogue it is empty in production, and its two notes are hashed into vessel designs | with the `program` key above |
| A retrieval report over a project's own corpus with the lanes that call a model (the graph, HyDE, a judge grading the answers): alpha 1.0's paid lanes (Live owed, §4.5) | after alpha 2.0, with the key: `pnpm lit:report` extended to a project and a judge route |
| The kit's `search_entities` and `get_entity_relationships` read the concept graph whole (every project's entities, relationships and evidence quotes), so the kit's MCP server leaves them off; nothing in openFerment builds the graph yet | before a graph is built: scope both to the project's chunks, or serve them from openFerment's registry |
| Catalogues that left with the seed are empty in production and supplied by fixtures in tests: the strain catalogue and its aliases, the proposer's products and hosts, Guild's skills, protocol steps and lessons, Primer's lessons. Until a store holds them, every pureOS proposal is refused for want of a host on file and Guild refuses an entry that names a skill | after alpha 2.0, each catalogue's store with its project |
| `stream_table` on a scenario's kept run lost its test with the seed scenarios; `run_flowsheet` and `selling_price` on a scenario the project keeps have theirs again (8.5) | a test that reads the stream table of the run `test_tools` now makes |
| The module reads leave a project's depositions and measured evidence out (`module_stores.PARTIAL` says so in every read's footer); the Runbooks page shows them | a `deposition` kind in the runbooks read |
| Proforma's screens keep alpha 1.0's split between a held scenario and one made here (`createdScenarioIds`, the index's `needsBinding`, the `/api/proforma/scenarios` path); every scenario is the project's now, so the held path is never taken | the screens read every scenario as the project's |
| `src/engine/geneos/enumeration` (Dominion era) still serves RunbookDetail's research funnel, whose words still speak of a clearance reading and a molecule | after alpha 2.0 (stage 7 left the module screens as they were, now views inside a project) |
| `src/data/types.ts` is still hand-kept beside the generated `src/api/types.gen.ts`, held to the service by `check:plan`'s pairs; the screens read the hand-kept types | the screens move to the generated types one by one, after alpha 2.0 |
| Component tests on fixtures recorded from the real service (`pnpm record:fixtures`, §9.3) are not built; the walk and the smoke run against the real service | after alpha 2.0 |
| No offline test computes on a published genome-scale model (Yeast9 and iMM904 need their fetched files); a model add-on applied in the worker, and a metabolite-defined product's demand through the worker, are untested | still open: after alpha 2.0 |
| `units.json` maps `wt%` and `% (w/w)` to `% CDW`, aliases written for the PHA program; changing them changes how a stored record converts | the vocabulary review, after alpha 2.0 |
| `openferment.records` (migration 0001, §7.4) is written by no code: a project's records are its candidates and the decisions on them (`biorepo.py`) | the owner's call: write it from `biorepo.write`, or drop it in a migration |
| `test_biorepo.py::test_the_committed_file_is_the_model_and_starts_empty` holds the shape of a tracked file nothing reads | when `core/data/biorepo.json` leaves git (owner action, Blockers) |
| The host scripts' PostgreSQL steps (`ensure_database`, the migration in `deploy.sh`, the nightly's settings) have run only as `bash -n` here: this container is not a Mac | the owner's first install on the Mini |
| `pnpm db:up` (compose.yaml, `pgvector/pgvector:pg17`) has never run here: this container has no Docker daemon; CI runs the same image as a service | the owner's machine |
| fermOS, pureOS and Proforma take a run's values as `Override`s (a person's assumption or a model's estimate) and name each input's source in the basis, which `basis.origin_of` reads as an `Origin`; their requests are not yet lists of `Quantity` objects, and their runs are artifacts with no row in `runs` (engine runs alone are) | still open: after alpha 2.0 |
| The shelf's hand-written reference entries (`cornstover_benchmark`, `corn_drygrind`) serve the reference run and its screen beside the library plants `cornstover` and `corn`, which discovery found | when the UI reads the library shelf alone, after alpha 2.0 |
| A ProcessModel plant runs on its default scenario; its scenario fields (cellulosic's feedstock, milk's feed, gas_fermentation's carbon source) are read and not offered | after alpha 2.0 (4.3 composes the cellulosic plant's pretreatment and fermentation instead) |
| A second organism's reaction set for the composed flowsheet: the package holds one | when a package or a record gives another |
| Small handler mismatches the worker op reference found (4.4): `train_spec.py` sends `train_run` a `product` its handler reads nowhere; `grid` and `montecarlo` leave out the `structure` that `evaluate` and `run` pass on (both ops are called by tests alone); an unknown flowsheet's refusal arrives quoted (`Refused: 'there is no flowsheet …'`); an unknown catalogue type raises `CatalogueUnknown`, which callers avoid by checking the type first | the next change to those ops |
| Paid: a review decision's provenance was the label the browser sent; `biorepo.provenance_of` computes it from the decision (ADR-006) | 8.5 |
| Paid: the evidence pool put an accepted candidate in front of Postdoc as `unverified`, and Home listed it as awaiting review; the pool applies the standing decisions | 8.5 |
| Paid: dead service paths the deletions left (Proforma's yield cap, the store branches in fermOS and Proforma, `_example`, the check:seed entry points, `ProjectionMissing`); kinetics' and the hashed texts stay (rows above) | 8.5 |
| Paid: `src/data/nav.ts` called the rail "THE TWELVE" and exported `ELEVEN`; it exports `DESTINATIONS` | 8.5 |
| Paid: the held scenarios were the seed's, so Postdoc's `selling_price` and `run_flowsheet`, the params scope and pureOS's naming saw none of a project's scenarios; they read the project's rows | 8.5 |
| Paid: the client's review path kept alpha 1.0's curated-record machinery (the extractor's best candidate beside a curated record, the span carried on promotion) and its committed file's rule that a decision needs a PMCID, DOI or PMID | 8.5 |
| Paid: `pnpm smoke` opened the rail entries and checked nothing more; the walk (`scripts/walk.ts`, proof step 9) goes through a project on the real service | stage 7 |
| Paid: both MCP servers connect at a session's start and answer over stdio (stage 8 log) | after the pull request |

## Live owed (folded from `docs/history/STATE-2026-10-21.md` at stage 8)

The two LIVE steps alpha 1.0 still owed, each judged against this build:

| Owed at alpha 1.0 | Now |
|---|---|
| §4.5, the paid lanes of the retrieval evaluation (`pnpm rag:eval && pnpm data:push`), waiting on a helper model the safety classifier lets through | Retired with their code: the bespoke retrieval stack and the data branch are deleted (§5.4, §5.5; ADR-010). Its successor is the kit's retrieval report, `pnpm lit:report`, which asks no model. A report with the lanes that call one (the graph, HyDE, a judge grading the answers), over a project's own corpus, is a debt below |
| §10.3, the saved answer (`pnpm demo:fixtures --real && pnpm data:push`): a real Postdoc answer, its artifacts and the retrieval report saved | Retired with the demo infrastructure (§5.3; ADR-010). A real answer is now a turn of a conversation the service keeps, with its tool calls and the artifacts they made (stage 6); `pnpm prove --live` step 6 keeps two, asked of the routed models |

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
| 10 | §11.1, asked at stage 6.3: the per-request key override (§4.8), and keys for a route's non-Anthropic model (read through Sci RAG Kit's settings). Each changes how a key is read | neither built: a route's other-provider model is passed over in words, every key is core/.env's; the design the override would take is in ADR-008, Implementation 6.3 | no |

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
- CI went green again on `1393b1c` (the stage 4 gate's last commit), the whole verify passing on
  the runner.
- Stage 8: `bash scripts/session-start.sh` wrote `core/.env` from `OPENFERMENT_API_KEY` (mode 600,
  ignored by git; the value never printed). The session's environment sets every route to
  `claude-haiku-5-5` at effort medium (`OPENFERMENT_MODEL`, its fallback and the index model).
  Europe PMC, OSTI, SGD and the Anthropic API answer from this container; OSTI rate-limits a
  burst of report fetches with a redirect to its 429 page.
- A container restart stops the local PostgreSQL: `service postgresql start`, then `pg_isready -h
  127.0.0.1`. `core/.env`, the virtual environment and `node_modules` survive it.
- CI (`.github/workflows/verify.yml`, read through the GitHub tools, 2026-10-30): verify runs on
  the runner's Python 3.12 with a `pgvector/pgvector:pg17` service. Green on 3.1 and 4.1; red on
  3.2 and 3.3 (fixed by 4.1), on 4.2 (`test_proforma_worker.py`'s toy fixture compared floats
  exactly, and the runner's sum ends `56.0` where this container's ends `56.00000000000001`) and
  on 4.3 (the recipe's `environment.yaml` pinned the Python that wrote it, 3.13 here and 3.12
  there). Both fixed in 4.4: the fixture is compared to twelve significant digits, and the recipe
  pins the lowest Python `core/uv.lock` resolves for.

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
- 3.3 Search and answers over the kit. `kit.search` (the project's passages with passage ids,
  vector and keyword, no model) behind `GET /api/literature/search`, BioRepo → Search and the
  `search_passages` tool's seam; `kit.answer` (the kit's cited answer as events, internal fields
  left out, each source with its passage id) behind `POST /api/literature/answer`. The Search
  screen searches and asks for a cited answer; a hit opens the reader at its passage. An upload
  keeps the title it gives itself. `pnpm lit:report` (`literature/report.py`) runs the kit's
  retrieval evaluation over its demo corpus and its seed questions (vendored,
  `core/tests/fixtures/kit-demo/eval_seed_questions.jsonl`) in a database of its own and writes
  `docs/reports/literature-retrieval.md` and `.json`: `interactive` and `vector_only` place the
  evidence passage first for all nine answerable questions (hit@5 1.00, MRR 1.00, nDCG@10 0.94),
  `keyword_only` for three. The gate: `test_literature_demo.py` (`lit`), the demo corpus held by
  one project and two of it by another: embedded once and linked by each, a search finds each
  seed question's evidence passage with its citation (at least 80 % in the top five; all nine
  here), an answer cites the document its evidence stands in, an extraction anchors in a demo
  passage and a gold decision on it is accepted and scored by Witness, and each project sees
  its own documents alone.

### Stage 4 — 2026-10-30

- 4.1 The SFF toolkit (ADR-003, Implementation). Vendored at `core/vendor/pisces_sff/` (`e236e32`,
  MIT, schema 0.2.4) without its exported flowsheets and model recipes, recorded in
  `core/licences.toml` (`[vendored.pisces_sff]`, which `check:licences` now verifies and lists);
  `jsonschema` and `pyyaml` in the `sim` extra. `workers/sff_toolkit.py` imports it in the
  Proforma worker alone and turns the toolkit's answers into JSON; the worker answers
  `sff_export` (a reference plant built afresh in `package_defaults()`, or a warm shelf plant set
  to the run's base values with its solved price on the product), `sff_validate` and
  `sff_score`. `engine/` begins: `simulator.py` (the worker's manager, moved from `proforma.py`)
  and `sff.py`: the `SFFFlowsheet` record in `flowsheets` (migration 0002: `origin`, `sha256`, the
  file as `document`), `import_sff` (read, checked in the worker, drawn, kept; invalid files kept
  with their findings), `export` (a run's base case, with `metadata.openferment`), the graph
  (nodes ranked left to right, edges, feeds, products, dangling streams, either unit style), and
  the reference corpus: `sff_library.json` names the eighteen files and the registry with their
  hashes, `fetch` brings one from the pinned commit and refuses a hash mismatch,
  `library_flowsheets()` loads them as `library` records, `import_library` keeps one. Routes
  under `/api/flowsheets`. Docs: `docs/api/sff.md`, `docs/api/workers.md`. Tests: `test_sff.py`
  (offline, the worker and GitHub stood in) and `test_sff_sim.py` (`sim`: the corn stover
  reference run and an ethanol shelf run exported, valid, scored, and the same base case as
  their runs read; `SF_BST_01` fetched, imported, valid and drawn with 71 units; `SF_BST_15` kept
  invalid with its findings and drawn).
- 4.2 The library plant runner (ADR-004, Implementation). `workers/library_plants.py` in the
  Proforma worker: discovery by reading each subpackage's namespace (never by attribute access;
  the package test found through the distribution's metadata, never imported, since importing it
  broke a later build), a fresh build through the entry point inside `package_defaults()`, the
  plant's parts found by the package test's names, the plant's own scenario or inspection, every
  parameter read back with its accessor (streams, TEA, utilities, each unit's design inputs by the
  SFF toolkit's registry), a run with a person's values, priced (the product's price solved at the
  TEA's IRR), its tables (without the TEA breakdown, said, where BioSTEAM cannot give one). Worker
  ops `library_discover`, `library_parameters`, `library_run`; `sff_export` takes a library run.
  `engine/library.py`: the shelf `library_shelf.json` (`pnpm library:discover`: fifteen
  subpackages, twelve plants, 29 of 33 builds), parameters as `ParameterSpec`s with
  `library-default` origins, `library.run` artifacts with the package test's values beside a run
  with no value of its own, `pnpm library:report` (`docs/reports/library-regression.md`). Routes
  under `/api/library`. The SFF writer adaptation lets every buildable plant export a valid file.
  Tests: `test_library.py` (offline, the worker stood in) and `test_library_sim.py` (`sim`: the
  committed shelf is what the package exposes; corn, sugarcane, lipidcane, cornstover and oilcane
  O2 held to their tests as they hold here; an agile configuration; a person's value; A→B→A by
  replay; a library run's SFF file; a refusal in the package's words).
- 4.3 The composed cellulosic ethanol flowsheet (ADR-004, Implementation 4.3).
  `flowsheets/recipes/cellulosic_ethanol_v0/` (the SFF toolkit's model directory: `load.py`
  importing nothing of openFerment, `extended_metadata.yaml`, `environment.yaml` written from
  `core/uv.lock` by `python -m openferment_core.flowsheets.recipes environment`). The recipe runs
  the package's own composition body with the pretreatment and fermentation kind chosen, the
  registry's renaming on, and reads the TEA's outside-the-battery-limits units and the wastewater
  recycle's tolerance from the package's `Biorefinery` code by `ast`: dilute acid with IB is the
  package's plant to ten digits (0.6588136420 USD/kg, 1.968 USD/gal). `flowsheets/cellulosic_ethanol_v0.py`
  runs through the library adapter (kind `flowsheet`, eight configurations; AFEX infeasible and
  alkaline refused, as measured): its feed moisture and dry composition, solids loadings, every
  conversion of the package's process units, every residence time, and the library parameters;
  its gates (share sums, conversion sums, infeasibility receipts) and read-back (each process
  unit's mode, temperature, residence times, vessels, reaction sets; the organism; the TEA; the
  utilities; the versions). `library_cases` runs cases on one warm build; A→B→A returns A exactly.
  A run's SFF file embeds the recipe with valid digests. Integer parameters stay integers;
  computed attributes are read back, never set; refusals carry no terminal colour codes. Tests:
  `test_cellulosic.py` (offline: the recipe's shape and declarations, its imports, its environment
  against the lock, its authored metadata against the exporter, no number typed in the flowsheet
  or the recipe) and `test_cellulosic_sim.py` (`sim`: the package's plant reproduced, each
  configuration, SCF's two batch reactors, the gates, a person's composition, A→B→A, the export).
- 4.4 (the rename) `demo` is `assumed` (ADR-006, Implementation 4.4; owner question 5): the
  service's vocabulary and ranking, `basis_provenance`, the browser's union, rank, tick, legend,
  figure encoding, CSV disclosure and screens; the label reads *Assumed · not measured*.
  Migration 0003 rewrites stored rows (text `provenance` columns and every `provenance` key in the
  schema's JSON columns, an artifact's output hash recomputed when its output changed; ids and
  lock hashes untouched) and renames back on downgrade; `import_alpha1` reads alpha 1.0's word
  under the new name. Tests: `test_db.py` (0002 → 0003 → 0002 over a record, an artifact and
  its output), `test_import_alpha1.py` (an alpha 1.0 artifact that says `demo`).
- 4.4 (origins) Typed quantities with origins (ADR-006, Implementation 4.4): `Origin` and the
  fuller `Quantity` (a bare one written as before), a `model-estimate` basis source and override
  origin that make a result `assumed`, every reader of a run's basis reading an estimate where it
  reads a person's value, `assumed` kept out of every aggregate, and BioRepo, the candidates
  store and a project's depositions and measurements refusing an estimate before writing.
  Tests: `test_estimates.py` (A6: an estimate planted at each record store and refused; one
  reaching a library run, a parameter panel and a scenario's overrides).
- 4.4 (runs) Engine runs on the `runs` table (ADR-004 and ADR-003, Implementation 4.4;
  `docs/api/runs.md`): each run's inputs as quantities with origins, its artifact, outputs,
  versions and the SFF file it wrote; a plant's refusal kept as a receipt; `POST
  /api/library/{plant}/run` answers the run's report, `GET /api/runs[/{id}]` reads them. Replay
  within the precision a library run's basis states. The worker's tables order facilities BioSTEAM
  ranks alike by ID, so a composed plant's tables read the same build after build. Tests:
  `test_runs.py` (offline: kept, answered from its row, a receipt, nothing kept for a bad request,
  a file that cannot be written, a model's estimate, replay tolerance, the routes) and
  `test_runs_sim.py` (`sim`: the flowsheet on library defaults with a valid SFF file, a scenario
  with a person's assumption and a model's estimate `assumed`, a replay within tolerance, AFEX's
  receipt).
- 4.4 (gate) `test_boundaries.py` holds the package rules of §7.2, read from the code by `ast`:
  each package imports what its row allows of openFerment's modules and none of the libraries it
  forbids; six exceptions are written down with their reasons (literature → projects and
  migrations; engine → artifacts, basis, the shelf's package-test reader and projects), and an
  exception no longer used fails the test. studies/ and postdoc/ are held to their rows from the
  commit that makes them. `docs/api/workers.md` gives every op's request and result (the Proforma
  worker's flowsheet, thermo, vessel and catalogue, and train ops, the geneos ops, beside the SFF
  and library ops), each read from its handler and its callers.
- 4.4 (CI) CI's verify had failed on 4.2 (the toy fixture compared floats to the last bit) and on
  4.3 (the recipe pinned the Python that wrote it); both fixed (`49b8eac`; Environment facts).
- Stage 4 gate, in a clean worktree at `309e8ab`: `test:core` 2112 passed, 2 skipped; `test:lit` 10
  passed; `test:sim` 130 passed: the library plants with their package tests, the composed
  flowsheet and its gates, A→B→A, an SFF export that validates and scores, a reference file
  imported and drawn, engine runs with their SFF files, and a replay within tolerance. Secrets,
  typecheck, plan, licences, tools, guild, state, figures, build, `pnpm smoke` (11 of 11 rail
  entries) and reconcile passed, and the worktree stayed clean.

### Stage 5 — 2026-10-30

- 5.1 (scenarios) `studies/` begins (`docs/api/studies.md`): a scenario names a plant on the
  library shelf, its configuration and the values it sets, each a quantity in the parameter's
  unit whose origin is a person's assumption or a model's estimate; checked against the plant's
  parameters when made, kept in `scenarios` with kind `engine` (migration 0004; the Proforma
  screens' rows are kind `proforma`), run as an engine run that names it. A plant's refusal is
  kept with the scenario as a receipt. `test_studies.py`.
- 5.1 (fresh builds) A library plant's `load()` returned a cached plant after the first build
  (ADR-004, Implementation 5.1): cornstover's second build costed at BioSTEAM's defaults. Every
  `ProcessModel` cache is now emptied while a `load()` builds; a mixer's inlets are listed by ID;
  an NPV at a solved price is kept to the precision of the plant's capital. The regression report
  is unchanged.
- 5.1 (comparisons) A comparison sets two to twelve engine runs side by side as one
  `study.comparison` artifact over the runs' artifacts (provenance the weakest of theirs,
  replayable): the price block and a flowsheet's outputs in their units with each run's change
  from the first, and each value a run set with its origin beside the library's default. A run's
  price block and a flowsheet's outputs now carry their units (`library run 2`).
  `test_comparisons.py`, `test_studies_sim.py` (`sim`: the flowsheet against a scenario with a
  person's assumption and a model's estimate, compared and `assumed`).
- 5.1 (runbooks) A study makes a runbook from an engine run: each output asked a point
  prediction in the run's unit, its basis the run and its artifact the run's, measured at
  harvest; kept as a row of the project's `runbooks` in the page's shape (`Runbook` now in
  `models.py`, paired by `check:plan`). The service locks a runbook, a study's or a person's,
  under the digest the browser writes: `runbook_lock.py` ports `src/engine/lock.ts` and is held to
  ten digests the browser's own code writes (`pnpm export:lock-fixtures`, run by `test:core`).
  Once a lock is kept the store refuses a runbook row whose predictions or measures differ, from
  either side. `test_runbook_lock.py`, `test_runbooks.py`; the `sim` study locks a runbook on the
  scenario's selling price.
- 5.1 (exports) The export package: one zip of `study.json` (runs with their inputs' origins,
  scenarios, comparisons, runbooks and the artifacts behind them), `study.md`, each run's SFF file
  byte for byte, `versions.json` and a manifest of sha256s, which the standard library opens
  alone (`python -I -S`). `GET /api/studies/export` and `python -m
  openferment_core.studies.exports`. The tests written in this build name the estimating model
  through `llm.DEFAULT_PRIMARY`. `test_exports.py`; the `sim` study exports its two runs.
- 5.2 (screens) `#/proforma/studies` (the runs, compared from there; the scenarios, run again
  from there; the comparisons; the study runbooks; the export package), `#/proforma/runs/{id}` (the
  run's parameters in the parameter panel, read-only, the values it set first; its basis with each
  origin; the package's own test; `RunReport`'s sections over its artifact as one case; its SFF
  file; a runbook made from its numbers) and `#/proforma/comparisons/{id}` (each output's change
  from the first run as a `Tornado` in `FigureFrame`; every number; every value the runs set). A
  study's runbook links each prediction to its run, and the page's own lock writes the digest the
  service recomputes (checked in the browser on a scenario run's runbook). A run's report carries
  its parameters as the panel reads them (`parameters_of`, `ParamScope` kind `library`). The run,
  SFF and study types are in `types.ts`, paired by `check:plan`; the smoke opens the studies screen.
- 5.2 (stream prices) The proof's A→B→A found sugarcane's process water price (0.000254 USD/kg)
  paid by the composed flowsheet built after it: `bst.process_tools.default()` leaves stream
  prices as the last plant set them. Every build now starts from BioSTEAM's own (ADR-004,
  Implementation 5.2); `test_library_sim.py` holds the flowsheet identical after sugarcane.
- 5.2 (the gate) `scripts/prove.py` (`pnpm prove`) proves steps 1, 2, 4, 5, 7 and 8 against a real
  service on loopback, a database and data directory of its own, no model key: 34 checks.
  `pnpm ready --offline` asks for no key and no network, as an offline run needs. Step 4 holds
  cornstover's two values outside its package test's tolerance to what the package's own code
  measures here (ADR-013, a departure). Steps 3 and 6 arrive with stages 6 and 8.
- 5.2 (gate run) In a clean worktree at `f612377`: `test:core` 2174 passed, 2 skipped; `test:lit`
  10 passed; `test:sim` 132 passed; secrets, typecheck, plan, licences, tools, guild, state,
  figures, build, `pnpm smoke` (12 of 12 screens) and reconcile passed; `pnpm prove` held 34 of 34
  checks; the worktree stayed clean.

### Stage 6 — 2026-10-30

- 6.1 (conversations) Postdoc keeps each question as a turn of its conversation under the
  project: `conversations`, `turns` in order and `tool_calls` under each turn, each call with
  what it answered the model and what it offered to cite, each turn with the artifacts its calls
  produced (`postdoc/conversations.py`; migration 0005 split the conversations the page kept
  whole). An ask names its conversation, its turn and who asked; a follow-up's history is read
  from the store, and a turn is asked once. The page's writes land on the same store and the
  service's turns stand; a turn the page writes `running` is taken over by its ask; a turn nobody
  is answering reads `interrupted`, and the screen follows one the service is still answering
  after a reload. `postdoc.py` is now `postdoc/single.py`. Reloaded conversations list newest
  first again (the load had read them oldest first since stage 2). ADR-008, Implementation 6.1.
- 6.1 (events) `GET /api/events`: engine runs say `job.queued/running/done/failed`, a kept
  artifact `artifact.kept`, a question `turn.started`, each `tool.call` and `tool.result`, each
  step `turn.delta` and its `turn.plan` or `turn.decline`. A page resumes with `Last-Event-ID`;
  one that falls behind is closed and reconnects; the stream holds no thread
  (`docs/api/postdoc.md`). `test_conversations.py`, `test_events.py`.
- 6.2 (typed values) A claim states numbers only in its `values`, each read from a computed value
  or a record by its id, or the model's own estimate with its unit, its range and what it rests
  on, marked as the model's; a claim stating one is `assumed`, and the answer screen shows each
  value with where it came from. A tool's input carries a number only inside a quantity, whose
  origin the registry writes from who called; a quantity nobody can be named for is refused. The
  prompt's rules say so; rule 11 no longer names the Dominion read. ADR-006, Implementation 6.2.
  `test_postdoc_agent.py` (a study proposed, run and explained by artifact id; each way a value
  drops its claim), `test_tools_study.py`.
- 6.2 (tools) Nine tools: `engine_plants`, `engine_parameters`, `engine_run`, `engine_report`,
  `study_scenario`, `study_compare`, `study_read`, `literature_sources`, `literature_document`
  (forty-three in all; the registry's docstring had said thirty-six since Dominion left two). The
  writes go through `tools/writes.py`, audited as their caller's; `POST /api/tools/{name}?by=`
  names a person. Every tool carries a project scope; the MCP server acts in the project
  `--project` names and marks an outside assistant's numbers as its estimates. `docs/TOOLS.md` is
  written by `pnpm gen:tools` from the registry, and `check:tools` holds the file to it, every
  schema's numbers to quantities and counts, and every tool to a project. ADR-008, Implementation
  6.2.
- 6.3 (routes) `llm.ROUTES`: the families `plan`, `explain`, `extract`, `index` and `judge`, each
  an ordered list of `provider:model` specs in Sci RAG Kit's syntax and an effort, with
  `OPENFERMENT_ROUTES` laid over it and `pnpm ready` failing on a table that cannot route. Every
  caller names its family. Anthropic's models are served; a route's model of another provider is
  passed over in words, since calling it reads that provider's key through the kit (§11.1), and
  the per-request key override waits for the owner the same way (owner question 10; ADR-008,
  Implementation 6.3, has the design it would take). The ask budget now keeps back the final
  turn's worst case before another round. `test_llm.py`, `test_ready.py`, `test_postdoc_agent.py`.
- 6.4 (evaluation) The evaluation set is two tables (migration 0006): `eval_questions`, with what
  a good answer does, and `eval_runs`, each run scored by code on tool choice, citations, labelled
  estimates and the claims dropped for a number (`postdoc/evaluate.py`; `pnpm eval seed | run
  [--live]`). Offline, a stand-in named `openferment-standin` answers through the service's answer
  path; its follow-up reads its history from the service and drops a bare number on purpose.
  `scripts/prove.py` step 6 runs it against the proof's project. ADR-008, Implementation 6.4.
  `test_evaluate.py`.

- 6.4 (gate run) In a clean worktree at `9663dc3`: `test:core` 2234 passed, 2 skipped; `test:lit`
  10 passed; `test:sim` 132 passed; every check, the build and `pnpm smoke` passed; `pnpm prove`
  (steps 1, 2, 4, 5, 6, 7, 8) held 43 of 43 checks; the worktree stayed clean. Stage 6 is complete.

### Stage 7 — 2026-10-30

- 7.1 (the generated API) `pnpm gen:api` writes `docs/api/openapi.json`, every route's project
  scope on it (A5; `test_openapi.py`), and `src/api/types.gen.ts` by openapi-typescript (a dev
  dependency, MIT); verify runs `gen:api --check`. `src/data/types.ts` and `check:plan`'s pairs
  stay until the screens read the generated types (a debt below).
- 7.1 (screens) Projects have addresses (`/p/:project`, its views below it); Home opens on the
  projects, a form to make one, the ask box, the recent conversations and the running jobs as live
  cards; the project home is the conversation beside the live trace. The trace cards render the
  event stream at once, each linking to its record. The SFF graph draws in the run report and on a
  flowsheet's page. ADR-009, Implementation 7.1.
- 7.1 (Durable) The snapshot keeps preferences and the writes the service has not acknowledged;
  a record the service holds is never kept there (ADR-014, a departure from §5.5 and A3).
- 7.2 (the walk) `scripts/walk.ts` walks the built app in Chromium against a real service; it is
  the proof's step 9, run in CI after verify. ADR-009, Implementation 7.2.

### Stage 8 — 2026-10-30

- 8.1 The old guidance moved to `docs/history/` at stage 0 (a departure above); STATE.md's two
  still-open "Live owed" items are folded into the section of that name, each judged against this
  build.
- 8.2 `CLAUDE.md`: 134 lines, every line labelled R, P or C, the ten sections stage 8 names; each
  architecture line names its decision record and each contract line its document, held by
  `core/tests/test_guidance.py` (A7) with the decision records 000 to 014 and this file's Resume.
- 8.3 `README.md` (two screens); `COMPONENTS.md` written by `pnpm gen:components` from the package
  map `test_boundaries.py` enforces and each module's docstring, checked in verify;
  `docs/api/intake.md` (§7.3 item 6); `pnpm gen:api` and `pnpm gen:tools` regenerate the rest of
  `docs/api/` and `docs/TOOLS.md`. Verify settled at sixteen stages (ADR-011, Implementation 8); CI
  runs `pnpm prove`, every step, after verify. `scripts/prototype-up.sh`'s header says where the
  records live now.
- 8.4 Proof step 3, offline: the kit's demo corpus (five fictional documents, CC0) through Intake's
  upload; 5 documents in 34 chunks, every chunk embedded; each of the kit's 9 seed questions answered
  by the passage that holds it, in the top five, with its citation; the service in fixture mode
  reads a stand-in's written response at the extract route and anchors its candidate to the stored
  passage, and refuses its second, quoting words the document does not hold (rule `quote`); a
  decision carrying a model's estimate refused at the record store (rule `estimate`); a person's
  decision accepting the candidate, and the record in BioRepo, verified and curated; after the
  restart, the documents and the record reload. The proof's last check reads its own spend table:
  offline it holds no call.
- 8.4 `pnpm prove --live`: the key from `core/.env`, the network, the routed models (here every
  route `claude-haiku-5-5` at effort medium, the session's settings). Step 3 collects the ethanol
  sources (`docs/corpus/ethanol-sources.txt`) and the model extracts PMC4842200 through the service;
  step 6 asks the evaluation set of the routed model. Its first run found two faults, fixed:
  - Intake refused `sgd:S000203483` and `sgd:S000203459`, the form the sources file documents:
    `collectors.by_identifier` takes `SGD:<SGDID>` to SGD's strain address, and a test holds every
    identifier in the file to a collector.
  - Every Postdoc request was refused with HTTP 400, "The compiled grammar is too large": the plan
    schema's typed values beside seven strict tools. `llm.converse` sends such a request again
    with its tools loose and remembers it (ADR-008, Implementation 8).
  - Its second run met OSTI's rate limit: both report addresses redirected to OSTI's 429 page,
    which Intake read as a source serving HTML. `fetch_pdf` now says it is the network's condition
    (`transient`), and the live proof asks such a source again once, two minutes later.
- 8.4 A8: the kit's vendored migrations and prompt templates join `core/licences.toml` as vendored
  code (BSD-3-Clause at `26b3990`), each with its `LICENSE` beside it; `THIRD_PARTY.md` regenerated.
- 8.4 The gate, in a clean worktree at `7e513d9` with no key: `pnpm verify` green, all sixteen
  stages; `pnpm prove` holds 63 of 63 checks offline, steps 1 to 9; the worktree left clean. With
  the key, `pnpm prove --live` held 46 of 46 (steps 1 to 8) on the same tree. Acceptance A1 to A8
  hold, with the departures recorded above (A3: ADR-014 and the tracked `biorepo.json`; A4: the test
  stand-ins). The pull request carries the completion report (§12).
- 8.4, after the pull request (#15): both MCP servers connected at the next session's start, with
  `core/.env` written. Called over stdio as `.mcp.json` starts them, on a proof database holding the
  kit's demo corpus: the `openferment` server with `--project` listed its 45 tools and answered
  `engine_plants` and `literature_sources`; the kit's server answered `corpus_stats` (5 documents,
  34 chunks) and `search_corpus`. With no project the kit's server answered only "Error executing
  tool corpus_stats": the MCP SDK (2.3) hands a client that line alone for an exception other than
  its `ToolError`, and the kit's service refuses with its REST `ApiError`. `literature_mcp.py` now
  raises each refusal as a `ToolError` in its words, takes `--project`, and leaves off the kit's
  two tools that read the concept graph whole (ADR-002, Implementation 8; `test_literature_mcp.py`).
- 8.4, after the pull request: the session's own client, its servers restarted on the new code,
  still read "Error executing tool corpus_stats": the container had restarted, PostgreSQL with it
  stopped, and the kit's `stats` query the database before they ask for a project. `InWords` now
  asks for the project before any call and says any failure in words, as `tools.run` does for
  openFerment's own server; checked over stdio with the database down (both refusals in words) and
  up again.
- 8.5, the remnant sweep (2026-10-31). ruff's pyflakes rules and vulture over the service, knip and
  `tsc --noUnusedLocals --noUnusedParameters` over the client, and three read-only surveys of what
  alpha 1.0 left behind. Each commit kept `test:core` green:
  - The lint: unused imports, f-strings with nothing to format, two request models both named
    `ProposeRequest` (the checks' one is `CheckProposeRequest`), and a thermo test that a duplicate
    name had hidden since it was written; it failed once it ran (its stand-in refused PHB) and
    passes on an invented chemical.
  - The seed's readers: `corpus.py` read alpha 1.0's generated `corpus.json`, module_stores
    `modules.json` and Guild `skills.json`, each whenever the file was there. alpha 2.0 ships none,
    and the live Mini's checkout still holds all three, so its first alpha 2.0 deploy would have
    served the deleted seed. All of them are gone; test_no_seed holds that no service module names
    a projection, in place of checking this checkout's disk. `anchor_report.py` went with them.
  - BioRepo and Witness stand on the project's candidates and decisions alone, their tests on
    candidates planted with the structure anchoring reads; `test_atomic`'s concurrency test, which
    looked for corpus records and skipped on every run since stage 1, runs and passes.
  - One loop: `/api/ask`'s `single` mode paid for a call over the empty corpus and could only
    decline, and nothing sent it. It is gone; the plan's prompt and schema live in
    `postdoc/plan.py`, byte for byte as the loop used them. `/api/health` and `pnpm ready` lost the
    corpus's fields and row; `pnpm ready`'s backup row, which said a git push backs decisions up,
    is gone (Blockers); `pnpm ask:batch` and `pnpm bundle:single` are deleted.
  - The evidence pool is the project's candidates as the standing decisions leave them, its papers
    the documents the project holds; `biorepo.provenance_of` computes a decision's provenance from
    what it is, where the label the browser sent was kept (ADR-006, Implementation 8.5).
  - Program-era dead code: Proforma's yield cap, the store branches no family reaches, `_example`,
    the check:seed entry points, `held_scenarios` where it said `seed_scenarios`; in the client the
    authored cost model, the simulated chat's types, Dominion's routes and patent components, the
    seed's extractor runs, the PHA read-back, the built entries of the subsystem map. `tsconfig`
    now fails typecheck on an unused local or parameter.
  - On screen: Settings said decisions are stored in a committed `biorepo.json`; its colophon,
    fidelity table and version rows, the Architecture page (which lacked pureOS and called fermOS
    unbuilt), Home, the guided tour and Witness (whose provisional mode stood curated seed records in
    as gold) now say what alpha 2.0 does. Witness counts the values reviewers typed, as witness.py
    does.
  - Kept, with reasons in the debts: the `program` key and the texts hashed into artifact ids,
    kinetics' storage branches (§11.5), the test stand-ins, the hand-kept client types.
  - CI: the client's dead-code commit deleted `src/data/runOutputs.ts` without regenerating the
    package map, and verify's `gen:components --check` failed on the three pushes that followed;
    `c8ba32b` regenerated it, verified in a clean worktree first, and CI went green.
  - The second half, from a read-only survey of every place that still described alpha 1.0
    (about sixty a person or Postdoc reads, about seventy comments):
    - Stage 2 made a project's Proforma scenarios, overrides, fits, runbooks and locks rows of
      the project (project_state.py), and the service's own readers went on reading the seed's
      projection, empty since stage 1. `proforma.held_scenarios` now reads the project's
      BioSTEAM scenarios; `selling_price` names and cites them, and `run_flowsheet` runs one as
      its page does (`project_state.run_request`: its flowsheet and parts, the overrides a person
      set there and the fits chosen for it); the params scope, pureOS's naming of a run and the
      module reads see them, and the runbooks read lists the project's runbooks with their locks.
      Their refusals, which sent Postdoc to "the browser that made it", say what the project
      keeps. `test_tools` runs a kept scenario once its person's overrides bind every input.
    - The review queue's filter and the client's refusal rule kept alpha 1.0's committed-file
      rule: a decision on a document with no PMCID, DOI or PMID was kept in the browser only, and
      such records were hidden from the default queue, though `biorepo.write` keeps a decision on
      any document the project holds (an upload, an OSTI report, an SGD entry). The rule is the
      service's now (`paperHeld`). The review card's comparison with a curated record, the span
      carried on promotion and their helpers in review.ts are gone: every record is a candidate.
    - `import_alpha1` computes each decision's provenance as `biorepo.write` does.
    - The paper type loses the `curation-note` text source and the `catalogued` ingest state on
      both sides of the API, and the corpus fields nothing read (thread, tranche, corpusRole,
      verifyNeeded); their branches in the reader, the citation chip and BioRepo go with them.
    - Words: the tool descriptions and refusals Postdoc reads (`search_records`, Primer, kept
      trains, Guild's skills), route and model docstrings (the API document regenerated), the
      screens (the provenance legend's gold and curated labels, Home, the review card and its
      export, the reader, Intake, Organisms, the strain page, runbooks, depositions, Proforma,
      pureOS, Postdoc, the shortcut sheet), the export headers that stamped "corpus OF-COR-001
      v1.0", and the comments of the service and the client.
    - Screenshots of the built app on the proof's kept service found three more: Home's first
      band was "Corpus vitals" with a "Papers catalogued" tile counting documents "awaiting
      full-text ingest", a state no document reaches now; it is "Project vitals", the tile counts
      the documents held and their passages. The reader printed an empty citation line for a
      pasted document with no authors, year or venue; it prints the parts there are. The runbook
      page said a runbook with no product "is not attached to a molecule"; it names no product.
