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
4. **Next step: 1.3** — stage 1, section 5.5: the file stores and the browser's scientific state
   (the merge driver, `data-sync.sh`, `data-prepare.sh`, `decisions-push.sh`,
   `scripts/host/sync_decisions.sh`, the tracked `core/data/biorepo.json`). Then 1.4 (the rest of
   5.6: `react-router-dom`, `recharts`, `src/engine/retrieval.ts`, unused exports and store
   fields, the dead types listed under Known debts), 1.5 (5.7: instruction sprawl to
   `docs/history/`), a minimal smoke over the real service, and the stage 1 gate.
5. Files in flight: none.

## Current stage

Stage 1 — delete. 1.1 (5.3, 5.4) and 1.2 (5.1, 5.2, Dominion and the retired guards of 5.6)
are committed; 1.3 to 1.5, the smoke and the gate remain. Stage 0 is complete except the tag push
(see Blockers).

## Last green runs

| When (UTC) | Suite | Result | Time | Commit |
|---|---|---|---|---|
| 2026-10-30 03:43 | `pnpm test:core` | 2165 passed, 1 skipped, 172 deselected | 5 min 35 s | `d19224f` (baseline) |
| 2026-10-30 03:48 | `pnpm test:sim` | 105 passed, 2233 deselected | 4 min 11 s | `d19224f` (baseline) |
| 2026-10-30 04:08 | `test:core` in a clean worktree | 2083 passed, 1 skipped, 170 deselected | 4 min 44 s | `20bd36d` (1.1) |
| 2026-10-30 04:12 | `test:sim` in a clean worktree | 103 passed, 2151 deselected | 3 min 44 s | `20bd36d` (1.1) |

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
| §10 stage 1.1 | Section 5 runs in the order 5.4 + 5.3 (one commit), 5.1, 5.2, 5.5, 5.6, 5.7 | `demo.py`, `retrieve.py` and `rageval.py` were the heaviest users of the program machinery and build their fixtures through each other; deleting them first spares edits to files deleted one step later, and a commit between 5.4 and 5.3 could not be green |
| §5.3 | `demo.py`'s stand-in evaluator and stand-in records moved to `core/tests/standins.py` (test-only) | Thirteen kept test files (Proforma, fermOS, params, pureOS, tools) test binding, override, ceiling and run-contract rules on them. Stage 4 replaces them with fixtures read from library plants (debt recorded below) |
| §5.4 | `search_passages` stays registered, with one seam (`tools/passages.py: search`) that answers "no literature index exists yet" | Postdoc's quote validation and its tests keep the passage contract; stage 3 fills the seam with Sci RAG Kit. The whole-sentence rule moved to `quotes.py` |
| §10 stage 1.1 | 5.1, 5.2, Dominion and the retired guards (from 5.6) are one commit, 1.2 | The program machinery, the seed and Dominion share the store, the types, `module_stores` and `models`, and the retired guards import the seed: no commit between them could be green |
| §5.2 | Tests that held seeded content were deleted with it; rule tests that only used it as material now run on fictional fixtures: `core/tests/fixtures/test-corpus.json` (placeholder papers and records, the `test_corpus` fixture), placeholder Guild skills and protocols in the alpha 1.0 shape, small fictional projections inside tests, and a test-only categorical field | A4 forbids seeded values under `core/`; the rules (anchoring, review decisions, retrieval, coverage, Guild) stay tested |
| §5.2 | Eval set O (`evalo.py`, `pnpm eval:o`) and the identifier tooling (`identifiers.py`, `scripts/resolve-identifiers.py`, `pnpm ids:*`) are deleted | Eval set O's ten questions named the seed; the identifier tooling patched DOIs into the TypeScript seed |
| §4, §5.2 | The record fields, the vocabulary (carbon sources and unit operations) and the unit tables live in `core/openferment_core/schema/` (`fields.yaml`, `vocabulary.yaml`, `units.json`), with no range and no example value; `src/data/ontology.ts` and `vocabulary.ts` mirror them, held equal by `test_schema.py` through the fixture `pnpm export:unit-fixtures` writes. BioRepo's typed-value refusal is renamed `range` → `unit`; `pyyaml` is a direct dependency | The service needs the fields without the TypeScript seed; a range is a number about a field (ADR-010) |

## Blockers

| Since | Blocker | Next command |
|---|---|---|
| 2026-10-30 | The session's git relay refuses tag pushes (branch pushes work): `git push origin alpha-1.0` ends with "unexpected disconnect while reading sideband packet", lightweight and annotated alike. The tag exists in this container only. Commit `d19224f` stays reachable as an ancestor of `main` | On the owner's machine: `git fetch origin && git tag alpha-1.0 d19224ff0b6eb809b21492d1b7a2e8fd895a0f44 && git push origin alpha-1.0` |

## Known debts (each names the stage that pays it)

| Debt | Paid at |
|---|---|
| `core/tests/standins.py` carries invented stand-in records (on real strain ids) and a closed-form evaluator for rule tests | stage 4: fixtures from `biorefineries` library plants |
| `program` survives as pureOS's chemical-set key (`TrainSpec.program`), and as a field of `FlowsheetInfo`, `VesselSummary`, `TrainSummary` and `TrainProposal`; the UI no longer shows or filters by it | stage 2 (projects) and stage 4 (the adapter) |
| Proforma tool rules that need a successful run of a seed scenario (`run_flowsheet` keeps one run and audits it; `stream_table` on a scenario's run) lost their tests with the seed scenarios | stage 5, when scenarios live in projects |
| The vessel's organism check reads the yeast program's species from a strain catalogue that is empty; its test supplies one | stage 2 (strains with a project's records) or stage 4 |
| `test_proforma_slow.py` and `flowsheets/cornstover_benchmark.py` still state the benchmark price this build once measured (1.968 USD per gallon); the browser no longer shows it | stage 4: the adapter holds a library plant to its package's own test values |
| `units.json` maps `wt%` and `% (w/w)` to `% CDW`, aliases written for the PHA program | the vocabulary review at stage 3 |
| `docs/TOOLS.md` was edited by hand to remove Dominion and the program switch | stage 6 regenerates it (A5) |
| `src/engine/geneos/enumeration` (Dominion era) still serves RunbookDetail's funnel | stage 7 |
| Dead types and fields: `Scenario.kind` `'authored'`, `LessonBlock` `'unit-playground'`, `Product.clearanceState`, `storageIds`, `scaleId`; `recharts` and `react-router-dom` imported by nothing under `src/` | 1.4 |
| Dead service paths the deletions left: the storage machinery (`kinetics.py`'s N and Q states, `fermos._no_broth_product`'s store-in-cells branch, `proforma.fit_info`'s store branch), `proforma._strain_labels`' program map, `proforma.basis_inputs`' `cap` and the yield cap in `_specs`; `fermos.NAMED_NOTE` still says "program" (its text is hashed into every simulation's basis) | stage 4, with the adapter |
| Catalogues that left with the seed are empty in production and supplied by fixtures in tests: held scenarios, the strain catalogue and its aliases, the proposer's products and hosts. Until a project's records carry them, every pureOS proposal is refused for want of a host on file | stage 2 |
| No offline test computes on a published genome-scale model (Yeast9 and iMM904 need their fetched files); a model add-on applied in the worker, and a metabolite-defined product's demand through the worker, are untested | stage 4 |
| `test_proforma.py` holds the package's own regression values and this build's benchmark price to test the parser | stage 4 (A4 review) |
| `core/tests/standins.py` keeps a closed-form ethanol evaluator, stand-in yeast records and `STANDIN_THEORETICAL` | stage 4 (with the row above on stand-ins) |
| No smoke test while the double is gone | end of stage 1: a minimal smoke over the real service; stage 7 extends it |

## Owner questions (execution prompt §13) and the defaults taken

| # | Question | Default taken | Answered |
|---|---|---|---|
| 1 | PostgreSQL as the one database | yes | no |
| 2 | Kit in-process with a local FastEmbed embedder | yes | no |
| 3 | Delete thread Q's TypeScript list, keep `docs/corpus/ethanol-sources.txt` | yes | no |
| 4 | Delete Dominion, return condition recorded | yes | no |
| 5 | Rename `demo` → `assumed` | yes | no |
| 6 | Python pin 3.12 if the kit fails on 3.13 | no pin: the kit's suite passed on 3.13.17 (1584 passed, 31 skipped) | measured |
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
