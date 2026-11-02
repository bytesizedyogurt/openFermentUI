# openFerment — One active program, nothing invented on screen, Postdoc with every tool

**Document:** OF-BLD-016 · **Version:** 2.0 · **Date:** 20 October 2026, 01:50 New York (v1.0 at 23:30 on 19 October was written against `6097df7` and is superseded: its Phases 3 and 5 landed tonight as PR #10)
**Repo:** `bytesizedyogurt/openFermentUI` · **start from** `main` @ `7e3ebb0` (PR #10, "the yeast-ethanol demo prep", merged 2026-10-20 00:59 New York)
**Merge in:** `claude/of-bld-015-postdoc` @ `7298143` (OF-BLD-015 Phase 7 complete: §7.1–§7.6, §7.R, Part B truth pass). Trial merge against `7e3ebb0` conflicts in two files only: `core/openferment_core/postdoc_agent.py` and `core/tests/fixtures/prototype/ask-draft-stream.jsonl`.
**Work branch:** `claude/of-bld-016-demo`, cut from `7e3ebb0`
**Executor:** Claude Opus 5.5 in Claude Code at extra-high effort, overnight, unattended. Sean reads the result at about 07:00 New York and shows the app to Dr. Ramarao that morning. The Mini serves `main` at `https://seans-mac-mini-1.tail918752.ts.net/` through Tailscale Funnel.
**Goal in one line:** by morning `main` carries Postdoc's read and write tools with their gates; casein (threads A–O) and PHA (thread P) are archived out of every default view with one switch to bring them back; every scripted reply, invented sample, demo banner and dead control is gone from what a user sees; the Witness scorecard is measured on thread Q; and one run sheet tells Sean what to click, what to say and what to steer around.

---

## For Sean: what this builds, in plain words

Four phases, in the order that protects the meeting:

1. **Land Phase 7.** The Postdoc-reaches-everything work (eleven read tools, eleven write tools behind gates, the proposals card on Home, a 24-stage verify) merges into tonight's yeast tree. Two files conflict; the session resolves them, regenerates the fixture, and confirms with one live question of each kind.
2. **Programs, and two archived.** Casein and PHA become archived programs. Their papers, values, strains, products, scenarios and questions stay in the repository and leave every screen, count, prompt and Postdoc evidence pool by default. A switch in Settings shows them again. Nothing is deleted tonight.
3. **Nothing invented on screen.** The scripted chat player goes; the two seed chat sessions, the invented activity feed and the invented Guild team go; "Load a sample run" goes; the demo banner, "Signed in as demo curator", the "Reset demo data" buttons, the dead Intake controls and the stale tour stop go; the ten seed runbooks and protocols that describe runs nobody made are marked as examples and hidden with the archive. Every empty state names the real next step.
4. **The run sheet, and the truth.** Witness's retrieval scorecard is rerun on thread Q (it predates it today). The session asks the meeting's questions live, records cost and time, merges `DEMO-YEAST.md` and `DEMO-PHASE7.md` into one `docs/DEMO.md` with a "Steer around" list, runs the truth pass and opens the pull request.

If the clock allows, Phase 5 adds a glucose-to-ethanol Proforma scenario and a yeast batch protocol whose every number is anchored to a sentence. Both are good to have and neither is the meeting.

Your part in the morning is Appendix 1 (about fifteen minutes). Appendix 4 is what you can do tonight before sleeping so the Mini already serves the yeast version as a fallback.

---

# PART A — HOW TO EXECUTE THIS DOCUMENT

OF-BLD-014 Part A applies in full (`docs/build/OF-BLD-014.md`, A.1–A.7), with these changes:

- **The id prefix is `OF-BLD-016`.** Commit messages are `OF-BLD-016 §n.m: <what>`. The handled list is `git log --format=%s | grep -o 'OF-BLD-016 §[0-9]*\.[0-9A-Z]*' | sort -u`.
- **The document lives at `docs/build/OF-BLD-016.md`** for the length of the build. `docs/build/` stays: OF-BLD-015's closing pass owns its deletion.
- **The session is unattended.** Where OF-BLD-014 A.5 says "Ask", take the default in Part D, record the choice in `STATE.md` under the step, and go on. One exception remains: a change that would delete corpus data, a record, a candidate, a decision, an artifact or a person's entry stops the session.
- **Wall clock.** `date -u` at the start of every step. From **10:30 UTC** (06:30 New York) start no new step: finish the step in hand, make verify green, push, write the report (A.7) and stop. A step that cannot go green by then is reverted and named in the report.
- **Context.** Past two thirds: finish the step, commit, push, stop, name the next step. Sean's "next phase" resumes there.
- **Model rule (OF-BLD-015 Part A.3).** Every call the platform makes runs `claude-haiku-5-5` at effort `medium` from the environment; `llm.py` defaults stay untouched. The build session runs on Opus.
- **Spend.** Appendix 3 estimates under 1.00 USD. A batch costing three times its estimate stops and reports.
- **Verify green before every commit, every commit pushed.** The gate is twenty-four stages once Phase 1 lands (`check:tools` joins after `check:seed`).

---

# PART B — MEASURED STATE

Measured 20 October 2026, 01:30 New York, from a fresh clone. A.2 step 5 applies: confirm each row a step relies on before building on it.

## B.1 `main` @ `7e3ebb0` — what PR #10 landed tonight

- **Thread Q**, program three: `src/data/corpus/threadQ.ts`, 22 sources (two NREL reports via OSTI, two SGD strain entries, 18 Europe PMC papers), all 22 fetched with full text, licences recorded. Extraction on Haiku: **163** anchored values, 15 dropped, $0.25. Index: 88 papers, 7,179 passages and vectors. The rule module is `threadp.py` with a `ThreadRule` per thread (`THREAD_Q`); scripts `thread:propose:q`, `thread:apply:q`; the letter pattern is `[A-Q]` in `papers.ts`, `src/sim/chat.ts`, `golden-path.mjs`.
- **Ontology**, family "Growth and product kinetics": `monod_ks`, `biomass_yield_substrate`, `ethanol_yield_substrate`, `ethanol_titre`, `ethanol_productivity`, `ethanol_inhibition_ki`, `ethanol_max_conc`, `substrate_inhibition_ki`, `ethanol_lp_alpha`, `ethanol_lp_beta`, `ethanol_mesp`; ranges accepted by Sean. Strains `s-cerevisiae-s288c`, `s-cerevisiae-cenpk113-7d` from SGD; the old `s-cerevisiae` species entry remains and carries the invented nootkatone runbook.
- **geneOS**: Yeast9 (yeast-GEM v9.1.1, CC BY 4.0) and iMM904 (BiGG, non-commercial, accepted by Sean) on the shelf, hash-pinned; ethanol ceiling on glucose 0.5114 g g⁻¹ on each; `/geneos/model` has an ethanol view; `test_geneos_yeast_live.py`.
- **Postdoc**: Live conversations are `LiveConversation`s in the store and the Durable tier, listed in the sidebar, resumed from Home; a follow-up sends prior turns as words (`postdoc_agent._opening`). The page opens in Live when the service answers; Scripted mode is offered only when it does not. `src/data/livePrompts.ts` holds the five tested questions as buttons. `selling_price` cites the stored corn stover benchmark (1.968 USD gal⁻¹).
- **Mini**: `deploy.sh` syncs every extra. `docs/DEMO-YEAST.md` §5 is the run order for the Mini and §4 its avoid-list.
- `pnpm verify` 23 of 23 on the merged tree (STATE, 2026-10-20). Day's model spend $0.51.

## B.2 `claude/of-bld-015-postdoc` @ `7298143` — Phase 7, complete

Eleven read tools and eleven write tools in the registry (29 names), one input shape each; `module_stores.py`, `tools/modules.py`, `tools/writes.py`, `tools/gates.py`, `proposals.py`; `docs/TOOLS.md`; `GET /api/proposals`, carry-out and dismiss under a named person; a proposals card on Home; the coverage pass before round one; `check:tools` as the eighth verify stage (twenty-four); `test_mcp` counts 31 tools. Reads go to the model non-strict (eighteen strict tools exceed the API's grammar limit). `CLAUDE.md`, `README.md`, `COMPONENTS.md` updated on the branch. `docs/build/OF-BLD-015-phase7.md` and `DEMO-PHASE7.md` are the document and its run sheet (eight cross-module questions, $0.0345 for all eight).

## B.3 Still invented, scripted or dead on screen (after PR #10)

| What | File | Shown where |
|---|---|---|
| Scripted chat player | `src/sim/chat.ts` (661 lines), `src/sim/latency.ts`; `send`, `sendFlow` imported by `Postdoc.tsx`; `chatMode` in the store; offered when the service is down | Postdoc |
| Seed chat sessions, activity feed, collections | `SEED_SESSIONS`, `ACTIVITY`, `COLLECTIONS` in `src/data/misc.ts` | Postdoc sidebar, Home |
| Suggested prompts | `SUGGESTED_PROMPTS` in `src/data/flows.ts` (casein and PHA flows F1–F12, F-SIALYL); `livePrompts.ts` holds the yeast five | Postdoc empty state (scripted) |
| Invented Guild team | `src/data/guildSample.ts`, "Show a sample team" in `GuildMatrix.tsx`, `GuildPeople.tsx`, `GuildChecks.tsx`, `PrimerPath.tsx`; `store.ts` ~2849 | Guild, Primer, Home → Workforce |
| Invented fermOS run | `fermosSample.json/.ts`, "Load a sample run" in `FermOS.tsx`, `FermOSForecast.tsx` | fermOS |
| Figure samples | `figureSamples.json` (sample PHB yields) in `SettingsFigures.tsx` | Settings → Figure grammar |
| Seed runbooks, protocols, depositions, lessons for runs nobody made | `runbooks.ts` (10, incl. `rb-taq-kigali`, `rb-nootkatone`), `protocols.ts` (9; six casein, PR-OD-01 and PR-CIP-01 generic), `runOutputs.ts`, `learn.ts` m0–m5 casein, m6 placeholder lessons, `scenarios.ts` `sc-s1…s3` | Runbooks, Protocols, Depositions, Ledger, Primer, Proforma, Home |
| Demo chrome | `App.tsx` `DemoBanner` ("Real literature · modeled economics"), "Signed in as demo curator"; Settings "Reset demo data"; `IntakeIngest.tsx` "Reset demo data", "scripted demo budgets", placeholder DOIs `10.0000/openferment.demo.001`; `BioRepo.tsx` "demo extractor"/"demo shelf" toasts; `CommandPalette.tsx` "New Proforma scenario from cw15 defaults"; `GuidedTour.tsx` | shell, Settings, Intake, BioRepo, palette |
| Dead controls | `IntakeIngest.tsx` "Import by DOI list" (inactive), "Upload PDFs" | Intake → Ingest |
| Placeholder header | `skills.ts` "PLACEHOLDER CONTENT" over fourteen real bench skills | Guild → Skills |
| Stale scorecard | Witness → Retrieval predates thread Q (`DEMO-YEAST.md` §4) | BioRepo → Witness |
| Casein examples in prompts and copy | `postdoc.py`, `validate.py`, `practice.py`, `AnswerPlanView.tsx`, `LessonEmbeds.tsx` use cw15 as the example; `Dominion.tsx` header count 117 against 119 molecules; `README.md`; `docs/DEMO.md` (the PHA demo) | copy |

Test fixtures and the service double (`demo.py --prototype`, `scripts/lib/service-double.mjs`, `europepmc/search-pha.json`, the B5 demo set) are how verify runs with no key and a user never sees them. They stay. `pnpm demo:offline` labels its replays and stays as a test and fallback tool; Appendix 2 tells Sean to leave it closed.

## B.4 Guards that rest on the casein and PHA data

`check:anchors` floor 93 of 104 (casein records); `check:lock` eight seed digests (seed runbooks); Witness gold set 46 records on 14 casein papers; `test:export` and the overlay fixtures on B5 (PMC8471596); the K question set; `test:slow`'s PHA flowsheet; Appendix 2 regressions (cases 1–6); the golden path (31 steps, walks the PHA path); the smoke's `/geneos/hosts/cw15`, `/biorepo/paper/H4`, `/proforma/scenario/sc-pha-1`. Deleting the data means rewriting all of these first. Part D says archive.

---

# PART C — WHAT IS TRUE WHEN THE DOCUMENT IS DONE

1. `main` carries OF-BLD-015 Phase 7: Postdoc reads every module, writes through each module's own function behind the gates, and proposals await a person on Home; verify is twenty-four stages, green.
2. Settings → Programs lists **Yeast ethanol (active)**, **Casein (archived)**, **PHA (archived)**. With archived programs hidden, the default, no screen, filter, count, prompt or Postdoc evidence pool shows a casein or PHA paper, value, strain, product, scenario, protocol, runbook, lesson or question. With the switch on, everything shows exactly as before. Verify is green in both positions.
3. Postdoc has no scripted path. With the service down it says so, keeps the history, and offers nothing invented. Its empty state offers the yeast five and the cross-module questions of Appendix 2.
4. No default view shows a sample team, a sample run, a sample figure, a demo banner, a demo curator, a reset-demo button, a placeholder DOI, a dead control or a casein example. Guild with no ledger shows how to add the first person; fermOS with no deposited run names what to deposit; the ledger counts zero.
5. Witness → Retrieval carries a scorecard measured on thread Q, dated, with the chosen lane.
6. `docs/DEMO.md` is the one run sheet: start, what to point at, the questions in order with what each showed tonight, the "Steer around" list. `DEMO-YEAST.md` and `DEMO-PHASE7.md` are folded into it and removed.
7. `README.md`, `COMPONENTS.md`, `CLAUDE.md`, `docs/TOOLS.md`, `STATE.md` say true things measured that morning. A pull request `claude/of-bld-016-demo → main` is open with the STATE entries as its description.

---

# PART D — DECISIONS

- **D1 — Archive, do not delete.** As B.4 says. Deletion is a later document with the guards rewritten first.
- **D2 — Merge, do not rebase.** Phase 7 lands as a merge commit of `claude/of-bld-015-postdoc` into the work branch, conflicts resolved by hand, so its history and STATE lines stay intact. The two conflicts: `postdoc_agent.py` keeps both the coverage pass and the module tools (branch) and `_opening` with `PriorTurn`s (main); the fixture is regenerated by `demo.py --prototype`, never edited.
- **D3 — Example content is flagged, not written over.** `example: true` on every seed runbook, protocol, deposition, lesson and scenario that describes a run nobody made; hidden with archived programs; lock digests untouched. Mirrored in `types.ts` and `models.py` where a Pydantic twin exists; `PAIRS` updated.
- **D4 — Samples stay for the double, leave the screen.** `demo.py --prototype` keeps writing `fermosSample.json` and `figureSamples.json`; the screens stop offering them; smoke assertions change from "sample drawn" to "empty state names the next step".
- **D5 — Scripted chat is removed with its tests.** `src/sim/` is deleted; `chatMode` goes; the F flows stay in `flows.ts` as the eval set; `SUGGESTED_PROMPTS` becomes a function of the active programs and reads `livePrompts.ts`.
- **D6 — The two host entries.** `s-cerevisiae` (the species catalogue entry) stays, loses nothing, and the nootkatone runbook that points at it is an example (D3). The two SGD strains are the yeast program's hosts.
- **D7 — Thread letters.** Casein is A–O, PHA is P, yeast is Q. The programs file names the letters; `check:seed` holds the `[A-Q]` pattern to it.
- **D8 — Branching.** Work on `claude/of-bld-016-demo` from `7e3ebb0`. The PR targets `main`. The Mini runs `main`: Sean merges, then `deploy.sh`.
- **D9 — Rule 1 covers the builder.** No process number enters seed data or product code. Protocol values (Phase 5) come from a cited sentence of a fetched thread Q paper through anchoring, or stay blank for Sean.
- **D10 — The yeast questions for the run sheet** are Appendix 2. A question that fails for a reason in the code is fixed with a failing test first; one that fails for want of data is recorded and goes to "Steer around".

---

# PART E — CONTRACTS THAT HOLD IN EVERY PHASE

OF-BLD-014 Part E and OF-BLD-015 Part A.3 hold, with:

- **E.1′ A program is data.** `src/data/programs.ts`: id, name, letters, status (`active` | `archived`), one line. The store exposes `activePrograms()`, `showArchived` (Durable), and `programOf(paperId | recordId | strainId | productId | scenarioId | protocolId | runbookId | lessonId)`. Every list a screen renders, every count on Home, every evidence pool and coverage sweep the service builds, and every suggested prompt filter through it. `check:seed` fails when a letter has no program or a program has no letter.
- **E.2′ The service knows the programs.** `export:corpus` writes `programs` into `corpus.json` and `modules.json`; `evidence_pool`, `retrieve`, `module_stores.coverage`, the read tools and `AskRequest` take `includeArchived` (default false); the API passes the switch through. With the switch off, a question naming an archived entity gets a coverage line *found in archived program PHA (hidden)* and a gap naming the switch.
- **E.3′ Nothing invented reaches a default view.** The user-facing strings `demo`, `sample run`, `stand-in`, `placeholder` and `scripted` appear in `src/` only in `pnpm demo:offline`'s replay label; `check:seed` greps for them (negative-tested).
- **E.4′ Routes are never removed from the smoke list.** What a route asserts changes in the same commit.

---

# PHASE 1 — Land Phase 7

## §1.1 Branch, baseline, pull

**Files:** `docs/build/OF-BLD-016.md` (this file), `docs/build/PROMPT-016.md`, `STATE.md`, `CLAUDE.md` (one line under the active-build section: this document, this branch).

1. `git fetch --all --prune`; check out `main` at `7e3ebb0`; `git switch -c claude/of-bld-016-demo`.
2. `bash scripts/session-start.sh`; `pnpm ready` ends `lane: full` on `claude-haiku-5-5` for both roles, or the LIVE steps are owed (A.4).
3. `pnpm data:pull`; record counts (papers fetched, candidates, passages, vectors, artifacts, live plans, proposals).
4. `pnpm verify`; record stages and time. Red is a stop.
5. Confirm Part B. Append the STATE heading `## OF-BLD-016 (branch claude/of-bld-016-demo, from 7e3ebb0)`.

**Commit:** `OF-BLD-016 §1.1: the branch, the document, and the baseline measured`

## §1.2 Merge OF-BLD-015 Phase 7

**Files:** the merge; `core/openferment_core/postdoc_agent.py` (by hand); `core/tests/fixtures/prototype/*` (regenerated); `STATE.md`.

1. `git merge --no-ff origin/claude/of-bld-015-postdoc`. Resolve `postdoc_agent.py` so that `ask` runs the coverage pass before round one, offers the 29 tools (reads loose, the seven strict), and opens with `_opening`'s prior turns; a test in `test_postdoc_agent.py` asserts all three on one run.
2. `pnpm demo:fixtures --prototype` regenerates the stream fixtures; `test_demo` holds them to the code.
3. `pnpm verify` (twenty-four stages). Commit the merge with the step message.
4. LIVE (needs the key): `pnpm prototype:up`; ask question 1 of DEMO-PHASE7 (Dominion and runbooks) and question 1 of DEMO-YEAST (the Yeast9/iMM904 ceiling) through the stream route; record claims kept and dropped, modules read, cost, seconds. Both must answer with claims kept; a regression against either run sheet's numbers is fixed before going on.

**Commit:** `OF-BLD-016 §1.2: OF-BLD-015 Phase 7 merged onto the yeast tree, and both run sheets still answer`

## §1.R and §1.T

§1.R as A.6 over the merge diff (a fresh subagent; the resolution of `postdoc_agent.py` is what it reads hardest). §1.T: `CLAUDE.md` (one active-build section naming this document; the registry, stages and model rule as the merged tree has them), `README.md`, `COMPONENTS.md`, `STATE.md`.
**Commits:** `OF-BLD-016 §1.R: …` · `OF-BLD-016 §1.T: README, CLAUDE and STATE for the merged tree`

---

# PHASE 2 — Programs, and two archived

## §2.1 Programs as data

**Files:** `src/data/programs.ts` (new), `types.ts`, `models.py` (`Program`), `check-plan.mjs`, `src/store.ts` (`activePrograms`, `programOf`, `showArchived` Durable), `check-seed.ts` (letters ↔ programs; the `[A-Q]` pattern read from the file), `export-corpus.ts`, `corpus.py`, `strains.ts` / `products.ts` / `scenarios.ts` / `protocols.ts` / `runbooks.ts` / `learn.ts` (`program` or `programs` field where the entry is program-specific), `core/tests/test_programs.py` (new).

Three entries: `casein` (A–O, archived), `pha` (P, archived), `yeast` (Q, active). `programOf` resolves by thread letter, by the paper a record cites, by the entry's own field, or by the product or strain a runbook names; an entry with no program is general and always shows.

**Tests.** The projection carries three programs; `programOf` on a P paper is `pha` and on `s-cerevisiae-cenpk113-7d` is `yeast`; an unknown letter fails `check:seed` (negative-tested).
**Commit:** `OF-BLD-016 §2.1: a program is data, and three are declared`

## §2.2 Every list filters by program

**Files:** `Home.tsx` (strip counts active programs; archived as one muted line), `BioRepo.tsx`, `BioRepoSearch.tsx`, `Intake.tsx`, `IntakeIngest.tsx`, `Organisms.tsx`, `StrainPage.tsx`, `Molecules.tsx`, `Dominion.tsx`, `Proforma.tsx`, `GeneOS.tsx`, `GeneOSModel.tsx`, `Protocols.tsx`, `Runbooks.tsx`, `RunbookLedger.tsx`, `Depositions.tsx`, `Witness.tsx`, `Compare.tsx`, `Guild.tsx` (review queue), `Primer.tsx`, `Settings.tsx` (Programs section with the switch), `flows.ts` (`SUGGESTED_PROMPTS` by program), `smoke.mjs`, `golden-path.mjs` (sets `showArchived` on at its start; its PHA walk passes unchanged), `check-store.ts` (round-trips the switch).

One selector in the store; screens call it. A deep link to an archived entity opens it under a banner naming the program and the switch.

**Commit:** `OF-BLD-016 §2.2: casein and PHA leave every default view, and one switch brings them back`

## §2.3 The service honours the switch

**Files:** `evidence_pool.py`, `retrieve.py`, `module_stores.py` (coverage and the read tools), `tools/records.py`, `tools/passages.py`, `tools/modules.py`, `postdoc_agent.py`, `api.py` (`includeArchived` on `/api/ask`, `/api/ask/stream`, `/api/rag/search`, `/api/tools/{name}`), `models.py` (`AskRequest.includeArchived`), `mcp_server.py`, `src/lib/postdoc.ts`, tests in `test_programs.py`, `test_postdoc_agent.py`, `test_module_tools.py`.

**Tests.** Pool with the switch off holds no A–P record or candidate and the coverage line says *archived (hidden)*; with it on, counts equal §1.1's (negative-tested by removing the filter).
**Commit:** `OF-BLD-016 §2.3: the evidence pool, the coverage pass and the module tools honour the program switch`

## §2.R and §2.T

**Commits:** `OF-BLD-016 §2.R: …` · `OF-BLD-016 §2.T: README, COMPONENTS and STATE for programs`

---

# PHASE 3 — Nothing invented on screen

## §3.1 Postdoc speaks only through the service

**Files:** `src/sim/` (deleted), `Postdoc.tsx`, `store.ts` (`chatMode`, `sessions`, `createSession`, `appendMessage`, `updateMessage`, `pinEvidence` removed where only the scripted path used them; `LiveConversation`s stay), `misc.ts` (`SEED_SESSIONS`, `ACTIVITY`, `COLLECTIONS` removed; Home's activity card reads real events or shows its empty state), `flows.ts`, `livePrompts.ts` (gains the cross-module questions of Appendix 2), `AnswerPlanView.tsx`, `check-seed.ts` (`grep -r "@/sim" src` finds nothing; the E.3′ string check), `smoke.mjs`, `golden-path.mjs` (the chip pattern moves to `programs.ts`), `CommandPalette.tsx`.

With the service down: *Postdoc needs the service. Start it with `pnpm prototype:up`*, history kept, the typed question kept.

**Commit:** `OF-BLD-016 §3.1: Postdoc speaks only through the service`

## §3.2 The team, the sample run, the demo chrome, the dead controls

**Files:** `guildSample.ts` (deleted) and its uses (`store.ts`, `Guild*.tsx`, `PrimerPath.tsx`, `PrimerPractice.tsx` `practiceLearner`, `BenchCheck.tsx`, `engine/checks.ts`, `Home.tsx` Workforce, `check-guild.ts`); `FermOS.tsx`, `FermOSForecast.tsx` ("Load a sample run" goes; the empty state names the readings to deposit, and `PR-YEAST-01` once §5.2 lands); `SettingsFigures.tsx` (draws over real artifacts from `/api/artifacts` when any exist, else the legend alone); `App.tsx` (`DemoBanner` goes; the sign-in line shows the reviewer name or *No reviewer name set* with the link); `Settings.tsx` ("Reset demo data" becomes *Clear this browser's data*, Durable tier only); `IntakeIngest.tsx` (the second reset button, the placeholder DOIs and "scripted demo budgets" go; "Import by DOI list" posts to a new `POST /api/intake/propose` that writes a proposal row for a person's approval and nothing else, or is removed; "Upload PDFs" is removed with one line saying how a paper enters today); `BioRepo.tsx` toasts; `GuidedTour.tsx` (every stop opens a route that exists, or the tour goes); `skills.ts` header; `ProformaScenario.tsx` and `Home.tsx` *demo* → *industry estimate* where that is the provenance; the casein examples in `postdoc.py`, `validate.py`, `practice.py`, `AnswerPlanView.tsx`, `LessonEmbeds.tsx` become yeast examples (`cenpk113-7d` is an identifier token like `cw15`); `Dominion.tsx` header count.

**Tests.** `check:guild` builds its ladder fixtures in memory; the smoke asserts the Guild, fermOS and Witness empty states; the golden path's fermOS beat runs against the double's fixture through a deposition the double supplies, or is dropped with the count updated; E.3′ string check green.
**Commit:** `OF-BLD-016 §3.2: the invented team, the sample run, the demo chrome and the dead controls leave the screens`

## §3.3 Example content is flagged and hidden

**Files:** `runbooks.ts`, `protocols.ts`, `runOutputs.ts`, `learn.ts`, `scenarios.ts`, `types.ts`, `models.py`, `check-plan.mjs`, `store.ts` (`example: true` treated as archived), `check-lock.ts` (digests unchanged), `check-seed.ts`, `smoke.mjs`.

All ten runbooks, the six casein protocols, every deposition in `runOutputs.ts`, lessons m0–m5 and m6, and `sc-s1…s3` are examples. PR-OD-01 and PR-CIP-01 (generic methods) and any lesson that teaches a method with no run behind it stay, with the word *placeholder* removed from their copy. Record the decision per entry in STATE. `check:seed` requires `example` on any runbook carrying a locked prediction with no deposition behind it (negative-tested).

**Commit:** `OF-BLD-016 §3.3: runs that never happened are marked as examples and leave the default views`

## §3.R and §3.T

The truth pass rewrites README's "What is real, and what is modeled" table.
**Commits:** `OF-BLD-016 §3.R: …` · `OF-BLD-016 §3.T: README, COMPONENTS and STATE with nothing invented on screen`

---

# PHASE 4 — The run sheet, and the truth

## §4.1 LIVE — the scorecard on thread Q, and the meeting's questions

**Needs:** the key, the index.

1. `pnpm rag:questions --n 100` over thread Q passages, `pnpm rag:eval`; record K, S, F sizes, nDCG@10 and recall@10 per lane, the chosen lane; paid lanes attempted on Haiku and recorded if declined. `pnpm witness:numbers`.
2. `pnpm prototype:up`; ask each Appendix 2 question twice through the stream route. Record per question: modules read, claims kept and dropped with reasons, cost, seconds. D10 governs fixes.
3. `docs/questions-yeast.txt` with the list; `pnpm ask:batch docs/questions-yeast.txt`; `pnpm data:push`.

**Commit:** `OF-BLD-016 §4.1: the scorecard on thread Q, and the meeting's questions asked live`

## §4.2 One run sheet

**Files:** `docs/DEMO.md` (rewritten: start on the Mini and the fallback on a laptop; what to point at; the questions in order with what each showed in §4.1; **Steer around**), `docs/DEMO-YEAST.md` and `docs/build/DEMO-PHASE7.md` (folded in and deleted), `README.md` (points at `docs/DEMO.md`).

**Commit:** `OF-BLD-016 §4.2: one run sheet for the yeast path, written after walking it`

## §4.R and §4.T

§4.R over the whole branch diff. §4.T: `README.md` top to bottom with counts measured now; `COMPONENTS.md`; `CLAUDE.md` (a Programs section; no scripted chat, no sample team; the active-build section names this document); `docs/TOOLS.md` (archive flag on the reads); `STATE.md` final entry; `pnpm shots --prefix of-bld-016` for `/`, `/postdoc`, `/geneos/model`, `/settings`; `pnpm verify`; push; the pull request to `main` with the STATE entries as its description and a note that it carries OF-BLD-015 Phase 7. Appendix 1 pasted at the top of the report.

**Commits:** `OF-BLD-016 §4.R: …` · `OF-BLD-016 §4.T: say true things about the prototype, everywhere the repository speaks`

---

# PHASE 5 — If the clock allows

## §5.1 Proforma: glucose to ethanol, every input named

**Files:** `flowsheets/ethanol_glucose_v0.py` (new: fermenter, beer column, rectifier, molecular sieves, no input value in the file), `proforma.py` (`bind` takes thread Q records: `ethanol_titre`, `ethanol_yield_substrate`, `ethanol_productivity`; sugar price and feed as assumptions), `scenarios.ts` (`sc-yeast-1`, `program: 'yeast'`), `ProformaScenario.tsx`, `test_proforma.py`, `test_slow`.
**Commit:** `OF-BLD-016 §5.1: Proforma prices glucose to ethanol, with every input bound or waiting for a name`

## §5.2 A yeast protocol with every number anchored

**Files:** `protocols.ts` (`PR-YEAST-01`, `program: 'yeast'`), `skills.ts` (tags), `learn.ts` (one lesson, *Why ethanol yield has a ceiling*, no quantity of its own), `check-seed.ts`, `core/tests/test_protocol_anchors.py`.

Shake-flask batch; sampling at timed points for OD, glucose and ethanol; readings deposited with `sampleTimes` and `seriesRoles` so fermOS can fit them. Every quantity is anchored to a fetched thread Q passage through `anchor_candidate` and shown with its citation, or is `___` with *Sean fills this from his lab's practice*. `check:seed` refuses a digit in an active-program protocol step that carries neither (negative-tested).
**Commit:** `OF-BLD-016 §5.2: a yeast batch protocol whose every number is anchored or left for Sean`

## §5.R and §5.T

**Commits:** `OF-BLD-016 §5.R: …` · `OF-BLD-016 §5.T: README, COMPONENTS and STATE for Proforma and the protocol on yeast`

---

# PART F — ORDER OF WORK

| Phase | Steps | Estimate | For the meeting? |
|---|---|---|---|
| 1 | §1.1 §1.2 §1.R §1.T | 1 h 15 | yes: Postdoc with every tool |
| 2 | §2.1 §2.2 §2.3 §2.R §2.T | 2 h | yes: casein and PHA out of sight |
| 3 | §3.1 §3.2 §3.3 §3.R §3.T | 2 h 15 | yes: nothing invented |
| 4 | §4.1 §4.2 §4.R §4.T | 1 h 15 | yes: the run sheet |
| 5 | §5.1 §5.2 §5.R §5.T | 1 h 45 | no |

About six and three-quarter hours of meeting work against roughly five on the clock. The wall-clock rule decides. **§4.1–§4.T run whatever state Phases 2 and 3 are in**, so Sean wakes to a run sheet that matches the tree. When a Phase 3 step is skipped, "Steer around" names what it would have removed.

---

# APPENDIX 1 — Sean's morning, fifteen minutes

On the laptop or the Mini, in the checkout:

```
git fetch --all --prune
git switch claude/of-bld-016-demo && git pull --ff-only
tail -80 STATE.md          # the report; MORNING and STEER AROUND first
cat docs/DEMO.md           # read "Steer around" twice
```

If `MORNING` says green:

1. GitHub → the pull request → **squash and merge** into `main`.
2. On the Mini, in Terminal, in the openferment folder: `git status` (nothing uncommitted; `git stash` if there is, and tell me), then
   ```
   bash scripts/host/deploy.sh --keep-decisions
   pnpm data:pull
   pnpm data:prepare
   sudo launchctl kickstart -k system/com.umutuzo.openferment
   pnpm ready
   ```
   You want `lane: full`, both roles `claude-haiku-5-5`, Yeast9 and iMM904 present.
3. Open `https://seans-mac-mini-1.tail918752.ts.net/` on your phone (cellular). Settings → reviewer name set; Programs shows Yeast ethanol active, the switch off.
4. Postdoc → ask question 1 of `docs/DEMO.md`. If it answers, you are ready.
5. Close any `pnpm demo:offline`. Ram sees the live app alone.

If `MORNING` says stopped: say "next phase" in a Claude Code session on the branch at about 07:15, with a hard stop at 08:30 New York. Anything unfinished then is named in "Steer around" and you demo around it.

---

# APPENDIX 2 — The questions for the meeting

The yeast five from `DEMO-YEAST.md` §3 stay as written, in that order, with their caveats (name the NREL authors, never the year). Then the cross-module questions, which show Phase 7:

6. **What does openFerment hold on ethanol fermentation by Saccharomyces cerevisiae, and in which modules?** — the coverage line, searched eleven, found in N; Intake and BioRepo rows for thread Q.
7. **Which hosts in geneOS could make ethanol, which models sit on their pages, and what ceiling does each give on glucose?** — `geneos_read`, `yield_ceiling`, the two SGD strains.
8. **Draft a runbook for a batch ethanol fermentation in CEN.PK113-7D on glucose, using the extracted yield records and the Yeast9 glucose ceiling as a bound.** — `draft_runbook`; **Turn into a runbook**; **Lock predictions** proposes under the `lock` gate and the card appears on Home; carry it out in Sean's name; the ledger counts one.
9. **What is waiting for a person on Home right now?** — `home_read`: the lock proposal from question 8, the review queue.
10. **What does Proforma need before it can price ethanol from glucose on this evidence, and what does the corn stover benchmark give?** — `selling_price` cites the stored benchmark; with §5.1 landed, `sc-yeast-1`'s inputs waiting for a source.
11. **What is archived in this corpus, and how would I see the PHA work?** — the honest answer about the switch, in words.

Hand Ram the keyboard at question 3 (the growth-rate question he can check against his own knowledge). The point to make once: every number on every screen was written by a paper, a model file, a run or a named person, and the model wrote the words.

---

# APPENDIX 3 — Spend estimate

| Step | Estimate (Haiku 5.5, medium) |
|---|---|
| §1.2 two live questions | 0.01 USD |
| §4.1 rag questions and eval | 0.25 USD |
| §4.1 twenty-two question runs and the batch | 0.15 USD |
| §5.2 anchoring the protocol | 0.02 USD |
| fixture regeneration, tests | 0.05 USD |
| **Total** | **under 0.50 USD**; stop at 1.50 |

---

# APPENDIX 4 — Tonight, before sleeping (optional, ten minutes of typing, twenty of waiting)

`main` already holds the yeast version. Deploying it to the Mini now means the public URL shows thread Q, the ethanol ceiling and the five tested questions in the morning even if the overnight session stops early. In Terminal on the Mini, in the openferment folder, follow `docs/DEMO-YEAST.md` §5 steps 2 to 7: add the four `OPENFERMENT_*` lines to `core/.env`, then

```
bash scripts/host/deploy.sh --keep-decisions
pnpm data:pull
pnpm data:prepare
sudo launchctl kickstart -k system/com.umutuzo.openferment
pnpm ready
```

`data:prepare` fetches thread Q's full text and the two models and takes a while; let it run. Then open the Funnel URL on your phone and ask question 1 of `DEMO-YEAST.md` §3 once.

---

# APPENDIX 5 — What this document leaves alone

- OF-BLD-017 Phase 5 (server-side history, memory, accounts, visibility) — Notion.
- Deleting casein and PHA data — a later document with B.4's guards rewritten first.
- Intake accepting arbitrary sources and the RAG-optimise button; the provenance-labelling redesign; the dual track; the funder map — their own documents.
- OF-BLD-014's two `## Live owed` lines (§4.5 paid lanes on a model the classifier allows; §10.3 `save_real`) — paid after Phase 4 if the clock allows, otherwise left.
- Security of the public URL (no login) — Sean's stated choice for now; OF-BLD-017's accounts are the fix.
