# STATE

One line per session, newest last — what landed, and the measured number that
says it landed. The full §0.5 report for each session is in that session's
transcript; this file is the index a later session reads first.

## Live owed

LIVE steps built offline whose run waits on a need this machine lacked, one line each: `- §n.m — needs <what> — <the command to run>` (OF-BLD-014 A.4).

- §1.5, the rest — needs a key the Models API accepts (since 2026-10-14 the key reaches the session, but api.anthropic.com answers 400: the key is not scoped to a workspace, and a request with it must name one in `anthropic-workspace-id`; Europe PMC answers; the parser defects in `docs/build/JATS-AUDIT.md` are fixed and re-audited) — `pnpm intake:fetch --all && pnpm intake:extract --all && pnpm demo:fixtures --real && pnpm test:core`, then `pnpm witness:numbers` with the service up, then `pnpm data:push`. B1 and D1 are not asked again: they are fetch failures (see Live runs)

- §2.4, the extraction — needs a key the Models API accepts (this one is not scoped to a workspace: 400 on every call) — `pnpm intake:extract --all && pnpm data:push`; report per thread P paper and per polymer field: anchored, rejected by rule, cost, values with a strain id, values with a carbon source
- §4.5, the rest — needs a key the Models API accepts (the API answers 400 to this one: not scoped to a workspace) — `pnpm rag:questions --n 200 && pnpm rag:eval && pnpm data:push`; report the questions discarded, and nDCG@10 and recall@10 on K and S for every lane, with the cost
- §5.5 — needs a key the Models API accepts (`pnpm ready` on 2026-10-15: 400, not scoped to a workspace) and the index (`pnpm data:prepare`) — `pnpm test:live` (on a `model-only` lane: `cd core && uv run --all-extras pytest tests/test_flows.py -m live -s`), then `pnpm ask:batch docs/build/questions-pha.txt && pnpm data:push`; report flows passed of twelve, and across the ten questions the median cost and seconds, claims kept and dropped, and the share of kept claims that carry a record or a quote

## Live runs

LIVE steps that ran, one line each: `- §n.m — <date> — <the numbers the step asks for>` (OF-BLD-014 A.4).

- §1.5, the fetch — 2026-10-14 — `pnpm intake:fetch --all`: **31 of the 59** asked returned full text (25 of the 27 with a PMCID, 6 found by DOI or PMID); 26 have no open-access text on Europe PMC; B1 and D1 answered 500 twice and are asked again on the next run. Licences: 26 CC BY 4.0, 1 CC BY stated in words, 1 Creative Commons licence named in words, 1 CC BY-NC 4.0, 1 CC BY-ND 4.0, 1 ACS AuthorChoice (CC BY-NC-ND terms). Of the 46 curated records on fetched papers, 3 quote a sentence the text holds. 0 USD; extraction owed
- §1.5, the fetch again — 2026-10-14 — `pnpm intake:fetch --all --force` after the parser fixes: 31 of the 59 again, B1 and D1 answered 500 again. Of the 46 curated records on fetched papers, still 3 quote a sentence the text holds (r-J10-1, r-O3-2, r-O3-4). 0 USD
- §2.4, the proposal — 2026-10-14 — `pnpm thread:propose` with the rule as OF-BLD-014 §2.3 writes it: Europe PMC counts 4,304 hits; of the first 100 by citations, 79 pass the filters and the rule proposes 16 (11 research articles, 5 reviews), because 77 of the 100 are reviews and only 11 research articles pass the filters. Every field the rule reads is present. Most proposals are off-topic: the query matches the words anywhere in the full text, and "PHA" also abbreviates phytohemagglutinin. The same query held to title and abstract (`TITLE_ABS:`) counts 120 hits, 95 of the first 100 pass the filters, and the rule fills its 30 and 5. 0 USD; pushed to `openferment-data`
- §1.5, B1 and D1 asked again — 2026-10-14 — `pnpm intake:fetch B1 D1`: both answered 500 again, in the session's fetch and once more on their own. Europe PMC's search says why: both are in Europe PMC (`inEPMC: Y`) but outside its open-access subset (`isOpenAccess: N`), and its `fullTextXML` endpoint answers 500 for such a paper where it answers 404 for one it lacks. They stay fetch failures; 31 of the 59 is the fetch. 0 USD
- §2.4, the proposal on Sean's query — 2026-10-14 — `QUERY` holds both term groups to title and abstract (`TITLE_ABS:(…) AND TITLE_ABS:(…)`), the filters unchanged; `pnpm thread:propose`: Europe PMC counts **120** hits; of the first 100 by citations **95** pass the filters; the rule proposes **35** (30 research articles, 5 reviews), **60** REVIEW (52 research articles, 7 reviews, 1 editorial), 0 INCLUDE. Every field the rule reads is present. A few proposals are still off the program (a cotton subtilase gene, a PHBV scaffold's hydrolysis, biodegradation in seawater), which is what the approval is for. 0 USD; pushed to `openferment-data`
- §2.4, approved, applied, fetched — 2026-10-14 — Sean Creighton approved the 35 proposed rows as listed. `pnpm thread:apply core/data/thread-p-proposed.tsv --approved-by "Sean Creighton"` wrote **P1–P35** into `threadP.ts` (167 papers in the seed); `pnpm verify` green. `pnpm intake:fetch --all`: **35 of 35** thread P papers returned full text (**66 of 94** overall; B1 and D1 500 as before). Thread P licences: 29 CC BY (25 at 4.0, 2 at 3.0, 2 at 2.0), 1 CC BY-NC 4.0, 2 CC BY-NC-ND, 3 an open-access licence stated in words. `pnpm intake:extract --all`: **0** papers extracted, every call answered 400 (the key is not scoped to a workspace). 0 USD; the extraction is owed
- §4.5, the free part — 2026-10-15 — `pnpm data:prepare`: **66** papers indexed, **5,036** passages (4,198 prose, 365 figure, 361 table, 112 abstract). `pnpm index:build --dense`: Hugging Face answered; **5,036** vectors, 384 dimensions, `BAAI/bge-small-en-v1.5`, 8 m 29 s. `pnpm rag:eval`: K **2** questions from **3** records whose quote sits in the text (no candidates yet); F **3** of the 12 gradable flows; S none (owed). bm25 K nDCG@10 **0.644**, recall@10 **1.000**; hybrid K nDCG@10 **0.500**, recall@10 **0.500**; both F nDCG@10 **0.000**, recall@10 **0.000**. The three paid lanes: the API refused the key. Chosen lane: **bm25**. 0 USD; pushed to `openferment-data`. Two questions decide nothing yet; the choice waits for S and the candidates
- §4.5, the free part again, after §4.R — 2026-10-15 — the chunker cuts a long abstract as prose and K names a strain by its id, so: `pnpm index:build --dense`: **66** papers, **5,043** passages, **5,043** vectors. `pnpm rag:eval`: K **2** questions (3 records), F **3** of 12 flows, S none. bm25 K nDCG@10 **0.395**, recall@10 **1.000**; hybrid K nDCG@10 **0.167**, recall@10 **0.500**; F **0.000** for both. Chosen lane: **bm25**. 0 USD; pushed to `openferment-data`. These replace the numbers on the line above
- §4.2, licences — 2026-10-15 — Sean Creighton accepted, in this session, `tqdm` (MPL-2.0 AND MIT) and `py_rust_stemmers` (no licence metadata; its repository's LICENSE is MIT, read 2026-10-15) for the `rag` extra; both are under `[accepted]` in `core/licences.toml` with his name and the date

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

