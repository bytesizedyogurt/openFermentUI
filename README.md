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
bind calcium and coagulate — is done natively by no yeast, plant or bacterial host. The corpus
keeps the counter-example that complicates this: H4 reports *Pichia*-expressed bovine β-casein
carrying the same degree of phosphorylation as the animal-derived protein, with no kinase
co-expressed.

The honest counterweight is seeded too: nuclear transgene expression in *Chlamydomonas* is
historically weak (~0.2% TSP **for intracellular reporters** — a reporter ceiling, never
measured on a casein or on a secreted product), secreted yields sit two to three orders below
*Trichoderma*
β-lactoglobulin, and whether *C. reinhardtii* even has a Fam20-family kinase is an **open
question the app labels as open** rather than answering.

## What is real, and what is modeled

| Layer | Status |
|---|---|
| Papers, venues, identifiers | **Real, unevenly keyed** — 132 catalogued entries, threads A–O; 59 carry a DOI/PMCID/PMID, 73 carry none |
| Extracted values | **Real** — 132 curated records traceable to a source, plus 2 `industry-estimate` figures with no source document |
| Strains, protocols, ontology | **Real** — drawn from the literature and standard bench practice |
| Simulation economics | **Modeled** — illustrative response surfaces, not validated |
| Agent answer prose | **Authored** — 13 scripted flows, deterministic and offline. No language model is called |

The corpus is real literature. That is the whole point of OF-COR-001, and it is why the
demo-labelling policy is narrow rather than blanket: only the two genuinely synthetic
surfaces — simulation grids and scripted agent text — carry demo treatment. Everything else
carries its actual provenance.

"Real" is not the same as "complete", and the app is built to say so. 36 of the 132 entries
carry a DOI, 59 carry some persistent identifier, 50 record no authors, and 18 sit at
`year: 0` because OF-COR-001 states no year. `curated` — the provenance on 132 of the 134
records — means *transcribed from the curation document and not yet checked against the source
PDF*. It does not mean verified. Nothing in the corpus is currently `verified`.

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
| 0 | PhycoExtract | Extraction quality is measurable | `/biorepo`, `/intake`, `/guild`, `/witness` |
| 1 | Corpus & Postdoc | Agentic RAG with visible retrieval | `/postdoc`, `/biorepo` |
| 2 | Organisms & Protocols | Verified parameters become executable | `/organisms`, `/protocols` |
| 3 | Proforma | Parameters feed techno-economics | `/proforma` |
| 4 | Primer | The platform doubles as curriculum | `/primer` |
| 5 | Assay | A claim is tested, and the result comes back | `/runbooks`, `/depositions` |

## The vocabulary

The rail says Postdoc, BioRepo, Intake, Proforma, Primer — component names, not generic
verbs. `COMPONENTS.md` is the canonical map of all eighteen; `/settings/architecture` is the
same map in the app. Every label carries a one-line descriptor, the ⌘K palette still answers
to the old words (`library` finds BioRepo), and every old path redirects rather than 404s, so
`/library/papers/H4` lands on `/biorepo/papers/H4` with its deep link intact.

Organisms, Molecules and Protocols keep their plain names: they are catalogue views of domain
objects, not components.

## Architecture

```
src/data/       seed content as typed TS modules — becomes API fixtures in production
src/data/corpus/  the 15 literature threads, A–O, one file per thread group
src/engine/     pure logic, unit-testable without UI, ships to production unchanged
src/sim/        latency model and chat flow player — two files, retired last
src/components/ shared primitives (citation chip, data table, quantity field, …)
src/screens/    one file per screen, named after the component it is
src/data/nav.ts the navigation vocabulary — labels, descriptors, aliases, redirects
```

The split is deliberate. `engine/` (units, scaling, diff, metrics, interpolation, retrieval)
is production code already. `data/` seed modules keep the shapes the API will return, so they
become fixtures and contract tests. `sim/` is designed to be thrown away, and the scripted chat flows survive
it as regression fixtures for the real agent's answer formatter. It is not quite a clean seam:
the simulated job pacing lives in `store.ts` (`startJob`/`tickJobs`) rather than in `sim/`, so
retiring the simulation means editing the store too.

### The evidence tick

The design system's signature: a 3px notched left border on any datum-bearing element,
colored by provenance.

| Tick | Provenance | Means |
|---|---|---|
| solid gold | `gold` | curated gold-set entry |
| solid green | `verified` | checked against the source document |
| green, 45% | `curated` | transcribed from the curation document, **not** yet checked |
| solid grey | `unverified` | extractor output, not reviewed |
| solid blue | `user` | user-entered |
| dashed grey | `industry-estimate` | vendor or market figure — no source document, never aggregated |
| dashed amber | `demo` | modeled, not measured |

Provenance stops being a badge you read and becomes a texture you perceive: a screen of
curated green feels different from one streaked with dashed grey. The two classes that must
never be mistaken for evidence — `industry-estimate` and `demo` — are the two that are dashed,
so they are distinguishable from their neighbours without relying on hue.

`isAggregatable()` is the single gate on what may enter a statistic: it excludes rejected
records, industry estimates, and any record marked `isPrimary: false` (a paper reciting someone
else's measurement, which would double-count). Excluded records stay visible in per-record lists
and plots and say why they were held out — the rule is about medians, not about hiding data.

Two honest limits. Ticks rendered inside `DataTable` are `aria-hidden`, so in those tables
provenance is conveyed by colour alone; the `Tick` component used everywhere else carries a
`title` and screen-reader label. And no tick renders an icon — icons appear on the explicit
`ProvenanceBadge` used in detail views and popovers, not in the ambient ticks.

### Units that refuse

The unit engine — which has no name of its own; Primer used to name it and now names the
Learn screens — does dimensional analysis over 25 unit families and converts freely inside a
family. Across families it does not guess — it fails. For the three crossings that actually
come up in this corpus it fails **with a reason**: %TSP ↔ g/L explains that the conversion
needs the cell density and the total-protein fraction of the biomass; %TSP ↔ % explains why a
share of soluble protein is not a share of anything else; EUR ↔ USD asks for an exchange rate
with a date attached and refuses to invent one. Every other cross-family pair gets a bare
dimension error, which is honest but less useful — the `REFUSALS` table is the mechanism for
upgrading one as soon as a corpus value needs it.

`explainRefusal(from, to)` takes two unit strings, not a record, so a refusal explains what the
*conversion* needs rather than what a particular record lacks.

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

One working mode. **Scripted** is offline and deterministic: it plays seeded conversation
flows — the plan ticks, tool calls appear, retrieval sets render, the answer streams. Because
every message comes from the flow object, the inspector's "trace" is the literal data that
produced the answer, honest by construction rather than reconstructed afterward. The composer
offers a "Live (needs network)" toggle, which is inert: selecting it shows a banner and the
turn still runs scripted. No language model is called anywhere in this build.

When no flow matches, a fallback ladder takes over: first an **entity-lookup flow** that
genuinely queries the seeded store and answers from live data with real chips, subject to the
same `isAggregatable()` gate as every other statistic; failing that, an explicit decline naming
what the corpus does cover.

Getting that ladder to actually run took work. Intent matching originally scored whole-phrase
containment in both directions, so a two-character query sitting inside a trigger scored 70+
and played a full scripted answer: `"hi"` scored 79.6, `"cost"` 76. Keyword overlap measured
only how much of the *trigger* the query covered, never how much of the query the trigger
accounted for, so `"max secreted yield from tomatoes"` scored 52.5 and answered `15 mg/L` about
*Chlamydomonas*. Matching now scores the F1 of both coverage directions, weights query tokens
by corpus document frequency so a rare unmatched term outweighs the common ones it shares, and
multiplies confidence by 0.4 for every token absent from the corpus vocabulary. All 65 authored
triggers still route to their own flow; the probes above now fall through to the ladder.

## Honesty policy

Real corpus, modeled economics — so the labelling is targeted rather than blanket:

1. A persistent shell banner: *"Real literature · modeled economics."*
2. The dashed demo tick on modeled values; real records carry their real provenance. Citation
   chips show title, authors, year, venue and the quoted span — an identifier reaches the
   clipboard via "Copy citation" when the paper has one, which 59 of 132 do.
3. A colophon at `/settings/about` with the full fidelity matrix — computed vs. scripted vs.
   visual.
4. Simulation headlines permanently subtitled *"Demo model v0 — illustrative economics, not
   validated."*
5. Agent answers footer the fact that their prose is scripted, alongside a source count.
6. Exports embed the disclosure. CSVs carry the 11-line provenance header from `src/lib/csv.ts`;
   run logs, review sessions, materials checklists and agent answers carry their own headers
   saying the same thing in the shape their format allows.

## Known open items

Recorded here because the app records them rather than papering over them:

- **Papers are catalogued, not ingested.** Metadata and a curator note only; no full text was
  retrieved, so extraction spans anchor to curator prose and the reader says so. `RUN_OUTPUTS`
  is deliberately empty — no extractor has run against un-ingested papers, so Witness shows
  the 66-record gold-set *plan* and 6 difficulty cases rather than fabricated P/R/F1.
- **49 entries are flagged `[verify]`, and they are thinner than that flag suggests.** Only 7 of
  the 49 hold title, a named journal, a real year and a DOI together. 28 carry no `doi`, `pmcid`
  or `pmid` at all, 18 record a placeholder venue rather than a journal, and 12 sit at `year: 0`.
  Where an identifier exists it is the authoritative key, never the author string — but for most
  of these entries no such key is on record yet. The scripted CrossRef/PubMed resolution pass
  (§22.1) is outstanding, and it has more to recover than author names.
- **One gold-set row is blocked.** F1's 5 planned records (gene length, exon count,
  precursor/mature length, variant count) have no expressible field in ontology v1. Marked
  `blocked` rather than silently dropped; extending the ontology is a product decision.
- **D5 is an open question, not an answer.** Whether *C. reinhardtii* encodes a Fam20-family
  kinase wants an HMM search of the v6.1 proteome against Pfam PF03881. The app labels it open.
- **The UI copy migration from the synthetic corpus is done but not proven exhaustive.** OF-COR-001
  replaced the data; the strings describing that data were corrected screen by screen afterwards,
  and several rounds of audit each turned up more. Anything phrased as "synthetic", "fictional",
  "ingested" or "demo" should be read as suspect until checked against `src/lib/csv.ts`, which
  carries the canonical wording.

## Documents

- `docs/OF-COR-001.md` — the corpus: 15 threads, the ontology, the gold-set plan, scenarios.
- `BUILD-SPEC.md` — the build contract: ID registry, seed invariants, content and style rules.
- `COMPONENTS.md` — the eighteen components, seven layers, and what has no name yet.
- `scripts/check-seed.ts` — enforces those invariants; run before any bundle.
