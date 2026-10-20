# openFerment — standing facts for every session

Read this before touching anything. Each line below is something a previous
session had to rediscover by reading the tree; the specs cite it as OF-BLD-012
§4.2.

## The active build (OF-BLD-015 Part B, then OF-BLD-017 Part C)

The branch is `claude/of-bld-015-postdoc`, from `main` at `6097df7` (OF-BLD-014 merged in
pull request #8). Its documents are `docs/build/OF-BLD-015-phase7.md` (Part B, "Postdoc
reaches everything"; its run sheet is folded into `docs/DEMO.md` by OF-BLD-016 §4.2); Part C
("Postdoc remembers", OF-BLD-017 Phase 5) is committed beside them when it starts. The closing
truth pass deletes `docs/build/`.

OF-BLD-016 (one active program, nothing invented on screen, Postdoc with every
tool) runs on `claude/of-bld-016-demo`, cut from `main` at `7e3ebb0`. Its document
is `docs/build/OF-BLD-016.md` (prompt `docs/build/PROMPT-016.md`); its commits are
`OF-BLD-016 §n.m: <what>`, and its Part A amends OF-BLD-014 Part A below.

- **"Next phase", "continue" and "go on"** mean Part A of `docs/build/OF-BLD-016.md`: start the
  session (`bash scripts/session-start.sh`), pay what `## Live owed` in `STATE.md` lists and this
  machine can run, find the first step whose id is missing from
  `git log --format=%s | grep -o 'OF-BLD-016 §[0-9]*\.[0-9A-Z]*' | sort -u`, and execute to the
  end of that step's phase. One commit per step, `OF-BLD-016 §n.m: <what>`, `pnpm verify` green
  before each.
- **The build documents are committed, for the length of the builds.** A cloud session starts
  from a fresh clone, so `docs/build/` holds OF-BLD-014's document, OF-BLD-015 Phase 7's and
  OF-BLD-016's on the work branch. OF-BLD-015's closing pass owns the folder's deletion. Every
  other spec stays out of git, as "Where the documents live" says.
- **Every model call openFerment makes runs `claude-haiku-5-5` at effort `medium`**: primary,
  fallback, index, eval. `OPENFERMENT_MODEL`, `OPENFERMENT_FALLBACK_MODEL`,
  `OPENFERMENT_INDEX_MODEL` and `OPENFERMENT_EFFORT` carry it (the environment in a cloud
  session; `core/.env` on the Mini); `llm.py`'s defaults are untouched. Numbers in `STATE.md`
  dated from 2026-10-16 are Haiku's.
- **The key in a cloud session** arrives as `OPENFERMENT_API_KEY`, and
  `scripts/session-start.sh` writes it to `core/.env`. Leave `ANTHROPIC_API_KEY` unset in the
  session's environment: Claude Code reads that name for its own sign-in. The key never
  appears in a chat, a log or a response.
- **Data from live runs** travels on the branch `openferment-data` (`pnpm data:push`,
  `pnpm data:pull`). Fetched full text, the audit log and the proposals stay on the machine.
- **Stop conditions**: verify red for a cause outside the step; a fact the prompt states
  turns out false when measured; a write tool that would reach a store with no write function
  and no clean refusal; a key that could reach a response, a log, the browser or git; a
  change that would let a second account read the owner's conversations with no visibility
  check in the way.

## The map is closed

- **Home plus eleven destinations, twelve rail entries, and the list does not
  grow.** `src/data/nav.ts` is the single source of truth for the rail, the
  palette, the Architecture screen and the smoke tests. `pnpm check:seed` fails
  the build if `RAIL` is not exactly twelve. `COMPONENTS.md` is the same map
  written for a person, and `check:seed` fails if the two disagree.
- Anything new lives *inside* one of the eleven as a tab or a view. The
  question is which one owns it — never whether to add a twelfth.
- The three OS components are the three stages of making something: geneOS the
  organism (stoichiometry), fermOS the reactor (dynamics), pureOS downstream
  (separation). fermOS computes from depositions: no parameter from a paper
  enters it. `src/screens/FermOS.tsx` may be extended, and its header keeps
  the reasoning.

## Stack rules that are not negotiable

- The router is a custom hash router in `src/router.tsx` (`useRoute`,
  `navigate`, `href`). **Never import `react-router-dom`.** It is listed in
  `package.json` and imported nowhere; the listing is not permission.
- UI primitives live in `src/components/ui.tsx`. **Never import `shadcn/ui`.**
- React 18 + TypeScript + Vite + Tailwind + zustand. Python side is `core/`
  (uv, FastAPI, Pydantic, `anthropic`). Every model call goes through
  `core/openferment_core/llm.py`: `claude-opus-5-5`, falling back to
  `claude-sonnet-5-5` on a refusal or when Opus is unavailable; structured
  outputs (`output_config.format`, schema made strict by `strict_schema`),
  effort `medium`, streamed. Postdoc alone runs a loop
  (`postdoc_agent.py`): `llm.converse` turns on one model with tools
  and `tool_choice` `auto`, bounded at 6 rounds, 12 tool calls,
  `OPENFERMENT_ASK_BUDGET_USD` and 180 seconds, after which one last turn
  runs with `tool_choice` `none`; a refusal or an outage restarts it once on
  the next model with a fresh conversation. Both models REJECT forced tool
  use (`tool_choice` "tool"/"any" is a 400); never reintroduce it. Prices
  live in `llm.PRICES`; `usage.models` records which model answered. The
  seven OF-BLD-014 tools go out strict; the twenty-two module tools go out
  loose, because eighteen strict tools compile to a grammar the API refuses
  (OF-BLD-015 §7.2, measured 2026-10-19), and `tools.run` validates every
  input alike before anything runs.

## Rule 1 and its mirror

- **No quantity originates in model weights.** Claim text carries no numbers —
  `core/openferment_core/validate.py` drops any claim containing a digit
  outside an identifier token (letters-then-digits, like `cw15`), counts it,
  and never repairs it.
- **A quantity enters BioRepo only inside a sentence the paper wrote.**
  Extraction candidates anchor to a verbatim quote in a fetched section, and
  the value must appear inside the quote (OF-BLD-012 §2.4). Rejected candidates
  are dropped and counted per reason; nothing is repaired.
- **Provenance is computed, never model-chosen.** `weakest_provenance` in
  Python, `provenanceOf` / `aggregateExclusion` in `src/store.ts`. No model
  output sets a provenance field. The same holds for `valueBasis` — exact,
  converted, range-midpoint, range-low, range-high, negation — which
  `anchor_candidate` computes and no reviewer or model sets (OF-BLD-012.1 F1).
- **The rules live in `biorepo.write`, and the browser asks them.** Guild
  posts to `POST /api/biorepo/check`, which runs every rule and writes
  nothing. `writeRefusal` in `src/lib/review.ts` is the OFFLINE FALLBACK and
  says so in its header; do not grow it into a second copy of the rules.
  `normalizeText` is the one thing mirrored, and it is fuzzed against
  `normalize_text`.
- **A typed value is held to the sentence like any other.** A correction or
  a gold value, whatever the decision's status, anchors on the decision's
  quote or the record's own, and needs the paper fetched (OF-BLD-012.1 §6.9).
  A decision that decides nothing — `unverified`, nothing typed, nothing
  rejected — is what an undo posts, and `biorepo.write` treats it as a
  withdrawal: the stored decision goes, and the candidate copy with it.
- Reference content (`src/data/reference.ts`) is domain knowledge, never a
  result: no titre, yield, cost or patent status. `pnpm check:reference`
  enforces it and every numeric cell needs a written justification.

## The key

- `ANTHROPIC_API_KEY` lives in `core/.env`, which is gitignored. Copy
  `core/.env.example` to create it. Set a spend cap first.
- `pnpm check:secrets` is the first stage of `verify` and fails the build if
  anything under `src/` names the variable, loads dotenv, reaches
  `api.anthropic.com`, or if any tracked file holds a key-shaped string.
- Never read the key into anything under `src/`. UI copy that needs to mention
  it points at `core/.env.example` instead.

## Shapes exist twice

- Every Pydantic model in `core/openferment_core/models.py` is mirrored as an
  interface in `src/data/types.ts`. `scripts/check-plan.mjs` diffs the field
  lists as text, by name, from its `PAIRS` list. **Add every new model to
  `PAIRS`** or the drift guard guards nothing.

## The seed, the overlay, and offline verify

- `src/data/*.ts` is the source of truth for the 189 papers (132 hand-curated,
  35 in thread P, 22 in thread Q) and 134 records.
  Do not edit `src/data/corpus/`, `PAPERS`, or `RECORDS`. There are TWO
  sanctioned exceptions, and in both a machine proposes and a person approves.
  The second is thread P (OF-BLD-014 §2.3): `pnpm thread:propose` asks Europe
  PMC with the fixed rule in `core/openferment_core/threadp.py` and writes
  `core/data/thread-p-proposed.tsv`; `pnpm thread:apply <file> --approved-by
  "<name>"` writes the `APPROVED` and `INCLUDE` rows, and no others, into
  `src/data/corpus/threadP.ts` — the one file there that changes — under a
  name `biorepo.write` would accept, on one line. Its record list stays
  empty. `test_threadp` fails when the file holds anything apply never
  writes — an organism, a topic, a licence, a record, another sentence, a
  placeholder approver — and `apply` refuses to build on such a file. A
  changed approver name that is itself acceptable is visible only in git.
  Thread Q (yeast ethanol, 2026-10-20) is the same rule module with its own
  `ThreadRule` (`THREAD_Q`): `pnpm thread:propose:q` and `thread:apply:q`,
  `core/data/thread-q-proposed.tsv`, `docs/thread-q-include.txt`, and
  `src/data/corpus/threadQ.ts`. Its include file may name `osti:<id>` (an
  NREL report on OSTI) and `sgd:<id>` (a Saccharomyces Genome Database
  strain entry) besides PMCIDs; such a row carries a `sourceUrl`, and only an
  INCLUDE row may stand on one alone. Thread P refuses a `sourceUrl`.
  The first is a DOI a person approved (OF-BLD-012.1 F9): `pnpm ids:propose`
  asks Crossref about every paper carrying no PMCID, DOI or PMID and writes
  `core/data/identifiers-proposed.tsv`, which is gitignored and is not the
  seed; `pnpm ids:apply <file>` writes back the rows — and only the rows —
  whose verdict a person changed to `APPROVED`, then prints the diff to
  commit. The script's own `PROPOSE` is an opinion, never an approval, and no
  amount of Crossref score substitutes for one. Guild's **Papers the service
  can keep** filter, on by default when the service is up, hides the records
  `biorepo.write` refuses for want of an identifier.
- The service supplies an **overlay** the store applies at load when
  `/api/health` answers (OF-BLD-012 §2.1). With the service down the app is
  exactly the seed. The overlay is AUTHORITATIVE: `candidates` and `runs` are
  a list or `null`, an empty list means the extractor produced nothing and the
  store drops what it had, and only `null` means "not supplied"
  (OF-BLD-012.1 F3). An undecided `claude-1` record absent from an incoming
  list is removed; a decided one stays and is marked `absentFromRun`.
- A record carries `original` — what it was published as — stamped once as it
  enters the store and never touched by a decision (OF-BLD-012.1 F7). Whether
  a promotion re-anchored it, and what a withdrawn correction restores, are
  answered from that field, never by diffing against `RECORDS`.
  `pnpm check:store` is the guard for both this and the overlay's contract.
- **`pnpm verify` runs with no key, no service and no network, and must stay
  green.** Twenty-four stages, in order: check:secrets → typecheck →
  check:plan → check:reference → test:core → test:sim → check:licences → check:tools →
  check:seed →
  check:biorepo → test:export → check:anchors → check:store → check:guild →
  check:lock → check:capture → check:figures → build → test:durable → test:deposition →
  test:reconcile → test:smoke → test:golden → test:deep. Live tests are
  `pnpm test:live` and never in verify. `test:sim` starts the real BioSTEAM
  worker (pytest marker `sim`); `slow` runs are `pnpm test:slow`, outside verify.
- `check:biorepo` brings its OWN export (OF-BLD-012.1 F5): it runs
  `export-corpus.ts` into a temp directory and checks against that, so it needs
  no prior `export:corpus` and can never call a decision unmerged when the
  truth is a stale projection. `OPENFERMENT_DATA_DIR` picks which biorepo.json
  it reads; `OPENFERMENT_CORPUS_IN` names a projection to check against
  instead of making one, which is how `test:export` gives rule 4 something to
  catch. Nothing in verify sets it.
- `core/openferment_core/data/corpus.json` is generated by
  `pnpm export:corpus` and gitignored.

## Hosting (OF-BLD-012 Appendix B)

- After `pnpm build`, the service serves `dist/` at `/` beside `/api`
  (`mount_app` at the bottom of `api.py`). The mount is a catch-all and MUST
  stay the last route; `test_app_static` imports `api.py` with a build present
  and fails if the mount is not last or any `/api` route is answered by it.
  With no `dist/` nothing is mounted. The page is served `no-cache` and
  `assets/` immutable, so a deploy never strands a browser on deleted assets.
- `scripts/host/` is the Mac Mini: `install.sh` once, `deploy.sh` after each
  merged session, `nightly.sh` at 03:00. `launchd.py` renders the two
  LaunchDaemons (`com.umutuzo.openferment`, `.nightly`), which run as the
  checkout's owner and never as root; `test_host` checks them. `deploy.sh`
  syncs every extra: a sync is exact, and the workers need `sim` and `rag`.
- `pnpm ready` (`core/openferment_core/ready.py`) answers "will the live loop
  work here" without spending: key, model (the free Models API, which is also
  how a retired model shows), corpus, build, data, intake counts, Europe PMC,
  huggingface.co (optional: a warning at most, never the exit code), push
  access for the decisions backup, the running service. Its last line is the
  lane (OF-BLD-014 A.4). install.sh and deploy.sh run it last. It never
  prints any part of the key; `test_ready` holds it to that. (`pnpm doctor`
  and `--offline` belong to pnpm itself.)
- The server binds to `127.0.0.1`. The service has no login, so the bind
  address is the access control; `tailscale serve` publishes it to the owner's
  devices. Widening it (`OPENFERMENT_HOST`) is a decision for Sean, never a
  default. Host and port given at install are baked into the plist, and
  `lib.sh` and `ready.service_address` read them back (`launchd.py`), so
  deploy and `pnpm ready` ask the job on its own address. `install.sh` takes
  the host only from `OPENFERMENT_HOST`, else loopback, never from the
  earlier install. `poll_host` exists in bash and Python; `test_host` keeps
  them equal. Tailscale on the Mini is the background
  service (`brew install tailscale`, `sudo brew services start tailscale`);
  its apps run only after a login. Uninstall turns off openFerment's serve
  alone (`serve --https=443 off`), never `serve reset`.
- `guard.py`, run as middleware on every request: a POST/PUT/PATCH/DELETE must
  name a host the service answers to (IP, dotless, `.local`, `.ts.net`, or
  `OPENFERMENT_ALLOWED_HOSTS`), and a browser `Origin` must be that host on
  the same port (or match `X-Forwarded-Host`, which Vite's proxy SETS from
  the browser's Host in `vite.config.ts`, overwriting any sent value; never
  switch that to `xfwd`, which keeps a forged one; `server.cors` stays off). Requests through Tailscale Funnel change nothing.
  This stops cross-site posts, DNS rebinding and other local apps. Reads stay
  open. New changing endpoints are covered automatically; `test_request_guard`
  is its test.
- Every file the service keeps is written through `atomic.write_text`
  (write beside, fsync, rename). `biorepo.write` holds `_WRITE_LOCK` across
  its read-modify-write. Never write those files with `Path.write_text`.
- `core/data/biorepo.json` merges by record through a git merge driver
  (`.gitattributes` → `scripts/host/merge_biorepo.py`, registered per clone
  by `lib.sh`). The driver never writes conflict markers: it writes a valid
  merge or leaves the file untouched and fails. Every clone registers it on
  `pnpm install` (`prepare` → `scripts/register-merge-driver.mjs`) and
  `lib.sh` registers the same string; both go through
  `scripts/host/merge-biorepo`, which picks the Python at merge time.
  `sync_decisions.sh` (what `deploy.sh --keep-decisions` runs) squashes every
  unpushed decision commit into one before rebasing, aborts a failed rebase,
  and refuses to start over an unfinished one. Decisions on one record are
  settled by the later `at`, compared as moments. `test_merge_biorepo` runs
  all of it through real git.

## Guild's ledger (OF-BLD-013)

- **A level is computed, never stored.** `competenceOf` in
  `src/engine/competence.ts` derives every person's level on every skill from
  the ledger's entries, with `today` passed in. No screen, service field or
  model output holds a level. `pnpm check:guild` holds the ladder still.
- **The rules live in `guild.py`, and the browser asks them.** Every write to
  `core/data/guild.json` goes through `write_person`, `write_evidence` or
  `withdraw`; `POST /api/guild/check` runs the entry rules and writes nothing.
  `offlineRefusal` in `src/lib/guild.ts` is the OFFLINE FALLBACK and says so;
  do not grow it into a second copy of the rules.
- **`core/data/guild.json` never enters git.** It is personnel data and the
  repository is public. Skills and step tags are TypeScript seed
  (`src/data/skills.ts`, `Step.skills`) and reach Python as `skills.json`,
  written beside `corpus.json` by `pnpm export:corpus`.
- **The service's one use for a level is mirrored.** Whether a cosigner, or
  an operator recording a run alone, holds the skill today is decided by
  `core/openferment_core/competence.py`, a mirror of `competence.ts` held to
  it by a fixture (`pnpm export:competence-fixtures`, run by `test:core`).
  When the two disagree, the TypeScript side is right and the mirror is fixed.
- **Run mode writes to the ledger, and holds on enforced skills.**
  `GuildGate` in Deposition names the operator and asks for a cosigner when
  they are Supervised, lapsed or suspended on a skill the step needs.
  Completing a step writes one entry per skill it needs, once per step: a run
  alone, a cosigned run or a deviation (`recordStepForGuild` in
  `src/store.ts`). The lead's `GuildPolicy` (in `guild.json`, set through
  `write_policy`, Settings → Guild policy) makes each criticality advise or
  enforce; on an enforced skill `holdFor` in `competence.ts` holds the step
  until an operator is named, a cosigner who holds the skill is recorded, or
  someone qualified takes over. Critical skills are enforced by default.
- **A lesson passed is Learning, and goes no further.** A lesson that names
  skills (`Lesson.skills`) writes one knowledge entry per skill, with no
  observer, for whoever is learning when its checkpoint is passed
  (`recordLessonForGuild`). Supervised needs an assessor's training sign-off
  (`source.kind === 'signoff'`), in `competence.ts` and its mirror alike. Such
  a lesson states no quantity of its own: its numbers arrive through the
  `skill-steps` embed, read live from the protocols, and `check:seed` holds
  its prose and questions to that.
- **My path is read, never kept.** `/primer/path` shows one person the next
  step on each skill from `pathOf` in `src/engine/path.ts`, which reads the
  statuses and the lessons and holds nothing; `check:guild` holds its rules.
  Primer reserves `path` and `practice` as second segments, matched before
  the lesson lookup, and `check:seed` refuses a lesson with either id.
- **Practice holds Rule 1 for teaching.** `core/openferment_core/practice.py`
  drafts a scenario through `llm.py` from the steps that need a skill, their
  protocols' materials (rendered into `skills.json` by `export:corpus`) and
  the runs the browser sends. The model writes words and cites sources; every
  value in the evidence pane is copied from the source it cites, and a draft
  with a number of its own, an unresolved source or marker, or no step
  needing the skill is refused whole. The tutor is held to the same, closes
  on the third answer with what it observed, and a closed session for a
  person on the ledger becomes a `scenario` entry (no observer, the session
  as its source), which is Learning and no more. With the sample shown the
  service is sent nobody (`practiceLearner`), and the entry goes on the
  sample alone. `core/data/practice.json` never enters git. Offline tests use
  a stand-in model; the real one is `pnpm test:live`.
- **Checks are proposed by fixed rules, and run by an assessor.**
  `rankPairs` / `proposeChecks` in `src/engine/checks.ts` rank every person
  and skill by suspended, lapsed, lapsing, ready, recent deviation, low
  confidence and the lead's quarterly rate; `core/openferment_core/checks.py`
  mirrors them (and `competence.py` now mirrors confidence), held by the
  competence fixture. `nightly.sh` runs `python -m openferment_core.checks
  propose`. A check is asked for, scheduled, dismissed with a reason, or run
  through `checks.py`; a run calls every criterion and writes one witnessed
  entry per skill with the check as its source, in one ledger write
  (`guild.write_check_entries`; `write_evidence` refuses a check source, so
  nothing reaches the ledger around the criteria). Every read-modify-write
  of `checks.json` holds `checks._held()`, the thread lock and a file lock,
  because the nightly job is a second process. A check's brief is one
  model call (`checks.brief`, and `brief --missing` nightly when a key is
  there): steps to watch by ref, criteria by index, and questions held to
  Practice's number check; the model is never told who is checked, and a
  brief that breaks a rule is refused whole. `core/data/checks.json` never
  enters git.
- **A check never shows to the person it names until it is run.**
  `shownTo` and `mayQueue` in `src/engine/checks.ts` decide what Guild's
  Checks tab, `/guild/checks`, Home's Workforce card and the tab badge show;
  the queue is for the lead and assessors. Asking for your own check from
  My path answers the same whether or not one is open (a `duplicate` refusal
  is swallowed for the asker alone). `/guild/checks/:id/run` is the bench
  (`BenchCheck.tsx`), a full-screen takeover under Deposition's constraints:
  one criterion at a time, Meets or Needs work, the assessor's words per
  skill, then a sign step in the assessor's name. With the sample shown the
  queue is the ranking run in the browser and the bench writes to the sample
  alone. `check:guild` part 10 and the smoke's bench flow hold all of it. A
  model's proposal to check someone follows the same rules on Home
  (`shownProposals` in `src/lib/proposals.ts`, `check:guild` part 11).
- **The sample team is invented and stays in the browser.** `guildSample` is
  shown in place of the ledger while loaded; nothing in it is posted, written
  to `guild.json` or kept in the Durable tier.

## Licences, sessions and data that outlive a VM (OF-BLD-014 Phase 1)

- **Every dependency's licence is read and checked.** `pnpm check:licences`
  (`scripts/check-licences.py`, after test:core in verify) reads the licence
  metadata of every distribution in `core/.venv` that `core/uv.lock` names
  (License, License-Expression, the licence classifiers; any one decides) and
  of every JavaScript production dependency, against `core/licences.toml`:
  the allowed strings in each package's own spelling, and under `[accepted]`
  each package a named person accepted, with the date and why. It rewrites
  `THIRD_PARTY.md` and fails while the committed copy is stale. A dependency
  lands with its licence line; a string outside the permissive families
  waits for Sean.
- **A session starts with `bash scripts/session-start.sh`.** It writes
  `core/.env` from `OPENFERMENT_API_KEY` when the file is missing (mode 600,
  checked ignored, never printed), installs every extra, exports the corpus,
  pulls the data branch, runs `scripts/data-prepare.sh` and `pnpm ready`.
  `pnpm ready` ends with the lane: `full` (a key the Models API accepted, and
  Europe PMC answering), `model-only` (that key alone), `none` otherwise, so
  `--no-network` and fixture mode read `none`. Its `huggingface` row warns
  and never changes the exit code.
- **What live runs produce travels on `openferment-data`,** an orphan branch:
  `pnpm data:push` and `data:pull` (`scripts/data-sync.sh`) copy the paths
  E.10 lists, through a throwaway checkout under `.data-sync/`, and refuse any
  other path by name, and any symbolic link on or under one. A pull keeps a
  local file that differs from the branch's and names it. Fetched full text,
  `core/.env`, spend and Guild's files never travel. `pnpm decisions:push` commits `core/data/biorepo.json` alone
  and pushes the current branch.
- **`pnpm prototype:up`** brings a fresh clone to the running prototype: the
  service on 127.0.0.1:8000 over `core/data/`, the build on 127.0.0.1:4173
  with `/api` passed through. `pnpm shots` photographs routes of a running
  app into `docs/shots/`.
- **The demo set follows its saved response** (`demo.py`): three
  demonstration decisions over the hand-written stand-in, the accept of
  `r-B5-3` alone over a real response. `pnpm test:export` exports
  `core/tests/fixtures/export/`, the stand-in decided all four ways, which
  `pnpm demo:fixtures` rebuilds every run. `pnpm witness:numbers` prints what
  Witness shows, from a running service.

## Thread P and the polymer family (OF-BLD-014 Phase 2)

- **Three programs, one corpus.** Threads A–O are the hand-curated casein
  program; thread P is PHA from waste cellulosic sugars and thread Q ethanol
  from glucose by wild-type *S. cerevisiae*, each proposed by rule and
  approved by a person (see "The seed" above). The thread letters are written
  as `[A-Q]` in three places — `byEntryId` in `src/data/papers.ts`,
  `src/sim/chat.ts` and the chip pattern in `scripts/golden-path.mjs` — and a
  new letter changes all three. Home's Programs strip counts each program
  live from the store.
- **A strain alias carries the designation.** `STRAIN_ALIASES` maps `h16` and
  `kt2440` spellings, never a species alone, so a value measured on another
  strain of the species stays apart. Extracted values carry `organismText`
  (the paper's words) beside `organism` (a strain id when one resolved) and a
  `carbonSource` kept only when it stands in the cited section.
- **A biopolymer is its own process family.** PHB and mcl-PHA are category
  `biopolymer`, process family `P12`: they share no train with the proteins
  and small molecules. Their bands are market framing, like every product's.

## Computed values, tools and budgets (OF-BLD-014 Phase 3)

- **`computed` is a provenance, and there is one ranking.** `measured, gold,
  verified, curated, computed, unverified, user, industry-estimate, demo`,
  identical in `PROVENANCE_RANK` (`src/store.ts`) and `PROVENANCE_ORDER`
  (`models.py`); `check:plan` parses both and fails on any difference in
  members or order. A computed value is held out of aggregates, like an
  industry estimate: it is derived from values already counted.
- **A computed value carries its basis, and its provenance follows from it.**
  `ComputedBasis` names the tool, its version and every input with its
  source (`record`, `deposition`, `artifact`, `model`, `convention`,
  `assumption`). `basis.basis_provenance` decides: an assumption makes it
  `demo`; otherwise the weakest of `computed`, each record's provenance,
  `measured` for a deposition and each artifact's provenance. No model, no
  person and no TypeScript copy sets it.
- **What was computed is kept.** `artifacts.compute` runs a registered pure
  function once per (tool, version, inputs, seed) and writes
  `core/data/artifacts/<16 hex>.json` (gitignored, on the data branch) under
  one store lock; a repeat returns the stored file with its provenance
  recomputed from the inputs as they stand now. `replay` recomputes and
  compares `outputHash` and never rewrites the file. BioRepo → Artifacts
  (`/biorepo/artifacts`) shows them; `artifacts` and `search` are reserved
  second segments under BioRepo.
- **A subsystem can be `live`**: code behind it computes or stores at run
  time. It names its files in `implementedIn`, and `check:seed` fails when
  one is missing. `biorepo.artifacts` is the first.
- **Two model roles, one daily cap.** `llm.chain("answer")` is Opus then
  Sonnet; `llm.chain("index")` starts on `OPENFERMENT_INDEX_MODEL`
  (`claude-haiku-5-5`) and falls back to the answer chain. Every call
  reserves its worst case in `core/data/spend.json` (`spend.reserve`, one
  step under a cross-process lock) and settles what it cost; a call that
  could pass `OPENFERMENT_DAILY_BUDGET_USD`, a model with no price in
  `llm.PRICES`, or a damaged spend file refuses the call
  (`BudgetExhausted`, a `ModelUnavailable`). Cost counts cached tokens:
  writes at 1.25× input, reads at 0.05× on Opus and Sonnet 5.5, 0.1×
  otherwise, and Haiku 5.5's long tier past 100,000 prompt tokens.
  Offline tests charge a file of their own (`core/tests/conftest.py`).
- **`converse` is one tool turn on one model.** Each tool strict unless the
  registry marks it loose (the twenty-two module tools, see above),
  `tool_choice` `auto` or `none` and nothing else (anything else is refused
  before it is sent), the answer schema in `output_config.format`, top-level
  `cache_control`. It falls back nowhere; the loop that owns the
  conversation decides.
- **One tool registry, closed at twenty-nine names** (`tools/__init__.py`, E.6
  and OF-BLD-015 §7.2–§7.3: the seven below, then one read and one write tool
  a module, named `<module>_read` and `<module>_write`).
  Postdoc's loop, `GET /api/tools` / `POST /api/tools/{name}` and the MCP
  server all go through `tools.run`. **Tool inputs carry ids and words:** a
  JSON number anywhere in an input outside top-level `k` and `limit` refuses
  the call, and every refusal is a `ToolResult` with `error` set. A summary
  over 9,000 characters is replaced by an error. Built: `search_records`
  (over `evidence_pool`: seed and verified records plus the extractor's
  anchored candidates no decision rejected, as `unverified`) and
  `convert_units` (a record's own value through `units.py`, kept as an
  artifact).
- **Heavy libraries run in workers.** `workers.SimWorker` starts a module
  on first use, keeps it warm, kills and restarts it on a timeout, and
  reports the stderr tail of a crash; `workers.serve` answers on a
  duplicate of fd 1 with fd 1 pointed at stderr, so a library's printing
  never reaches the stream. `cobra` is imported in the geneOS worker alone
  and `biosteam` in the Proforma worker and `flowsheets/` alone;
  `test_workers` greps for both.

## Passages and search (OF-BLD-014 Phase 4)

- **A passage is the paper's own words.** `passages.py` cuts every
  `complete` fetched paper (never a curation note): prose at sentence ends to
  about 900 characters and never past 1,400, with one sentence of overlap; a
  table with whole rows, each chunk led by the heading and the first row; a
  figure caption whole; an abstract as one, two, or as prose when two halves
  cannot hold it. `start`/`end` are offsets into the section's text; the
  `context` (title, year, heading) is indexed and never shown as the paper's
  words. `CHUNKER_VERSION` changes cut every paper again. The index lives in
  `core/data/index/` (gitignored, rebuilt per machine; `config.json` and the
  vectors, `dense.npy` and `dense.json`, travel on the data branch, and
  `data-prepare.sh` builds the vectors only when they are missing or stale).
- **Five lanes, one entry point.** `retrieve.search_detail` runs `bm25`,
  `bm25+expand`, `hybrid`, `bm25+rerank` or `hybrid+rerank`, fused by
  reciprocal rank (`1 / (60 + rank)`). With no lane named it uses
  `config.json`'s, and falls back to `bm25` with a note when that lane cannot
  run here; a named lane that cannot run is refused with why. Dense vectors
  (`embed.py`, `fastembed` imported inside `FastEmbedder`) are refused when
  their ids or words no longer match the index. Helper calls are `index`-role
  `llm.call`s, cached under `core/data/index/cache/`.
- **The grading reader is held to the passage.** Its copied sentence must be
  a whole sentence or table row of the passage, or a run of them, word for
  word after `normalize_text`; anything else zeroes the grade and is
  counted, never repaired, cache included.
- **The default lane is chosen by a number.** `rageval.choose_lane`: mean
  nDCG@10 on K and S; `bm25` holds until a lane scores higher, and a lane
  that calls a model per question must lead the best free lane by 0.02. K is
  built from records and candidates whose quote sits in a passage, S is
  model-written from sampled passages (a question sharing five words in a row
  or a number with its passage is discarded; questions written for another
  cut are set aside), F is the flows whose records anchor.
- **Search reaches the browser in two places.** BioRepo → Search
  (`/biorepo/search`, `POST /api/rag/search`) and Witness → Retrieval
  (`GET /api/rag/report`). The reader takes `?section=…&quote=…`, marks the
  words where span location finds them, and says so when it cannot.
- **One service double.** `scripts/lib/service-double.mjs` answers the
  browser tests from fixtures `demo.py --prototype` generates (with no key).
  The smoke starts it in full; the golden path starts it `seedOnly`, leaving
  health and the overlay to the static server so its demo script walks the
  seed.
- **A licence with no metadata** can be accepted only under the exact string
  `"no licence metadata"` (`check-licences.py`), and stops passing once the
  package states one.

## Postdoc's loop (OF-BLD-014 Phase 5)

- **A Live conversation is kept, and a follow-up reads it.** Live turns are
  `LiveConversation`s in the store and the Durable tier, never `ChatMessage`s.
  A follow-up posts the earlier turns as `PriorTurn`s (question, claims,
  gaps, decline: words only); `postdoc_agent._opening` sends the last four as
  user and assistant text, drops a line holding a number, and `SeenSet`
  still starts empty, so nothing an earlier turn retrieved is citable. The
  coverage sweep reads those earlier questions with the follow-up
  (`_swept`), never the earlier answers, and the map then says it names what
  the conversation names.

- **A plan answers to `validate_plan`.** Every claim the loop writes is
  dropped whole and counted when its text holds a number, a record id does
  not resolve in the evidence pool, it cites a record, passage or evidence id
  no tool returned in this run (`SeenSet`, which keeps nothing from a refused
  result), a quote is over 300 characters or is not one whole sentence or
  table row of its passage, or a run of them, after `normalize_text`
  (`rerank.is_whole_sentence`: a fragment can lift a number out of its
  negation), or it cites nothing without saying `unsupported`. A gap or the
  decline with a number is dropped and named in `rejectionReasons`
  (`held_to_rule_one`, on the single path too), and the decline code writes
  stands in. Its provenance is the weakest of its records and
  computed values, `unverified` on quotes alone; its papers are derived. A
  restart opens as the first conversation did (earlier turns, then the
  question and the map), forgets what the first conversation retrieved and
  gets the whole call budget again; the tool cache does not forget, and what a search lane
  spends on a model (`ToolResult.usage`) is charged to the question once.
- **Text inside a tool result is evidence, never an instruction.** The
  prompt says so, and the validator is the guard: a passage telling the
  model to state a number changes nothing it lets through
  (`test_postdoc_agent`).
- **`search_passages` is the third tool**: up to six passages, each cut to
  900 characters in the summary, the passages themselves in
  `ToolResult.passages`, which is what a quote is checked against.
- **Trace lines are written by code** (`_summary_line`), never by the
  model, and stream as `step` events from `POST /api/ask/stream`, then one
  `plan` (a declined plan included) or one `error`. When the reader leaves,
  the loop stops before its next model turn (`_stream_events`). `POST /api/ask` takes
  `mode`, `agent` by default; `single` is the one-call path in `postdoc.py`.
- **The double replays a recorded loop.** `demo.py --prototype` runs the
  real loop with a scripted stand-in over B5's stand-in passages and the
  overlay's candidate, and writes `ask-stream.jsonl`; `test_demo` holds it to
  the code, and the smoke and golden path watch the panel draw it.
- **`pnpm ask:batch <file>`** asks a file of questions through the loop and
  keeps each plan under `core/data/live/` (on the data branch);
  `docs/build/questions-pha.txt` holds Appendix 4's ten.

## Postdoc reaches every module (OF-BLD-015 Phase 7)

- **A coverage pass runs before the first turn, in code.** `module_stores.py`
  reads all eleven modules into one row shape: the seed's modules through
  `modules.json`, which `pnpm export:corpus` writes beside `corpus.json`
  (Dominion's molecules and findings, runbooks, protocols, hosts, pathways,
  unit operations, scenarios, lessons), and the service's own stores (records
  and candidates through the evidence pool, artifacts, Guild's ledger and
  checks, Intake's fetch state, the geneOS shelf, the open proposals).
  `coverage(question)` finds the rows the question names by label, id or
  spelling, and every row of a module it names, kept to the states a clause
  about that module asks for. The map rides in round one after the question,
  is the trace's first step (one line a module when opened), and the plan
  carries it: the footer reads "Searched eleven, found in two: … · read in
  part: Runbooks, fermOS, BioRepo". A plan with no claim never says the
  corpus is silent when a module found something.
- **One state enum, computed, never chosen.** `open`, `fenced`, `approved`,
  `locked`, `proposed`, `retired`, from each module's own word in
  `module_stores.py` (a clearance of `clear-expired` or `clear-none` is
  `open`; `watch-*`, `blocked` and `unknown` are `fenced`; a locked runbook is
  `locked`). The table is in `docs/TOOLS.md`.
- **A read tool a module** (`tools/modules.py`): one input (ids or refs,
  words, a kind, a state, a limit), one output, `ModuleRow` (`ref`
  `<module>/<kind>/<id>`, label, state, the module's status word, the
  provenance mark or null, a short detail). Guild reads a name, a role and
  whether the person is active, never a level or a title. A claim cites rows
  in `moduleRefs`; `SeenSet` keeps them and `validate_plan` drops a claim
  citing a ref no tool returned; the rows' marks enter the claim's weakest
  provenance. An artifact row's mark is recomputed from its inputs as they
  stand when it is read (`basis_provenance`), never copied from the file.
- **A write tool a module** (`tools/writes.py`), and it never touches a
  store: each action calls the module's own write function (`geneos.ceiling`
  and kin, `fermos.forecast_run`, `proforma.run`, `extract.add_candidate`
  under §2.4 with ids `mw1-…`, `intake.fetch_paper`, `extract.extract_paper`)
  or refuses in words with who makes the change (Dominion, pureOS and Primer
  are seed; protocols, depositions, assumptions, decisions and new sources
  are a person's). Every write that goes through is appended to
  `core/data/audit.jsonl` (`audit.py`, `GET /api/audit`, gitignored) with
  `agent: model`, the model id, the effort and the ask id
  (`ToolContext.ask_id`). A person's carry-out or dismissal is appended the
  same way. **A candidate written by hand is not an extraction:** it is kept
  in `candidates/hand/<paper>.json`, never in the extractor's file, so the
  extractor still runs on its paper and Witness never scores it (the overlay
  still carries it, and `biorepo.write` resolves its id there). It passes on
  only the fields the action lists, and `negativeResult` and `isPrimary` as
  the word true or false; any other field refuses the call.
- **The gates are one table** (`tools/gates.py`, the same rows in
  `docs/TOOLS.md`): `publish`, `spend`, `lock`, `sign`, `personnel`, `bench`,
  `notebook`. An action at a gate writes nothing and becomes a proposal
  (`proposals.py`, `core/data/proposals.json`, gitignored) with
  `state: proposed`; Home shows every open one as a card with one button,
  disabled until a reviewer name is set; `POST /api/proposals/{id}/carry-out`
  and `/dismiss` take a named person (placeholders refused) and, for a check,
  `actingId`, the Guild person the browser acts as. The server runs what it
  can in the person's name (`checks.request` by the acting Guild person; an
  extraction once the budget allows), with the store's locks let go while it
  runs, and records that the person took the rest to the place the gate
  names; a server gate with no server action is refused and stays open. The
  model may propose a check and may never record or sign one:
  `guild record_check` is refused, and no gate's server action signs
  anything. **A proposal is held to Rule 1** (`proposals.propose`): its
  note, target, field values, title and why hold no number and its target
  is one id, or it is refused whole; one ask leaves one open proposal per
  module, action and target. A Guild proposal is served
  (`proposals.listed`, `home_read`) without its note, why and target, and
  its title names nobody.
- **`pnpm check:tools`** (`scripts/check-tools.py`, the eighth stage) fails
  when a module lacks a read or a write tool, when `writes.py` holds a file
  write or reaches a store function outside `ALLOWED_WRITES` (the file is
  parsed and every name followed through its import, aliases included; a
  store module handed around bare or a dynamic import fails), when a gated action
  completes without a named person, or when `gates.py` and `docs/TOOLS.md`
  name different gates. **Eval set O** (`evalo.py`, `pnpm eval:o`): ten
  cross-module questions keyed by the coverage code, scored on the modules
  read; the footer is not scored, because its key and the footer are the
  same `coverage` call and it held by construction. The report goes to
  `core/data/live/eval-o.json`.
- **The MCP server needs no change for any of it**: it lists `tools.infos()`
  and calls `tools.run`, so the module tools appear there with the same marks
  and gates; `test_mcp` counts thirty-one.

## Figures and geneOS's ceiling (OF-BLD-014 Phase 6)

- **One figure grammar.** Every chart this build adds comes from
  `src/components/figures/`: the kind of thing decides the mark (a record a
  point, a computed limit a rule, a computed curve a line), provenance
  decides shape, fill and dash through `ENCODING` in `encoding.ts`, a
  `Record` over every provenance. Each figure exports `toTable(props)`, which
  feeds its "View as table" twin and the tests, and sits in `FigureFrame`
  (the question as title, units, CSV, sources, the basis of anything
  computed, and what would fill it when empty). `pnpm check:figures` holds
  it; `recharts` stays in Compare and ProformaScenario alone. Settings →
  Figure grammar (`/settings/figures`) is the written definition, over a
  sample `demo.py --prototype` writes to `src/data/figureSamples.json`.
- **geneOS computes a ceiling.** Flux balance analysis on a shelf of
  published reaction networks (`geneos_models.py`, data only): `e_coli_core`
  and `iJO1366` bundled with cobra plus the phaCAB add-on, each added
  reaction checked for mass balance; `RehMBEL1391` (*C. necator* H16),
  which `pnpm geneos:fetch` clones at `00c70c5`; and for ethanol two
  reconstructions of *S. cerevisiae* S288C, `iMM904` (BiGG's file by URL;
  its non-commercial licence accepted by Sean Creighton) and `Yeast9`
  (yeast-GEM v9.1.1 by git; CC BY 4.0, its `r_` ids mapped and checked by
  name). Files land in `core/data/models/` (gitignored) and are checked
  against their sha256, a mismatch set aside. A product is a metabolite
  (PHB: the worker adds `DM_phb_c` where a file lacks it) or an exchange
  (ethanol: `EX_etoh_e`, or the model's own id), and the worker reports each
  model's counts as its file publishes them. The uptake (10 mmol gDW⁻¹
  h⁻¹), the product's formula and the sugars' molar masses are
  conventions in every basis; every other bound stays as the file publishes
  it. Ceiling, frontier (twelve growth rates) and sugar mix (eleven
  proportions at equal carbon) are artifacts; a sugar a model cannot take up
  is a finding in words and stores no number. Appendix 2's bundled-model
  values are asserted in `test:core`, the *C. necator* ones in
  `test_geneos_live.py`, the yeast ones in `test_geneos_yeast_live.py`.
- **`cobra` lives in `workers/geneos_worker.py` alone**, behind the
  `SimWorker` JSON contract, with `swiglpk` and `python-libsbml`: three
  copyleft libraries accepted under D4 in `core/licences.toml`, where model
  files are listed under `[data]` with source, revision, hash and licence.
  The toy network the worker builds is a STAND-IN for tests and fixtures and
  is never listed on the shelf: the API and the tool refuse it, and
  `allow_toy` (fixtures alone) gives it an `assumption` model input, so
  anything computed on it is `demo`. A fetched file is checked against its
  hash wherever it is used (`geneos_models.available`), and `geneos:fetch`
  fetches again only a file that is missing or does not match.
- **geneOS → Model** (`/geneos/model`, `geneos.model` is `live`) draws every
  shelf model's ceiling for the chosen sugar beside each
  `pha_yield_substrate` record measured on that sugar (`yieldsOnSugar`; the
  rest are counted, not drawn), rings a record above a ceiling and asks a
  reviewer to check its basis, and shows the chosen model's frontier and
  sugar-mix line and what it lacks. A strain page whose host has a model
  shows its card; an evidence card with the `ceiling` hint draws it inline.
  `yield_ceiling` is the registry's fourth tool.

## fermOS fits what a run measured (OF-BLD-014 Phase 7)

- **A deposition's readings become a series.** `Deposition.sampleTimes`
  (hours, by entry id) and `seriesRoles` (biomass, product, substrate, set by
  a person) are optional and Durable. `seriesOf` (`src/engine/series.ts`)
  groups timed entries by measure in time order, in the measure's unit; a
  correction keeps its reading's time (`amendEntry`) and replaces it; an
  untimed entry keeps its old meaning. CSV readings attach as unconfirmed
  entries in time order, a row placed only when its measure names the
  measure (`placeRow`), every other line kept as an observation.
- **`fermos.py` fits, and the browser sends the series.** A growth rate over
  the best window of four or more readings; a closed-form kinetic model
  refined in two weighted passes, intervals from the covariance and Student's
  t; μ and Xmax `identified` when the interval excludes zero, decided by the
  service from the numbers. Fits and forecasts are artifacts (`growth_fit`,
  `kinetic_fit`, `growth_forecast`) with source `deposition`; the service
  cannot see the browser's depositions and says so in each basis. A forecast
  is 200 seeded draws with each series' scatter added (yield is taken
  without it), ends where the median sugar runs out, and refuses a fit whose
  μ or Xmax is unidentified. A changed starting value is an assumption with
  a name, so the forecast is `demo`; one equal to the run's own is no change.
- **The sample run is invented** (`demo.py --prototype` writes
  `src/data/fermosSample.json`), labelled, fitted and forecast inline
  (`sample: true`) and kept nowhere. `growth_forecast` is the fifth tool.

## Proforma prices a flowsheet BioSTEAM ran (OF-BLD-014 Phase 8)

- **BioSTEAM lives in the Proforma worker.** `biosteam` is imported in
  `workers/proforma_worker.py` and `flowsheets/` alone (`test_workers`).
  `proforma.py` keeps one warm `SimWorker`; `GET /api/proforma/status`
  answers cold, starting, ready or failed, and `OPENFERMENT_WARM_PROFORMA=1`
  starts it with the service. `pnpm test:sim` (marker `sim`) runs the real
  worker in verify; `pnpm test:slow` (marker `slow`) holds the benchmark and
  the PHA flowsheet, outside verify.
- **The benchmark comes first.** `biorefineries.cornstover` with its own
  defaults must give 1.968 USD per gallon within 0.5 % (B.3); it is an
  artifact sourced `model`. `GET /api/proforma/benchmark` reads, POST runs.
- **`pha_sugar_v0` holds no input value.** Sugar and its dilution water are
  two streams, so sugar is priced on sugar alone. `tea._sales` is reset
  before every `solve_price`: the solver starts from the last answer, and a
  price would otherwise depend on run order. An infeasible case names its
  reason: carbon, oxygen (BioSTEAM's own "infinite flow rate of gas"), or
  the fermenter's balance.
- **Every input names its source.** `proforma.bind` takes thread P records
  of a sugar or hydrolysate feed through the aggregate gate and `units.py`,
  or a named person's assumption (kept in the Durable tier, merged by input
  key); an input with neither refuses the run with a 422. A run is one
  artifact, `demo` while any assumption remains. Spearman uses averaged ranks
  and skips an input with no spread. `selling_price` is the sixth tool and
  never runs a scenario; given `proforma_benchmark` it cites the stored
  benchmark run (the NREL 2011 corn stover design) in USD per gallon. The double's Proforma fixtures come from
  `demo.py --prototype` with a STAND-IN evaluator in place of BioSTEAM.

## Runbooks keep score (OF-BLD-014 Phase 9)

- **Three prediction kinds.** A `Prediction` with no `kind` is a point, held
  within ten percent; an `interval` holds inside its ends; a `bound` is a
  ceiling and holds at or below its value (no field names a side, and the
  only bounds the service writes are ceilings). `holds` and `deltaOf` in
  `reconcile.ts` decide all three, and nothing else does; from a zero
  reference the sign of the reading decides.
- **The lock covers the new fields only when present.** `canonical()` in
  `lock.ts` appends kind, interval, artifactId and recordIds when a
  prediction carries any of them, so a point hashes as before:
  `scripts/fixtures/seed-lock-digests.json` holds the eight locked seed
  digests and `check:lock` holds the seed to them. A draft from the service
  carries those fields as null, which is part of what is hashed; never turn
  null into undefined between lock and reload.
- **A drafted runbook's numbers come from the service.** `draft_runbook`
  (the seventh tool) takes ids and words; `runbook_draft.build` writes every
  value and interval from the artifact or records an item names, accepts
  only ids this run's tools returned (`ToolContext.seen`; a draft is never
  served from the cache), and a measure must share its prediction's
  dimension and records in its unit. `corpus.json` exports product and
  strain ids for the check. The plan carries `runbookDraft`; "Turn into a
  runbook" opens an unlocked research runbook.
- **Adopted runbooks are Durable**, with their locks (`adoptedRunbooks`,
  re-applied by `applyDurable`, which `hydrateDurable` calls; check:store
  round-trips it). Their ids are time-based, because `nextId` restarts.
- **The ledger is read, never kept.** `engine/ledger.ts` counts locked,
  tested (the latest conclusive run), held, missed and inconclusive runs for
  `/runbooks/ledger` and Home's Predictions card alike; a hit rate shows from
  five tested. `ledger` is a reserved second segment under `/runbooks`.
  `IntervalLedger` draws a runbook's predictions and a deposition's
  reconciliation; `Dossier` draws the artifacts behind a runbook's
  predictions as ceiling, forecast, price, keeping what loads. The double
  replays `ask-draft-stream.jsonl` for a question that starts with "Draft".

## Persistence tiers

- The **Durable** tier persists depositions, review decisions, runbook locks,
  this browser's copy of Guild's ledger with what it still owes the service,
  the lessons finished here, and Postdoc's Live conversations across a refresh (OF-BLD-006 §4.6: `snapshotOf`, `hydrateDurable`,
  `saveDurable` in `src/store.ts`). Reference and Ephemeral tiers stay in
  memory. The review queue and its `accept` / `reject` / `skip` / `gold`
  actions already exist in `src/screens/Guild.tsx` and `reviewRecord` —
  extend that card; never build a second queue.

## Deposition (was Run Mode)

- `src/screens/Deposition.tsx` — the file the specs still call `RunMode.tsx` —
  is glove-tolerant, 810 px tablet portrait at arm's length, touch targets
  ≥ 44 px, step text at ≥ 7:1 contrast, no hover-dependent affordance,
  full-screen takeover. These constraints are load-bearing. **Extend it; never
  rewrite it**, and preserve the header comment that documents them.

## How work lands

- One commit per spec step, message `OF-BLD-0NN §x.y: <what>`. `pnpm verify`
  green before every commit. Stop and report when verify goes red or a fact
  the spec states turns out wrong when measured.
- Retired paths redirect (`REDIRECTS` in `nav.ts`, longest prefix, exact beats
  pattern); retired words stay as palette aliases; a rename touches the file
  name too so code and product share one vocabulary.
- Build guards are negative-tested: sabotage the thing, watch it fail, restore.

## Where the documents live

- `COMPONENTS.md` — the map of the eleven and the seams between them.
- `docs/OF-COR-001.md` — the corpus and its curation.
- `BUILD-SPEC.md` — the original build contract against `src/data/types.ts`.
- OF-BLD specs arrive as files at repo root for the session (`OF-BLD-0NN.md`,
  `PROMPT.md`) and are deleted before the final commit of that session; they
  live in Notion. Never commit them.
- A build's own document is the exception, for the length of its build
  (OF-BLD-014's decision D1, kept by OF-BLD-015): `docs/build/` holds it on
  the work branch, and the closing truth pass deletes the folder. OF-BLD-014's
  `docs/build/OF-BLD-014.md` and `PROMPT.md` are still on `main`, its §10.4
  having been left undone; the OF-BLD-015 truth pass removes them with its own.
