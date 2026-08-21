# Contributing to openFerment

Read `CLAUDE.md` first. It is short, it is checked into the root on purpose,
and every rule in it is load-bearing. `MIGRATION.md` records how the repository
got to its current shape and where the older briefs disagree with it.

## The one gate

```
pnpm verify
```

Twenty stages, and green is the definition of done — for every change, not
just releases. It typechecks, checks the seed invariants, proves the corpus is
a fixed point of its models, replays four TypeScript/Python parity gates, runs
the canonical Python suites, checks every generated file is current, enforces
engine purity, pins the interpolation properties, holds the MCP servers to
their manifests, checks the bioSTEAM numerics, builds, and drives the app
through three browser suites. If a stage is in your
way, the fix is to complete the change, never to weaken the stage.

Running it needs Node 22 + pnpm, and Python 3.11 with the two packages
installed (`pip install -e 'packages/core[dev]' -e 'packages/assay[dev]'`).
CI (`.github/workflows/verify.yml`) runs the same gate on every push and PR.

## Things maintained in ONE place

The failure this repository is built to prevent is the same thing maintained in
two places. Concretely:

| This… | …is generated from | Regenerate with |
|---|---|---|
| `src/data/types.ts` / `types.generated.ts` | the Pydantic models in `packages/core` | `pnpm gen:types` |
| `data/corpus/*.json` canonical form | the models (fixed point) | `pnpm export:corpus` |
| `packages/core/seed/schema.sql` | the models | `python3 packages/core/seed/cli.py emit` |
| `fixtures/answer-shapes.json` | the flows | `pnpm capture:answer-shapes` |
| `packages/assay/fixtures/flows.json` | the flows | `pnpm capture:eval-flows` |
| `servers/*/manifest.json` tool lists | the servers' own source | hand-edited, but `check:servers` fails if the two disagree |

Never edit a generated file by hand — a generated file somebody has patched has
quietly stopped being generated, and there is a verify stage watching each one.

Five modules in `src/engine/` are MIRRORS of Python canon (`units`, `scale`,
`diff`, `metrics`, `aggregation`); each says so in its header. So is
`servers/guild/src/meta.ts`, which mirrors `openferment_core.snapshot`. Change
the Python first, then the mirror, and expect the parity gates to catch
anything less.

Two rules currently live in more than one language on purpose, each with a gate
holding the copies together and each naming its own retirement: the
strain-attribution rule (`openferment_core.corpus.records_attributed_to`, with
copies in `src/adapters/fixture/cell.ts` and `src/screens/Organisms.tsx`), and
the cost-model summary, which `servers/economics` derives from the corpus while
`src/data/scenarios.ts` builds it in TypeScript. Do not add a third of either
without extending `check:servers` to cover it.

## Absolute prohibitions

- Do not regenerate, summarise, or "improve" `docs/OF-COR-001.md` or
  `data/corpus/*.json`. They contain curated claims about real papers, and
  fabricating content about a real publication is the one unrecoverable error
  in this project.
- No fabricated data anywhere. `RUN_OUTPUTS` stays empty until a real extractor
  has run. Never invent a precision, recall, F1, DOI, year, author, or venue.
- No `localStorage` / `sessionStorage`. Session-only persistence is a product
  behaviour; export is the escape hatch.
- Provenance semantics are fixed: `curated` ≠ `verified`; `industry-estimate`
  and `demo` never enter an aggregate; `isAggregatable()` is the single gate.
- Sentinels stay: `year: 0`, `undetermined`, the unstated-venue string. They
  mark real gaps in real literature; do not "clean them up" by guessing.

## Where new work goes

Anything callable by BioSTEAM, COBRApy, PaperQA2, Inspect AI, or the extraction
pipeline is Python (`packages/core`, `packages/assay`, `servers/`). Screens,
components and UI conveniences are TypeScript and read data only through the
seams: `src/data/source.ts` for collections, `src/adapters/` for subsystems.
A screen importing seed data directly is a regression — `check:purity` and the
Phase 3 exit condition in `MIGRATION.md` say exactly what is allowed.

## Adding an MCP server tool

`servers/README.md` has the detail. Two rules that are not negotiable:

- **Declare it in `manifest.json`.** `check:servers` fails on a tool the
  manifest does not name, because an undeclared tool is one nobody reviewed.
- **Ask what an unattended call would produce.** Several tools are deliberately
  absent — nothing publishes, nothing mints a seal, nothing writes an
  extraction record, nothing authors a cost model, nothing registers a strain.
  Each was left out because an agent calling it would create something carrying
  authority nobody granted. If a proposed tool fails that test, it does not go
  in, and a refusal is not a substitute for leaving it out.

A tool that cannot answer honestly yet is DECLARED and REFUSES: it keeps its
shape so callers do not change later, its manifest entry says
`"status": "declared-refuses"`, and its refusal message names what is missing
and what it will return once that exists.
