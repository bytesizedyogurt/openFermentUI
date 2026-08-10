# openFerment Sim — build contract

Implementation contract for OF-DES-001 v0.1. Every module below is written
against `src/data/types.ts` (the source of truth for shapes) and the store API
in `src/store.ts`. Read both before writing code.

## Stack

React 18 + TypeScript + Vite + Tailwind. Hash router in `src/router.tsx`.
Single Zustand store. **No localStorage/sessionStorage anywhere** — session-only
persistence is a stated product behavior (§9.5); export is the escape hatch.

## Directory layout

```
src/data/      seed content as typed TS modules (one file per entity type)
src/engine/    pure logic — units, scaling, diff, interpolation, metrics, retrieval
src/sim/       latency model, job scripting, chat flow player
src/components/ shared primitives (§7)
src/screens/   one file per screen (§8)
```

## ID registry (stable, human-readable — never renumber)

| Entity | IDs |
|---|---|
| Papers (corpus) | `SP-001` … `SP-016` |
| Papers (demo shelf, held out for ingest) | `SP-017` … `SP-020`; **`SP-020` is the parse-hostile paper** whose ingest fails at Parse |
| Extraction records | `ex-0001` … `ex-0132` (zero-padded to 4) |
| Strains | `cw15`, `cc1690`, `gs115`, `aplat` |
| Protocols | `PR-TAP-01`, `PR-TAP-02`, `PR-SEED-01`, `PR-PBR-01`, `PR-OD-01`, `PR-HARV-01`, `PR-PICH-01`, `PR-CIP-01` |
| Scenarios | `sc-s1` (model S1), `sc-s2` (S2), `sc-s3` (S3) |
| Collections | `col-gold`, `col-kinetics`, `col-downstream` |
| Learn modules | `m0` … `m5`; lessons `l0-1` … `l0-4`, `l1-1`, `l2-1`, `l3-1`, `l4-1`, `l5-1` |
| Chat flows | `F1` … `F12` |
| Paper sections | `s1`, `s2`, … within each paper |

## Seed module exports (exact names — the store imports these)

| File | Exports |
|---|---|
| `src/data/papers.ts` | `PAPERS: Paper[]` |
| `src/data/records.ts` | `RECORDS: ExtractionRecord[]` |
| `src/data/runOutputs.ts` | `RUN_OUTPUTS: RunOutput[]` |
| `src/data/strains.ts` | `STRAINS: Strain[]` |
| `src/data/protocols.ts` | `PROTOCOLS: Protocol[]` |
| `src/data/scenarios.ts` | `SCENARIOS: Scenario[]`, `COST_MODELS: CostModel[]` |
| `src/data/flows.ts` | `FLOWS: ChatFlow[]`, `SUGGESTED_PROMPTS: string[]` |
| `src/data/learn.ts` | `MODULES: LearnModule[]` |
| `src/data/misc.ts` | `COLLECTIONS: Collection[]`, `ACTIVITY: ActivityEvent[]`, `SEED_SESSIONS: ChatSession[]` |
| `src/data/ontology.ts` | `ONTOLOGY`, `ONTOLOGY_BY_ID`, `fieldName` (already written) |

## Hard invariants (enforced by `pnpm check:seed`)

1. **Every `record.quote` appears verbatim in its paper section's `text`.** The
   reader locates spans by string search, so a quote that isn't in the section
   silently loses its highlight. Write the section text first, then copy the
   quote out of it.
2. Every `paperId`, `recordId`, `sourceRecordId`, and chip reference resolves to
   a real entity.
3. `record.si` equals `toSI(record.value, record.unit)` from `src/engine/units.ts`.
4. Records with `gold` set are the gold set; `RUN_OUTPUTS[*].results` reference
   only gold record IDs.
5. Grid dim `values` arrays are ascending.

## Content rules (§20 — non-negotiable)

- **All content is synthetic.** Fictional author names (globally diverse),
  invented journal titles, no real DOIs, no real researcher names, no real
  venue titles. Values must be plausible and inside the ontology ranges in
  `src/data/ontology.ts`, but they are invented.
- Never attribute a value to a real person or real publication.
- Any datum with no literature ancestry is provenance `'demo'` and renders with
  the dashed tick.
- No lorem ipsum anywhere. Every string is real, purposeful copy.

## Screen contract

Each screen is a default export in `src/screens/<Name>.tsx`:

| File | Signature |
|---|---|
| `Home.tsx` | `() => JSX` |
| `Ask.tsx` | `({ sessionId?, initialQuery? }) => JSX` |
| `Library.tsx` | `() => JSX` |
| `PaperReader.tsx` | `({ paperId, spanId? }) => JSX` |
| `Ingest.tsx` | `() => JSX` |
| `Extract.tsx` | `() => JSX` |
| `Review.tsx` | `() => JSX` |
| `Validation.tsx` | `() => JSX` |
| `Organisms.tsx` | `() => JSX` |
| `StrainPage.tsx` | `({ strainId }) => JSX` |
| `Protocols.tsx` | `() => JSX` |
| `ProtocolDetail.tsx` | `({ protocolId }) => JSX` |
| `RunMode.tsx` | `({ protocolId, runId }) => JSX` |
| `Simulate.tsx` | `() => JSX` |
| `ScenarioWorkspace.tsx` | `({ scenarioId }) => JSX` |
| `Compare.tsx` | `() => JSX` |
| `Learn.tsx` | `() => JSX` |
| `Lesson.tsx` | `({ moduleId, lessonId }) => JSX` |
| `Settings.tsx` | `({ section }) => JSX` |

## Primitives to reuse (never re-implement)

`@/components/ui` — `PageHeader`, `Card`, `SectionTitle`, `EmptyState`,
`Skeleton`, `Button`, `LinkButton`, `Popover`, `Sheet`, `Modal`, `Stat`, `Bar`,
`Callout`, `Explain`, `cx`.
`@/components/Chip` — `CitationChip`, `RecordChip`.
`@/components/Provenance` — `Tick`, `ProvenanceBadge`, `ProvDot`, `ProvenanceLegend`.
`@/components/DataTable` — `DataTable`, `Column`, `FacetDef`.
`@/components/QuantityField` — `QuantityField`, `Quantity`.
`@/components/Markdown` — `Markdown`, `inlineMarkdown`.
`@/lib/csv` — `exportCSV`, `exportText`, `toCSV`.
`@/engine/*` — units, scale, metrics, interp, grids, diff, retrieval.

## Style rules

- Tailwind classes only; the token colors are `surface-0/1`, `ink`, `ink-soft`,
  `line`, `accent`, `accent-wash`, `gold`, `signal-warn/error/info`.
- Serif (`font-serif`, Spectral) for page titles, paper/lesson body, protocol
  titles. Never for controls.
- All numerals in tables, stats, and units use `font-num` (IBM Plex Mono,
  tabular figures).
- Elevation is border-first: `card` class, `border-line` hairlines. The single
  soft shadow (`overlay`) is reserved for popovers/sheets/palette.
- Radii: `rounded-input` (4px) inputs/chips, `rounded-btn` (6px) buttons,
  `rounded-card` (8px) cards.
- Charts use recharts. Categorical series use the Okabe–Ito palette from
  `@/lib/viz`; never reuse the UI accent green for a data series.
- Accessibility floor is WCAG 2.2 AA: visible focus rings, keyboard traversal,
  `aria-live` for timers, ≥44px targets in Run Mode, "view as table" for charts.

## Honesty mechanisms every screen must respect (§20)

1. Synthetic-derived data renders with the dashed demo tick.
2. Simulation headlines keep the subtitle "Demo model v0 — illustrative
   economics, not validated."
3. Agent answers in Scripted mode carry a demo-corpus footer.
4. Exports embed the disclosure header (handled by `@/lib/csv`).
