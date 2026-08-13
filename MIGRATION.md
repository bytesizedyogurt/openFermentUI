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

## Phase log

| Phase | Description | Status | verify |
|---|---|---|---|
| 0 | Freeze, baseline, import map | [x] complete | green, 15 stages |
| 1 | Extract the schema | [ ] **blocked — see below** | |
| 2 | Extract the engine | [ ] not started | |
| 3 | The adapter seam | [ ] partial — seam exists, 4 collections outstanding | |
| 4 | Quarantine the simulation | [ ] partial — `src/sim/` already headed and fixture-exported | |
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
