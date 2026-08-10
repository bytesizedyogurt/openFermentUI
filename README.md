# openFerment — working simulation

A complete, richly seeded front-end simulation of **openFerment**: an agentic RAG platform
for precision fermentation and algal bioprocessing, built around a literature corpus,
structured parameter extraction, executable protocols, and techno-economic modeling.

This repository implements **OF-DES-001 v0.1** — the front-end design document and working
simulation plan. It is the design proven at full fidelity, the faculty demo, and the
executable spec for the eventual production build.

> ⚠️ **Everything in this application is synthetic.** All papers, authors, journals, and
> values are fictional and were written for demonstration. No real researcher's name, venue,
> or DOI appears anywhere in the seed content. Simulation economics are illustrative and not
> validated. Every export carries this disclosure in its header.

## Running it

```bash
pnpm install
pnpm dev          # http://localhost:5173
pnpm build        # typecheck + production bundle
pnpm check:seed   # validate every seed invariant
```

## What "working" means here

The simulation holds itself to eight conditions (design §11):

1. **No dead controls.** Every visible button, link, chip, toggle, and slider does its
   designed thing, or is explicitly labeled inactive.
2. **No lorem ipsum.** Every string is real copy; every datum comes from the seeded content set.
3. **Traversable journeys.** Every cross-entity path — chip → reader → record → strain →
   protocol → scenario — is walkable in both directions.
4. **Believable time.** Latency is simulated per operation class, so the prototype
   demonstrates the *pacing* of the product, not just its layouts.
5. **Deterministic where it matters.** Scripted agent flows and simulation results are
   reproducible run to run; randomness is confined to cosmetic timing jitter.
6. **Functional protocols.** Scaling math, timers, run logging, materials aggregation,
   version diffs, and exports actually compute.
7. **Honest boundaries.** Session-only persistence, synthetic corpus, and demo economics are
   labeled at the shell level and at every point of possible confusion.
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
src/engine/     pure logic, unit-testable without UI, ships to production unchanged
src/sim/        latency model, scripted job timelines, chat flow player — retired last
src/components/ shared primitives (citation chip, data table, quantity field, …)
src/screens/    one file per screen
```

The split is deliberate. `engine/` (units, scaling, diff, metrics, interpolation) is
production code already. `data/` seed modules keep the shapes the API will return, so they
become fixtures and contract tests. `sim/` is the only layer designed to be thrown away —
and the scripted chat flows survive it as regression fixtures for the real agent's answer
formatter.

### The evidence tick

The design system's signature: a 3px notched left border on any datum-bearing element,
colored by provenance — gold for curated gold-set entries, green for extracted-and-verified,
gray for unverified, blue for user-entered, and a **dashed warn-colored tick for anything
synthetic**. Provenance stops being a badge you read and becomes a texture you perceive: a
screen full of verified green ticks feels different from one streaked with unverified gray.

Provenance is never encoded by color alone — every tick pairs with an icon and label on hover
and in its accessible name.

### Simulated BioSTEAM

The Sim ships *response surfaces, not a process simulator*. Each cost model is authored once
(spreadsheet-grade: CAPEX scaling exponents, annualization, media/utility/labor line items,
downstream yield effects) and evaluated over its full sweep grid at load. The client
multilinearly interpolates between grid points, so sliders are continuous and instantaneous —
and the cost waterfall always sums to the headline MSP, because the lines were computed
together.

In production, the frozen grids become caches in front of a real BioSTEAM worker against the
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

Six mechanisms, all mandatory (design §20):

1. A persistent shell banner naming the corpus as synthetic.
2. The dashed demo tick on every synthetic-derived datum.
3. A colophon at `/settings/about` carrying the full fidelity matrix — what is computed,
   what is scripted, what is merely visual.
4. Simulation headlines permanently subtitled "Demo model v0 — illustrative economics, not
   validated."
5. A demo-corpus footer on every agent answer.
6. No real researcher name, venue title, or DOI anywhere in seed content — and exports embed
   the disclosure so a CSV cannot launder demo data into a real analysis.

## Documents

- `BUILD-SPEC.md` — the build contract: ID registry, seed invariants, content and style rules.
- `scripts/check-seed.ts` — enforces those invariants; run before any bundle.
