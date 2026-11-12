# openFerment — progress

The resume point for every session: the alpha 2.0 foundation build (stages 0 to 8, merged into
`main` as #15 on 2026-11-02), the alpha 2.1 work that makes it functional on real work (the
execution prompt of 2 November 2026, stages A to F), and the alpha 2.2 work (the alpha 2.2 execution
prompt of 2 November 2026, the base, stages A to H). Keep it current at every checkpoint. A fresh
session continues from this file and `git log` alone.

## Resume

1. Branch: `claude/alpha-2-2-base`, cut from `main` at `112eb8b` (the merge of #16, alpha 2.1).
   `git fetch origin claude/alpha-2-2-base && git checkout claude/alpha-2-2-base`. The work is the
   alpha 2.2 execution prompt of 2 November 2026 (the base, sealed), stages A to H. Alpha 2.2 closes on
   the branch at stage H (8 November); its pull request to `main`, with the prompt's §9 completion
   report, and the tag `alpha-2.2` on the branch's head follow it.
2. Environment:
   - `pnpm install --frozen-lockfile`
   - `cd core && uv sync --frozen --all-extras`
   - PostgreSQL: `pnpm db:up` (compose.yaml), or a local PostgreSQL 16 or later with pgvector and a
     role that may create databases (in a cloud container, `service postgresql start`).
     `OPENFERMENT_DATABASE_URL` in `core/.env` (`core/.env.example` has the development address),
     then `pnpm db:migrate`. The tests make databases of their own on the server
     `OPENFERMENT_TEST_DATABASE_URL` names; the default is the compose role on 127.0.0.1:5432.
   - `core/.env` holds the key and the budgets (`OPENFERMENT_DAILY_BUDGET_USD=150`,
     `OPENFERMENT_ASK_BUDGET_USD=8`). Its five routing lines stay commented out (F.2f), so every
     family runs on `llm.ROUTES` (ADR-008, Implementation 17; `docs/api/postdoc.md`, the routing
     table): `plan`, `explain` and `extract` on Opus then Sonnet at high, `index` on Haiku at low,
     `judge` on Opus then Sonnet at max. A comparison names its table in `OPENFERMENT_ROUTES` on the
     command line. A cloud session's own environment pins the three model settings
     (`OPENFERMENT_MODEL`, `OPENFERMENT_FALLBACK_MODEL`, `OPENFERMENT_INDEX_MODEL`) to Haiku and
     `OPENFERMENT_EFFORT` to medium, and carries the key as `OPENFERMENT_API_KEY`, which `bash
     scripts/session-start.sh` writes into `core/.env`; the service reads `core/.env` with
     `override=False`, so run every command with the four settings unset (`env -u OPENFERMENT_MODEL -u OPENFERMENT_FALLBACK_MODEL -u OPENFERMENT_INDEX_MODEL -u
     OPENFERMENT_EFFORT <command>`).
3. First tests to run: `pnpm test:core`, then `pnpm test:sim`.
4. **Where alpha 2.2 stands at its close** (Current stage; the Log). Stages A to E and G are done,
   stage F is done as far as the Anthropic account allowed, and stage H's steps 1 and 2 are done
   (step 1's `pnpm prove --live` waiting on the account); step 3, the pull request with §9's report
   and the tag `alpha-2.2` attempted once, comes next (item 7). The base is sealed: `docs/api/engines.md`
   and ADR-015 are the engine contract, `biosteam`, `kinetics` and `train` register through the
   entry-point group `openferment.engines`, each holds `conform`'s eight checks, and every run is one
   `runs` row of one shape (B, C); a reading deposited at the bench enters a scenario as a
   `measurement`, and a run resting on readings and the package's defaults reads `measured` (C.5);
   both strangers finished their first round with no core file changed (D;
   `docs/reports/handoff-2026-11.md`); every screen and `src/lib` module reads the generated types,
   `src/data/types.ts` is deleted, and a project's catalogues have a screen at `/catalogues` (E); the
   routing defaults are set on the comparison's evidence and a plan turn's room follows its route's
   effort (F.2; ADR-008, Implementations 16 and 17); the retrieval lanes that ask no model are measured
   over the Ethanol project (F.5; `docs/reports/literature-retrieval.md`); the live host's runbook and
   scripts are held to the tree (G); H.0 swept every screen and the service on the final tree; and
   stage H ran `pnpm verify` green on all sixteen stages and `pnpm prove` offline, 99 of 99 checks in 203 s with no model call (Last green
   runs). The Ethanol project stands in this container's `openferment_dev` (22 documents, 457
   candidates waiting for the owner's review), and alpha 2.1's in `openferment_dev_alpha21`, read with
   SELECT alone; a fresh container makes the project again on Home from `docs/corpus/ethanol-sources.txt`
   through Intake (four minutes of collecting), then extracts (fourteen minutes). Alpha 2.2 spent
   39.723806 USD over 349 calls (Spend). `docs/BASE.md` is the page for a reader new to the base, and
   the Known debts table stands in three groups: paid, open, and left by decision.
5. **What waits on the account** (Blockers). Every model call is refused until 2026-12-01 at 00:00 UTC,
   or until the owner raises the limit in the Anthropic console (Settings, Limits). Then, in this order,
   from the repository's root, with the four settings of item 2 unset in a cloud session, the service
   and every live command run with `OPENFERMENT_DATA_DIR` on a copy of the fetched caches (Yeast9's and
   iMM904's files and the toolkit's reference files). This session's copy is
   `/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/f/data/`, in this session's own
   scratchpad, and stays with this container. A fresh container leaves `OPENFERMENT_DATA_DIR` unset
   and fills `core/data/` again: `pnpm geneos:fetch` for the genome-scale models, and `cd core && uv
   run --frozen --all-extras python -m openferment_core.engine.sff fetch` for the toolkit's reference
   files, as stage 4 fetched them. `OPENFERMENT_MAX` stands for the opus-max table as one line of
   JSON, as `docs/reports/model-routing-2026-11.md` writes it out under the alpha 2.2 part's "To
   finish it" ("Alpha 2.2, stage F: the comparison asked again (8 November 2026)", from line 491).
   Each command spends, under the day's cap of 150 USD:
   - `pnpm ready --probe`, its probe row green;
   - the larger room's measure: `OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES="$OPENFERMENT_MAX" pnpm
     eval run --live --suite ethanol --tag opus-max-room --judge --only
     eq-eth-01,eq-eth-02,eq-eth-03,eq-eth-04` (the tag `opus-max` keeps the old room's record);
   - the table's other ten on the same table and tag: the same command with `--only
     eq-eth-05,eq-eth-06,eq-eth-07,eq-eth-08,eq-eth-09,eq-eth-10,eq-eth-11,eq-eth-12,eq-eth-13,eq-eth-14`;
   - the second judge, Sonnet alone at max over every tag's newest runs: `OPENFERMENT_PROJECT=ethanol
     OPENFERMENT_ROUTES='{"judge":{"models":["claude-sonnet-5-5"],"effort":"max"}}' pnpm eval judge
     --suite ethanol`;
   - the summary, `OPENFERMENT_PROJECT=ethanol pnpm eval summary --suite ethanol --rows`, and the
     routing report's rule worked again on it (a default the second judge reverses returns to ADR-008's
     Implementation 17 with its numbers);
   - F.3: the fourteen asked on the Postdoc screen in the Ethanol project on the final routes, their
     record in `docs/reports/live-questions-2026-11.md`;
   - F.4: `pnpm build && pnpm prove --live`;
   - F.5's live run: `pnpm lit:graph --project ethanol --by <name>`, then `pnpm lit:report --project
     ethanol --by <name> --judge --render`.
6. **What waits on the owner** (Blockers; Owner questions):
   - the merge of the pull request from `claude/alpha-2-2-base` into `main` (item 7 opens it);
   - after the merge, the live-host install on the Mini, `docs/runbooks/live-host-install.md` steps 0
     to 6 (Blockers), the owner's first install being the test of the host scripts on macOS (Known
     debts, open);
   - the nightly's dump, written to the place the prompt's §3 names (`~/openferment-backups/`, seven
     daily files kept, `scripts/host/nightly.sh`): the owner's first install runs it, its first night
     the first on macOS (Blockers);
   - the tag pushes the session's git relay refuses, from the owner's machine (Blockers);
   - owner questions 11, 12 and 13, each default standing in the tree; question 13 asks how `has_key`
     reads the key line (stage G), a change to how a key is read;
   - the review of the Ethanol project's 457 candidates in BioRepo;
   - the licence (ADR-012);
   - the account's limit, raised if the live steps of item 5 should run before 2026-12-01.
7. Next: stage H's step 3, the pull request from `claude/alpha-2-2-base` into `main` with the
   prompt's §9 completion report, and the tag `alpha-2.2` attempted once on the branch's head. Files in
   flight: none; stage H's commits hold the records, the runs of its step 1 and the close review's
   fixes (the Log, stage H).
8. **The bug hunt and its fixes.** The hunt of `2047f5a` (10 and 11 November) is reported in
   `docs/reports/bug-hunt-2026-11.md` on `claude/alpha-2-2-bughunt`, its reproductions in
   `bughunt/repro/<id>/run.sh`. The fixes take the report's fix order group by group on
   `claude/alpha-2-2-fixes`, cut from the hunt's head (`fa8db4a`); each group's fix reruns its
   reproductions twice beside the hunt's logs (`after-fix-run1.log`, `after-fix-run2.log`). Group 1
   (H5-01) is done, and so is the concept-graph build race its review found; group 2 (H7-01, the
   browser's shared pending-writes snapshot) is done; group 3 (H7-04, a scope's overrides written
   whole) is done, each write of a scope laid on key by key against the rows it read; group 4 (H5-03,
   a write under one kind replacing another kind's row, in the same `_put`) is next. Groups 16
   and 19 change how a key is read, a stop condition, and wait on the owner (the Log, Fixes after the
   bug hunt).

## Current stage

Alpha 2.2, stage H (2026-11-08, steps 1 and 2 done; step 3, the pull request with §9's report and the tag
`alpha-2.2` attempted once, comes next): the close. H.0 swept every screen and the service on the final tree,
each finding confirmed against the code and fixed where it held, in five commits (the Log). Stage H ran `pnpm
verify` on all sixteen stages and `pnpm build && pnpm prove` offline on the branch as it stood (Last green runs),
wrote this file's Resume, Known debts (paid, open, left by decision), Blockers and Spend to the branch's end,
brought `CLAUDE.md`'s alpha 2.2 lines to the tree, gave `README.md` five lines on alpha 2.2, and held
`docs/BASE.md` to the tree. A close review read the commit, and its fixes followed: the nightly's dump in
`scripts/host/nightly.sh` to the place the prompt's §3 names, with its tests on stand-ins, and the records' facts and
words (the Log). `pnpm prove --live` waits on the account (Blockers). The pull request into `main` and the tag
`alpha-2.2` follow.

Alpha 2.2, stage G (2026-11-08, done): the live host's runbook and scripts held to the tree. A reader held
`docs/runbooks/live-host-install.md` and `scripts/host/` to the code, five verifiers held its findings and its patch to
Homebrew's source, python-dotenv and stand-ins, and every verdict is applied: the keg's tools, PostgreSQL from
power-on, the example's database line kept out of the live `core/.env`, the checkout at `~/openferment`, step 5's
order, `pnpm ready`'s rows, the tests' server for `deploy.sh --verify`, and the settings read in the forms of
python-dotenv they take (the Log). An independent reviewer read the commit, and its fixes followed: the install waits
for alpha 2.2's merge into `main`, and the runbook's commands read the lock as committed. Nothing in it has run on
macOS.

Alpha 2.2, stage F (2026-11-05 to 2026-11-08, done as far as the account allowed): the live work. F.0's probe answered, and F.1 rebuilt the Ethanol
project from Home through Intake, its 22 documents extracted on the `extract` route. F.2 ran as far as the account
allowed: the evaluation the comparison reads (F.2a), the judge's room (F.2c, ADR-008 Implementation 15), the haiku,
sonnet and opus-high tables asked and judged with opus-max's first four, the plan's room by the route's effort (F.2g,
Implementation 16), and the routing report written to its end with the defaults set in `llm.ROUTES` (F.2e and F.2f,
Implementation 17). F.5's commands were built with no model call (F.5.1 to F.5.4: a run's own count, the concept graph
over a project's own passages, the graph tools on the `sci-rag` server, the report's project lanes; Implementation 18
and ADR-002's Implementation F). They and stage E's E.17 to E.20 landed by cherry-pick on 8 November, the landing
review's fixes after them. The account's usage limit has refused every model call since 8 November 04:28 UTC, until
2026-12-01 (Blockers), and the live steps wait on it in Resume item 5's order.

Alpha 2.2, stage E (2026-11-04 to 2026-11-05, done): the screens on the generated types, and the catalogues. E.0a and
E.0b gave every JSON route its model, so a schema the service only writes lists every property as required and the
rows a project keeps of its pages read as theirs; E.1 to E.14 moved each lib with the screens and components that read
it onto the generated types, one commit each in the order §6.5 names, the browser's own types going to their owners;
E.8 built the catalogues screen, E.9 and E.12 put geneOS, Guild, the protocols and Primer on the project's catalogues,
and E.12a gave a project its protocols and a lesson its body (ADR-017, ADR-018); E.10 deleted the research funnel; E.15
deleted `src/data/types.ts`, `check:plan` keeping the provenance ranking alone; and E.16 paid the agent builder's
interface points. The gate (E.gate) fixed what three reviewers found, among it a lesson's body lost on an edit and the
protocol editor opened by its address with no steps, and holds `pnpm verify` on all sixteen stages, `pnpm smoke` with
no key on every screen and `pnpm prove` offline with the catalogue screen in the walk. Its two Known debts and the
gate's leftovers followed during stage F, built in a worktree and landed on 8 November: E.17 (a reading chosen on a
Proforma panel row), E.18 (Studies' run card naming a kinetics configuration by its kind), E.19 (the screens saying the
service keeps a project's rows), their review (E.debts) and E.20 (the gate's leftovers).

Alpha 2.2, stage D (2026-11-04, done): the handoff by strangers. D.0 read the handoff pages as
the two strangers would and closed every gap before the core's commit was recorded (D.1,
`CORE=6f85338`). Each stranger, given its brief verbatim and a worktree at `CORE`, finished in
its first round with no core file changed: the mirror engine, installed, listed, conformed 8 of
8 and run from the Runs screen in the proof's walk; and the record-reader, whose write and
audit row name `example-agent/0.1` (`docs/reports/handoff-2026-11.md`).

Alpha 2.2, stage C (2026-11-03 to 2026-11-04, done): every run one shape. C.1 pinned sixteen computations to their ids
and output hashes before anything moved, fixed the worker's handler mismatches, and gave every
engine's computation one keeper, `engine/runs.keep_run`, with `outputs.values` that comparisons
and runbooks read for a run of any engine. C.2 registered fermOS as the engine `kinetics`: its
requests take typed quantities with their origins, each simulation, kept forecast and vessel
design is one `runs` row at every door, and `conform kinetics --inputs <file>` holds all eight
checks, which `pnpm prove` step 10 makes with the placeholders it writes. C.3 registered pureOS's
trains as the engine `train`: a train's requests take typed inputs named by place, each run is one
`runs` row at every door with the values pureOS reads and its SFF file or the toolkit's words, and
`conform train --project <id>` holds all eight checks in a project with a train, which `pnpm prove`
step 10 makes from step 4's corn stover run. C.3b has conformance read a project and check a copy
of it on a database of its own: every row of the project the same after the checks, the verdict the
one row written where they read, the production database read as any other, and each train that
can run checked, each one left out listed with its words. C.4 has Proforma and the library door
take typed inputs at every door, keeps each Proforma run as a row of `biosteam` with its SFF file,
and gives `biosteam` the shelf's scenario flowsheets as things through a provider Proforma
registers with it; a run a person makes through the panel keeps the artifact id it had, and the
Proforma pin moved once under D1's amendment at C.4 (Departures). C.5 gives every door that takes
values the `measurement` origin: a reading a person deposited at the bench and read back, looked up
in the project's depositions before anything runs and refused in words when it does not stand; a
run resting on readings and the package's defaults is `measured`; the bench records readings
against a locked runbook's measures alone, the service keeps its record the bench's way, and the
proof's walk deposits a reading, makes a scenario on it and reads its run `measured`. C.6 retires
the shelf's two hand-written entries (the reference run and its screen read the library shelf's
`cornstover` and `corn`, a kept run of either entry still replaying), reads every Proforma
scenario as the project's, and imports an SFF file by its https address, a public address alone,
at the person's word. C.7 is the gate: `pnpm prove` step 10 requires every engine
`core/pyproject.toml` registers and makes the eight checks on each, `kinetics` on the placeholders
it writes and `train` on a train it makes from step 4's corn stover run, the proof's project the
same after the checks; step 9's walk holds its run `measured` on the reading it deposited;
Postdoc's ethanol suite gains the base's two questions (fourteen in all); the bench's
readings-alone record is ADR-016; and three reviewers' findings are fixed, among them the engine
reads naming every engine and the runs each made, and a train read from a run starting on the
stream that carries the most product into it.

Alpha 2.2, stage B (2026-11-03): the engine contract. `docs/api/engines.md` is the page a stranger
builds an engine from, ADR-015 records the registry on the entry-point group `openferment.engines`,
and `biosteam` is registered through `core/pyproject.toml`'s own entry point with every number and
test as it was. `conform biosteam` holds all eight checks; `pnpm prove` runs them for every
registered engine (step 10).

Alpha 2.2, stage A (2026-11-02): #16 merged into `main` as `112eb8b` and `claude/alpha-2-2-base`
cut from it; the tag pushes refused again (Blockers); `pnpm verify` green on all sixteen stages and
`pnpm prove` 66 of 66 offline on the merged `main`; `pnpm ready --probe` added and run once, and the
index route answered, so the account's usage limit no longer refuses a call.

Alpha 2.1, stage F (2026-11-02): the work is on `claude/alpha-2-1-functional` with its pull request
to `main` and the §9 completion report. Stage C is held by the Anthropic account's own usage limit
(Blockers), which refuses every model call until the owner raises it or 2026-12-01; stage D paid
debts 2 and 4, debt 1 in part and one of debt 6's tests; stage E wrote the live host's runbook.
`pnpm verify` is green on all sixteen stages and `pnpm prove` holds 66 of 66 offline.

Alpha 2.1, stage B (2026-11-02): the project "Ethanol" made on Home, the 22 ethanol sources held
through Intake (814 passages), extraction over every document (272 candidates waiting for the
owner's review), the twelve questions asked through the Postdoc screen on Opus, and the owner's
plant work done from the screens (`docs/reports/live-questions-2026-11.md`). The first asking
answered five of twelve as expected; nine faults were fixed with tests across two more askings,
and eleven of twelve now come back as expected, the twelfth (Q1) as expected in kind and short in
coverage. The screens could not run a plant, make a scenario of a person's own or import an SFF
file; Studies, a run's page and the new Flowsheets screen now do, and every run, comparison, locked
runbook and SFF record read back after a restart. Stage B spent 17.65 USD over 203 calls (Spend).

Stage A (2026-11-02): #15 is merged into `main` with a merge commit (`7f990f8`), and the work
continues on `claude/alpha-2-1-functional`. The tag push was refused again (Blockers). `pnpm
verify` is green on all sixteen stages after conftest stopped `core/.env`'s routing table reaching
the offline tests; `pnpm prove` holds 63 of 63 offline and `pnpm prove --live` 46 of 46 on the Opus
routes, for 10 calls and 0.6601 USD.

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
| 2026-10-30 05:43 | `test:core` with 1.3 | 1888 passed, 2 skipped, 128 deselected | 4 min 12 s | 1.3 |
| 2026-10-30 05:44 | `test:sim` in a clean worktree | 102 passed, 1957 deselected | 4 min 9 s | `b24e997` (1.2) |
| 2026-10-30 06:10 | Stage 1 gate in a clean worktree: `typecheck`, `build`, `test:core` | 1888 passed, 2 skipped, 128 deselected | 4 min 7 s | 1.6 |
| 2026-10-30 06:10 | Stage 1 gate: `test_no_seed.py`, `test:sim`, `pnpm smoke` | 45 passed; 102 passed, 1916 deselected; 11 of 11 rail entries open | 4 s; 3 min 59 s; 22 s | 1.6 |
| 2026-10-30 06:25 | `test:core` with 2.1 | 1905 passed, 2 skipped, 128 deselected | 4 min 33 s | 2.1 |
| 2026-10-30 06:47 | `test:core` with 2.2; `check:tools`; `pnpm smoke` (own database, project made through the API) | 1920 passed, 2 skipped, 128 deselected; passed; 11 of 11 rail entries open in the project | 4 min 26 s | 2.2 |
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
| 2026-10-30 18:39 | `pnpm prove --live` (steps 1 to 8): 22 of 22 ethanol sources, 814 chunks; PMC4842200 extracted by `claude-haiku-5-5` (8 candidates kept, 2 refused); the evaluation set answered live | 46 of 46 checks hold; 10 calls, $0.0163 from the proof's spend table | 7 min 21 s | 8.4 |
| 2026-10-30 18:58 | `test:core` with stage 8 (the guidance test, the SGD form, the grammar fix, OSTI's rate limit) | 2250 passed, 2 skipped, 168 deselected | 5 min 17 s | 8.4 |
| 2026-10-30 19:13 | Stage 8 gate in a clean worktree at `7e513d9`, no key: `pnpm verify`, all sixteen stages; `test:core`; `test:sim`; `test:lit`; `smoke` | every stage green; 2250 passed, 2 skipped, 168 deselected; 132 passed; 10 passed; 12 of 12 screens open | 13 min 33 s (verify) | 8.4 (gate) |
| 2026-10-30 19:16 | Stage 8 gate, the same worktree: `pnpm prove`, steps 1 to 9 offline (1: 4 checks, 2: 1, 3: 9, 4: 7, 5: 10, 6: 9, 7: 3, 9: 9, 8: 10, the spend: 1); the worktree left clean | 63 of 63 checks hold; the proof's spend table holds no call | 2 min 47 s | 8.4 (gate) |
| 2026-10-31 01:39 | `test:core` with 8.5's second half (the project's scenarios and runbooks read, the review path, the words) | 2257 passed, 1 skipped, 168 deselected | 4 min 55 s | `5287542` |
| 2026-10-31 01:56 | 8.5 gate on `74381fb`, no key: `pnpm verify`, all sixteen stages (`test:core` 2257 passed, 1 skipped; `test:sim` 132 passed; `test:lit` 10 passed; `smoke` 12 of 12 screens); `pnpm prove`, steps 1 to 9 offline | every stage green; 63 of 63 checks hold, no call in the proof's spend table | 11 min 42 s (verify); 2 min 24 s (prove) | `74381fb` (8.5 gate) |
| 2026-10-31 01:58 | On the proof's kept service: a document pasted in (no DOI, no PMCID), a stand-in candidate on it, the default review queue in Chromium, Accept; both MCP servers over stdio on the proof's database | the candidate listed and accepted, the service keeping the decision `verified` under the reviewer's name, no console error; `openferment` 45 tools, `runbooks_read` lists the proof's locked study runbook, `selling_price` refuses an unknown id in words; `sci-rag` refuses with no project, serves the project's 7 documents in 36 chunks and refuses an unknown document in words | | `74381fb` (8.5 gate) |
| 2026-10-31 02:00 | `pnpm test:slow` (by hand, outside verify), on the 8.5 gate's head | 8 passed, 2418 deselected | 1 min 55 s | `74381fb` (8.5 gate) |
| 2026-10-31 02:59 | `pnpm build`, then `pnpm prove --keep` on `b72fd12`; the tour's eleven screenshots in Chromium on the kept service | 63 of 63 checks hold; every page opens, and the shots show what the second pass fixed | 2 min 24 s (prove) | `b72fd12` |
| 2026-10-31 03:12 | `test:core`, typecheck, plan, figures, state, reconcile, `gen:components --check`, `gen:api --check`, `pnpm smoke` on the second pass; the shots again on the rebuilt client | 2257 passed, 1 skipped, 168 deselected; all passed; 12 of 12 screens open | 4 min 37 s | `d0bda01` |
| 2026-10-31 03:22 | `pnpm prove` with its data directory removed at the end; `test:core` | 63 of 63 checks hold, and the run's directory is gone from `/tmp`; 2257 passed, 1 skipped, 168 deselected | 2 min 20 s; 4 min 36 s | `724843d` |
| 2026-11-02 11:52 | Alpha 2.1 stage A on `7f990f8` with conftest's isolation fix, the Opus `core/.env` in place: `pnpm verify`, all sixteen stages | every stage green: `test:core` 2257 passed, 1 skipped, 168 deselected; `test:sim` 132 passed; `test:lit` 10 passed; `smoke` 12 of 12 screens | 11 min 12 s | `d30fb63` |
| 2026-11-02 11:56 | `pnpm build && pnpm prove`, offline, steps 1 to 9 | 63 of 63 checks hold, no call in the proof's spend table | 2 min 41 s | `d30fb63` |
| 2026-11-02 12:05 | `pnpm prove --live`, steps 1 to 8, every route on the alpha 2.1 table (`plan`, `explain`, `extract` and `judge` on `claude-opus-5-5`, `index` on `claude-haiku-5-5`): 22 of 22 ethanol sources, 814 chunks; PMC4842200 extracted by `claude-opus-5-5` for 0.1898 USD (26 candidates kept, 12 refused); the evaluation set asked of `claude-opus-5-5` | 46 of 46 checks hold; 10 calls, 0.6601 USD from the proof's spend table; scored by code `eq-price` tools 1, citations 1, estimates 1, bare numbers 0 (one claim dropped for a number), `eq-dearer` tools 1, citations 1, estimates 0, bare numbers 1 | 7 min 54 s | `d30fb63` |
| 2026-11-02 19:41 | Alpha 2.1 stage B on `2d2ca61`, the Opus `core/.env` in place: `pnpm verify`, all sixteen stages | every stage green: `test:core` 2279 passed, 1 skipped, 168 deselected; `test:sim` 132 passed; `test:lit` 10 passed; `smoke` 12 of 12 screens | 9 min 34 s | `2d2ca61` |
| 2026-11-02 19:43 | `pnpm build && pnpm prove`, offline, steps 1 to 9 | 66 of 66 checks hold, the walk's scenario begun from a run, Studies' plants and Flowsheets among them; no call in the proof's spend table | 2 min 11 s | `2d2ca61` |
| 2026-11-02 20:55 | Alpha 2.1 stage F on `32b95f1`, the Opus `core/.env` in place: `pnpm verify`, all sixteen stages | every stage green: `test:core` 2302 passed, 1 skipped, 168 deselected; `test:sim` 132 passed; `test:lit` 10 passed; `smoke` 12 of 12 screens | 9 min 32 s | `32b95f1` |
| 2026-11-02 20:58 | `pnpm build && pnpm prove`, offline, steps 1 to 9 | 66 of 66 checks hold; no call in the proof's spend table. `pnpm prove --live` was not run: the account's usage limit refuses every call (Blockers) | 2 min 6 s | `32b95f1` |
| 2026-11-02 21:29 | Alpha 2.1 F.2, A→B→A held within one part in 10¹²: `pnpm test:sim` | 132 passed, 2339 deselected | 4 min 9 s | F.2 |
| 2026-11-02 21:35 | `pnpm test:core` | 2302 passed, 1 skipped, 168 deselected | 3 min 59 s | F.2 |
| 2026-11-02 22:07 | Alpha 2.1 F.3, every conversation held: `typecheck`, `check:state`, `gen:components --check`, `check:plan`, `build`, `pnpm test:core`, `pnpm smoke` | all passed; 2302 passed, 1 skipped, 168 deselected; 12 of 12 screens open | 4 min 13 s (`test:core`) | F.3 |
| 2026-11-02 23:46 | Alpha 2.2 stage A on `112eb8b` (the merge of #16), `core/.env` as the prompt's §4 names: `pnpm verify`, all sixteen stages | every stage green: `test:core` 2302 passed, 1 skipped, 168 deselected; `test:sim` 132 passed; `test:lit` 10 passed; `smoke` 12 of 12 screens | 9 min | `112eb8b` |
| 2026-11-02 23:49 | `pnpm build && pnpm prove`, offline, steps 1 to 9 | 66 of 66 checks hold; no call in the proof's spend table | 2 min 18 s (the proof 119 s) | `112eb8b` |
| 2026-11-03 01:24 | Alpha 2.2 stage B gate on `e375ede`: `pnpm verify`, all sixteen stages | every stage green: `test:core` 2328 passed, 1 skipped, 171 deselected; `test:sim` 135 passed (132 and the three of `test_engines_sim.py`); `test:lit` 10 passed; `smoke` 12 of 12 screens | 13 min 56 s | `e375ede` |
| 2026-11-03 01:28 | `pnpm prove`, offline, steps 1 to 10 | 69 of 69 checks hold: step 10 lists `biosteam`, `conform biosteam` holds all eight, its verdict listed; no call in the proof's spend table | 3 min 35 s | `e375ede` |
| 2026-11-03 01:50 | `pnpm test:core` on B.5 (the contract's defects the design measured) | 2343 passed, 1 skipped, 172 deselected | 5 min 22 s | B.5 |
| 2026-11-03 04:03 | `pnpm test:core` on B.6 (the critic's defects and the review's) | 2397 passed, 1 skipped, 172 deselected | 5 min 8 s | B.6 |
| 2026-11-03 04:08 | B.6: `pnpm test:sim`; verify's fast stages (`check:secrets`, `typecheck`, both `--check`s, `check:plan`, `check:licences`, `check:tools`, `check:guild`, `check:state`, `check:figures`, `test:reconcile`); `build`; `smoke` | 136 passed; every stage green; 12 of 12 screens open | 5 min 14 s (`test:sim`) | B.6 |
| 2026-11-03 06:10 | C.1: `pnpm test:core`; `test:sim` (the fix round's); `typecheck`, both `--check`s, `check:plan`, `check:tools`, `check:state`, `check:figures`, `check:secrets`; `build`; `smoke` | 2422 passed, 1 skipped, 174 deselected; 138 passed; every stage green; 12 of 12 screens open | 6 min 0 s (`test:core`) | C.1 |
| 2026-11-03 10:52 | C.2: `pnpm test:core`; `test:sim`; the pins; `typecheck`, the three `--check`s, `check:tools`, `check:plan`, `check:state`; `build`; `smoke`; `pnpm prove --steps 10`; `pnpm prove`, offline, steps 1 to 10 | 2458 passed, 1 skipped, 174 deselected; 138 passed; 13 passed; every stage green; 12 of 12 screens open; 11 of 11 checks, `conform kinetics` and `conform biosteam` 8 of 8 each; 71 of 71 checks | 7 min 38 s (`test:core`); 265 s (the proof) | C.2 |
| 2026-11-03 12:42 | C.3: `pnpm test:core`; `test:sim`; the pins; `typecheck`, the three `--check`s, `check:tools`, `check:plan`, `check:state`, `check:secrets`, `check:figures`, `check:guild`, `check:licences`, `test:reconcile`; `build`; `smoke`; `pnpm prove --steps 10`; `pnpm prove`, offline, steps 1 to 10 | 2474 passed, 1 skipped, 175 deselected; 139 passed; 13 passed; every stage green; 12 of 12 screens open; 22 of 22 checks, `conform train`, `conform kinetics` and `conform biosteam` 8 of 8 each; 75 of 75 checks | 7 min 28 s (`test:core`); 297 s (the proof) | C.3 |
| 2026-11-03 15:00 | C.3's review round: `pnpm test:sim`; `pnpm test:core`; the touched files and the pins; `typecheck`, the three `--check`s, `check:plan`, `check:state`, `check:tools`, `check:secrets`, `check:figures`; `build`; `smoke`; `pnpm prove`, offline, steps 1 to 10 | 140 passed, 2521 deselected; 2484 passed, 1 skipped, 176 deselected; every file and pin green; every stage green; 12 of 12 screens open; 75 of 75 checks, `conform train`, `conform kinetics` and `conform biosteam` 8 of 8 each | 7 min 5 s (`test:sim`); 7 min 29 s (`test:core`); 299 s (the proof) | C.3 |
| 2026-11-03 17:36 | C.3b and its review round: the touched files and the pins; `pnpm test:sim`; `pnpm test:core`; `gen:api`, `gen:tools` and `gen:components` (no file changed); `build`; `pnpm prove`, offline, steps 1 to 10 | 270 passed; 140 passed, 2530 deselected; 2494 passed, 1 skipped, 176 deselected; every stage green; 75 of 75 checks, `conform train` 8 of 8 on a copy of the proof's project beside `conform biosteam` and `conform kinetics` | 2 min 17 s (the touched files); 5 min 58 s (`test:sim`); 6 min 56 s (`test:core`); 273 s (the proof) | C.3b |
| 2026-11-03 21:30 | C.4 and its review round: the touched files and the pins; `pnpm test:sim`; `pnpm test:core`; `gen:api`, `gen:tools` and `gen:components`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:tools`; `build`; `smoke`; `pnpm prove --steps 10`; `pnpm prove`, offline, steps 1 to 10 | 477 passed, the pins 13 of 13 (the Proforma pin's second id, Departures); 141 passed, 2558 deselected; 2522 passed, 1 skipped, 177 deselected; the three files regenerated; every check green; 12 of 12 screens; 22 of 22 checks, `conform biosteam`, `conform kinetics` and `conform train` each 8 of 8; 75 of 75 checks | 1 min 56 s (the touched files); 7 min 12 s (`test:sim`); 7 min 1 s (`test:core`); 172 s (step 10); 262 s (the proof) | C.4 |
| 2026-11-04 01:25 | C.5 and its review round: the touched files and the pins; `pnpm test:sim`; `pnpm test:core`; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:tools`, `check:guild`, `check:secrets`, `test:reconcile`; `build`; `smoke`; `pnpm prove --steps 9`, offline | 393 and 474 passed, the pins 13 of 13; 141 passed, 2624 deselected; 2587 passed, 1 skipped, 177 deselected; the three files regenerated and current; every check green; 12 of 12 screens; 43 of 43 checks | 1 min 29 s and 2 min 56 s (the touched files); 6 min 37 s (`test:sim`); 6 min 43 s (`test:core`); 132 s (step 9 with what it stands on) | C.5 |
| 2026-11-04 06:33 | C.6 and its review round: `pnpm test:core`; `pnpm test:sim`; `build`; `smoke`; `pnpm prove`, offline, steps 1 to 10 | 2678 passed, 1 skipped, 175 deselected; 142 passed; green; 12 of 12 screens; 82 of 82 checks | 7 min 43 s (`test:core`); 295 s (the proof) | `f5405f8` |
| 2026-11-04 07:06 | C.7, before its review round: `pnpm build`, `pnpm prove`, offline, steps 1 to 10; `pnpm verify`, all sixteen stages | 82 of 82 checks, no call in the proof's spend table; every stage green: `test:core` 2681 passed, 1 skipped, 175 deselected; `test:sim` 142 passed; `test:lit` 10 passed; `smoke` 12 of 12 screens | 273 s (the proof); 16 min 31 s (verify) | `f5405f8` and C.7 |
| 2026-11-04 10:07 | C.7's review round: the touched files and the pins; `pnpm test:sim`; `pnpm test:core`; `gen:api`, `gen:tools` and `gen:components`; `typecheck`, `check:secrets`, `check:plan`, `check:state`, `check:figures`, `check:licences`, `check:guild`, `check:tools`, `test:reconcile`; `build`; `pnpm prove`, offline, steps 1 to 10; `pnpm verify`, all sixteen stages | 463 passed, the pins 13 of 13; 142 passed, 2721 deselected; 2687 passed, 1 skipped, 175 deselected; TOOLS.md and COMPONENTS.md regenerated, the OpenAPI document as it was; every check green; green; 83 of 83 checks, `conform biosteam`, `conform kinetics` and `conform train` each 8 of 8, no call in the proof's spend table; every stage green: `test:core` 2687 passed, 1 skipped, 175 deselected; `test:sim` 142 passed, 2721 deselected; `test:lit` 10 passed; `smoke` 12 of 12 screens | 4 min 5 s (the touched files); 8 min 57 s (`test:sim`); 7 min 17 s (`test:core`); 295 s (the proof); 18 min 0 s (verify) | C.7 |
| 2026-11-04 10:18 | The stage C gate: `pnpm test:core` on `466d10e` with C.7; `test_proforma_runs` with the simulator's state left ready, and as the suite runs it; the changed tests on Python 3.12 with the database address empty | 2687 passed, 1 skipped, 175 deselected; 11 passed each way; 241 passed | 7 min 43 s; 7 s; 3 min 3 s | `466d10e` and C.7 |
| 2026-11-04 10:43 | CI on `1243e81` (C.7), run 41814877309: `pnpm verify`, then `pnpm prove` | every stage green: `test:core` 2687 passed, `test:sim` 142 passed, `test:lit` 10 passed, `smoke` 12 of 12 screens; every proof check holds | 7 min 44 s (verify); 126 s (the proof) | `1243e81` |
| 2026-11-04 16:04 | D.0 and its review round, on the final tree: `gen:api`, `gen:tools`, `gen:components`; the touched files and the pins; the changed tests with the database address empty and on Python 3.12; `pnpm test:sim`; `pnpm test:core`; `build`; `pnpm prove`, offline, steps 1 to 10, with no `examples/`; `pnpm verify`, all sixteen stages | regenerated; 868 passed; 530 passed each way; 142 passed; 2865 passed, 1 skipped, 175 deselected; green; 83 of 83 checks, no call in the proof's spend table; every stage green | 459 s; 458 s; 269 s (the proof); 17 min 50 s (verify) | `1243e81` and D.0 |
| 2026-11-04 16:15 | The D.0 commit: `pnpm test:core` again after the guard in `test_prove_examples.py` names the engine-package form | 2865 passed, 1 skipped, 175 deselected | 7 min 45 s | `1243e81` and D.0 |
| 2026-11-04 16:35 | CI on `6f85338` (D.0), run 41865693107: `pnpm verify`, then `pnpm prove` | every stage green; every proof check holds | 13 min 27 s (verify); 3 min 23 s (the proof) | `6f85338` |
| 2026-11-04 17:05 | The stage D rounds: the mirror's own tests in core's environment; `conform mirror`; `pnpm prove`, offline, steps 1 to 10, with the mirror under `examples/engines/`; the record-reader against `pnpm prove --keep`'s service | 30 passed; 8 of 8 checks; 86 of 86 checks, `conform mirror` 8 of 8 in step 10 and `reflect` run from the Runs screen in the walk, no call in the proof's spend table; exit 0, the entry and the audit row naming `example-agent/0.1` | 3 s; 9 s; 297 s; about 30 s | `bde178d` and stage D |
| 2026-11-04 17:32 | The stage D gate: `pnpm verify`, all sixteen stages, with both examples in the tree and the mirror installed | every stage green: `test:core` 2865 passed, 1 skipped, 175 deselected; `test:sim` 142 passed; `test:lit` 10 passed; `smoke` 12 of 12 screens | 17 min 25 s | `bde178d` and stage D |
| 2026-11-04 17:44 | CI on `37e6bd0` (the stage D gate), run 41878467102: `pnpm verify`, then `pnpm prove` | every stage green; every proof check holds | 8 min 36 s (verify); 2 min 14 s (the proof) | `37e6bd0` |
| 2026-11-04 18:44 | E.0a: `pnpm test:core`, twice, the second on the final tree; `pnpm test:sim`; the new and changed tests with the database address empty and on Python 3.12; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:tools`, `check:secrets`; `build`; `smoke` with no key; `pnpm prove`, offline, steps 1 to 10 | 2876 passed, 1 skipped, 175 deselected each time; 142 passed; 64 passed each way; every check green; 12 of 12 screens; 86 of 86 checks, no call in the proof's spend table | 7 min 36 s (`test:core`); 7 min 29 s (`test:sim`); 275 s (the proof) | E.0a |
| 2026-11-04 19:48 | E.0b: `pnpm test:core` on the final tree; `pnpm test:sim`; the new and changed tests with the database address empty and on Python 3.12; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:tools`, `check:secrets`; `build`; `smoke` with no key; `pnpm prove --steps 5,9`, offline | 2889 passed, 1 skipped, 175 deselected; 142 passed; 124 passed each way; every check green; 12 of 12 screens; 45 of 45 checks, no call in the proof's spend table | 7 min 47 s (`test:core`); 7 min 30 s (`test:sim`); 139 s (the proof) | E.0b |
| 2026-11-04 20:28 | E.1: `pnpm test:core` on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`; `gen:api --check` and `gen:components --check`; `build`; `smoke` with no key; `pnpm prove --steps 9`, offline | 2889 passed, 1 skipped, 175 deselected; every check green, `check:state` 54 checks; the document and COMPONENTS.md as they were; 12 of 12 screens; 45 of 45 checks, no call in the proof's spend table | 7 min 34 s (`test:core`); 131 s (the proof) | E.1 |
| 2026-11-04 20:42 | E.2: `pnpm test:core` on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`; `gen:api --check` and `gen:components --check`; `build`, its bundle set beside the one the tree before the commit builds; `smoke` with no key | 2889 passed, 1 skipped, 175 deselected; every check green, `check:state` 54 checks; the document and COMPONENTS.md as they were; the bundle byte for byte the same; 12 of 12 screens | 7 min 35 s (`test:core`) | E.2 |
| 2026-11-04 21:10 | E.3: `pnpm test:core` on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:secrets`; `gen:api --check` and `gen:components --check`; `build`; `smoke` with no key, and the Postdoc screen read on a service with no key; `pnpm prove --steps 9`, offline | 2889 passed, 1 skipped, 175 deselected; every check green, `check:state` 54 checks; the document and COMPONENTS.md as they were; 12 of 12 screens, the Postdoc screen saying in words that the service holds no key; 45 of 45 checks, no call in the proof's spend table | 7 min 28 s (`test:core`); 134 s (the proof) | E.3 |
| 2026-11-04 21:54 | E.4: `pnpm test:core` on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:secrets`; `gen:api --check` and `gen:components --check`; `build`; `smoke` with no key; `pnpm prove --steps 3,9`, offline, its service kept for a scratch check of BioRepo's screens and a review | 2889 passed, 1 skipped, 175 deselected; every check green, `check:state` 56 checks; the document and COMPONENTS.md as they were; 12 of 12 screens; 54 of 54 checks, no call in the proof's spend table; each screen drew with no console error, and an accept from the review card reached the service | 7 min 48 s (`test:core`); 126 s (the proof) | E.4 |
| 2026-11-04 22:16 | E.5: `pnpm test:core` on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:secrets`; `gen:api --check` and `gen:components --check`; `build`; `smoke` with no key; `pnpm prove --steps 9`, offline; `pnpm prove --steps 3 --keep`, offline, its service kept for a scratch check of the ingest board, the reader and an extraction | 2889 passed, 1 skipped, 175 deselected; every check green, `check:state` 56 checks; the document and COMPONENTS.md as they were; 12 of 12 screens; 45 of 45 checks and 16 of 16, no call in either proof's spend table; each document's source named on both screens and the extraction's toast read, with no console error | 7 min 46 s (`test:core`); 127 s and 50 s (the proofs) | E.5 |
| 2026-11-04 22:52 | E.6: `pnpm test:core` on the final tree; `test_thermo.py`'s sim tests; the changed tests with the database address empty and on Python 3.12; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:secrets`; `build`; `smoke` with no key; `pnpm prove --steps 4 --keep`, offline, its service kept for a scratch check of the Properties panel and fermOS's four views | 2889 passed, 1 skipped, 175 deselected; 7 passed; 61 passed each way; every check green, `check:state` 56 checks; the document gains `ThermoPropsAnswer`, TOOLS.md and COMPONENTS.md as they were; 12 of 12 screens; 14 of 14 checks, no call in the proof's spend table; the panel asked thermosteam, drew the pair and read it back after a reload with no second ask, and each fermOS view drew with no console error | 6 min 49 s (`test:core`); 34 s (the sim tests); 72 s (the proof) | E.6 |
| 2026-11-04 23:16 | E.7: `pnpm test:core` on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild`, `check:secrets`; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `build`; `smoke` with no key; `pnpm prove --steps 4 --keep`, offline, its service kept for a scratch check of pureOS's screens | 2889 passed, 1 skipped, 175 deselected; every check green, `check:state` 56 checks, `check:guild` 126; the document, TOOLS.md and COMPONENTS.md as they were; 12 of 12 screens; 14 of 14 checks, no call in the proof's spend table; the index, the Builder on a saved train, a run's units and a kept train's copy, and the Train page each drew the units the service holds, with no console error | 6 min 52 s (`test:core`); 67 s (the proof) | E.7 |
| 2026-11-05 01:01 | E.8: `pnpm test:core` on the final tree; the changed tests and the tests of the service code they cover with the database address empty, on Python 3.13 and on 3.12; `test_propose.py`'s sim test; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:tools`, `check:guild`, `check:secrets`; `build`; `smoke` with no key; `pnpm prove --steps 9 --keep`, offline, its service kept for a scratch check of the catalogues screen's four tabs and the rail's reach | 2895 passed, 1 skipped, 175 deselected; 679 passed each way; 1 passed; every check green, `check:state` 57 checks, `check:guild` 126; the document, TOOLS.md and COMPONENTS.md as the service writes them; 13 of 13 screens; 47 of 47 checks, no call in the proof's spend table; 30 of 30, the two refusals it asked for the only 4xx answers and no 5xx | 4 min 34 s (`test:core`); 98 s (the proof) | E.8 |
| 2026-11-05 01:38 | E.9: `pnpm test:core` on the final tree; `test_prove_examples.py` with the database address empty and on Python 3.12; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild`, `check:secrets`; `gen:api --check` and `gen:components --check`; `build`; `smoke` with no key; `pnpm prove --steps 9`, offline, twice, the first with `--keep` for a scratch check of the screens that read the store's strains and products | 2895 passed, 1 skipped, 175 deselected; 9 passed each way; every check green, `check:state` 57 checks, `check:guild` 126; the document and COMPONENTS.md as they were; 13 of 13 screens; 48 of 48 checks each time, no call in the proof's spend table; 25 of 25, no 4xx and no 5xx | 4 min 31 s (`test:core`); 97 s and 89 s (the proof) | E.9 |
| 2026-11-05 02:06 | E.10: `pnpm test:core`, twice, the second on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild`, `check:secrets`; `gen:api --check`, `gen:tools --check` and `gen:components --check`; `build`; `smoke` with no key; `pnpm prove --steps 9 --keep`, offline, its service kept for a scratch check of the runbook pages | 2895 passed, 1 skipped, 175 deselected, each time; every check green, `check:state` 57 checks, `check:guild` 126; the document and TOOLS.md as they were, COMPONENTS.md with `src/engine/`'s 14 files; 13 of 13 screens; 48 of 48 checks, no call in the proof's spend table; 20 of 20, no 4xx and no 5xx | 4 min 45 s and 4 min 41 s (`test:core`); 97 s (the proof) | E.10 |
| 2026-11-05 02:36 | E.11: `pnpm test:core` on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild`, `test:reconcile`, `check:secrets`; `gen:api --check`, `gen:tools --check` and `gen:components --check`; `export:lock-fixtures`; `build`; `smoke` with no key; `pnpm prove --steps 5,9 --keep`, offline, its service kept for a scratch check of the runbook and deposition pages | 2895 passed, 1 skipped, 175 deselected; every check green, `check:state` 62 checks, `check:guild` 126, the reconciliation's 10; the document, TOOLS.md and COMPONENTS.md as they were; the lock digests byte for byte; 13 of 13 screens; 48 of 48 checks, no call in the proof's spend table; 33 of 33, no 4xx and no 5xx | 4 min 37 s (`test:core`); 99 s (the proof) | E.11 |
| 2026-11-05 03:28 | E.12a: `pnpm test:core` on the final tree; the new and changed tests with the tests of the service code they cover, with the database address empty, on Python 3.13 and on 3.12; `test_propose.py`'s sim test; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild`, `check:tools`, `check:secrets`; `build`; `smoke` with no key; `pnpm prove`, offline, steps 1 to 10 | 2926 passed, 1 skipped, 175 deselected; 484 passed each way; 1 passed; every check green, `check:state` 62 checks, `check:guild` 126; the document, TOOLS.md and COMPONENTS.md as the service writes them; 13 of 13 screens; 89 of 89 checks, no call in the proof's spend table | 4 min 47 s (`test:core`); 204 s (the proof) | E.12a |
| 2026-11-05 04:17 | E.12: `pnpm test:core` on the final tree; the changed tests with the tests of the code they cover, with the database address empty, on Python 3.13 and on 3.12; `export:competence-fixtures`; `gen:components` with each generated file's `--check`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild`, `check:tools`, `check:secrets`; `build`; `smoke` with no key; `pnpm prove --steps 2 --keep`, offline, its service kept for a scratch check of Guild, the protocols and Primer | 2928 passed, 1 skipped, 175 deselected; 128 passed each way; `competence.json` byte for byte, `competence-unrated.json` 96 statuses; every check green, `check:state` 62 checks, `check:guild` 140; the document and TOOLS.md as they were, COMPONENTS.md with `src/lib/protocols.ts`; 13 of 13 screens; 7 of 7 checks, no call in the proof's spend table; 35 of 35, no 4xx and no 5xx | 4 min 51 s (`test:core`); 34 s (the proof) | E.12 |
| 2026-11-05 04:51 | E.13: `pnpm test:core`, twice, the second on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild` (its new check also run on the store before the fix), `check:secrets`; `gen:api --check`, `gen:tools --check` and `gen:components --check`; `build`, its bundle with the names moved set beside the one the tree before the commit builds; `smoke` with no key; `pnpm prove --steps 2 --keep`, offline, each time on a fresh database, its service kept for a scratch check of Settings and the clear | 2928 passed, 1 skipped, 175 deselected; every check green, `check:state` 62 checks, `check:guild` 141 (the new check failing on the store before the fix); byte for byte; the document, TOOLS.md and COMPONENTS.md as they were; 13 of 13 screens; 7 of 7 checks each, no call in the proof's spend table; 22 of 24 before the fix, 24 of 24 after it, and 25 of 25 on the final tree, no 5xx | 4 min 56 s (`test:core`); 32 s (the proof) | E.13 |
| 2026-11-05 05:10 | E.14: `pnpm test:core`, twice, the second on the final tree; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild`, `test:reconcile`, `check:secrets`; `gen:api --check`, `gen:tools --check` and `gen:components --check`; `build`, its bundle set beside the one the tree before the commit builds; `smoke` with no key | 2928 passed, 1 skipped, 175 deselected; every check green, `check:state` 62 checks, `check:guild` 141, the reconciliation's 10; the document, TOOLS.md and COMPONENTS.md as they were; byte for byte; 13 of 13 screens | 4 min 47 s (`test:core`) | E.14 |
| 2026-11-05 05:55 | E.15: `pnpm verify`, all sixteen stages; `pnpm build && pnpm prove`, offline, steps 1 to 10; `pnpm test:core` again on the final tree; the changed tests with the database address empty and on Python 3.12; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `typecheck`, `check:plan` (each of its checks also made to fail on a scratch copy of the two files it reads), `check:state`, `check:figures`, `check:guild`, `test:reconcile`, `check:secrets`; `build`, its bundle set beside the one the tree before the commit builds; `smoke` with no key; `grep -rn "data/types" src scripts` | every stage green: `test:core` 2928 passed, 1 skipped, 175 deselected, `test:sim` 142 passed, `test:lit` 10 passed, `smoke` 13 of 13 screens; 89 of 89 checks, the catalogue screen in the walk, no call in the proof's spend table; the same counts; 13 passed each way; the document and `src/api/types.gen.ts` with their descriptions regenerated, TOOLS.md as it was, COMPONENTS.md with `src/data/`'s nine files; every check green, `check:plan` 9 classes in one order, `check:state` 62 checks, `check:guild` 141, the reconciliation's 10; byte for byte; 13 of 13 screens; nothing found | 11 min 39 s (verify); 4 min 51 s (`test:core`); 5 min 13 s (`test:sim`); 199 s (the proof) | E.15 |
| 2026-11-05 06:50 | E.16: `pnpm test:core`, twice, the second on the final tree; the changed tests with the database address empty and on Python 3.12; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `check:tools`, `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:secrets`, `test_guidance.py`; `build`, its bundle set beside E.15's; `smoke` with no key; `pnpm prove --steps 3 --keep`, offline, its service kept for the stage D record-reader and a filtered read of the audit | 2940 passed, 1 skipped, 175 deselected, twice; 113 passed each way; each generated file as the code writes it; every check green, `check:state` 62 checks; the bundle byte for byte E.15's; 13 of 13 screens; 16 of 16 checks, the record-reader exiting 0 | 5 min 13 s (`test:core`); 39 s (the proof) | E.16 |
| 2026-11-05 07:04 | CI on `dc02f20` (E.16), run 41982676788: `pnpm verify`, then `pnpm prove` | every stage green; every proof check holds | 13 min 9 s (verify); 3 min 25 s (the proof) | `dc02f20` |
| 2026-11-05 08:49 | The stage E gate (E.gate): the changed tests with the tests of the code they cover, with the database address empty, on Python 3.13 and on 3.12; `pnpm test:sim`; `pnpm test:core`; `gen:api`, `gen:tools` and `gen:components`; `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:guild`, `test:reconcile`, `check:secrets`; `build`; `pnpm smoke` with no key; `pnpm prove --steps 9` and `pnpm prove`, offline; `pnpm verify`, all sixteen stages | 579 passed each way; 142 passed; 2946 passed, 1 skipped, 175 deselected; the document, the types and `docs/TOOLS.md` regenerated, `COMPONENTS.md` as it was; every check green, `check:state` 66 checks, `check:guild` 146; 20 of 20 screens, Postdoc's saying it runs with no key; 52 of 52 and 93 of 93 checks, the catalogue screen and the five new walk steps in the walk, no call in the proof's spend table; every stage green (`test:core` 2946 passed, `test:sim` 142, `test:lit` 10, `smoke` 20 of 20) | 5 min 29 s (sim); 5 min 25 s (core); 218 s (the proof); 13 min 7 s (verify) | `dc02f20` and E.gate |
| 2026-11-05 09:55 | F.1: `pnpm test:core` on the final tree, the report's stage F section and this file's record of F.0 and F.1 in it | 2946 passed, 1 skipped, 175 deselected | 5 min 20 s | F.1 |
| 2026-11-08 05:42 | The landing, w1's five picks (E.17, E.18, E.19, E.debts, E.20) on `2ed7dac`: after each, its changed tests with the tests of the code they cover, with the database address empty, on Python 3.13 and on 3.12, `gen:api`, `gen:tools` and `gen:components` with each `--check`, and `typecheck`; `check:state` after E.19; then `pnpm test:core` | 158, 143, 428 and 160 passed each way (E.19 changed no Python); every check green; 2987 passed, 1 skipped, 175 deselected | 4 min 57 s | `448adbb` (E.20) |
| 2026-11-08 05:53 | The landing, w2's four picks (F.5.1 to F.5.4): after each, the test files it changed with the test files of the code it changed (each that calls `llm.call` or the kit, and `test_boundaries.py` for the package map), with the database address empty, on Python 3.13 and on 3.12, and `gen:api`, `gen:tools` and `gen:components` with each `--check` (`typecheck` after F.5.2, whose generated types moved); then `pnpm test:core` | 297, 171, 177 and 253 passed each way; every check green; 3037 passed, 1 skipped, 175 deselected | 5 min 5 s | `adb9c8d` (F.5.4) |
| 2026-11-08 05:55 | The landing's final tree: `gen:api`, `gen:tools` and `gen:components` with each `--check`; `check:secrets`, `check:plan`, `check:state` (86 checks), `check:figures`, `check:guild` (146 checks), `check:tools`; `pnpm test:sim`; `pnpm test:lit`; `pnpm build`; `pnpm smoke` with no key, on its own service at 127.0.0.1:43339, stopped after; `pnpm prove`, offline, steps 1 to 10 | each file as the code writes it; every check green; 142 passed, 3071 deselected; 10 passed, 3203 deselected; built; 20 of 20 screens; 99 of 99 checks, the sci-rag server's graph tools in step 3 and no call in the proof's spend table | 4 min 55 s (sim); 7 s (lit); 18 s (build); 36 s (smoke); 195 s (the proof) | `adb9c8d` |
| 2026-11-08 07:18 | The landing review: the changed tests with the tests of the code and the docs they read, with the database address empty, on Python 3.13 and on 3.12; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `check:tools`, `check:secrets`, `typecheck`, `pnpm build`; `pnpm test:lit`; `pnpm prove --steps 3`, offline; `pnpm test:core` | 281 passed each way; each file as the code writes it; every check green; built; 10 passed, 3212 deselected; 19 of 19 checks, no model call; 3046 passed, 1 skipped, 175 deselected | 5 min 4 s (core); 40 s (the proof) | the landing review |
| 2026-11-08 08:26 | F.5's offline part: `pnpm build`; the service restarted and `pnpm ready` (no probe); `pnpm lit:graph --project ethanol --dry-run` and `pnpm lit:report --project ethanol --configs interactive,vector_only,keyword_only --render`, no model call; `pnpm test:lit`; `pnpm test:core` | ready; the dry run 92 batches; the run 130 questions, 0 calls; 10 passed; 3064 passed, 1 skipped, 175 deselected | 2.8 s; 8.5 s; 8 s; 5 min 10 s | F.5 |
| 2026-11-08 10:21 | H.0's first list (the screens the sweep walked): `pnpm test:core`; `pnpm test:sim`; the touched test files with the database address empty, on Python 3.12; `gen:api`, `gen:tools` and `gen:components` with `--check`; `check:licences`, `check:secrets`, `check:plan`, `check:figures`, `check:guild`, `check:state`, `check:tools`, `typecheck`; `pnpm build` and `pnpm smoke` on a port of its own | 3066 passed, 1 skipped, 175 deselected; 142 passed; 205 passed after the last edit; each file as the code writes it; every check green; 20 of 20 screens | 5 min 23 s (`test:core`, ended 10:16); 4 min 47 s (`test:sim`, ended 10:21) | `a024dfc` |
| 2026-11-08 10:55 | H.0's second list (the screens, the notes a basis hashes, the remnants, the records): `pnpm test:core`; `pnpm test:sim`; `pnpm test:lit`; the touched test files and their neighbours with the database address empty, on Python 3.12; `gen:api`, `gen:tools` and `gen:components` with `--check`; `typecheck`, `check:state`, `check:figures`, `check:guild`, `check:plan`, `check:tools`, `check:secrets`; `pnpm build` and `pnpm smoke` on a port and a database of its own | 3057 passed, 1 skipped, 175 deselected (`validate_claims`' 20 tests gave way to eleven on `validate_plan`); 142 passed; 10 passed; 484 passed; each file as the code writes it; every check green; 20 of 20 screens | 5 min 34 s (`test:core`, ended 10:50); 5 min 6 s (`test:sim`, ended 10:55); 10 s (`test:lit`) | `9b6e5c7` |
| 2026-11-08 11:10 | Stage H: `pnpm verify`, all sixteen stages, on `9b6e5c7` (H.0's last commit) | every stage green: `check:secrets`; `typecheck`; `gen:api --check` and `gen:components --check`; `check:plan`; `test:core` 3057 passed, 1 skipped, 175 deselected (5 min 22 s); `test:sim` 142 passed, 3091 deselected (4 min 56 s); `test:lit` 10 passed (10 s); `check:licences`; `check:tools`; `check:guild` 146 checks; `check:state` 95 checks; `check:figures` 13 checks; `build`; `smoke` 20 of 20 screens with no model key; `test:reconcile` | 12 min 11 s | `9b6e5c7` |
| 2026-11-08 11:14 | Stage H: `pnpm build && pnpm prove`, offline, steps 1 to 10, on the same tree | built in 4.7 s; 99 of 99 checks, `conform` 8 of 8 on `biosteam`, `kinetics`, `mirror` and `train` in step 10, the proof's spend table 0 calls | 19 s (the build); 203 s (the proof) | `9b6e5c7` |
| 2026-11-08 11:21 | Stage H's records on the final tree: `pnpm test:core`; `test_guidance.py` with the database address empty, on Python 3.12 and on 3.13 | 3057 passed, 1 skipped, 175 deselected; 6 passed each way | 5 min 59 s; 2 s | stage H |
| 2026-11-08 11:50 | The close review's fixes: `test_host.py` and `test_guidance.py` with the database address empty, on Python 3.12 and on 3.13; ShellCheck 0.11.0 and `bash -n` on the four host scripts; `pnpm test:core` | 58 passed each way; clean; 3060 passed, 1 skipped, 175 deselected | 3 s; 5 min 12 s | stage H, the close review |

## Spend (alpha 2.1)

From the spend tables (`spend.state()`; a proof reads its own before its database is dropped). The day's
cap for this work is 150 USD and an ask's 6 USD (`core/.env`).

| Stage | Calls | USD | What |
|---|---|---|---|
| A | 10 | 0.6601 | `pnpm prove --live` on the Opus routes |
| B | 203 | 17.6463 | extraction over 22 documents (4.53) and nine again after the anchoring fixes (1.80); the twelve questions asked three times (4.54, 5.01, and 1.60 for the three asked a third time). Those sums are what each answer reported of itself; the table of `openferment_dev` holds 0.17 more |
| C | 72 | 2.1006 | the three route tables until the account's usage limit refused every call (eight answers kept, five judged); the judge's calls among them |

## Spend (alpha 2.2)

From the spend tables of every database on this server, read with SELECT alone at the close (8
November: `openferment_dev`, `openferment_dev_alpha21`, and `check_tools_26521_a78452`, a database
`check:tools` left on the server at 04:51 that day, its spend table empty, which the close review
dropped with `python -m openferment_core.migrations drop`; `sci_rag_test`, the kit's own, holds no
spend table); a proof reads its own before its database is dropped. The day's cap for this work is 150
USD and an ask's 8 USD (`core/.env`, the prompt's §4).

| Stage | Calls | USD | What |
|---|---|---|---|
| A | 1 | 0.000004 | `pnpm ready --probe`: one call on the index route (`claude-haiku-5-5`, 18 tokens in, 4 out) |
| B | 0 | 0 | none: the contract, the registry and the conformance checks make no model call |
| C | 0 | 0 | none: every step of stage C and its gate ran offline with no key; each proof's spend table held no call |
| D | 0 | 0 | none: the pre-read, the fixes, both strangers' rounds and every proof ran offline with no key; the record-reader's run against the kept proof made no model call |
| E | 0 | 0 | none: every step of stage E, its gate and E.17 to E.20 ran offline with no key; each proof's spend table held no call |
| F | 348 | 39.723802 | F.0 to F.2, over two days, each day settled over every database (`openferment_dev`, `openferment_dev_alpha21`); F.5's commands and its offline part made no call. 5 November, 140 calls and 14.439322 settled: F.0's `pnpm ready --probe`, one call on the index route (`claude-haiku-5-5`), 0.000004, its row now in `openferment_dev_alpha21`; F.1's extraction of the 22 documents on the `extract` route, 31 calls and 5.377950 (22 answers, 13 by `claude-opus-5-5` and 9 by `claude-sonnet-5-5` after Opus declined in `bio`, and the nine declines, 1.216816); the haiku table, 94 calls and 4.376768 (answers on `claude-haiku-5-5` 0.2780, judgements on `claude-opus-5-5` at 16,000 4.0988); its second judge pass at 32,000, 14 calls and 4.684600. 8 November, 208 calls and 25.284480 settled: the sonnet table, 75 calls and 6.920110 (answers on `claude-sonnet-5-5` 2.4974, judgements on `claude-opus-5-5` 4.4227); the opus-high table, 92 calls and 11.903559 (answers on `claude-opus-5-5` 6.5359, judgements 5.3676); the opus-max table, 41 calls and 6.460811 (four answers on `claude-opus-5-5` 5.5457 and their judgements 0.2421, eq-eth-05's first asking cut off by the session's two-hour limit 0.3909 with no run kept, its second refused by the account 0.2822); one hold of 0.982072 left by the stopped runner settles nothing and expires. Each day against the 150 USD cap |
| G | 0 | 0 | none: the runbook and the host scripts held to the tree with no model call |
| H | 0 | 0 | none: H.0's sweep and its fixes, `pnpm verify`, `pnpm prove` offline and the records made no model call; the proof's spend table held none |
| Alpha 2.2 | 349 | 39.723806 | stages A to H: A's probe on 2 November, F's 348 calls on 5 and 8 November; the hold of 0.982072 is outside the sum |

## Decisions

| ADR | Decision | Status |
|---|---|---|
| [000](decisions/ADR-000-fresh-slate.md) | Fresh slate; every old rule classified | accepted |
| [001](decisions/ADR-001-postgresql.md) | PostgreSQL with pgvector is the one database | accepted, stage 2 |
| [002](decisions/ADR-002-sci-rag-kit.md) | Sci RAG Kit as an in-process library | accepted, stage 3 (Implementation 8: the MCP server over stdio; alpha 2.2 F.5, Implementation F: the concept graph a project builds and reads, the graph tools on the `sci-rag` server, the report's project lanes, and from the landing review a batch within one document and an edge named in its own passage) |
| [003](decisions/ADR-003-sff.md) | SFF is the flowsheet record | accepted, stage 4 |
| [004](decisions/ADR-004-biosteam-adapter.md) | BioSTEAM through one adapter | accepted, stage 4 |
| [005](decisions/ADR-005-projects.md) | Projects replace programs | accepted |
| [006](decisions/ADR-006-quantities-and-estimates.md) | Typed quantities with origins replace Rule 1 | accepted, stages 4 and 6 (alpha 2.2 E.15: the browser's quantity types are generated, a note added at E.gate; E.17: a reading chosen on a Proforma scenario's parameter panel, kept in its own value and unit; E.debts: who chose a reading, kept on its row) |
| [007](decisions/ADR-007-schema-source.md) | Types generated from OpenAPI | accepted, stage 7 (alpha 2.2 E.0a: a schema the service only writes lists every property as required; E.0b: the rows a project keeps of its pages read as their models and served as kept; E.1: each lib names the generated schemas it answers, and its screens and components read them there; E.3: Postdoc's lib, and the one seam where a draft becomes the store's runbook until E.11; E.4: the review family in lib/review.ts, a record's field held to the ontology as it enters the store; E.6: fermOS's lib, and thermosteam's POST answering its artifact beside what it holds; E.7: pureOS's lib, and a train's units read as a request may leave them; E.8: the catalogues' lib born on the generated types, and an entry a keep sends read as a request may leave it; E.9: geneOS's lib, and a strain and a product read as the project's catalogue entries; E.11: the runbook family and the bench's record in lib/studies.ts, a runbook read as a row served as kept may leave it, and the draft's seam gone; E.12: Guild's, the checks' and Practice's libs and a new lib/protocols.ts, a skill and a lesson read as the project's catalogue entries, a protocol read as served whole, and a skill kept with no policy rated by nobody on both sides; E.14: the last readers, and the browser's own types with their owners, so no file imports src/data/types.ts; E.15: src/data/types.ts deleted and check:plan's pairs retired with it, every reader held to the service by `gen:api --check` and `typecheck`; E.gate: a decision's refusal rule generated as the eight rules, each hand copy of a generated request or union derived from its schema, a Proforma run's view built from its typed answer, and an artifact's output read per tool, a recorded departure) |
| [008](decisions/ADR-008-postdoc-memory-routing.md) | Postdoc memory on the server; model routes | accepted, stage 6 (alpha 2.2 E.16: the agent builder's interface points, Implementation 13: one rule for a BioRepo record, a write's answer naming its audit rows, the audit read by what a write was and served with its null fields left out; F.2a, Implementation 14: the judge pass reads core/.env as a run does and stops in words where no judge answers, and a model's write carries the plan route's effort; F.2c, Implementation 15: the judge's room set by measurement; F.2g, Implementation 16: the plan's room by the route's effort; F.2e and F.2f, Implementation 17: the defaults the comparison set; F.5, Implementation 18: a run's own count and the kit's room, its room at max the judge's since the landing review) |
| [009](decisions/ADR-009-ui.md) | The UI is kept and wired | accepted, stage 7 (alpha 2.2 E.15: the hand-kept types and check:plan's pairs retired, a note added at E.gate) |
| [010](decisions/ADR-010-deletions.md) | Deletions | accepted, stage 1 (alpha 2.2 E.10: the enumeration funnel deleted, both its pieces standing at `alpha-1.0`) |
| [011](decisions/ADR-011-guards.md) | Guards and verify stages | accepted, stages 1 and 8 (Implementation 8: sixteen stages; alpha 2.2 E.15: `check:plan` keeps the provenance ranking alone, its pairs retired with `src/data/types.ts`, and verify keeps its sixteen stages) |
| [012](decisions/ADR-012-licence-undecided.md) | Licence undecided | open (owner) |
| [013](decisions/ADR-013-cornstover-package-test.md) | The corn stover plant's two values its package's own test fails, held to the package's measurement | accepted, stage 5 |
| [014](decisions/ADR-014-durable-write-queue.md) | The Durable snapshot keeps the writes the service has not acknowledged | accepted, stage 7 (a departure; alpha 2.2 E.12: the snapshot keeps no lesson, a lesson's passing standing on the ledger; E.19: the screens say the service keeps a project's rows, and `check:state` holds their words to this record) |
| [015](decisions/ADR-015-engine-contract.md) | Engines register through Python entry points, behind one contract | accepted, alpha 2.2 stage B (E.18: a thing may title its configurations, `EngineThing.configurationTitles`, words alone in no run's basis) |
| [016](decisions/ADR-016-bench-readings-alone.md) | The bench records a locked runbook's readings alone | accepted, alpha 2.2 stage C (a departure from §11.5; alpha 2.2 E.12a: its first revisit condition met by ADR-017, the readings-alone mode standing beside a protocol's steps) |
| [017](decisions/ADR-017-project-protocols.md) | A project keeps its protocols | accepted, alpha 2.2 E.12a (ADR-016's revisit condition; the owner may reverse it) |
| [018](decisions/ADR-018-lesson-body.md) | A lesson keeps its body in the lesson catalogue | accepted, alpha 2.2 E.12a (the owner may reverse it) |

## Departures from the execution prompt

| Where | Departure | Why |
|---|---|---|
| alpha 2.2 D1, C.1 | D1's amendment, the dispatch: every pin's output hash is computed under one fixed dispatch (`OPENBLAS_CORETYPE=Haswell`, `OPENBLAS_NUM_THREADS=1`, `NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"`), in a process `test_engine_pins.py` starts with them, and each id in the suite's own process as well; a host that is not x86-64 with AVX2 and FMA3 skips the pins, saying why (the fit's id rests on readings numpy computes in the test). Four literals were captured again from ed33c02's code under the fixed dispatch, on Python 3.13.17 and 3.12.3 alike: `fermos.simulation chemostat_v1` `ea77840641c03bb5…` (first `0cd4343efc7cbfe5…`), `kinetic_fit` `905045fddf738d41…` (first `1a00f394d4c7a1fa…`), `growth_forecast` `5cb631e5e0ae170e…` (first `dc1cf3ef52dd2cbc…`) and the forecast with a changed start `859f488203c5439f…` (first `5d29ef33c8831f7a…`); every id and the other twelve hashes read as first captured. The step counts as green once a CI run passes | The first capture was this AVX-512 Xeon's own dispatch (numpy's X86_V4 loops, OpenBLAS's SkylakeX kernels). The review measured that OpenBLAS's Haswell or Zen kernels move the chemostat's hash, and numpy's dispatch moves the fit's and the forecasts'; CI's runners include AVX2 hosts. The fixed dispatch is the one such a host takes of itself |
| alpha 2.2 D3, C.1 | `study.comparison` reads its version from the runs it compares: `study comparison 1` for library runs alone, every row, id and pin as before, and `study comparison 2` for a comparison that holds a run of another engine, which reads outputs.values, names a contract run's thing, and gives a library run the library's default only for a value its plant declares (every other such cell null) | Before C.1 such a comparison set no row of a contract run's outputs and gave every run that set a value none a `library-default` cell; reading the new outputs under the old version would replay a kept comparison differently with nothing to say why. Version 2 makes the replay name the change, and the nightly reads a version-1 artifact over such a run as stale. Before C.1 only `biosteam` registered through an entry point, so test databases alone could hold one |
| alpha 2.2 §6.1, C.2 | `kinetics` declares `worker` None and `heavy` (): fermOS integrates with SciPy in the service's process, as it always has, and a vessel design runs on BioSTEAM in the Proforma worker; `GET /api/engines` lists the worker's status as `none`, `pnpm ready` names the Proforma worker for a vessel design, and a 503 from an engine route names the worker the computation called | §6.1 has every engine name its worker module. fermOS's integrators are SciPy alone (`test_workers.py` allows it in `kinetics.py` and `fermos.py`) and read the store's ceiling artifacts; moving them into a worker of their own would move every fermOS pin |
| alpha 2.2 §6.1, C.2 | A parameter with no default reads `value` and `origin` null, its `sourceRule` naming `assumption` (`EngineParameter`); conformance check 2 reads "every default carries an origin, and a parameter with none says a run sets it"; `run_engine` refuses in words, keeping nothing, a contract engine's run that leaves one unset | §6.1 has every parameter carry an origin. A kinetics family's rates and start values have no default, and a default typed in would be science in the code (§1 item 7) |
| alpha 2.2 D3, C.2 | `growth_forecast` is a write tool: its kept forecast is a run of the kinetics engine in its caller's name, so at the HTTP door (`POST /api/tools/growth_forecast`) it names its caller with `?by=`, and a call naming nobody is a 422 in words | D3 has every door make one row, created by who asked |
| alpha 2.2 D4, C.2 | `runs.check_inputs` reads whether a parameter takes a number from `takes_number`: a parameter with choices takes one of them, a default of words in no unit takes words, and every other parameter takes a number, one with no default and one whose default is a convention's words in a unit (`ki_substrate` off, in g L⁻¹) among them | The kinetics families state a term left off as words in the parameter's unit, which a run replaces with a number; the rule before C.2 read a number from the default alone |
| alpha 2.2 D4, C.2 | Conformance check 3 keys the run with its seed (`artifact_id(tool, toolVersion, inputs, seed)`) | A forecast's computation takes a seed, and its id joins it; check 3 keyed the run without the seed, and so held a seeded run to another id |
| alpha 2.2 D4, C.2 | kinetics' configurations: `forecast` takes a kept logistic_v0 fit, `vessel` a kept batch_v1 simulation, a logistic fit or a forecast, each thing listed while the project holds one, read afresh in the request's project by the artifact store's tool column. Conformance, in a fresh project, checks the three families; `core/tests/test_engines.py` holds the forecast's and the vessel's parameters and runs | The plan left the things' configurations to the step; a thing run on the project's own artifacts has none to list in an empty project |
| alpha 2.2 D4, C.2 | `version()` reads numpy and scipy from the modules and biosteam and thermosteam from their installed metadata, the versions a vessel design's tool version names, and starts no worker. Each row names what its own thing ran on: numpy and scipy for a family's simulation and a forecast; biosteam, thermosteam and biorefineries for a vessel design | The brief asked for BioSTEAM's version as the simulator reports it, which needs the Proforma worker warm: a listing or a `pnpm ready` row would then start BioSTEAM. A family's simulation and a forecast run on numpy and SciPy alone, and their rows name those |
| alpha 2.2 D1, C.2 | The forecast that sets a start value moved its id from ed33c02's `611bd4b34eed98fd` to `80ef18a4b9924dba` under D1's amendment: its typed start value writes the day it was set and the unit of the fitted run's series in the basis. Its output hash `859f4882…` holds, and every other pin reads as captured | The amendment; the unit lets a run's page and `GET /api/runs/{id}` read the start value in the unit it was typed in |
| alpha 2.2 §6.1, C.3 | A default's origin is one of five (`EngineParameter`): a `library-default` and a `convention`, and for a thing the project holds a `record` (its `ref` the records, its `sourceRule` naming the field), an `artifact` (its `ref` the run, simulation or design) or a `person-assumption` (its `by` the person). A parameter with no default takes a run's value: a run sets it, the engine binds it, or the thing fills it itself when a run leaves it unset, which its `note` then says with the reason (the train engine's: a value the unit's class decides at run time, a component the inlet does not carry, a split left to the class). Conformance check 2 reads "every default carries an origin naming what it rests on (a library-default, a record or an artifact its ref, a convention its note, a person's assumption its by), and a parameter with none takes a run's value" | A train's values resolve from the project's records, its inlet's run and what a person typed into the train; §6.1's two origins name a package's default and a software setting. 27 of a stand-in train's 55 parameters have no default and a run computes with them unset (the C.3 review), so the rule names the third case |
| alpha 2.2 D5, C.3 | An engine whose things are all a project's own declares `things_are`, in words, which `GET /api/engines` lists as `thingsAre`, beside `rests_on`, the rows of the project its things rest on by table (the train engine's: every train, each artifact a train's inlet reads with its run's row, the scenarios a run-stream inlet names, the evidence pool whole and the project's strains), required beside it, and `unready`, why a thing cannot be checked as it stands; an engine that declares `things_are` with no `rests_on` loads and runs, conformance refuses it in words and `pnpm ready` says them in its row. `conform <name> --project <id>` reads those rows from the configured database, writing nothing there, copies them under the same ids into a project of the same id on a database of the checks' own (a runs row of the engine being checked is left out of the copy), checks there each thing the copy holds that can run with the values `--inputs` sets on every one, checks 3, 4, 5 and 8 on every one, and drops that database however the checks end (a check that raises, Ctrl-C, `SIGTERM`, `SIGHUP`; a process killed outright leaves it, holding the migrated schema and no row, and `pnpm prove` asks a run past its time to end before it kills it); each thing left out (a saved draft, a train whose values wait for a source, a train whose run is refused before it computes, a value naming a place the train lacks among them) is listed in check 3's words, numbered, with its own. The verdict in the configured database's `engine_checks` is the one row the command writes where it read; the row is the machine's, so the verdict of a project's things keeps counts in its words and names no project, train or run, and the command's table gives each thing's words. A project the database lacks, and one that holds no thing that can run, are refused in words (exit 2) with no verdict kept and the engine's last one standing, where D5's amendment at C.3 has the check fail; the command with no `--project` is refused too (exit 2). The production database `openferment` is read as any other, and `pnpm ready` names the command there. With every thing checked, check 8's model sets one parameter of each at its own default as its estimate on that thing; with no values set elsewhere, it sets the first parameter whose source rule takes a run's value (`assumption`), else the first with a default | A database made for the checks holds no train, and a person's project is theirs. The C.3 review measured the first cut, which ran every train the project held in the project itself: a person's earlier run of the train answered check 3 and failed check 8 (its created_by the person's), the checks' rows then answered the person's next request, and a saved draft or a train that waits failed checks 2 and 8. C.3's second cut ran one train in the project on a basis of its own and refused the production database, so the live host could check none of its trains; D5's amendment at C.3 has conformance read a project and check a copy of it (C.3b). A project with nothing that runs says nothing of the engine, so a failing verdict kept for it would have `pnpm ready` warn of an engine that holds; the refusal says why and keeps the last verdict. The machine's row is read in every project (`GET /api/engines`), and C.3b's review found it naming one project, its trains and the left-out trains' refusals. A from-run inlet's first values carry the rule `artifact` (read from the inlet's run), which pureOS lets no run's value set |
| alpha 2.2 D5, C.3 | The proof's train is the tail of the from-run train on step 4's corn stover run: pureOS's from-run reads the units the product passes through whose classes are catalogue types, at their classes' own defaults; its first units are taken out while the check refuses its inlet as one the chemical set cannot build (since C.7 the read train starts on the broth, which carries the plant's own chemicals), the units whose values wait (the check's places) are then taken out with every unit before them, and the inlet is the run's own stream entering the first unit kept (`scripts/prove.py`, `make_train`). At these pins the tail is the four units from T701 on, none of them a separation, each passing the whole of the product on (a debt below) | D5 has the proof make a train on the reference run's product stream. The read train's first units wait on values their classes require and no default gives (D402 and D403 six each; H402, U401 and H403 one each); the tail runs on its classes' own values, with nothing the proof types |
| alpha 2.2 D5, C.3 | Every train run keeps `sffRefused`. The schema the toolkit ships at `e236e32` requires every file's `metadata.TEA_year` (`sff_schema.json`, the metadata's `required`), which the exporter reads from the system's TEA (`metadata['TEA_year'] = tea.duration[0]`, `export/_export.py`), its one read of a TEA; a train run computes no TEA and no TEA year. The Proforma worker's `sff_export` reads that requirement from the toolkit's schema file and, while it stands, refuses a train's file in those words before it builds anything (`a train carries no TEA, and the SFF schema the toolkit ships (0.2.4) requires every file's metadata.TEA_year, …`); once the schema leaves the year to the file, it rebuilds and simulates the train from the run's basis and hands it to the toolkit, whose own words it quotes. Check 5 holds by the words | D5 has a train's run write its file once `sff_export` learns the train. It has learned it; the schema the toolkit ships holds a file to a TEA year a train run never computed. The first cut rebuilt and simulated every train a second time for a file the toolkit always refused, and showed a person its AttributeError (the C.3 review; a debt below) |
| alpha 2.2 D5, C.3 | A train run replays exactly: `pureos.train_run` registers no tolerance and the train engine's things state rtol 0, atol 0 (`train_spec.replay_precision`), the library run's last-kept-digit rule read for a run that rounds nothing | D5 asked for the library's last-kept-digit precision. A library run rounds its outputs to its `precision` input's digits; a train run keeps every digit BioSTEAM gives. The C.3 review measured train replays identical at 0ad02c9 and in the working tree, in one worker, after another train ran; a rtol of 1e-9 would pass a train run whose last digits move, every one kept before C.3 among them |
| alpha 2.2 D5, C.3 | The train engine's run checks and converts its values at pureOS's own door (`train_spec.converted`), with `runs.check_inputs` left out: the engine's route and `POST /api/pureos/train/run` and `/check` refuse every bad value at once, by place, with the train's own refusals, in one set of words; a key set twice is refused there too (`F1.V is set twice`) | The first cut checked the engine's values with `runs.check_inputs` first, which says the first key it cannot take and stops, while pureOS's door said every refusal by place; pureOS's door laid a key given twice key by key, the last value kept and no word said (the C.3 review) |
| alpha 2.2 D1 and D6, C.4 | The Proforma pin moved its id under D1's amendment at C.4, from ed33c02's `7fd5c088e90f6689` to `87a47693d171d91d`; its output hash `865d88ab…` holds. The pin was captured through the older `assumptions` field, whose basis carried no line saying where its values came from; every run a person made through the parameter panel sent overrides and carried the convention `assumptions read from: overrides`. From C.4 a run that sets a value, an input's or a composite's Finance value, writes that line word for word (`proforma.values_read`), so the panel's ids hold: measured on the stand-in evaluator through b6a85d0's overrides and the working tree's inputs, `52e1bc2d2c215e81` (a held scenario), `b1931d595489ef2e` (with titre over the records), `66845418720c7794` (one made here), `5787b339a1c448e9` and `f32cbb91635cb3d5` (`custom_train_v1`, the second with a Finance value) are each the same id with the same output hash. The pin's values gain the line and the id the panel's overrides gave the same values at b6a85d0; the pin names both ids, and the basis the older field built still gives ed33c02's. A run sent through the older field before C.4, kept by a client that sent it, is kept afresh under the panel's id when asked again, its artifact standing | The plan's D6 amendment at C.4: a run a person makes through the panel keeps the artifact id it had. The older field retired at C.4 (the brief), so no request can make its basis again; the pin moves once, with its output hash held, as C.2's forecast pin did |
| alpha 2.2 D6, C.4 (ADR-006) | A model's estimate in a Proforma run bases as the model's estimate (`basis.estimate_source`: kind `model-estimate`, the model's id as `by`, `estimated on <day>`), where the binding based it as a person's assumption naming the model (`assumption_source`: kind `assumption`); the input's sensitivity reads `sourceKind` `model-estimate`, so the output moves with the id. Measured on the stand-in evaluator, a held scenario with one estimated input: `c44e394da9e9eaa8` at b6a85d0, `ea9fa993c41e5cf8` now, the output hash moving with it. A model's id on two lines is refused in words at Proforma's door, a blank one by the request's own origin. Every kept artifact replays as it was | The plan's D6 amendment at C.4 allows this one move: ADR-006 names an estimate as an estimate, and the run is `assumed` either way (ADR-006, Implementation, alpha 2.2 C.4) |
| alpha 2.2 D6, C.4 | `custom_train_v1` is a thing of `biosteam` while the project keeps a scenario of it whose parts stand (`composite.parts_of`), one configuration `vessel <id>, train run <id>` for each pair the project's scenarios of it name, with no default; a run naming none is refused in words; every composite row, at the engine's door and at `POST /api/proforma/run` alike, carries its parts as its configuration (`proforma.parts_configuration`) | The contract's run names a composite's parts only through its configuration, and one configuration keeps both doors on one row; D6 named the flowsheet among biosteam's things, and a composite runs nothing until a scenario names its parts |
| alpha 2.2 D3 and D6, C.4 | A Proforma run's `outputs.values` hold the base case's price, solved at its TEA's IRR, named as a library run names its own (`price.solvedPrice`), and the five quantiles of the price over its samples (`quantiles.p5` to `quantiles.p95`), each in the artifact's price unit and on its TEA's basis; a comparison sets a value another engine's run names as a library run names its own (`price.<key>`, `outputs.<key>`) on that output's row, so a Proforma run's price and a library run's meet on one row with its change (`studies/comparisons._row_of`) | The brief asked for the base price in its price basis; the quantiles are the run's price over its samples. The first cut named it `basePrice`, and the screens' review found a comparison of the two runs sharing no row and its figure saying nothing varies |
| alpha 2.2 D2 and D6, C.4 | Every door of Proforma takes typed inputs: `GET /api/proforma/bind` (on the flowsheet's own scope, `proforma:<flowsheet id>`) and `GET /api/proforma/ceiling-check` take `?inputs=`, converted at Proforma's door as a run's values are; the retired `?overrides=` (both) and the older `?assumptions=` (the ceiling check) are refused in words naming `?inputs=`; the Scenario and geneOS screens send the typed yield in its input's unit | The plan's D6 amendment at C.4. FastAPI passes over a query field a route does not declare, so a retired field is declared to be refused, as the run's body refuses a field it does not name |
| alpha 2.2 D6, C.4 | The biosteam engine reaches Proforma's scenario flowsheets through a provider Proforma registers with it as it is imported (`engine/biosteam.py` `provide`, `Provider`), and the package map holds no exception for it; the service's app imports Proforma through its tools, and conformance imports the app before it reads an engine (`conform.as_served`) | The plan's D6 amendment at C.4: `engine/` imports no module above it. The first cut imported `proforma` from `engine/biosteam.py` under a new exception, one hop from fermOS, pureOS and the composite |
| alpha 2.2 D6, C.4 | A library plant that takes configurations, asked with none, is read in its default at every parameters door (`GET /api/engines/biosteam/parameters`, `GET /api/library/{plant}/parameters`, `engine_parameters`, and a study scenario's check when it is made, its configuration kept as made), and `engine_plants`' rows give that default; a thing neither on the library's shelf nor provided is refused at biosteam's doors in words naming the engine's own things (a 422, as a contract engine's unknown thing is); a kept study scenario's value its plant's parameters refuse is a 422 in words at its run route and the tool's refusal in words, nothing kept | The plan's D6 amendment at C.4 (every door, the parameters doors and the study scenario door among them, and a 422 in words). The first cut ran the default at the run doors alone, answered an unknown thing with the library's shelf, and let the kept scenario's refusal reach a 500 |
| alpha 2.2 D6, C.4 | `conform biosteam` refuses in words a named thing that cannot run as it stands (biosteam's `unready`: a scenario flowsheet whose values wait), before anything is made, keeping no verdict; check 3 says when a run it makes answers no output. `pnpm prove` step 10 runs `conform biosteam` on its first thing, a library plant, check 2 reading every thing's parameters, the scenario flowsheets' among them; `core/tests/test_engines_sim.py` makes the eight checks on a scenario flowsheet on the real worker, with `--thing` | A failing verdict for a scenario flowsheet run without its values would stand in for biosteam's, as C.3b found for a project whose trains wait. The brief's reading of step 10: one more call there would run a Monte Carlo sample of the scenario flowsheet in the proof, which the sim test already makes |
| alpha 2.2 D7, C.5 | The bench records readings against a locked runbook's measures alone, with no protocol's steps: `Deposition.protocolId` and `MeasuredEvidence.conditions.protocolId` are null for such a deposition, opened from RunbookDetail's *The readings alone* once the person has set their name in Settings, and recorded at `DepositionBench` (`/runbooks/depositions/<id>/bench`), in `src/screens/Deposition.tsx` under that screen's constraints, its header comment kept and extended | No store holds a protocol in this build, and D7's walk deposits a reading at the bench on step 5's locked runbook. §11.5 keeps Deposition as it is beyond the store and type changes that reach it, so the gate (C.7) recorded the extension as a decision of its own: ADR-016 |
| alpha 2.2 D7, C.5 | A run's page makes a scenario through NewScenarioDialog's from-run mode, which holds the run page's former scenario maker and offers a deposition's readings beside a typed value, each said as what it measured and what it would set; the dialog's shelf mode carries no value | D7 has NewScenarioDialog offer the readings; the run page's own maker was the one that set values on a run's plant, and one dialog keeps one way to set them |
| alpha 2.2 D7, C.5 | `GET /api/depositions/readings[?unit=]`, a route of its own, lists the readings a run may take, the lookup's own rules deciding (`measurements.readings`) | The dialog offers what the service would take, read by the one copy of the rules |
| alpha 2.2 D7, C.5 | A deposition's, an entry's, an observation's and a measured evidence's id is time-based (`timeId`), unique across page loads | A measurement names a reading as `<deposition id>/<entry id>`; the counters before restarted with every page load |
| alpha 2.2 D7, C.5 (ADR-006) | `basis.origin_of` reads a deposition source naming one reading as a `measurement`, and one naming a whole series (a kinetic fit's readings) as a record, as it did; every reader of a value a run set asks `basis.is_set`, which holds a deposition to being a reading | The brief had origin_of map every deposition to measurement; a fit's series would then read as a measurement, and a fit's provenance would move |
| alpha 2.2 D7, C.5 (ADR-006) | A run is `measured` when any input is a measurement and none is a person's assumption or a model's estimate or rests on one (an artifact or a record behind a reading that is assumed, or that cannot be found, makes the run `assumed`). A record of a weaker class or an artifact computed with no assumption beside a reading leaves the run `measured`, the first class of `PROVENANCE_ORDER`, so a claim citing it ranks above gold while an unverified record stands in its basis | D7 and the prompt's §6.3 as written; §3 words a measured run as one on "measurements and records alone". ADR-006's note states the consequence, for the owner to settle §3's wording against §6.3's |
| alpha 2.2 D7, C.5 | The runbooks read lists a `reading` kind (each reading a run may take, read by its id, with its measure, value, unit, time and depositor) and a `measured-evidence` kind beside the `deposition` kind, and `module_stores.PARTIAL` holds no runbooks line; fermOS's read lists the depositions whose series it fits; Postdoc's rule 18 says how a scenario's value names a reading | D7 named a `deposition` kind; a model names a reading in a scenario with the reading's own value and unit, which the read then gives it, and the measured evidence was the rest of what the line said a read left out |
| alpha 2.2 D7, C.5 | A Proforma input set to a reading keeps `binding: assumption`, as a named value is bound; its words (the yield's, the ceiling check's, the titre pairing's) and the scenario card's counts read its source, a reading | A binding word of its own changes `ScenarioInput`'s type and every reader of it; the source names the reading already |
| alpha 2.2 D7, C.5 | `engine_report`'s parameter evidence reads each parameter's own origin word, so a person's value is `assumed` there (it read `computed` before C.5) | The evidence was labelled from a mix of `ParamOrigin` and `OriginKind` (the brief) |
| alpha 2.2 D7, C.5 | The service keeps a deposition the bench's way (`project_state.deposition_refusal`): readings and observations appended and kept as taken, a read-back moving `confirmed` from false to true, the state moving forward, a reconciliation kept as made, and closing stops new readings, observations and sample times; every other write is a 422 in words, and every write a closed deposition accepts is audited (`amend_depositions`). A correction keeps the `at` of the reading it corrects, the time the reading was taken, and says when it was typed (`correctedAt`) | A run rests on a reading's row, and the review found a page could rewrite a closed deposition under a run's reading; the bench's own comment promised an append-only record |
| alpha 2.2 D7, C.5 | A later entry on a measure still waiting to be read back corrects an earlier confirmed one, and the lookup's refusal says the newer number waits; the bench reads back the entries no later one corrects, and the record says which entry corrects which | The bench's newest number on a measure is what it says now: the person reads it back or corrects it |
| alpha 2.2 D7, C.5 | A reading whose deposition was kept with no person's name (`this browser`) or under a placeholder name is no measurement, refused in words naming Settings | A measurement names the person who took it, as a person's assumption names the person who typed it |
| alpha 2.2 D7, C.5 | At the tool door a reading's origin names the reading alone (its kind and ref); a depositor or a time written there is refused in words, and the REST door holds either to the rows | The registry writes every other origin from who called, and a tool's schema for a reading holds the two fields alone |
| alpha 2.2 D7, C.5 | `GET /api/state` carries `depositedBy`, each deposition's maker by id, which the record page shows | The person a measurement names is the row's maker, which the row's body does not hold |
| alpha 2.2 D7, C.5 | A comparison's value cell for a reading carries its `ref`; the export's study.md names a reading beside its depositor and study.json carries the depositions the runs' and the scenarios' readings rest on | A reading's number traces to its deposition without the service; a comparison with no reading keeps its id and its output |
| alpha 2.2 D8, C.6 | The code that computed a reference run and a benchmark stays, in `workers/kept_references.py`, reached by the Proforma worker's `replay_reference` and `replay_benchmark` alone (the ops `reference` and `benchmark` renamed), where D8 retires the two flowsheet modules and the worker ops that served only them | `proforma.reference` and `proforma_benchmark` stay registered so a kept artifact replays, and a replay recomputes its output through the code that made it; the shelf, the routes, the tools and the screens reach none of it |
| alpha 2.2 D8, C.6 | Both methods of `/api/proforma/benchmark` and `/api/proforma/reference/{id}` retire, the routes D8 names; the brief named their POST routes alone | Each GET read the newest run of a retired entry alone; the reference screen reads the library plant's runs (`GET /api/runs?engine=biosteam`) and the project's kept reference runs (`GET /api/artifacts`) |
| alpha 2.2 D8, C.6 | `FlowsheetInfo.reference` and `FlowsheetInfo.packageTest` leave the shelf's entries, with their pair in `check:plan` | The two retired entries alone set them; the library shelf names each plant's package test (`GET /api/library`) |
| alpha 2.2 D9, C.6 | `GET /api/proforma/scenarios` lists a kept scenario whose binding is refused with the refusal in words (`ProformaScenarioInfo.refused`, its inputs empty) | One scenario whose parts cannot stand (a vessel design or a train run gone, damaged or of another chemical set) answered 500 for the whole list; the list now answers, and the scenario's card on the index and its page say why it cannot bind |
| alpha 2.2 D10, C.6 | A file fetched by its address that hashes as one of the toolkit's reference flowsheets is kept with origin `library`, as an uploaded one is, where D10 writes origin `imported`; its source is the reference flowsheet's words followed by `fetched from <address>`, and the record gains `url`, the address a file fetched by its address came from (`SFFFlowsheet.url`, with its pair in `check:plan`) | The record's origin is computed from the file's hash whichever door it came through (`docs/api/sff.md`); the source keeps the URL beside the library's words (D10's amendment at C.6), and `url` holds the address for a reader that links it |
| alpha 2.2 D10, C.6 | The import by address refuses an address that names a user or a password, a case D10's list leaves open, a 422 in words; fixture mode's refusal, which D10 names, answers 422 in the collectors' words, a status D10 leaves open | The record keeps the address as its source, so a password in it would be kept with the file; a refusal of what a request names is a 422 in words |
| alpha 2.2 D10, C.6 | The fetch by address connects to a checked address itself, with no proxy (`trust_env` off: no proxy, netrc or certificate settings read from the environment), and holds the whole exchange, the resolution and the headers included, to the 120 s deadline (`anyio.fail_after` over an async client) | D10's amendment at C.6 sends the connection to the address that was checked, which a proxy would resolve again; a host that trickles its headers held a worker thread without end under a deadline read between body chunks alone |
| alpha 2.2 D2, C.7 | D2 moves the run requests to typed inputs: fermOS's, pureOS's, Proforma's and the library door's. Two shapes keep the resolvers' `Override` form, a bare value with `by`, `at` and a note and no unit: a train's own carried values (`TrainParam`, in `TrainInlet.params` and `TrainUnitSpec.params`, which `POST /api/pureos/train/run`, `/check`, `/validate` and `PUT /api/state/trains/{id}` carry, and `train_spec._as_overrides` lays under a request's inputs key by key), and the project's stored panel overrides (`PUT /api/state/overrides/{scope}`, checked for scope and key, then read as `Override`s and sent as typed inputs in each parameter's unit by `project_state.run_request` and `proforma.inputs_of`) | A train is hashed whole into its run's basis input `train`, so a train carrying typed quantities moves every train run's artifact id (D1); and the stored overrides are the browser's Durable snapshot's writes the service has not acknowledged (ADR-014). A request's input set on the same key replaces a carried value, converted at pureOS's door in the parameter's unit. Revisit: a train spec version that moves the ids, or accounts giving pending writes a home on the service (Known debts) |
| alpha 2.2 D2, E.17 | A stored panel override set to a deposition's reading keeps the reading's own value and unit (`Override.unit`, empty for every other row), and both senders send what the row holds: the browser's `inputsOf` (the panel's resolve, the run, the ceiling check) and the service's `proforma.inputs_of` (`project_state.run_request`). The C.7 row's stored overrides keep the resolvers' form for a person's value and a model's estimate, and every resolver still takes an Override in its parameter's unit (`basis.override_of` leaves `unit` empty) | The lookup's rule *its own*: a measurement carries its reading's own value and unit, so a reading kept in its parameter's unit is refused at every door; the row keeps one number, the bench's, and the service makes the one conversion at the door each time it is sent, stated in the value's note (ADR-006's note of E.17) |
| alpha 2.2 D5, C.7 | A train read from a run (`POST /api/pureos/train/from-run`) starts where the stream carrying the most product enters it from outside it, by the run's stream table: a feed, or a stream from no unit taken and no unit the train's own outlets reach going forward in run order; a unit taken before that one is listed among the units the train leaves out, with why, and the notes name every other stream entering the train from outside it with its product kg/hr. The Builder says in words when a run-stream inlet entered another unit than the train's first in its run, with each stream the first unit took there a click away (`builder-inlet-away`) | The rule took the first unit taken and its first inlet: on step 4's corn stover run that was a vent's mixer, M304, on a stream of gases carrying no ethanol, and a train cut to its tail ran on gas. The corn stover run now reads from M401 on the broth, s24 (the review round of C.7, the stranger's walk) |
| alpha 2.2 §6.1, C.7 | Conformance check 7 on a hand-written engine (the core's three) holds the refusal it reaches, a thing the engine lacks refused in words before any run with nothing kept, and its words say so; the receipt half of the check runs on a `WorkerEngine`, and a refusal inside a hand-written engine's own computation is a receipt its own tests hold (`test_engines.py`, `test_runs.py`) | A hand-written engine has no `compute` for the check to offer a thing to; the check's words read "kept as a receipt" above a refusal that kept nothing (the review round of C.7). A probe an engine declares, a request its own computation refuses, would hold the receipt by code (Known debts) |
| alpha 2.2 D0.1, D.0 | The worker's `run` op may answer `diagnostics` beside its outputs: what the computation reports about itself (the time it took, the iterations it made), each `{name, value, unit}`, a finite number or words, at most 50, held to the outputs' shape (`EngineBroken` on a break). The service keeps them on the run as `EngineRun.diagnostics` beside `durationMs`, from the computation that made the row; the run's page shows them under its outputs and `engine_report` names them as words. They enter neither the artifact (its output, hash, id and replay, the pins) nor `outputs.values`, comparisons, runbooks or evidence, and conformance check 3 holds their shape when a run answers some | The handoff's pre-read found the engine brief asking for the time a run took as an output and for a run that replays identically: a replay compares every output, so a clock reading among them fails check 4, and the proof with it. The contract named outputs and `durationMs` alone, and no channel for what a computation reports about itself; a result stays an output, a function of the request alone. No core engine answers diagnostics, and every pin holds (ADR-015, Implementation D.0) |
| alpha 2.2 §6.1, E.18 | `EngineThing` carries `configurationTitles` beside the fields `GET /api/library` answers for a plant: optional words a person reads for each configuration, by its name, each 1 to 200 characters; a key outside the thing's configurations, or a title of spaces alone, breaks the contract as a `defaultConfiguration` outside them does | §6.1 has `things()` answer in the shape `GET /api/library` answers, whose configurations are words a person reads; a kinetics configuration is an artifact id, which tells a person neither its kind nor when it was kept. The field is optional and enters no basis, so every package built on the page before it, the mirror among them, stands as built (ADR-015's note of E.18) |
| alpha 2.2 D0.8, D.0 | `pnpm prove` installs every package directory under `examples/engines/` (one holding a `pyproject.toml`) into core's environment with `uv pip install -e` before its service starts, one check a package, and step 9's walk runs the first thing of each engine those packages register from the Runs screen, the engine chosen on Studies' run card, reading the run's provenance, outputs and diagnostics on its page; with no package there, one line says so and the walk checks nothing more. Step 10 conforms every engine the service lists, as at C.7. The proof names no engine of `examples/`. After the review (D0.8a, D0.8b): every install, the proof's and `scripts/engines-local.sh`'s, is held to `core/uv.lock`'s versions (`uv export --frozen` as its constraints), so a package that would move a pin is refused in uv's words; a package that leads outside `examples/engines/`, a `pyproject.toml` that cannot be read and a hung build each fail the proof in words; every thing of an example engine runs at its own defaults, and the walk fails at once in the service's words for one that waits; and at its end, however it ends, the proof leaves core's environment as it found it, uninstalling what it installed there, with `--keep` leaving the packages while the kept service runs | The stage's proof step installs the stranger's engine and checks it, and the core is frozen before the strangers work: a step written generic over engines picks the stranger's package up with no change under `scripts/`. An install resolved from PyPI with no lock could move BioSTEAM, thermosteam or biorefineries under the proof or a live service, and an engine left installed after the proof was listed with its import's error once its directory went, failing the next proof |
| alpha 2.2 D.0 (M, B1, B5) | The MCP server takes `--service <origin>` and acts through a running service on loopback (`http://` or `https://`, 127.0.0.1, [::1] or localhost, an explicit port, nothing after it), sending each call to the service's own routes with the project and the client's declared name in `X-OpenFerment-Assistant`, opening no database, through no proxy; `POST /api/tools/{name}` reads the header and runs the call in the model's lane under that name. In its own process the server checks its project at the first call and says at every call, in words, a project its database lacks | The agent stranger gets a project id and a running service's address in a worktree with no `core/.env`, and the proof's kept service runs on a database of its own whose address the brief cannot carry; the server read its own database alone, and acted unchecked in a project its store lacked. The header gives an HTTP caller the model's lane under the name it declares: a number it types is that name's estimate, which every record store refuses; its `catalogue_write` replaces only an entry that name kept through an assistant's door; and it writes the stores that hold a model's work alone, pureOS's kept trains among them, where a `?by=` call is refused. A loopback caller reaches that lane already through `POST /api/ask`, and an MCP client in the server's own process with the database's address; the header is one more door to it, `guard.py` holds it as it holds every POST, and no listener, host or CORS rule is added (ADR-008, Implementation 12) |
| alpha 2.2 D.0 (D0.4, B11) | A model's `catalogue_write` (Postdoc or an MCP client) replaces only an entry kept in the model's lane under its own name through the same kind of door, Postdoc's loop or an outside assistant's (MCP, or the tool door's assistant header); a person's entry, and another caller's, stays as it is, and the call is refused in words naming the entry and who kept it, nothing written. A person's keep (the route, a file, `?by=`) replaces whatever the id holds. Each entry records its lane and its door (`CatalogueEntry.agent` and `via`); an entry kept before reads both from its source | The tool replaced whatever entry held the id, a person's included, and no tool or route takes an entry out. D0.4 names a person's entry and lets a caller replace its own; an entry another model or client kept is refused too, so a client cannot rewrite Postdoc's entries, or another client's, under its own name. A model whose name changes (a fallback model, a client's new version) keeps its next entry under an id of its own |
| alpha 2.2 §6.5, E.1 | `src/lib/studies.ts` and `src/lib/params.ts` move to the generated types with Proforma's screens; §6.5 counts `lib/studies.ts` as on them already and lists it with the runbook screens | The Proforma screens hand both libs their values, and `lib/studies.ts` read ten hand types beside its four generated ones (the stage plan's finding 4); the runbook screens read the store's runbooks, which move in E.11 |
| alpha 2.2 §6.5, E.4 | BioRepo's Organism and Topic columns, filters and CSV fields, PaperReader's organism and topic chips and its abstract, and the attribution of a record to a strain through its paper's organism list (StrainPage, Organisms) leave with the hand-kept paper; a strain's papers are the papers its records were read from, and the CSV's Venue column is Journal, the service's name | The generated paper is the overlay's entry, what the service writes of a document the project holds (ADR-002), and the overlay carries no organisms, topics or abstract: the store filled each empty, so every column, filter, chip and attribution that read them showed nothing (ADR-007's note of E.4) |
| alpha 2.2 §6.5, E.9 | The readers of the alpha 1.0 strain and product fields that no catalogue entry keeps leave with them: StrainPage's taxonomy, badges, biosafety level, Notes band and its band of the products made in the host (a product named its default host), Organisms' badges and biosafety level, Protocols' biosafety level in a strain's label, geneOS's Pathway list of the routes products declared and its count, pureOS's count of the molecules that declared each unit operation with its two stats (*Molecules with a train*, *Operations unused*), and RunbookDetail's process train of the unit operations a product declared, which now says the product's entry keeps its class, its location and its sequence, and that pureOS builds and proposes a train. A strain's page and card show what its entry keeps: its species, name, other names, chemical set, note and who kept it; Hosts and a strain's page say they are reading the catalogue until it answers; pureOS counts the products on file and those with the class its proposer reads; the palette finds a strain by its other names; the walk opens Hosts and the strain's page after the catalogues screen keeps it (`scripts/walk.ts`, step 9) | The store's strains and products are the project's catalogue entries (ADR-007's note of E.9), whose kinds keep names and words, never a measured value (`catalogues.CatalogueEntry`); every read that went read an empty list, since the store held no strain or product before this commit, and the service holds none of those fields to serve |
| alpha 2.2 §6.5, E.12 | Primer's screens read the project's lessons from `GET /api/catalogues/lesson`, where §6.5 writes `/api/catalogues/lessons` | `catalogues.KINDS` names each kind in the singular, so the plural path answers 404 (the stage plan's finding 3); the catalogues screen's lessons tab keeps `/catalogues/lessons` as its own address |
| alpha 2.2 §6.5, E.12 | The Durable snapshot keeps no lesson, and Primer lists the project's lessons in the catalogue's order, a lesson addressed by its id alone (`/primer/<lesson>`): the modules slice, `learnProgress` and `completeLesson` leave the store, and a lesson shows passed from the ledger's knowledge entries for whoever is learning, so a lesson that counts toward no skill shows passed for nobody; a snapshot's older `learnProgress` loads, and the next save leaves it out (ADR-014's note of E.12) | §6.5 asks that the snapshot keep no lesson; the lesson catalogue keeps no module (ADR-018), and the ledger is where a lesson's passing stands for every device and every person |
| alpha 2.2 §6.5, E.12 | `src/lib/protocols.ts` is born with the protocol screens, beside the two libs §6.5 names for them (`lib/guild.ts`, `lib/practice.ts`): the generated protocol family, the four protocol routes and the readers of a version's lists | A project keeps its protocols on the service since E.12a (ADR-017), and the protocol screens, Guild's Matrix and skills, Primer's path and the bench read them; neither of the two named libs is about protocols |
| alpha 2.2 §6.5, E.gate | An artifact's `output` stays the engine's own dict, and the screens read it per tool through the shapes their readers name, each field read with its default: a comparison's runs, rows and values (ProformaComparison), a run's `outputs.values` (each in the shape the service writes an input in, `RunInput`, through a guard), geneOS's frontier and mix points, a Proforma or library run's tables and its package-test checks (`lib/proforma.ts`) and a train run's (`lib/pureos.ts`). The service serves a run's tables and checks as typed reads (`GET /api/biorepo/artifacts/{id}/tables` and `/checks`, alpha 2.2 E.0a) for a client that holds no artifact, and the screens read the artifact they hold already. The SSE envelopes (`ServiceEvent`, `StreamEvent`) and the kit's answer citations (`AnswerSource`, `lib/literature.ts`) stay the client's own event shapes | `Artifact.output` is `dict[str, Any]` on the service: each tool writes its own, and a tool's output gains fields over its versions (a run kept before the tables reads with empty ones), so a model per tool's output is a change to the artifact store's contract that needs a decision record of its own; the OpenAPI document holds no events (the stage plan's finding 5) |
| alpha 2.2 stage E, E.gate; F.5 | The two Known debts alpha 2.1 gave stage E (a Proforma panel row that chooses a deposition reading; Studies' run card naming a kinetics configuration by its kind and when it was kept) leave stage E's gate: each is built as a commit of its own (E.17, E.18) in a worktree beside stage F's live rebuild, E.19, the review of the three (E.debts) and the gate's leftovers (E.20) after them on the same worktree's branch (`alpha22-e-debts`), and stage F's retrieval commands in a second worktree (`alpha22-f5`: F.5.1 to F.5.4). Both landed on `claude/alpha-2-2-base` on 8 November, before the fourteen are asked on the screen, each commit cherry-picked onto F.2e/F.2f's `2ed7dac` with its own message: E.17 `7e178bb`, E.18 `09e95dd`, E.19 `b70fa83`, E.debts `8bde8ab`, E.20 `448adbb`; F.5.1 `2795aa7`, F.5.2 `8e2ec88`, F.5.3 `19d129a`, F.5.4 `adb9c8d`. Each pick's log lines go in their stage's section; the main line had moved under both (F.1 to F.2f), so F.5's note in ADR-008 stands as Implementation 18 with each reference to it, `llm.KIT_ROOM`'s comment names the judge's 32,000 tokens (`JUDGE_TOKENS`), its room at max set to them by the landing review, and F.5.1's two new tests read the routes' defaults of Implementation 17 (its tally test `explain` at high and `judge` at max; its room test sets `explain` at medium, F.5.4's version of it at high) | Each needs a service model beyond the screens' types: a panel override that keeps a reading's own value and unit (`Override` holds a bare value in its parameter's unit), and a title per configuration in `EngineThing`, which changes the engine contract's page; stage E's gate stands on the type move, the catalogues, Primer and Guild on the catalogue, and the review's fixes. F.5's commands are built and checked with no model call, beside stage F's live steps |
| alpha 2.2 §6.5, E.7 | `src/lib/proposals.ts` moves to the generated types with pureOS's screens, where §6.5 names it; its readers are Home's ProposalsCard and check:guild, and it reads the Guild person acting from the hand-kept types until Guild's lib moves (E.12) | A gate's proposal is what a model asked for in any module (OF-BLD-015 §7.4); pureOS's screens read a train's proposal, `TrainProposal`, from `lib/pureos.ts`. The file moves in the commit §6.5 names, with the readers it has |
| alpha 2.2 §6.1, B.2 | `run(thing, configuration, inputs, by)` takes `inputs` as a list of `EngineInput`, each a parameter's key and a `Quantity` (the shape a run's inputs have, `RunInput`), where §6.1 writes `inputs: list[Quantity]` | A `Quantity` carries no name, so the parameter each value sets is named beside it |
| alpha 2.2 §6.1, B.2 and B.6 | An engine declares `heavy` beside `worker`: the modules its worker alone imports. The registry and conformance check 6 keep the worker module, each module `heavy` names (with every module below it) and `workers.WORKER_LIBRARIES` (BioSTEAM, thermosteam, biorefineries, the SFF toolkit, cobra) out of the service's process for every engine; `worker` may be `None` only with `heavy` empty | §6.1's `worker` names one module, and its name alone cannot say which of the libraries it imports are heavy; check 6 needs the list to hold them out |
| alpha 2.2 §6.1, B.2 | `engine → api` and `engine → tools` join the package map's exceptions (`test_boundaries.py`) | Conformance check 1 sends a bare number through the service's own route and its tool, the two doors a number enters by, and §6.1 names the command `openferment_core.engine.conform` |
| A4, stage 8 | `test_no_seed.py` holds what A4 names (each deleted module absent, no `.ts` under `src/data/` exporting content, the shipped stores empty), and an `rg` over `core/tests/` still finds test values: `standins.py` (stand-in records on real strain ids, a closed-form ethanol evaluator with the theoretical yield on glucose; 27 test files use it) and `test_proforma_slow.py` (the benchmark price this build once measured). `src/` and the service's code hold none | The stand-ins carry rule tests (binding, overrides, ceilings, run contracts) that stage 4's library fixtures were to replace; that work did not fit stages 4 to 8 (a debt below) |
| §5.5, A3, stage 7.1 | The Durable snapshot keeps the writes the service has not acknowledged (review decisions, Guild entries, project rows), beside the preferences; a record the service holds is never kept there (ADR-014) | Without the queue, a reviewer's decision made while the service is away is lost on the next reload |
| §4.8, §11.1, stage 6.3; alpha 2.1 D.4 | Built at alpha 2.1 D.4 on the owner's word (question 10): `X-OpenFerment-Key` serves a request's calls and is kept nowhere; a local model behind `OPENFERMENT_LOCAL_BASE_URL` stands in a route; a route naming another provider waits in words (ADR-008, Implementations 10 and 11) | Stage 6.3 left both for the owner, since §11.1 asks the owner before a change to how keys are stored or read; the owner authorized question 10 and the local model on 2 November (the alpha 2.1 prompt's §3) |
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
| §9 step 4, stage 4.2 | The corn stover plant (the NREL cellulosic ethanol design) holds nine of its package test's eleven values on the pinned versions; the run's checks name the two it misses. `scripts/prove.py` step 4 holds each of the two to what the package's own code measures on this installation, to the run's ten digits, and fails on any other value outside (ADR-013) | Measured, as its reference run has since 2026-10-20: installed equipment cost −7.9 %, electricity consumption −5.2 % (`docs/reports/library-regression.md`). The package's own `test_cornstover` fails the same way under biosteam 2.54.0 (run 2026-10-30) |
| §8.4, stage 4.2 | `engine/library.py` imports the shelf's package-test reader (`flowsheets/shelf.py`) and, where a run is kept, `artifacts` | Both belong to the engine by §7.2's table and still live outside `engine/`; the boundary test at the stage 4 gate decides their place |
| §8.3, stage 4.3 | The recipe's authored file is `extended_metadata.yaml`, where the prompt wrote `metadata.yaml` | The SFF toolkit's runner reads that name (`load_extended_metadata`) |
| §8.4, stage 4.3 | The composed flowsheet runs through the library adapter (kind `flowsheet` on the library shelf, `library.run` artifacts), and runs the package's own composition body (`SystemFactory.f`) with its pretreatment and fermentation factories chosen | One adapter for every plant (§2 item 3); the package's own system factory checks that dilute acid's inlets are used and cannot take another pretreatment, and its body keeps every number the package's (ADR-004, Implementation 4.3) |
| §8.4, stage 4.3 | The organism is the one the package's reaction sets model, declared in the recipe (`extended_metadata.yaml`); a configuration names none | A BioSTEAM system names no host, as the toolkit's own recipes say; the package holds one organism's reaction sets, so a choice would have one entry |
| §8.4, stage 4.3 | AFEX and alkaline pretreatment are on the shelf and refused: AFEX with BioSTEAM's `InfeasibleRegion` in its ammonia mixer, alkaline with a chemical alias the cellulosic chemicals lack | Measured: the package's factories, composed on its corn stover feed and chemicals |
| §10 stage 1.1 | Section 5 runs in the order 5.4 + 5.3 (one commit), 5.1, 5.2, 5.5, 5.6, 5.7 | `demo.py`, `retrieve.py` and `rageval.py` were the heaviest users of the program machinery and build their fixtures through each other; deleting them first spares edits to files deleted one step later, and a commit between 5.4 and 5.3 could not be green |
| §5.3 | `demo.py`'s stand-in evaluator and stand-in records moved to `core/tests/standins.py` (test-only) | Thirteen kept test files (Proforma, fermOS, params, pureOS, tools) test binding, override, ceiling and run-contract rules on them. Stage 4 replaces them with fixtures read from library plants (debt recorded below) |
| §5.4 | `search_passages` stays registered, with one seam (`tools/passages.py: search`) that answers "no literature index exists yet" | Postdoc's quote validation and its tests keep the passage contract; stage 3 fills the seam with Sci RAG Kit. The whole-sentence rule moved to `quotes.py` |
| §10 stage 1.1 | 5.1, 5.2, Dominion and the retired guards (from 5.6) are one commit, 1.2 | The program machinery, the seed and Dominion share the store, the types, `module_stores` and `models`, and the retired guards import the seed: no commit between them could be green |
| §5.2 | Tests that held seeded content were deleted with it; rule tests that only used it as material now run on fictional fixtures: placeholder papers and records in the tests' own stand-in pools (`test_tools.py`'s `pool`), placeholder Guild skills and protocols in the alpha 1.0 shape (`core/tests/fixtures/guild-projection.json`), small fictional projections inside tests, and a test-only categorical field | A4 forbids seeded values under `core/`; the rules (anchoring, review decisions, retrieval, coverage, Guild) stay tested |
| §5.2 | Eval set O (`evalo.py`, `pnpm eval:o`) and the identifier tooling (`identifiers.py`, `scripts/resolve-identifiers.py`, `pnpm ids:*`) are deleted | Eval set O's ten questions named the seed; the identifier tooling patched DOIs into the TypeScript seed |
| §5.5, §10 stage 1 | Stage 1 deletes the merge driver, the data-sync, data-prepare and decisions-push scripts, `sync_decisions.sh` and the `openferment-data` branch convention. The file stores (`core/data/*.json`, `audit.jsonl`, `artifacts/`, `candidates/`, `live/`) and the browser's Durable scientific state stay until stage 2 replaces each with its PostgreSQL store, as stage 2 step 2 says; `core/data/biorepo.json` stays tracked until then | Untracking `biorepo.json` would make the live Mini's next pull delete the review decisions people made there (§11.1); stage 2 imports them into PostgreSQL |
| §7.4 | Tables `overrides`, `fits`, `trains` and `practice_scenarios`, and `projects.settings`, beyond the list; each table keeps its lookup keys as columns and the rest of a row as `body`, the Pydantic model as JSONB | §5.5 moves those browser states to the server; the Pydantic models stay the one description of content (ADR-001, Implementation) |
| §5.5, stage 2 | The fetched full texts (`core/data/fulltext/`) and the fetched genome-scale models (`core/data/models/`) stay files | They are caches of documents fetched from outside, fetched again when gone; stage 3 hands documents to Sci RAG Kit's tables |
| §5.5, stage 2 | The browser keeps an outbox: review decisions, Guild changes and project rows the service has not yet acknowledged, saved in IndexedDB until sent; and three preferences, who is deciding, who is acting in Guild, and the lessons finished here | A deposition at the bench must survive a reload while the service is away (the reason Durable state existed); the outbox holds nothing the service already has |
| §7.4, stage 2 | A Live conversation is kept whole in `conversations.body`; `turns` and `tool_calls` wait for stage 6 | Stage 6 gives Postdoc its memory on the server and fills them |
| §7.4, stage 2 | `project_state.py` checks a page's row for kind, id and shape, and keeps its content as sent (since alpha 2.2 E.0b each kind reads as its model in `models.py` first, and `GET /api/state` names a kept row that does not read in `refused`) | The content's rules run where they always ran; stage 7 generates the page's types from Pydantic models |
| §5.5, stage 2 | `core/data/biorepo.json` stays tracked, and nothing reads it | Removing it from git would delete a live instance's working copy on its next pull, decisions and all, before they could be carried into a project (§11.1). `pnpm db:import-alpha1` carries it; it leaves git once the owner says the live instance's import read right |
| §5.4, stage 8.5 | The evidence pool keeps BM25 as its ranker: it loads the project's candidates and decisions from PostgreSQL and ranks them in memory for one question, with the coverage rule, the filters and the cap of ten | A project's records are few, and the ranking rules are tested on their own (`test_evidence_pool.py`); a ranking in SQL would change what Postdoc cites without a measurement to say it is better |
| §6.2, stage 8.5 | `src/engine/units.ts` stays the browser's unit engine, mirroring `units.py` on the same tables (`schema/units.json`), held equal by the fixture `pnpm export:unit-fixtures` writes and `test_units.py` asserts | Every screen formats and converts with it; serving each conversion from the service is a change to every caller, after alpha 2.0 |
| §4, §5.2 | The record fields, the vocabulary (carbon sources and unit operations) and the unit tables live in `core/openferment_core/schema/` (`fields.yaml`, `vocabulary.yaml`, `units.json`), with no range and no example value; `src/data/ontology.ts` and `vocabulary.ts` mirror them, held equal by `test_schema.py` through the fixture `pnpm export:unit-fixtures` writes. BioRepo's typed-value refusal is renamed `range` → `unit`; `pyyaml` is a direct dependency | The service needs the fields without the TypeScript seed; a range is a number about a field (ADR-010) |

## Blockers

| Since | Blocker | Next command |
|---|---|---|
| 2026-11-08 04:28 UTC | The Anthropic account's own usage limit: "You have reached your specified API usage limits. You will regain access on 2026-12-01 at 00:00 UTC." It refuses every model call; openFerment's daily cap stood at 25.28 USD of 150 that day. It stops stage F's live steps where they stand: the opus-max table's other ten questions (eq-eth-05 to eq-eth-14), the second judge (Sonnet alone at max over every tag's newest runs), the measure of the plan's larger room (F.2g), the fourteen on the Postdoc screen on the final routes (F.3), `pnpm prove --live` (F.4) and the retrieval lanes that call a model (F.5: the concept graph, HyDE, the judge's grading and the answer lane) | The owner raises the limit in the Anthropic console (Settings, Limits), or waits for 2026-12-01; then the five steps `docs/reports/model-routing-2026-11.md` lists under the alpha 2.2 part's "To finish it" (from line 491), in its order, `OPENFERMENT_MAX` standing for the opus-max table it writes out: `pnpm ready --probe`, its probe row green; the larger room's measure, `OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES="$OPENFERMENT_MAX" pnpm eval run --live --suite ethanol --tag opus-max-room --judge --only eq-eth-01,eq-eth-02,eq-eth-03,eq-eth-04`; the table's other ten on the same table and tag, `--only eq-eth-05,eq-eth-06,eq-eth-07,eq-eth-08,eq-eth-09,eq-eth-10,eq-eth-11,eq-eth-12,eq-eth-13,eq-eth-14`; the Sonnet pass, `OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES='{"judge":{"models":["claude-sonnet-5-5"],"effort":"max"}}' pnpm eval judge --suite ethanol`; and `OPENFERMENT_PROJECT=ethanol pnpm eval summary --suite ethanol --rows`. The tag `opus-max` keeps the old room's four answers. Then F.3, F.4 and F.5's live run, in Resume item 5's order |
| 2026-10-30 | Owner action, before the first alpha 2.0 deploy on the live Mini: its records are files under `core/data/` until carried into a project. The files keep as they are while the owner waits: since stage 2 the service writes every record to the database | Once alpha 2.2 is merged into `main` (until then `main` holds alpha 2.1, whose `install.sh` stops at step 3 with Homebrew's keg-only PostgreSQL off its PATH), on the Mini, in its checkout `~/openferment`, as `docs/runbooks/live-host-install.md` steps 0 to 5 give it, with no alpha 1.0 deploy first (alpha 1.0's `deploy.sh --keep-decisions` commits the decisions and pushes them to GitHub): `brew install postgresql@17 pgvector && sudo brew services start --sudo-service-user="$(id -un)" postgresql@17` (PostgreSQL from power-on; `brew services --help` lists the flag); alpha 1.0's own `scripts/host/install.sh --uninstall`, `[ -e ~/openferment-alpha-1.0-data ] || cp -Rp core/data ~/openferment-alpha-1.0-data` and `git pull --ff-only`; `core/.env` kept, or made from the example without its database line; `scripts/host/install.sh`, which makes the database `openferment`, names it in `core/.env` and stops at its deploy step while `core/data/biorepo.json` holds the Mini's decisions; then a copy of the file outside the checkout, `pnpm db:migrate && pnpm db:import-alpha1 --name "Alpha 1.0 records" --by "<your name>"`, `git checkout -- core/data/biorepo.json` and `scripts/host/install.sh` again; then `pnpm ready` (step 4) and `OPENFERMENT_PROJECT` as step 6 says |
| 2026-10-31, the step written 2026-11-08 | Owner action: the live instance's backup runs from the first night after the owner's first install. The place is the alpha 2.2 prompt's §3: `scripts/host/nightly.sh` dumps the database `openferment` first each night with the keg's `pg_dump` (`backup_database` in `scripts/host/lib.sh`) into `~/openferment-backups/openferment-<date>.dump`, the folder and its files the owner's alone, the newest seven kept, tested on stand-ins in `core/tests/test_host.py`. Guild's decisions live in the database since stage 2, and `pnpm ready`'s backup row left at 8.5. Guild's ledger is personnel data and never enters git | The live-host install (the row above), once alpha 2.2 is merged into `main`; the morning after its first night, `ls -l ~/openferment-backups/` names the night's dump, and `~/Library/Logs/openferment/nightly.log` says what the dump step did. `docs/runbooks/live-host-install.md` step 7 reads a dump back into a database of its own |
| 2026-10-30, again 2026-11-02 (HTTP 403, twice) | The session's git relay refuses tag pushes (branch pushes work): `git push origin alpha-1.0 alpha-2.1` ends with "RPC failed; HTTP 403" and "unexpected disconnect while reading sideband packet". The tags `alpha-1.0` (`d19224f`) and `alpha-2.1` (`fa1b744`, #16's head) exist in this container only; both commits stay reachable from `main` | On the owner's machine, in any clone: `git fetch origin && git push origin d19224ff0b6eb809b21492d1b7a2e8fd895a0f44:refs/tags/alpha-1.0 fa1b7448a5b5e5a2b943b3fc9546f8a420a8ef10:refs/tags/alpha-2.1`, which runs the same in a clone that holds the tags already |
| 2026-11-04 (11, 12), 2026-11-08 (13) | Owner questions 11 (the label of a run resting on a bench reading and a weaker record), 12 (an address a model names for the service to fetch an SFF file from) and 13 (how `has_key` reads the key line) are open; each default stands in the tree, and 12 and 13 each touch a stop condition (a widening of what the service reaches outbound; a change to how a key is read) | The owner answers each in the Owner questions table; a changed answer is one commit with its test: 11 in `basis.basis_provenance` (ADR-006), 12 at the import door (`POST /api/flowsheets/import-url`, `flowsheet_import`), 13 in `scripts/host/lib.sh` with `core/tests/test_host.py` |

## Known debts

Three groups, as alpha 2.2 closes (stage H, 8 November): the debts paid, each with its commit; the
debts open, each with the stage or condition that pays it; and the debts left by decision, each with
the line that records the decision and the decision record it stands under.

### Paid

| Debt | Paid at | Commit |
|---|---|---|
| A scope's overrides went to the service as one list and the service replaced the scope whole, so of two tabs on one Proforma scenario's panel the second's write deleted the first's kept override with no word on either page (H7-04, S1); a write of a scope now names the rows its view stood on and the service lays it on key by key, keeping another page's keys and refusing in words a key both pages changed, nothing kept, after which the page reads the project's overrides again | the bug hunt's fix run, group 3 (12 November 2026) | the commit after `6b93984` |
| Review decisions were keyed by record id alone in the browser's snapshot, so of two projects' offline decisions on one record id (a record id is made from a paper and its words, and one paper may be held by two projects) the later stood and the other was never sent; each is keyed by its project and record now (`decisionKey`, `decisionsIn`), and a decision kept by its record alone leaves once the page saves it under its project | the bug hunt's fix run, the fourth round of the H7-01 fix (11 November 2026) | the commit after `c12687b` |
| Two concept-graph builds at once (`pnpm lit:graph` for two projects) could lose one project's document from an entity's `document_ids`: each build batch read `kg_entities`, merged in Python and wrote the arrays back with no lock, so the entity kept the description the lost document's passage produced and `graph.entities` showed it to the other project. Every build batch's transaction now holds one advisory lock (`graph.GRAPH_LOCK`), and a test makes two builds overlap every time | the bug hunt's fix run, 11 November 2026 (found by group 1's review) | on `claude/alpha-2-2-fixes`, after `e173803` (the Log, Fixes after the bug hunt) |
| The agent builder's interface points (`docs/reports/handoff-2026-11.md`, round 1), each in the code `docs/TOOLS.md` and `docs/api/openapi.json` are written from (ADR-008's Implementation 13): a BioRepo record is one rule, `module_stores.RECORD`, that `biorepo_read` lists its kinds `record` and `candidate` by and `search_records` names each hit's kind by, so a candidate a reviewer verified is a record; a write's answer names the audit rows it left (`ToolResult.auditIds`), a gated write's proposal among them; `GET /api/audit` takes `action`, `target` and `who` beside `limit`, so a write of any age is found by what it was, and serves each row as an `AuditRow` under its `id`, its null fields left out as an answer over MCP leaves them out; `AuditEntry`'s `detail` says what a row holds, and `catalogue_write` and `study_scenario` keep their call's note there as the other writes do; a module read's summary is a `ModuleRead`, its `partial` a sentence, and `module_stores.DETAIL` names each kind's `detail` field by field; the client recipe hands the server no `VIRTUAL_ENV`, and the page's top points at it. `core/tests/test_agent_interface.py` holds each, a row of every kind among them | alpha 2.2, E.16 | `dc02f20` |
| The per-request key override and the local-model route (owner question 10 and §3 of the alpha 2.1 prompt): `X-OpenFerment-Key` serves a request's calls and is kept nowhere; `OPENFERMENT_LOCAL_BASE_URL` serves a local model in single calls | alpha 2.1, D.4 | `fa9782e`, `53c123c` |
| A retrieval report over a project's own corpus, as far as it asks no model: the commands (`pnpm lit:graph`, `pnpm lit:report --project`; ADR-002, Implementation F), then the Ethanol project's 130 questions, built by code from its 457 kept candidates and asked in `interactive`, `vector_only` and `keyword_only` under both relevance rules with 0 model calls (`docs/reports/literature-retrieval.md`), and the graph build's dry run, 92 batches over its 814 passages. The lanes that ask a model are open (below) | alpha 2.2, F.5.4 and F.5's offline part | `adb9c8d`, `0dd8415` |
| The kit's `search_entities` and `get_entity_relationships` read the concept graph whole (every project's entities, relationships and evidence quotes), so the kit's MCP server left them off; the `sci-rag` server serves both under the kit's names and arguments, each reading the project's graph alone through `literature/graph.py` (ADR-002, Implementation F) | alpha 2.2, F.5.3 | `19d129a` |
| The catalogues are project stores (migration 0007, `catalogues.py`): strains and their aliases, products, Guild's skills and Primer's lessons, each with a route, `catalogue_read` and `catalogue_write`, and an Intake path for a file of entries; the proposer, ProtParam, Guild and the module reads read them (alpha 2.1, D.1). The catalogues screen at `/catalogues` lists, adds and edits each kind in the name Settings holds and takes in a file; a skill's entry holds the policy Guild's levels read, and a product's the class and the place the cells leave it, which pureOS's proposer reads (E.8). The store reads the project's strains and products from the catalogues as the page opens and after each keep and file on the catalogues screen, so geneOS's hosts and their pages, the strain choosers of fermOS and pureOS, pureOS's proposal chooser, the runbooks, the protocols and the palette name what the catalogues keep (E.9). A project keeps its protocols in a store of their own (migration 0010, `protocols.py`, ADR-017), each step's skills held to the skill catalogue, and Guild's steps, Practice's sources, a check's brief and the runbooks module read them; a lesson keeps its body, its minutes, blocks and checkpoint (ADR-018), and the Primer module's read lists a catalogue lesson (E.12a). The store reads the project's skills and lessons with its strains and products, and its protocols from the service, as the page opens: Guild rates people on the skills the catalogue keeps, a protocol's step names them in the editor's picker, and Primer teaches the lessons with their bodies (E.12) | alpha 2.1, D.1; alpha 2.2, E.8, E.9, E.12a and E.12 | `a0c33bb`, `50a4f96`, `61c4e3f`, `37addaf`, `c18c0e7` |
| `src/engine/competence.ts` and `checks.ts` read a skill's policy as present, where the service leaves a skill kept with no policy out of every level in words (`competence.unrated`, E.8). The browser's skills are the catalogue's, and competence.ts leaves such a skill out the same way (`rated`): nobody holds it, the ranking proposes no check on it, a path and the skill's page say it waits for its policy, and the gate names it; `core/tests/fixtures/competence-unrated.json` holds the two equal on it, and `competence.json` stands byte for byte | alpha 2.2, E.12 | `c18c0e7` |
| No screen made a protocol, so a project's first protocol reached the screens through the API alone; the protocols page begins one (its id, title, category, biosafety level, purpose, organisms, base batch, minutes and first steps, version 1.0) in the reviewer's name, and its editor opens on it to add materials and each step's skills as version 1.1 | alpha 2.2, E.gate | `3b40de6` |
| `stream_table` on a scenario's kept run lost its test with the seed scenarios; `test_tools` reads the stream table of the run it makes of a kept scenario, from the run's artifact | alpha 2.1, D.6 | `32b95f1` |
| The module reads list a project's depositions, each reading a run may take and the measured evidence a reconciliation released; `module_stores.PARTIAL` holds no runbooks line | alpha 2.2, C.5 | `fd17f32` |
| Proforma's screens read every scenario as the project's (`createdScenarioIds`, the index's `needsBinding` and the held path gone); `GET /api/proforma/scenarios` binds a kept `custom_train_v1` scenario with the parts it names and lists one whose parts cannot stand with its refusal in words, where it answered 500; pureOS's choosers list each scenario once | alpha 2.2, C.6 | `f5405f8` |
| `src/engine/geneos/enumeration` (Dominion era) served RunbookDetail's research funnel, whose words spoke of a clearance reading and a molecule; the module and the funnel are deleted with those words, and each returns from `alpha-1.0` with a decision record if ever needed (ADR-010's note of E.10) | alpha 2.2, E.10 | `e90deeb` |
| `src/data/types.ts` was hand-kept beside the generated `src/api/types.gen.ts`, held to the service by `check:plan`'s pairs. Each lib moved to the generated types with the screens and components that read it, one commit at a time: Proforma's (E.1), the two flowsheet screens (E.2), Postdoc's (E.3), BioRepo's (E.4), Intake's (E.5), fermOS's and thermosteam's (E.6), pureOS's (E.7), geneOS's with the catalogue's strains and products (E.9), the runbook and deposition pages (E.11), Guild's, the checks', Practice's and the protocols' with Primer's screens (E.12), the two Settings screens (E.13), and the components and modules that remained, with the browser's own types each moved to its owner (E.14); the catalogues' lib and screen were born on them (E.8). E.15 deleted the file, and `check:plan`'s pairs retired with it, 218 types and 1629 fields at their last run: `gen:api --check` holds the generated types to models.py and `typecheck` holds every reader to them, and `check:plan` keeps the provenance ranking (ADR-007's and ADR-011's notes of E.15) | alpha 2.2, E.1 to E.15 | `a471f92` (E.1) to `8281f5e` (E.15) |
| The generated types name three fields an answer serves as kept as present (`Override.origin`, `Runbook.note`, `Runbook.progressPct`), since openapi-typescript writes a field with a default as one an answer holds. Each reader reads them as a row may leave them out: `inputsOf` reads a change kept with no origin as a person's assumption, as the service does (E.1, `pnpm check:state`), and the runbook pages read a runbook with no note as one that keeps none and one with no progress at none (E.11, ADR-007's note of E.11); a new reader of the three reads them the same way | alpha 2.2, E.1 and E.11 | `a471f92`, `ec90d5a` |
| `store.adoptRunbookDraft` wrote the store's hand-kept `Runbook` from the generated `RunbookDraft` under one type assertion. The store's runbooks are the generated `Runbook`: a draft's predictions and measures enter as the service wrote them, with no assertion, and `pnpm check:state` holds each null and each field left out and the lock taken over them (ADR-007's note of E.11) | alpha 2.2, E.11 | `ec90d5a` |
| A runbook a page promoted from a research runbook (`store.promoteRunbook`) or opened to revise a locked one (`store.supersedeRunbook`) stayed the page's alone, under an id `nextId` starts again on a reload, so the next load of the project dropped it, a person's revision of a locked runbook among them (found at E.10). Each takes an id that holds across reloads (`timeId`) and joins the runbooks the page sends to the project, and `pnpm check:state` holds both | alpha 2.2, E.11 | `ec90d5a` |
| The project state's three routes answered the rows in a dict with no model; `GET /api/state` answers a `ProjectState`, each row read as its kind's model and served as kept, `PUT` a `StateKept` and `DELETE` a `StateTakenBack`, and `core/tests/test_route_models.py` keeps no waiting set | alpha 2.2, E.0b | `c34c8c9` |
| `openferment.records` (migration 0001, §7.4) was written by no code; each decision `biorepo.write` keeps now writes the record as it leaves it as the next version of its row, and an undo the candidate as extracted (`biorepo.versions`) | alpha 2.1, D.2 (the owner's §6 chose to write it) | `ae603d3` |
| fermOS's, pureOS's and Proforma's run requests take typed quantities with their origins, and their runs are rows of the engines `kinetics`, `train` and `biosteam`; every door of Proforma takes `inputs` (`?inputs=` on the binding and the ceiling check), and the library's door takes them on the biosteam engine's own path. Two shapes keep the resolvers' `Override` form, left by decision (below) | alpha 2.2, C.2, C.3 and C.4 | `0ad02c9`, `a4a739f`, `17c5197` |
| The train engine's `rests_on` names the project's depositions, which a train's value set to a reading is looked up in, and the completeness test's project holds a measured value, so the test fails when the copy leaves the depositions out | alpha 2.2, C.5 | `fd17f32` |
| pureOS → Train read a Proforma run and a train run alone, and a library run, which the Builder's run choosers offer, opened no train page. pureOS reads a library run as a train, keyed by the study scenario its runs row names, else by its own id (`pureos.library_scenarios`, `pureos.TABLE_RUNS`; `test_pureos.py`), and the train page links a study scenario to Studies | alpha 2.2, H.0 | `744e32e` |
| Studies' run card named a kinetics forecast's or vessel's configurations by their bare artifact ids. A thing may title its configurations (`EngineThing.configurationTitles`, optional: words by configuration name, `{}` when the engine gives none, in no run's basis or id); the kinetics engine titles each with the kind of artifact it names and when the project kept it, and the card reads each by its title beside its name, on its chooser and on the line for the run it made (`lib/studies.offeredConfigurations`, `lib/pureos.ranWhat`, held by `check:state`); the mirror, which gives none, conforms as it did (ADR-015's note of E.18; Departures, E.18) | alpha 2.2, E.18 | `09e95dd` |
| The screens' words gave this browser, or a session, rows the service keeps: eighteen sentences under `src/`, as `pnpm check:state` named them before E.19 changed them (the commit's diff keeps their words). Postdoc's empty list says the service keeps each conversation with the project, as it has since alpha 2.0's stage 6.1; pureOS's Builder says Save keeps a train with the project, and a run whose train the Builder lacks says a model or a tool built it; Guild names the project's ledger as the page last read it, and Settings the lesson catalogue; the review queue, Witness, Intake, the protocol compare and the lesson embeds name the project's records, decisions, gold set and versions; and a review decision made while the service is away says it waits in this browser and is sent when the project next loads with the service answering. `pnpm check:state` holds every sentence under `src/` to ADR-014, and `pnpm smoke` reads Postdoc's list on the screen (ADR-014's note of E.19) | alpha 2.2, E.19 | `b70fa83` |
| The shelf's hand-written reference entries (`cornstover_benchmark`, `corn_drygrind`) retired; the reference run and its screen read the library shelf's `cornstover` and `corn`, and the runs a person kept from the entries replay through `workers/kept_references.py` (ADR-004's note) | alpha 2.2, C.6 | `f5405f8` |
| Small handler mismatches the worker op reference found (4.4): `train_spec.py` sent `train_run` a `product` its handler reads nowhere; `grid` and `montecarlo` left out the `structure` that `evaluate` and `run` pass on; an unknown flowsheet's refusal arrived quoted; an unknown catalogue type raised `CatalogueUnknown`. Each is fixed with a test (D11), and `docs/api/workers.md` follows | alpha 2.2, C.1 | `0c49630` |
| Proforma's screens offered no reading for a Proforma scenario's value, and the panel's path sent a measurement override in its parameter's unit (`params.inputsOf`, `proforma.inputs_of`), which the lookup refuses unless the reading is in that unit. A Proforma scenario's panel row lists, on asking, the readings deposited at the bench its parameter may take, and keeps a chosen one as the scope's override in the reading's own value and unit (`Override.unit`), its depositor and the time it was taken; both senders send what the row holds, and the lookup sets the reading in the parameter's unit at each door, the conversion stated in the value's note (ADR-006's note of E.17) | alpha 2.2, E.17 | `7e178bb` |
| A review decision's provenance was the label the browser sent; `biorepo.provenance_of` computes it from the decision (ADR-006) | alpha 2.0, 8.5 | `b9ba0d2` |
| The evidence pool put an accepted candidate in front of Postdoc as `unverified`, and Home listed it as awaiting review; the pool applies the standing decisions | alpha 2.0, 8.5 | `b9ba0d2` |
| Dead service paths the deletions left (Proforma's yield cap, the store branches in fermOS and Proforma, `_example`, the check:seed entry points, `ProjectionMissing`); kinetics' and the hashed texts stay (left by decision, below) | alpha 2.0, 8.5 | `e738506` |
| `src/data/nav.ts` called the rail "THE TWELVE" and exported `ELEVEN`; it exports `DESTINATIONS` | alpha 2.0, 8.5 | `74d5e66` |
| The held scenarios were the seed's, so Postdoc's `selling_price` and `run_flowsheet`, the params scope and pureOS's naming saw none of a project's scenarios; they read the project's rows | alpha 2.0, 8.5 | `5287542` |
| The client's review path kept alpha 1.0's curated-record machinery (the extractor's best candidate beside a curated record, the span carried on promotion) and its committed file's rule that a decision needs a PMCID, DOI or PMID | alpha 2.0, 8.5 | `5287542` |
| `pnpm smoke` opened the rail entries and checked nothing more; the walk (`scripts/walk.ts`, proof step 9) goes through a project on the real service | alpha 2.0, stage 7 | `b00721f` |
| Both MCP servers connect at a session's start and answer over stdio (the Log, stage 8.4, after the pull request) | alpha 2.0, 8.4 | `2d488fb`, `85c7a26` |

### Open

| Debt | Paid by |
|---|---|
| The retrieval lanes that ask a model, over the Ethanol project's own corpus: the concept graph (at most 2.3239 USD on `claude-haiku-5-5` by the dry run), `full_deep`, `no_graph` and `no_hyde`, the judge's grading, and the answer lane that `explain`'s default rests on (ADR-008, Implementations 17 and 18). Alpha 1.0 owed them as its paid lanes (Live owed, §4.5) | stage F's live run, once the account answers (Blockers): `pnpm lit:graph --project ethanol --by <name>`, then `pnpm lit:report --project ethanol --by <name> --judge --render` |
| The host scripts' PostgreSQL steps (`ensure_database`, the migration in `deploy.sh`, the nightly's settings and its dump) have run as `bash -n`, under ShellCheck 0.11.0 and against stand-ins for Homebrew and the PostgreSQL tools on Linux's bash 5 (stage G and the close review; `core/tests/test_host.py`): the scripts were read against macOS's bash 3.2 and BSD tools, and the owner's first install runs them | the owner's first install on the Mini, once alpha 2.2 is merged into `main` (Blockers) |
| `pnpm db:up` (compose.yaml, `pgvector/pgvector:pg17`) has never run here: this container has no Docker daemon; CI runs the same image as a service | its first run on a machine with Docker, the owner's |
| Component tests on fixtures recorded from the real service (`pnpm record:fixtures`, alpha 2.0 prompt §9.3) are unbuilt; the walk and the smoke run against the real service | a stage after alpha 2.2 that builds `pnpm record:fixtures` |
| No offline test computes on a published genome-scale model (Yeast9 and iMM904 need their fetched files, caches kept outside git; Departures, §5.5 stage 2); a model add-on applied in the worker, and a metabolite-defined product's demand through the worker, are untested | a test under the marker `slow` or `live`, on a host that holds the fetched files |
| Two concept-graph builds at once (`pnpm lit:graph` for two projects that share a document) can each send a batch of a shared passage to the model before either stamps it, and pay for that batch twice; `GRAPH_LOCK` keeps the graph whole, and the spend is the same as two builds run one after the other with no stamp between them (found by the review of the graph lock, 11 November 2026) | a build that reads the stamps again inside the lock before it asks the model, or one build at a time for the instance |
| Two pages owing one row send it each on its own: a copy a loading page took at load, a tab's own queue, or what a closing tab left (`foldParting`) can reach the service after another page's later write of the row, and a row the service keeps whole (a scenario, a train, a runbook, a scenario's fits) then takes the older copy (found by the reviews of the H7-01 fix, 11 November 2026; ADR-014's note). A scope's overrides are laid on key by key since group 3 (H7-04), so an older copy of one changes its own keys alone and a key changed since is refused in words; two copies of one write that added a key still land twice, and the second puts back a key taken back between them (found by the review of the H7-04 fix, 12 November 2026) | a write that carries an id of its own, which the service keeps and answers a second time as kept, for every kind; and a write that names the version of the row it read, refused in words when the row changed since, for each kind the service keeps whole |
| `units.json` maps `wt%` and `% (w/w)` to `% CDW`, aliases written for the PHA program; changing them changes how a stored record converts | the vocabulary review, after alpha 2.2, with a migration for the records it converts |
| RunbookDetail's held-for-review panel keeps words of Dominion's era: candidates near a claimed identity band, a ruling with legal consequences, and two rulings (a boundary accepted as mapped; candidates excluded pending counsel) that `store.resolveRunbookReview` writes into the held stage, with a boundary map among the runbook's outputs. No code in this build sets a runbook held for review, so the panel answers only a row kept in that state | the stage that lets a runbook be held for review, with that state's own words and rulings |
| `fermos.forecast_run` keeps `duration_h`, a length the calling code sets as its own convention, which the tests and their stand-ins pass (`standins.py`, `test_fermos.py`, `test_fermos_3r.py`, `test_proforma_fermos.py`, `test_proforma_ceiling.py`); the routes, the tools and the engine set a forecast's length as a typed `t_end` | the change that has those tests set a typed `t_end`, or reach `fermos.forecast()` through a helper of their own |
| The service holds a reading's unit to its parameter's alone: a runbook's measure names no parameter it may set, so a scenario may set any parameter in a unit that converts to any reading (the proof's walk pairs a placeholder by unit) | a later pass that ties a runbook's measure to the parameters it may set (ADR-016) |
| A ProcessModel plant runs on its default scenario; its scenario fields (cellulosic's feedstock, milk's feed, gas_fermentation's carbon source) are read and kept off the parameters door (stage 4.3 composes the cellulosic plant's pretreatment and fermentation in openFerment's flowsheet) | a stage after alpha 2.2 that offers a plant's scenario fields as its configurations (ADR-004) |
| A second organism's reaction set for the composed flowsheet: the package holds one | a package or a record that gives another |

### Left by decision

| Debt | Recorded at | Decision record | Returns when |
|---|---|---|---|
| `core/tests/standins.py` (39 test files import it) keeps stand-in records on real strain ids, a closed-form ethanol evaluator and `STANDIN_THEORETICAL`, the theoretical yield on glucose; `test_proforma.py` keeps the package's regression values to test the parser (the benchmark price this build once measured left the tree with the retired shelf entries, C.6). A4's `rg` clause finds them | Departures, §5.3 and A4 stage 8 | ADR-010 (the demo infrastructure deleted, its stand-ins kept as test material) | fixtures read from the library plants replace them |
| Postdoc's scripted stand-in model and the test pool speak of PHB, casein and xylose hydrolysate (`test_tools.py`, `test_postdoc_agent.py` and the tests that import their fixtures); §5.3 asks them to speak of library plants and the kit's demo corpus. The words are test material, and their values stay in the tests; H.0 gave placeholders the PHB-era words in comments and the tests it touched | Departures, §5.2 (the fixtures that stand) | ADR-010 | with the stand-ins above |
| pureOS's chemical-set key is called `program` (`TrainSpec.program` in `core/openferment_core/models.py`, and `FlowsheetInfo`, `Train`, `TrainSummary`, `TrainProposal`); kept trains and train runs validate on that name, and its texts ("the yeast program's chemicals", `PROGRAM_CHEMICALS`, `fermos.NAMED_NOTE`'s "program filter", the kinetics settings' notes, the shelf's description and price basis of `custom_train_v1`) are hashed into artifact ids, so renaming them shifts the id of every new train run and composite run. The refusals and descriptions of pureOS, the vessel and the shelf say "the yeast program" beside the key, and fermOS's note on every fit's deposition input ("the readings as the browser sent them; the service cannot see the deposition itself"), hashed the same way, is untrue since stage 2. The screens say "chemical set", and the shelf's comment does | the Log, stage H.0 ("Kept, with the reason"); Departures, alpha 2.2 D1 C.1 (the pins) | ADR-005 (projects replace programs; this key names a chemical set) and ADR-015 (a run's id is its engine's own artifact id) | one stage renames the key with a before-validator for stored rows and accepts the id shift |
| `proforma._strain_labels`' per-program species map serves the vessel's organism check; with no catalogue it is empty in production, and its two notes are hashed into vessel designs | as the `program` key | ADR-005 and ADR-015 | with the `program` key |
| `kinetics.py` keeps the storage machinery of the deleted `storage_v1` family (the N and Q states, `Mode.storing`, the N event, the Storage group); no family sets `has_N` or `has_Q`, so none of it runs. Dropping the state slots changes LSODA's finite-difference Jacobian, which a replay compares exactly | `CLAUDE.md`, Mission and scope (§11.5 keeps the kinetics families as they are) | ADR-015 (`kinetics` wraps fermOS as fermOS computes, its trajectories held bit for bit) | the next change to the kinetics families, with every family's trajectories held bit for bit |
| Words stored in bases that a run's page shows: decision tags (`(D5)`, `(D9)`, `D8: …`, `(OF-BLD-020 §3.2 …)`, `(Appendix 2 §A)`, `(CARBON_RULE)`) and a doubled word in a train's input name and note (`T701 outlet outlet`, a port named `outlet` after the word). A page drops the tags as it shows a note (`lib/proforma.plainNote`: the run's page, the parameter panel's notes, bounds and sources, fermOS's fit, simulation and vessel notes, a figure's basis), and the CSV keeps the words whole; editing them moves the pinned ids, and at H.0's second sweep a changed `kinetics.ZERO_SAID` moved `fermos.simulation batch_v1`'s id. The notes no basis hashes say their words alone since that sweep. H.0 found three more: the precision convention's note a library run's basis carries (`engine/library.py`: "…and a replay compares the plant", its sentence unfinished, the chip on the artifact page now wrapping), and two flowsheet descriptions a Proforma run's basis carries as its `flowsheet` note (`flowsheets/shelf.py`: "no number is the flowsheet's" and "The train's own inlet is not an input"); the screens' own words, which no basis hashes, were restated | the Log, stage H.0 (the second list, notes a basis hashes); Departures, alpha 2.2 D1 C.1 | ADR-015 | the next change that may move ids: a train spec version, or a basis version of each tool |
| A library run's TEA breakdown is read at the product's set price (`workers/library_plants.py` `_Module.parts` passes no price), and a flowsheet's run reads it at the price it solved; where a library run's overrides move the solved price, the lines sum to the set price. The cost card draws the lines' own price as its last row and says the solved price beside it (`CostWaterfall.priceNote`, H.0). The same run's price block keeps the IRR's unit blank (`PRICE_UNITS`); its evidence names it `fraction` (`tools/engine.py` `BLANK_UNITS`). Either change to the run's output moves its tables or its output hash under `library run 2`, so a kept run would replay differently with nothing to say why | the Log, stage H.0 (the cost card) | ADR-004 (one adapter, each plant built fresh, a kept run replayed) | the next `library run` version, which moves every library run's id |
| A train's own carried values (`TrainParam`) keep the resolvers' `Override` shape, a bare value with no unit, and the project's stored panel overrides (`PUT /api/state/overrides/{scope}`) keep it for a person's value and a model's estimate, a deposition's reading keeping its own value and unit since E.17 (`Override.unit`): a saved train cannot hold a measurement, and a value a person typed into a train is checked against its parameter's unit only as its parameter's own | Departures, alpha 2.2 D2 C.7 and D2 E.17 | ADR-006 (typed quantities with origins) and ADR-014 (the Durable snapshot's pending writes) | a train spec version that moves the train runs' ids, its values typed quantities with their origins; and accounts giving the Durable snapshot's pending writes a home on the service |
| Conformance check 7 holds a hand-written engine (the core's three) to a refusal before any run alone | Departures, alpha 2.2 §6.1 C.7 | ADR-015 | a probe a hand-written engine declares, a request its own computation refuses, which check 7 asks twice: a kinetics family run whose integration refuses, a train the Proforma worker refuses, a scenario flowsheet's value past its bound |
| A contract engine's run whose SFF step failed (a worker that crashed or broke the protocol in `sff_export`) keeps its artifact and no row, and the next ask keeps the row from that artifact with no diagnostics, since nothing computed for it (`runs.run_engine`) | Departures, alpha 2.2 D0.1 D.0 | ADR-015 | an engine's diagnostics must outlive a failed file step: kept beside the artifact, or the row kept before the file |
| A kept train (pureOS's, `pureos/kept.py`) is changed by any caller of the model's lane, an outside assistant's through MCP or the tool door's header among them, and keeps `madeBy` and its row's `created_by` as the model that made it; the audit row of each change names who changed it and its door (`detail.via`). A catalogue entry stays its keeper's by name and door | Departures, alpha 2.2 D.0 (D0.4, B11) | ADR-008 (Postdoc's lane and the outside assistants') | a kept train is to stay its maker's: the catalogue's rule of name and door applied to `kept.keep_train` |
| An outside assistant names itself (MCP's `clientInfo`, the tool door's header), so one assistant may declare another's name and act in that name's lane, and a name past 200 characters is cut, two such names reading as one; the door tells Postdoc's loop from every outside assistant | Departures, alpha 2.2 D.0 (M, B1, B5) | ADR-005 (accounts wait as a membership stub) | accounts, when a caller is known by more than the name it declares |
| A train run's SFF file: a train carries no TEA, and the schema the toolkit ships at `e236e32` requires every file's `metadata.TEA_year`, which its exporter reads from the system's TEA, so the Proforma worker refuses every train run's file before building it and the run keeps the words as `sffRefused`; the Flowsheets screen lists no record for a train run | Departures, alpha 2.2 D5 C.3 (every train run keeps `sffRefused`) | ADR-003 (the toolkit vendored unmodified) | the toolkit's schema leaves the TEA year to a file whose system no TEA prices and its exporter writes one (an upstream change to `export/_export.py` and `sff_schema.json`, offered with the writer's adaptation), or a train carries a TEA of its own |
| The proof's train (`scripts/prove.py`, `make_train`) is the tail of the train read from step 4's corn stover run: at these pins the four units from T701 on, none a separation, each passing the whole of the product on, so `conform train` in the proof exercises no distillation and no sieve | Departures, alpha 2.2 D5 C.3 (the proof's train) | ADR-015 | a train read from a library run binds its units' values from the run's own read-back parameters, or from a `readFrom` of a library plant's unit (D8, C.6), so the proof's train keeps the distillation and the sieve |
| What the library path cannot give yet of the retired reference entries: the benchmark's price per gallon (a library run prices its product per kilogram, and the package's own ethanol density per gallon waits for a library run to read it), and a Graphviz drawing of a library plant (a library run draws none; its SFF file's graph draws the plant on the run's page, and the run's Diagram card says so). A run kept from a retired entry has no runs row (no backfill, D3), so it has no run page: the plant's reference page lists it with its checks, Proforma's module rows list it, selling_price and stream_table cite its price, and BioRepo's page shows it whole | Departures, alpha 2.2 D8 C.6 | ADR-004 (its note of C.6) | a library run reads a plant's own per-gallon density, and draws its plant where Graphviz is on the host |
| A comparison of library runs alone (`study comparison 1`) of two plants gives a run whose plant lacks a value another run set a `library-default` cell, its value and unit null; version 2 (a comparison that holds a run of another engine) names a default only where the plant declares one | Departures, alpha 2.2 D3 C.1 (`study.comparison` reads its version from the runs it compares) | ADR-015 (every run one shape, a comparison reading `outputs.values`) | the next change to `comparisons._set_values`' default cells, with a version for the comparisons it moves (C.5 gave a reading's own cell its `ref`, which moves no comparison kept before it) |
| Two devices writing one deposition: a page that lacks the entries another device appended writes a deposition the service refuses as leaving them out, and the page's own new entries go with the refused write, said in words | Departures, alpha 2.2 D7 C.5 (the service keeps a deposition the bench's way) | ADR-014 | accounts give pending writes a home on the service |
| `test_biorepo.py::test_the_committed_file_is_the_model_and_starts_empty` holds the shape of a tracked file nothing reads | Departures, §5.5 stage 2 (`core/data/biorepo.json` stays tracked) | ADR-001 (the one store) | `core/data/biorepo.json` leaves git, once the owner says the live instance's import read right (Blockers) |

## Live owed (folded from `docs/history/STATE-2026-10-21.md` at stage 8)

The two LIVE steps alpha 1.0 still owed, each judged against this build:

| Owed at alpha 1.0 | Now |
|---|---|
| §4.5, the paid lanes of the retrieval evaluation (`pnpm rag:eval && pnpm data:push`), waiting on a helper model the safety classifier lets through | Retired with their code: the bespoke retrieval stack and the data branch are deleted (§5.4, §5.5; ADR-010). Its successors: `pnpm lit:report` runs the kit's demo offline, and `pnpm lit:report --project <id>` (alpha 2.2 F.5.4) runs a project's lanes, the graph and HyDE among them and the judge with `--judge`; its live run is a Known debts row above |
| §10.3, the saved answer (`pnpm demo:fixtures --real && pnpm data:push`): a real Postdoc answer, its artifacts and the retrieval report saved | Retired with the demo infrastructure (§5.3; ADR-010). A real answer is now a turn of a conversation the service keeps, with its tool calls and the artifacts they made (stage 6); `pnpm prove --live` step 6 keeps two, asked of the routed models |

## Owner questions (execution prompt §13) and the defaults taken

| # | Question | Default taken | Answered |
|---|---|---|---|
| 1 | PostgreSQL as the one database | yes | yes, the default confirmed (2026-11-02) |
| 2 | Kit in-process with a local FastEmbed embedder | yes | yes, the default confirmed (2026-11-02) |
| 3 | Delete thread Q's TypeScript list, keep `docs/corpus/ethanol-sources.txt` | yes | yes, the default confirmed (2026-11-02) |
| 4 | Delete Dominion, return condition recorded | yes | yes, the default confirmed (2026-11-02) |
| 5 | Rename `demo` → `assumed` | yes | yes, the default confirmed (2026-11-02) |
| 6 | Python pin 3.12 if the kit fails on 3.13 | no pin: the kit's suite passed on 3.13.17 (1584 passed, 31 skipped) | yes, the default confirmed (2026-11-02) |
| 7 | Kit REST under `/rag` on the same port | yes, behind `OPENFERMENT_RAG_KEY` | yes, the default confirmed (2026-11-02) |
| 8 | Licence | none added | yes, the default confirmed (2026-11-02) |
| 9 | Accounts: tables and a membership stub only | yes | yes, the default confirmed (2026-11-02) |
| 10 | §11.1, asked at stage 6.3: the per-request key override (§4.8), and keys for a route's non-Anthropic model (read through Sci RAG Kit's settings). Each changes how a key is read | neither built: a route's other-provider model is passed over in words, every key is core/.env's; the design the override would take is in ADR-008, Implementation 6.3 | authorized (2026-11-02) within the alpha 2.1 prompt's §3 rules: a key sent on a request serves that request's calls and is never stored, logged or echoed; built at stage D |
| 11 | Alpha 2.2 C.5: a run resting on a bench reading and on a record weaker than `measured` (or a computed artifact) reads `measured`, as §6.3's rule writes it. Should the label be the weakest of what the run rests on instead? | §6.3's rule as written: `assumed` when any input is a person's assumption or a model's estimate, else `measured` when any input is a measurement, else as before (`basis.basis_provenance`; ADR-006, the C.5 note) | open |
| 12 | Alpha 2.2 C.6: may Postdoc or an MCP client name an address for the service to fetch an SFF file from? Each would widen what the service reaches outbound on a model's word, a stop condition (§11.1) | no: the address is a person's alone (the prompt's §3, "a URL the person names"; D10's amendment at C.6): `POST /api/flowsheets/import-url` is the one door that fetches by address, held to public addresses, and `flowsheet_import` takes a reference file's id alone | open |
| 13 | Alpha 2.2 G: `has_key` (`scripts/host/lib.sh`) reads the key line. May its placeholder pattern take `[[:space:]]` for `\s` (the same set on GNU grep; BSD grep's reading of `\s` is unchecked here), and may it read a quoted or `export` key line as python-dotenv does? Each changes how the key line is read, a stop condition (§11.1) | neither: `has_key` stands as before stage G and reads an unquoted `ANTHROPIC_API_KEY=sk-ant-` line; the example's placeholder line reads the same either way | open |

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
    served the deleted seed. All of them are gone; test_no_seed reads every service module for a
    projection's name, whatever this checkout's disk holds. `anchor_report.py` went with them.
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
    - A second pass over the same screens: counts read "1 passages", "1 records" and "1 claims";
      Postdoc showed raw ISO times to the microsecond (the page now writes ISO as the service does
      and shows `2026-10-31 02:52 UTC`); the review card said "Extracted by claude-1", the extractor
      run's name, as if a model of that name had read the document; a runbook made from an engine
      run drew an empty price distribution ("no sample of this scenario ran"), and it now draws the
      run's cost breakdown as the run page does; the flowsheet graph cut its feeds' names at its
      left edge and laid two names on one unit over each other; pages carried alpha 1.0's "Module
      0 · Evidence" numbering, and empty states and the subsystem map cited OF-BLD documents; an
      id in a page's eyebrow was set in capitals; the reader said "Full text from pasted text" and
      repeated a document's title as a passage heading; a licence class read "unknown" alone; and
      a disclosure laid out as flex lost its marker. Each is fixed in the client.
    - `pnpm prove` stopped its service and dropped its database at the end, and left its data
      directory in `/tmp` after every run, about 870 KB each. It removes the directory when every
      check holds, and keeps it with the service's log when one fails.

### Alpha 2.1 — Stage A — 2026-11-02

- A1. CI was green on #15's head (`724843d`, runs 294 and 295); the owner's §3 authorized the
  merge, and #15 is merged into `main` with a merge commit (`7f990f8`). `claude/alpha-2-1-functional`
  is cut from it. `git push origin alpha-1.0` was refused again, now with HTTP 403 (Blockers).
- A2. PostgreSQL started; `bash scripts/session-start.sh` found `core/.env` and left the key as it
  was; `pnpm db:migrate`; `pnpm ready` green: the key accepted, `claude-opus-5-5` then
  `claude-sonnet-5-5` at effort high, `index` on `claude-haiku-5-5`, the 150 USD cap.
- A3. `core/.env` holds the prompt's §4 table. `OPENFERMENT_ROUTES` has the shape `llm.routes()`
  reads (a family to `models` and `effort`), so `core/.env.example` stands. The session's own
  environment pins `OPENFERMENT_MODEL` and its three kin to Haiku and medium, and the service reads
  `core/.env` with `override=False`; every command of this work runs with those four unset, so the
  file decides (Resume).
  - The first `pnpm verify` failed 19 offline tests (`test_llm`, `test_ready`, `test_spend`,
    `test_writes`, `test_postdoc_agent`, `test_phase3_review`): `core/.env`, loaded at import, laid
    `OPENFERMENT_ROUTES` over the models a test set and gave the budgets 150 and 6. CI has no
    `core/.env`. conftest's autouse fixture, which already cleared the day's budget for a test not
    marked live, clears every routing and budget setting now (`ROUTING_SETTINGS`), and verify is
    green.
  - `pnpm prove` 63 of 63 offline; `pnpm prove --live` 46 of 46 on the Opus routes, 0.6601 USD
    (Last green runs).


### Alpha 2.1 — Stage B — 2026-11-02

The live Ethanol project end to end, on the screens, on Opus (`docs/reports/live-questions-2026-11.md`
holds the numbers, the tables and the judgements).

- B1. The project "Ethanol" made on Home in this container's `openferment_dev`; every identifier
  of `docs/corpus/ethanol-sources.txt` collected through Intake's Identifier form, one at a time:
  22 of 22 held, 814 passages. OSTI reset the connection once and the second try held it. Intake
  had said "Offline" for a service that answered and refused the overlay: `openferment_dev` had
  drifted from migration 0001 (`pnpm db:reset openferment_dev` cured it), and the page now says a
  running service's refusal in its words and asks for the overlay only once a project is open
  (`lib/intake.ts`, `check:state`; `50f014d`).
- B2. Extraction over every held document from Intake's list on the `extract` route (Opus, then
  Sonnet, at medium): 224 kept and 89 refused, 4.53 USD; Opus declined ten of the 22 papers in the
  `bio` refusal category and Sonnet answered each. The anchoring rule refused a mean with its
  spread and a range written whole, and the unit table held no `% w/v`; both fixed (`21306e1`),
  and the nine documents extracted again kept 103 where they had kept 55 (1.80 USD). Intake's list
  now says what a document's kept extraction found and offers Extract again. 272 candidates wait
  for the owner; no decision was made here.
- B3. The twelve questions asked through the Postdoc screen: five of twelve as expected at first
  (4.54 USD). Fixed with tests (`fb03eb2`): ordinals and labels named in the plan prompt; the loop's
  bounds raised to 10 rounds, 24 tool calls and 360 s (ADR-008, Implementation 9); a run's TEA
  lines and the values it read back, each with its origin, as evidence ids; drafts of a plant's
  run with no product or strain; and `flowsheet_library`, `flowsheet_import` and `flowsheet_read`
  (46 tools). Asked again, eleven of twelve (5.01 USD); then fixed (`c007456`): a turn's ceiling
  sized to the question's budget between 8,000 and 32,000 tokens, the rate-of-mass units and
  `kg kg⁻¹`, and fractions in the prompt; asked a third time for those three (1.60 USD). Eleven of
  twelve as expected, Q1 as expected in kind and short in coverage.
- B4. The owner's plant work from the screens (`422e617`). The screens could not run a plant, make
  a scenario of a person's own, import an SFF file or list the project's SFF records; Studies' Run
  a plant, a run's page's A scenario from this run, and Flowsheets now do, on the generated types.
  Every plant the package built here ran, and the composed flowsheet in dilute acid and hot water
  with IB and SCF; a glucose-only scenario of the person's assumptions ran; two comparisons, a
  runbook locked, the export downloaded, a run's SFF file from it imported and a reference file
  kept; after a restart every one read back as it was, with no console error.
- B5. Found for the owner, the package's and not openFerment's: biorefineries 2.35.1 builds hot-water
  pretreatment with dilute acid's `PretreatmentReactorSystem` and its reaction conversions, at
  another temperature, so the pretreatment comparison rests on dilute acid's conversions (Postdoc's
  answer to Q7 found it; the package's code confirms it).

### Alpha 2.1 — Stage C — 2026-11-02 (held)

- C1. The evaluation set gained the owner's twelve as the suite `ethanol`, runs tagged by route
  table and timed, and a judge on the `judge` route that reads each answer with what each claim
  cites and scores answers, grounded, labelled and coverage, each judgement labelled with its
  model; a judge that declines leaves no score and says why (`2161189`; `docs/api/postdoc.md`).
- C2. The three tables (Haiku alone, Sonnet alone, and `core/.env`'s Opus then Sonnet, each at
  effort high, judged by Opus) ran in parallel in the Ethanol project. At 20:01 UTC the Anthropic
  account's own usage limit refused every call: eight answers were kept (Haiku Q1 to Q4, Sonnet Q1
  to Q3, Opus Q1), five judged; the Opus judge declined two of Haiku's in the `bio` category
  (`docs/reports/model-routing-2026-11.md`; Blockers). The routing defaults stay as they are until
  the comparison finishes. 2.10 USD over 72 calls.
- C3. The service called the limit's 400 "refused the request as malformed"; `llm` now names an
  account past its usage limit in words, with the date the API gives and who can raise it
  (`UsageLimitReached`; `test_llm.py`). `pnpm ready` checks the key by listing models, which an
  account past its limit still answers, so it cannot see the limit before a call.

### Alpha 2.1 — Stage D — 2026-11-02 (in progress)

- D.2 `openferment.records` written from `biorepo.write`: each decision leaves the record as the
  next version of its row, an undo the candidate as extracted (`ae603d3`; `test_biorepo.py`).
- D.4 The key a request names (`fa9782e`, `f957fd0`; ADR-008, Implementation 10): the
  `X-OpenFerment-Key` header, read after the guard; `llm.request_key` serves openFerment's calls
  and the kit's, and the threads a request starts; the audit row says an override was used; the
  negative test finds the key in no log line, response or row of either schema.
- D.4 A local model behind an OpenAI-compatible endpoint (`53c123c`; ADR-008, Implementation 11):
  `OPENFERMENT_LOCAL_BASE_URL` serves `openai-compatible:<model>` in single calls through the kit's
  adapter (its `openai` extra, Apache-2.0, now locked); Postdoc's loop passes it over in words.
- D.1 The catalogues as project stores (`a0c33bb`): the `catalogue` table (migration 0007) of
  strains, products, skills and lessons, read by the proposer, ProtParam, Guild and the module
  reads; `GET`/`POST /api/catalogues/{kind}`, `POST /api/intake/catalogue` for a JSON or CSV file,
  and `catalogue_read` and `catalogue_write` (48 tools). The protocol steps' skills and a
  catalogue screen are still open.
- D.6 The stream table of a kept scenario's run has its test again (`test_tools.py`).
- Departure: debts 2 and 4 were paid before debt 1, the catalogues, because every live step after
  them waits on the account's usage limit and these two needed no model call; the catalogues,
  Quantity runs (3), the screens on the generated types (5) and the small debts (6) follow in
  order, and the retrieval lanes (7) wait on the limit.

### Alpha 2.1 — Stage E — 2026-11-02

- E1. This session runs in a Linux container, so the live host is written up and not installed:
  `docs/runbooks/live-host-install.md`, from the host scripts as they stand: what the Mini needs,
  the key and the account's own limit, `core/.env`, `scripts/host/install.sh` (the database, the
  two LaunchDaemons, the power settings, `tailscale serve`), `pnpm ready`, alpha 1.0's records,
  the first project, and what `deploy.sh` does after. None of it has run on macOS.

### Alpha 2.1 — Stage F — 2026-11-02

- F1. `pnpm verify` green on all sixteen stages and `pnpm prove` 66 of 66 offline on `32b95f1`
  (Last green runs); pull request #16 to `main` with the §9 completion report.
- F2. CI's push run of `b6dccdb` failed `test:sim` on A→B→A: A again's capital numbers came back
  one unit in the last place from A's (the NPV 1.5e-15 relative), where the test held seventeen
  digits equal; the pull-request run of the same commit passed. BioSTEAM sums its units'
  installed costs over a set, in the set's order; the test now holds A again within one part in
  10¹² of A, about 700 times the drift CI saw and 2,000 times or more below what a plant that
  keeps its recycles moves (ADR-004, alpha 2.1).
- F3. The Postdoc screen held the 30 newest conversations (`MAX_LIVE_CONVERSATIONS`, from alpha 1.0,
  when the browser kept them), though `GET /api/state` returns every one. Stage C's 31 evaluation
  runs were all newer than stage B's answers, so the Ethanol project's answers were out of reach and
  a link to one opened an empty pane. The page now holds every conversation the service keeps
  (`projectState.conversationsHeld`; `check:state` holds a project of 51); the browser's snapshot
  keeps no conversation, so nothing grows there.

### Alpha 2.2 — Stage A — 2026-11-02

- A1. #16 merged into `main` with a merge commit (`112eb8b`, CI green on its head `fa1b744`) and
  `claude/alpha-2-2-base` cut from it. The tag `alpha-2.1` was made beside `alpha-1.0`, and the push
  of both was refused once more (HTTP 403 from the session's relay); the commands are in Blockers.
- A2. `core/.env` set to the prompt's §4: effort max on `plan` and `judge`, `explain` and `extract`
  at high, Sonnet behind Opus in every answering family, `index` on Haiku at low, an ask's budget
  of 8 USD. `llm.routes()` reads the table as written and `llm.PRICES` prices every model it names.
  This session's environment sets `ANTHROPIC_BASE_URL` to `https://api.anthropic.com`, so the
  service's calls reach the account behind the key. `pnpm ready` green.
- A3. `pnpm verify` green on all sixteen stages, and `pnpm prove` 66 of 66 offline (Last green runs).
- A4. `pnpm ready --probe` (`ready.check_probe`): one call of a few tokens on the index route, the
  one row that sees the account's own usage limit, since an account past it still answers the free
  Models API the model row asks. A refused probe names the API's date and sets the lane to `none`
  (`test_ready.py`). Run once at 23:50 UTC: `claude-haiku-5-5` answered, 18 tokens in and 4 out,
  0.000004 USD. The plan keeps every stage, F after E.


### Alpha 2.2 — Stage B — 2026-11-03

- B.1. `docs/api/engines.md`, the contract a stranger builds from: what an engine is (one object
  registered under the entry-point group `openferment.engines`), what it declares (`name`,
  `worker`, `heavy`, `version()`, `things()`, `parameters()`, `run()`, `replay()`, `export_sff()`),
  the shapes `EngineThing` (the fields `GET /api/library` answers for a plant, with a precision),
  `EngineParameter` (a `ParameterSpec` with its default and the default's origin) and
  `EngineInput`, the worker (started with no key, token, password or database address in its
  environment; `serve`; `Refused`), `WorkerEngine` over four ops, what the service does with an
  engine, the eight conformance checks and what is deliberately absent. Every example value is a
  placeholder in a placeholder unit. `docs/api/workers.md` gains the engine ops and the sample
  worker.
- B.2. ADR-015 (entry points, over a class hierarchy in the core or a configuration file). The
  `Engine` protocol in `engine/__init__.py`; `engine/contract.py` (`WorkerEngine`, the version
  string every run is keyed by); `engine/registry.py` (each entry point loaded once; a load error,
  a name that differs from its entry point's, a missing method, heavy modules with no worker, or
  two packages claiming one name, each said in words while the service runs on); `GET
  /api/engines`, `GET /api/engines/{name}/parameters`, `POST /api/engines/{name}/run`; migration
  0008 (`runs.engine`, stored rows read `biosteam`; 61aaeda) and 0009 (`engine_checks`, each
  engine's last verdict); `GET /api/runs?engine=`; the Runs screen's engine column and filter, and
  Studies' run card offering every usable engine's things; the four engine tools take `engine`
  (48 tools still); `pnpm ready` a row per engine; `engine/runs.py` `run_engine` keeps a contract
  engine's run as one row (a value set checked against its parameter's key, unit, kind, choices
  and bounds; a refusal a receipt; the SFF file validated in the Proforma worker or the engine's
  words kept); `engine/conform.py`, the eight checks on a scratch database with the verdict kept.
  The contract's own sample engine (`engine/sample.py` over `workers/sample_worker.py`, which no
  entry point registers) carries `test_engines.py` (22 tests). An engine's worker starts with
  every key, token, password and database address withheld (`workers.withheld`); the four kit
  settings the package writes on import are its own constants (`literature.KIT_SETTINGS`).
- B.3. `biosteam` registered by `core/pyproject.toml`'s entry point (`engine/biosteam.py` over
  `library.py` and `runs.run`), every number and test as before. `python -m
  openferment_core.engine.conform biosteam` holds all eight in 46 s: 1833 parameters of nine
  things, each with its origin; a run of `cane` asked twice is one row, identical on replay, its
  SFF file valid and scored 0.803; a bare number refused before the worker; a thing it lacks
  refused in words; `created_by` the asker. `test_engines_sim.py` (3 tests) runs it on the real
  worker. Proof step 10 lists every registered engine, makes the eight checks on each and reads
  the verdict back: 9 of 9 checks in 94 s with steps 1 and 2.
- B.4. `docs/BASE.md`'s first draft (6e13f55), brought to the contract.
- B.5. The defects the stage's design reader measured in the contract as first written, each
  fixed with a test: `from openferment_core.engine import WorkerEngine`, the page's own line,
  failed (the package now exports it lazily, and a test runs every import line and validates every
  example on the page); a stray number beside a run request's fields, a field a quantity or its
  origin does not name, and a value of `true` were accepted (now 422s, and check 1 sends a stray
  number too); a contract engine's run could not be replayed on a service just started (the
  registry is read at startup and before every replay, and the nightly's registrars read it);
  `biosteam` advertised a default configuration its run refused (a plant asked with none runs in
  its default); a value set with no `at` was stamped by one path and left unstamped by the other
  (both write it as a library override is, the day of the request); a crash of the worker
  checking a run's SFF file was kept as a permanent `sffRefused` (raised, as a library run's is);
  a package registering `biosteam` would have set the core's own engine aside (the core's keeps
  its name); `engine_report`'s `engine` defaulted to empty where §6.1 has `biosteam` (checked only
  when named). Check 3 now holds the run's id to its basis's artifact id, check 7 asks a
  `WorkerEngine`'s worker to refuse too, check 8 makes a second run in a model's name, and the
  command takes `--thing` and `--inputs`. `test_boundaries.py` reads every registered engine's own
  package for a heavy import outside its worker.
- B.5, for stage D. The MCP server marks a client's writes and typed numbers with the name it
  declares when it connects (`clientInfo`, written `<name>/<version>`; `mcp_server.caller`), and
  `an assistant over MCP` when it declares none or only the SDK's default; a catalogue entry a
  client keeps says it came over MCP, where it said Postdoc. `docs/TOOLS.md` had no section for
  the catalogue and flowsheet tools (their families were missing from `tools/reference.py`); it
  has both, and the page refuses to render with a family it places nowhere.
- B.6. The sixteen defects the stage's critic found in the contract after B.5, each fixed with a
  test (`test_engines.py` holds 82):
  - BioSTEAM checks a value's unit before its plant is built, through the one checker every
    engine's values pass (`runs.check_inputs`); a plant's bounds stay the library's, flagged on the
    run's parameters as `outOfBounds`.
  - A value set on a contract engine's run carries the day it was set (`origin.at`, required), and
    the service stamps no day of its own.
  - Discovery runs on past an entry module that exits as it is imported, whose declaration
    raises, which asks the registry while it is imported, or which brings its worker module, a
    heavy module it declares or one of `workers.WORKER_LIBRARIES` into the service's process; each
    is listed with its words, and the service starts when the group itself cannot be read.
  - A worker that answers outside the protocol (a key missing, a name repeated, blank or too long,
    a number NaN or infinite, a `things` or `parameters` answer of the wrong shape) raises
    `EngineBroken`: nothing is kept, the routes answer 503 in words and the job says it failed.
  - Check 7 holds a refusal to one call of the worker's `run` op and its receipt; check 8 makes
    its model's run through the tool door.
  - A thing that must name a configuration is checked in its first and refused with none, and
    every door resolves a thing's configuration as a run does (`runs.thing_of`).
  - Every contract engine's tool version begins with `engine run 1` (`contract.CONTRACT_RUN`).
  - A `WorkerEngine`'s things are asked once, a cold worker given 30 s on the listing.
  - The nightly holds a replay within its stated precision and says so.
  - A run whose SFF step fails says its job failed and keeps no row.
  - Migration 0008 takes a body's engine name on an upgrade after a downgrade.
  - The engine routes declare their 404, 422 and 503 answers in the OpenAPI document.
  - Proforma's run page shows a run's `outputs.values`.
- B.6, the review round. Three reviewers read the fixes: one built a stranger's engine from the
  four contract pages alone, one looked for regressions, one for boundaries. They found 29 more,
  all confirmed and fixed. Four change behaviour beyond the engine package:
  - Every worker process starts through `workers.LAUNCH` (`python -c LAUNCH <module>`), which
    points descriptor 1 at stderr before the worker module is imported, so a library that prints
    as it is imported, from Python or from C, leaves every response whole (`test_workers.py`).
  - A tool that writes, called at `POST /api/tools/{name}`, runs only for the person `?by=` names
    (a 422 in words with none), and its audit row, its proposal and what it keeps are marked as
    that person's, where they were marked as the chain's first model. pureOS's kept trains hold a
    model's work alone and refuse a person's write in their own words, as they do at every door.
    No screen calls this endpoint.
  - A replay whose tool version moved names it as its first difference, an identical output
    included, and BioRepo's artifact page says which version kept it and which replayed it.
  - `Quantity`, `ScenarioValue` and `ReviewDecision` are each one schema in `openapi.json`: their
    serializer's return annotation had made empty `-Output` twins.
  - `docs/api/engines.md` states the run id's recipe (recomputed from the page alone), the limits
    on names (an engine's 40 characters, a configuration's 80), the reinstall and restart a new
    version needs, and the launcher.

### Alpha 2.2 — Stage C — 2026-11-03

- C.1. The pins, the handler mismatches and one row shape.
  - `core/tests/test_engine_pins.py` holds sixteen computations stage C carries to their artifact
    id and output hash, captured at `ed33c02` before a line moved: fermOS's three simulating
    families, a kinetic fit and two growth forecasts, a vessel design, a train run, a Proforma
    run, library runs, comparisons of them and a run of the contract's sample engine. Each is
    built on the existing tests' stand-ins. Output hashes are checked under one fixed CPU dispatch
    in a process of their own (Departures, D1).
  - The worker's handler mismatches (debt paid): refusals arrive unquoted, `grid` and
    `montecarlo` pass `structure`, an unknown catalogue type is refused in words, and the
    `train_run` request drops the `product` its handler never read.
  - `engine/runs.keep_run` keeps every engine's computation as one `runs` row, or its receipt. A
    held row is answered from the store, its first asker's `by` and `at` kept. A row's
    `outputs.values` holds the numbers its artifact states a unit for, each a quantity whose
    origin is the run's artifact.
  - Comparisons and runbooks read `outputs.values` for a run of any engine. A comparison of
    library runs alone keeps `study comparison 1`, every row and id as before; one holding another
    engine's run is `study comparison 2` (Departures). The studies export prints any engine's
    values.
  - CI's verify passed on `0c49630` (run 325, 13 min 43 s): the pins hold on GitHub's runners
    under the fixed dispatch, as the departure asks.
- C.2. The kinetics engine, fermOS's requests on typed quantities, and fermOS's runs as rows.
  - fermOS's requests take typed values (D2): `SimulationRequest`, `VesselRequest` and
    `ForecastRequest` take `inputs`, each a parameter's key and a `Quantity` with its origin and
    the day it was set, and `by`; the panels' resolve (`ParamResolveRequest`) takes `inputs` for
    every scope. `basis.override_of` is the one converter into the `Override` each resolver
    takes, so params, kinetics and vessel compute as they did. The four requests refuse a field
    they do not name, and the client puts FastAPI's list of field errors into words, asking a
    page older than the service to reload (`lib/http.ts`). The browser keeps a person's change as
    an `Override` and sends it as an input in its spec's unit (`lib/params.ts`, `inputsOf`).
  - fermOS's runs are rows (D3): a simulation, a kept forecast and a vessel design each keep one
    `runs` row of the engine `kinetics` (`engine/runs.compute_kept`) at every door (the routes,
    the tools, MCP, the engine), created by the request's `by` or the tool's caller; a refusal
    inside the computation is a receipt, and a value that waits keeps nothing. `outputs.values`
    holds a simulation's end state and hours, a forecast's finals with their 5th and 95th
    percentiles, and a design's rows. A held row's provenance follows its artifact's when a
    record it rests on is reviewed or demoted.
  - `kinetics` registered (D4; `core/pyproject.toml`, `fermos_engine.py`): the three simulating
    families, a forecast of a kept fit and a vessel design, the things read afresh in the
    project by the artifact store's tool column. `conform kinetics --inputs <file>` holds all
    eight checks with the placeholders `fermos_engine.write_placeholder_inputs` writes, and
    `pnpm prove` step 10 writes them for it; `pnpm ready` names that command and the worker a
    vessel design runs in (Departures).
  - The tools keep rule E.4‴, as the plan's amendment to D2 decides: `fermos_simulate`,
    `fermos_vessel` and `growth_forecast` take ids and words, check:tools' strict rule holds for
    `fermos_` and `pureos_` alike (each negative-tested), and Postdoc's rules 15 and 16 stand. A
    person sets a fermOS value on the screens' routes or at `POST /api/engines/kinetics/run`.
    `growth_forecast` becomes a write, keeping its forecast as a run in its caller's name.
  - A refusal of a key a scope lacks names the scope's own keys: a pureOS unit's as its scope
    expands them, and for a key no vessel declares, those of the vessel's kind; an anaerobic
    design with no scale asks for a plant scale alone.
  - The screens: a run's page shows a forecast's medians with their percentiles, every number to
    a few digits (in full in its title and the CSV), a kinetics run's missing SFF file as a fact,
    and a receipt's words ending in a full stop; the Forecast tab resolves with its scope's every
    spec and waits for the scope to load; Studies' card links fermOS → Simulate or Vessel for a
    kinetics thing whose values wait; a comparison holding another engine's run says each
    output's unit is its artifact's.
  - `pnpm test:core` 2458 passed, 1 skipped, 174 deselected (7 min 38 s); `pnpm test:sim` 138
    passed (7 min 12 s); the pins 13 passed, every literal as captured but the changed-start
    forecast's id (Departures, D1); `typecheck`, `gen:api`, `gen:tools` and `gen:components
    --check`, `check:tools`, `check:plan`, `check:state`, `build` and `smoke` (12 of 12 screens)
    green; `pnpm prove --steps 10` 11 of 11 checks in 123 s, `conform kinetics` 8 of 8 with the
    placeholders it wrote; `pnpm prove`, steps 1 to 10 offline, 71 of 71 checks in 265 s.
- C.3. The train engine, pureOS's requests on typed inputs, and a train's runs as rows.
  - pureOS's requests take typed values (D2): `TrainRunRequest`, for `POST /api/pureos/train/run`
    and `/check`, takes `inputs`, each named `<unit id>.<key>` or `inlet.<key>` with a `Quantity`
    carrying its origin and its day, and `by`. `train_spec.converted` converts each at pureOS's
    door through `basis.override_of` in its place's scope, and refuses together, by place, a name of
    neither form, a place the train lacks, a key its place lacks, a key set twice and a value its
    parameter cannot take, beside every other refusal the run would say (`_prepared`), at every
    door, the engine's run route among them (Departures); the resolution is as it was, and the
    pins hold a request sent as inputs and the same request's Overrides to one artifact id. The
    Builder sends each place's changes in the units its panel read (`lib/pureos.trainInputs`, held
    by `check:state`), and Studies' card links a train to the Builder, where its values are set.
  - A train's runs are rows (D3): `train_spec.run_train` keeps one `runs` row of the engine `train`
    (`engine/runs.compute_kept`; the tool `pureos.train_run`, the train's id as its thing, no
    configuration) at every door (the route, `pureos_build`, `pureos_write`, MCP, the engine),
    created by the request's `by` or the tool's caller; the worker's refusal is a receipt, a value
    that waits keeps nothing, and a worker that fails while writing the file keeps no row.
    `outputs.values` holds pureOS's own reading of the run's tables (each unit's recovery and the
    overall, the product out, each stream's mass flow, and the product share of each stream that
    carries product), registered with the tool (`artifacts.register`'s `values_of`). A train run
    replays exactly, as before C.3 (Departures). No backfill.
  - The train's SFF file: the Proforma worker's `sff_export` takes a train (`train`, the `train_run`
    request the run's basis gives, `train_spec.plant_of`); `POST /api/flowsheets/export` takes a
    train run too, its 409 in the worker's words. The schema the toolkit ships at `e236e32`
    requires every file's TEA year and a train carries no TEA, so the worker refuses the file in
    those words before it builds anything, and a real train run keeps them as `sffRefused`; the
    rebuild, the simulation and the toolkit's own words follow once the schema leaves the year to
    the file (Departures; a debt).
  - `train` registered (D5; `core/pyproject.toml`, `pureos/engine.py`): its things are the
    project's trains, saved and built, read afresh; its parameters are each place's values with the
    origin each resolution names, a default's origin widened to five and check 2 with it, a value
    the train fills itself marked in its note (Departures). `conform train --project <id>` holds all
    eight checks in a project with a train, on one train and a basis of its own, refusing the
    production database, where `pnpm ready` says where the checks run; the command with no
    `--project` names it, as `pnpm ready` does (Departures). `pnpm prove` step 10 makes a train
    from step 4's corn stover run through pureOS's from-run and checks it there (Departures; a
    debt). A train stands on a library run's stream: `STREAM_TOOLS`, from-run's `RUN_TOOLS`,
    `stream_table` and thermo's stream reader admit `library.run`, and the Builder's run choosers
    offer the project's library runs (`lib/pureos.runChoices`); pureOS → Train reads a train run's
    stream properties. The screens name a train run's train: the Runs table and the run's page
    give its name beside its id and link it, the Builder's result links its run, and Studies' card
    of an engine with no thing in the project says what one would be (`thingsAre`) and where it is
    made.
  - `pnpm test:core` 2474 passed, 1 skipped, 175 deselected (7 min 28 s); `pnpm test:sim` 139
    passed (7 min 12 s); the pins 13 passed, every literal as captured; `typecheck`, `gen:api`,
    `gen:tools` and `gen:components --check`, `check:tools`, `check:plan`, `check:state`,
    `check:secrets`, `check:figures`, `check:guild`, `check:licences`, `test:reconcile`, `build` and
    `smoke` (12 of 12 screens) green; `pnpm prove --steps 10` 22 of 22 checks in 193 s, `conform
    train` 8 of 8 in the proof's project beside `conform biosteam` and `conform kinetics`; `pnpm
    prove`, steps 1 to 10 offline, 75 of 75 checks in 297 s.
  - The review round: four reviewers read the uncommitted step, and each finding confirmed against
    the code is fixed, with a test where it is behaviour (Departures, the rows marked by the C.3
    review; three debts). A train run replays exactly again; an input that cannot stand is said
    beside every other refusal of the run or the check, and a key set twice is refused, at both
    doors in one set of words; the worker refuses a train's file before building it while the
    toolkit's schema requires a TEA year, the reason first, and the export route's 409 says the
    worker's words; `conform train --project` runs one train on a basis of its own, past a draft
    and a train that waits; `pnpm ready` on the production database says where the train engine
    is checked; a parameter the train fills itself says so in its note, and check 2 reads "takes a
    run's value"; `outputs.values` keeps a stream's product share where it carries product;
    thermosteam's stream reader takes every run a train's inlet reads; `GET /api/engines` lists
    `thingsAre`; the Builder's run choosers offer the project's library runs and its result links
    the run's row; the Runs table, the run's page and Studies' card name a train run's train.
    `pnpm test:sim` 140 passed (7 min 5 s); `pnpm test:core` 2484 passed, 1 skipped, 176
    deselected (7 min 29 s); `typecheck`, the three `--check`s, `check:plan`, `check:state`,
    `check:tools`, `check:secrets`, `check:figures`, `build` and `smoke` (12 of 12 screens) green;
    `pnpm prove`, steps 1 to 10 offline, 75 of 75 checks in 299 s, `conform train` 8 of 8 in the
    proof's project beside `conform biosteam` and `conform kinetics`.
- C.3b. Conformance reads a project and checks a copy of it (D5's amendment at C.3).
  - `conform <name> --project <id>` reads the project's own row and the rows the engine's
    `rests_on()` names from the configured database, writing nothing there, and copies them under
    the same ids into a project of the same id on a database of the checks' own
    (`engine/conform.copy_of`), every session there a savepoint of one transaction the checks never
    commit; the database is dropped however the checks end (a check that raises, Ctrl-C, `SIGTERM`,
    `SIGHUP`), and `pnpm prove` asks a run past its time to end before it kills it. The train
    engine's `rests_on` names every train, each artifact a train's inlet reads with its run's row,
    the scenarios a run-stream inlet names, the evidence pool whole and the project's strains; a
    test reads every table a train's resolution reads in the project and fails when the copy leaves
    one out, and the copy resolves each train as the project does, its parameters and the artifact a
    run of it computes.
  - Each train the copy holds that can run is checked, checks 3, 4, 5 and 8 on every one, with the
    values `--inputs` sets on every one; a saved draft, a train whose values wait for a source and a
    train whose run is refused before it computes are listed in check 3's words, numbered, each with
    its own, and left out (`unready`). A project with none that can run is refused in words saying
    the ways on, keeping no verdict (Departures). A runs row of the engine being checked is left out
    of the copy, so a person's earlier run of a train changes nothing.
  - The verdict is the one row written where the checks read: `engine_checks`, the machine's row,
    whose words give counts and name no project, train or run, beside the command's table with each
    thing's words. The production database is read as any other and `pnpm ready` names the command
    there; its row of a failed verdict reads `to see why, run …`, and an engine that declares
    `things_are` with no `rests_on` is said uncheckable in words (`conform.unrested`).
  - The review round: two reviewers read the uncommitted step, one for what is written where it must
    not be and one as a stranger with the pages, and each finding confirmed against the code is
    fixed, with a test where it is behaviour (Departures; a debt for C.5). `SIGTERM` and `SIGHUP`
    end the command with the checks' database dropped, and a rollback a busy connection refuses
    gives way to the drop, so Ctrl-C during a query is what the person meets; the verdict kept gives
    counts; the test of the production database's name holds every engine off a database of that
    name; `pnpm ready`'s row of a failed verdict reads to its end, and an engine that names nothing
    its things rest on is said uncheckable; check 3's words say the verdict alone is written where
    the rows were read, then list the things left out, numbered; a project with none of the engine's
    things is told what they are, and one with none that runs is given `--inputs <file>` among the
    ways on; check 8's first run is the checks' run, a replay with no tolerance says identical once,
    a check's words are cut at a word, and an option with no value says what it takes. The pages say
    that the values `--inputs` names are set on every train checked, that each command keeps one
    verdict, that a train run another train's inlet reads is copied as its artifact, and that a
    process killed outright leaves its database, with the command that drops it.
  - The touched files and the pins 270 passed (2 min 17 s); `pnpm test:sim` 140 passed (5 min 58 s);
    `pnpm test:core` 2494 passed, 1 skipped, 176 deselected (6 min 56 s); `gen:api`, `gen:tools` and
    `gen:components` changed no file; `build` green; `pnpm prove`, steps 1 to 10 offline, 75 of 75
    checks in 273 s, `conform train` 8 of 8 on a copy of the proof's project beside `conform
    biosteam` and `conform kinetics`.
- C.4. Proforma and the library door on typed inputs, Proforma's runs as rows of `biosteam`, and the
  shelf's scenario flowsheets as things of `biosteam`.
  - The requests take inputs (D2): `ProformaRunRequest` takes `inputs`, each an input's key or a
    composite's Finance key with a `Quantity` and its origin, converted at Proforma's door through
    `basis.override_of` in the scope `proforma:<scenario id>` (`proforma.overrides_of`), its low
    and high the range the samples draw over, and `by`; it refuses a field it does not name, the
    older `assumptions` field among them. `GET /api/proforma/bind` and `/ceiling-check` take
    `?inputs=` the same way and refuse the retired `?overrides=` and `?assumptions=` in words.
    `LibraryRunRequest` takes `inputs` on the biosteam engine's own path (`engine/biosteam.run_plant`):
    a value's unit is checked before the plant is built, the library's two doors are one path, and
    a plant that takes configurations, asked with none, is read and run in its default at every
    door. The tools (`run_scenario`, `run_flowsheet`, the library tools), `project_state.run_request`
    and a study scenario's run follow, and the screens send inputs through `params.inputsOf`.
  - Proforma's runs are rows (D3): `proforma.run` keeps one row of `biosteam` (`proforma.keep_run`,
    through `engine/runs.compute_kept`): tool `proforma.run`, thing the flowsheet, the scenario's
    id on the row, created by the request's `by` or the tool's caller, its SFF file written as it
    is kept (`proforma.write_file`, `plant_of`); a refusal inside the run is a receipt, a value
    that waits keeps nothing, and a grid or a sample is one row. `outputs.values` hold the base
    case's solved price (`price.solvedPrice`) and the five quantiles, in the artifact's price unit
    and on its TEA's basis; a comparison sets a Proforma run's price and a library run's on one
    row (Departures).
  - biosteam's things (D6): the shelf's scenario flowsheets join the library's plants through a
    provider Proforma registers with the engine as it is imported (`engine/biosteam.provide`),
    with no exception in the package map; their parameters are what a scenario of each binds, and
    a run of one is an unsaved scenario named by the flowsheet's own id, so the same request is one
    row at every door. `custom_train_v1` runs in a configuration naming its parts (Departures). An
    unknown thing is refused naming the engine's own; conformance reads the engine as the
    service's app holds it and refuses a named thing that cannot run as it stands, keeping no
    verdict.
  - Ids: a run that sets a value writes the line the panel's overrides wrote, so every run a
    person makes through the panel keeps its artifact id; the Proforma pin moved once under D1's
    amendment at C.4, its output hash held, and a model's estimate now bases as one (Departures,
    both rows; ADR-006's note). Every kept artifact replays as it was.
  - The review round: four reviewers (the ids, the plan, the pages with a stranger's walk, and the
    screens in Chromium) read the uncommitted step, and each finding confirmed against the code is
    fixed, with a test where it is behaviour: the panel's ids and the pin's move named; the
    model's estimate; the layering; the two reads on `?inputs=` and the retired fields refused;
    the default configuration at the parameters doors and the study door; a kept scenario's
    refused value a 422 at its route and the tool's words; refusals said whole at the engine's
    door; an unknown thing named in the engine's words; the conformance refusal and check 3's
    words; the comparison's shared row and its figure's own words; the Scenario screen's Run held
    for a name and for a composite's Finance units, the ceiling check's yield sent as an input; the
    run linked to its page from the scenario and the index; a run that holds no price said on the
    Runs screen and the run's page, its distribution in words of its own; the run's page naming
    its inputs and its scenario, its units on one line; the grid read at a one-value dimension;
    the export naming a Proforma run's scenario; the two run routes' responses declared; the slow
    test's whole yeast run naming the stand-ins' converter it calls; BASE.md, engines.md, runs.md,
    studies.md and ADR-015, and ADR-006's note.
  - The touched files and the pins 477 passed (1 min 56 s), the pins 13 of 13 with the Proforma pin's
    second id; `pnpm test:sim` 141 passed (7 min 12 s); `pnpm test:core` 2522 passed, 1 skipped, 177
    deselected (7 min 1 s); `gen:api`, `gen:tools` and `gen:components` regenerated (the OpenAPI
    document, the client's types and TOOLS.md; COMPONENTS.md as at C.3b); `typecheck`, `check:plan`,
    `check:state` (42 checks), `check:figures` and `check:tools` (48 tools) green; `build` green;
    `smoke` 12 of 12 screens; `pnpm prove --steps 10` 22 of 22 checks in 172 s, `conform biosteam`,
    `conform kinetics` and `conform train` each 8 of 8; `pnpm prove`, steps 1 to 10
    offline, 75 of 75 checks in 262 s; `test_proforma_slow.py`'s whole yeast run on the real worker
    1 passed (1 min 47 s).
- C.5. The `measurement` origin end to end (D7, the prompt's §6.3).
  - The kind: `OriginKind` gains `measurement` (`ref` the reading, `<deposition id>/<entry id>`;
    `at` the time it was taken; `by` its depositor), `OverrideOrigin` and `ParamOrigin` gain it and
    `Override` gains `ref`, so a reading travels through every resolver as a person's value does;
    every door that takes values admits it (a study scenario and `study_scenario`, fermOS, pureOS,
    Proforma, the library and the contract engines).
  - The lookup (`measurements.py`, through `basis.resolved` and `basis.override_of`) reads the
    project's depositions before anything runs and refuses in words a reading the project does not
    hold, one nobody confirmed, one a later entry corrects (a newer number still waiting to be read
    back among them), one kept by a browser with no person's name or under a placeholder name, one
    holding no number or no time, a value or unit other than the reading's own, a depositor or time
    other than the row's, and a unit that does not convert into the parameter's to a finite number.
  - The basis: a reading's source is a `deposition` naming it (`basis.measurement_source`), read back
    as a `measurement`; a run resting on readings, records and the package's defaults is `measured`,
    one beside a person's assumption or a model's estimate `assumed`; every reader of a value a run
    set asks `basis.is_set`, which holds a deposition to being a reading. No pin moves.
  - The bench's record on the service: `project_state.deposition_refusal` keeps a deposition the
    bench's way (appended readings kept as taken, a read-back from false to true, the state forward,
    a reconciliation as made, nothing new after the close), each other write refused in words and
    each write a closed deposition accepts audited; `GET /api/state` carries each deposition's maker.
  - The reads: the runbooks read lists each deposition, each reading a run may take (kind `reading`,
    its value and unit) and the measured evidence a reconciliation released, so `PARTIAL` holds no
    runbooks line; Postdoc's rule 18 says how a scenario's value names a reading; the tool door
    takes a reading's ref alone. `GET /api/depositions/readings` lists what a person chooses from.
  - The screens: NewScenarioDialog offers a deposition's readings beside a typed value, each said as
    what it measured and what it would set; a run's page names a measurement and links to its
    deposition at the reading, marked; the bench records readings against a locked runbook's
    measures alone once a name is set, reads back only the numbers no later entry corrects, and
    keeps a correction's time of reading; the record says which entry stands and which corrects it,
    names its depositor, and takes nothing new once closed. The walk deposits a reading there on
    step 5's runbook, makes a scenario on it alone (a placeholder pairing chosen by unit) and reads
    its run `measured`.
  - The review round: four reviewers (the rules, the plan, the pages, the screens in Chromium) read
    the uncommitted step, and each finding confirmed against the code is fixed, with a test or a
    check:state case where it is behaviour (Departures, C.5 rows; ADR-006's note of 2026-11-03).
  - The suites on the fixed tree: the touched files 393 and 474 passed, the pins 13 of 13;
    `pnpm test:sim` 141 passed (6 min 37 s); `pnpm test:core` 2587 passed, 1 skipped, 177 deselected
    (6 min 43 s); `gen:api`, `gen:tools` and `gen:components` regenerated, each `--check` green;
    `typecheck`, `check:plan`, `check:state`, `check:figures`, `check:tools`, `check:guild`,
    `check:secrets` and `test:reconcile` green; `build` green; `smoke` 12 of 12 screens; `pnpm prove
    --steps 9`, offline, 43 of 43 checks in 132 s, the walk's reading, scenario and `measured` run
    among them.
- C.6. The shelf's two hand-written entries retire, Proforma's split goes, and a flowsheet imports
  from a URL (D8, D9, D10; the prompt's §6.4).
  - `cornstover_benchmark` and `corn_drygrind` leave the shelf, their routes, tools, worker ops and
    screens with them; the reference screen and Proforma's index read the library shelf's
    `cornstover` and `corn` runs, and the regression table stays on screen (ADR-013's values where
    the package's own test keeps them). `proforma.reference` and `proforma_benchmark` stay
    registered, their code kept in `workers/kept_references.py`, so a run a person kept replays,
    reads into a train and prices as before (sim tests replay kept runs from `fd17f32`'s bases).
    `STREAM_TOOLS`, `RUN_TOOLS` and `stream_table` admit `library.run`.
  - Every scenario is the project's: `createdScenarioIds`, `needsBinding` and the held path go;
    `proforma.scenarios` binds a kept composite with its vessel and train run, so a kept
    `custom_train_v1` scenario answers where it answered 500, and a scenario on a retired
    flowsheet is listed with its refusal in words.
  - `POST /api/flowsheets/import-url {url, by}`: the person's address alone (the import tool
    takes a file), https alone, a public address alone (loopback, private, link-local, reserved
    and unspecified refused on every hop, the connection pinned to the address checked), fetched
    with the collectors' manners under the file limit and a whole-exchange deadline, refused in
    fixture mode; its sha256 kept, the URL as its source, origin `imported`; 413, 422, 502 and 503
    in words. The Flowsheets screen gains the field beside the file picker.
- C.7. The gate (the prompt's stage C gate: verify green; prove green with a scenario resting on a
  measurement; the kinetics' trajectories bit for bit; test:sim green).
  - `pnpm prove` step 10 makes the eight checks on every engine the service lists and requires
    every engine `core/pyproject.toml` registers among them (`biosteam`, `kinetics`, `train`), each
    listed with its version and its worker's state, none with an error. `kinetics` is checked with
    `--inputs`, the placeholders `fermos_engine.write_placeholder_inputs` writes, each the proof's
    person's assumption dated the proof's day; `train` with `--project`, on a train the proof makes
    in its own project from step 4's corn stover run through the Builder's routes (read from the
    run on the broth; its first units taken out while the check refuses an inlet the chemical set
    cannot build; the units whose values wait then cut with every unit before them, each refused
    for values that wait alone; the inlet the run's stream entering the first unit kept), saved
    and read back as the proof's person's. Each engine's line prints the words of checks 3, 5 and 7, the proof's
    project holds its runs, trains and artifacts as before the checks, and each verdict is kept and
    listed. A negative probe with `kinetics` left out of the listing fails two of the step's checks,
    and one with a cut unit refused for another reason stops the step in those words. The checks
    took 51 to 63 s on `biosteam`, 9 to 11 s on `kinetics` and 30 to 36 s on `train`, within
    `CONFORM_TIMEOUT_S`, which stays 1800 s.
  - Step 9's walk deposits a reading at the bench on step 5's locked runbook, makes a scenario from
    it through NewScenarioDialog and runs it; the proof holds the run `measured` and the reading's
    origin with its ref, its depositor and its time (C.5 built the walk; C.7 checks the run).
  - The kinetics' trajectories bit for bit: `core/tests/test_engine_pins.py` holds every literal.
  - Postdoc's ethanol suite gains the prompt's questions 13 and 14 (§5), in its words: the engine
    reads set out as one table, the engines expected `biosteam`, `kinetics` and `train` (stage D
    adds the stranger's); and a deposition's reading set as the glucose-only scenario's yield with
    its `measurement` origin, run, compared and its run's provenance said. `pnpm eval seed --suite
    ethanol` keeps fourteen (`docs/api/postdoc.md`).
  - The review round: three reviewers (a critic over stage C, the proof, a stranger on the screens)
    read stage C and the uncommitted step; each finding confirmed against the code is fixed, with a
    test where it is behaviour. `engine_plants` lists every engine registered here with its
    version, its worker's state, its last verdict and the ids of the project's runs it made
    (`runs.made_by`), and `engine_report` and `engine_run` name a run's engine and tool; a train
    read from a run starts on the stream carrying the most product into it from outside it, the
    corn stover run's from M401 on the broth (Departures), and the Builder says when a run-stream
    inlet entered another unit than the train's first, with the streams that first unit took a
    click away; check 7's words on a hand-written engine say what it holds (Departures; a debt);
    each module write's description gives an action every call refuses with the refusal's words
    and no fields; check:tools names a kept forecast among the runs. The screens: Simulate,
    Vessel and Forecast link each kinetics run's page; a train run's SFF words read in plain ink;
    every run's outputs show on its page, folded under a summary for BioSTEAM's; a comparison names
    each run from its row; Studies offers a kinetics family's page alone and folds a long refusal
    under its first sentence; the Runs card names every engine; a run's page shows a note without
    the build's decision tags. The records: a train's carried values and the stored panel overrides
    keep the resolvers' `Override` shape (Departures; a debt), debt 3's line narrowed to the run
    requests; ADR-016 records the bench's readings-alone mode; ADR-015's implementation notes;
    `docs/api/runs.md` says a fit keeps its artifacts alone; `docs/BASE.md` says stage D adds the
    handoff; the README names the engines; CLAUDE.md's lines.
  - The suites on the fixed tree: the touched files 463 passed and the pins 13 of 13. Two others failed on
    that pass: a literal in from_run that Rule 1's test counts, now named, and test_proforma_runs' read of
    the simulator's state, which holds alone and in test:core's order of files and failed in that run's
    order alone. The first `test:core` failed the boundaries test's reading of runs.py, which now reads its
    run ids through `db.rows.columns`. `pnpm test:sim` 142 passed (8 min 57 s); `pnpm test:core` 2687
    passed, 1 skipped, 175 deselected (7 min 17 s); the changed tests
    again with the database address empty, as CI's child process sees it, and on Python 3.12; `gen:tools` and
    `gen:components` regenerated; `build` green; `pnpm prove`, offline, steps 1 to 10, 83 of 83 checks in
    295 s with no call in its spend table; `pnpm verify`, all sixteen stages green in 18 min 0 s.
  - At the gate commit: the branch takes `466d10e` (the address words the same on Python 3.12 and
    3.13) under the step, and `pnpm test:core` holds on the two together. `test_proforma_runs`' read
    of the simulator's state now holds the read to asking neither name that starts the worker, the
    status the same before and after, so it holds whatever state an earlier test in the process left
    (made to fail first with the worker's state left ready, then green); the changed tests again on
    Python 3.12 with the database address empty.

### Alpha 2.2 — Stage D — 2026-11-04

- D.0, the engine side. The handoff pages read before the core is frozen: two readers confined to
  the engine brief's files planned the mirror from the pages alone, and every gap they found (the
  merged list's A1 to A36) is fixed on its page, and in the core where the page showed a gap the
  code has (the plan's D0.1 and D0.5 to D0.13). The two briefs stand verbatim; `docs/api/engines.md`
  says how a brief's words read on the contract.
  - Diagnostics (D0.1, A1). The worker's `run` op may answer `diagnostics` beside its `outputs`,
    what the computation reports about itself (the time it took, the iterations it made), each a
    name, a finite number or words, and a unit, at most 50, held to the outputs' shape; a break is
    `EngineBroken`, a 503 that keeps nothing. `runs.run_engine` holds `contract.diagnosed` open
    around its computation and `keep_run` keeps them on the row, `EngineRun.diagnostics` beside
    `durationMs`; the same request again is the kept row with its first computation's
    diagnostics. They enter neither the artifact (its output, its hash, its id, its replay) nor
    `outputs.values`, comparisons, runbooks or evidence. The run's page shows them under its
    outputs (`ProformaRun.tsx`, `Diagnostics`), `engine_report` and `engine_run` name them as words
    within a budget, and conformance check 3 holds their shape. A worker of its own speaking the
    protocol (`test_engine_diagnostics.py`) reports the time its run took, replays identically and
    holds all eight checks; every pin holds, the sample's id and output hash bit for bit with
    diagnostics answered (Departures; ADR-015, Implementation D.0; a debt for a failed SFF step).
  - The train engine's defaults (D0.5, A12). By every path that keeps a train, a train's own value
    is a person's: a typed value (`TrainParam`) carries its person and day and no origin of its
    own, the Builder's route keeps it so, a row whose typed value names an origin is no train and
    no thing, and a model's train built through `pureos_build` holds ids and words alone. So the
    default origins stay the five `models.DEFAULT_ORIGINS` names; `pureos/engine.py` maps each
    origin a resolution names onto them (`DEFAULT_OF`, a fit an artifact as Proforma's mapping
    has it) and refuses in words a value only a run sets, should a resolution hand one in.
    Check 2's measurement branch and `basis.reading_refusal`, which only it read, went with the
    sixth origin engines.md had named; the pages name the five, and workers.md says the worker's
    two are `library-default` and `convention`.
  - NaN and infinity (D0.6, A14). `EngineInput` refuses a number that is NaN or infinite as it is
    read (`models.non_finite`), so every door that takes a run's values refuses one before
    anything computes: the engine, library, Proforma, pureOS and fermOS routes, the params
    resolver, `?inputs=` on the bind reads, a study scenario (which refused one already), the tool
    door in its own words, and `conform --inputs`; `runs.check_inputs` and `basis.override_of`
    hold a caller that builds its values in code. A refusal echoing such a number answered 500,
    since JSON carries neither; the app's handler for a request's refused fields writes each as
    words, and every one is a 422 (`test_finite_inputs.py`, 69 cases).
  - `conform` with no database (D0.7, A20): no `OPENFERMENT_DATABASE_URL`, or a server that does
    not answer, is said in words naming it and the address, its password hidden, and the command
    exits 2, with `--project` or without.
  - The proof, generic over engines (D0.8): `pnpm prove` installs every package directory under
    `examples/engines/` with `uv pip install -e` before its service starts, one check a package,
    and the walk runs the first thing of each engine they register from the Runs screen and reads
    its run's page; with none, one line says so (Departures). The tree holds no `examples/`, and
    `pnpm prove` here takes the line at the install and at the walk: 83 of 83 checks in 296 s,
    no call in its spend table.
  - Every core test with an outside engine installed (D0.9): the skeleton engine `example` (below)
    made in the scratchpad, installed into `core/.venv`, its own test green from its directory
    with no database, `conform example` eight of eight on a database of its own; then `pnpm
    test:core` with it installed beside the core's three: 2788 passed, 1 skipped, 1 failed, the
    failure D0.6's own (a non-finite value at Proforma's door is now refused as the request's fields
    are read, its words in the field errors, and `test_proforma_ethanol` reads them there). No test
    assumed the registry holds the core's three alone. `pnpm prove` then ran with the skeleton
    placed under `examples/engines/` for the run: the package installed before the service started,
    the walk ran `a-thing` from Studies' run card and read its page (computed, two outputs, one
    diagnostic), step 10 held `example` eight of eight beside the core's three, and the licence
    check read it as the project's own; 86 of 86 checks in 319 s with no call in its spend table.
    `examples/` was removed and the engine uninstalled after, `core/.venv` holding what
    `core/uv.lock` names alone, and `pnpm test:core` ran again green (The suites, below).
  - `pnpm check:licences` (D0.10) reads every distribution in `core/.venv` that registers an
    engine and that `core/uv.lock` does not name, and each dependency of one the lock does not
    name: one installed from under `examples/` passes declaring no licence and fails declaring
    one (ADR-012); any other is held to `core/licences.toml`. They are reported and kept off
    THIRD_PARTY.md, so the listing reads the same with an engine installed or not.
  - `core/engines.local` (D0.11, A21): one package directory a line, ignored by git;
    `scripts/engines-local.sh` installs each again, and `scripts/session-start.sh` and
    `scripts/host/deploy.sh` run it after their `uv sync` (so `pnpm session:start` and `pnpm
    prototype:up` keep an installed engine).
  - Question 13 (D0.12): seeded, its expectation names every engine the registry holds, the core's
    three among them (`evaluate.engines_here`, read through `tools.engine.registered_names`, as the
    package map has Postdoc reach the engines); the code's own names the core's three alone.
  - The pages (D0.13): engines.md, workers.md and runs.md take A2 to A36 where the merged list
    puts each: how a brief's words read (the house rules a builder in its own worktree follows
    among them, A36), the install and its backends, a fresh checkout, the sync and
    `core/engines.local`, starting and restarting the service, the licence and the checks over
    an installed engine, `WorkerEngine`'s constructor, `serve`'s, the order and form of a run's
    inputs, an output's unit, the five default origins, the refusal shapes, the row's conventions,
    `created_by` and `by`, the listing's fields, the tools' inputs and the audit of a run, the
    conform command and checks 1, 3, 7 and 8, the basis kinds a run's inputs read as origins; and
    two new sections, an engine's own tests and a skeleton of the placeholder engine `example`
    (its `pyproject.toml`, its engine, its worker and one test), whose files are the package D0.9
    installed, tested and conformed.
  - The suites: the touched files, 594 passed in 190 s (nineteen files, the core's markers); the
    changed and new tests again with `OPENFERMENT_DATABASE_URL` empty and on Python 3.12, 359
    passed each; `check:tools` (48 tools), `gen:api`, `gen:tools` and `gen:components` with
    `--check`, `typecheck`, `check:plan`, `check:secrets`, `check:licences` (with the skeleton
    installed from `examples/` and without it) and `build` pass; `pnpm test:core` 2790 passed, 1
    skipped, 175 deselected in 496 s with no engine beside the lock; `pnpm test:sim` 142 passed,
    2824 deselected in 481 s; `pnpm prove` 83 of 83 checks in 296 s with no `examples/`.

- D.0, the client side (section M of the plan, D0.2 to D0.4, B2 to B28), done in a worktree of its
  own and merged onto the engine side's.
  - The MCP server takes `--service <origin>` and acts through a running service: each registry call
    is `POST <origin>/api/tools/<name>` with the arguments as the client sent them, the project in
    `X-OpenFerment-Project` and the client's declared name in `X-OpenFerment-Assistant`;
    `ask_postdoc` is `POST <origin>/api/ask`, its `by` the client's name, and `get_artifact` is `GET
    <origin>/api/biorepo/artifacts/<id>`. The origin is `http://` or `https://`, the host 127.0.0.1,
    [::1] or localhost, an explicit port and nothing after it (`mcp_server.service_origin`, the same
    answers on Python 3.12 and 3.13); anything else is refused in words at start, on stderr and in
    the server's instructions, and at every call, and a password a refused origin holds is never
    repeated. In this mode the server opens no database, reads `core/.env` for `OPENFERMENT_PROJECT`
    alone when `--project` names none, sends through `httpx.Client(trust_env=False)`, and waits up
    to the Proforma worker's start and one call of it and a minute more (900 s). The service's
    refusal comes back as the call's `error` in its own words, and a silent service as "the service
    at <origin> did not answer: <words>".
  - `POST /api/tools/{name}` reads `X-OpenFerment-Assistant` as UTF-8 text (`tools.caller_name`:
    control, format and surrogate characters dropped, whitespace collapsed, at most 200 characters)
    and runs the call in the model's lane under that name, `ToolContext(model=<name>,
    via="http")`: a number it types is that name's estimate, a write is marked with that name, its
    audit row names it as `who` with agent `model` and the door in `detail.via`, and a catalogue
    entry's source reads "<name>, at the HTTP endpoint" (the review's fixes, below). `?by=` and the
    header together are a 422 in words, so is a header naming nobody, and a writing tool's call
    naming neither is the existing 422, its words naming both ways. The OpenAPI document carries
    the header.
  - In its own process the server checks its project against its database at the first call and,
    while the database lacks it, answers every call with words naming the project and the database
    (B5); a project held is asked once.
  - A model's `catalogue_write` (Postdoc or an MCP client) replaces an entry kept in the model's
    lane under its own name through the same kind of door (the review's fixes, below) and is
    refused for any other, in words naming the entry and who kept it, nothing written (D0.4); a
    person's keep through the route, a file or `?by=` replaces whatever the id holds. Each entry
    records its lane and its door (`CatalogueEntry.agent` and `via`, written by the service; an
    entry kept before reads both from its source), and a project's catalogue keeps take one
    advisory lock, so a person's keep never lands between a model's check and its write.
  - The pages. `docs/TOOLS.md` (written by `tools/reference.py` and the tools' registrations) says
    how the server starts, both ways it reaches a project, the two extra tools' inputs, the SDK's
    names, an answer's shape over MCP, where the audit row is read and that no stand-in serves a
    store (B2 to B9, B13, B17, B19 to B21, B24, B28), and the catalogue, module read, primer and two
    field descriptions say what B10 to B12, B14, B15, B23 and B27 asked. The OpenAPI document
    declares `?project=` and the 404 on every scoped operation, `CatalogueEntry` on the catalogue
    routes, `text/event-stream` on the three event streams, the audit's limit and times, the audit
    row's lanes, the keep's 422 for a keep naming nobody, and the app's description of how a request
    names its project and what the guard admits (B14, B16, B18, B22, B25, B26). CLAUDE.md gains the
    line for a builder working from a handoff brief (D0.3). ADR-005, ADR-006 and ADR-008 record the
    service mode and the header.
  - Security, as reviewed: no listener, host or CORS rule is added, and `guard.py` is unchanged,
    holding the forwarded POSTs as it holds any. The header gives an HTTP caller the model's lane
    under the name it declares: a number it types is that name's estimate, which every record store
    refuses; its `catalogue_write` replaces only an entry that name kept through an assistant's
    door; and it writes the stores that hold a model's work alone, pureOS's kept trains among them,
    where a `?by=` call is refused. A loopback caller reaches that lane already through
    `POST /api/ask`, and an MCP client in the server's own process with the database's address, so
    the header is one more door to it (ADR-008, Implementation 12). The server sends to a loopback
    origin alone, through no proxy.
  - Tests: `test_mcp_service.py` (the origin rule's shapes, the flags, the forwarding through a
    stand-in transport with each failure's words, the tool door's header, and one test that starts
    the real server over stdio with `--service` against the app on a free loopback port, uvicorn in
    a thread on the test's database, a client declaring `example-test/0.1` writing a catalogue entry
    and reading the audit row that names it, with `OPENFERMENT_DATABASE_URL` empty in the server's
    environment); `test_mcp.py` (a project its store lacks; a second client's write over another's
    entry); `test_catalogues.py` (both lanes, and an entry kept before the lane was written);
    `test_openapi.py` (the query, the 404s, the response models, the streams, the header).
  - The suites in the worktree: the touched files 79 passed, the wider touched set 385; the changed
    tests again with the database address empty and on Python 3.12; `check:tools`, `typecheck`,
    `check:secrets`, `check:plan` and each generator's `--check` green; `pnpm test:core` 2734
    passed, 1 skipped, 175 deselected (8 min 16 s).
- D.0, the two sides merged. The client side's worktree diff against `1243e81`, its new test among
  it, applied onto the engine side's tree with `git apply --3way`. One file conflicted, `api.py`'s
  imports, and both sides' lines stand: FastAPI's `Header` (the client side's) beside
  `jsonable_encoder` and `RequestValidationError` (the engine side's). Every other file merged as
  each side wrote it, the three generated ones among them, and `gen:api`, `gen:tools` and
  `gen:components` then wrote the generated files again from the merged code, each the same as the
  merge and `COMPONENTS.md` as it stood. `docs/api/engines.md`'s tool door names its caller with
  `?by=` or the `X-OpenFerment-Assistant` header, and CLAUDE.md's line for a builder working from a
  handoff brief agrees with engines.md's reading of the brief's house rules. The suites on the
  merged tree: both sides' touched files, 886 passed in 241 s (thirty-five files, the core's
  markers); the changed and new tests of both sides again with `OPENFERMENT_DATABASE_URL` empty and
  on Python 3.12, 438 passed each; `typecheck`, `check:tools` (48 tools), `check:licences`,
  `check:plan`, `check:secrets` and each generator's `--check` pass; `pnpm test:core` 2837 passed, 1
  skipped, 175 deselected in 477 s, the base's 2687 with the engine side's 103 new and the client
  side's 47.
- D.0, the review's fixes: the engine pages, the proof's installs and the house rules. Two fixers
  worked the reviewers' findings by file; this entry is the one that held CLAUDE.md,
  `.gitignore`, the scripts, `engine/conform.py`, `engine/runs.py`, `migrations.py` and the engine
  pages, and the other's lines follow it.
  - CLAUDE.md's line for a builder working from a handoff brief (S3, D0.3a): the brief settles what
    the builder reads and that it commits and pushes nothing, which sets aside for it the Resume
    read and the commit and push rules above; every other rule, each R rule and stop condition
    among them, holds for its work too, and the line names no file the briefs forbid.
    `docs/api/engines.md`'s reading of the brief's house rules says the same.
  - `.gitignore` (D0.14) ignores `*.egg-info/`, the record a setuptools editable install writes
    beside a package's code, and `.claude/worktrees/`, the worktrees a session's workflows and the
    handoff's builders work in.
  - Every engine install held to the lock (S2, the amendment): `scripts/engines-local.sh`, which
    `session-start.sh` and `host/deploy.sh` run after their sync, and the proof's install read
    `core/uv.lock`'s versions (`uv export --frozen --all-extras --no-hashes --no-emit-project`) and
    install with them as constraints, so a package whose dependencies would move a pin (BioSTEAM,
    thermosteam, biorefineries, fastapi, httpx) is refused in uv's words and installs nothing, and
    a lock that cannot be read so installs nothing, said in words. In a throwaway environment an
    engine requiring a newer version of an installed pin was refused that way, the pin left at
    its version. engines.md's install is the same command, `cd core && uv pip install --python
    .venv/bin/python -c <(uv export …) -e <path>`, and says what an install trusts: the build
    backend runs in the installing shell's environment, the entry module in the service's process
    with the key in reach, the worker as the same user with the withheld variables left out.
  - The proof's installs (S11, D0.8a): a package that leads outside `examples/engines/` (a
    symbolic link elsewhere), a `pyproject.toml` that cannot be read or names no distribution, and
    an install that outlives its time each fail a check in words while the rest install. The
    install runs inside the proof's `try`; `SIGTERM` ends the proof as Ctrl-C does, and a `conform`
    the proof waits on is asked to end with it. At its end, however it ends, the proof leaves
    core's environment as it found it, one line a package: each package it installed whose
    distribution was installed nowhere before is uninstalled, one installed before from the same
    directory stays, and one installed before from another directory is installed from there
    again; with `--keep` each stays while the kept service runs, said with the command that takes
    it out.
  - Every thing of an example engine at its own defaults (D0.8b, C2, R1): engines.md says so in
    bold beside the proof's bullet, with what the walk and step 10 run. The walk waits for the run
    or the card's refusal and fails at once in the service's words, the rule beside them. Check 3
    names the way on for a thing whose values wait (`--inputs <file>`, or a default for each such
    parameter), the refusal now `runs.ValuesWait`, a subclass of `EngineRefused`; check 2's words
    agree in number (R8).
  - `python -m openferment_core.migrations` (R4) says in words, exit 2, a server that does not
    answer and a database its server does not hold, the latter with `pnpm db:reset <name>`.
  - The pages (the re-reader's 1 to 13, R2 to R5, C13). engines.md says what a package's modules
    and its tests import; maps the brief's "given typed quantities, it returns them", "tests that
    run with pytest" and "replays identically"; gives the install held to the lock with
    `--python .venv/bin/python`, `--no-build-isolation` added to it, and the egg-info record; how a
    database of one's own is made, migrated and dropped, the service needing a migrated database
    and `conform` a server; that a `WorkerEngine`'s parameter with no default is one every run
    sets (check 2's sentence too); the entries a `sourceRule` may name, any other breaking the
    contract; `serve` handed both streams; `ENGINE.parameters` by the thing's id, `EngineRefused`
    and `EngineBroken` through `ENGINE`, and the worker's life; an engine's own tests holding its
    replay at the worker, `conform` left to the base without a database address; what
    `[tool.pytest.ini_options]` does; `check:licences` reading this checkout's own `examples/`; and
    the proof's uninstall at its end.
  - The header's security property (S1) stands as the code holds it in ADR-008, Implementation 12,
    and in this file's two D.0 places (Departures, and the client side's entry above).
  - Left: `docs/BASE.md`'s handoff section waits for D.4 as planned (C11); the worktree under
    `.claude/worktrees/` is the workflow's, ignored now and left in place; the three leftover
    databases were gone from the test server when looked for.
  - Checks: the page's skeleton, cut from engines.md's code blocks, installed with the page's own
    command, its test green from its directory with `core/.venv/bin/python -m pytest` (1 passed),
    then uninstalled, `uv sync --frozen --dry-run` making no changes after. The touched files
    (`test_host`, `test_prove_examples`, `test_engines`, `test_db`, `test_guidance`, the core's
    markers) 211 passed in 72 s; again with `OPENFERMENT_DATABASE_URL` empty 211 passed, and on
    Python 3.12 211 passed. The generated files, `test:sim`, `test:core`, build, prove and verify
    run on the final tree once both fixers have stopped.
- D.0, the review's fixes, the client side. Four reviewers (security, the two re-readers, correctness)
  and a rehearsal read the merged tree; every finding on the MCP server, the tool door, the
  catalogues and docs/TOOLS.md is fixed in the code and the page that code writes.
  - The door a write came in by. `ToolContext.via` is `mcp` in the MCP server's own process and
    `http` at the tool door's `X-OpenFerment-Assistant` header, and `ToolContext.door()` names
    Postdoc's loop `postdoc`. Every audit row of the model's lane carries the door in
    `detail.via`, a proposal's among them, and only Postdoc's carries an `effort`: an outside
    assistant's row named the service's own effort, and no model of the service ran for it. A
    catalogue entry keeps its door (`CatalogueEntry.via`, read from the source for an entry kept
    before), and its source reads `Postdoc (<name>)`, `<name>, over MCP` or `<name>, at the HTTP
    endpoint`. A model's `catalogue_write` replaces an entry kept under its own name through the
    same kind of door, so an assistant that declares Postdoc's model id is refused over Postdoc's
    entries in words, and an assistant keeps its own through MCP and the header alike.
  - A name read one way at every door: `?by=` at the tool door, the catalogue route's `by` and
    Intake's pass through `tools.caller_name` as the header does, so a newline or a bidi override
    reads as nothing in an audit row.
  - The MCP server through a service: a value holding `@` is refused before it is parsed, in words
    that repeat nothing of it (a password written with `/`, `?` or `#` was repeated); `localhost`
    is sent to `127.0.0.1`, the address the service binds; the client follows no redirect, a 307
    answered as the service's words; `get_artifact` refuses an id of no artifact's shape before
    anything is sent, so `.` and `..` steer no read; an ask waits `ASK_TIMEOUT_S` (21 minutes,
    Postdoc's wall time beside the longest tool), a tool call 15; httpx's line a request stays
    off the server's stderr; the refusal for an unreadable database reads as whole sentences.
  - Answers over MCP leave their null fields out in both modes (`AnswerPlan`, `Artifact`), so an
    answer holds no `declined`; `catalogue_write`'s summary is the entry as kept (its own note,
    `agent`, `via`, `source`, `at`) beside `state` and `meaning`; `catalogue_read` keeps each
    entry's `at`, and a keep's time is written as the audit writes its rows' (`+00:00`).
  - `PUT /api/state/{kind}/{id}` refuses a row holding NaN, an infinity or an integer past a
    float's range, a 422 in words naming where it stands (it answered 500 from PostgreSQL); the
    engine contract breaks on an output or a diagnostic past a float's range before anything is
    kept (`models.float_holds`), and a diagnostic's refusal reads "a finite number or words; a
    boolean is refused".
  - The pages, through the code that writes them: docs/TOOLS.md's client recipe for `mcp` 2.3
    (`stdio_client`, `initialize()` first, `call_tool`, `result.content[0].text`, the snake-case
    fields), the shape of a refusal the server writes itself, the doors and the timeouts, a rule
    for an example's placeholder words, `catalogue_read`'s answer and bounds, `catalogue_write`'s
    id advice for a `<name>/<version>` caller and its fields for every kind, and the module reads'
    summary keys (`partial` among them). The OpenAPI document names the guard's own names from
    `guard.OWN_SUFFIXES` (`.localhost` among them), the door on the audit route, and each field
    of `AuditEntry`. ADR-005 and ADR-008 (Implementation 12) record the door and the loopback rule.
  - Two debts (Debts): a kept train is changed by any caller of the model's lane and keeps the
    name of the model that made it, the audit row naming who changed it; and an outside assistant
    names itself, so one may declare another's name, which the door tells from Postdoc's alone.
  - Tests: `test_mcp_service.py` (the `@` forms, localhost, a redirect, the waits, the log line,
    the dot ids, the null fields, the header door's `via` and effort, an assistant under Postdoc's
    name refused, `?by=` read as a name, the end-to-end row's `via` and the server's stderr),
    `test_catalogues.py` (an assistant's entry through either door, the entry as kept, the legacy
    doors), `test_project_state.py` (five numbers JSON cannot carry), `test_openapi.py` (the
    guard's names, the audit row's words), `test_engine_diagnostics.py` (a number past a float's
    range in an output and a diagnostic).
  - The suites on the final tree, both fixers' work together, run once both had stopped:
    `gen:api`, `gen:tools` and `gen:components` regenerated (COMPONENTS.md as it stood); the
    touched files with the pins, thirty files, 868 passed in 210 s (the core's markers); the
    changed and new tests of the stage, sixteen files, again with `OPENFERMENT_DATABASE_URL` empty
    530 passed and on Python 3.12 530 passed; `typecheck` and `check:secrets` green; `pnpm
    test:sim` 142 passed in 459 s; `pnpm test:core` 2865 passed, 1 skipped, 175 deselected in 458
    s; `pnpm build` green; `pnpm prove` 83 of 83 checks in 269 s with no `examples/`, the install
    and the walk each saying so in one line, and no call in its spend table; `pnpm verify`, all
    sixteen stages green in 17 min 50 s. The tree holds no `examples/`, and `core/.venv` holds
    what `core/uv.lock` names alone (`uv sync --frozen --dry-run` makes no change; the engine
    group lists biosteam, kinetics and train).
- D.0, at its commit. `test_prove_examples.py`'s guard that the proof and the walk name no
  example engine holds them to naming no distribution or module of the engine-package form the
  contract page gives (`openferment-engine-…`, `openferment_engine_…`), so the core names no
  example engine of its own; `core/tests/test_licences.py` loses a blank line at its end
  (`git diff --check` clean). `pnpm test:core` 2865 passed, 1 skipped, 175 deselected (7 min 45 s).
  The three databases left on the test server by runs a restart ended (`check_tools_25136_a40333`,
  `check_tools_32254_ccf87b`, `openferment_test_29588_792e52`) are dropped. A note on how the
  review ran: a message to the review's fixer while it worked started a second copy of it beside
  the first; the two split the findings by file between them, neither ran a suite while the other
  edited, and one carried every gate on the final tree.
- D.1. The core's commit for the handoff: `CORE=6f85338` (the D.0 commit; CI run 41865693107
  green). Until stage D's rounds end, nothing under `core/openferment_core/`, `core/tests/`,
  `core/pyproject.toml`, `src/` or `scripts/` changes, and `git diff --stat 6f85338 -- …` over
  those paths prints nothing for a round to count. Each stranger works in a worktree made at
  `CORE` (`git worktree add --detach .claude/worktrees/stranger-<a|b><n> 6f85338`), its absolute
  path the brief's `<path>`, and is started with the Agent tool's `isolation: "worktree"`: the
  harness cuts that isolated worktree from `origin/main` (alpha 2.1, which holds no
  `docs/api/engines.md`), and the agent receives this checkout's CLAUDE.md, the same as `CORE`'s.
- D.2. The engine stranger, round 1 (Appendix A verbatim, its `<path>` the worktree
  `.claude/worktrees/stranger-a1` at `CORE`). It read `docs/api/engines.md`, `workers.md` and
  `runs.md` and `openapi.json` alone, confirmed the four pages in its own worktree (the harness's,
  cut from `origin/main`, where its writes are held) were the same blobs as at `CORE`, moved that
  worktree to `CORE`, and built `examples/engines/openferment-engine-mirror/`: seven files, its
  worker's four ops through `serve`, one thing `reflect` on two placeholder parameters, the time
  its run took as the diagnostic `time taken`, a precision of `rtol` 0 and `atol` 0, its SFF file
  refused in words, 30 tests with no database, no licence and no dependency declared. No core file
  changed in either worktree or the main tree. Copied into the tree, installed with the page's
  command held to `core/uv.lock` (the registry lists biosteam, kinetics, mirror and train), its own
  tests 30 passed, `conform mirror` 8 of 8, and `pnpm prove` 86 of 86 checks with the package under
  `examples/engines/`: installed, listed, conformed in step 10, and `reflect` run from Studies' run
  card in the walk, its page reading 3 outputs and 1 diagnostic; question 13, seeded, names the
  mirror. Its six points on what the contract should have said are on `docs/api/engines.md` now
  (D.4).
- D.3. The agent stranger, round 1 (Appendix B verbatim, its `<path>` the worktree
  `.claude/worktrees/stranger-b1` at `CORE`, its project `proof` and its port the service `pnpm
  build && pnpm prove --keep` left: 83 of 83 checks). It read `.mcp.json`, `docs/TOOLS.md` and
  `docs/api/openapi.json` at `CORE`, and, beyond the brief's list, its own worktree's alpha 2.1
  copies of the same three files, to learn why that worktree could not serve the task. It built
  `examples/agents/record-reader/` (`record_reader.py` on `mcp` 2.3, a six-line README), which
  starts `.mcp.json`'s server with `--project` and `--service`, lists records with
  `biorepo_read`, keeps a placeholder skill with `catalogue_write` as `example-agent/0.1`, and
  reads back the entry and its audit row. Its first run worked. No core file changed. Run from the
  main tree against the kept service it exits 0: the entry by `example-agent/0.1`, agent `model`,
  via `http`, and the newest audit row's who the same. The kept service is stopped and its
  database dropped. Its interface points are a Known debt for stage E.
- D.4. The gate's records: `docs/reports/handoff-2026-11.md` (each round: what the stranger read,
  built, where it stalled, what the page lacked); `docs/BASE.md`'s two handoff tests with their
  commands; `docs/api/engines.md` takes the engine builder's six points (the install without
  process substitution, a count's unit, the placeholder rule beside it, `WorkerError`'s words, a
  worker checking its values again, the models' attribute names). Question 13 needs no core
  change: seeded with the mirror installed, it expects biosteam, kinetics, mirror and train.

### Alpha 2.2 — Stage E — 2026-11-04

- E.0a. The service answers a model on every JSON route the screens read, and a schema it only
  writes lists every property as required (the stage plan's section 2; ADR-007's implementation
  note of E.0a). Thirty-five routes gain their model and return it: Proforma's shelf, scenarios,
  binding, ceiling check, run, runs and simulator status; fermOS's fits, families, simulation,
  binding, simulations, harvest, vessel parameters and vessels; the parameter panel's scope and its
  resolve; pureOS's catalogue, a unit type's parameters, the proposal, trains, train runs,
  validation, check, from-run, run, one train and the kept trains; the stored answers of
  thermosteam, ProtParam and volatility; the catalogue's file intake; the literature's counts; and
  health. models.py gains `GridDim` (`ProformaGrid.dims`), `ScenarioRunsResponse`,
  `SimulatorStatus` (served by `proforma.simulator_status`; `status()` keeps the dict its callers
  and the sim tests read), `ThermoPropsStored` (`GET /api/thermo/props` answers the stored
  artifact beside what it holds, `{artifact, props}`), `StoredAnswer`, `LiteratureStats` and
  `Health`. Two reads are new, `GET /api/biorepo/artifacts/{id}/tables` (`proforma.tables_of`)
  and `/checks` (`proforma.checks_of`), each refusing in words an artifact of a tool outside
  `proforma.TABLE_TOOLS`, the tuple `stream_table` now reads too; `docs/api/runs.md` lists both.
  `api._scoped_openapi` marks the schemas reached from a success response and from no request:
  the document holds 255 schemas, 66 of them new, and 177 are marked (the plan's scratch documents
  measured 172), none split in two; the runbook family (`api.AS_KEPT`) and every schema a request
  takes keep Pydantic's lists, and the client typechecks against the new `src/api/types.gen.ts`
  with no file of its own changed. `core/tests/test_route_models.py` holds every route to a model
  with its exceptions named (the three event streams, a flowsheet's file, the study export, and
  the project state's three routes, which wait for E.0b: a Known debts row), each marked schema's
  list, the request schemas' and the family's, and the two reads; `test_thermo.py`'s stored read
  expects the pair. Checks: `pnpm test:core` 2876 passed, 1 skipped, 175 deselected (7 min 36 s, on the
  final tree); `pnpm test:sim` 142 passed (7 min 29 s), the Proforma run, fermOS's simulation, the
  train run and the vessel among them; the new and changed tests with the database address empty
  and on Python 3.12, 64 passed each way; `gen:api`, `gen:tools` and `gen:components` with each
  `--check`, `docs/TOOLS.md` and `COMPONENTS.md` as they were; `typecheck`, `check:plan`,
  `check:state`, `check:figures`, `check:tools`, `check:secrets`; `build`; `pnpm smoke` with no
  key, 12 of 12 screens; `pnpm prove`, offline, steps 1 to 10, 86 of 86 checks.
- E.0b. `GET /api/state` answers a `ProjectState`: the rows a project keeps of its pages get
  models (the stage plan's E.0b; ADR-007's implementation note of E.0b). Measured first, on this
  container's `openferment_dev`: the Ethanol project keeps one runbook with its lock and 51 Live
  conversations, and no deposition, measured evidence, Proforma scenario, train, fit or override;
  every row reads, nothing is refused, and the route answers in 0.19 s. models.py gains
  `Deposition` with `DepositionEntry`, `DepositionObservation`, `Reconciliation` and
  `ReconciliationDelta`, `MeasuredEvidence` with `MeasuredConditions`, `ProformaScenario`,
  `TrainMade`, `RunbookLock`, `RefusedRow`, `ProjectState`, `StateKept` and `StateTakenBack`; each
  row model is written from the page's hand type, its required fields the hand type's, and keeps
  the fields it does not name (`extra="allow"`, alpha 1.0's `dims`, `point` and `assumptions` of a
  scenario among them). `project_state.state` reads each row as its kind's model one at a time
  and the route serves it as kept (`response_model_exclude_unset`): a row kept before its kind had
  a model that does not read is left out and named in `refused` with its kind, id and why, and the
  rest load; a Live conversation is read from the whole of what Postdoc keeps and served whole.
  A write is read as its kind's model before it is kept, a 422 naming the fields
  (`project_state._reads_as`); `PUT` answers `StateKept` and `DELETE` `StateTakenBack`, so every
  JSON route answers a model and the Known debts row is paid. `api.AS_KEPT` gains the ten row
  schemas; `test_route_models.py` adds the state's route to `SERVED_AS_KEPT`, names the
  conversation family in `SERVED_WHOLE`, and holds every schema an as-kept route serves to
  AS_KEPT, Pydantic's own list or that family. The store names each refused row in its activity
  feed and says so once in a toast (`lib/projectState.ts` reads `refused`). The document holds 270
  schemas, 15 of them new, 182 marked, none split. Tests (`test_project_state.py`): every kind
  comes back through the route byte for byte as the page writes JSON, a field left out staying
  out, a null staying null and a field the model does not name kept (an integral number in a
  float field is written with a point and read back as the number sent); a row kept before its
  model that does not read is named with its words while the rest load; lock.ts's ten fixture
  digests hold over the runbooks read back, each lock holding the row sent back; a write that
  does not read is refused in words, nothing kept; a conversation is served whole, a turn kept
  before a field existed among them. Seven test files write their rows as the page writes them,
  and a row a test keeps that does not read is kept straight into its table
  (`kept_before_its_model`), where the reader that refuses it is tested. Checks: `pnpm test:core`
  2889 passed, 1 skipped, 175 deselected (7 min 47 s, on the final tree; the run before it found
  two of `test_engines.py`'s rows in their earlier shape, now written as the page writes them); `pnpm
  test:sim` 142 passed (7 min 30 s), the kept-scenario runs through `run_request` and the
  composite's kept scenarios among them; the new and changed tests with the database address empty
  and on Python 3.12, 124 passed each way; `gen:api`, `gen:tools` and `gen:components` with each
  `--check`, `docs/TOOLS.md` and `COMPONENTS.md` as they were; `typecheck`, `check:plan`,
  `check:state`, `check:figures`, `check:tools`, `check:secrets`; `build`; `pnpm smoke` with no
  key, 12 of 12 screens; `pnpm prove --steps 5,9`, offline, 45 of 45 checks, the walk's
  deposition, its scenario on the reading and the measured run among them, no call in the proof's
  spend table.
- E.1. Proforma's libs and screens read the generated types (the stage plan's E.1; ADR-007's
  implementation note of E.1). `lib/proforma.ts`, `lib/studies.ts` and `lib/params.ts` name the
  generated schemas of what each answers (`export type X = components['schemas']['X']`), and the
  eight Proforma screens (Proforma, ProformaBiosteam, ProformaComparison, ProformaReference,
  ProformaRun, ProformaScenario, ProformaStudies, Compare), the parameter panel and its row,
  NewScenarioDialog, SffGraph, ReadingOrigin, Dossier, FigureFrame, CostWaterfall, Distribution,
  Tornado and the figures' encoding read every name there. The store, the Durable snapshot, the
  project state, fermOS's and pureOS's libs, GeneOSModel, StrainPage, FermOSSimulate, FermOSVessel,
  PureOSBuilder and check:state read the generated `Override`, `Scenario` (the generated
  `ProformaScenario`), `FlowsheetInfo`, `CeilingCheck`, `FermosFitInfo` and `VesselSummary`. The hand
  `SimulatorStatus` and `ScenarioRunsResponse` are the generated ones, and the sliders' grid
  (`CostLine`, `SensitivityRow`, `ResultGrid`) moved into `lib/proforma.ts`, `src/data/types.ts`
  re-exporting it. The readers' changes: a run's body leaves `samples` to the service's default
  (`Body<T, K>`); a person's change is written with its origin (`person-assumption`, the service's
  default), and one kept with none reads as a person's; a study's runbook may leave its predictions
  out (Dossier, Studies) and a change its note (the panel's typed row); a new scenario writes none
  of alpha 1.0's `dims`, `point` and `assumptions`, and StrainPage and Organisms link a scenario to
  a strain by the names in its name, description or product (their record link read those fields,
  which no scenario made since alpha 2.0 holds). check:state's fixtures of the service's shapes are
  whole values of the generated types, and it gains the check that a change kept with no origin is
  sent as a person's assumption. Checks: `pnpm test:core` 2889 passed, 1 skipped, 175 deselected
  (7 min 34 s, on the final tree); `typecheck`; `check:plan`, 1629 fields across 218 types;
  `check:state`, 54 checks, the new one among them; `check:figures`; `gen:api --check` and
  `gen:components --check`, the document and `COMPONENTS.md` as they were; `build`; `pnpm smoke`
  with no key, 12 of 12 screens; `pnpm prove --steps 9`, offline, 45 of 45 checks, the run report,
  NewScenarioDialog over the run's parameters, the plants Studies offers, Flowsheets, the runbook,
  the scenario on a reading and its measured run among them, no call in the proof's spend table.
- E.2. FlowsheetPage and Flowsheets read the generated types (the stage plan's E.2). Each screen
  imports `SFFFlowsheet` from `lib/studies.ts`, whose calls answer it (ADR-007's note of E.1); the
  generated schema holds the hand interface's fields one for one, so every reader stands as it was,
  and the bundle `pnpm build` writes is byte for byte the one the tree before this commit builds.
  Checks: `pnpm test:core` 2889 passed, 1 skipped, 175 deselected (7 min 35 s, on the final tree);
  `typecheck`; `check:plan`, 1629 fields across 218 types; `check:state`, 54 checks;
  `check:figures`; `gen:api --check` and `gen:components --check`, the document and
  `COMPONENTS.md` as they were; `build`; `pnpm smoke` with no key, 12 of 12 screens.
- E.3. Postdoc's lib, its screen and the components that draw a plan read the generated types
  (the stage plan's E.3; ADR-007's implementation note of E.3). `lib/postdoc.ts` names the
  generated schemas of Postdoc's answers: `Health`, where the hand-kept `PostdocHealth` stood; the
  question (`AskRequest`, `PriorTurn`); the plan with all it rests on (`AnswerPlan`,
  `AnswerPlanUsage` for the generated `Usage`, `Claim`, `ClaimValue`, `PassageRef`, `Passage`,
  `Evidence`, `ModuleRow`, `CoverageMap`, `RunbookDraft`, `TraceStep`, `StopReason`); and the
  conversation (`LiveConversation`, `LiveTurn`). The Postdoc screen, PlanTrace and PassageQuote
  read every name there, AnswerPlanView and EvidenceCard each one they draw (`ExtractionRecord`
  and `Paper` stay on the hand-kept types until E.4, and EvidenceCard reads `BasisInput` from
  `lib/studies.ts`), and the store, the Durable snapshot, the project state and check:state read
  the conversation's. The readers' changes: a question sends `by` with every ask, empty when
  nobody is named, the service's own default; a turn the page begins writes its asker and its
  artifacts, every field the generated `LiveTurn` holds; a draft's measure may leave its
  prediction out (DraftCard); and `store.adoptRunbookDraft` writes the generated draft into the
  store's hand-kept runbook under one type assertion, its values as the service wrote them, the
  seam E.11 removes (a Known debts row). check:state's conversations are whole values of the
  generated type. Checks: `pnpm test:core` 2889 passed, 1 skipped, 175 deselected (7 min 28 s, on
  the final tree); `typecheck`; `check:plan`, 1629 fields across 218 types; `check:state`, 54
  checks; `check:figures`; `check:secrets`; `gen:api --check` and `gen:components --check`, the
  document and `COMPONENTS.md` as they were; `build`; `pnpm smoke` with no key, 12 of 12 screens,
  and the Postdoc screen on a service with no key saying so in words, its health the generated
  shape's five fields; `pnpm prove --steps 9`, offline, 45 of 45 checks, the conversation read from
  the service with its estimate marked among them, no call in the proof's spend table; a scratch
  check of the seam outside the tree, a draft's nulls and fields left out copied as they arrive
  and the lock digest over the adopted runbook the digest over the draft's own predictions and
  measures.
- E.4. BioRepo's libs and screens read the generated types (the stage plan's E.4; ADR-007's
  implementation note of E.4). `lib/review.ts` names the review family the service writes
  (`Candidate`, `ReviewDecision`, `DecisionCheck`, `RecordStatus`, `ExtractorRun`, `RunOutput` for
  the generated `ExtractRun`, `Overlay`, `OverlayPaper`) and the store's own shapes of them: the
  record (`ExtractionRecord`, the generated candidate with the review layer over it, its audit lines
  `AuditLine`) and the paper (`Paper`, the overlay's entry under its id). `lib/literature.ts` names
  `CollectOutcome`, `CollectRequest`, `PasteRequest`, `LiteratureDocument` and `SearchResponse`, and
  `lib/artifacts.ts` names `ReplayResult`. BioRepo, BioRepoSearch, BioRepoArtifacts, PaperReader,
  Witness, CollectCard and the run metrics (`engine/metrics.ts`) read every name there; the store,
  the Durable snapshot, `lib/intake.ts`, `lib/guild.ts`, `lib/geneos.ts`, check:figures and every
  screen and component that names a record, a paper or a decision check read theirs. `FieldId`,
  `ParameterFamily` and `ParameterDef` moved into `data/ontology.ts` and `Job` and `JobStage` into
  the store, `src/data/types.ts` re-exporting each. The readers' changes: a candidate enters the
  store as a record when the ontology names its field (`recordOf`, through the guard `isFieldId`),
  and one on any other field stays out and is named once in the activity and a toast; a run's false
  positive keeps the service's field, which `fieldName` names by its id when the ontology holds no
  such field; a record decided with no reject reason holds a null one; the page's audit lines write
  `from` and `to` only when a value changed; the Durable decision reads each field's type from the
  generated decision; a paste sends its licence, empty as the service's default; the citation chip,
  the palette's paper hint and BioRepo's year filter leave an unknown year out; Witness converts and
  compares an extracted value only when it is a number; the quantity display takes an SI value in
  words; IntakeIngest and the reader name a text's source by the service's `source`; BioRepo's
  Organism and Topic columns, filters and CSV fields, PaperReader's chips and abstract, and
  StrainPage's and Organisms' attribution through a paper's organism list go with the fields the
  overlay never carried (Departures), and the papers a strain counts are those its records were read
  from. check:state gains two checks: a candidate on a field the ontology names enters as a record
  of its values, its audit trail empty, and one on any other field stays out. Checks: `pnpm
  test:core` 2889 passed, 1 skipped, 175 deselected (7 min 48 s, on the final tree); `typecheck`;
  `check:plan`, 1629 fields across 218 types; `check:state`, 56 checks, the two new among them;
  `check:figures`; `check:secrets`; `gen:api --check` and `gen:components --check`, the document and
  `COMPONENTS.md` as they were; `build`; `pnpm smoke` with no key, 12 of 12 screens; `pnpm prove
  --steps 3,9`, offline, 54 of 54 checks, the kit's demo corpus with its accepted record and the
  walk's pasted note and search among them, no call in the proof's spend table; on its kept service
  a scratch check outside the tree opened BioRepo, the reader on each of the six papers, Witness,
  Search, Artifacts and an artifact, Intake, the ingest board and the review queue with no console
  error and no refused call, and a stand-in candidate extracted there, its card drawn and accepted
  from the keyboard, reached the service as a verified decision in the reviewer's name. The dev
  database's 272 candidates are on 16 fields, each one the ontology names.
- E.5. Intake's lib and the ingest board read the generated types (the stage plan's E.5).
  `lib/intake.ts` names the generated schemas of what it reads: `ExtractResponse`, the answer of
  `POST /api/intake/{paper_id}/extract`, and `FetchSource`, read from the overlay paper's `source`,
  where the document writes the service's `Literal` of sources inline in the field; the review
  family it posts and reads is `lib/review.ts`'s (E.4), and its header says what the lib reads and
  how it says the service is down. IntakeIngest reads `Candidate` from `lib/review.ts`; Intake and
  Guild moved in E.4's sweep, so Intake's screens and its lib read the generated types. The store's
  extraction toast reads the generated answer's candidates, refusals and cost. One reader's change:
  `fetchSourceName` takes the source the overlay always writes (`intake.overlay_papers` names the
  collector that served the text, or `upload`), and its Europe PMC default for a source left out
  goes. Checks: `pnpm test:core` 2889 passed, 1 skipped, 175 deselected (7 min 46 s, on the final
  tree); `typecheck`; `check:plan`, 1629 fields across 218 types; `check:state`, 56 checks;
  `check:figures`; `check:secrets`; `gen:api --check` and `gen:components --check`, the document and
  `COMPONENTS.md` as they were; `build`; `pnpm smoke` with no key, 12 of 12 screens; `pnpm prove
  --steps 9`, offline, 45 of 45 checks, the walk's pasted note on the ingest board among them, no
  call in the proof's spend table; on the service `pnpm prove --steps 3 --keep` left (16 of 16
  checks), a scratch check outside the tree opened the ingest board and the reader of each of its
  six documents (the kit's five demo files and a placeholder note pasted through the API), each
  naming its source as the overlay writes it, and pressed Extract again on the proof's extracted
  document, whose saved response the store's toast read as one candidate anchored and one refused at
  no cost, with no console error, no refused call and no call in the spend table; its database
  dropped after.
- E.6. fermOS's lib, its four views and the figures they draw read the generated types (the stage
  plan's E.6; ADR-007's implementation note of E.6). Service first: `POST /api/thermo/props`
  answers `ThermoPropsAnswer`, the `thermo_props` artifact beside what it holds, the pair the `GET`
  reads back as `ThermoPropsStored`; models.py gains the schema, `test_thermo.py` holds the POST to
  the pair, the GET to the same pair and a second ask to it with nothing asked of thermosteam, and
  `test_route_models.py` counts it among the marked schemas (the document holds 271 schemas, 183
  of them marked). `lib/fermos.ts` names the generated
  schemas of a fit and its series, a forecast and its bands, a family, a binding, a simulation with
  its steady state, the kept simulations, a harvest and a vessel, and `lib/thermo.ts` thermosteam's
  question and answer; FermOS, FermOSForecast, FermOSSimulate, FermOSVessel, PropertiesPanel,
  TimeCourse, TrajectoryBand and OxygenBalance read every name there, Dossier its `Band` and the
  store its kept fits. The readers' changes: the Properties panel draws the pair either door
  answers, each property read as typed, and the cast of an artifact's output goes; a fit's
  parameters and quality, a series' points and a quality's residuals are read as a request may
  leave them (a fit and its series go back to the service in a request, so their schemas keep
  Pydantic's lists), nine reads. A deposition and its runbook stay on the hand-kept types until
  E.11, and a train until E.7. Checks: `pnpm test:core` 2889 passed, 1 skipped, 175 deselected (6 min 49 s, on the final tree);
  `test_thermo.py`'s sim tests, 7 passed; the changed tests with the database address empty and on
  Python 3.12, 61 passed each way; `gen:api`, `gen:tools` and `gen:components` with each
  `--check`, `docs/TOOLS.md` and `COMPONENTS.md` as they were; `typecheck`; `check:plan`, 1629
  fields across 218 types; `check:state`, 56 checks; `check:figures`; `check:secrets`; `build`;
  `pnpm smoke` with no key, 12 of 12 screens; `pnpm prove --steps 4 --keep`, offline, 14 of 14
  checks, no call in the proof's spend table; on its kept service a scratch check outside the tree
  made the proof's train on the reference run through the Builder's routes and ran it once, opened
  pureOS → Train on that run, found the Properties panel's stored answer empty with one GET, asked
  thermosteam, drew the five properties in the library's units with its version and the artifact's
  link, each the value of the pair the POST answered, and after a reload drew the same answer from
  the GET with no second POST; it opened fermOS's Fits, Simulate, Vessel and Forecast, each drawn
  with no console error and no refused call; its database dropped after.
- E.7. pureOS's libs, its four screens and the components that draw a train or a proposal read the
  generated types (the stage plan's E.7; ADR-007's implementation note of E.7). `lib/pureos.ts`
  names the generated schemas of a run's train and its units, a proposal with its reasons and what
  it misses, the catalogue's unit types and their specs, a train as data with its validation, check
  and run, a stream's purity, a train read from a run and a train a model kept, and reads a stream,
  a train on file and a vessel from `lib/proforma.ts`; `lib/proposals.ts` names a gate's proposal
  and a person's act on it, and reads the Guild person acting from the hand-kept types until E.12
  (Departures). PureOS, PureOSBuilder, PureOSPropose, PureOSTrain, ProposedTrain, ProposalsCard,
  PurityByStream and RecoveryByUnit read every name there; `lib/thermo.ts` its train,
  `lib/params.ts` its train (the alias E.1 left goes), the store its saved trains, its proposals and
  what the Builder showed, and check:state, check:figures and check:guild theirs. The Durable
  snapshot's `TrainMade` is the generated row of E.0b, and the vocabulary's types
  (`UnitOperationStage`, `UnitOperation`, `CarbonSource`) moved into `data/vocabulary.ts`,
  `src/data/types.ts` re-exporting them. The readers' change: a train goes to the service in a
  request, so the generated `TrainSpec` names its units as a field a request may leave out, and
  each reader takes them through `unitsOf` (the lib's own, pureOS's two lists, the Builder's steps,
  its read from a run and its inlet), 23 reads. Checks: `pnpm test:core` 2889 passed, 1 skipped,
  175 deselected (6 min 52 s, on the final tree); `typecheck`; `check:plan`, 1629 fields across 218
  types; `check:state`, 56 checks; `check:figures`; `check:guild`, 126 checks; `check:secrets`;
  `gen:api`, `gen:tools` and `gen:components` with each `--check`, the document, `docs/TOOLS.md`
  and `COMPONENTS.md` as they were; `build`; `pnpm smoke` with no key, 12 of 12 screens; `pnpm
  prove --steps 4 --keep`, offline, 14 of 14 checks, no call in the proof's spend table; on its kept
  service a scratch check outside the tree saved and ran the proof's train through the Builder's
  routes, kept a model's train of one unit through the tool door under an assistant's name, and
  opened pureOS's index (the train built here with its four units, the model's with its one, the
  Propose chooser saying no host is on file), the Builder on the saved train (its four steps in
  order, a unit added from the palette, moved up and taken out, the page reading it as the saved
  train before the change and after), on the reference run's twelve units and on a copy of the
  model's train, and the Train page on the train run's four units, with no console error and no
  refused call; its database dropped after.
- E.8. The catalogues screen (the stage plan's E.8 and its section 4; the prompt's §6.5; ADR-007's
  implementation note of E.8). A container restart stopped the first attempt before it committed;
  its work in the tree was read again against the plan, the review changed the screen in two
  places (below), and every check ran again from the start. Service first, measured before it:
  this container's `openferment_dev` keeps no catalogue entry of any kind, the alpha 1.0 import
  writes none, and the live host waits on its install (stage G), so no stored entry falls outside
  what follows. A skill's entry gains its policy, `criticality`, `recencyDays`, `supervisedRuns`
  and `prerequisites`, its first three kept together, all three or none, and refused in words
  otherwise; `catalogues.as_skills` hands Guild all four, which repairs the defect the plan found
  (a catalogue skill held no `prerequisites`, and `Competence.level` raised `KeyError`).
  `competence.py` and `checks.py` leave a skill kept with no policy out of every level
  (`competence.unrated`): its level is 0, the checks' ranking passes it over, and a run of it
  alone, a cosign of it and a check asked for by name are refused in words that say it has no
  policy. A product's `category` is one of the twelve classes pureOS's proposer reads
  (`catalogues.ProductCategory`, held to `proposer.CLASS_OF_CATEGORY`, `biopolymer` among them)
  and belongs to a product, any other refused in words at the keep, in a file and at
  `catalogue_write`; a product gains `location`, secreted or intracellular, which `as_products`
  now hands the proposer, and a product kept with no class is proposed nothing in words that say
  so. `CatalogueKeep.entry` takes the entry's model, so a keep's body names the entry's kind (a 422
  in words when it is another catalogue's) and the generated `CatalogueEntry` reads every field
  with a default as one a reader may find absent; `catalogue_write` takes a product's location and
  no number, and says a skill it keeps holds no policy (`docs/TOOLS.md`); `docs/api/intake.md`
  names each kind's fields. Client: `src/lib/catalogues.ts` names the catalogue's generated
  schemas, and `src/screens/Catalogues.tsx` at `/catalogues`, a tab a kind, lists each catalogue
  with who kept each entry, in which lane, when and from where, adds an entry and edits one in the
  name Settings holds (a keep waits for a name, and an edit keeps the entry's id), and takes in a
  JSON or CSV file through `POST /api/intake/catalogue`, each row kept or refused in the service's
  words. The review's two changes to the screen: a tab of another kind starts afresh, its form,
  its kept line and its file its own (a file chosen on one tab, and the result of one taken in,
  had carried over to the next), and the skill choosers mark a skill kept with no policy, since a
  skill that needs it first waits on it too; the rail's comment says where Hosts sits beside the
  new destination, and a test's name and ADR-007's note read in plainer words. Each tab says who
  reads its catalogue on the service today (pureOS's proposer, Postdoc's reads of geneOS's hosts,
  ProtParam, Guild); the store's own lists of strains, products, skills and lessons stay empty
  until E.9 and E.12 (Known debts). It is the rail's eleventh destination (`src/data/nav.ts`, the
  chord `g a`), so Home's tiles, the command palette, the shortcut sheet and the smoke reach it;
  the palette takes a person to the other three tabs by name (Products, Skill policies, Lessons),
  and `src/data/components.ts` lists it as code with no name of its own. `labels.ts`' class labels
  read the generated union, its twelve classes (the stage plan gave the name to E.9, and it moves
  with its first generated reader by the plan's rule 3), beside a location's labels and a
  criticality's; a refusal's field errors reach the page in a model's own words, Pydantic's "Value
  error, " left off (`lib/http.ts`, a new check:state check). The walk keeps a placeholder strain
  on the screen in the proof's person's name, edits its other names, takes it in again from a file
  through the screen and reads it back as the person's keep, and step 9 holds it as the strain
  catalogue's one entry, the person's keep from that file. Checks: `pnpm test:core` 2895 passed,
  1 skipped, 175 deselected (4 min 34 s, on the final tree, and the same before a test's rename);
  the changed tests and the tests of the service code they cover, 21 files, with the
  database address empty on Python 3.13 and on Python 3.12, 679 passed each way; `test_propose.py`'s
  sim test through the real worker, 1 passed; `gen:api`, `gen:tools` and `gen:components` with
  each `--check`, the document, `docs/TOOLS.md` and `COMPONENTS.md` as the service writes them;
  `typecheck`; `check:plan`, 1629 fields across 218 types; `check:state`, 57 checks, the new one
  among them; `check:figures`; `check:tools`; `check:guild`, 126 checks; `check:secrets`; `build`;
  `pnpm smoke` with no key, 13 of 13 screens, Catalogues among them; `pnpm prove --steps 9 --keep`,
  offline, 47 of 47 checks, the walk's strain and its read-back among them, no call in the proof's
  spend table. On its kept service a scratch check outside the tree kept a product with its class
  and location, a skill with a policy, one with none (its row saying Guild rates nobody on it, and
  the next skill's chooser marking it), one needing another first and a lesson counting toward a
  skill, edited the lesson under its id, took in a file of products whose one refused row the
  screen said in the service's words, saw a sequence with no source and part of a policy refused on
  the screen in the service's words, found the next tab starting afresh after a file was chosen on
  one, found the keep waiting for a name when Settings held none, read Home's Catalogues tile,
  reached each tab from the palette by name and the strains by the chord `g a` with the rail
  marking Catalogues, and read back what the service held, `catalogue_read` among it: 30 of 30,
  the two refusals it asked for the only 4xx answers, Chromium's own console line for each the only
  console errors, and no 5xx; its database dropped after.
- E.9. geneOS's lib and screens read the generated types, and the store reads the project's strains
  and products from its catalogues (the stage plan's E.9; ADR-007's implementation note of E.9).
  `lib/geneos.ts` names the generated `GeneosModelInfo` and `GeneosResult` and reads a field's types
  from `data/ontology.ts`; GeneOSModel, Organisms and the figures Frontier, MixLine, CeilingGap and
  EvidenceStrip read every name there or in `lib/studies.ts`, and EvidenceCard finishes. A strain and
  a product are the project's catalogue entries: `lib/catalogues.ts` names `Strain` and `Product`,
  lists each kind (`listStrains`, `listProducts`) and names a strain in words (`strainWords`, its
  species, then its name); the store fills its strains and products as the page opens and again after
  each keep and each file on the catalogues screen (`hydrateCatalogues`, the newest read's answer
  kept), says where the read stands (`cataloguesRead`, `cataloguesProblem`), and keeps both across a
  reset of the browser's data, the service's as the overlay is. The readers' changes: a strain's
  binomial reads its entry's species, its designation its name and its description its note
  (Organisms, StrainPage, ProcessTrain, RunbookDetail, Protocols, FermOSSimulate, PureOSPropose and the
  palette, which finds a strain by its other names too); a strain's card and page show its other
  names, chemical set and note, the page who kept the entry, in which lane, when and from where, with
  a link to edit it on the catalogues screen, and both say they are reading the catalogue until it
  answers; a scenario links to a strain by any name its entry keeps (`strainNames` and `namesStrain`,
  moved into `lib/geneos.ts`, where E.1 asked); a promoted runbook's host is the research runbook's
  own; the board names a product's class when its entry keeps one; pureOS counts the products on file
  and those with the class its proposer reads; geneOS's Pathway view points to the routes the models
  on its shelf name; RunbookDetail's process train says that a product's entry keeps its class, its
  location and its sequence, and that pureOS builds and proposes a train; the reads of the alpha 1.0
  fields no entry keeps go (Departures). StrainPage keeps the hand-kept `Protocol` until E.12. The
  walk opens geneOS → Hosts after the catalogues screen keeps its placeholder strain, finds the
  strain's card and reads its page naming its other names (`scripts/walk.ts`, step 9's words in
  `scripts/prove.py`). The plan counted 48 reader fixes; with Organisms and StrainPage written against
  the entry, 21 typecheck errors stood in ten other files, ProtocolDetail's among them through
  Protocols' `strainLabel`. Checks: `pnpm test:core` 2895 passed, 1 skipped, 175 deselected (4 min 31
  s, on the final tree, and the same before the store's last change); `test_prove_examples.py`, which reads the proof's script, with the
  database address empty and on Python 3.12, 9 passed each way; `typecheck`; `check:plan`, 1629
  fields across 218 types; `check:state`, 57 checks; `check:figures`; `check:guild`, 126 checks;
  `check:secrets`; `gen:api --check` and `gen:components --check`, the document and `COMPONENTS.md`
  as they were; `build`; `pnpm smoke` with no key, 13 of 13 screens; `pnpm prove --steps 9`, offline,
  48 of 48 checks, the walk's Hosts step among them, no call in the proof's spend table, twice, the
  second on the final bundle. On the service `pnpm prove --steps 9 --keep` left, a scratch check
  outside the tree kept a second placeholder strain, with a species, a chemical set and other names,
  and a placeholder product with a class and a location on the catalogues screen, and found, with no
  reload since, both strains' cards on Hosts (its tab counting two, each card naming its entry's
  species, name, other names, note and chemical set, the species in italic, sorted by species and
  then by name), each strain's page with its entry and no products band, a strain the catalogue lacks
  said in words, the Pathway view counting the product, pureOS's index counting it among the products
  with a class, the Propose chooser offering both hosts by their words and the product among those on
  file, the service's proposal of four units for the product in the walk's strain, opened in the
  Builder with its four units, Simulate's strain chooser naming both strains, the palette finding a
  strain by one of its other names and opening its page, the runbook board, and the proof's runbook's
  process train in words: 25 of 25, no console error, no 4xx and no 5xx; Hosts, a strain's page and a
  missing strain's page opened cold by their addresses each drew from the catalogue's read; its
  database dropped after.
- E.10. The enumeration funnel deleted (the stage plan's E.10 and its section 4; the prompt's §3 and
  §6.5; ADR-010's implementation note of E.10). `src/engine/geneos/enumeration.ts` and RunbookDetail's
  `EnumerationFunnel` leave the tree with their import, their render, the column the funnel took beside
  a research runbook's stages, and the two imports they left unused (`useMemo`, `Explain`). Every
  research runbook this build makes starts with no stage, so the funnel drew no count for any of them;
  the stage card now spans its band and says in words that a runbook made from a study or drafted by
  Postdoc starts with its predictions and the measures that test them. The words of Dominion's era go
  with the funnel: RunbookDetail's note on a stage's value names a titre, a cost figure or a count; its
  promotion card says what a promotion carries (what the finished stages found, as the industrial
  runbook's first stage, with the host, the product, the predictions and the measures); the promotion's
  toast names the research findings; and the budget panel and the board's cost note say a person
  authorises a runbook's compute, the board grouping the runbooks awaiting it in a column of their own.
  The geneOS entry of `src/data/components.ts` and `COMPONENTS.md` (`src/engine/`, 14 files) follow;
  `RunbookStage` leaves its last importer, its hand declaration staying in `src/data/types.ts` for
  check:plan until E.15. Both pieces stand unchanged at `alpha-1.0`, the debt row is paid, and a new row
  names the held-for-review panel's words of the same era, which only a row kept in that state reaches.
  Checks: `pnpm test:core` 2895 passed, 1 skipped, 175 deselected (4 min 41 s, on the final tree);
  `typecheck`; `check:plan`, 1629 fields across 218 types; `check:state`, 57 checks; `check:figures`;
  `check:guild`, 126 checks; `check:secrets`; `gen:api --check`, `gen:tools --check` and `gen:components
  --check`, the document and `docs/TOOLS.md` as they were and `COMPONENTS.md` as regenerated; `build`,
  the bundle holding none of the funnel's or the clearance's words; `pnpm smoke` with no key, 13 of 13
  screens; `pnpm prove --steps 9 --keep`, offline, 48 of 48 checks, the walk's runbook page among them,
  no call in the proof's spend table. On its kept service a scratch check outside the tree read the
  walk's study runbook (research, no stages) with no funnel and the stage band's line, its card as wide
  as its band; kept two placeholder runbook rows through `PUT /api/state/runbooks/{id}`, a finished
  research runbook with one done stage and one awaiting a budget, and read the promotion card's words, a
  stage value written as a vocabulary id marked as a term no vocabulary carries, the promotion and its
  toast, the industrial runbook it made (its first stage the finding, its host the research runbook's),
  the budget panel's words and the board's cost note with the runbook awaiting budget in a column of its
  own: 20 of 20, no console error, no 4xx and no 5xx; its database dropped after.
- E.11. The runbook and deposition pages read the generated types (the stage plan's E.11; ADR-007's
  implementation note of E.11). `lib/studies.ts` names the rest of the runbook family beside its `Runbook`
  (`RunbookStatus`, `RunbookStage`, `RunbookStageStatus`, `Prediction`, `Measure`) and the bench's record
  (`Deposition`, `DepositionEntry`, `SeriesRole`, `MeasuredEvidence`); `lib/projectState.ts`'s `ProjectState` is
  the generated answer of `GET /api/state` with its `RefusedRow`, where the hand mirror stood, and `ProjectRows`
  the kinds of rows a page compares and sends, so who deposited each deposition and the rows the service cannot
  read are always in the answer. Runbooks, RunbookDetail, DepositionDetail, RunbookBits, DepositionPanel,
  TimeSeriesPanel, ProcessTrain (its `UnitOperation` from `data/vocabulary.ts`, and the process code no caller
  passes gone), the figure IntervalLedger, the engine modules ledger, lock, readings, reconcile, series and
  capture, check-reconcile-kinds and export-lock-fixtures move whole; `lib/fermos.ts` and check:state finish,
  check:state's depositions now whole values of their generated type; the store, the Durable snapshot,
  `lib/practice.ts` and `data/labels.ts` move their names; Deposition.tsx's runbook reads follow, its own `Step`
  waiting for E.12 and its header comment and glove constraints standing, and Depositions.tsx's state tones read
  the generated state. A runbook is served as kept, so a reader takes its stages, predictions, measures and
  outputs through `stagesOf`, `predictionsOf`, `measuresOf` and `outputsOf` (the engine modules through `?? []`),
  reads a runbook with no lock time as unlocked, one with no price as unpriced and a measure that names no
  prediction as context, each strict null test of RunbookDetail, Runbooks and the store now a loose one, and
  reads its note and its progress as a row may leave them out: the note card says the runbook keeps no note,
  and the progress stands at none. The seam of E.3 goes: a draft's predictions and measures enter the runbook as
  the service wrote them, with no assertion, and the lock digests the browser writes hold byte for byte. Every
  runbook a page makes is one of the project's rows: one promoted from a research runbook and a revision opened
  on a locked one take an id that holds across reloads and join the runbooks the page sends, where a reload
  dropped both before (found at E.10; Known debts). The plan counted 102 reader fixes; 68 typecheck errors
  stood once the names moved, 66 of them a field a row served as kept may leave out and 2 the project state's
  answers beside its rows. Checks: `pnpm test:core` 2895 passed, 1 skipped, 175 deselected (4 min 37 s, on the
  final tree); `typecheck`; `check:plan`, 1629 fields across 218 types; `check:state`, 62 checks; `check:figures`;
  `check:guild`, 126 checks; `test:reconcile`, the three kinds and the ledger's counts, 10 checks;
  `check:secrets`; `gen:api --check`, `gen:tools --check` and `gen:components --check`, the document,
  `docs/TOOLS.md` and `COMPONENTS.md` as they were; `export:lock-fixtures`, `core/tests/fixtures/lock-digests.json`
  byte for byte; `build`; `pnpm smoke` with no key, 13 of 13 screens; `pnpm prove --steps 5,9 --keep`, offline,
  48 of 48 checks, no call in the proof's spend table. On its kept service a scratch check outside the tree kept
  a runbook row that sets only its id, kind, title and status, served back as kept, and read its board card (0%,
  0/0 stages) and its page (no stage, nothing predicted, not yet locked, a deposition waiting for the lock,
  compute unpriced, progress at 0%, the note card's words, and no undefined, NaN or error card); read the proof's
  study runbook locked and intact, a deposition open to it and its ledger figure drawn; opened a revision of it
  and promoted a finished placeholder research runbook, each sent as a project row and there after a reload;
  read the walk's deposition's record and the depositions list; and opened a new bench of the readings alone,
  its staged screen listing the runbook's measures: 33 of 33, no console error, no 4xx and no 5xx; its database
  dropped after.
- E.12a. A project keeps its protocols, and a lesson keeps its body (the stage plan's E.12a; ADR-017 and
  ADR-018, each accepted, the owner free to reverse either). ADR-017 answers ADR-016's revisit condition:
  `models.py` gains `Protocol`, `ProtocolVersion`, `Step`, `Material` with `MaterialStock`, `BaseBatch`,
  `EstMinutes` and `ProtocolReference`, written from the page's hand shapes (a category and a material's
  scaling as Literals, every number finite, a step's placeholders binding materials its version holds, each
  step id and material name held once), with `ProtocolKeep` and `ProtocolVersionKeep`; migration 0010 makes
  the `protocols` table, one row a protocol; and `protocols.py` keeps them: `POST /api/protocols` makes a
  protocol once under its id, `POST /api/protocols/{id}/versions` adds a version under a version of its own
  and makes it the current one, a version held already refused in words so a kept version stays as it was
  kept, and `GET /api/protocols` and `GET /api/protocols/{id}` serve each protocol whole. The service writes
  each version's keeper and time, holds the keeper's name to the rule a person's recorded name keeps, audits
  each keep in that name, and refuses in words a step naming a skill the project's skill catalogue does not
  hold. `guild.projection()` reads every version's steps with their skills, so `guild.step_skills` answers
  for a kept protocol, and the current version of each protocol a step of which needs a skill, its steps in
  the words the bench shows at the base batch (`protocols.as_quoted`), which Practice quotes and a check's
  brief reads; the runbooks module's read lists each protocol from a source of its own (`Sources.protocols`),
  apart from the projection a train's resolution reads for its strains' names, which the conformance copy's
  test holds (the first run of `pnpm test:core` found the train's resolution reading the new table). ADR-018
  gives the lesson kind `minutes`, `blocks` (prose in Markdown and the nine embeds Primer's page draws) and
  `checkpoint` (a multiple-choice question with its options and the index of its answer; a numeric one with
  a value, a unit the converter reads or none, and a tolerance in percent), each refused in words on any
  other kind and where a question does not stand; a JSON file takes the body, `catalogue_write` keeps a
  lesson with none, and `catalogue_read` lists a lesson with its skills and minutes, its body left to the
  catalogues screen and Primer (`docs/TOOLS.md`). Two defects of alpha 2.1 D.1 found and repaired on the way,
  each with a test: the check ranking and a check's run read Guild's own projection inside their transaction,
  where `db.run` refuses to run, so each raised a RuntimeError in any project, the nightly ranking among
  them (the frozen fixture the tests hand in for the projection hid it); each now reads the skills
  before its transaction begins (`checks._propose`, `guild.write_check_entries_in`). And the Primer module's read raised `KeyError: 'moduleTitle'` on every
  catalogue lesson, which names no module; it reads a lesson's title, words, skills and minutes. The document
  holds 285 schemas, 14 of them new, 182 marked as written, none split; CLAUDE.md gains both records' lines
  and says ADR-000 to ADR-018, ADR-016 gains its implementation note, `docs/api/studies.md` documents the
  protocols, `docs/api/intake.md` a lesson's body, and BASE.md's content line both. Checks: `pnpm test:core`
  2926 passed, 1 skipped, 175 deselected (4 min 47 s, on the final tree); the new and changed tests with the
  tests of the service code they cover, 16 files, with the database address empty on Python 3.13 and on
  Python 3.12, 484 passed each way; `gen:api`, `gen:tools` and `gen:components` with each `--check`, the
  document, `docs/TOOLS.md` and `COMPONENTS.md` as the service writes them; `typecheck`; `check:plan`, 1629
  fields across 218 types; `check:state`, 62 checks; `check:figures`; `check:guild`, 126 checks;
  `check:tools`; `check:secrets`; `build`; `pnpm smoke` with no key, 13 of 13 screens; `test_propose.py`'s sim
  test through the real worker, 1 passed; `pnpm prove`, offline, steps 1 to 10, 89 of 89 checks, the four
  engines' eight checks each among them, no call in the proof's spend table.
- E.12. Guild, the protocols and Primer read the generated types, and the store reads the project's skills, lessons
  and protocols from the service (the stage plan's E.12 and its section 4; the prompt's §6.5; ADR-007's and ADR-014's
  implementation notes of E.12). `lib/guild.ts`, `lib/checks.ts` and `lib/practice.ts` name Guild's ledger, its
  checks and Practice's scenarios and sessions; a new `lib/protocols.ts` names a project's protocols (ADR-017) with
  their four routes (Departures); `lib/catalogues.ts` names a skill and a lesson as the catalogue's own entries, a
  lesson with its blocks and checkpoint (ADR-018). Guild's screens (GuildChecks, GuildMatrix, GuildPeople,
  GuildSkills), the protocol screens (Protocols, ProtocolDetail, ProtocolEditor), Primer's (Primer, PrimerLesson,
  PrimerPath, PrimerPractice), GuildBits, GuildGate, LessonEmbeds, the bench (Deposition, its header comment and
  glove constraints standing, and BenchCheck), StrainPage, the engine modules competence, checks, path, diff and
  scale, `lib/proposals.ts`, check:guild, export-competence-fixtures and its two libs move whole; the store and the
  Durable snapshot move their names, and Home, the palette, Organisms, JobsTray and Settings follow; `RunState`,
  `TimerState` and `Deviation` live in the store and `SkillFamily` in `data/skillFamilies.ts`, each named from
  types.ts until E.15. The store reads the skills and lessons with the strains and products (`hydrateCatalogues`) and
  the protocols from `GET /api/protocols` (`hydrateProtocols`), each as the page opens; the editor keeps a version
  in the reviewer's name (`POST /api/protocols/{id}/versions`) and lays the protocol the service answers in its
  place, each step's skills picked from the skill catalogue, and a step naming a skill the catalogue lacks holds the
  save back in words. Primer reads its lessons from `GET /api/catalogues/lesson` (Departures) and addresses one by
  its id, `/primer/<lesson>`, an address of the module era still reaching the lesson its last part names; the
  palette finds a lesson by its name. A lesson shows passed from the ledger's knowledge entries for whoever is
  learning, and the Durable snapshot keeps no lesson: the modules slice, `learnProgress` and `completeLesson` leave
  the store (Departures). A skill kept with no policy is left out of every level on the browser's side as on the
  service's (`rated` in competence.ts): nobody holds it, the ranking proposes no check on it, a path and the skill's
  page say it waits for its policy, and the gate names it; `core/tests/fixtures/competence-unrated.json` holds the
  two equal on such a skill and on one that needs it, replayed by test_competence.py and test_checks.py, and
  `competence.json` is byte for byte what it was (Known debts, paid). Guild's screens list a skill whose entry names
  a family outside the six, or none, under Other skills. A protocol is served whole, so a step's timer is tested
  with `!= null`, where a served null read as set would have drawn a timer on every step, and a version's lists are
  read with `?? []`. No screen makes a protocol yet (Known debts). The plan counted 56 reader fixes; 159 typecheck
  errors stood once the names moved, 64 of them a list a keep's body may leave out, most of the rest the modules
  slice's readers. Checks: `pnpm test:core` 2928 passed, 1 skipped, 175 deselected (4 min 51 s, on the final
  tree); the changed tests with the tests of the code they cover (test_competence, test_checks, test_guild,
  test_catalogues, test_protocols), with the database address empty, on Python 3.13 and on Python 3.12, 128 passed
  each way; `typecheck`; `check:plan`, 1629 fields across 218 types; `check:state`, 62 checks; `check:figures`;
  `check:guild`, 140 checks; `check:tools`; `check:secrets`; `export:competence-fixtures`, `competence.json` byte for
  byte (sha256 `6db0c6c0…`) and `competence-unrated.json` 96 statuses over 2 ledgers; `gen:components`, COMPONENTS.md
  with `src/lib/`'s new file, and `gen:api --check`, `gen:tools --check` and `gen:components --check`; `build`;
  `pnpm smoke` with no key, 13 of 13 screens. On a service kept by `pnpm prove --steps 2 --keep` (offline, 7 of 7
  checks, no call in the proof's spend table) a scratch check outside the tree kept two placeholder skills (one
  with no policy, its family outside the six), two placeholder lessons (one with no body) and a placeholder
  protocol, and walked the screens: Primer listed both lessons with their skills, minutes and checks; a lesson's
  checkpoint passed wrote a lesson passed on the lead's ledger, shown passed after a reload and counted on the
  lessons page, the Durable snapshot holding no `learnProgress`; the bare lesson said it keeps no body; a
  module-era address reached its lesson; My path and Guild's skill pages named the skill with no policy, Guild's
  skills listing it under Other skills; the protocol's page showed one timer, on the one step that keeps one; and
  the editor kept version 1.1 in the reviewer's name with a step's skill picked from the catalogue, version 1.0
  standing: 35 of 35, no console error, no 4xx and no 5xx; its database dropped after.
- E.13. Settings and SettingsFigures read the generated types (the stage plan's E.13). Settings names `FieldId` and
  `ParameterDef` from `data/ontology.ts` and `GateMode` and `GuildPolicy` from `lib/guild.ts`, and SettingsFigures
  names `Artifact` from `lib/studies.ts` and hands the ceiling's figure the store's records as they are, each the
  generated record. Each twin holds its hand type's fields one for one, so with the names moved `pnpm build` wrote byte
  for byte the bundle the tree before this commit builds, and every screen now reads the generated types. A check of
  the screen on a kept service found two things E.12 left on it: "Clear this browser's data" emptied the project's
  skills, lessons and protocols from Primer, the protocol pages and Guild until the next reload, and its confirmation
  named a lesson finished here among what it discards. The reset keeps the three as it keeps the strains and products
  (`store.clearBrowserData`), so what the service keeps is back at once, as the confirmation says, and `pnpm
  check:guild` holds it with a check that fails on the store before this commit; the confirmation names what the
  Durable snapshot holds, as the panel above it does since E.12, and counts each kind in its singular or its plural;
  and the API keys card says the service has no sign-in and issues no key. Checks: `pnpm test:core` 2928 passed, 1
  skipped, 175 deselected (4 min 56 s, on the final tree); `typecheck`; `check:plan`, 1629 fields across 218 types;
  `check:state`, 62 checks; `check:figures`; `check:guild`, 141 checks, the new one among them; `check:secrets`;
  `gen:api --check`, `gen:tools --check` and `gen:components --check`, each generated file as it was; `build`; `pnpm
  smoke` with no key, 13 of 13 screens. On a service kept by `pnpm prove --steps 2 --keep` (offline, 7 of 7 checks, no
  call in the proof's spend table) a scratch check outside the tree kept a placeholder skill, lesson and protocol and a
  lead, and opened each of Settings' seven sections; the playground offered each of the 34 fields; the lead saved the
  Guild policy and the service kept it in the lead's name; the figure grammar stood by its legend on a project that
  keeps no computed result; an export from the ontology card was listed in the export center, the API keys card
  beside it in its new words; and after the clear the lesson, the protocol and the skill still showed: 25 of 25, no
  console error and no 5xx (22 of 24 on the tree before the fix, the two the clear and its words); its database
  dropped after.
- E.14. The components and modules that remained read the generated types, and the browser's own types finish moving
  to their owners (the stage plan's E.14; ADR-007's implementation note of E.14). Provenance, TraceCards and
  check:figures name the provenance class from `lib/studies.ts`, QuantityField a record's field from
  `data/ontology.ts` and JobsTray a job from the store; the store names a project from `lib/project.ts`, which names
  the generated `Project` that `/api/projects` answers. A line of the page's recent activity (`ActivityEvent`) is
  declared in the store, and a Proforma assumption as a snapshot written before the parameter panel keeps it
  (`InputAssumption`) in `lib/durable.ts`, with the seven fields the browser wrote, each read as a person's
  assumption; `src/data/types.ts` re-exports `ActivityEvent` until E.15 and keeps its own `InputAssumption`,
  check:plan's twin of the model the service binds a scenario's values with, its origin and reading among its fields.
  `PROVENANCE_RANK` keeps its declaration line, `Record<Provenance, number>` over the generated union, which
  check:plan reads by text. No file under `src/` or `scripts/` imports `src/data/types.ts` now, and check:plan alone
  reads it (Known debts). Two comments in the moved files are corrected: `data/vocabulary.ts` names a train's own
  units, in order, as the authority on the train, since no catalogue entry keeps a product's `unitOperationIds` (E.9's
  note), and `data/ontology.ts` drops its wait for stage 7 to serve the fields, since no route serves them. Every
  change is to types and comments, so `pnpm build` wrote byte for byte the bundle the tree before this commit builds.
  Checks: `pnpm test:core` 2928 passed, 1 skipped, 175 deselected (4 min 47 s), and again on the final tree with the
  same counts; `typecheck`; `check:plan`, 1629 fields across 218 types; `check:state`, 62 checks; `check:figures`;
  `check:guild`, 141 checks; `test:reconcile`, 10 checks; `check:secrets`; `gen:api --check`, `gen:tools --check` and
  `gen:components --check`, each generated file as it was; `build`; `pnpm smoke` with no key, 13 of 13 screens.
- E.15. `src/data/types.ts` is deleted and `check:plan`'s pairs retire with it, as the prompt's §3 and §6.5 say (the
  stage plan's E.15; ADR-007's and ADR-011's notes of E.15). No file had imported it since E.14, so the client
  typechecks as it stood, and `pnpm build` wrote byte for byte the bundle the tree before this commit builds.
  `scripts/check-plan.mjs` keeps the provenance ranking alone, and its header says what it checks: models.py's
  `Provenance` union and `PROVENANCE_ORDER` name the same classes, each held to the other; the order starts at
  `measured`, ranks `measured` above `gold` and an unverified extraction at least as high as an industry estimate;
  and `PROVENANCE_RANK` in `src/store.ts` gives each class a rank of its own in that order. Each of those checks
  failed on a scratch copy of the two files made to break it. The browser's union is generated (`gen:api --check`),
  and `PROVENANCE_RANK` is a `Record<Provenance, number>` over it, so `typecheck` holds its keys; verify keeps
  ADR-011's sixteen stages in their order. The words that named the hand-kept file say what stands: models.py's
  module docstring and comments, and the descriptions the OpenAPI document carries for `LiveTurn`,
  `LiveConversation`, `FetchedSection`, `Prediction`, `Measure`, `RunbookStage`, `Runbook`, the deposition family,
  `MeasuredEvidence`, `ProformaScenario` and `Protocol`, each naming the lib where the browser reads it
  (`docs/api/openapi.json` and `src/api/types.gen.ts` regenerated, their descriptions alone changing); the
  docstrings of params.py, project_state.py, flowsheets/shelf.py, studies/runbooks.py and pureos/train_spec.py, and
  a comment in test_runbooks.py; `docs/api/postdoc.md` and `docs/api/studies.md`; ADR-011's stage list, with a
  note; and CLAUDE.md's working-assumptions line (147 lines, every line labelled). `core/tests/test_schema.py`'s
  mirror of `fields.yaml`, `vocabulary.yaml` and `units.json` stands as it is, and COMPONENTS.md lists
  `src/data/`'s nine files. The debt is paid (Known debts), and the Resume names what stage E still holds. Checks:
  `pnpm verify`, all sixteen stages (`test:core` 2928 passed, 1 skipped, 175 deselected; `test:sim` 142 passed;
  `test:lit` 10 passed; `smoke` 13 of 13 screens), in 11 min 39 s; `pnpm build && pnpm prove`, offline, steps 1 to
  10, 89 of 89 checks in 199 s, the catalogue screen in the walk and no call in the proof's spend table; `pnpm
  test:core` again on the final tree, the same counts; `test_runbooks.py` and `test_guidance.py` with the database
  address empty and on Python 3.12, 13 passed each way; `typecheck`; `check:plan`, 9 classes in one order;
  `check:state`, 62 checks; `check:figures`; `check:guild`, 141 checks; `test:reconcile`, 10 checks;
  `check:secrets`; `gen:api`, `gen:tools` and `gen:components` with each `--check`; `build`; `pnpm smoke` with no
  key, 13 of 13 screens; and `grep -rn "data/types" src scripts` finds nothing.
- E.16. The agent builder's interface points are paid, each in the code `docs/TOOLS.md` and `docs/api/openapi.json`
  are written from (`docs/reports/handoff-2026-11.md`, round 1; ADR-008's Implementation 13). A BioRepo record is one
  rule, `module_stores.RECORD`, which `biorepo_read` and `search_records` both quote: a record is an extraction a
  reviewer verified against its document's own words (verified, or gold), and a candidate one no reviewer has verified
  yet (unverified). `biorepo_read` lists the two as its kinds `record` and `candidate` (`record_kind`, from the row's
  state), so a candidate a reviewer accepted is kind `record` now; `search_records` names each hit's `kind` by the same
  rule; and the row `biorepo_write`'s candidate action answers with is the row the read lists (`record_row`). A
  write's answer names its audit rows: `tools.run` opens `audit.written()` around the tool, `audit.add` adds each new
  row's id to it, the rows a store's own transaction writes on the database's thread among them, and
  `ToolResult.auditIds` names each, a gated write's proposal included, at the HTTP door and over MCP alike. An audit
  row's id is its place in the table, served as a string of digits on `AuditRow`; `GET /api/audit` takes `action`,
  `target` and `who` beside `limit`, each matched as a row names it, so a write of any age is found by what it was,
  and leaves a row's null fields out as an answer over MCP does (`response_model_exclude_none`; `AuditRow` joins
  `api.AS_KEPT`, and the route `SERVED_AS_KEPT`). `AuditEntry.detail` says what a row holds, and `catalogue_write`
  and `study_scenario` keep their call's note there as the other writes do. A module read's summary is a
  `ModuleRead`, its `partial` a sentence, and `module_stores.DETAIL` names each kind's `detail` field by field;
  `docs/TOOLS.md` renders both at the end of Module reads, its client recipe hands the server a client's environment
  with `VIRTUAL_ENV` taken out, and its top points at the recipe. `docs/api/engines.md` says an engine run's answer
  names its row, and the handoff report says the five points are paid. `core/tests/test_agent_interface.py` holds each
  point in twelve tests, a row of every kind among them, and `test_mcp_service.py`, `test_mcp.py`, `test_openapi.py`,
  `test_route_models.py` and `test_projects.py` read the new answers. Against `pnpm prove --steps 3 --keep`'s service,
  the stage D record-reader (`examples/agents/record-reader/`, as its builder left it) lists the project's one record
  as kind `record` and exits 0, and `GET /api/audit` narrowed by its write's action, target and name serves that
  write's row alone, under its id, with no null field. Every client change is to the generated types, so `pnpm build`
  wrote byte for byte the bundle E.15's tree builds. Checks: `pnpm test:core` 2940 passed, 1 skipped, 175 deselected
  (5 min 13 s), and again on the final tree with the same counts; the changed tests with the database address empty
  and on Python 3.12, 113 passed each way; `gen:api`, `gen:tools` and `gen:components` with each `--check`;
  `check:tools`; `typecheck`; `check:plan`; `check:state`, 62 checks; `check:figures`; `check:secrets`;
  `test_guidance.py`; `build`; `pnpm smoke` with no key, 13 of 13 screens; `pnpm prove --steps 3 --keep`, offline,
  16 of 16 checks.
- E.gate. The stage E gate, with the review's fixes: three reviewers read E.0a to E.16 (a critic of the code against the
  plan and §6.5, a walker through the built app on a kept proof's service, and a reader of the service), and each
  finding was confirmed against the code and fixed, two of them answered by a recorded departure.
  - The catalogues screen keeps a lesson's body when a person edits the lesson: the form sends the entry it opened with
    the fields it holds laid over it (`lib/catalogues.ts` `edited`), so a lesson's minutes, blocks and checkpoint go
    back as the lesson holds them, and the keep, which replaces the entry whole, keeps them. The lessons tab counts each
    lesson's blocks and checkpoint questions, the form says a body is written in a file of lessons, a lesson's note is
    labelled as the words Primer opens it with and its summary as what Primer shows under its name, and the line naming
    the last keep gives way to a file's result. The service reads a catalogue's rows one at a time, and a protocol's:
    a row of an older shape is left out and logged with why, the rest and every reader of them reading on (geneOS's
    hosts, Guild's projection, the proposer), a model's write under such an id is refused in words and a person's keep
    writes it afresh. An entry's id and a skill's policy are refused in the words the form uses, each policy part with
    its field. A protocol keep is held to 2,000,000 bytes as its row keeps it, refused in words past it.
  - The protocol pages: the editor's form opens on the protocol's current version once the service has answered with
    it, so an editor opened by its address starts from the steps and materials kept, and a version with no step is
    refused before it is kept. A screen that names a protocol by its address (the protocol's page, its editor, the
    bench) reads one made after the page opened from the service (`useProtocol`, `GET /api/protocols/{id}`). The bench
    says while the protocols are read, offers a fresh run for a run a reload ended, and names a run's version the
    protocol lacks. Two versions compared differ in every field a step or a material keeps, a step's skills among them,
    each change named on the compare sheet with the skills on each side. The protocols page begins a protocol in the
    reviewer's name (its id, title, category, biosafety level, purpose, organisms, base batch, minutes and first steps),
    its editor opening on it (the Known debts row is paid). The lesson, protocol and editor pages say so when a read
    fails, and the editor names a step's skill unknown only once the skill catalogue is read.
  - Guild and Primer: a skill with no policy says so in words on a person's ledger, on the skill's page and on the
    pair sheet, and a skill whose entry names no criterion says where one is written. Primer shows a lesson's summary on
    its index and under its title and counts its checkpoint questions, and Practice's By skill says what fills it.
    Counts take their singular or their plural on the protocols, the editor's publish sheet, Home, BioRepo, the ledger
    and Guild's skill page, and the not-found words of a scenario, a runbook and the runbook board name the project.
  - The types: `DecisionCheck.rule` is the eight rules `biorepo.write` refuses under (`models.DecisionRule`,
    `biorepo.RULES` read from it), so the browser's `RefusalRule` is the generated union, and `POST /api/guild/check`,
    which answered the same model, answers an `EvidenceCheck` of its own with Guild's fourteen rules (`models.GuildRule`,
    `guild.RULES` read from it). The hand copies of generated shapes are derived from their schemas (`ParamAsk`,
    `SimulateAsk`, `VesselType`, `PredictionKind`, a reconciliation's outcome, a rated skill's criticality,
    `StateKind`), and the browser's own Proforma assumption is `ScenarioAssumption`. A Proforma run's view is built
    from its typed answer field by field, and `aggregateExclusion` takes the three fields it reads. Each non-null
    assertion and cast the critic listed narrows with a guard or a local, a lesson's strip plot draws the field its
    argument names only when the ontology holds it, the walk reads the generated `RunReport`, `CatalogueEntry`,
    `DepositionReading` and `Protocol`, and seven libs read a refusal's body through `detailWords`. The exports nothing
    read are gone. An artifact's output stays the engine's own dict, read per tool (Departures; ADR-007's E.gate note).
  - The service: a tool call that fails after a write committed names that write's audit row (`audit.standing`; a
    write the failure rolled back left none), and `runbooks_write`'s refusal of `revise_protocol` says how a protocol's
    version is kept; `TrainMade`'s docstring names its browser reader.
  - smoke runs the service with no key whatever the shell or `core/.env` holds, as the proof's does, opens the seven
    screens beyond the rail an empty project opens (Settings, the catalogues' three other tabs, Flowsheets, the
    protocols and the depositions), and checks that Postdoc's screen says it runs with no key.
  - The walk gains five steps: a lesson taken in from a file with its body and renamed on the form, its body read back
    whole; a skill kept with no policy that its Guild page says so of; a protocol kept after the page opened, found at
    its address, and its editor opened by its address on a fresh load with its steps; and a protocol begun on the page.
  - The two Known debts alpha 2.1 gave stage E move to after stage F, each a commit of its own before the close
    (Departures). ADR-006 and ADR-009 gain E.15 notes, and ADR-007 an E.gate note.
  - Tests: `test_catalogues.py` (a lesson edited as the screen sends it keeps its body; an id refused in words; a row
    of an older shape left out of its catalogue and of every reader), `test_protocols.py` (a row that does not read;
    the size limit), `test_agent_interface.py` (a failed call names the row that stands); `check:state` (the form's
    edit sends the body), `check:guild` (a skills-only version differs, and every compared field).
  - Checks: the changed tests with the tests of the service code they cover, with the database address empty, on
    Python 3.13 and on 3.12, 579 passed each way;
    `pnpm test:sim` 142 passed (5 min 29 s); `pnpm test:core` 2946 passed, 1 skipped, 175 deselected (5 min 25 s);
    `gen:api`, `gen:tools` and `gen:components`, the document, `src/api/types.gen.ts` and `docs/TOOLS.md` regenerated
    and `COMPONENTS.md` as it was; `typecheck`; `check:plan`; `check:state`, 66 checks; `check:figures`;
    `check:guild`, 146 checks; `test:reconcile`; `check:secrets`; `build`; `pnpm smoke` with no key, 20 of 20
    screens, Postdoc's saying it runs with none; `pnpm prove --steps 9`, offline, 52 of 52 checks, the five new
    walk steps among them; `pnpm prove`, offline, steps 1 to 10, 93 of 93 checks in 218 s, the catalogue screen
    in the walk and no call in the proof's spend table; and `pnpm verify`, all sixteen stages in 13 min 7 s (`test:core`
    2946 passed, 1 skipped, 175 deselected; `test:sim` 142 passed; `test:lit` 10 passed; `smoke` 20 of 20 screens with no key).
- E.17. A Proforma scenario's parameter panel row chooses a deposition reading and sends the reading's own value and
  unit (the Known debts row is paid; ADR-006's note of E.17). Built in a worktree beside stage F's live rebuild, with no
  model call (Departures, E.gate).
  - The service: `Override` gains `unit`, the unit a reading's own value is in as a page keeps it, and its validator
    refuses a unit on a person's assumption or a model's estimate in words. The service's sender,
    `proforma.inputs_of` (`project_state.run_request`, which `selling_price`, `run_flowsheet` and `proforma_write`
    read), sends a reading in its own value and unit and every other row in its parameter's unit, as the browser's
    `inputsOf` does, so the lookup holds the reading to its rules at each door and sets it in the parameter's unit, the
    conversion stated in the value's note; `basis.override_of` still returns an Override in the parameter's unit, and
    `standins.as_input` mirrors the senders (Departures, E.17).
  - The panel: `ParameterPanel` takes `readings`, which the scenario page passes and fermOS's and pureOS's panels
    leave off. Each numeric row a person may change then lists, on asking, the readings its parameter may take (`GET
    /api/depositions/readings?unit=`), each drawn by `ReadingChoice`, which moves into `ReadingOrigin.tsx` for the row
    and NewScenarioDialog alike; choosing one keeps the scope's override in the reading's own value and unit, its
    depositor and the time it was taken, with the person's words on why it stands for the parameter. Your value stays
    empty while a reading is set, a typed value or the slider replaces it with the person's own, the row offers a low,
    a high and a basis for a person's value alone, a reading being one value, and a reading the service lists no more
    is said so beside the service's words.
  - The scenario page binds by `laidOn` (`lib/proforma.ts`): a reading laid on as one value held fixed, its source the
    reading, its value shown where its unit is the input's, so the questions for a modeller leave it out. A fit chosen
    for an input set to a reading names the reading, the ceiling check draws a yield set to a reading as measured and
    linked to its deposition, a line names the readings the shown run rests on, and `assumptionOfOverride` answers none
    for a reading.
  - The walk makes a Proforma scenario on `ethanol_glucose_v0` and, on its panel, sets `glucose_price` (`USD kg-1`) to
    the bench's reading (`USD/kg`): the row's chip measured, its words naming the reading as deposited, the project's
    row kept in the reading's own value and unit. The proof reads the row back by the scenario the walk names and asks
    `selling_price` of the kept scenario, which binds the reading from the row with nothing waiting for it and no
    lookup refusal (two checks).
  - Tests: five in `test_measurements.py` (a run, the panel's resolve and a tool, each from a row kept in the reading's
    own unit; the row the panel's path kept before refused in the lookup's words; a unit kept for a reading alone), a
    reading's row served as kept and a unit on a person's value refused in `test_project_state.py`, the optional `unit`
    in `test_route_models.py`, and `test_basis.py`'s round trip of a person's and a model's Override, `ref` and `unit`
    left empty and every other field filled; `check:state` gains nine checks (`inputsOf`, `runBody`, `ceilingQuery`, `laidOn`,
    `modellerQuestions`, `assumptionOfOverride`). `docs/api/studies.md`, `docs/api/runs.md` and the Known debts row on
    the stored panel overrides follow, and the gate's Departures row on the two stage E debts says where and when
    they land.
  - Checks: the changed tests with the tests of the service code they cover, with the database address empty,
    on Python 3.13 and on 3.12, 285 passed each way; `pnpm test:sim` 142 passed (5 min 45 s); `pnpm test:core` 2952
    passed, 1 skipped, 175 deselected (5 min 24 s); `gen:api`, `gen:tools` and `gen:components`, the document and
    `src/api/types.gen.ts` regenerated (`Override.unit`) and `docs/TOOLS.md` and `COMPONENTS.md` as they were;
    `typecheck`; `check:plan`; `check:state`, 75 checks; `check:figures`; `check:guild`; `check:tools`;
    `test:reconcile`; `check:secrets`; `build`; `pnpm smoke` with no key, 20 of 20 screens; and `pnpm prove --steps
    9`, offline, 55 of 55 checks in 109 s, the panel's reading in the walk and no call in the proof's spend table.
- E.18. Studies' run card names each kinetics configuration by its kind and when it was kept (the Known debts row is
  paid; ADR-015's note of E.18). Built in a worktree beside stage F's live rebuild, with no model call (Departures,
  E.gate).
  - The contract: `EngineThing` gains `configurationTitles`, the words a person reads for a configuration by its name,
    optional and `{}` when the engine gives none; each key is one of the thing's configurations and each title words,
    1 to 200 characters, held at every read as `defaultConfiguration` is held to them, so a worker's answer outside
    the rule is `EngineBroken`, its words naming the field. A title enters no basis, id, replay or pin, and the eight
    checks read none (Departures, E.18). `docs/api/engines.md` (the `things()` row, `EngineThing` and its example, the
    kinetics table, Conformance) and `docs/api/workers.md` (the answers outside the shapes, `things`) follow, and the
    contract's sample worker titles one of its two configurations, so a title travels the worker protocol in the
    core's tests.
  - The kinetics engine titles each kept fit, forecast and simulation with its kind and when the project kept it
    (`a kinetic fit, kept <YYYY-MM-DD HH:MM> UTC`, `a forecast, kept …`, `a batch_v1 simulation, kept …`;
    `fermos_engine.configuration_title`, the time as the screens' `stamp` writes one), from the artifacts its listing
    reads already: `_kept` answers each id with its title.
  - The card: `lib/studies.offeredConfigurations` offers a thing's configurations, its default first, each by the
    engine's title beside its name (`<title> · <id>`, as fermOS → Vessel's chooser writes a kept artifact) or by its
    name where the engine gives none, and a thing that takes none in its own; the line for the run the card made
    names its configuration the same way (`lib/pureos.ranWhat`, given the thing's titles), the runs list and the
    comparison page reading it by name as before. `check:state` gains five checks.
  - The mirror stands as built: `examples/engines/openferment-engine-mirror/` is unchanged since `37e6bd0`, its own
    tests pass (30), and the proof's step 10 holds `conform mirror` 8 of 8, its walk running `reflect` from the card.
  - Tests: three new in `test_engines.py` (a thing's titles held to its configurations and to words; a worker whose
    title names a configuration it lists none of broken, its parameters and runs a 503 and the listing naming it with
    the words; a kept artifact's title), and five extended (the sample's title through `GET /api/engines`, the
    kinetics families titling none, the fit and the forecast made of it titled, the stand-in batch simulation titled,
    the `_kept` stand-in answering titles).
  - Checks: the changed tests with the tests of the service code they cover (`test_engines.py`, `test_route_models.py`,
    `test_engine_diagnostics.py`), with the database address empty, on Python 3.13 and on 3.12, 176 passed each way;
    `pnpm test:sim` 142 passed (5 min 37 s); `pnpm test:core` 2955 passed, 1 skipped, 175 deselected (5 min 35 s);
    `gen:api`, `gen:tools` and `gen:components`, the document and `src/api/types.gen.ts` regenerated (`EngineThing`
    alone) and `docs/TOOLS.md` and `COMPONENTS.md` as they were; `typecheck`; `check:plan`; `check:state`, 80 checks;
    `check:figures`; `check:guild`; `check:tools`; `test:reconcile`; `check:secrets`; `build`; `pnpm smoke` with no
    key, 20 of 20 screens; and `pnpm prove`, offline, steps 1 to 10, 96 of 96 checks in 217 s and no call in the
    proof's spend table. On the proof's kept service, a scratch check outside the tree kept a stand-in fit and its
    forecast through fermOS's routes (the tests' own stand-in series): `GET /api/engines` titled the forecast's
    configuration `a kinetic fit, kept <date> <minute> UTC` and the vessel's the forecast and the fit, newest first;
    the card offered each as `<title> · <id>`, ran the forecast and named it so on its Ran line, with no console error;
    the service was stopped and its database dropped after.
- E.19. The Postdoc screen says where conversations are kept, and every screen puts a project's rows with the service
  (the Known debts row is paid; ADR-014's note of E.19). Built in a worktree beside stage F's live rebuild, with no
  model call.
  - Postdoc: the empty list of conversations says the service keeps each conversation with the project, as it has
    since alpha 2.0's stage 6.1 (`docs/api/postdoc.md`): each one is listed after a reload and on every page that
    opens the project (`live-conversations-none`).
  - The search read every sentence under `src/` for words that give a browser or a session a row the service keeps;
    the check below, run before the change, named eighteen of them, and the commit's diff keeps their words. pureOS:
    the Builder's copy of a model's train and a proposal's note say Save keeps the train with the project, and a train
    run whose train the Builder lacks says a model or a tool built it, or it waits to be saved in the Builder. Guild: a
    check's entry and a person missing from the ledger name the project's ledger as the page last read it, and the
    review queue's empty words, its auto-fill line, a queue entry that no longer resolves and a corrected record's
    callout name the project's extractions, records and decisions. Witness's gold set, Intake's records of a document,
    the protocol compare's versions and the lesson embeds' queue, gold set and strip plot name the project; Settings
    names the lesson catalogue; a review decision made while the service is away says it waits in this browser and is
    sent when the project next loads with the service answering; and Home's list of activity, the page's own, says
    nothing has happened since the page opened. The comments of pureOS's two screens follow.
  - The check: `pnpm check:state` reads each file under `src/` with the TypeScript parser, a sentence being a string
    or a template, a JSX attribute's words, or one element's text with the strings of its expressions (the words of
    comments are the code's own), and holds every sentence to ADR-014: one that keeps something in this browser names
    a write that waits for the service or a preference, a browser owns no row, and a session holds what it loaded.
    Run before the words changed, it named eighteen of the nineteen sentences above (Home's title names no keeping);
    it reads 19,166 sentences now and names none. A second check reads Postdoc's empty list, and `pnpm smoke` reads it
    on the screen of the empty project it opens.
  - Checks: `typecheck`; `check:plan`; `check:state`, two checks more, 82 in all, which fails on the words before this
    commit, naming the eighteen; `check:figures`; `check:guild`; `check:tools`; `test:reconcile`; `check:secrets`;
    `build`; `pnpm smoke` with no key, 20 of 20 screens, Postdoc's list saying the service keeps each conversation;
    `gen:api`, `gen:tools` and `gen:components` with `--check`, each file as the code writes it; `test_guidance.py`
    and `test_no_seed.py`, which read the docs and the decision record this commit changes, with the database address
    empty, on Python 3.13 and on 3.12, 53 passed each way; and `pnpm test:core` 2955 passed, 1 skipped, 175 deselected
    (5 min 49 s). No Python changed, and neither the walk nor `prove.py`, so `test:sim` and `pnpm prove` did not run.
- E.debts. The review of E.17, E.18 and E.19: fifteen findings, three of them should-fix, each confirmed against the
  code and each fixed (ADR-006's note of E.debts). Built in a worktree beside stage F's live work, with no model call.
  - Who chose a reading: an override keeps it in `chosenBy`, a reading's alone (a person's value or a model's estimate
    naming one is refused in words), which the panel fills with the reviewer and `project_state` writes as the row's
    maker, `by` staying the depositor; each keep that sets a parameter to a reading its scope did not hold, or the
    same reading chosen by another person, writes a `choose_reading` audit row, and the row's Readings say who chose
    it. The state door keeps a reading in its own unit on a Proforma scenario's scope alone, and refuses one on a
    pureOS or fermOS scope in words.
  - The row's words when the readings list cannot load: `params.readingLeftTheList` says a reading has left the list
    only when the service answered with a listing that lacks it, and `check:state` holds three cases.
  - The Proforma scenario page's words on a person's assumptions: the inputs card, the shelf notes of `plant_scale` and
    `glucose_price`, the read-back's groups (a composite's Finance value set to a reading is credited to its depositor
    as a reading, held by `check:state`), the words of a Proforma panel's value that waits for a source and the
    refusals of a run with one name a reading deposited at the bench beside a person's assumption. The panels of
    fermOS and pureOS offer no reading and keep their words (`params.READINGS_OFFERED`): a kinetics run keeps them in
    its outputs, and the fed-batch pin's output hash moved when they changed, so they stand as they were.
  - The minors: a worker's `configurationTitles: null` reads as `{}` (a test), and `docs/api/workers.md` lists a blank
    title and one past 200 characters among the breaks; the panel's detail line says when a reading was taken to the
    minute, and a reading's value note leaves the converter's name out, so a run on a reading in another unit than its
    parameter's takes a new id and every pin holds; the run card lists the engines again after a run made there, the
    runs table names a configuration by its title, and a refusal's summary carries the first clause after
    `<thing> refused:`; a comparison with no maker is set side by side for nobody named, the reset's words say this
    browser then holds none of the project's rows, the panel says a change waits in this browser while the service
    is not running, and `check:state` names a browser drawn where a person's name stands; Guild's empty queue tells
    a project with no extraction that it holds none yet; two comments; and the three log lines above count
    `check:state` as their trees run it, 75, 80 and 82.
  - Checks: the touched tests (`test_basis.py`, `test_engines.py`, `test_measurements.py`, `test_proforma_ethanol.py`,
    `test_project_state.py`, `test_route_models.py`, `test_params.py`, `test_tools.py`, `test_proforma_runs.py`,
    `test_proforma_shelf.py`, `test_proforma_overrides.py`, `test_engine_pins.py`) with `test_guidance.py` and
    `test_no_seed.py`, the database address empty, on Python 3.13 and on 3.12, 488 passed each way; `gen:api`,
    `gen:tools` and `gen:components` with `--check`, the document and `src/api/types.gen.ts` regenerated
    (`Override.chosenBy`); `typecheck`; `check:state`, four checks more, 86 in all, whose new rule names
    `ProformaComparison.tsx` on the words before this commit; `check:figures`; `build`; `pnpm smoke` with no key, 20
    of 20 screens; `pnpm prove --steps 9`, offline, 55 of 55 checks in 89 s, the walk's reading chosen and kept in the
    reviewer's name, and no call in the proof's spend table; `pnpm test:sim` 142 passed (4 min 35 s); and
    `pnpm test:core` 2960 passed, 1 skipped, 175 deselected (4 min 30 s).
- E.20. The stage E gate's leftovers, and stage F.1's two screen faults. Built in a worktree beside stage F's live work,
  with no model call.
  - The seven casts that hid a generated optional or nullable field, each narrowed where the value can be absent:
    CostWaterfall's row carries its own label and number and says a number it lacks as a dash; StrainPage reads a
    point whose value converts into its field's unit through a guard (`converted`), the plot and the statistics
    taking those alone and the page counting the rest as unconvertible in words, and a field's facet label reads a
    field the ontology names by its name and any other by the record's words; ProformaComparison's Tornado draws a
    row whose every later change is a number, and the table says the others' changes as a dash; PaperReader finds a
    paper's most named field in a loop the compiler follows, and asks of the paper as a whole when it holds no
    record; Settings' conversion playground takes a field the ontology names and leaves the field as it stands for
    any other value.
  - Home's fermOS tile says what fermOS holds: the deposited runs it can fit (`lib/fermos.qualifies`), and its fits,
    forecasts, simulations and vessel designs kept with the project, and the tile is drawn as a built destination's.
  - A person's catalogue keep, by the route or from a file, writes its audit row in the keep's own transaction, as
    `project_state` and `protocols` write a person's: `keep_catalogue` under the module that reads the kind
    (`catalogues.MODULES`, which `catalogue_write` now reads too), its target `<kind>/<id>`, a file's rows naming the
    file; `catalogue_write`, in a person's lane or a model's, stays audited by its tool alone, and a keep refused is
    audited as nothing (`test_catalogues.py`; `docs/api/intake.md`).
  - Stage F.1's screen faults: the extraction's job, its activity line and its toasts name the document by its title
    where the project holds one, by the kit's id otherwise, and a job names its document by id in `Job.subject`,
    which Intake, BioRepo and the paper's page find it by; the toast's words break inside a long unbroken word, so its
    Open Witness and dismiss buttons stay inside its 340 px.
  - Checks: the touched tests (`test_catalogues.py`, `test_catalogue.py`, `test_mcp_service.py`,
    `test_agent_interface.py`, `test_tools.py`, `test_openapi.py`, `test_protocols.py`, `test_route_models.py`) with
    `test_guidance.py` and `test_no_seed.py`, the database address empty, on Python 3.13 and on 3.12, 261 passed each
    way; `gen:api`, `gen:tools` and `gen:components` with `--check`, the document and `src/api/types.gen.ts`
    regenerated (the two catalogue routes' words); `typecheck`; `check:state`, 86 checks; `check:figures`;
    `check:secrets`; `build`; a page with the built stylesheet drew the toast with a 32-character id, its Open Witness
    button 62 px past the toast's edge as the toast stood before this commit and inside it after; `pnpm smoke` with no
    key, 20 of 20 screens; `pnpm prove --steps 9`, offline, 55 of 55 checks in 87 s and no call in the proof's spend
    table; `pnpm test:sim` 142 passed (4 min 29 s); and `pnpm test:core` 2961 passed, 1 skipped, 175 deselected
    (4 min 35 s).

### Alpha 2.2 — Stage F — 2026-11-05

The live work (the prompt's §6.7 and §7): F.0 to F.2 on the routes of its §4 as `core/.env` held them, and from
F.2f on, on `llm.ROUTES`' defaults (ADR-008, Implementation 17);
`docs/reports/live-questions-2026-11.md` holds the numbers in its section of 5 November.

- F.0. `pnpm ready --probe` answered at 08:26 UTC on 5 November on the index route (`claude-haiku-5-5` at effort
  low, the route's one model), 0.000004 USD, so the account answers and stage F runs. Its row is in the spend table
  the rename of F.1 carried to `openferment_dev_alpha21`.
- F.1. The Ethanol project rebuilt from nothing, on the screens.
  - Before it: the tree clean at `3b40de6`, equal to `origin/claude/alpha-2-2-base`; 0 sessions on
    `openferment_dev`; `pnpm build` (20 s).
  - The rename. At 08:52 UTC alpha 2.1's development database was renamed `openferment_dev_alpha21` in one guarded
    chain through the maintenance database (0 sessions on it, the new name free, `ALTER DATABASE openferment_dev
    RENAME TO openferment_dev_alpha21`, both names read back), and `pnpm db:reset openferment_dev` made a fresh
    `openferment_dev` at the heads (`openferment` 0010, `sci_rag` 0006) with 0 projects. Why: the rename keeps
    alpha 2.1's project whole and readable with SELECT for the reports' earlier numbers (1 project, 22 document links
    and 22 extraction rows at migration 0009, with F.0's probe row), and the fresh database is the one a fresh
    container starts from, as the prompt's §0 and §6.7 describe the rebuild. There the kit ingests every document
    anew, so the rebuild measures the parsing, chunking and embedding a fresh container makes; the project keeps the
    id `ethanol` that the drivers, the evaluation commands and the reports name; the database stands at the tree's
    heads; and the fourteen questions are seeded as the code holds them now. It reverses with `python -m
    openferment_core.migrations drop openferment_dev`, then `ALTER DATABASE openferment_dev_alpha21 RENAME TO
    openferment_dev`. It is a cloud container's development database; the rename moved it whole, and its rows stay
    as they were.
  - The service on 127.0.0.1:8800 alone, from that tree, with `OPENFERMENT_DATA_DIR` on a copy of the fetched
    caches: health ok with the key, and the routes and caps of §4 (150 USD a day, 8 USD an ask).
  - The rebuild, each step in Chromium on the screens with "Claude Code (build session)" typed in Settings as the
    person's name: "Ethanol" made on Home at 08:58 UTC (id `ethanol`); the 22 identifiers of
    `docs/corpus/ethanol-sources.txt` collected one at a time on Intake's Identifier form (08:58 to 09:02 UTC), each
    `ingested` on its first try, 814 passages in 180 s of collecting, the board reading "22 held" with 0 refused;
    Extract on every held document on the `extract` route, Opus then Sonnet at effort high (09:02 to 09:16 UTC), one
    extraction call each: 457 candidates kept and 54 refused, all 54 by the unit rule, partial 0, Opus declining nine
    papers in `bio` and Sonnet answering each; and three warm-up runs from Studies' run card on the package's own
    values (`cornstover`, and `cellulosic_ethanol_v0` in dilute acid and in hot water, each with IB), each done and
    `computed` with its SFF file, each run's id the one `openferment_dev_alpha21` holds for the same plant and
    configuration.
  - Cost and time: 5.3780 USD over 31 model requests, 22 answers and the nine declines (1.2168 USD of it the
    declines); 803 s of extraction, 24 s a document at the median and 151 s at the most. The day over every database
    read 5.377954 USD against the 150 USD cap, and the account answered every call.
  - For the owner: all 457 candidates wait for review; the project holds 0 decisions, 0 records and 0 depositions,
    and its audit table one row, the project made on Home.
  - One screen fault joins the stage's list: the extraction's toast names its document by the kit's 32-hex id, as
    the job's title and the activity line do, and the unbroken id widens the toast past its fixed 340 px, so its Open
    Witness button sits outside it at 1440 px (`src/store.ts` 1462, 1470 and 1482; `src/components/ui.tsx` 364-386);
    fixed at E.20 (`448adbb`). The drivers recorded 0 console errors, 0 page errors, 0 failed requests and 0 API answers of 400 or above.
  - Checks: `pnpm test:core` on the final tree, 2946 passed, 1 skipped, 175 deselected (5 min 20 s).
- F.2a. The evaluation the model comparison reads, landed before the ethanol suite is seeded (ADR-008,
  Implementation 14; `docs/api/postdoc.md`, the evaluation set). A run keeps the seconds to the loop's first
  step, to the model's first step and to the answer, timed through the answer path's `on_step`, with the
  loop's stop, its restart steps and the validator's reasons (`EvalRun.firstStepSeconds`, `firstModelSeconds`,
  `stopped`, `restarts`, `dropReasons`, each empty on a row kept before); a judgement keeps the models its
  route tried and the route itself (`Judgement.tried`, `route`). `pnpm eval judge` reads `core/.env` as
  `pnpm eval run` does, importing the service module first (its loader, `override=False`); it had read no key,
  no routes and the default cap, so each judgement it kept was a decline naming the missing key. A judge none of
  whose route's models answers stops `run --judge` and `judge` in words with exit 1, keeping no judgement for
  the run it was judging and naming the commands that go on. `pnpm eval summary` counts each run once for each
  judge model by its newest judgement and gives each tag's code scores, each judge's scores, answers judged,
  declines and cost, each judge route's fallbacks and declines, how far the two judges' scores of the same
  answers lie apart (per tag and pooled, an answer one judge left unscored counted beside the pairs), the
  declined plans and the restarts, the claims kept and dropped with the drop reasons by kind, the tool calls,
  the median seconds, the stops and the cost per question and in all; `--rows` adds each tag's newest run of
  each question; `--only` asks or judges the questions it names under a tag, a follow-up in the conversation
  of its question's newest run there. Question 4 follows question 3, as the owner's screen asked it. A model's
  write carries the plan route's effort on its audit row (`tools/writes._plan_effort`), `core/.env`'s single
  setting where the table names none or cannot be read. `JUDGE_TOKENS` and the loop's bounds stay as they are.
  Tests: `test_evaluate.py` (13 new, 3 changed), `test_writes.py` (1 new). Checks: the two files with the
  database address empty, on Python 3.13 and on 3.12, 73 passed each way; `gen:api`, `gen:tools` and
  `gen:components --check`, each file as it was; `pnpm test:core` 2960 passed, 1 skipped, 175 deselected
  (5 min 55 s); `pnpm prove --steps 6`, offline, steps 1, 2 and 6, 16 of 16 checks in 101 s, no model call.
- F.2a review. The review's nine findings, each confirmed and fixed (ADR-008, Implementation 14, the review's note;
  `docs/api/postdoc.md`). A judged run that stops at a question no model of the plan route answered either (the
  account's limit most often lands on a plan call first: no claim, a final step `No answer: …`, a decline in
  words `evaluate.REFUSAL` leaves unmatched, `evaluate.unanswered`) says to ask that question again with the rest, beside the questions a full asking
  asks in its conversation before it when it follows one, and names no judge command for it. `--only` asks a
  follow-up in its question's conversation when that conversation holds what a full asking has it read before it,
  and refuses in words, naming the questions to add, a follow-up that would read its own earlier asking, miss a
  question asked ahead of it, or follow an unanswered one. `llm.Result.refused` and `Judgement.refused` name the
  models the safety classifier declined, so each judge's `refused` stands apart from its route's other pass-overs
  (a 529, a model the key cannot reach), which `declined` counts beside them; a stop names what the judge route spent
  on the call it stopped at (`spentAtStopUsd`, in its words and its JSON); the summary counts the restarts by kind
  (`restartCount`); each row gives each judge's verdict cut to 200 characters; the docs say a tool's own time is in
  `firstModelSeconds` and that the cost totals cover the newest runs. F.2a's ADR and log lines say what the judge
  pass had read in plain words. `test_llm.py`'s local-model test gets a stand-in client, so it holds alone with no
  key (it had read a key another test leaves in the environment). Tests: `test_evaluate.py` (5 new, 9 changed),
  `test_llm.py` (3 changed, 1 made to hold alone). Checks: `test_evaluate.py`, `test_llm.py` and `test_writes.py`
  with the database address empty, on Python 3.13 and on 3.12, 157 passed each way; `gen:api`, `gen:tools` and
  `gen:components --check`, each file as it was; `pnpm test:core` 2966 passed, 1 skipped, 175 deselected (5 min
  40 s); `pnpm prove --steps 6`, offline, steps 1, 2 and 6, 16 of 16 checks in 64 s, no model call.
- F.2c. The judge's room set by measurement (ADR-008, Implementation 15; `docs/api/postdoc.md`, the evaluation set).
  The haiku table's fourteen answers, judged on its judge route (`claude-opus-5-5` then `claude-sonnet-5-5` at effort
  max) with `JUDGE_TOKENS` at 16,000, lost three judgements to the ceiling (eq-eth-01, 02 and 03, each kept with no
  score, its `declined` saying the judge's answer ran out of room), and five more wrote about 14,000 to 16,000 tokens
  by their cost. `JUDGE_TOKENS` is now 32,000, the plan's own turn ceiling (`postdoc/plan.py`, `MAX_TOKENS`), the
  step's one line of Python, and `pnpm eval judge --suite ethanol --tag haiku` judged the table's fourteen newest runs
  again on the table's own judge route (11:45:48 to 12:20:29 UTC, exit 0), each run keeping both judgements and the
  summary reading the newer, so the four tables are judged at one setting. All fourteen arrived whole, each given by
  `claude-opus-5-5` with no fallback and no refusal; the largest wrote about 23,900 tokens (eq-eth-01), and five wrote
  past 16,000. A judgement cost 0.3346 USD on the mean and 0.5183 at the most, against 0.2928 and 0.3853 at 16,000;
  the pass spent 4.6846 USD over 14 calls, each spend row equal to its judgement's cost, and the day over every
  database read 9.754722 USD before it and 14.439322 after, against the 150 USD cap. Opus's means over the fourteen,
  by its newest judgement of each: answers 0.601, grounded 0.646, labelled 0.938, coverage 0.589 (0.573, 0.595, 0.923
  and 0.573 over the eleven it scored at 16,000). Each token count comes from a judgement's cost, since neither a
  judgement nor a spend row keeps tokens (Implementation 15 says how). Checks: `test_evaluate.py` with the database
  address empty, 31 passed.
- F.2c, the other three tables, asked on 8 November one at a time with the machine quiet (`pnpm eval run --live
  --suite ethanol --tag <tag> --judge`, each table's routes in `OPENFERMENT_ROUTES`, the judge route Opus then Sonnet
  at effort max with `JUDGE_TOKENS` at 32,000). sonnet: 14 of 14 (02:27 to 03:01 UTC), answers 2.4974 USD and
  judgements 4.4227; Opus's means answers 0.656, grounded 0.540, labelled 0.882, coverage 0.625. opus-high: 14 of 14
  (03:07 to 03:53 UTC), answers 6.5359 USD and judgements 5.3676; answers 0.787, grounded 0.662, labelled 0.942,
  coverage 0.760. opus-max: 4 of 14 (eq-eth-01 to eq-eth-04, 04:00 to 04:22 UTC), each at the 24 tool calls and its
  answer out of room at 32,000 tokens (F.2g), answers 5.5457 USD and judgements 0.2421; the runner then reached the
  session's two-hour limit for a background command and stopped. Asked again from eq-eth-05 with `--only` at 04:26,
  the Anthropic account's own usage limit refused the next call at 04:28 ("You will regain access on 2026-12-01 at
  00:00 UTC"); eq-eth-05's run keeps that decline in words (0.2822 USD for the tool calls before it), and the table's
  other nine wait on the account. Every judgement made at 32,000 arrived whole (32 of 32), each given by
  `claude-opus-5-5` with no fallback. The day over every database: 25.28448 USD settled (`openferment_dev`),
  against the 150 USD cap; one hold of 0.9821 USD left by the stopped runner settles nothing and expires.
- F.2g. The plan's room set by the route's effort (ADR-008, Implementation 16): `postdoc/plan.py` gains `ceiling`,
  `MAX_TOKENS` (32,000) at high and below, 64,000 at xhigh and 128,000 at max, and `postdoc_agent` sizes each turn to
  it within the question's budget. Tests: `test_postdoc_agent.py` two new (48 in the file, 3.13 and 3.12), one
  holding the three levels and one holding the tool turn and the answer after a stop at the larger room, effort high
  at 32,000 and a spent budget at the floor. The measure of the larger room waits on the account (Blockers).
- F.2e and F.2f. The report and the defaults (ADR-008, Implementation 17; `docs/reports/model-routing-2026-11.md`,
  the section of 8 November 2026, alpha 2.1's text kept above it, its one strain name cut from sonnet Q2's quoted
  words, and its "To finish it" marked finished here as far as the account allowed). The section holds the method
  (the rebuilt project, the fourteen and what each expects, the four tables as JSON, the judge and its room, one
  table at a time with the machine quiet), one row a table for every quantity of the summary, the per-question rows,
  the judge's words paraphrased to what it found about each answer, question 14's footnote, what the account's limit
  left unasked, the decision and a new "To finish it" (the larger room's measure on eq-eth-01 to 04, then opus-max's
  rest, both on the opus-max table under the tag `opus-max-room`, so its fourteen at 128,000 make one summary row;
  the Sonnet pass; the summary; each with its routes). With one judge, the rule of §6.7 is worked against the
  judge's disagreement with itself, taken as a floor under the two judges' disagreement: Opus judged eleven haiku
  answers twice whole (eq-eth-04 to 14, the same request at 16,000 and at 32,000), mean absolute difference answers
  0.023, grounded 0.041, labelled 0.032, coverage 0.045. opus-high stands above haiku past it on answering (+0.186,
  higher on 11 of 14) and coverage (+0.171, 9 of 14), within it on grounded and labelled, and above sonnet past it
  on all four; the code's tools and citations point the same way; opus-max's four answers hold no claim and stay out
  of the rule, and eq-eth-05's refused run out of every mean. The decision rests on one judge, the same model as the
  opus tables' plan model, so a judge's preference for its own model's answers is unmeasured until the Sonnet pass;
  effort medium, the old default, was asked in no table. The defaults in `llm.ROUTES`: `plan` Opus then Sonnet at
  high (the opus-high table); `explain` Opus then Sonnet at high, held there until the retrieval report's answer
  lane measures it; `extract` Opus then Sonnet at high (F.1: Sonnet answered the nine documents Opus declined in
  `bio`); `index` Haiku alone at low (F.0's probe, its one call; every table held it there, and none of their calls
  reached it); `judge` Opus then Sonnet at max with `JUDGE_TOKENS` 32,000. `routes()` starts from `ROUTES` and lays
  a plain setting over the families it covers when the environment sets it: the answering chain and the effort over
  plan, explain and extract (`llm.ANSWERING`), the index model over index's first model; judge and index's effort
  keep their defaults under every plain setting and move with `OPENFERMENT_ROUTES`, laid last, so the live-host
  runbook's four settings leave every family at its default. `DEFAULT_EFFORT` is high. `GET /api/health` names the
  plan route's models, its `fallbackModel` joined the same way on both paths, and the Postdoc screen's "Working on"
  after a restart names the first of them; `pnpm ready`'s model row names the plan route's models and effort, and
  its roles row says when the index route holds no other model the key lists; `core/.env.example`'s routing comment
  says each default and where it rests. This container's `core/.env` set `OPENFERMENT_EFFORT=max` and laid the
  prompt's §4 table through `OPENFERMENT_ROUTES` (`plan` at max); its five routing lines are commented out in place
  after this commit, the budgets and the key kept, so F.3 asks on the defaults. Tests: `test_llm.py` (2 new, 4
  changed), `test_ready.py` (1 new, 1 changed), `test_api_intake.py` (1 new, the health test), `test_writes.py` (1
  changed, the single setting's default). Checks: the four files with the database address empty, on Python 3.13 and
  on 3.12, 203 passed each way; `gen:api` regenerated for the health docstrings, then `gen:api`, `gen:tools` and
  `gen:components`, each with `--check`, each file as the service writes it; `pnpm typecheck` and
  `pnpm check:secrets`; `pnpm test:core` 2972 passed, 1 skipped, 175 deselected (4 min 54 s).
- F.5.1. The model layer the retrieval lanes stand on (the F.5 plan's §3 item 1; the orchestrator's decisions 2 and
  8). `llm.tally()` opens a run's own count: within it every `llm.call` adds one `llm.Spent`, an answer, a refusal
  and an outage alike, holding the family and effort it ran at, the ceiling it asked, its outcome (`answered`,
  `refused` or `unavailable`), the model that answered, the models asked and those the safety classifier declined,
  its tokens and USD, how the answer stopped, and a failure in the words its caller was given. Tallies nest, and a
  context copied from a tally's carries it: a thread `asyncio.to_thread` starts, and a coroutine `db.run` hands to
  the database loop (measured on Python 3.12.3 and 3.13.17, where a thread `threading.Thread` starts begins with an
  empty context); outside every tally nothing is kept. `call`'s body moves to `_call`, and a model counts as asked
  once its reservation holds, so a call the daily cap refuses names no model. `KIT_ROLES` gains `draft`, the role
  openFerment names for the kit's drafter of seed questions, on the `extract` route; each kit call asks the larger
  of the kit's ceiling and the room for thinking its route's effort sets (`KIT_ROOM`: low 0, medium 4,096, high
  8,192, xhigh 12,000, max 16,000), the live Search answer's call among them. ADR-008's note on the room, the role
  and the tally comes with the plan's records (its §3 item 15). Tests: `test_llm.py` (7 new). Checks: `test_llm.py`
  and the thirteen files that reach `llm.call`, the kit or the package map, with the database address empty, on
  Python 3.13 and on 3.12, 333 passed each way; `gen:api`, `gen:tools` and `gen:components --check`, each file as
  it was; `pnpm test:core` 2973 passed, 1 skipped, 175 deselected (6 min 8 s); `pnpm test:lit` not owed
  (literature/ unchanged, and its tests hand the kit its own `MockLLM`).
- F.5.2. The concept graph a project builds and reads (the F.5 plan's §3 items 2, 3 and 12; its decisions 1 and 2;
  ADR-002, Implementation F). `literature/graph.py` builds the graph over the project's unread chunks alone, in the
  kit's order, ten to a batch through the kit's own batch step (`_extract_with_recovery`, its signature pinned), on
  the client the caller hands in, with `stop` read after each batch; a chunk of a document two projects hold is read
  once. Its reads show what the project's own passages prove: an entity where a passage of the project names it
  (aliases left out), its description where every document naming it is the project's, an edge where its evidence
  passage is the project's and both ends are its entities, with its document and passage id, its quote where its
  words stand in that passage, and counts over the project's passages alone; a project no build has read is told
  the command that builds it. `ProjectService` gains `search_entities`, `entity_relationships` and `fingerprint`;
  `stats` counts the project's graph and 0 communities (the stats route's words, `docs/api/intake.md`). The
  orchestrator's narrowing (8 November) leaves the kit's question drafter out, so ADR-002 names three kit roles.
  Tests: `test_literature_graph.py` (16 new: two projects, neither reading the other's entities, edges or
  descriptions), `test_literature_kit.py` (1 new, 1 changed). Checks: the twenty files the change reaches, with the
  database address empty, on Python 3.13 and on 3.12, 435 passed and 1 skipped each way; `gen:api`, `gen:tools` and
  `gen:components --check`, each file as written; `pnpm test:lit` 10 passed; `pnpm test:core` 2990 passed, 1
  skipped, 175 deselected (5 min 39 s, on this Python tree as committed).
- F.5.3. The kit's two graph tools back on the `sci-rag` server, each reading the project's graph alone (the F.5
  plan's §3 items 4 and 13; ADR-002, Implementation F; the Known debts row on the kit's two graph tools paid). `literature_mcp.build` removes the
  kit's `search_entities` and `get_entity_relationships`, which query the store whole, and adds openFerment's own
  under the same names and argument schemas, each calling `ProjectService.search_entities` or
  `entity_relationships` through `InWords` (the project asked for first, every failure in words), each description
  naming the domain's entity or relation types; a graph tool asked of a project no build has read is refused in
  `NO_GRAPH`'s words, the command that builds its graph among them. `docs/TOOLS.md` gains the sci-rag server's
  section, its tools listed from the server's own listing over `literature_mcp.Unopened` (a service that holds the
  domain profile and opens nothing), with how it starts and the scope its graph tools read in. CLAUDE.md's MCP line
  says so. Tests: `test_literature_mcp.py` (3 new, 1 replaced, 3 cases added to two refusal tests),
  `test_literature_graph.py` (1 new: the two tools over two projects' graphs, neither reading the other's),
  `test_agent_interface.py` (1 changed). Checks: the seven files the change reaches, with the database address
  empty, on Python 3.13 and on 3.12, 107 passed each way; `gen:api`, `gen:tools` and `gen:components --check`, each
  file as written; `pnpm test:lit` 10 passed; `pnpm test:core` 2997 passed, 1 skipped, 175 deselected (5 min 8 s).
- F.5.4. The report's project lanes and the command that runs them (the F.5 plan's §3 items 9 to 11 and 15, under the
  orchestrator's narrowing of 8 November; ADR-002, Implementation F; ADR-008, Implementation 18). `report.truth`
  builds a project's ground truth by code from its kept candidates at run time: a candidate counts when its passage
  is the project's, its quote stands in that passage (whitespace aside) and its field is the ontology's; one question
  a group by document, passage and field, the documents taken in turn, its evidence the group's quotes, its relevant
  passage their chunk, tagged `from-candidates`. No model writes or reads a question, so F.5.1's `draft` kit role
  goes and the kit's roles are three. `report.lanes` asks each question in `interactive`, `vector_only`,
  `keyword_only`, `full_deep`, `no_graph` and `no_hyde`, scored under the kit's rule and the passage rule, the graph
  and HyDE stages' statuses counted, `no_retracted` and `with_citations` refused by name; with `--judge` the `judge`
  route grades each question's top ten in `interactive` and `full_deep` (0 to 2), and the kit's answer through each
  profile, on `explain`, is graded blind for grounding on `judge`, each answer and each judgement under its own
  tally. `report.public` keeps a run's numbers alone (scores with intervals, counts, question ids, model ids, USD,
  seconds), and `report.write` sets them beside the demo in `docs/reports/literature-retrieval.md` and `.json`,
  whose JSON of the old shape reads as the demo. `literature_live.py` runs `graph` (`--dry-run` measures the batches'
  prompts, `graph.prompts`, and their cost on the route's first model, calling nothing) and `report` (the run whole
  written to `<data folder>/literature/<project>-<UTC time>.json`, gitignored; `--render`, and `--from` a kept
  file); it reads `core/.env` through `extract.load_env` (`override=False`), installs `llm.kit_client`, stops after
  the batch or question whose call no model answered (`Watch`, read from its own tally), and audits each build and
  run (`literature_graph`, `literature_report`, module `intake`, the person `--by` names). `literature/` imports no
  `llm` and no `spend` (the command hands in the tally and the stop). `package.json`'s `lit:graph` and `lit:report`
  run it; `pnpm lit:report` alone stays the demo, offline. Proof step 3 starts the sci-rag server over stdio in the
  proof's project, lists its tools with the two graph tools, reads `search_entities` refused in `NO_GRAPH`'s words
  and `corpus_stats` counting the project's documents. Words: ADR-002, ADR-008 (Implementation 18: the tally and the
  room), `docs/api/intake.md`, CLAUDE.md's `lit:report` line; the Known debts row on a retrieval report with the lanes that call a model says
  the live run waits. Tests:
  `test_literature_report.py` (11 new, one over three configurations: two projects, neither building a question from
  the other's candidates nor retrieving the other's passages), `test_literature_live.py` (6 new),
  `test_literature_graph.py` (1 new), `test_llm.py` (1 changed, 1 removed). Checks: the ten files the change
  reaches, with the database address empty, on Python 3.13 and on 3.12, 217 passed each way; `gen:api`, `gen:tools`
  and `gen:components --check`, each file as written (COMPONENTS.md regenerated); `pnpm test:lit` 10 passed; `pnpm
  prove --steps 3`, offline, steps 1 to 3, 19 of 19 checks in 40 s, no model call; `pnpm test:core` 3016 passed, 1
  skipped, 175 deselected (5 min 10 s).
- The landing (8 November). The two worktrees' commits land on the branch by cherry-pick from the main checkout, each
  read first and each keeping its own message: w1's five (`alpha22-e-debts`, cut at `3b40de6`) as `7e178bb` (E.17),
  `09e95dd` (E.18), `b70fa83` (E.19), `8bde8ab` (E.debts) and `448adbb` (E.20), their log lines in stage E's section;
  then w2's four (`alpha22-f5`, cut at `0bd047e`) as `2795aa7` (F.5.1), `8e2ec88` (F.5.2), `19d129a` (F.5.3) and
  `adb9c8d` (F.5.4), their log lines after F.2e and F.2f. Each conflict was a log line both sides appended, save two
  in F.5.4: `test_llm.py`'s room test, taken as F.5.4 wrote it, and ADR-008, where F.5's note follows
  Implementation 17 as Implementation 18, F.5.4's two lines here naming it so. F.5.1's pick names the judge's 32,000
  tokens in `llm.KIT_ROOM`'s comment, and two of its seven new tests read the defaults of Implementation 17, which
  F.5.1 was written before: its tally test sets `explain` at high and `judge` at max, and its room test set `explain`
  at medium at F.5.1's pick, F.5.4's version, the one taken, setting it at high. `adb9c8d`'s message names F.5's note
  Implementation 15, its number on w2's base; the tree holds it as Implementation 18. Every
  generated file stood as the code writes it after each pick. Checks: after each pick its changed tests with the
  tests of the code they cover, with the database address empty, on Python 3.13 and on 3.12, each set green both ways;
  `pnpm test:core` after each series, 2987 and then 3037 passed, 1 skipped, 175 deselected; and on the final tree
  `gen:api`, `gen:tools` and `gen:components --check`, `check:secrets`, `check:plan`, `check:state`, `check:figures`,
  `check:guild`, `check:tools`, `pnpm test:sim` 142 passed, `pnpm test:lit` 10 passed, `pnpm build`, `pnpm smoke` with
  no key on 20 of 20 screens, and `pnpm prove`, offline, steps 1 to 10, 99 of 99 checks in 195 s with no model call
  (Last green runs). Every check held, so this record is the one commit after the picks.
- The landing review (8 November). Three reviewers read `2ed7dac..9a06a88`: the merge of the two series, the scope
  of F.5's code, and the records. Each finding was checked against the tree, and each that held is fixed here, with
  no model call.
  - The concept graph's build cuts its batches at each document's end (`graph.batches`, which `prompts` reads too).
    The kit writes one description a name from the whole batch and files each entity and edge against the passage
    numbers the model names, so a batch that mixed a document two projects hold with one project's own could carry
    that project's words into the other's reads; the scope review's probe showed a description and an edge statement
    reaching the other project. A document shorter than ten passages takes a call of its own, and the dry run counts
    the calls. An edge is the project's where its own passage names both its ends, so a name another project's build
    kept as an alias, which the kit joins to that entity at build time, renames no edge of this project. Every entity
    listed with no description carries one note (`DESCRIPTION_NOTE`), the same for a description withheld and one no
    model wrote. A project that holds no passage, a store that holds no project of the id among them, is told its
    documents enter on Intake (`NO_PASSAGES`), and the `sci-rag` server refuses its graph tools in those words too
    (ADR-002, Implementation F).
  - `--limit` counts one at least (`literature_live._count`; `graph.pending` and `report.truth` read None alone as no
    limit). `report --from` rebuilds the part it renders from the kept run whole (`report.public`), filed under the
    run's own project, and refuses a file that holds no `literature-lanes` run. The dry run and `--from` install no
    model client, and `--from` reads no store.
  - `llm.KIT_ROOM` at max is 32,000, the room of openFerment's own judge (`evaluate.JUDGE_TOKENS`, a test holding the
    two equal): Implementation 15 measured 16,000 too small at max, and Implementation 17 set the `judge` route there.
    ADR-008's Implementation 18 says so, names the answer lane as the measure `explain` waits on, and says what a
    batch the index route declines meets; `llm.py` names Implementation 18 beside its code. The room test gains
    `explain` at medium and at xhigh.
  - The `sci-rag` server describes the kit's `answer_question` and `list_sources` in openFerment's words
    (`literature_mcp.DESCRIBED`), and `docs/TOOLS.md` says which tools are the kit's own and which are openFerment's.
  - Records: Resume, Current stage (stage F's paragraph and E.17 to E.20), the Decisions rows of ADR-002, 006 and 008,
    the key override's Departures row, Blockers' next command in the routing report's order, stage E's Spend row, Live
    owed, the order of Last green runs, the landing's entry, and words held to the writing preference here, in
    ADR-002, in `docs/api/postdoc.md` (with a section on the routing table), in `docs/api/intake.md`, in CLAUDE.md, in
    `core/.env.example` and in the live-questions report, which names the strains no more.
  - Left for the owner: the dry run and `--from` still read `core/.env` whole through `extract.load_env`, and reading
    only the database address and the routes there would change how the key is read, a stop condition; the organism
    the cellulosic recipe declares stays named in its `extended_metadata.yaml`, its tests and ADR-004; and the
    `sci-rag` server starts with no check that the store holds its project, a read saying the project holds no
    passage.
  - Tests: `test_literature_graph.py` (3 new: a batch within one document, a shared document's reads free of the
    other project's words, another project's alias naming no edge; 3 changed), `test_literature_live.py` (6 new cases
    of one test: a limit of 0, -3 or a word refused on both commands; 2 changed), `test_literature_mcp.py` (2
    changed), `test_llm.py` (1 changed). Checks: the four with `test_literature_report.py`, `test_literature_kit.py`,
    `test_agent_interface.py`, `test_boundaries.py`, `test_check_tools.py`, `test_guidance.py`, `test_no_seed.py`,
    `test_key_override.py`, `test_api_intake.py` and `test_route_models.py`, with the database address empty, on
    Python 3.13 and on 3.12, 281 passed each way; the two new graph tests run on the landing's `graph.py` fail as the
    findings say; `gen:api`, `gen:tools` and `gen:components --check`, each file as the code writes it (the stats
    route's words and the sci-rag section moved); `check:tools`, `check:secrets`, `typecheck` and `pnpm build`;
    `pnpm test:lit` 10 passed; `pnpm prove --steps 3`, offline, 19 of 19 checks in 40 s with no model call; and
    `pnpm test:core` 3046 passed, 1 skipped, 175 deselected (5 min 4 s). `test:sim` is not owed: no worker, engine or
    flowsheet changed.
- F.5, its offline part (8 November): the project's retrieval lanes that ask no model, over the Ethanol project
  (ADR-002, Implementation F). On the landed tree (`311990d`): `pnpm build`; the service this session started
  restarted on 127.0.0.1:8800, `/api/health` answering and `pnpm ready` (no probe) ready. `pnpm lit:graph --project
  ethanol --dry-run`, which calls no model, measured the build the concept graph waits on: 814 passages in 92 batches,
  1,758,899 prompt characters (439,725 kit tokens), 0.2199 USD of input on `claude-haiku-5-5` and at most 2.3239 USD,
  each batch's whole answer counted (2.8 s). Then, with nothing else heavy running, `pnpm lit:report --project ethanol
  --by "Claude Code (build session)" --configs interactive,vector_only,keyword_only --render`: its ground truth built
  by code from the project's kept candidates, 130 questions from 457 of its 457 candidates in 130 groups by document,
  passage and field, over 20 of its 22 documents, none left out; each question asked in the three configurations
  inside the project's scope and scored under the kit's rule and the passage rule; 0 model calls and 0 USD in its
  tally, the graph and HyDE stages disabled for all 130 in each configuration; `interactive` 2.7 s, `vector_only`
  1.9 s, `keyword_only` 1.0 s, 8.5 s for the command whole. Under the kit's rule hit@10 is 0.54 for `interactive` and
  `vector_only` and 0.06 for `keyword_only`, under the passage rule 0.17, 0.17 and 0.01, each interval in the report.
  The run whole is kept outside git at
  `/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/f/data/literature/ethanol-20261108T081732Z.json`
  and audited as `literature_report` under the person `--by` names; `--render` set its public numbers as the
  project's part of `docs/reports/literature-retrieval.md` and `.json`, the demo's part standing as it was (its JSON
  payload equal, nested under `demo` in the report's two-part shape). The project's part gains two sections by hand
  after the rendered ones, what the run measured and what waits on the account with each command; the project's next
  `--render` writes its part whole again. Records: the Known debts row on the paid lanes (debt 7), Resume, ADR-002's
  Implementation F. No code moved, so no test file is owed. Checks: `pnpm test:lit` 10 passed (8 s); `pnpm test:core`
  3064 passed, 1 skipped, 175 deselected (5 min 10 s).

### Alpha 2.2 — Stage G — 2026-11-08

- The live host's runbook and scripts held to the tree, with no model call and nothing run on the Mini. A reader held
  `docs/runbooks/live-host-install.md` and `scripts/host/` (install, deploy, nightly, lib and launchd) to the code and
  wrote a patch; five verifiers held its 24 findings and the patch to Homebrew's source, python-dotenv 1.2.3 and
  stand-ins for brew and the PostgreSQL tools; every verdict is applied here, the refuted one dropped (`tailscale_cli`
  shows its error on the retry that matters). The groups:
  - PostgreSQL on the Mini: `ensure_database` puts the keg's tools first on the path whenever `brew --prefix
    --installed postgresql@17` answers (Homebrew keeps the formula keg-only), names `sudo brew services start
    --sudo-service-user=<you> postgresql@17` for a server from power-on and says so when a LaunchAgent starts it at
    login, refuses the example's developer database (`openferment_dev`, or the role `openferment`) in words, checks
    pgvector with `psql -X` before it makes the database, and writes the database line on a line of its own.
  - `core/.env`: step 1 makes it from the example without the database line and keeps one already there (an alpha 1.0
    Mini's, with its key); the key goes on the file's one `ANTHROPIC_API_KEY=` line, in `install.sh`'s, `pnpm
    ready`'s and Postdoc's words alike, with the restart; step 1 says how each model setting lays over `llm.ROUTES`'
    defaults and lists alpha 1.0's model lines to take out. `env_setting` reads a line in the forms of python-dotenv
    (`export`, blanks around `=`, quotes, a ` #` comment, a carriage return), leaves an environment value as it
    stands, and returns 0 when the name is absent, so a caller under `set -e` may assign it.
  - The alpha 1.0 Mini: the checkout at `~/openferment` throughout; step 0 stops alpha 1.0's jobs with its own
    `install.sh --uninstall`, copies `core/data` and pulls, with the recourse when the pull stops and a word against
    alpha 1.0's `--keep-decisions`; step 5's order runs: `install.sh` stops at its deploy step, then the copy, `pnpm
    db:migrate && pnpm db:import-alpha1`, the file put back and `install.sh` again, and `deploy.sh`'s stop says that
    order (and sends a machine whose `core/.env` names no database to `install.sh` first). `import_alpha1` refuses a
    database behind the newest schema in words naming `pnpm db:migrate`.
  - The deploy: `--verify` names the tests' server (the environment or `core/.env`, else the live database's server,
    else this Mac's PostgreSQL as you); the migration runs after the gate and the build, so a deploy that stops at
    either leaves the live database on the running service's schema; each deploy fetches a genome-scale model the
    shelf gained; the migration's failure names pgvector and a role or database the server lacks; the jobs' PATH holds
    Homebrew's bin, where Graphviz's `dot` lives.
  - The runbook's steps: Python 3.13 and `uv sync --frozen`, `pnpm geneos:fetch`, Tailscale's background service,
    Graphviz, Node as run, the Intel Mini's source builds; step 4 with every row `pnpm ready` prints, its marks, the
    lane, what a fresh Mini shows and what `pnpm db:up` means there; step 6 with `OPENFERMENT_PROJECT`, Studies as it
    stands and the catalogues screen; step 7 with the engines row, the proof, the restart, the environment made again,
    a backup step as a commit on `main` with the keg's `pg_dump`, and both tags. The flag `--sudo-service-user` was
    read in Homebrew's source; the runbook says to confirm it on the Mini with `brew services --help`.
  - Words: the scripts' headers (`install.sh`, `deploy.sh`, `nightly.sh`, `lib.sh`, `launchd.py`) say what each runs;
    `core/.env.example` gains `OPENFERMENT_PROJECT` and `OPENFERMENT_RAG_KEY` as commented lines with what each does,
    and the per-question cap sits in the spend block; `db/engine.py`'s, `ready.py`'s and `conform.py`'s words for a
    database that is absent or silent name the live host beside `pnpm db:up`; CLAUDE.md names `~/.cache/fastembed`
    and `uv sync --frozen`, README.md too; Resume, Current stage, Blockers (the live host's row in the runbook's order,
    the backup row) and Known debts.
  - Left for the owner: `has_key` reads an unquoted `ANTHROPIC_API_KEY=sk-ant-` line; python-dotenv reads a quoted or
    `export` line too, and widening `has_key` changes how the key line is read, a stop condition. This commit changed
    its placeholder pattern's `\s` to `[[:space:]]`, and the review put `\s` back (below). `OPENFERMENT_HOST` stays
    an install's explicit choice, default loopback.
  - Checks: `bash -n` on the four changed scripts; ShellCheck 0.11.0 (`-x -s bash`) on them, no finding; stand-in
    runs of `deploy.sh` in a scratch clone (both words of the decisions stop; `--verify`'s order: install, sync,
    model fetch, playwright, verify, then the migration, with the derived test server); the runbook's step 1 block on
    a fresh and a kept file (mode 600, no database line, the key line once). `core/tests/test_host.py` (17 new: eleven
    lines read as python-dotenv reads them, an environment value as it stands, the database made from the keg and
    named once on a line of its own, three developer addresses refused, a missing pgvector and a login-started
    server said) 49 passed on Python 3.13 and on 3.12; `test_import_alpha1.py` (1 new) with `test_host.py`,
    `test_ready.py`, `test_engines.py`, `test_db.py`, `test_mcp_service.py`, `test_guidance.py`,
    `test_boundaries.py` and `test_no_seed.py`, with the database address empty, 408 passed each way; `gen:api`,
    `gen:tools` and `gen:components --check`, each file as the code writes it; `check:secrets`; `typecheck`;
    `pnpm build`; `pnpm smoke` on a loopback port of its own, 20 of 20 screens with no key; and `pnpm test:core`
    3064 passed, 1 skipped, 175 deselected (5 min 25 s). `test:sim` and `test:lit` are not owed: no worker, flowsheet or literature code changed, and
    `engine/conform.py` gains words in one refusal.
- The review (8 November). An independent reviewer walked the runbook twice, as the owner of a fresh Apple Silicon
  Mini and on the alpha 1.0 Mini at `~/openferment`, and named 24 findings; each was held to the tree, and every one
  is applied here:
  - The merge: `main` holds alpha 2.1 (`112eb8b`) until alpha 2.2's pull request (stage H), and alpha 2.1's
    `ensure_database` looks for `pg_isready` on the PATH, where Homebrew's keg-only `postgresql@17` puts none. The
    runbook's head, Resume and the live Mini's row in Blockers say the install waits for that merge.
  - Step 0: no alpha 1.0 deploy before the block, said above it (the block's pull replaces alpha 1.0's `deploy.sh`);
    the copy made once (`[ -e ~/openferment-alpha-1.0-data ] ||`, since a second `cp -Rp` copies into the first);
    git's three stops quoted as git 2.43 prints them in scratch, each met by `git reset --hard origin/main`.
  - The lock: `pnpm ready`, `geneos:fetch`, `prove`, `db:migrate` and `db:import-alpha1` run `uv run --frozen`, and
    `deploy.sh --verify` runs the gate with `UV_FROZEN=1`, so a newer uv on the Mini (Homebrew serves 0.13.7; this
    lock was written by 0.11.32) leaves `core/uv.lock` as committed for the next deploy's check of uncommitted changes.
  - `has_key` stands byte for byte as it stood before stage G, `\s` back in its placeholder pattern; the portable
    class and a wider key line are owner question 13.
  - Words held to the tree: `env_setting`'s comment names the three forms it reads as the line stands (`${VAR}`, a
    `\"` inside quotes, a value running onto a second line), each run beside python-dotenv in scratch;
    `install.sh`'s key words add the line when `core/.env` has none, and `pnpm ready`'s and Postdoc's leave the
    example's database line out on the live host; step 5's stop reads as `deploy.sh` does, while the file differs
    from its committed version; step 1's grep finds an `export` or spaced model line; the Node row names Node 26 as
    unrun and `pnpm --version` printing `10.33.0` in the checkout; `core/.venv` made again runs
    `scripts/engines-local.sh`; the tags go up by refspec from any clone (here and in Blockers); the catalogues
    screen's address is `#/p/<its id>/catalogues`; and the Log's stage G entry names `engine/conform.py`'s refusal.
  - The writing preference: two passages of the runbook's step 0, two of step 4's, two of `core/.env.example`
    (the spend cap and `/rag`), one Known debt and two lines of the Log above.
  - Checks: `bash -n` and ShellCheck 0.11.0 (`-x -s bash`, from `scripts/host/`) on `deploy.sh`, `lib.sh` and
    `install.sh`, no finding; `deploy.sh --verify --no-pull --no-restart` in a scratch clone against stand-ins,
    `UV_FROZEN=1` on the `pnpm verify` line, with the derived test server; step 0's copy run twice and step 1's
    grep on a stand-in file; the refspec push twice to a scratch remote; `pnpm db:import-alpha1 --help` and `pnpm
    ready --offline` through `uv run --frozen`, `core/uv.lock` unchanged; `test_host.py` with `test_ready.py`, 114
    passed on Python 3.13 and on 3.12; `typecheck`; `check:secrets`; `pnpm build`; and `pnpm test:core` 3064
    passed, 1 skipped, 175 deselected (5 min 20 s). `test:sim` and `test:lit` are not owed: no worker, engine,
    flowsheet or literature code changed.

### Alpha 2.2 — Stage H.0 — 2026-11-08

- The sweep's findings on the final tree, each confirmed against the code first, fixed where they held:
  - Links: `LinkButton`, the rail, Settings' sections and the remaining plain-hash links go through `router.href`, so a
    click inside `/p/<project>/` stays in the address; the sr-only span of `ComponentTag` sits in a positioned parent
    and `<main>` is positioned, so the window has one scroll.
  - The cost card: its last row is the price the lines sum to, and a library run whose TEA solved another price says
    so beside the figure (`check:figures` holds both); the breakdown at the solved price waits on a version (Debts).
  - pureOS reads a library run as a train, keyed by the study scenario its runs row names, else by its own id
    (`pureos.library_scenarios`; `test_pureos.py`); the train page links a study scenario to Studies.
  - Words: the usage-limit refusal names the date alone and logs the API's message (`llm.regains`;
    `test_llm.py`); Postdoc's trace names a document by its title, a scenario by its title and a catalogue read in
    words; validate's two refusals, the inlet gloss, the shortcut column's line, three kinetics notes and fifteen
    field definitions (`schema/fields.yaml` with `src/data/ontology.ts`) are stated positively; screens across
    geneOS, pureOS, fermOS, Catalogues, Runbooks, Depositions, Witness, Settings, Provenance and Postdoc likewise.
  - Ids and stamps: a document is named by its short cite or title where an id stood (`src/lib/cite.ts`: chips,
    Intake's columns and facets, the reader's rail, crumb and marks, Guild's card, fermOS's titre select, BioRepo's
    Papers); ISO times read as `stamp` writes them (`stampsIn`); exponents are superscripts.
  - Screens that missed rows the service holds: Home's Proforma tile counts the studies, Proforma's empty state names
    the study scenarios, BioRepo's Compare lists the kept comparisons, the run's header names its study scenario,
    the artifact pages name runs and comparisons and link their pages, the flowsheet page lists the toolkit's
    findings, the ceiling figure says the sugars its records name.
  - Remnants: `--save-fixture` is gone from extraction and `core/tests/fixtures/extract/` is ignored; OF-BLD tags
    leave the strings people read and the service's docstrings (generated docs regenerated), the hashed basis notes
    kept (Debts); `damaged on disk` reads `damaged in its row`; `prototype:up` is recorded in ADR-000's implementation
    note; the sim fixture names its maker; PHB-era words in tests and comments give way to placeholders; the three
    subsystems Intake and BioRepo built leave the unbuilt shelf; `SET_KINDS`, `PRESETS`, toy's `OUTPUTS` and the
    spend-lock test go; 143 names used in their own file alone lose `export`.
- Kept as found, with the reason: the 'assumption' rule entry answers for an estimate (its words name a person's
  assumption, a model's estimate and a reading); the Model tab's keeping is deliberate (`lib/geneos.ts`) and now said
  on the tab; the overlay's size at this scale; `curated` in `PROVENANCE_ORDER` (check:plan); the paper reader's
  repeated INTRODUCTION heading, unchecked against the kit's sectioning.
- Checks: `pnpm test:core` 3066 passed, 1 skipped, 175 deselected (5 min 23 s); `pnpm test:sim` 142 passed (4 min
  47 s); the touched test files on Python 3.12, 205 passed after the last edit (836 on the first pass); `gen:api`,
  `gen:tools` and `gen:components` with `--check`, `check:licences` (THIRD_PARTY.md rewritten), `check:secrets`,
  `check:plan`, `check:figures`, `check:guild`, `check:state` (four new checks: links keep the project, stamps,
  short cites, superscripts), `check:tools`, `typecheck`, `pnpm build` and `pnpm smoke` on a port of its own (20 of 20
  screens). `test:lit` is not owed: the literature layer did not move. No model was called and nothing was spent.
- The sweep's second list (32 findings), each confirmed against the tree first:
  - Screens: Home's runbooks band is named Runbooks (`home-runbooks`); Settings names the release once
    (`RELEASE`, alpha 2.2), its Appearance blurb names the three settings the page holds, and the Export page's
    disabled API-key card is gone (the fidelity row says accounts and tokens wait); the Architecture map names
    Catalogues at `/catalogues`, and the palette's entry reads "the named components"; the paper reader's crumb says
    BioRepo (its id had given way to the short cite at H.0's first list); Ingest's header holds its title and blurb,
    the Extract tab beside it; pureOS's unit
    operations are glossed by what each does (`schema/vocabulary.yaml` with its mirror `src/data/vocabulary.ts`).
  - Notes a basis hashes: the parameter panel, fermOS's fit, simulation and vessel notes and a figure's basis show a
    note through `plainNote` (moved to `src/lib/proforma.ts` from the run page), which drops a decision tag, a build
    document or a rule's constant anywhere in it; the kinetics notes no basis hashes say their words alone. A changed
    `ZERO_SAID` moved `fermos.simulation batch_v1`'s pinned id, so the hashed ones stay whole (Debts).
  - Remnants: the module projection holds geneOS's hosts and Primer's lessons alone, the tests hand runbooks,
    protocols and scenarios through their own doors, and the `pathway` row kind is gone (docs/TOOLS.md
    regenerated); `validate_claims` is deleted and the rules its tests held run on `validate_plan`; `atomic.held`,
    `sff.library_flowsheets`, `library_plants.package_test_name`, `is_share` and `SHARE_NAMES`,
    `proposals.as_rows`, `spend.would_pass` and `witness.new_candidates` are deleted, the cap's tests held through
    `spend.reserve`; in the client `basisInput`, `checksView`, three `*Refused` aliases and fifteen figure-barrel
    aliases. ADR-000, ADR-001 and ADR-003 name what stands; ADR-008 records the one-call path's going
    (Implementation 19).
  - Records: the §5.2 departure row names the fixtures that stand; collectors.py names `pnpm intake:extract`;
    `docs/reports/live-questions-2026-11.md` names PMC3639890 and osti:1013269 by identifier and leaves out the
    values quoted from papers and the scenario's and the comparison's numbers; `model-routing-2026-11.md` puts
    haiku's Q3 note in words; `literature-retrieval.md`'s hand section counts the documents with candidates and
    `keyword_only`'s short lists.
- Kept, with the reason: pureOS's `program` key and the words hashed with it (`TrainSpec.program`, the shelf's
  description and price basis of `custom_train_v1`): renaming shifts the id of every new train run and composite run,
  so it waits on the stage its debt row names (Debts); the shelf's comment says chemical set. The dry
  run's 2.8 s stands: a re-run gave real 0m2.872s, and the next measured run sends its `time` to its .err file.
- Checks of the second list: `pnpm test:core` 3057 passed, 1 skipped, 175 deselected (5 min 34 s; `validate_claims`'
  20 tests gave way to eleven on `validate_plan`); `pnpm test:sim` 142 passed (5 min 6 s); `pnpm test:lit` 10 passed
  (10 s); the touched test files and their neighbours on Python 3.12, 484 passed; `gen:api`, `gen:tools` and
  `gen:components` with `--check`; `typecheck`, `check:state` (five new checks: a kept note's tags dropped on a screen,
  every rail destination a named component at its address, a link back named as the rail names it, a tab's header
  with no link back, no unbuilt subsystem with a route), `check:figures`, `check:guild`, `check:plan`, `check:tools`,
  `check:secrets`; `pnpm build` and `pnpm smoke` on a port and a database of its own, 20 of 20 screens; the pins of
  `test_engine_pins.py` held. Read-only SELECTs on `openferment_dev_alpha21` named the reports' documents. No model was called and nothing was spent.

### Alpha 2.2 — Stage H — 2026-11-08

- H.1, the runs on the branch as it stood (`9b6e5c7`, H.0's last commit), with no model call: `pnpm verify` green
  on all sixteen stages in 12 min 11 s (`test:core` 3057 passed, 1 skipped, 175 deselected; `test:sim` 142 passed;
  `test:lit` 10 passed; `smoke` 20 of 20 screens with no model key); then `pnpm build && pnpm prove`, offline, 99 of
  99 checks in 203 s, `conform` 8 of 8 on each of the four engines the service lists (`biosteam`, `kinetics`,
  `mirror`, `train`), the proof's spend table 0 calls (Last green runs). `pnpm prove --live` waits on the account
  (Blockers): `pnpm build && pnpm prove --live`, F.4 in Resume item 5's order.
- H.2, this file to the branch's end: the Resume rewritten to the close (where alpha 2.2 stands, what waits on the
  account with its commands in order, what waits on the owner); Known debts in three groups, 33 paid each with its
  commit, 11 open each with what pays it, 18 left by decision each with the line that records the decision and its
  decision record. pureOS → Train reading a library run moves to paid at H.0 (`744e32e`), and the retrieval report's
  row parts into its paid offline lanes (`adb9c8d`, `0dd8415`) and its open model lanes. Blockers current, owner
  questions 11 to 13 among them; Spend (alpha 2.2) read over every database on this server with SELECT alone,
  stage F settled at 14.439322 USD on 5 November and 25.284480 on 8 November, stages G and H at 0, alpha 2.2 at
  39.723806 USD over 349 calls; Current stage opens with stage H.
- H.3, `CLAUDE.md`'s alpha 2.2 lines held to the tree, 148 lines, each labelled: the catalogues screen at
  `/catalogues` (R, the alpha 2.2 prompt §1 item 4 and §6.5); the routing defaults per family and a plan turn's room
  by its route's effort (C, ADR-008 Implementations 16 and 17), its revisit line naming the second judge and the
  larger room; the `convention` origin beside `measurement` (ADR-006); `pnpm ready`'s workers and engine rows;
  `pnpm eval`'s `--only`; verify's measured time. The registry and `conform`, the probe's account-limit row, the
  `sci-rag` server's graph tools, `pnpm lit:graph` and `pnpm lit:report --project` held the tree as written.
- H.4, `README.md`'s first section says what alpha 2.2 is in five lines and points at `docs/BASE.md`, which "Read
  further" lists first; `docs/BASE.md` held to the tree: a run's `measurement` origin, the catalogues screen, the
  `sci-rag` server's graph tools and `uv sync --frozen`, its pinned versions read again from `core/uv.lock` as
  written.
- H.5, the checks on the final tree: `pnpm test:core` 3057 passed, 1 skipped, 175 deselected (5 min 59 s);
  `test_guidance.py` 6 passed on Python 3.12 and on 3.13, `CLAUDE.md` at 148 lines. No model was called and nothing
  was spent.
- H.6, the close review: an independent reader of `ae6f74c` gave 26 findings (5 errors of fact, 9 smaller gaps, 2
  remnants, 10 places in the words); each was confirmed against the tree, the prompt, the logs or a SELECT before it
  was fixed, and every one held.
  - The backup in the nightly, in the place the prompt's §3 names: `scripts/host/nightly.sh` runs `backup_database`
    (`scripts/host/lib.sh`) first each night, the keg's `pg_dump -h 127.0.0.1 --format=custom openferment` into
    `~/openferment-backups/openferment-<date>.dump`, written beside its name and moved into place once whole, the folder
    700 and its files 600, the newest seven kept, in words macOS's bash 3.2 reads. Three tests in
    `core/tests/test_host.py` on stand-ins: the keg's tool called once, seven kept and a file of another name left as
    it was; a failed dump keeping the kept files; the dump ahead of the night's work. ShellCheck 0.11.0 is clean over
    the four host scripts. The runbook's steps 3, 6 and 7 and `launchd.py`'s docstring name it, step 7 with how to
    read a dump back; Blockers row 3, Resume item 6 and the macOS debt row say the place is §3's and the owner's first
    install runs it.
  - Stage H: steps 1 and 2 done and step 3 next, the pull request with §9's report and the tag `alpha-2.2` attempted
    once (Resume items 4, 6 and 7; Current stage).
  - Facts: Resume item 5 for the live steps' order (stage F; Blockers row 1); the final Last-green row at 11:21, the
    time its run ended; 39 test files import `standins.py`; Resume item 2 names the three model settings at Haiku and
    the effort at medium; Resume item 5 names this session's copy of the fetched caches and what a fresh container
    runs to fill `core/data/`, and the routing report's alpha 2.2 "To finish it"; H.0's two rows join Last green
    runs; `CLAUDE.md` gives verify's measured range (nine to eighteen minutes) and CI's Python (the runner's, CPython
    3.12.3 on the close's run), parts the catalogues line into the R line §1 item 4 and §6.5 name and a C line for
    E.8 and E.9, and adds alpha 2.2's three engines to the scope line; `docs/BASE.md`'s Postdoc entry says what holds:
    its doors, the base running with no key, and the two pieces of the `postdoc` package the base reads.
  - The test database `check_tools_26521_a78452`, left by a `check:tools` run at 04:51: a SELECT read its one project
    (`check-tools`, made by `check:tools`) and its empty spend table, and `python -m openferment_core.migrations drop`
    dropped it; the Spend paragraph names it and `sci_rag_test`, the kit's.
  - Words: Blockers rows 1 to 3, two debt rows, `CLAUDE.md`'s SFF, provenance, tool-result and estimate lines, and
    `docs/BASE.md`'s opening, records row, software line and module line, each said positively.
  - Kept as found: the A4 departure row's "27 test files use it", the record of stage 8's day.
- Checks of the close review: `test_host.py` 52 passed (49 before) and `test_guidance.py` 6 passed, with the
  database address empty, on Python 3.12 and on 3.13, `CLAUDE.md` at 149 lines; ShellCheck 0.11.0 and `bash -n` on
  the host scripts; `pnpm test:core` 3060 passed, 1 skipped, 175 deselected (5 min 12 s). `test:sim` and `test:lit`
  are not owed: neither the engines nor the literature layer moved. No model was called and nothing was spent.

### Fixes after the bug hunt — 2026-11-11

On `claude/alpha-2-2-fixes`, cut from `claude/alpha-2-2-bughunt` at `fa8db4a`, in the fix order of
`docs/reports/bug-hunt-2026-11.md`.

- Group 1, H5-01 (S1): a literature search in one project returned another project's private passage
  when the other project committed it, under a source the two share, while the search ran. `_narrowed`
  read the scope (`visible`) before the kit's retrieval statements ran, so the new document passed the
  `sources` allowlist and an `exclude_document_ids` list read before it existed.
  - The fix: `kit.ProjectRetriever`, the retriever `kit.service()` builds, reads the documents a
    retrieval's items name against the project's holdings once the retrieval is done (`kit.holding`).
    An item naming a document the project does not hold sends the retrieval again, up to
    `ProjectRetriever.RERUNS` (2) times, each time excluding the strays seen so far and every other
    document of the project's sources as `visible` reads them then, so the scope still precedes the
    ranking and a second document committed in the same window goes out with the first. Any such item
    the last run returns is dropped. The search, the answer engine and the retrieval report reach the one retriever, and a
    retrieval with no project named is refused in words (422, `project_required`). The kit's
    `RetrievalScope` carries no document allowlist, so the check stands on openFerment's side; the fix
    order's own example, a condition inside the retrieval statement, waits on a document allowlist in
    the kit's scope.
  - Tests: four in `core/tests/test_literature_kit.py`. Two replay the race every time: the scope
    read before the other project's commit, then the search and an answer in the project. A check in
    the first shows the kit alone ranks the other project's note first under that scope. The third
    stands in for the kit's retrieval with runs that each return a new stray, and holds the
    exclusions each rerun carries and the drop after the last. The fourth asks the retriever with no
    project named, the kit's retrieval set to fail if it is reached. Each fails on `fa8db4a`'s
    `kit.py` and passes on the fix; the file's 24 tests pass.
  - The reproduction: `bash bughunt/repro/H5-01/run.sh`, twice, reads `RESULT: NO-DEFECT` in
    `after-fix-run1.log` and `after-fix-run2.log`: A pasted all 60 notes while B searched 115 and 104
    times, and 0 of A's notes reached B's hits (the hunt's runs read DEFECT after 18 and 17 searches).
  - Records: `kit.py`'s docstring and ADR-002's line on the project as the scope name the check.
  - Review: three readers (every read path, the retriever's own correctness, regressions and cost),
    each claim then checked against the code. Confirmed and fixed: the first commit's one rerun
    excluded only the strays that ranked (now the bounded rerun above), no test reached the drop after
    the rerun, and the no-project test could not show the refusal comes before any read. Checked and
    set aside: the reruns replace the first run's traces (the hits B gets come from the last run, and
    a trace naming the rerun would tell B of another project's work), a deep-profile rerun asks the
    graph and HyDE layers' model again (a rerun happens only in a race), and the LLM reranker reads a
    racing passage before the check (its text reaches no reply to B). Every read path was found
    covered: the search, the answer engine, `/rag`, both MCP servers, the document, citation, graph
    and stats reads, and the retrieval report.
  - Found by the review, apart from H5-01: two concept-graph builds at once can lose one project's
    document from an entity's `document_ids` and keep the description its passage produced (an Open
    debt, below).
  - Checks: `pnpm test:core` 3064 passed, 1 skipped, 175 deselected (5 min 31 s); `pnpm test:lit` 10 passed.
    No model was called and nothing was spent.
- The concept-graph build race group 1's review found (not a hunt finding): two builds at once could
  lose one project's document from an entity's `document_ids`. The kit's batch step
  (`sci_rag/graph/extractor.py`, `_extract_batch`) asks the model, then in one transaction reads the
  entities the batch names, merges their chunk and document lists in Python and writes them back,
  with no lock and under READ COMMITTED. A batch that read an entity before another build's commit
  wrote its stale lists over that commit, and the entity kept the description the lost document's
  passage produced. `graph.entities` shows a description only while every document naming the
  entity is the project's, so the other project then read it.
  - The fix: `graph.build` hands the kit's batch step a session factory on the kit's engine
    (`_writer`) whose every transaction first takes one PostgreSQL advisory lock
    (`pg_advisory_xact_lock(GRAPH_LOCK)`, an `after_begin` hook on `_GraphWrite`) and holds it to
    the commit. The batches of every build then write one after another, each reading what the last
    committed. The model call comes before the batch's transaction, so it stays outside the lock.
    `graph.build` is the one writer of the concept graph (`pnpm lit:graph` calls it).
  - Tests: `test_two_builds_at_once_keep_every_document_an_entity_is_named_in` in
    `core/tests/test_literature_graph.py` makes the two builds overlap every time: this project's
    batch reads the entity, then waits inside its transaction (1.5 s at most) for the other
    project's build to commit. Without the lock the other build commits in that wait and its
    document is lost from the entity; with the lock it waits, and the entity names all three
    documents, its description withheld from this project. `test_the_kits_batch_step_is_the_one_this_build_calls`
    now holds that the factory the build hands the kit is on the kit's engine and takes the lock.
    The two literature test files' 46 tests pass; `pnpm test:core` 3065 passed, 1 skipped, 175
    deselected (5 min 56 s); `pnpm test:lit` 10 passed. No model was called.
  - Records: `graph.py`'s docstring (the build), ADR-002's Implementation F and the Paid row.
- Group 2, H7-01 (S1): two tabs on one project during an outage each saved their own queue whole under
  the browser's one Durable key (`durable.ts`'s `KEY`), so the tab that saved last set the queue for the
  whole browser, and a reading queued at the bench in the other tab was erased and never sent.
  - The fix: a save merges (`durable.ts`, `mergeSnapshot`, `hold`, `emptyHeld`). Each tab keeps the owed
    writes it has held, by what names each (an outbox entry by project, kind, row and time; a review
    decision by record and time; Guild's owed ids; a withdrawal by entry and time). A save keeps what
    the tab owes now and, from the stored snapshot, every owed write the tab has never held; of two
    writes of one row the later stands, and the outbox runs oldest first. A write the tab held and no
    longer holds was answered or replaced, so it leaves. The stored outbox and Guild's owed writes a
    page loads count as held at once (the page takes them as its own); a loaded review decision counts
    once a snapshot the page saves carries it, so a decision for a record the page has not loaded stays
    in the store. The read and the write run in one IndexedDB transaction.
  - Checks: ten in `scripts/check-state.ts` (the browser's one snapshot, two tabs): two tabs saving in
    turn keep both depositions, oldest first, and the page that opens next sends both to a stand-in
    service; an answered write leaves while the other tab's stays; the later of two writes of one row
    stands; review decisions and Guild's owed writes alike. `pnpm check:state` passes.
  - The reproduction: `bash bughunt/repro/H7-01/run.sh`, twice in Chromium over the built app, reads
    `RESULT: NO-DEFECT` (`after-fix-run1.log`, `after-fix-run2.log`): the queue held A's and B's
    depositions through B's save and both tabs closing, and once the service answered it held A's with
    5.5 USD/kg and B's with 6.6 USD/kg.
  - Records: `durable.ts`'s section on the one snapshot, ADR-014's implementation note.
  - Checks: `pnpm typecheck`, `check:state` (the ten above among its checks), `check:plan`, `check:figures`,
    `check:guild`, `test:reconcile`, `gen:components --check`, `pnpm build` and `pnpm smoke` (20 screens) pass;
    `pnpm test:core` 3065 passed, 1 skipped, 175 deselected (6 min 11 s). No model was called.
- The review of the graph lock (70abace): two readers, the lock's correctness and its regressions,
  each claim checked against the code. Held: `after_begin` runs `pg_advisory_xact_lock` as the
  statement that opens each batch's transaction, on the connection every later statement of the
  batch uses; each retry and half of a batch opens a session of its own and takes the lock again; no
  model call or sleep falls inside it; no other writer of the graph runs in openFerment's paths; the
  key meets no other advisory lock of the database (`db.lock`'s keys are hashed), and the one lock
  taken before any row lock leaves no deadlock. Confirmed and fixed: the test's fixed 1.5 s wait could
  let a regression that loses the lock itself pass on a slow machine; it now waits until the other
  build has committed or is seen waiting on `GRAPH_LOCK` in `pg_locks`, 30 s at most, and it fails
  every time with the lock's `after_begin` hook removed. Confirmed and recorded: the records said a
  shared passage is read once, and two builds at once can each pay for it (`graph.py`'s docstring,
  ADR-002's Implementation F and `docs/api/intake.md` now say so, and the Open table holds the spend).
  `pnpm test:core` 3065 passed, 1 skipped, 175 deselected (6 min); `pnpm test:lit` 10 passed.
- The review of the H7-01 fix (165f90e): three readers (loss and resurrection, the store and the browser, the checks
  and records), each claim checked against the code; 21 claims, 11 confirmed.
  - Fixed in the merge: two writes of one row from tabs that never saw each other's both stay, oldest first, for
    the service to rule on in order (the first commit kept the later alone, so the earlier tab's reading was erased
    with no word); a stored value the read cannot read back is written over by the tab's snapshot, so it blocks no
    save; a review decision the service holds, or a later one, leaves the snapshot (`holdDecision`, called by
    `syncDecisions`); a decision from before decisions carried their own time keeps its snapshot's time when carried;
    a person's owed write is named by its id and the time of the change, and a withdrawal by every field.
  - Fixed beside it, both older than the fix: Guild's owed writes carried no project, so a page open on another
    project took them as its own and posted them there; they are kept by project now (`guildOwed`, `owedGuild`), a
    legacy block read once as the open project's. `syncGuild` dropped an owed change to a person the service already
    held without posting it; it posts the change unless the service's copy carries it (`write_person` takes a person
    it holds as a change).
  - Records and checks: ADR-014's note said a write another tab queued is sent once that tab has closed; a page that
    loads takes it at once, beside the queuing tab, and the note says so, the stale copy that can follow in the Open
    table. Check 4's words named a case its input cannot reach and now name the one it tests. `check:state` holds
    nine more: a stored write later than the tab's own, a write taken at load and written again, a loaded decision
    on a record not loaded, a decision with no time of its own, a later change of a person, two withdrawals of one
    entry, another project's Guild block, and the legacy block taken and left.
  - Set aside, with its reason: the reproduction's verdict wording (it reads DEFECT on the loss it was built for).
    The put waiting on the read's success event on a closing tab was set aside here, and the second review showed
    it holds (the entry below).
  - Checks: `pnpm typecheck`, `pnpm build`, the reproduction twice (`RESULT: NO-DEFECT`), `check:state`,
    `check:plan`, `check:figures`, `check:guild`, `test:reconcile`, `gen:components --check` and `pnpm smoke` (20
    screens) pass; `pnpm test:core` 3065 passed, 1 skipped, 175 deselected (6 min 4 s).
- The second review of the H7-01 fix (fffa62d): two readers (correctness, regressions and records), each claim
  checked against the code; 16 claims, 16 confirmed.
  - New with fffa62d, and fixed: `syncGuild` posted an older owed change of a person over a later one the service held
    (it now sends a change only when the service's copy differs and was written before it, and an add the service
    holds is the service's); the page read the snapshot before its project settled, and a page kept running after
    `openProject` set the new project (the snapshot is read once the project list settles, `openProject` reloads with
    the page's project unchanged, and a page whose project went away reloads); a Guild write with no project open was
    kept nowhere (it is refused in words); `holdDecision` could let go of another project's decision on a record of
    the same id (a decision carries its project, and a page re-applies, sends and lets go of its own project's
    alone); the pagehide save waited on the read's success event, which a closing page may never run (it is placed
    at once, merged over the snapshot the tab last read or wrote); and the records claimed a write sent twice is kept
    as the first (a second lock, withdrawal or Guild entry is refused; a withdrawal the service shows is no longer
    sent again).
  - Older than the fix, and fixed: of two tabs' owed changes of one person the saving tab's own stood (the later
    stands now); a page that took two tabs' writes of one row and wrote it again replaced both (`enqueue` replaces the
    row's last queued write alone).
  - Records: ADR-014's note is rewritten to the code, the acting person kept per project among it; the Open row
    names both remaining gaps. `check:state` holds three more (the open project's Guild block read, the later of two
    tabs' changes of one person, a write replacing the row's last queued write) and `check:guild` four (a person the
    service carries, an older copy on the service, a later change on the service, an add the service holds).
  - Checks: `pnpm typecheck`, `pnpm build`, the reproduction twice (`RESULT: NO-DEFECT`), `check:state`, `check:guild`,
    `check:plan`, `check:figures`, `test:reconcile`, `gen:components --check` and `pnpm smoke` (20 screens) pass;
    `pnpm test:core` 3065 passed, 1 skipped, 175 deselected (5 min 36 s).
- The third review of the H7-01 fix (d5bb479): three readers (Guild, the open project, the queue), a verifier per
  claim; 12 claims, 12 confirmed.
  - New with d5bb479, and fixed: `syncGuild` read the service's copy of a person by when the service wrote it, cut to
    the second, against when the page made its own change, so the first of two pages to sync stood whichever change
    was later (the service keeps a change's own time, `guild.py` `_change_time`, when it runs no more than five
    minutes ahead of the service's clock, and the page compares change against change); the review screen showed
    another project's offline decision on a record of the same id (`durableReview` holds this project's alone); a
    reload the person cancelled after `openProject` left the store on one project and its requests naming another
    (`openProject` remembers the choice and the page keeps its project until it reloads); `loadProjects` reloaded a
    page whose project went away and went on to read in it (its reload is gone: the list settles before the snapshot
    is read, so the page holds no other project's writes then); the pagehide save wrote over a remembered copy of the
    snapshot, so it could erase another tab's writes stored since, put back a write another tab had sent, and write
    whole over a snapshot it never read (every save reads and then writes in one transaction, a pagehide save
    starting it in the same task on the open database); and a change made while an unanswered flush ran left two
    writes of its row (`enqueue` replaces the row's left-over write).
  - Older than the fix, and fixed: an address naming a project the service does not hold, deleted or mistyped,
    reloaded the page without end (it opens nothing, and the page says the service holds no such project, with a
    link to the projects it holds); checked in Chromium over the built app: two loads and the words, and none from a
    page already open.
  - Records: ADR-014's note says the service keeps a change's own time, the page keeps its project until it reloads,
    the review screen holds this project's decisions, and a closing page may leave its last 400 ms of changes
    unstored. `test_guild.py` holds a change's own time and the service's time for one ahead of its clock or
    unreadable, `check:guild` an owed change made after the one the service holds, and `check:state` one write of
    a row after an unanswered flush.
  - Checks: `pnpm typecheck`, `pnpm build`, the reproduction twice (`RESULT: NO-DEFECT`), `check:state`, `check:guild`,
    `check:plan`, `check:figures`, `test:reconcile`, `gen:components --check` and `pnpm smoke` (20 screens) pass;
    `pnpm test:core` 3070 passed, 1 skipped, 175 deselected (5 min 27 s).
- The fourth review of the H7-01 fix (c12687b): three readers (Guild's times, the open project, the queue), a
  verifier per claim; 12 claims, 12 confirmed, five new with c12687b and seven older.
  - New with c12687b, and fixed: the pagehide save placed its read in the closing task and its write in the read's
    success event, which a closing page never runs, so a page closed or reloaded stored nothing of its last 400 ms
    (a closing tab now writes its last snapshot and what it held under its own key, committed at once, and the next
    page to load folds it in, `foldParting`; a write left to commit on its own did not land in Chromium either); the
    comments said the write started in that task; a project made in another tab after the page loaded was called
    one the service did not hold, and left unopenable (the list is read again, once, before the page says so); a
    fresh load of a dead project's address opened it for a whole load and forgot the project the browser had (the
    page waits for the list, and keeps the project it remembers); and check-guild's comment still spoke of the
    service's write time.
  - Older than c12687b, and fixed: a person the service held as an add alone counted as carrying a later owed change,
    by the add's arrival time (such a change is sent); two pages syncing at once could write the earlier of two
    changes over the later (the service keeps the later, whichever arrives last); the snapshot kept one decision a
    record id, so of two projects' offline decisions on one record the earlier was never sent (keyed by project and
    record, `decisionKey`; the Paid table); with site data blocked every `/p/` address reloaded without end, and the
    switch at a `/p/` address was undone by the next load, `Make it and open it` too (the address names the project a
    page opens, and choosing one writes it); a flush whose every write was refused left a change made while it ran
    unsent (it goes round again); and a flush out when this browser's data was cleared put back what it took (it
    puts back nothing).
  - Checked in Chromium over the built app: a dead address opens nothing after one load and keeps the remembered
    project; a project made later opens; the switch at a `/p/` address lands; with `localStorage` throwing, an
    address opens in one load and the switch lands; a name typed just before a reload is there after it; a project
    chosen during a run, the person staying at the prompt, leaves the page in its project and its address, and going
    ahead lands in the new one.
  - Records: ADR-014's note is rewritten to the code (Guild's later change, decisions by project, the address, the
    parting record, the flush); the Open row names what a closing tab left among the late copies; `project.ts`'s
    header names the address. `test_guild.py` holds the later change kept; `check:guild` an owed change over an add
    alone; `check:state` two projects' decisions on one record, a decision rekeyed, the fold of a parting tab's last
    save, and the store's flush over a refused round and over a clear (each of the last two fails on c12687b's lines).
  - Checks: `pnpm typecheck`, `pnpm build`, the reproduction twice (`RESULT: NO-DEFECT`), `check:state`, `check:guild`,
    `check:plan`, `check:figures`, `test:reconcile`, `gen:components --check`, `pnpm smoke` (20 screens) and
    `pnpm prove --steps 9` (55 checks) pass; `pnpm test:core` 3071 passed, 1 skipped, 175 deselected (5 min 38 s).
- The fifth review of the H7-01 fix (826926c): four readers (the parting record, the open project, decisions,
  Guild), a verifier per claim; 11 claims, 11 confirmed, seven new with 826926c and four older.
  - New with 826926c, and fixed: the fold laid a closed tab's reviewer and acting person over a later save (what a
    save takes whole now comes from whichever was saved later, and a tab whose last save landed leaves nothing); the
    load took the fold before its transaction committed, so a failed write-back left records to be laid in twice (it
    takes the fold once committed, else the snapshot as stored); after a failed first project list, an address to
    another project showed `Opening project…` for good (the list is read again, and a list still unanswered leaves
    the page to open the address); a project made during a run, the person staying at the prompt, left links naming
    it (it joins the list once the address is the page's again); under the development build's double start the
    second list read could let the snapshot be read before the project settled (a call waits for the first read); a
    person added and changed offline reached the service as an add with its change time dropped, so an earlier
    change from another page was written over it (the add keeps the change's maker and time); and two records
    overstated (`mergeSnapshot`'s docblock, ADR-014's sentence on decisions kept by record alone).
  - Older than 826926c, and fixed: clearing this browser's data left a flush, a Guild sync and a decision sync
    sending what they had not sent yet (each stops); an undo back to undecided, made with the service away after a
    decision it held, was kept nowhere though the page said it waited (it is kept and sent like any decision); and a
    Guild sync whose read again failed showed the ledger as it was before its posts (it shows each post's answer).
  - Records: ADR-014's note is rewritten to the code; `durable.ts`'s comments follow. `test_guild.py` holds an add
    that carries a change; `check:guild` a failed read again; `check:state` the fold by time, a write unsent at a
    clear, and an undo kept (each of these three fails on 826926c's lines).
  - Checked in Chromium over the built app: the walk of the fourth review's six cases holds again, and a page whose
    first project list failed opens another project's address, reading the list again when it answers and opening
    the address when it does not.
  - Checks: `pnpm typecheck`, `pnpm build`, the reproduction twice (`RESULT: NO-DEFECT`), `check:state`, `check:guild`,
    `check:plan`, `check:figures`, `test:reconcile`, `gen:components --check`, `pnpm smoke` (20 screens) and
    `pnpm prove --steps 9` (55 checks) pass; `pnpm test:core` 3072 passed, 1 skipped, 175 deselected (6 min 5 s).
- The sixth review of the H7-01 fix (e313119): three readers (Durable, the open project, Guild and decisions), a
  verifier per claim; 7 claims, 7 confirmed, four new with e313119 and three older.
  - New with e313119, and fixed: the fold took a later save's acting person for every project, so a closed tab's
    newer choice in its own project gave way to an older block another project's tab only carried (each project's
    block carries its own time, and the later block's person stands); a page whose list went unanswered remembered
    the address's project although no list confirmed it (it opens the address and remembers nothing); a clear while
    a Guild sync's posts were out left the never-sent rows shown, open to being sent by a later edit (they leave the
    page's ledger, and the stopped sync reads the ledger again); and ADR-014 said a page holding a list opens an
    address whose second read goes unanswered (it says so and stays, as the note now reads).
  - Older than e313119, and fixed: a first lead who left themself inactive offline left a ledger no one could add to
    (the first person stays active); a deviation the service went away before taking was lost with the refused run
    (it is owed in the run's place); and an add whose change was made by a lead added in the same sync lost the
    change's time (each person is sent after the people who added and changed them, `byMakers`).
  - Records: ADR-014's note follows. `test_guild.py` holds the first lead kept active; `check:state` the fold by
    project and `byMakers`; `check:guild` a deviation owed and a clear during a sync (three of these fail on
    e313119's lines). `check:guild`'s stand-ins answer the project rows with a 503: a reset reads them, and the
    stand-in had answered with the Guild ledger, an unhandled rejection a later wait brought out.
  - Checked in Chromium over the built app: the walk holds again, and a page whose list stays unanswered opens the
    address and remembers nothing.
  - Checks: `pnpm typecheck`, `pnpm build`, the reproduction twice (`RESULT: NO-DEFECT`), `check:state`, `check:guild`,
    `check:plan`, `check:figures`, `test:reconcile`, `gen:components --check`, `pnpm smoke` (20 screens) and
    `pnpm prove --steps 9` (55 checks) pass; `pnpm test:core` 3073 passed, 1 skipped, 175 deselected (5 min 52 s).
- Group 3, H7-04 (S1): a scope's overrides went to the service as one list (`rowsOf`), and the service replaced the
  scope whole (the overrides branch of `project_state._put`), so of two tabs on one Proforma scenario's panel the
  second tab's write deleted the first tab's kept override, with no word on either page.
  - The fix, on the service: `PUT /api/state/overrides/{scope}` takes the rows the page's view stood on beside the
    rows it sends (`StateWrite.base`), and `_put` lays the write on what the scope keeps key by key
    (`project_state._merged`). A key the page set or took back is changed where the service keeps it as the page read
    it, or already as the page sends it; a key the page left as it read it stays as kept, another page's among them;
    a key another page changed since, which this page changed too, refuses the whole write in words naming the key and
    who kept it, a 422, nothing kept. Two rows compare as the `Override` model reads them (`_as_read`), so `3` and
    `3.0` are one value, and a kept row that does not read compares as no row. Each key is written on its own, so a
    row the write leaves as kept keeps its maker and its time. The answer is the scope as it then holds. A list or a
    base naming one key twice, a base of another shape, and a base sent with another kind are refused in words. A
    write without a base replaces the scope whole, as before.
  - The fix, on the page: an overrides write in the outbox carries `base`, the scope's list in the state the change
    was made from (`changes`); a later write that replaces an unsent one stands on what that one stood on, and a write
    an older page queued with none stays whole (`enqueue`); a write made while its scope's write was out stands on what
    that write sent (`flushProjectState`). The page lays the service's answer into its view and its `stateSeen` alike,
    so it shows the other page's key and sends nothing more; a refused write is said in the service's words, and the
    page reads the project's overrides again (`rereadOverrides`).
  - Tests: five in `core/tests/test_project_state.py`, two writes to one scope from two lists each holding one key
    among them (the route keeps both and answers both), a key both pages changed refused in words with the first
    kept, a key taken back since refused, number forms, a kept row's maker and time, and the refusals of a base. Eleven
    in `scripts/check-state.ts` (a scope's overrides from two pages): the rows a write carries, what a replacing write
    stands on, the body sent and the answer taken back, the store laying the answer in, a change made while its
    scope's write was out, and a refusal said and read again (the review below rewrote the in-flight case).
  - The reproduction: `bash bughunt/repro/H7-04/run.sh`, twice in Chromium over the built app, reads
    `RESULT: NO-DEFECT` (`after-fix-run1.log`, `after-fix-run2.log`): after tab B typed `titre=5.678` the service held
    `feed_glucose_conc=1.234` and `titre=5.678`, and tab A after a reload showed its value overridden.
  - Records: `project_state.py`'s docstring, `docs/api/studies.md`, ADR-014's note, the Paid row, and the Open row
    narrowed to the kinds the service keeps whole.
  - Checks: `pnpm typecheck`, `check:state` (the eleven above among its checks), `check:plan`, `check:figures`,
    `check:guild`, `test:reconcile`, `gen:components --check`, `pnpm build`, `pnpm smoke` (20 screens) and
    `pnpm prove --steps 9` (55 checks) pass; `test_project_state.py` 72 passed; `pnpm test:core` 3082 passed, 1
    skipped, 175 deselected (5 min 59 s). No model was called.
- The review of the H7-04 fix (4d224fd): three readers (the service's merge, the page's queue, regressions and
  records), a verifier per claim; 11 claims, 9 confirmed, 1 refuted and 1 confirmed of the same order, read below as
  one S3.
  - Fixed, the page's queue (four claims, two S2): a later write of a scope replaced the scope's last queued write and
    took its rows read, even when that write had reached the service (its answer lost, sent and saved at a closing
    page, or another tab's taken at load), so a key taken back stayed kept, or the page's own second change was refused
    as another page's; and the rebase after a round took the rows of the row's last kept write, so a change made while
    a refused write was out could carry the refused value in. A later write now replaces only a write this page never
    handed to a flush (`unsent`, `queueOwed`); any other stays queued, and the later write follows it on the rows
    `changes` gave it. Sent in order, each lands whether or not the one before was kept. The rebase is gone.
  - Fixed, the read after a refusal (two claims, one S2): a read that predated a write the service answered while it
    was out laid the older scope over the page. The newest read alone is laid, and a scope the service answered since
    the read began keeps what the page holds (`rereadOverrides`).
  - Fixed, the refusal's words (two claims, S3): a chosen reading's depositor and reading time were named as who kept
    the key and when; the words name the row's maker and, for a reading, the reading (`_changed_since`).
  - Fixed, the answer's order (S3): a changed key is written again and a load serves it last, while the answer kept it
    in place, so the page laid in a reordered list and the panel resolved again. The answer is the scope as the next
    load serves it (`_put` reads the scope again; `_served`), and the page lays an answer in only when its rows differ
    from those it sent (`sameOverrides`).
  - Recorded (S3): two copies of one write that added a key (two tabs holding one owed write, H7-01) both land, and
    the second puts back a key taken back between them; comparing rows cannot tell a key never kept from one taken
    back. A copy replaced the scope whole before the fix. The Open row names the remedy, a write that carries an id
    the service keeps, and ADR-014's note says so.
  - Tests: two in `test_project_state.py` (a refusal over a chosen reading names who chose it and the reading; the
    answer is the scope as the next load serves it), each failing on 4d224fd's lines. `check:state`'s H7-04 section
    runs the store against a stand-in that merges as `_merged` does: a write whose answer was lost, then a take-back or
    a second value; two tabs' writes taken at load, one refused, with a change made while it was out; a read that
    predates a write the service answered; an answer holding the rows sent. Five fail with the replacement rule
    removed, one with the read's guard removed, one with the answer's comparison removed.
  - Checks: `pnpm typecheck`, `pnpm build`, the reproduction twice (`RESULT: NO-DEFECT`, the logs beside the hunt's),
    `check:state`, `check:guild`, `check:plan`, `check:figures`, `test:reconcile`, `gen:components --check`,
    `gen:api --check`, `pnpm smoke` (20 screens) and `pnpm prove --steps 9` (55 checks) pass; `test_project_state.py` 74
    passed; `pnpm test:core` 3084 passed, 1 skipped, 175 deselected (5 min 19 s). No model was called.
- The second review of the H7-04 fix (c264fb4), held to S1 and S2 at the owner's word: one S2, confirmed and fixed. A
  flush counted every write it took as one that may have reached the service, those after the first unanswered write
  among them, so while the service was away each change to a scope queued a write of its own and the outbox grew with
  every keystroke. A write counts so once its request goes out (`flush`'s `sending`); `check:state` holds a scope at two
  owed writes while the service is away, and fails on c264fb4's line. The S3 findings stand unfixed: a clash on a key
  never kept reads "taken back", an older reading with no `chosenBy` names "another page", and `StateKept`'s docstring
  still reads "as the page sent it" for whole rows.
