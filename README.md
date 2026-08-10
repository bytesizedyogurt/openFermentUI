# openFerment — working simulation

A complete, richly seeded front-end simulation of **openFerment**: an agentic RAG platform
for precision fermentation and algal bioprocessing, built around a literature corpus,
structured parameter extraction, executable protocols, and techno-economic modeling.

This repository implements **OF-DES-001 v0.1** (front-end design and working-simulation plan)
against the corpus of **OF-COR-001 v1.0** (`docs/OF-COR-001.md`). It is the design proven at
full fidelity, the faculty demo, and the executable spec for the eventual production build.

## The program it is built around

Not a generic demo. Every screen is populated from one real research question:

> **Can phosphorylated bovine β-casein be expressed in the cell-wall-deficient
> *Chlamydomonas reinhardtii* strain cw15?**

Caseins have been expressed in bacteria, in yeast, and in plants. They have never been
published in a microalga — Mora Vásquez et al. (2025) tabulate 17 bacterial, 5 yeast and 2
plant studies with no algal row. The case for cw15 assembles from four established facts: a
real ER/Golgi secretory pathway (12–15 mg/L secretion established from UVM4), FDA GRAS status,
cell-wall deficiency as a downstream asset (~3× protein release under pulsed electric field),
and the observation that Ser-x-Glu phosphorylation by FAM20C — what makes casein assemble,
bind calcium and coagulate — is unsolved in *every* host.

The honest counterweight is seeded too: nuclear transgene expression in *Chlamydomonas* is
historically weak (~0.2% TSP), secreted yields sit two to three orders below *Trichoderma*
β-lactoglobulin, and whether *C. reinhardtii* even has a Fam20-family kinase is an **open
question the app labels as open** rather than answering.

## What is real, and what is modeled

| Layer | Status |
|---|---|
| Papers, authors, journals, DOIs | **Real and citable** — 132 catalogued entries, threads A–O |
| Extracted values | **Real** — 134 curated records traceable to a real source |
| Strains, protocols, ontology | **Real** — drawn from the literature and standard practice |
| Simulation economics | **Modeled** — illustrative response surfaces, not validated |
| Agent answer prose | **Scripted** — 13 authored flows, deterministic and offline |

The corpus is real literature. That is the whole point of OF-COR-001, and it is why the
demo-labelling policy is narrow rather than blanket: only the two genuinely synthetic
surfaces — simulation grids and scripted agent text — carry demo treatment. Everything else
carries its actual provenance.

### Seed inventory

```
132 papers          all ingest: 'catalogued'   (metadata + curator note; no full text retrieved)
134 records         132 curated · 2 industry-estimate · 127 flagged is_primary
 24 ontology fields  5 families: expression, ptm, functional, cultivation, downstream
  8 ontology gaps   real values the v1 ontology cannot express, recorded rather than dropped
  7 strains         cw15, UVM4, C. reinhardtii wild type, GS115, T. reesei, E. coli, bovine
  9 protocols       TAP media → transformation → PEF disruption → Phos-tag → CIP
 13 chat flows       3 scenarios · 6 learn modules / 9 lessons
```

## Running it

```bash
pnpm install
pnpm dev            # http://localhost:5173
pnpm build          # typecheck + production bundle
pnpm bundle:single  # one self-contained .html (inlined CSS/JS/fonts), openable from file://

pnpm verify         # the full gate, in order:
  pnpm typecheck    #   tsc --noEmit
  pnpm check:seed   #   every seed invariant, incl. unit dimensional analysis
  pnpm build
  pnpm test:smoke   #   32 routes, headless: console errors, uncaught throws, empty renders
  pnpm test:golden  #   the ten-minute demo script, driven end to end
  pnpm test:deep    #   ingest failure, protocol version diff, scenario compare
```

The test suite is not decoration. `test:golden` is what caught a markdown-renderer infinite
loop that crashed the tab: a table's `|` header row arriving before its `|---|` separator
consumed no input and allocated empty blocks forever. Every route rendered fine; the app was
still broken. Rendering is not working.

## What "working" means here

The simulation holds itself to eight conditions (design §11):

1. **No dead controls.** Every visible button, link, chip, toggle, and slider does its
   designed thing, or is explicitly labeled inactive.
2. **No lorem ipsum.** Every string is real copy; every datum comes from the seeded corpus.
3. **Traversable journeys.** Every cross-entity path — chip → reader → record → strain →
   protocol → scenario — is walkable in both directions.
4. **Believable time.** Latency is simulated per operation class, so the prototype
   demonstrates the *pacing* of the product, not just its layouts.
5. **Deterministic where it matters.** Scripted agent flows and simulation results are
   reproducible run to run; randomness is confined to cosmetic timing jitter.
6. **Functional protocols.** Scaling math, timers, run logging, materials aggregation,
   version diffs, and exports actually compute.
7. **Honest boundaries.** Session-only persistence, catalogued-not-ingested papers, and
   modeled economics are labeled at the shell level and at every point of possible confusion.
8. **The golden path holds.** The ten-minute demo script runs start to finish with no dead
   ends, offline, with no external calls.

## Module map

| Module | Name | What it proves | Where it lives |
|---|---|---|---|
| 0 | PhycoExtract | Extraction quality is measurable | `/library`, `/extract`, `/extract/validation` |
| 1 | Corpus & Ask | Agentic RAG with visible retrieval | `/ask`, `/library` |
| 2 | Organisms & Protocols | Verified parameters become executable | `/organisms`, `/protocols` |
| 3 | Simulate | Parameters feed techno-economics | `/simulate` |
| 4 | Learn | The platform doubles as curriculum | `/learn` |

## Architecture

```
src/data/       seed content as typed TS modules — becomes API fixtures in production
src/data/corpus/  the 15 literature threads, A–O, one file per thread group
src/engine/     pure logic, unit-testable without UI, ships to production unchanged
src/sim/        latency model, scripted job timelines, chat flow player — retired last
src/components/ shared primitives (citation chip, data table, quantity field, …)
src/screens/    one file per screen
```

The split is deliberate. `engine/` (units, scaling, diff, metrics, interpolation, retrieval)
is production code already. `data/` seed modules keep the shapes the API will return, so they
become fixtures and contract tests. `sim/` is the only layer designed to be thrown away —
and the scripted chat flows survive it as regression fixtures for the real agent's answer
formatter.

### The evidence tick

The design system's signature: a 3px notched left border on any datum-bearing element,
colored by provenance.

| Tick | Provenance | Means |
|---|---|---|
| gold | `gold` | curated gold-set entry |
| green | `verified` | extracted and checked against source |
| slate | `curated` | curated, source check pending |
| gray | `unverified` | extracted, unverified |
| blue | `user` | user-entered |
| amber | `industry-estimate` | trade figure — **not evidence, never aggregated** |
| dashed warn | `demo` | modeled, not measured |

Provenance stops being a badge you read and becomes a texture you perceive: a screen of
verified green ticks feels different from one streaked with unverified gray. It is never
encoded by color alone — every tick pairs with an icon and label on hover and in its
accessible name, and `isAggregatable()` refuses to roll industry estimates into statistics.

### Units that refuse

The unit engine does dimensional analysis over the ontology's unit families and converts
freely inside a family. Across families it does not guess — it **refuses with a reason**.
Asking for %TSP → g/L returns an explanation that the conversion needs a total-soluble-protein
figure the record does not carry; EUR → USD returns that no exchange rate is pinned to the
record's year. A refusal that says why is more useful than a number that is wrong.

### Simulated BioSTEAM

The Sim ships *response surfaces, not a process simulator*. Each cost model is authored once
(CAPEX scaling exponents, annualization, media/utility/labor line items, downstream yield
effects) and evaluated over its full sweep grid at load. The client multilinearly interpolates
between grid points, so sliders are continuous and instantaneous — and the cost waterfall
always sums to the headline MSP, because the lines were computed together.

In production the frozen grids become caches in front of a real BioSTEAM worker against the
same `Scenario`/`ResultGrid` contract. Nothing in the UI changes, which is the point of
specifying it this way.

### Simulated agent

Two modes, one UI. **Scripted** (default, offline, deterministic) plays seeded conversation
flows: the plan ticks, tool calls appear, retrieval sets render, the answer streams. Because
every message comes from the flow object, the inspector's "trace" is the literal data that
produced the answer — honest by construction rather than reconstructed afterward.

When no flow matches, a fallback ladder keeps it honest: first an **entity-lookup flow** that
genuinely queries the seeded store and answers from live data with real chips; failing that,
an explicit decline naming what the corpus does cover. It never fabricates a specific answer
to an unmatched question.

## Honesty policy

Real corpus, modeled economics — so the labelling is targeted rather than blanket:

1. A persistent shell banner: *"Real literature · modeled economics."*
2. The dashed demo tick on simulation-derived values only; real records carry their real
   provenance.
3. A colophon at `/settings/about` with the full fidelity matrix — computed vs. scripted vs.
   visual.
4. Simulation headlines permanently subtitled *"Demo model v0 — illustrative economics, not
   validated."*
5. Agent answers footer their scripted status; citation chips carry real DOIs.
6. Exports embed the disclosure, so a CSV cannot launder modeled economics into a real
   analysis.

## Known open items

Recorded here because the app records them rather than papering over them:

- **Papers are catalogued, not ingested.** Metadata and a curator note only; no full text was
  retrieved, so extraction spans anchor to curator prose and the reader says so. `RUN_OUTPUTS`
  is deliberately empty — no extractor has run against un-ingested papers, so Validation shows
  the 66-record gold-set *plan* and 6 difficulty cases rather than fabricated P/R/F1.
- **49 entries carry `[verify]` author strings.** Title, journal, year and DOI are confirmed;
  the DOI or PMCID is the authoritative key, never the author string. The scripted
  CrossRef/PubMed resolution pass (§22.1) is outstanding.
- **One gold-set row is blocked.** F1's 5 planned records (gene length, exon count,
  precursor/mature length, variant count) have no expressible field in ontology v1. Marked
  `blocked` rather than silently dropped; extending the ontology is a product decision.
- **D5 is an open question, not an answer.** Whether *C. reinhardtii* encodes a Fam20-family
  kinase wants an HMM search of the v6.1 proteome against Pfam PF03881. The app labels it open.

## Documents

- `docs/OF-COR-001.md` — the corpus: 15 threads, the ontology, the gold-set plan, scenarios.
- `BUILD-SPEC.md` — the build contract: ID registry, seed invariants, content and style rules.
- `scripts/check-seed.ts` — enforces those invariants; run before any bundle.
