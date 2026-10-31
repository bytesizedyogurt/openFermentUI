# openFerment

openFerment is an open platform in which a person directs **Postdoc**, an AI research
coordinator, through bioprocess engineering work, and every claim, number and result stays
inspectable back to its source, its calculation and its assumptions. The first domain is
cellulosic ethanol from characterized biomass, served by BioSTEAM's `biorefineries` library
plants.

The repository holds software alone. The science arrives at run time through the platform's
own doors: documents through Intake, plants and their numbers through the library, values
through people and models, each value carrying where it came from.

## What it is made of

| Part | What it does |
|---|---|
| **PostgreSQL** with pgvector | the one store: projects, records, decisions, runs, artifacts, studies, conversations, the audit and the spend |
| **Sci RAG Kit** | the literature layer: documents chunked, embedded locally, searched, cited and answered |
| **BioSTEAM** | the engine: any library plant or openFerment flowsheet runs in a worker through one adapter, every parameter read back with its origin |
| **SFF** | the flowsheet record: every run exports a validated, scored file, and files import as records |
| **Postdoc** | one loop over one typed tool registry, by REST, server-sent events and MCP, with its conversations kept on the server |
| **The app** | React, wired to the service for every record; each project at its own address |

A project's path: Intake collects papers, reports, uploads and pasted text into the kit;
extraction anchors candidate values to the stored words and a reviewer decides on them in
BioRepo; the engine runs plants and flowsheets; studies keep scenarios, comparisons, runbooks
and an export package; Postdoc reads all of it through its tools and states each number with
its origin, an estimate marked as one.

## Run it

```
pnpm install --frozen-lockfile
cd core && uv sync --all-extras && cd ..
pnpm db:up && pnpm db:migrate     # PostgreSQL 16 or later with pgvector; or name a server in core/.env
pnpm prototype:up                 # the service on 127.0.0.1:8000, the app on 127.0.0.1:4173
```

The model key goes in `core/.env` (gitignored; `core/.env.example` lists every setting). The
service binds `127.0.0.1` alone. Without a key the app runs whole, and the steps that need a
model say so.

## Test it

```
pnpm verify      # the gate: secrets first, types, generated files, the suites, licences, build, smoke
pnpm build && pnpm prove      # the end-to-end proof, offline, on a database of its own
```

`pnpm test:core` runs offline in about five minutes; `pnpm test:sim` starts the BioSTEAM worker
(a cold import takes about 31 s); `pnpm test:lit` embeds the kit's demo corpus.

## Read further

- [`docs/PROGRESS.md`](docs/PROGRESS.md): where things stand, how to resume, the debts and the blockers.
- [`CLAUDE.md`](CLAUDE.md): the working guidance, every line labelled.
- [`docs/decisions/`](docs/decisions/): the decision records, ADR-000 to ADR-014.
- [`docs/api/`](docs/api/): the contracts (OpenAPI, events, workers, runs, SFF, studies, Intake);
  [`docs/TOOLS.md`](docs/TOOLS.md): the tool registry; [`COMPONENTS.md`](COMPONENTS.md): the package map.
- [`docs/history/`](docs/history/): the guidance written before alpha 2.0, kept as evidence.

The repository declares no licence yet: the choice is the owner's (ADR-012). The licences of
its dependencies are recorded in `core/licences.toml`.
