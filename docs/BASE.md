# The base

openFerment is two layers. **The base** is the part that is finished and kept stable: a store,
projects, records whose provenance the code computes, runs of one shape, flowsheet files,
studies, the screens, and the ways in for programs and agents. **Modules** are what other
people build on top of it, against written contracts, without editing the base.

This page is for a reader who has never spoken to the people who wrote openFerment. It says
what the base is, what a module is, how to prove a module needs no edit to the base, and what
the base runs on.

## What the base is

| Part | What it holds | Where it is described |
|---|---|---|
| The store | PostgreSQL with pgvector, the one database: every row carries its project, who made it and when | `docs/decisions/ADR-001-postgresql.md` |
| Projects | Everything a person keeps belongs to one project, named on every request by `X-OpenFerment-Project` | `docs/decisions/ADR-005-projects.md` |
| Records | Values read from documents, each anchored to the verbatim quote it stands in; a reviewer's decisions; the candidates waiting; the catalogues of strains, products, skills and lessons; the depositions made at the bench. Provenance is computed by code from inputs and origins, and no person or model sets it | `docs/api/intake.md`, `docs/decisions/ADR-006-quantities-and-estimates.md` |
| Runs | One `runs` row per computation, of one shape whatever engine made it, each input a typed quantity with its origin, replayable within the precision the run states | `docs/api/runs.md`, `docs/api/engines.md` |
| Flowsheets | SFF files: every run of a plant writes a validated, scored file, and files import as records | `docs/api/sff.md` |
| Studies | Scenarios, comparisons, runbooks with locked predictions, and an export package that opens without the service | `docs/api/studies.md` |
| The screens | A React application, one address per project, reading the types generated from the service's OpenAPI document | `docs/api/openapi.json` |
| The ways in | The REST API, the server-sent event stream, one tool registry, and the `openferment` MCP server over that registry | `docs/TOOLS.md`, `docs/api/postdoc.md` |

The base works with no model key configured. Every screen of the base opens and works without
one; the Postdoc screen says in words that it needs a key.

The repository holds software alone. No composition, yield, price, titre, strain fact or a
paper's finding is written into its code, seed or fixtures: science arrives at run time through
documents, library plants, people and models, each value carrying where it came from.

## What a module is

A module adds capability through a contract and edits nothing in the base:

- **An engine**: a Python package that registers one object under the entry-point group
  `openferment.engines`, runs its heavy computation in a worker process of its own, takes typed
  quantities and gives back one run of the shape every run has (`docs/api/engines.md`). The
  engines in this repository register the same way, from `core/pyproject.toml`: `biosteam`
  (library plants and openFerment's composed flowsheet). `python -m
  openferment_core.engine.conform <name>` makes the contract's eight checks on an engine, and
  `pnpm prove` makes them on every engine registered (step 10).
- **An agent**: a program that acts in a project through the REST API or the MCP server, under
  a name of its own, every write audited under that name (`docs/TOOLS.md`).
- **The literature layer**: Sci RAG Kit, used as a library, with its REST under `/rag` and an
  MCP server of its own (`docs/decisions/ADR-002-sci-rag-kit.md`).
- **Postdoc**: the first agent, which stays in the repository with its screen; nothing in the
  base depends on it.
- **Content**: Guild's protocols and skills, Primer's lessons, kept as catalogue entries of a
  project.

## The two handoff tests

The claim that a module needs no edit to the base is tested by someone who has read only the
contract pages.

1. **An engine from the contract alone.** A builder who may read `docs/api/engines.md`,
   `docs/api/workers.md`, `docs/api/runs.md` and `docs/api/openapi.json`, and nothing else,
   builds an installable engine package. Installed into the service's environment, the service
   lists it, every conformance check passes, and its runs appear on the Runs screen with their
   provenance, with no file of the base changed:

   ```
   cd core && uv pip install -e ../examples/engines/openferment-engine-mirror
   uv run python -m openferment_core.engine.conform mirror
   ```

2. **An agent from the interface alone.** A builder who may read `docs/TOOLS.md`,
   `docs/api/openapi.json` and `.mcp.json`, and nothing else, writes a client that starts the
   `openferment` MCP server in a project, reads the project's records, writes one catalogue
   entry under its own name, and reads back the audit row that names it:

   ```
   pnpm prove --keep        # prints the project and the address of the service it leaves running
   cd core && uv run python ../examples/agents/record-reader/read.py --project <id>
   ```

`pnpm prove` runs the first test on every run; `docs/reports/handoff-2026-11.md` records the
builders' rounds, what each read and what the pages lacked.

## What the base runs on

| Piece | Version |
|---|---|
| Python | 3.12 or later |
| PostgreSQL | 16 or later, with pgvector |
| BioSTEAM, thermosteam, biorefineries | 2.54.0, 0.54.2, 2.35.1 |
| cobra | 0.32.1 |
| Sci RAG Kit | 0.5.0, with FastEmbed 0.9.0 embedding locally (`BAAI/bge-small-en-v1.5`, 384 dimensions) |
| The SFF toolkit | vendored unmodified, schema 0.2.4 |
| FastAPI, the MCP SDK, the Anthropic SDK | 0.141.1, 2.3.0, 1.0.0 |

Every pin is in `core/uv.lock` and `pnpm-lock.yaml`. Every dependency stays inside the
permissive licence families `core/licences.toml` lists (`pnpm check:licences`).

## Running it

```
pnpm install --frozen-lockfile
cd core && uv sync --all-extras && cd ..
pnpm db:migrate          # PostgreSQL named by OPENFERMENT_DATABASE_URL in core/.env
pnpm verify              # every gate, offline, with no key
pnpm build && pnpm prove # the proof on a database of its own, with no key and no network
```
