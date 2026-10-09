# STATE

One line per session, newest last — what landed, and the measured number that
says it landed. The full §0.5 report for each session is in that session's
transcript; this file is the index a later session reads first.

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
