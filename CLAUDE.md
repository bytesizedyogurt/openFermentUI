# openFerment — repo rails

## What this repo is

`openFermentUI` is the front-end simulation of openFerment (OF-DES-001), built
against the corpus in `docs/OF-COR-001.md`. It is currently ALSO holding the
canonical schema, the unit engine, and the corpus data. Those three are being
migrated out to Python. That migration is in progress.

## The one rule

Anything that must be callable by BioSTEAM, COBRApy, PaperQA2, Inspect AI, or
the extraction pipeline **must be Python**. Those are all Python-only. A second
implementation in TypeScript that must agree with the Python one is the failure
mode this migration exists to prevent.

## Where things belong

| Concern | Language | Home |
|---|---|---|
| Entity schema (`Provenance`, `FieldId`, `Paper`, `ExtractionRecord`, …) | Python | `openferment-core` → generated to TS |
| Unit conversion, dimensional analysis, refusals | Python | `openferment-core` → golden-fixture cross-check in TS |
| Extraction metrics / gold-set scoring | Python | Inspect AI scorer |
| Corpus retrieval | Python | PaperQA2 — do not reimplement |
| Protocol scaling math | Python | drives physical lab work |
| Protocol version diff | Python | Ledger concern, must run server-side |
| Cost model authoring | Python | BioSTEAM |
| Grid interpolation for sliders | TypeScript | legitimate UI convenience, stays |
| Screens, components, routing, store | TypeScript | stays, do not touch |

## Invariants that must never break

1. `pnpm verify` passes green at the end of every phase. It is the regression
   harness for this entire migration. It runs: typecheck → check:seed → build →
   test:smoke → test:golden → test:deep.
2. No fabricated data. `RUN_OUTPUTS` stays empty until a real extractor runs.
   Never invent P/R/F1, DOIs, years, authors, or venues.
3. Provenance semantics are fixed. `curated` ≠ `verified`. `industry-estimate`
   and `demo` never enter an aggregate. `isAggregatable()` is the single gate.
4. Where a value is unknown, the existing sentinel stays: `year: 0`, the
   `VENUE_UNSTATED` constant, `undetermined` as a first-class `AnalysisMethod`.
   Do not "clean these up" by guessing.
5. Docstrings in `src/data/types.ts` encode design decisions, not noise. They
   port with the types.

## Do not

- Do not rewrite screens or components.
- Do not "improve" the corpus data. It is real literature, unevenly keyed on
  purpose, and the gaps are documented deliberately.
- Do not delete the honesty policy in README or the provenance tick system.
- Do not hand-maintain a type in both Python and TypeScript. Generate one from
  the other.
