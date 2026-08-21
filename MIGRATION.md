# MIGRATION.md

Restructuring log for `openFermentUI`. One section per phase, each recording the
`pnpm verify` result that closed it.

This file opens with a correction, because the brief that commissioned it
describes an earlier repository. Six migration phases have already landed
(`git log 8722f9d..723c58d`), and they did a large part of what Phases 1-3 ask
for — by a different route, and in the opposite direction on one point that
matters. The measurements below are the evidence; the reconciliation is at the
bottom and needs a decision.

---

## Phase 0 — freeze and baseline

**Status:** complete. `pnpm verify` green at `723c58d`.

### The gate, as it actually stands

The brief describes six stages. There are fifteen:

```
typecheck -> check:seed -> check:corpus -> check:units -> check:protocol ->
check:metrics -> check:aggregation -> check:python -> check:types ->
check:answers -> check:biosteam -> build -> test:smoke -> test:golden -> test:deep
```

Nine of those are cross-implementation gates added by the earlier migration.
Each has been watched failing before being trusted; several exist because a gate
was found watching only one side of a two-sided thing.

### Inventory — the brief's table against measurement

| Area | Brief says | Actual | Why it moved |
|---|---|---|---|
| `src/data/` | ~13,500 | **3,900** | the corpus left TypeScript; it is `data/corpus/*.json` now |
| `src/screens/` | ~14,900 | **18,571** | |
| `src/components/` | ~2,800 | **5,609** | |
| `src/engine/` | ~900 | **5,901** | a bioSTEAM port (3,690 lines) landed here |
| `src/sim/` | ~700 | **2,557** | flowsheet definitions live here |
| `src/store.ts` | ~830 | **971** | |
| `packages/core/` | — | **8,143** | did not exist: Pydantic schema, unit engine, Postgres loader |
| `packages/assay/` | — | **1,267** | did not exist: Inspect AI scorer |

`src/engine/` is no longer "the most valuable code in the repo" in the sense the
brief means. Five of its modules are now MIRRORS of Python canon, each carrying a
header saying so and each held to a parity gate inside `pnpm verify`.

### The import map

Phase 0's real deliverable: it sizes Phase 3 before anyone commits to it.

**Totals across 23 screens, 44 import lines:**

| Kind | Count | Meaning |
|---|---|---|
| type-only | 21 | explicitly allowed by the brief's own exit condition |
| helper | 13 | `fieldName`, `ONTOLOGY_BY_ID`, `ONTOLOGY_GAPS`, `FAMILY_LABEL` — display logic, not seed data |
| adapter | 3 | already reads through `@/data/source` |
| **SEED** | **7** | **the actual remaining work** |

The brief estimates Phase 3 at "roughly 80% of the total effort". Measured, it is
**7 import lines across 6 screens**, touching four modules: `designs`, `flows`, `patents`, `runOutputs`.

The seam it asks for already exists — `src/data/source.ts`, with a `bundled`
backend and an `api` backend behind one synchronous surface — and the seven main
collections already go through it. Four collections do not.

#### The work that remains

| Screen | Module | Kind | Imported |
|---|---|---|---|
| `Ask.tsx` | `@/data/flows` | SEED | `SUGGESTED_PROMPTS` |
| `DesignDetail.tsx` | `@/data/designs` | SEED | `DESIGNS` |
| `Home.tsx` | `@/data/runOutputs` | SEED | `GOLD_SET_PLAN, GOLD_SET_DIFFICULTY_CASES` |
| `Home.tsx` | `@/data/designs` | SEED | `DESIGNS` |
| `Notary.tsx` | `@/data/designs` | SEED | `DESIGNS` |
| `Parchment.tsx` | `@/data/patents` | SEED | `PATENTS` |
| `Validation.tsx` | `@/data/runOutputs` | SEED | `GOLD_SET_PLAN, GOLD_SET_DIFFICULTY_CASES` |

#### Everything else, for completeness

| Screen | Module | Kind | Imported |
|---|---|---|---|
| `Ledger.tsx` | `@/data/source` | adapter | `ONTOLOGY` |
| `Settings.tsx` | `@/data/source` | adapter | `ONTOLOGY` |
| `StrainPage.tsx` | `@/data/source` | adapter | `ONTOLOGY` |
| `Ask.tsx` | `@/data/ontology` | helper | `fieldName` |
| `Ask.tsx` | `@/data/ontology` | helper | `ONTOLOGY_BY_ID` |
| `DesignDetail.tsx` | `@/data/ontology` | helper | `fieldName` |
| `Extract.tsx` | `@/data/ontology` | helper | `fieldName, ONTOLOGY_BY_ID` |
| `Ledger.tsx` | `@/data/ontology` | helper | `ONTOLOGY_BY_ID, ONTOLOGY_GAPS, FAMILY_LABEL, fieldName` |
| `OpenLab.tsx` | `@/data/ontology` | helper | `fieldName` |
| `PaperReader.tsx` | `@/data/ontology` | helper | `fieldName, ONTOLOGY_BY_ID` |
| `ProtocolDetail.tsx` | `@/data/ontology` | helper | `fieldName` |
| `Review.tsx` | `@/data/ontology` | helper | `ONTOLOGY_BY_ID, fieldName` |
| `Settings.tsx` | `@/data/ontology` | helper | `ONTOLOGY_BY_ID, fieldName` |
| `StrainPage.tsx` | `@/data/ontology` | helper | `ONTOLOGY_BY_ID, fieldName` |
| `Validation.tsx` | `@/data/ontology` | helper | `fieldName` |
| `Validation.tsx` | `@/data/ontology` | helper | `ONTOLOGY_GAPS` |
| `Ask.tsx` | `@/data/types` | type-only | `ChatMessage, ChatRetrievalHit, ChatToolCall` |
| `Compare.tsx` | `@/data/types` | type-only | `CostLine, Scenario` |
| `DesignDetail.tsx` | `@/data/types` | type-only | `DesignRecord, TierResult` |
| `Extract.tsx` | `@/data/types` | type-only | `ExtractionRecord, FieldId` |
| `Ingest.tsx` | `@/data/types` | type-only | `Job, Paper` |
| `Ledger.tsx` | `@/data/types` | type-only | `ExtractionRecord, FieldId, ParameterView` |
| `Lesson.tsx` | `@/data/types` | type-only | `CheckpointQuestion` |
| `Library.tsx` | `@/data/types` | type-only | `Job, Paper` |
| `Notary.tsx` | `@/data/types` | type-only | `DesignRecord, PublicationStatus` |
| `OpenLab.tsx` | `@/data/types` | type-only | `FieldId, ResultField, RunOutcome, RunState` |
| `Organisms.tsx` | `@/data/types` | type-only | `ExtractionRecord, Paper, Strain` |
| `PaperReader.tsx` | `@/data/types` | type-only | `Contradiction, ExtractionRecord, FieldId, Job, Paper` |
| `ProtocolDetail.tsx` | `@/data/types` | type-only | `ExtractionRecord, Protocol, ProtocolVersion, RunState, Step` |
| `ProtocolEditor.tsx` | `@/data/types` | type-only | `Material, ProtocolVersion, ScalingClass, Step` |
| `Protocols.tsx` | `@/data/types` | type-only | `ExtractionRecord, Protocol, ProtocolCategory, ProtocolVersion, Strain` |
| `Review.tsx` | `@/data/types` | type-only | `ExtractionRecord` |
| `RunMode.tsx` | `@/data/types` | type-only | `Step` |
| `ScenarioWorkspace.tsx` | `@/data/types` | type-only | `CostLine` |
| `Settings.tsx` | `@/data/types` | type-only | `FieldId, ParameterDef` |
| `StrainPage.tsx` | `@/data/types` | type-only | `ExtractionRecord, FieldId, ParameterDef, Protocol, Scenario` |
| `Validation.tsx` | `@/data/types` | type-only | `ExtractionRecord, ExtractorRun, FieldId, RunOutput` |

---

## Phase 3 — the last seven seed imports

**Status:** complete. `pnpm verify` green, all fifteen stages, 53 routes / 48
golden / 44 deep.

The seven SEED import lines Phase 0 measured are gone. Nothing was routed by
convenience: the four modules landed behind four different answers, because the
adapter a collection sits behind is a claim about which server will serve it.

| Module | Landed on | Why |
|---|---|---|
| `PATENTS` | `CorpusAdapter.listPatents` — BioRepo | Catalogued literature that carries claims, keyed by `paperId` to H17a–f. `getScope` already read the same six. Parchment is the SCREEN; naming an adapter after the page that draws it turns a UI layout into an architecture. Not the Guild — a patent is not an attestation a chapter issued. |
| `DESIGNS` | `ProcessAdapter.listDesigns` / `getDesign` — fermOS | A design is the OUTPUT of the tier cascade, and three of its four tiers are Python (COBRApy, BioSTEAM twice). The client can sweep it today only because T1 and T2 are absent and T3 is a grid interpolation. Derived-at-module-scope is what a fixture looks like, not what the thing is. No new methods were needed, which is the seam being right already. |
| `GOLD_SET_PLAN`, `GOLD_SET_DIFFICULTY_CASES` | `CorpusAdapter.getGoldSetPlan` — BioRepo | Audit owns the SCORE, not the SET. Every plan field is a corpus coordinate and one row's `blocked` is a fact about `ONTOLOGY_GAPS` a scorer holding no ontology could not evaluate; when annotation happens the rows become `provenance: 'gold'` records in the same store. `RUN_OUTPUTS` goes the other way — a scorer's output, Audit's whenever that seam is built. They share a file because one screen renders both. |
| `SUGGESTED_PROMPTS` | `src/sim/prompts.ts` — the agent seam | Not corpus and not a server's. Each chip is one flow TRIGGER verbatim so a click is an exact match — a property of the scripted matcher, which retires with it. Moved next to the thing that needs it, headed for `AgentAdapter.suggestedPrompts()` in the phase that quarantines `src/sim/`. Building that adapter now, with `send`/`sendFlow` still going around it, would be a seam that lied about what passed through it. |

`src/data/source.ts` was deliberately NOT extended. None of the four is a
JSON-backed corpus collection: there is no `data/corpus/patents.json`, the
exporter maps seven keys to seven Pydantic models, and that module's whole
contract is that its collections come from the exporter and are fetchable at
`${API_BASE}/<name>.json`. An eighth array with no file behind it and no `api`
path would be a lie in the most-copied place in the data layer. `Patent` does
have a Pydantic model (`schema/design.py`); when it is exported, `listPatents`
reads it through `@/data/source` like the rest and nothing above changes.

### Loading states — the real work

The adapter surface is async by contract, so six screens gained three states
where they had one. Two of those screens were rendering a FALSE SENTENCE on the
first frame, not a blank:

- `DesignDetail` answered "Design not found" for any unresolved id, and every
  design's first frame is an unresolved id. `loading` and `null` are now
  different branches; the not-found branch is still reachable and still tested.
- `Notary`'s callout reads "N of M designs are publishable"; `0 of 0` is a
  finding about the corpus when it is a fact about a promise. It gates.

`Home` does not gate — its two reads feed counts inside two tiles, and an
unarrived count renders as `—` rather than `0`. `Validation` folded the read
into the `delayClass('quick')` skeleton it already had. `Ask` gained nothing:
its prompts never leave the client.

This was checked rather than assumed. A frame audit recorded every DOM mutation
from before the bundle evaluated until 2 s after load and asserted the false
sentences appear in NO frame — not merely in the settled one the 500 ms waits in
`test:golden` observe. Separately, the rendered text of all nine affected routes
is byte-identical before and after, with zero console errors.

### Exit condition

`grep -r "from '@/data/" src/screens/` returns 37 lines: 21 type-only, 13
display helpers from `@/data/ontology` (`fieldName`, `ONTOLOGY_BY_ID`,
`ONTOLOGY_GAPS`, `FAMILY_LABEL` — id-to-label lookups, not seed data), and 3
`ONTOLOGY` reads that already go through `@/data/source`. All three categories
are the ones the brief's own exit condition and Phase 0's import map allow.
**SEED: 0.** Each surviving helper import is annotated in place so the next
reader does not read it as one that was missed.

---

## Phase log

| Phase | Description | Status | verify |
|---|---|---|---|
| 0 | Freeze, baseline, import map | [x] complete | green, 15 stages |
| 1 | Extract the schema | [ ] **blocked — see below** | |
| 2 | Extract the engine | [x] complete, reshaped — see Phase 2 section | green, 17 stages |
| 3 | The adapter seam | [x] complete — 0 seed imports in `src/screens/` | green, 15 stages |
| 4 | Quarantine the simulation | [x] complete, reshaped — see Phase 4 section | green, 19 stages |
| 5 | Server skeletons | [x] complete — see Phase 5 section | green, 20 stages |
| 6 | Workspace hygiene | [x] complete, one item declined — see Phase 6 section | green, 20 stages |

---

## Where the brief and the repository disagree

Four conflicts. The first needs a decision before Phase 1 can start; the rest
have a recommended resolution and can proceed on it.

### 1. Which language owns the schema — BLOCKING

The brief, Phase 1: create `packages/schema/` in TypeScript, with Zod as the
runtime contract. Phase 5: "generate Pydantic models from the Zod schemas".

The repository does exactly the reverse, and `CLAUDE.md` — committed at the top
of this repo — states it as the one rule:

> Anything that must be callable by BioSTEAM, COBRApy, PaperQA2, Inspect AI, or
> the extraction pipeline **must be Python**. [...] Do not hand-maintain a type
> in both Python and TypeScript. Generate one from the other.

`packages/core/openferment_core/schema/` holds the Pydantic models;
`src/data/types.ts` is GENERATED from them and `check:types` fails if it drifts.
The Postgres DDL is derived from the same models, and `packages/assay` imports
them.

Reversing the direction would orphan all three. **Recommendation:** keep Pydantic
canonical and GENERATE the Zod validators from it, exactly as `types.ts` is
generated. `packages/schema` then exists with the interface Phase 1 wants,
Phase 5's Pydantic models are already there, and nothing is hand-maintained
twice. This needs confirmation because it inverts the brief.

### 2. `Provenance` means something else here

The brief replaces `Provenance` with a three-variant discriminated union
(`accession` / `computation` / `assumption`) as the Rule 1 write-path gate.

The repository's `Provenance` is an eight-member enum — `gold`, `verified`,
`curated`, `unverified`, `user`, `industry-estimate`, `demo`, `unsourced` —
pinned by `CLAUDE.md` invariant 3, load-bearing across the tick system, the
aggregation gate, `check:seed`, and all 134 records. It answers *how far has this
been checked*.

The brief's schema answers a different question: *what justifies writing this
number*. **Recommendation:** they are orthogonal and both should exist. Add the
brief's schema under its own name for write paths; leave `Provenance` alone.
Replacing it would change what every record in the corpus means.

### 3. Phase 2's module list is out of date

`retrieval.ts` was deleted, deliberately — PaperQA2 is the retrieval layer, which
is what the brief's own table says ("the corpus server replaces it"). No action.

`units.ts`, `scale.ts`, `diff.ts` and `metrics.ts` can move to `packages/engine`,
but they are mirrors: their headers and their parity gates must move with them,
or `pnpm verify` loses four of its fifteen stages.

### 4. Branch and tag names

The brief asks for `git tag v0.1-sim` and a `restructure/monorepo` branch. This
session is constrained to `claude/openferment-design-sim-99drgg` and may not push
elsewhere without explicit permission. `v0.1-sim` also names a state six phases
back — `8722f9d` is the closest commit. Both need a go-ahead.

---

## Phase 3 — the adapter seam

**Status:** complete. `pnpm verify` green, fifteen stages.

### Exit condition

The brief's own wording: `grep -r "from '@/data/" src/screens/` returns nothing
except type imports. It now returns type imports, plus `@/data/ontology` display
helpers (`fieldName`, `ONTOLOGY_BY_ID`, `ONTOLOGY_GAPS`, `FAMILY_LABEL`) and
`@/data/source`, the adapter itself. **Zero direct seed imports remain.**

The helpers are left deliberately and said so where they sit: they are display
logic over the ontology, not seed data, and pushing them into a data adapter
would put UI formatting behind a server boundary.

### The five interfaces

`src/adapters/` — `types.ts`, a `fixture/` backend, `mcp/` stubs that throw
`NotImplemented`, and an `index.ts` selecting on `VITE_ADAPTER_BACKEND`
(defaulting to fixture, and forced to fixture under Node).

Every method is async, including the ones the fixture answers from an array it
already holds — a synchronous interface cannot grow latency later without
touching every caller. Every response is
`{ data, serverVersion, corpusSnapshotId, modelVersion?, notice? }`.
`corpusSnapshotId` is an FNV-1a digest **of the corpus itself**, not a constant,
so it changes when the corpus does and a trace recorded today stays replayable.

Expensive tiers are asynchronous as required: `submitEvaluation` returns a
handle and `getEvaluation` collects it. The fixture completes before it returns
and issues the handle anyway — the shape is what is being fixed now, not a
simulation of slowness. `jobRunner()` is the one synchronous method, reusing the
`JobRunner` from `src/sim/jobs.ts`, because it is called from a
`requestAnimationFrame` loop.

### Where the four remaining collections landed, and why

Routing is a claim about which server will serve a thing, so each was decided on
its own terms rather than swept into the corpus adapter:

| Module | Landed | Reasoning |
|---|---|---|
| `patents` | **CorpusAdapter** | prior-art literature; `SourceType` already has a `patent` member |
| `runOutputs` | **CorpusAdapter** | the gold-set plan describes corpus records. `RUN_OUTPUTS` stays empty |
| `designs` | **ProcessAdapter** | `designs.ts` says it outright — *"Derived at load from the authored cost models, never seeded"*. A computed sweep is something fermOS produces, not something a corpus server stores |
| `flows` (`SUGGESTED_PROMPTS`) | **`src/sim/prompts.ts`** | never corpus data. Each string is a flow's trigger verbatim, and the exact-match guarantee it exists to provide dies with the scripted agent, so it retires with it rather than being carried across a server boundary |

### Two absences that are disclosed rather than silent

`getScope` and `getWhitespace` are new and return `[]` under fixture. Both carry
a `notice` in the same object as the payload, following the rule
`CorpusSearchResult.method` already set:

- `getScope` genuinely runs `inScope` over all six patents and finds nothing,
  because every claim carries `bounds: []`. *"An empty result here means the
  question could not be asked — not that the configuration is unencumbered."*
- `getWhitespace` runs nothing at all. The computed answer from zero parsed
  claims would be "the entire parameter space is unclaimed", which is the most
  commercially dangerous sentence the system could emit and it would arrive with
  the authority of a computation. *"The empty array is a stub, not a finding."*

---

## Phase 2 — extract the engine (reshaped)

**Status:** complete. `pnpm verify` green, seventeen stages.

### Why the file movement did not happen

The brief's rationale for moving `src/engine/` into `packages/engine/` is that
it is "directly reusable by the production subsystems. `units.ts` in particular
becomes Intake's normalisation layer." That goal was met by the earlier
migration, in the other language: the production normalisation layer is
`openferment_core.units` (Python, `packages/core`), with `protocol/scale`,
`protocol/diff` and the `packages/assay` metrics scorer beside it. The
TypeScript copies of those four are MIRRORS — browser-only, headed as such, held
to parity gates inside `verify` — and CLAUDE.md's one rule forbids offering them
for reuse by anything a production subsystem calls. Moving mirrors into a
package named for reuse would invite exactly the second-implementation coupling
the rule exists to prevent.

`interp.ts` and `grids.ts` are the two modules that are legitimately TypeScript
forever (CLAUDE.md routing table: "Grid interpolation for sliders — legitimate
UI convenience, stays"). They move into a JS package the day a second JS
consumer exists (`packages/client`, Phase 6 workspaces); today the only consumer
is the app, and a package with one tenant is filing with alias machinery as its
only content. `retrieval.ts`, the sixth module on the brief's list, was deleted
in the earlier migration — the brief's own table agrees ("the corpus server
replaces it").

What Phase 2 is FOR — an engine that stays pure and numerics other systems can
trust — is enforced instead of arranged:

### `check:purity` — the brief's purity rule, mechanical

No runtime import of `@/store`, React/zustand, or `@/data/*` anywhere under
`src/engine/` (28 modules scanned; type-only imports allowed, the same
distinction the brief's Phase 3 exit condition makes). Three pre-existing
`@/data/ontology` imports (`designs`, `balance`, `posterior` — none of them on
the brief's six) are carried as an explicit allowlist with reasons; a NEW
violation fails, and a RESOLVED entry left unpruned also fails, so the ledger
stays exact. Proved in both directions before being trusted.

### `check:interp` — the pin the brief's tests asked for

`units.convert` was already pinned harder than any unit test: 1,632 convert
cases plus 600 cross-family refusals in `fixtures/units.json`, replayed against
BOTH implementations on every verify. `interp.interpolate` had **no pin at
all** — the Phase 0 capture never recorded it, and every number a slider shows
between two solved points passes through it.

It is now pinned by 3,863 property checks against the live cost-model grids, no
remembered constants: node exactness, per-axis midpoint linearity, clamping
(including absent-keys-clamp-low), the waterfall identity (Σ cost lines = MSP)
surviving interpolation at 200 seeded interior points per model, and a sample of
nodes re-solved through `model.evaluate()` so the grid is tied to the plant
rather than to itself. A 0.1% perturbation of one corner weight trips 3,215 of
them.

---

## Phase 4 — quarantine the simulation (reshaped)

**Status:** complete. `pnpm verify` green, nineteen stages.

### The AgentAdapter

The brief moves `src/sim/` under `packages/client/.../fixture/agent/`. There is
no `packages/client`, and a physical move would also mislabel what lives there:
`src/sim/flowsheets/` is the REAL bioSTEAM plant definition (its header says
"NOT SIMULATION — NOT DELETED WITH THE REST OF sim/"), and `src/sim/jobs.ts` is
the job-pacing seam, not agent content. So the quarantine is by seam rather
than by directory: `src/sim/` stays where its headers and removal notes are,
and the ONLY path a screen reaches the scripted agent by is now
`adapters.agent` — the sixth interface, beside the five from Phase 3.

The interface is two methods, because that is the true surface `Ask.tsx` used:
`send(sessionId, input)` and `sendFlow(sessionId, flowId, label)`. The
conversation itself streams through the store — that is how a turn renders in
progress — and the response carries only what the caller must act on
immediately (slash-command handling, a scope change). Every fixture turn is
stamped `modelVersion: 'sim-scripted-flows'`, so a trace of the scripted player
cannot be mistaken for a model run. `sendFlow` is scripted-clarify vocabulary
and is kept deliberately: it retires with `src/sim/`, and the MCP stub for it
says so.

`SUGGESTED_PROMPTS` stays a direct sim import in `Ask.tsx`, commented at the
site: each chip is a flow trigger verbatim (a click is an exact match), which is
a guarantee only the scripted player can offer. The chips retire with it rather
than crossing a boundary the real agent will never serve them over.

### The flows as Audit's seed corpus

`packages/assay/fixtures/flows.json` — all 13 ChatFlows, exported by
`capture:eval-flows` and held current by `check:evals` inside verify. This is
the eval-side sibling of `fixtures/answer-shapes.json`: answer-shapes is the
formatter contract (shape, not prose); flows.json keeps the prose, because an
eval needs the expected answer, the expected retrieval set, and the expected
tool sequence per question.

They land in `packages/assay/` rather than the brief's `packages/evals/`
because assay IS the Audit package — the Inspect AI scorer lives there, and a
second eval home would split the thing these fixtures feed. **Deviation,
recorded.**

On the way out every flow passes through the Pydantic `ChatFlow` model and must
round-trip unchanged — their first contact with the schema anywhere, and all 13
survived it. Export is byte-stable; hand-editing the fixture fails `check:evals`
with a note that a change here is a change to what counts as a right answer.

---

## Phase 5 — server skeletons

**Status:** complete. `pnpm verify` green at 20 stages.

Five MCP servers under `servers/`, one per subsystem, each the server-side half
of one interface in `src/adapters/types.ts`. Full detail is in
`servers/README.md`; this section records what the phase changed elsewhere and
what it found.

### What was found before anything was written

Two servers (`process`, `guild`) already existed on disk from an earlier,
interrupted attempt. Both were good, and both were checked rather than
inherited:

- **`process`'s smoke client had never run to completion.** Line 48 read
  `init.serverInfo`, which is the wire alias; the Python attribute is
  `server_info`. The server itself was fine — the handshake completed before
  the client crashed on the response — but the transcript that was supposed to
  prove it could not have been produced. Fixed the client.
- **The two servers disagreed about what a `corpusSnapshotId` is.** `process`
  framed `name \0 bytes` under a `corpus-` prefix; `guild` framed `name : bytes`
  under `sha256:`. Two servers reading the same file would have reported
  different ids — while `guild`'s own docstring promised that reading the same
  files yields the same id. A snapshot id whose meaning depends on which server
  minted it is barely better than the constant it must never be.

### What moved into `openferment_core`

Three modules, each because more than one server needs them to agree:

- **`snapshot.py`** — one framing for `corpusSnapshotId`: names sorted, each
  entry `name \0 length \0 bytes`, `sha256:` and 16 hex characters. The length
  prefix closes an ambiguity a `name \0 bytes` framing has, where a file named
  `a` holding `b \0 c` and one named `a \0 b` holding `c` digest identically.
  `servers/guild/src/meta.ts` is now a declared MIRROR of it, gated.
- **`corpus.py`** — the collection→model map (lifted out of the exporter, which
  now imports it, so the exporter and every server read the same page), a
  `CorpusReader` that mints the id for exactly the bytes it opened, and
  `records_attributed_to`.
- **`serving.py`** — the `AdapterResponse` envelope, so four Python servers
  cannot answer in four slightly different shapes.

`records_attributed_to` is the one that changes an existing decision.
"Which records count for a strain" already existed twice — in
`src/adapters/fixture/cell.ts` and in `src/screens/Organisms.tsx` — and the
fixture's own comment says the rule is server-side work and names its own
retirement. Writing a third copy in the `cell` server would have been a
cross-language twin, so Python became canonical and the copies are now held to
it by a gate.

### The new gate: `check:servers`

Five checks, each watched failing before being trusted:

| Check | Broken by | Reported |
|---|---|---|
| manifest ↔ server | renaming `list_strains` in `cell`'s manifest | both directions — the undeclared tool AND the phantom one |
| snapshot parity | dropping the length prefix from the TypeScript half | 3 of 6 cases diverge, and the adversarial pair collides |
| cost model derivation | appending a value to one axis in `scenarios.json` | derivation no longer equals `COST_MODELS` |
| attribution parity | disabling the untagged-record clause | per strain, with the first divergent record id |
| status vocabulary | setting one tool's status to `stub` | names the offending tool and the three legal values |

The status vocabulary is checked because it had already drifted: `process`
said `stub` where the other four said `declared-refuses` for identical
behaviour, and an operator reading five manifests should not have to work out
whether those are the same thing.

Two of the five also check that agreement is not vacuous: the snapshot ids must
be DISTINCT across inputs (two halves both returning a constant would agree
perfectly), and the attribution must be non-empty (a rule attributing nothing
to anything agrees trivially).

It deliberately does not start the servers. That needs five virtualenvs and a
node install, which is a CI job rather than a `pnpm verify` stage — so each
README carries the transcript its smoke client actually produced and a
**PROVEN vs written** section separating what was watched from what was not.

### Language split, and the one exception

Four Python, one TypeScript. Every server that serves an ENTITY is Python,
because every entity has a canonical Pydantic model and a server must validate
what it serves through the same model the exporter wrote it with. The brief's
original split put `corpus` in TypeScript; it was moved, because BioRepo serves
`Paper` and `ExtractionRecord` and a TypeScript server would need either a
hand-maintained validator or none. **Deviation, recorded.**

The Guild stays TypeScript because it has nothing to validate: `GuildChapter`
and `Seal` have no Pydantic model, deliberately. It pays for that — it cannot
detect a corpus file the schema would reject, so its health tool reports
`ok: false` rather than refusing to start, and it serves only a thin projection
of the one file it reads. Both facts are in its README.

### Deliberate absences, extended

The brief names one: no Notary tool that publishes. Four more were added, each
by the same test — would an unattended call produce something carrying
authority nobody granted?

- no `write_record` (BioRepo) — it would write a claim about a real publication
  into the store the Ledger and every aggregate read from;
- no cost-model authoring (Proforma) — widening an axis moves a headline number
  without touching a datum, and looks like arithmetic;
- no strain registration (geneOS) — it would let a BSL be asserted rather than
  assessed;
- no seal minting (Guild) — already refused by the fixture; here the tool is
  simply not offered, which is the stronger statement.

### Proven

All five servers were started and driven over real stdio: 26 tools registered
across the five, every real tool answering from `data/corpus/*.json`, every
declared refusal refusing with a message naming what is missing, and every miss
carrying a notice that says which kind of empty it is. `process` and
`economics` both read only `scenarios.json` and both report
`sha256:a942d5c30fed7fba` — the agreement the shared framing exists for, and
the thing that was not true before this phase.

---

## Phase 6 — workspace hygiene

**Status:** complete, one item declined. `pnpm verify` green at 20 stages.

- **`.github/workflows/verify.yml`** — CI running the full gate on push and PR.
  It installs `packages/core[dev]` then `packages/assay[dev]`, and installs
  `inspect-ai` explicitly, because `packages/assay/tests/test_scorer.py` opens
  with `pytest.importorskip("inspect_ai")` — without it the scorer suite would
  skip silently and CI would report green over less than it appears to cover.
- **`CONTRIBUTING.md`** — the one gate, the generated-from relationships as a
  table, the absolute prohibitions, and where new work goes.
- **`LICENSE`** — a deliberate placeholder naming the requirement (copyleft
  with no enclosure) rather than guessing at a licence. It states plainly that
  until one is committed, default copyright applies.
- **`.gitignore`** — `servers/*/.venv/`.

### `pnpm-workspace.yaml` — declined, with a reason

The brief asks for one. Adding it here would be a file that does nothing at
best and breaks a deployable at worst.

`packages/core` and `packages/assay` are Python and a pnpm workspace cannot
hold them. That leaves `servers/guild`, the one npm package outside the root —
and it is deliberately standalone: its `Dockerfile` runs `npm ci` against its
own lockfile so the image builds without the UI's dependency graph. Enrolling
it in a pnpm workspace would delete that lockfile and break its build for the
sake of deduplicating `typescript` in a dev tree. A workspace file listing only
the root package would declare nothing.

The hygiene the brief wanted from it — one place that says what each package is
and how it is installed — is `servers/README.md` and `CONTRIBUTING.md`.
**Deviation, recorded.**

### Turborepo — not added

Optional in the brief. `pnpm verify` is a linear chain of gates whose whole
value is that it runs in a fixed order and stops at the first failure; a task
graph that parallelised it would trade that for wall-clock on a chain that
takes well under two minutes.

---

## OF-DEMO-001 — the demo suite

A second brief, commissioning a parallel demo pool: six query archetypes over one
shared object pool, alongside the casein corpus rather than inside it. Steps 1–3
of its §3 build order are complete and gated; the screens are not built yet.

### The brief describes an earlier repository, again

Same as OF-FE-003 before it. Measured, not assumed:

| Brief says | Repository is |
|---|---|
| §7: migrate `library→intake`, `extract→repo`, `organisms→geneos`, … | Already migrated, at `src/App.tsx:107` — but to `trawl` and `ledger`, not `intake` and `repo` |
| Routes are `library, extract, organisms, simulate, ask, protocols` | Those are permanent aliases; the canonical set is `trawl, ledger, geneos, fermos, postdoc, runbook, assay, notary, parchment, openlab, learn, settings` |
| §6: "a directory under `parts/`" | No `src/parts/`. The tree is `screens/ components/ engine/ lib/ data/ adapters/ sim/` |
| §3 Step 1: "`types-demo.ts` … imports `Provenance`, which it widens" | The file imports nothing and declares its own 11-member union. The prose and the file disagree; the file is right |

`/notary`, `/geneos`, `/fermos`, `/ledger` and `/assay` already exist and render
the casein build. The demo routes in OF-DEMO-002 §2 will have to land beside
them rather than found them.

### Where the demo pool lives, and why not where the brief said

`src/data/demo/`, not `src/data/`. Both modules export a type called
`Provenance` and they are NOT the same type — the corpus one is GENERATED from
the Pydantic models and has eight members, the demo one has eleven. Side by side
in one directory, a wrong import compiles to a silently different union. The
directory boundary makes them impossible to confuse, and it serves the brief's
own §8: "do not merge the two object pools." **Deviation, recorded.**

Nothing in `src/data/demo/` is generated and nothing in it may be, because no
entity there has a Pydantic model yet. If a server ever produces one, that model
becomes canonical and the TypeScript is generated from it, exactly as
`types.generated.ts` is. The repo rails apply to this pool too.

### The fabricated-identifier conflict, and how it is resolved

CLAUDE.md invariant 2 forbids fabricated data and names DOIs, years, authors and
venues. OF-DEMO-001 §2.1 requires exactly those to be synthetic. That is a real
conflict and it is resolved by making the synthesis **provable rather than
promised**:

- Every DOI in the pool is under `10.9999`, a prefix no registration agency has
  issued, so no string here can resolve to a real article.
- Every patent number is in a series that cannot have been granted — `US 2029/…`,
  `EP 4 9xx xxx`, `WO 2028/…`.
- Every id carries a demo-pool prefix (`OF-A-`, `PF-`, `SRC-`), so a demo object
  can never be mistaken for a corpus object.
- `SEED_DISCLAIMER` must be long and must actually say "synthetic" and "patent".

All four are checked by `check:demo-seed` and all four were watched failing: a
`10.1016` DOI, a `US 2019/…` number, and a vague-but-long disclaimer are each
rejected by name. The invariant's concern is fabricated claims wearing the face
of real literature; identifiers that are impossible by construction and
mechanically held that way are the opposite of that.

### What Steps 1–3 found

**Six of 134 Accessions were passing a check that asked them nothing.**
`verifyNormalisation` handled `molar-to-mass` and the pH case by writing
`computed = acc.normalized.value`, which makes the comparison true by
construction. A perturbation sweep — nudge each authored normalisation by 1 %
in turn and count what the checker catches — reported 128 of 134. The brief is
explicit on this point ("Do not trust the authored normalisation; verify it in
code"), so the arithmetic those two branches state in prose is now typed
(`DerivationParams`), the species are named rather than inlined so a molar mass
lives in one place, and the sweep reports 134 of 134.

**Six rows of OF-DEMO-003 §3 were not being recomputed** although its §7 requires
every row to be. C\*, the de-rated peak OUR, the cooling duty and headroom, the
RUN-047 O₂ deficit and closure gap, and the capex anchor are now all replayed
and all land within 1 % of the stated value.

**The provided `assertCoreIntegrity` and seed check are not vacuous** — nudging
the van 't Riet constant by 1 % and breaking one accession reference were both
caught by name.

### Deviation: a separate check script

§6 says to add the acceptance criteria to `scripts/check-seed.ts`. They are in
`scripts/check-demo-seed.ts` instead, wired into `pnpm verify` beside it. One
script asserting over both pools would be the merge §8 forbids, in the one place
where the two would be hardest to tell apart. **Deviation, recorded.**

### Steps 4–10 — the screens

Complete. Ten components and thirteen screens across twenty-three new routes,
all rendering under `scripts/smoke.mjs` (76/76 clean, up from 53).

| Route | Archetype | What it must show |
|---|---|---|
| `/bench` | — | six cards, each the archetype's QUESTION rather than its name |
| `/repo`, `/repo/a/:id`, `/repo/p/:field`, `/repo/contradictions` | — | the atom, and the company it keeps |
| `/fermos/gap/:id` (+ `/f/:factor`) | 1 | the unexplored region as the subject, not the leftover |
| `/geneos/routes/:product` (+ `/:route`) | 2 | the ranking reversing under the claim overlay |
| `/proforma/screen/:plant` (+ `/c/:candidate`) | 3 | failed candidates IN the table, binding axis named |
| `/proforma/concept/:id` | 4 | the accuracy band drawn, not footnoted |
| `/postdoc/tree/:id` | 5 | patent density as a pre-verbal four-step scale |
| `/fermos/runs/:runId`, `/fermos/envelope/:plantId` | 6 | the excursion band across every channel at once |
| `/notary/disclosures` | all | the queue that makes the project's reason legible |

Routing decisions, both to keep the pools apart:

- The demo Notary queue is at `/notary/disclosures`; `/notary` stays the casein
  enablement checklist. A screen serving both pools would be the merge §8
  forbids, in the one place it would be hardest to notice.
- `/geneos/routes/...` is matched BEFORE the bare-segment strain branch, or
  `/geneos/routes/3-HP` renders a chassis page for a strain called "routes".

### What building the screens found

**`OF-A-00307` was a computed value citing nothing.** Its note named its two
inputs — P/V = 1500 W m⁻³ and vs = 0.049 m s⁻¹ — in prose, and prose is not a
citation. Rule 1 says no number renders unless it traces to an Accession or to a
computation over Accessions; a computation over two numbers that are not
Accessions does not satisfy it. Both are now Accessions (`OF-A-00327`,
`OF-A-00328`), which also makes the seam-matrix row calling for a two-deep
derivation chain true rather than nearly true. A `superficial_gas_velocity`
field was added for the second, because it had been living inside a note.

**Contradictions 2 and 3 were not wired.** All four are documented in
OF-DEMO-003 §5 as deliberate, but only the first carried `conflictsWith`, so
only one rail rendered. Contradiction 3 needed a NEW relation rather than the
existing one: it is the case where normalisation CLOSES an apparent
disagreement, and filing it under `conflictsWith` would make the interface cry
wolf about its own success. `reconciledWith` renders in `signal-open` beside the
warn-coloured unresolved block. All four are now gated, including the fourth,
which must NOT render — and the gate catches each failure mode by name.

**The capacity screen could not compute an import displacement**, and says so.
`min(capacity, volume) × (CIF − landed cost)` needs a landed cost this pool does
not hold for those candidates. The column shows the volume and the CIF price —
the two quantities that exist — and the note names the missing one. A number
computed from an invented landed cost would have been the most quotable thing on
the screen and the least defensible.

**A single-source exclusion states its flag AND lists its Accessions**, so the
band's warning triangle and the ids beside it can disagree. They are now checked
against each other, along with every exclusion falling inside its domain and
every factor having a non-empty unexplored gap — a factor with none has no
finding to show on the screen that exists to show it.

**Two of my own checks were wrong before the data was.** The seam-9 check read
`RunRecord.verdict`, which is optional and unset in this seed, so it would have
passed silently on `undefined`; the verdict lives on the deliverable payload. And
a "watching nothing" guard in the honesty section caught my own wrong field name
on `PatentFamily` before it could report a vacuous pass.

### The agent layer

The six archetype flows were shipped in the package and wired to nothing —
`ARCHETYPE_FLOWS` had no importer. They now share one matcher with the thirteen
casein flows, as a SEPARATE array concatenated at the point of use rather than
merged into `FLOWS`: one array would make a casein flow and an archetype flow
indistinguishable to everything downstream, including the eval fixture exporter,
which must not start scoring one against the other's expectations.

Three additions, each the smallest thing that made the contract real:

- **`[[chip]]` resolution dispatches by PREFIX** to a demo resolver. The demo
  flows cite `[[OF-A-00147]]`, `[[PF-003]]`, `[[RUN-047]]`; without this they
  rendered as paper chips pointing at papers that do not exist. Prefix rather
  than lookup order, because a chip falling through from one pool to the other
  would be the merge §8 forbids, happening at render time where nobody would see
  it. An id matching a demo prefix and resolving to nothing renders as a visible
  fault.
- **`deliverableId` becomes the first follow-up chip**, navigating to the
  rendered artifact instead of asking another question. That is the reason the
  field exists: a ranked table with eleven columns squeezed into a chat bubble is
  a screenshot of a screen, and the screen is right there.
- **`handoffs` follow it**, so Archetype 5 terminates by spawning route
  comparisons rather than by concluding.

The gate now checks that no trigger is claimed by two flows across BOTH pools —
a shared trigger means the matcher answers by array order, and array order is not
a product decision anybody made. Watched failing by giving an archetype flow a
real casein trigger; it names both flows.

### The rail

The demo suite gets its own group rather than three entries scattered among the
casein ones. The rail is the first place a reader forms a mental model of what
this system holds, and interleaving them would say the two pools are one corpus.
`f` is Proforma as the brief asks; `y` was already Notary and the demo queue is a
sub-path of it, so it needs no key of its own.

### Density — deviation

§5 says to default the demo routes to dense. Density is a global `⇧D` toggle, and
flipping it on navigation would fight the user's own setting and surprise them on
the way back out. The dense row is applied where the brief's reason applies —
the capacity table, which is the screen with eleven columns — and the global
toggle is left alone. **Deviation, recorded.**

### The demo home, and the upstream notes

**`/bench` leads with the agent.** It was a grid of six deliverable cards, which
is a menu of ANSWERS and gets the demo backwards — the thing being shown is not
six artifacts, it is a system you can ask a question. The composer is now first,
the six archetypes are PROMPTS that run rather than links that navigate, and each
still offers "skip to the deliverable" for a reviewer who has already watched the
flow play once.

**`src/data/demo/upstream.ts` names what each part will be derived from**, and
`UpstreamNote` renders it from the app shell rather than from each screen —
twenty-six screens each carrying their own sentence is twenty-six sentences that
drift, and one of them would be the one nobody updated. Driven off the route, so
a new screen under an existing part inherits the note.

The `status` field is the substance, not decoration. It is very easy to write a
slide saying "powered by AlphaFold" about software that has never called
AlphaFold, and three values keep that from happening by accident:

| status | means | who has it |
|---|---|---|
| `ported` | code from that project is in this repository now | BioSTEAM, Pydantic, Inspect AI, Postgres, MCP |
| `named` | the decision is recorded in CLAUDE.md, a manifest or a docstring; nothing calls it yet | PaperQA2, COBRApy, Escher, ThermoSTEAM, ORCID, in-toto |
| `candidate` | an obvious fit nobody has committed to | AlphaFold (geneOS) |

Parts with no decided upstream — Parchment, Primer — say so rather than
borrowing a famous name, and every entry states WHERE the decision is recorded
so a reader can check it. Several notes carry an `openQuestion` that is more
useful than the dependency list: Proforma's says the economics server refuses
`solve_plant`, and Postdoc's says the model is deliberately unnamed because Rule
1 means no number in an answer may come from weights either way.

