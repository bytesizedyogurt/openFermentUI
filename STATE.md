# STATE

One line per session, newest last — what landed, and the measured number that
says it landed. The full §0.5 report for each session is in that session's
transcript; this file is the index a later session reads first.

## Live owed

LIVE steps built offline whose run waits on a need this machine lacked, one line each: `- §n.m — needs <what> — <the command to run>` (OF-BLD-014 A.4).

- §4.5, the paid lanes — needs a helper model the safety classifier lets through (Haiku is declined, bio) — `pnpm rag:eval && pnpm data:push`
- §10.3, the saved answer — needs `save_real` to save a real Postdoc answer, its artifacts and the retrieval report, as §10.3 step 1 says; the code saves the extraction alone (found 2026-10-16) — build that part, then `pnpm demo:fixtures --real && pnpm data:push`

## Live runs

LIVE steps that ran, one line each: `- §n.m — <date> — <the numbers the step asks for>` (OF-BLD-014 A.4).

- **Yeast-ethanol demo prep, 2026-10-20** (all on Haiku 5.5, effort medium; report `docs/DEMO-YEAST.md`) — thread Q applied on Sean Creighton's approval: **22** sources (2 NREL reports from OSTI, 2 SGD strain entries, 18 Europe PMC papers), **22 of 22** fetched with full text; `intake:extract`: **163** anchored, **15** dropped, $0.25 over two passes; index **88** papers, **7,179** passages and vectors. geneOS: Yeast9 and iMM904 ethanol ceilings on glucose **2.000 mol mol⁻¹ (0.5114 g g⁻¹)** each. Five Postdoc questions asked three times each: the GEM-ceiling and SGD questions kept 5–6 claims with 0–1 dropped every run. Model spend for the day **$0.51**. `pnpm verify` 23 of 23. Pushed to `openferment-data`

- **Fix pass, 2026-10-16** — after the ten OF-BLD-014 fixes (unit minus sign, chemistry names, -fold, the saved JATS, Witness's models, per-question refusals, vectors on the data branch, nullable filters, step words, % CDW) and the one-model test change, all on Haiku 5.5. Before → after:
  - `pnpm verify`: 22 of 23 → **23 of 23**. `pnpm test:live`: 31 of 40 → **33 of 40** (fails: five flow citations, the tutor's reply carries a number, a check brief out of shape).
  - `pnpm intake:extract --all --force`, 66 papers: kept 216 → **337**, rejected 293 → **76**; unit rule 263 → **67**; $0.2482 → **$0.2354**. Thread P: 175 → 303 kept, pha_content_cdw 20 → **184**, titre 73 → 68, biomass 33 → 21, μ 19 → 10, yield 4 → 1: the % CDW enumeration pulls values into that field, and 104 of the 184 quote no wording that says cell mass (a pH of 7.0 among them). The 15 papers with % vs % CDW rejections, re-extracted alone: 70 → **0** such rejections.
  - `pnpm witness:numbers`: precision 57.1 → **70.0 %**, recall 17.4 → **15.2 %**, F1 26.7 → **25.0 %** (tp 7, fp 3, fn 39).
  - Flows citing a named record: 5 → **7** of 12 (F1, F2, F4, F5, F8, F9, F11).
  - `pnpm ask:batch` (ten PHA questions): kept 37 → **41**, dropped 20 → **15**; claims citing a record 6 → **11**; question 7 0 → 3 kept; `search_records` calls carrying literal quotes 13 of 24 → **0 of 21**; median $0.0041, 18.3 s; total $0.0407.
  - §8.6 bindings: titre 22 → **14** records (0.045–7.86 g L⁻¹), content 9 → **46** (0.003–0.811 g g⁻¹), productivity 0 → **2** (0.0095–0.0113 g L⁻¹ h⁻¹); bound 2 → **3** of 7 inputs.
  - `pnpm rag:eval`: NOT measured. With refusals per question the run outlasted the two-hour background limit and was stopped; no report was written, and `report.json` is still the 05:31 run (hybrid chosen). Its spend counts.
  - Day's ledger: $2.9167 over 1,368 calls, every one Haiku 5.5.

- **Model override, 2026-10-16** — by Sean's choice for this test pass, every model call uses `claude-haiku-5-5` at effort `medium` (`OPENFERMENT_MODEL`, `OPENFERMENT_FALLBACK_MODEL`, `OPENFERMENT_INDEX_MODEL` set on the environment; `llm.py` defaults untouched). Numbers below dated 2026-10-16 are Haiku's, not Opus's.
- §2.4, the extraction — 2026-10-16 — `pnpm intake:extract --all` on Haiku 5.5: **66** papers, **216** candidates anchored, **293** rejected (unit 263, quote 13, range 11, value 6), **$0.2482**. Thread P alone: **175** anchored over 35 papers — pha_titre 73, final_biomass_density 33, pha_content_cdw 20, growth_rate_mu 19, medium_component_conc 14, pha_productivity 9, pha_yield_substrate 4, pha_mw 2, titer_secreted 1; 157 carry an organism id (no candidate fills a strain field), 106 a carbon source. Of the unit rejections on thread P, 131 are units that do not normalise (25 of them `g L−1` with U+2212 as the minus, 11 `mg L−1`) and 70 are `%` given for a `% CDW` field. Pushed to `openferment-data`
- §8.6, the bindings — 2026-10-16 — `pnpm data:pull`, then `/api/proforma/scenarios`, `sc-pha-1` on Haiku-extracted records: titre bound **22** records, 0.045 to 16.0 g L⁻¹ (mode 0.69); content bound **9**, 0.0049 to 0.811 g g⁻¹; yield, productivity, recovery, sugar price and sugar feed wait for an assumption. Productivity binds none although 9 pha_productivity candidates exist; yield none of 4 pha_yield_substrate candidates
- §6.5, the shot — 2026-10-16 — `pnpm shots --prefix phase-6 /geneos/model`: the figure drew **0** reported yield records on glucose; it says 4 PHA yield records on another feed or none stated are not drawn. 0 USD
- §1.5, the rest, in part — 2026-10-16 — `pnpm intake:fetch --all`: 66 of 94, B1 and D1 500 again. `pnpm intake:extract --all` ran under §2.4 (casein papers: 41 anchored over 31 papers). `pnpm test:core`: 1117 passed, 4 failed, the same four that pass with the model variables unset: they expect a two-model chain and the override makes it one. `pnpm witness:numbers`: claude-1 provisional precision **57.1 %**, recall **17.4 %**, F1 **26.7 %** (tp 8, fp 6, fn 38; gold set 46 records on 14 papers). `pnpm demo:fixtures --real` FAILED: Europe PMC now sends the XML declaration and `<article>` on one line, `save_real` splits at the first newline and writes its comment after the article, and the saved JATS no longer parses; the fixture was restored
- §1.5, the saved paper — 2026-10-16 — after two fixes (the note's `--` broke the XML comment; the declaration was split at the first newline), `pnpm demo:fixtures --real` saved B5 (PMC8471596): 2 anchored, 3 rejected (value 2, unit 1), $0.0032 on Haiku; the demo sets rebuilt, `pnpm verify` green. The earlier line's cause was the comment, not the one-line header alone
- §4.5, in part — 2026-10-16 — `pnpm rag:questions --n 200`: **179** kept, 21 discarded (10 a number from the passage, 11 five words in a row), $0.0181. `pnpm index:build --dense` rebuilt the 5,043 vectors (they do not travel with `data:push`). `pnpm rag:eval`: K 94 questions (3 records, 216 candidates), S 179, F 3. bm25 K nDCG@10 **0.295** recall@10 **0.476**, S nDCG@10 **0.558** recall@10 **0.793**; hybrid K **0.267** / **0.435**, S **0.595** / **0.849**; F 0.000 for both. bm25+expand, bm25+rerank and hybrid+rerank: unscored, Haiku's helper call was declined by the safety classifier (bio), on two runs. Chosen lane: **hybrid**. Two eval runs $0.82 on the index role
- §5.5 — 2026-10-16 — `pnpm test:live` on Haiku: 31 of 40 passed. Flows: every one of 13 produced a usable plan; **5 of 12** gradable flows cite a record a person named (F2, F4, F5, F8, F9); in F1, F3, F6, F7, F10, F11 none of the named records was even retrieved, in F-SIALYL 5 were and none survived (6 claims dropped, glycan linkage names such as α2,6 read as numbers). Practice: both live tests failed, the situation text carried a number. `pnpm ask:batch docs/build/questions-pha.txt`: kept 37, dropped 20 across ten questions; median **$0.0041** and **19.5 s**; **30 of 37** kept claims carry a record or a passage (6 a record); question 7 declined, all five claims dropped for a `3` in 3HB/3HV; total $0.0432. 13 of 24 `search_records` calls passed the two characters `""` as a filter and got nothing back
- §10.3, in part — 2026-10-16 — the §5.5 batch above ran with all seven tools registered; Haiku called four of them (search_records, search_passages, yield_ceiling, selling_price) and never draft_runbook, growth_forecast or convert_units, question 10 included. Question 8: no Proforma run from Sean has arrived (only the benchmark artifact), and the plan names that gap. `pnpm demo:fixtures --real` failed as under §1.5

- §1.5, the fetch — 2026-10-14 — `pnpm intake:fetch --all`: **31 of the 59** asked returned full text (25 of the 27 with a PMCID, 6 found by DOI or PMID); 26 have no open-access text on Europe PMC; B1 and D1 answered 500 twice and are asked again on the next run. Licences: 26 CC BY 4.0, 1 CC BY stated in words, 1 Creative Commons licence named in words, 1 CC BY-NC 4.0, 1 CC BY-ND 4.0, 1 ACS AuthorChoice (CC BY-NC-ND terms). Of the 46 curated records on fetched papers, 3 quote a sentence the text holds. 0 USD; extraction owed
- §1.5, the fetch again — 2026-10-14 — `pnpm intake:fetch --all --force` after the parser fixes: 31 of the 59 again, B1 and D1 answered 500 again. Of the 46 curated records on fetched papers, still 3 quote a sentence the text holds (r-J10-1, r-O3-2, r-O3-4). 0 USD
- §2.4, the proposal — 2026-10-14 — `pnpm thread:propose` with the rule as OF-BLD-014 §2.3 writes it: Europe PMC counts 4,304 hits; of the first 100 by citations, 79 pass the filters and the rule proposes 16 (11 research articles, 5 reviews), because 77 of the 100 are reviews and only 11 research articles pass the filters. Every field the rule reads is present. Most proposals are off-topic: the query matches the words anywhere in the full text, and "PHA" also abbreviates phytohemagglutinin. The same query held to title and abstract (`TITLE_ABS:`) counts 120 hits, 95 of the first 100 pass the filters, and the rule fills its 30 and 5. 0 USD; pushed to `openferment-data`
- §1.5, B1 and D1 asked again — 2026-10-14 — `pnpm intake:fetch B1 D1`: both answered 500 again, in the session's fetch and once more on their own. Europe PMC's search says why: both are in Europe PMC (`inEPMC: Y`) but outside its open-access subset (`isOpenAccess: N`), and its `fullTextXML` endpoint answers 500 for such a paper where it answers 404 for one it lacks. They stay fetch failures; 31 of the 59 is the fetch. 0 USD
- §2.4, the proposal on Sean's query — 2026-10-14 — `QUERY` holds both term groups to title and abstract (`TITLE_ABS:(…) AND TITLE_ABS:(…)`), the filters unchanged; `pnpm thread:propose`: Europe PMC counts **120** hits; of the first 100 by citations **95** pass the filters; the rule proposes **35** (30 research articles, 5 reviews), **60** REVIEW (52 research articles, 7 reviews, 1 editorial), 0 INCLUDE. Every field the rule reads is present. A few proposals are still off the program (a cotton subtilase gene, a PHBV scaffold's hydrolysis, biodegradation in seawater), which is what the approval is for. 0 USD; pushed to `openferment-data`
- §2.4, approved, applied, fetched — 2026-10-14 — Sean Creighton approved the 35 proposed rows as listed. `pnpm thread:apply core/data/thread-p-proposed.tsv --approved-by "Sean Creighton"` wrote **P1–P35** into `threadP.ts` (167 papers in the seed); `pnpm verify` green. `pnpm intake:fetch --all`: **35 of 35** thread P papers returned full text (**66 of 94** overall; B1 and D1 500 as before). Thread P licences: 29 CC BY (25 at 4.0, 2 at 3.0, 2 at 2.0), 1 CC BY-NC 4.0, 2 CC BY-NC-ND, 3 an open-access licence stated in words. `pnpm intake:extract --all`: **0** papers extracted, every call answered 400 (the key is not scoped to a workspace). 0 USD; the extraction is owed
- §4.5, the free part — 2026-10-15 — `pnpm data:prepare`: **66** papers indexed, **5,036** passages (4,198 prose, 365 figure, 361 table, 112 abstract). `pnpm index:build --dense`: Hugging Face answered; **5,036** vectors, 384 dimensions, `BAAI/bge-small-en-v1.5`, 8 m 29 s. `pnpm rag:eval`: K **2** questions from **3** records whose quote sits in the text (no candidates yet); F **3** of the 12 gradable flows; S none (owed). bm25 K nDCG@10 **0.644**, recall@10 **1.000**; hybrid K nDCG@10 **0.500**, recall@10 **0.500**; both F nDCG@10 **0.000**, recall@10 **0.000**. The three paid lanes: the API refused the key. Chosen lane: **bm25**. 0 USD; pushed to `openferment-data`. Two questions decide nothing yet; the choice waits for S and the candidates
- §4.5, the free part again, after §4.R — 2026-10-15 — the chunker cuts a long abstract as prose and K names a strain by its id, so: `pnpm index:build --dense`: **66** papers, **5,043** passages, **5,043** vectors. `pnpm rag:eval`: K **2** questions (3 records), F **3** of 12 flows, S none. bm25 K nDCG@10 **0.395**, recall@10 **1.000**; hybrid K nDCG@10 **0.167**, recall@10 **0.500**; F **0.000** for both. Chosen lane: **bm25**. 0 USD; pushed to `openferment-data`. These replace the numbers on the line above
- §4.2, licences — 2026-10-15 — Sean Creighton accepted, in this session, `tqdm` (MPL-2.0 AND MIT) and `py_rust_stemmers` (no licence metadata; its repository's LICENSE is MIT, read 2026-10-15) for the `rag` extra; both are under `[accepted]` in `core/licences.toml` with his name and the date
- §6.5 — 2026-10-15 — `pnpm geneos:fetch`: RehMBEL1391 at `00c70c5`, sha256 matches the pin. `cd core && uv run --all-extras pytest tests/test_geneos_live.py -m live`: 5 passed. Appendix 2 reproduced within 0.1 %: case 1 `e_coli_core` glucose **10.0000** (0.4779 g/g), case 2 `iJO1366` glucose **12.4122** (0.5931), case 3 `iJO1366` xylose **10.2383** (0.5871), case 4 the mix midpoint **12.3600** (0.5906), case 5 `RehMBEL1391` fructose **12.4138** (0.5932), case 6 CO2 and H2 **4.6250**; the frontiers end at 0.8739, 0.9824 and 0.9304. The file publishes 1,538 reactions, 1,348 metabolites, 1,350 genes, and carries **no** `DM_phb_c` (Appendix 2 said it did; corrected): the worker adds it. Reported yield records the figure drew: **0**, as no `pha_yield_substrate` record exists until thread P is extracted. 0 USD

---

- **2026-09-15 · OF-BLD-012.1 §6.1 (F1.1–F1.3)** — `export-corpus.ts` emits
  `range` and `negativeResult` as data instead of folding them into the
  `conditions` prose; §2.4 rule 3 reads the quote as quantities (units the
  paper wrote, the range it states, numbers written in words) instead of bare
  numbers, and records how it found the value as `valueBasis`; `biorepo.write`
  passes the record's recorded structure into anchoring. **30 of the 34**
  refused gold records now anchor, not the 32 the spec predicted: `r-A2-1` and
  `r-O8-1` refuse on rule 5, the field's own range, which no rule-3 fix
  reaches. `pnpm verify` green, all sixteen stages.
- **2026-09-15 · OF-BLD-012.1 §6.2 (F1.4–F1.5)** — `emit_candidates` gains
  `range` and `negativeResult` and the prompt says what each is for, so the
  extractor can say what the curators recorded; `match_run` scores a range
  candidate against a range record on its endpoints. `biorepo.write` grows a
  `dry_run`, `POST /api/biorepo/check` asks it, and Guild gates Accept and
  Gold on that answer with `writeRefusal` demoted to the offline fallback —
  the rules are not mirrored. New verify stage `check:anchors` holds the
  anchoring floor at **93 of 104**; seventeen stages now. Both new guards
  negative-tested. `pnpm verify` green.
- **2026-09-16 · OF-BLD-012.1 §6.3 (F2)** — decisions are signed by a person.
  Settings gains a Reviewer name field, kept in the Durable tier under
  `reviewerName`; `reviewerName()` in the store is the one place it is read and
  replaces all **12** hard-coded `'you'` sites (the spec said 10); an audit line
  made before a name is set says `this browser`, which can never be posted.
  `writeRefusal` gains a blocking `reviewer` rule while the service is up, and
  `biorepo.write` refuses a name under two characters or in the closed
  placeholder list (`you`, `me`, `reviewer`, `user`, `test`). The smoke now
  reviews as a named person and checks the posted decision carries that name;
  the durable check reloads the page and finds the name still there. Both new
  assertions negative-tested. `pnpm verify` green.
- **2026-09-16 · OF-BLD-012.1 §6.4 (F3)** — the overlay is authoritative.
  `Overlay.candidates` and `runs` are a list or `null` in both languages; a
  list replaces whatever its length, and only `null` keeps what was there. An
  undecided `haiku-1` record absent from an incoming list is removed from the
  store and the review queue; a decided one stays and carries `absentFromRun`,
  which the review card explains. New verify stage `check:overlay` drives the
  real store through five scenarios; eighteen stages now. Negative-tested.
  Correction to the spec: the eight store scenarios it says live in `scripts/`
  were scratchpad probes — this stage is the first one in the tree.
  `pnpm verify` green.
- **2026-09-16 · OF-BLD-012.1 §6.5 (F6–F7)** — `match_run` pairs by distance:
  every agreeing (record, candidate) pair is scored, sorted, and consumed
  greedily, ties breaking on record then candidate order, so the result no
  longer depends on arrival order and a record cannot take the candidate its
  sibling was closer to. The dropped-span pass is paired the same way and the
  docstring states the algorithm. `ExtractionRecord.original` is stamped once
  as a record enters the store and never touched by a decision;
  `reanchoredSpan` and the withdrawal of a correction read it instead of
  diffing against `RECORDS`, which a corpus update would move underneath a
  decided record. The overlay guard grew the F7 scenarios and is renamed
  `pnpm check:store`. Both fixes negative-tested. `pnpm verify` green.
- **2026-09-17 · OF-BLD-012.1 §6.6 (F8)** — a truncated paper is split, never
  discarded. `MAX_TOKENS` is 16 000 and no longer derived from Postdoc's; a
  response that hits the limit halves the paper by character count and asks
  again, twice deep, and only the remainder that still will not fit is
  reported. `ExtractResponse` gains `calls` and `truncatedSections` (the spec
  said `ExtractRun`; that model is Witness's per-run aggregate, and these are
  per-extraction facts that belong beside `usage`). Every call is paid for in
  `usage`. A paper that truncates all the way down is still refused and still
  cached as nothing. Negative-tested. `pnpm verify` green.
- **2026-09-17 · OF-BLD-012.1 §6.7 (F4–F5)** — the merge is tested and the
  guard brings its own export. `export-corpus.ts` takes
  `OPENFERMENT_CORPUS_OUT`; `check:biorepo` takes `OPENFERMENT_DATA_DIR` and
  exports into a temp directory itself, so it passes on a fresh clone with no
  `corpus.json`. New stage `pnpm test:export` exports the demo's decisions and
  checks the corrected value, the SI twin, the re-anchored quote, the appended
  record, gold provenance and the excluded rejection. The demo fixture now
  carries one of each kind of decision. **Tension resolved:** F4 asks the
  guard to fail on a bent value, but after F5 the guard builds the corpus it
  checks, so bending the decision bends both sides — rule 4 is testable
  through `OPENFERMENT_CORPUS_IN`, which nothing in verify sets. Nineteen
  stages. Both negative-tested. `pnpm verify` green.
- **2026-09-19 · OF-BLD-012.1 §6.8 (F9)** — identifiers proposed by machine,
  approved by a person. `pnpm ids:propose` asks Crossref about each of the
  **73** seed papers carrying no PMCID, DOI or PMID and writes a gitignored
  TSV; `pnpm ids:apply` writes back the rows a person changed to `APPROVED`
  and only those — under the entry's `venue:` line, never onto a paper that
  already has one, one line and nothing else — then prints the diff to commit,
  and raises rather than guess at an id the seed does not hold. Crossref lives
  in one function, so the matching, the verdict and the patcher are pinned
  offline: **19** tests in verify, plus one `live` test that is the only place
  an unreachable Crossref shows up as a refusal instead of 73 silent REVIEW
  rows. Guild gains the **Papers the service can keep** filter over the **52**
  unverified records `biorepo.write` refuses for want of an identifier.
  **Two findings.** The filter as first written was decoration: Guild seeded
  its queue at mount, before `/api/health` had answered, so the box read
  "hiding 52" above a queue still holding all 135 — the smoke's old `/ 135`
  assertion passing is what proved it. The queue waits for the answer now,
  which cost the smoke its cold-open race for §7.3's "an arriving candidate
  joins an open queue"; that contract moved into `check:store`, where it needs
  no clock. And **Crossref is unreachable from this environment** — the agent
  proxy answers 403 to CONNECT for `api.crossref.org` — so `ids:propose` is
  Sean's to run; from here every lookup degrades to a REVIEW row, as designed.
  Four guards negative-tested. `pnpm verify` green, nineteen stages.
- **2026-09-21 · OF-BLD-012.1 §6.9 (review pass, truth pass, PR)** — the
  thirty commits since `main` were read adversarially before the PR, with the
  store and the service driven by probes. **Fifteen findings, all confirmed,
  all fixed, each with a test that failed first** (`a264368`). The ones that
  mattered: a live fetch applied its result with `candidates: []`, which under
  F3 wiped the extractor's candidates on every fetch; a reviewer-typed
  correction with no quote skipped rule 3 and reached `corpus.json` inside no
  sentence; an undo was stored as a decision and counted by Witness; rule 3
  read "one of the highest titres" as a titre of 1 and matched negation
  markers as substrings; a numeric superscript on any digit was a power of
  ten; `applyOverlay` moved the reviewer to a different card when the queue
  was pruned; the deep-link effect re-fired on every queue change and, opened
  early, defeated F9's filter. `check:anchors` still **93 of 104**; **318**
  Python tests. Truth pass over README: three stages missing from the gate
  (`test:export`, `check:anchors`, `check:store`), **15** strains not 7, the
  F9 commands and the reviewer name in "Running it", dates re-measured (still
  0 fetched, 0 extracted, 0 verified in this checkout). `CLAUDE.md` already
  carried F1's `valueBasis` list and the `/check` rule from §6.1–6.2; it
  gains the typed-value and withdrawal rules. `pnpm verify` green, nineteen
  stages. PR opened to `main`.
- **2026-09-22 · OF-BLD-012.1 §6.9 (security pass)** — the branch read once
  more, for what an attacker rather than a reviewer would find. **One
  vulnerability, confirmed and closed:** every script that serves `dist/` —
  the smoke, the five browser checks and `pnpm demo:offline` — resolved the
  request path with `join(DIST, url)`, which collapses `..`, so
  `/../core/.env` read the key off the disk of whoever was running the demo,
  and the demo listened on every interface while it did. The seven copies are
  one confined handler now, `scripts/lib/serve-dist.mjs`; a request that
  leaves `dist/` is a 404, every server binds to loopback, and the demo takes
  `OPENFERMENT_DEMO_HOST` to be shown to another machine on purpose. The
  smoke sends four traversal shapes raw and expects four 404s; with the
  confinement removed it says so. **Two hardening fixes, below the bar as
  vulnerabilities and taken anyway:** a DOI is written into a TypeScript
  string literal the gate then executes, so `ids:apply` refuses — never
  repairs — any value that is not `10.NNNN/suffix` free of quotes and
  whitespace, and `ids:propose` marks such a hit REVIEW; and a candidate id's
  paper segment is `[A-Za-z0-9_]+`, so `_resolve` cannot be asked to open
  `candidates/../../x.json`. Examined and clean: the API's `paper_id` is
  checked against the corpus before it reaches a path; JATS parsing resolves
  no external entities; no `dangerouslySetInnerHTML`; the workflow uses
  `pull_request`, not `pull_request_target`. `pnpm verify` green, nineteen
  stages.
- **2026-10-09 · OF-BLD-013 Phase 1 (§1.1–§1.4)** — Guild's competence
  ledger as a training matrix. **14** placeholder skills in six families,
  tagged on **36** steps of PR-CIP-01, PR-OD-01 and PR-SEED-01; `check:seed`
  holds ids, prerequisites (acyclic) and tags. People, entries and
  withdrawals in both languages (five new `PAIRS`), written only by
  `guild.write_person`, `write_evidence` and `withdraw` under one lock, with
  `POST /api/guild/check` as the dry run and `offlineRefusal` as the labelled
  fallback; `core/data/guild.json` is gitignored. Levels are computed by
  `competenceOf` and never stored. Guild gains Matrix, People and Skills
  beside Review, a sign-off sheet, ledger export and an invented, labelled
  sample team that is never posted or kept. New stage `check:guild`; twenty
  stages now. Every rule negative-tested. `pnpm verify` green at each commit.
- **2026-10-09 · OF-BLD-013 Phase 2 (§2.1–§2.2)** — the bench link, advise
  mode. `competence.py` mirrors the ladder for the service's one use of a
  level (does a cosigner, or a lone operator, hold the skill), held to
  `competence.ts` by a generated fixture, now **602** statuses over five
  ledgers. Deposition names its operator, hands over, asks for a cosigner
  when the operator is Supervised, lapsed or suspended, and names who could
  take over when they are below it; completing a step writes a run alone, a
  cosigned run or a deviation, once per step. Home gains a Workforce card.
  `pnpm verify` green.
- **2026-10-09 · OF-BLD-013 Phase 3 (§3.1–§3.3)** — path and knowledge.
  A lesson may name skills; passing its checkpoint writes knowledge with no
  observer for whoever is learning, which makes **Learning and no more**:
  Supervised still needs an assessor's training sign-off (the plan's
  "knowledge evidence complete", read as the sign-off, because a checkpoint
  can be answered by anyone holding the tablet). A placeholder bench track of
  **3** lessons teaches from the protocols through a live `skill-steps`
  embed, and `check:seed` holds such a lesson to Rule 1: no quantity of its
  own. Lesson progress is Durable. My path (`/primer/path`, rules in
  `pathOf`) shows one person the next step on each skill. Smoke **55**
  routes; `check:guild` **93** checks. `pnpm verify` green.
- **2026-10-09 · OF-BLD-013 §3.4 (review)** — an independent read found no
  blocking defect; what it did find is fixed and held by `check:guild`
  part 7 or `test_guild`: a refused run is kept as a deviation; the service
  judges a run on its own day; an auditor signs nothing; sync skips what is
  stored and keeps what it did not send; the sample stays out of
  depositions; pending entries sort last in both engines; the sample's
  sign-offs follow their assessor's designation, and the whole sample now
  replays through the service's rules. **559** Python tests. Known and left:
  entries made offline before an offline deactivation are refused at sync,
  and a real run continued while the sample is shown records nothing.
  `pnpm verify` green.
- **2026-10-09 · OF-BLD-013 Phase 4 (§4.1–§4.4)** — Practice. `practice.py`
  drafts a scenario for a skill through `llm.py` from the steps that need it,
  their materials (now projected into `skills.json`) and the confirmed
  records of the newest bench runs that recorded something at those steps;
  the model writes words and cites sources, and every value in the evidence
  pane is copied from the source it cites. A draft or a tutor reply with a
  number of its own, an unresolved source or marker, or no step needing the
  skill is refused whole, and the refusal never quotes it. The tutor asks
  why, changes one condition or asks what next, closes on the third answer
  with what it observed, and a closed session becomes one `scenario` entry on
  the learner's ledger, dated its close: Learning and no more. Primer gains
  Practice, phone-first, with the transcript an assessor reaches from the
  ledger. Thirteen new shapes in both languages. An independent review's
  findings are fixed in §4.4. **593** Python tests offline; the real model is
  `pnpm test:live`, which no key here could run. Smoke **56** routes.
  `pnpm verify` green.
- **2026-10-09 · OF-BLD-013 Phase 5 (§5.1–§5.5)** — Checks. The lead sets
  each gate to advise or enforce (Settings → Guild; critical skills enforce
  by default), and in enforce mode a Supervised, lapsed or suspended
  operator's step waits for a cosigner who holds the skill; skipping a held
  step writes a deviation. Every night `checks.py` ranks each person and
  skill by fixed rules (suspended, lapsed, lapsing, ready, a recent
  deviation, low confidence, the lead's quarterly rate), mirrored from
  `src/engine/checks.ts` and held to it by the fixture, and proposes the top
  checks with their reasons written out; a brief beside each is one model
  call with no number in it and no name. Guild gains Checks for the lead and
  assessors: schedule, dismiss with a reason, or run at the bench, a
  full-screen takeover under Deposition's constraints that calls one
  criterion at a time and signs in the assessor's name, writing one
  witnessed entry per skill in one ledger write. A check never shows to the
  person it names until it has been run; My path lets a person ask for one.
  An independent review's fourteen findings are fixed in §5.5. **623**
  Python tests offline; `check:guild` **160** checks; smoke **58** routes.
  Known and left: the plan's practice–bench disagreement signal and an
  assessor's flag as a cause of suspension are not built; a brief has
  never been drafted by the real model here, as no key could run
  `pnpm test:live`. `pnpm verify` green.
- **2026-10-14 · OF-BLD-014 Phase 1 (§1.1–§1.5, §1.R, §1.T)** — the base, and
  the first real run, owed. The work branch starts from `guild-primer-phase1`
  at `90cb31d`, whose verify measured green in **439 s**, twenty stages, **623**
  Python tests. The build document lives in `docs/build/` (D1). A licence
  ledger: `pnpm check:licences` reads **36** Python and **54** JavaScript
  packages against **12** allowed strings and one acceptance (certifi,
  MPL-2.0, Sean Creighton), and keeps `THIRD_PARTY.md` current; verify is
  twenty-one stages. `pnpm session:start` starts every session the same way
  (**8.7 s** warm), `pnpm ready` ends with the lane, and live-run data
  travels on `openferment-data` (`pnpm data:push`, `data:pull`), whose
  refusal of an unlisted path is tested through real git. `pnpm prototype:up`
  answers in **24 s** warm; `pnpm shots` photographs a running app. Demo
  decisions follow the saved response, `pnpm test:export` exports its own
  stand-in set, and `pnpm witness:numbers` prints what Witness shows, checked
  against the screen. §1.5's run is owed: lane **none** here (no key; Europe
  PMC and huggingface.co answer ProxyError). An independent review found
  ten defects, none high: nine are fixed in §1.R, each with a test watched
  to fail first, and this pass corrects the stage counts. **680** Python
  tests offline; smoke **58** routes, golden path **26**, deep paths **7**.
  `pnpm verify` green in **437 s**, twenty-one stages.
- **2026-10-14 · OF-BLD-014 Phase 2 (§2.1–§2.4, §2.R, §2.T)** — PHA enters as
  program two, with its papers owed. Ontology **29** fields in six families
  (the polymer five, D9's ranges), `growth_rate_mu` to 2.5 h⁻¹, a carbon source
  and a strain id on extracted values; `check:anchors` holds **93 of 104**.
  Two hosts (**17** strains), PHB and mcl-PHA (**119** molecules, 12
  categories, 11 process families: a biopolymer opens its own, P12), the
  `phb-route` pathway, thread letter P in the three places it is written, and
  Home's Programs strip. `pnpm thread:propose` / `thread:apply` with the rule
  in `threadp.py`; apply writes approved rows only, under a name `biorepo.write`
  accepts, and refuses a file holding what it never writes. The first live
  proposal ran: the rule as written proposes **16**, mostly off-topic (the
  query matches the full text, and "PHA" also names phytohemagglutinin);
  held to title and abstract it proposes the full 30 and 5. §2.4 is owed:
  Sean's choice of query, his approval, then the key. The review found nine;
  seven fixed (five with a failing test first, two copy corrections), two
  left as notes (process codes
  P1–P12 read as paper ids in scripted chat; `wt%` aliases to `% CDW`
  everywhere, as §2.1 asked). **812** Python tests offline; smoke **59**
  routes, golden path **26**, deep paths **7**. `pnpm verify` green in
  **467 s**, twenty-one stages (467 s again for this pass). Screenshots: `docs/shots/phase-1-*` and
  `phase-2-*`.
- **2026-10-15 · OF-BLD-014 Phase 3 (§3.1–§3.4, §3.R, §3.T)** — contracts for
  computed values. `computed` joins the provenance ranking after `curated`,
  and the two rankings are one order (`check:plan` now compares order, and
  `user` moved below `unverified` in Python); a computed value carries a
  `ComputedBasis` and `basis_provenance` decides its class. BioRepo keeps
  what was computed (`artifacts.py`, three endpoints, replay) and shows it on
  a new **Artifacts** tab, the first `live` subsystem. `llm.py` gains roles
  (Haiku 5.5 for index work), cached-token costs (prices confirmed on the
  page on 2026-10-15), `converse()` for tool turns, and a daily cap that
  reserves each call's worst case in `spend.json`. One tool registry, closed
  at seven names, refuses a number typed into a tool input; `search_records`
  reads an evidence pool that includes unrejected candidates as
  `unverified`, and `convert_units` stores its result as an artifact.
  `SimWorker` runs a simulator in its own process. The review found **7**
  defects, one high (a record rejected since the last export stayed
  citable); all 7 fixed with a failing test first. **911** Python tests
  offline; smoke **61** routes. One real artifact made for the screenshots
  (r-B5-3, 17.5 d = 420 h, `computed`). The key on the cloud environment
  still reaches no model: the API answers 400 because it is not scoped to a
  workspace, so §1.5's and §2.4's extractions stay owed. Screenshots:
  `docs/shots/phase-3-*`.
- **2026-10-15 · OF-BLD-014 Phase 4 (§4.1–§4.5, §4.R, §4.T)** — passages:
  the papers' own words, indexed and measured. `passages.py` cuts the **66**
  fetched papers into **5,043** passages (sentence-bounded prose with one
  sentence of overlap, whole table rows under their heading and first row,
  captions, abstracts), and `pnpm index:build` cuts only what changed. Five
  lanes (`bm25`, `bm25+expand`, `hybrid`, `bm25+rerank`, `hybrid+rerank`)
  fused by reciprocal rank; the grading reader's sentence is held to its
  passage word for word. `fastembed` 0.9.0 joins as the `rag` extra, with two
  licences Sean accepted. `rageval.py` scores every lane on K, S and F and a
  fixed rule picks the default: **bm25** (K nDCG@10 **0.395**, recall@10
  **1.000**; hybrid 0.167 and 0.500; F 0.000) on 2 K questions and 3 flows,
  so provisional. BioRepo gains **Search**; the reader lands on a sentence
  (`?quote=`); Witness gains **Retrieval**. The service double is shared by
  the smoke and the golden path. Owed: S and the three paid lanes, which need
  a key the API accepts. The review found ten, none high; nine fixed with a
  failing test first, one left (the golden step walks the seed). **965**
  Python tests offline; smoke **62** routes, golden path **27**. Screenshots:
  `docs/shots/phase-4-*`.
- **2026-10-15 · OF-BLD-014 Phase 5 (§5.1–§5.5, §5.R, §5.T)** — Postdoc
  as an agent. `postdoc_agent.py` runs a bounded loop of tools on Claude Opus
  5.5 (6 rounds, 12 tool calls, `OPENFERMENT_ASK_BUDGET_USD`, 180 seconds;
  one last turn with `tool_choice` `none`; a refusal or outage restarts once
  on Sonnet 5.5). `search_passages` is the third tool. `validate_plan` holds
  every claim to five rules: no number, a record the pool holds, nothing no
  tool returned, every quote whole sentences or rows of its passage, and a
  citation or `unsupported`. `/api/ask` runs the loop by default (`mode:
  'single'` keeps one call); `/api/ask/stream` sends each step as it
  completes, and the live panel draws them, with each claim's record values,
  quoted sentences that open the reader, computed cards and a footer that
  says why the loop stopped. `pnpm ask:batch` and Appendix 4's ten questions
  are in `docs/build/questions-pha.txt`. Every run is owed: the key is not
  scoped to a workspace (`pnpm ready`: lane none). The review found nine,
  none high, all fixed with a failing test first (two screen ones by
  reading). **1,016** Python tests offline; smoke **62** routes, golden path
  **29**. Screenshot: `docs/shots/phase-5-postdoc-live.png`, the live panel
  over the service double's recorded stand-in loop.
- **2026-10-15 · OF-BLD-014 Phase 6 (§6.1–§6.5, §6.R, §6.T)** — one figure
  grammar and geneOS's first computation. `src/components/figures/` draws
  every new chart from one table of marks (`ENCODING`, held to E.8 by
  `pnpm check:figures`, the 22nd verify stage), each figure with a table
  twin; Settings → Figure grammar shows them over a labelled sample. The
  `sim` extra brings cobra 0.32.1 into one worker process, with three
  copyleft libraries accepted under D4 and the model files listed by hash.
  geneOS computes the most PHB a published network allows from a sugar, its
  production envelope and a sugar-mix line, each kept as an artifact, and
  draws them in geneOS → Model beside the reported yields measured on that
  sugar; `yield_ceiling` is Postdoc's fourth tool. Appendix 2 reproduces
  within 0.1 % (0.4779 g/g central carbon and 0.5931 g/g genome scale on
  glucose; 0.5932 g/g for C. necator on fructose; the iJO1366 mix runs
  0.5931 to 0.5881). Appendix 2 said the C. necator file carries
  `DM_phb_c`; it carries none, and the worker adds it. The figure draws
  **0** reported yields: thread P's extraction is owed. The review found
  eleven, one high (the toy network reachable as `computed`), all fixed or
  guarded with a failing test or check first. **1,045** Python tests
  offline; smoke **64** routes, golden path **30**. Screenshots:
  `docs/shots/phase-6-*`, from the running service with the real models.
- **2026-10-15 · OF-BLD-014 Phase 7 (§7.1–§7.4, §7.R, §7.T)** — fermOS fits
  what a run measured. A deposition's readings carry hours and a series role,
  typed on the deposition page or attached as CSV, and survive a reload.
  `fermos.py` fits a growth rate and a closed-form kinetic model (logistic,
  Luedeking–Piret, substrate balance) and forecasts a run like it as a band
  of 200 seeded draws; fits and forecasts are artifacts with the deposition
  as source, and the sample run is invented, inline and kept nowhere.
  Measured on synthetic runs: noiseless parameters back within 0.1 %; a
  fresh reading inside the band in 35, 34 and 33 of 40 runs (biomass,
  product, substrate; the spec's floor is 28); a run cut before biomass
  levels off gives an Xmax interval more than twice as wide (median of nine).
  No real run is fitted yet: none is deposited with timed readings. fermOS
  is no longer the emptiest of the eleven; transport, mode, scale and
  control stay unbuilt. `growth_forecast` is the fifth tool. The review
  found six, two high (CSV rows placed by unit alone; the service taking
  the browser's word for a deposition); five fixed with a failing test
  first, the sixth stated in the basis and the screen. **1,070** Python
  tests offline; smoke **65** routes, golden path **31**. Screenshots:
  `docs/shots/phase-7-*`, over the sample run.
- §8.6, the benchmark — 2026-10-15 — `pnpm test:slow`: **7 passed**. `biorefineries.cornstover@2.35.1` on biosteam 2.54.0 with the package's defaults: minimum ethanol selling price **1.9677** USD per gallon (B.3: 1.968; within 0.02 %), kept as artifact `35e708d122a6b4fc` and pushed to `openferment-data`. Bindings over the pool as it stands: **134** records, all seed, **0** thread P records, so each of the seven inputs of `sc-pha-1` binds **0** records and all seven wait for a source; the yield cap reads **0.593** g g-1 from a stored geneOS ceiling. The binding half is owed with §2.4's extraction. 0 USD

## OF-BLD-016 (branch claude/of-bld-016-demo, from 7e3ebb0)

- **§1.1 — 2026-10-20 05:57 UTC** — branch cut from `main` at `7e3ebb0` (the merge of PR #10; its tree equals `b5819d5`). `scripts/session-start.sh` ran; `pnpm ready` ends **lane: full**, answer and index roles both `claude-haiku-5-5`, effort medium, from the environment; $0.51 of the day's $25.00 cap spent before tonight. `pnpm data:pull`: **150** files. Measured here: **88** of 116 papers fetched with full text (B1 and D1 answered 500 from Europe PMC and stay owed to intake), **88** candidate files holding **500** extracted values, index **88** papers and **7,179** passages with current vectors (`lane hybrid`), **25** artifacts, **4** entries under `core/data/live/`, no proposals file yet (Phase 7 brings it). geneOS shelf: RehMBEL1391, iMM904 and Yeast9 present with matching hashes. `pnpm verify` **23 of 23** green in about **9 min 15 s**: **1,418** Python tests passed (1 skipped), smoke **67/67** routes, golden path **35/35**. Part B checked: the trial merge of `claude/of-bld-015-postdoc` at `7298143` conflicts in `postdoc_agent.py` and `ask-draft-stream.jsonl` alone, as B says; the branch's registry holds **29** tools, seven strict.
