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
| 2 | Extract the engine | [ ] not started | |
| 3 | The adapter seam | [x] complete — 0 seed imports in `src/screens/` | green, 15 stages |
| 4 | Quarantine the simulation | [ ] partial — `src/sim/` headed and fixture-exported; `SUGGESTED_PROMPTS` moved there in Phase 3 | |
| 5 | Server skeletons | [ ] not started | |
| 6 | Workspace hygiene | [ ] not started | |

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
