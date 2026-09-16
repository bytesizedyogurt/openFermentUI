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
  (uv, FastAPI, Pydantic, `anthropic`). Model for every call is
  `claude-haiku-4-5-20251001`, forced tool choice, no agent loop.

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
  Do not edit `src/data/corpus/`, `PAPERS`, or `RECORDS`.
- The service supplies an **overlay** the store applies at load when
  `/api/health` answers (OF-BLD-012 §2.1). With the service down the app is
  exactly the seed. The overlay is AUTHORITATIVE: `candidates` and `runs` are
  a list or `null`, an empty list means the extractor produced nothing and the
  store drops what it had, and only `null` means "not supplied"
  (OF-BLD-012.1 F3). An undecided `haiku-1` record absent from an incoming
  list is removed; a decided one stays and is marked `absentFromRun`.
- **`pnpm verify` runs with no key, no service and no network, and must stay
  green.** Eighteen stages, in order: check:secrets → typecheck → check:plan →
  check:reference → test:core → check:seed → check:biorepo → check:anchors →
  check:overlay → check:lock → check:capture → build → test:durable →
  test:deposition → test:reconcile → test:smoke → test:golden → test:deep.
  Live tests are `pnpm test:live` and never in verify.
- `core/openferment_core/data/corpus.json` is generated by
  `pnpm export:corpus` and gitignored.

## Persistence tiers

- The **Durable** tier persists depositions, review decisions and runbook
  locks across a refresh (OF-BLD-006 §4.6: `snapshotOf`, `hydrateDurable`,
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
