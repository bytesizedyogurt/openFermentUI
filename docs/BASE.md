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
| Runs | One `runs` row per computation, of one shape whatever engine made it, each input a typed quantity with its origin (a reading deposited at the bench among them, as a `measurement`, which a run resting on readings and the package's defaults reads as `measured`), replayable within the precision the run states | `docs/api/runs.md`, `docs/api/engines.md` |
| Flowsheets | SFF files: every run of a plant writes a validated, scored file, and files import as records | `docs/api/sff.md` |
| Studies | Scenarios, comparisons, runbooks with locked predictions, and an export package that opens without the service | `docs/api/studies.md` |
| The screens | A React application, one address per project, reading the types generated from the service's OpenAPI document; a project's catalogues have a screen at `/catalogues`, a tab a kind | `docs/api/openapi.json` |
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
  (library plants, openFerment's composed flowsheet and the shelf's scenario flowsheets, each run
  as a Proforma scenario of it), `kinetics` (fermOS's model families, its forecasts of a kept fit
  and its vessel designs, computing in the service's process with no worker of its own, a vessel
  design in the Proforma worker) and `train` (pureOS's trains, each a project's own, built and run
  in the Proforma worker). `python -m openferment_core.engine.conform <name>` makes the
  contract's eight checks on an engine (`biosteam --thing <a scenario flowsheet> --inputs <file>`,
  the values a scenario flowsheet waits for; `kinetics` with `--inputs <file>`, the values its
  families wait for; `train` with `--project <id>`, a project that holds a train, which the
  checks read and check in a copy of their own), and `pnpm prove` makes them on every engine
  registered (step 10).
- **An agent**: a program that acts in a project through the REST API or the MCP server, under
  a name of its own, every write audited under that name (`docs/TOOLS.md`).
- **The literature layer**: Sci RAG Kit, used as a library, with its REST under `/rag` and the
  `sci-rag` MCP server: the kit's tools and two graph tools of openFerment's, each reading the
  project's concept graph alone (`docs/decisions/ADR-002-sci-rag-kit.md`).
- **Postdoc**: the first agent, which stays in the repository with its screen; nothing in the
  base depends on it.
- **Content**: Guild's protocols, kept as a project's protocols (`docs/api/studies.md`), and
  its skills and Primer's lessons, kept as catalogue entries of a project (`docs/api/intake.md`).

## The two handoff tests

The claim that a module needs no edit to the base is tested by someone who has read only the
contract pages. Stage D of alpha 2.2 ran both tests, each by a builder with none of the base's
context, in a worktree of its own at the core's commit `6f85338`; both finished in their first
round with no file of the base changed (`docs/reports/handoff-2026-11.md`), and what they built
is in `examples/`.

1. **An engine from the contract alone.** A builder who may read `docs/api/engines.md`,
   `docs/api/workers.md`, `docs/api/runs.md` and `docs/api/openapi.json`, and nothing else,
   builds an installable engine package: `examples/engines/openferment-engine-mirror/`, the engine
   `mirror`, which returns the typed quantities a run gives it, their count, and the time its run
   took as a diagnostic. Installed into the service's environment, the service lists it, every
   conformance check passes, and its runs appear on the Runs screen with their provenance:

   ```
   cd core
   uv pip install --python .venv/bin/python \
       -c <(uv export --frozen --all-extras --no-hashes --no-emit-project --quiet) \
       -e ../examples/engines/openferment-engine-mirror
   uv run python -m openferment_core.engine.conform mirror
   cd ../examples/engines/openferment-engine-mirror && ../../../core/.venv/bin/python -m pytest
   ```

   `pnpm prove` runs this test on every run: it installs every package under `examples/engines/`
   held to `core/uv.lock`, step 10 makes the eight checks on each engine the service lists, and
   step 9's walk runs one thing of each example engine from the Runs screen and reads its run's
   provenance, outputs and diagnostics; at its end it leaves core's environment as it found it.

2. **An agent from the interface alone.** A builder who may read `docs/TOOLS.md`,
   `docs/api/openapi.json` and `.mcp.json`, and nothing else, writes a client
   (`examples/agents/record-reader/`) that starts the `openferment` MCP server in a project,
   through a running service, reads the project's records, writes one catalogue entry under its
   own name, `example-agent/0.1`, and reads back the audit row that names it:

   ```
   pnpm build && pnpm prove --keep   # prints the service's address, its project and its database
   uv run examples/agents/record-reader/record_reader.py --project <id> --service http://127.0.0.1:<port>
   ```

   It exits 0 when the entry and the audit row both name `example-agent/0.1`.

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
cd core && uv sync --frozen --all-extras && cd ..
pnpm db:migrate          # PostgreSQL named by OPENFERMENT_DATABASE_URL in core/.env
pnpm verify              # every gate, offline, with no key
pnpm build && pnpm prove # the proof on a database of its own, with no key and no network
```
