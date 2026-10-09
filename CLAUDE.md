# openFerment — standing facts for every session

Read this before touching anything. Each line below is something a previous
session had to rediscover by reading the tree; the specs cite it as OF-BLD-012
§4.2.

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
  (separation). fermOS cannot be seeded from literature; kinetic parameters
  arrive through Deposition. `src/screens/FermOS.tsx` is not to be touched.

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
  effort `medium`, streamed, no agent loop. Both models REJECT forced tool use
  (`tool_choice` "tool"/"any" is a 400); never reintroduce it. Prices live in
  `llm.PRICES`; `usage.models` records which model answered.

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

- `src/data/*.ts` is the source of truth for the 132 papers and 134 records.
  Do not edit `src/data/corpus/`, `PAPERS`, or `RECORDS`. The ONE sanctioned
  exception is a DOI a person approved (OF-BLD-012.1 F9): `pnpm ids:propose`
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
  green.** Twenty stages, in order: check:secrets → typecheck → check:plan →
  check:reference → test:core → check:seed → check:biorepo → test:export →
  check:anchors → check:store → check:guild → check:lock → check:capture → build →
  test:durable → test:deposition → test:reconcile → test:smoke → test:golden →
  test:deep. Live tests are `pnpm test:live` and never in verify.
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
  checkout's owner and never as root; `test_host` checks them.
- `pnpm ready` (`core/openferment_core/ready.py`) answers "will the live loop
  work here" without spending: key, model (the free Models API, which is also
  how a retired model shows), corpus, build, data, intake counts, Europe PMC,
  push access for the decisions backup, the running service. install.sh and
  deploy.sh run it last. It never prints any part of the key; `test_ready`
  holds it to that. (`pnpm doctor` and `--offline` belong to pnpm itself.)
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
- **Run mode writes to the ledger, in advise mode.** `GuildGate` in
  Deposition names the operator, asks for a cosigner when they are
  Supervised, lapsed or suspended on a skill the step needs, and lets every
  step complete. Completing a step writes one entry per skill it needs, once
  per step: a run alone, a cosigned run or a deviation
  (`recordStepForGuild` in `src/store.ts`). Holding a step waits for Phase 5.
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
- **The sample team is invented and stays in the browser.** `guildSample` is
  shown in place of the ledger while loaded; nothing in it is posted, written
  to `guild.json` or kept in the Durable tier.

## Persistence tiers

- The **Durable** tier persists depositions, review decisions, runbook locks,
  this browser's copy of Guild's ledger with what it still owes the service,
  and the lessons finished here across a refresh (OF-BLD-006 §4.6: `snapshotOf`, `hydrateDurable`,
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
