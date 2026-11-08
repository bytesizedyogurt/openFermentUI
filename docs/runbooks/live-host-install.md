# Installing openFerment on the live host

Alpha 2.1, stage E (execution prompt of 2 November 2026, §3), held to the tree again at alpha 2.2,
stage G (8 November 2026): the live instance is one Mac mini serving its owner on loopback
(CLAUDE.md, working assumptions). Both sessions ran in a Linux container, so nothing here has run
on the Mini; the scripts it calls have run as `bash -n`, under ShellCheck 0.11.0 and against
stand-ins for Homebrew and the PostgreSQL tools on Linux's bash 5 (PROGRESS.md, Known debts). Follow it in order
the first time; afterwards `scripts/host/deploy.sh` alone brings the Mini to `main`.

Every step runs as yourself in Terminal; a command that needs root carries its own `sudo`, and
`install.sh` stops when started with `sudo`. Nothing here prints the key.

## 0. What the Mini needs first

| Need | How | Check |
|---|---|---|
| macOS with Homebrew | https://brew.sh | `brew --version` |
| Node and pnpm | `brew install node pnpm` | `node --version` (the build has run on Node 22 in this build's container and on Node 20 in CI), `pnpm --version` |
| uv, with Python 3.13 | `brew install uv && uv python install 3.13` | `uv python find 3.13` names it; the service has run on 3.12 and 3.13 |
| PostgreSQL 17 with pgvector, started at power-on | `brew install postgresql@17 pgvector && sudo brew services start --sudo-service-user="$(id -un)" postgresql@17` | `"$(brew --prefix postgresql@17)/bin/pg_isready" -h 127.0.0.1` answers "accepting connections" |
| Graphviz, for Proforma's flowsheet diagrams | `brew install graphviz` | `dot -V`; without it Proforma lists a flowsheet's units in run order |
| Tailscale's background service, signed in | `brew install tailscale && sudo brew services start tailscale && sudo tailscale up` | `tailscale status` lists the Mini |
| The checkout at `~/openferment`, outside Desktop, Documents, Downloads and iCloud Drive | `git clone https://github.com/bytesizedyogurt/openFermentUI ~/openferment`; a Mini that ran alpha 1.0 has it already (below) | macOS privacy protection stops background jobs reading those four places, and `install.sh` checks |

Homebrew keeps `postgresql@17` keg-only, so its tools live under `$(brew --prefix postgresql@17)/bin`,
where `install.sh` finds them. `sudo brew services` installs the service as a LaunchDaemon, which
runs from power-on, before anyone logs in, as the server's own LaunchDaemon runs, and
`--sudo-service-user` runs it as you, the owner of its data directory (PostgreSQL refuses to run as
root). This build read the flag in Homebrew's source and could not run it: confirm it on the Mini
with `brew services --help`, which lists `--sudo-service-user`. A Mini that started PostgreSQL with
`brew services` alone runs it from your login; `install.sh` says so, and `brew services stop
postgresql@17` followed by the `sudo` line above moves it. Tailscale's background service likewise
runs from power-on, and `install.sh` says so when it finds the Tailscale app running in its place.

Homebrew's formulae for `postgresql@17` and `pgvector` carry bottles for Apple Silicon alone, so on
an Intel Mini `brew install` builds both from source with the Command Line Tools (run
`xcode-select --install` first), and pgvector's build brings in `postgresql@18` as a build
dependency. `brew info postgresql@17` says `bottled` beside the version when a bottle serves this
Mac.

A Mini that ran alpha 1.0 holds its checkout at `~/openferment` already (alpha 1.0's README cloned
it there), and `core/data/` there holds every alpha 1.0 record step 5 carries. Stop alpha 1.0's two
jobs with its own install script, keep a copy of its records, and bring the checkout to `main`:

```
cd ~/openferment
scripts/host/install.sh --uninstall
cp -Rp core/data ~/openferment-alpha-1.0-data
git pull --ff-only
```

`--uninstall` keeps the checkout and `core/data`, and step 3 installs both jobs again. `main` has
left `core/data/biorepo.json` as alpha 1.0 committed it, so the pull keeps the review decisions in
the file for step 5. Leave alpha 1.0's `scripts/host/deploy.sh` unrun from here on: its
`--keep-decisions` commits the decisions and pushes them to GitHub, after which `deploy.sh` no
longer stops for step 5. When the pull stops, saying the checkout holds commits of its own or local
changes it would overwrite, bring the checkout to `main` with `git fetch origin && git reset --hard
origin/main` (the copy keeps every record) and give step 5's import the copy (step 5 says how).

## 1. The key, and the account's limit

1. Make an API key in the Anthropic console for the workspace openFerment should spend in.
2. In the console's limits, set a monthly limit you mean to keep. **The account's own limit is
   separate from openFerment's daily cap**: on 2 November 2026 the account behind this build's key
   reached its limit, and every call answered HTTP 400 until the date it named (PROGRESS.md,
   Blockers). openFerment now says so in those words.
3. Write `core/.env` (it is gitignored; keep it mode 600). The block makes it from the example when
   it is absent, leaving out the example's database line, which names a developer's database
   (`openferment_dev`), and keeps a `core/.env` already there, such as the one an alpha 1.0 Mini
   holds with its key; `install.sh` writes the live database line in step 3:

   ```
   cd ~/openferment/core
   [ -e .env ] || (umask 077 && sed '/^OPENFERMENT_DATABASE_URL=/d' .env.example > .env)
   chmod 600 .env
   ```

   Write the key on the file's `ANTHROPIC_API_KEY=` line, the one line of that name, and set the
   two budgets:

   ```
   ANTHROPIC_API_KEY=<the key>
   OPENFERMENT_DAILY_BUDGET_USD=150
   OPENFERMENT_ASK_BUDGET_USD=8
   ```

   Every task family runs on its default route while the model settings stay out of `core/.env`;
   `core/.env.example` lists each default and the measure it rests on. A model setting lays over
   the defaults once it is set: `OPENFERMENT_MODEL` with `OPENFERMENT_FALLBACK_MODEL` sets the
   models of `plan`, `explain` and `extract`, `OPENFERMENT_EFFORT` their effort, and
   `OPENFERMENT_INDEX_MODEL` the first model of `index`; `judge` and `index` keep their effort
   under all three. `OPENFERMENT_ROUTES` (the routing table as JSON, `core/.env.example` shows its
   shape) sets the families it names, their effort among them. A `core/.env` kept from alpha 1.0
   may hold model settings of its own (alpha 1.0's example offered `OPENFERMENT_EFFORT=medium`, for
   one): take out its `OPENFERMENT_MODEL`, `OPENFERMENT_FALLBACK_MODEL`, `OPENFERMENT_INDEX_MODEL`,
   `OPENFERMENT_EFFORT` and `OPENFERMENT_ROUTES` lines to keep the defaults.
   `grep -nE '^OPENFERMENT_([A-Z_]*MODEL|EFFORT|ROUTES)=' .env` lists them and prints no key, and
   `pnpm ready`'s `model` row names the plan route's models and its effort. The install script
   writes the database line in step 3, and step 6 says which project `OPENFERMENT_PROJECT` names.

## 2. Install the packages and build

```
cd ~/openferment
pnpm install --frozen-lockfile
cd core && uv sync --frozen --all-extras --python 3.13 && cd ..
pnpm geneos:fetch
pnpm build
```

`uv sync --frozen --all-extras` installs `core/uv.lock` as committed, with every extra: `sim`
(BioSTEAM and the workers), `lit` (Sci RAG Kit with FastEmbed, and the kit's OpenAI-compatible
adapter for a local model), `agent` (the MCP servers) and `dev` (the tests `deploy.sh --verify`
runs). `--python 3.13` makes `core/.venv` on Python 3.13, replacing an environment alpha 1.0 made
on another Python, and every later sync keeps it (step 7 says how to make it again). `pnpm geneos:fetch`
fetches the genome-scale models geneOS computes on into `core/data/models/`; the nightly job checks
each against its pinned hash and fails the night while one is missing. The first FastEmbed use
fetches the embedding model from Hugging Face once into `~/.cache/fastembed`
(`FASTEMBED_CACHE_PATH` moves it).

## 3. The database, the jobs, the network

```
scripts/host/install.sh
```

In order, it: checks the tools and where the checkout lives; finds Homebrew's PostgreSQL, checks
that it answers on `127.0.0.1`, says so when it starts at your login (step 0), and, when no
database is named in `core/.env`, checks for pgvector, makes the database `openferment` and names
it there; runs `deploy.sh --no-pull --no-restart`, which installs the packages and each engine
`core/engines.local` names (step 7), fetches a genome-scale model the shelf gained, builds the app
and migrates both schemas (`openferment` and the kit's `sci_rag`), so step 2 is done again here and
does no harm; sets the power settings an always-on machine needs (never sleep, restart after a
power failure, wake for network access); installs two LaunchDaemons, the server (at power-on,
before anyone logs in) and the 03:00 nightly job (the night's extraction, the nightly checks, and
Guild's check proposals with their briefs); waits for `/api/health`; publishes the port to your own
devices with `tailscale serve`; and runs `pnpm ready` (step 4). The service binds `127.0.0.1` and
nothing else; `tailscale serve` is how your phone and laptop reach it, and a request through
Tailscale Funnel, from the public internet, changes nothing and may not name a key.

On a Mini that ran alpha 1.0, `install.sh` stops at its deploy step while `core/data/biorepo.json`
holds review decisions made on this Mini (the committed file holds none). Step 5 carries them into
a project and runs `install.sh` again; step 4 follows it.

`scripts/host/install.sh --uninstall` stops both jobs, removes them and turns off `tailscale
serve`'s HTTPS port; the checkout, `core/.env` and the database stay.

## 4. Check it

```
pnpm ready
```

reads, one row a check, whether the service can run: `✓` ready, `!` works with a gap worth
knowing, `✗` the live loop fails here, `·` skipped. Each `!` and `✗` says what to do, and the
command exits 1 on any `✗`. The rows: `key`; `app`, the build; `data`, the `openferment` schema at
its newest revision, which the row names; `intake`; `literature`, pgvector and the kit's `sci_rag`
schema at its newest revision; `embedder`; `rag`; `models`, the files `pnpm geneos:fetch` fetched;
`artifacts`; `spend`, against the daily cap; `workers`; `graphviz`; one `engine <name>` row for
each engine of the entry-point group `openferment.engines` (`biosteam`, `kinetics` and `train`,
with each engine `core/engines.local` keeps); `model` and `roles`, the routes' models through the
Models API; `europepmc`; `huggingface`; and `service`, the server on `127.0.0.1:8000`. A fresh Mini
shows `!` on `embedder` until the first document is collected (FastEmbed fetches its model file
then), on `intake` until a project holds a document, on `rag` until `core/.env` holds an
`OPENFERMENT_RAG_KEY` (another program searching the literature through `/rag` needs one; the app
runs without it), and on each engine row until its checks have run here. Where a row or a command
says `pnpm db:up`, which starts the development database in Docker, start the Mini's own
PostgreSQL with `sudo brew services start --sudo-service-user="$(id -un)" postgresql@17`; its
address is the one `install.sh` wrote in `core/.env`. The last line names the lane: `full` with a
key the Models API accepted and Europe PMC answering, `model-only` with that key alone, `none`
otherwise.

The `model` row asks the free Models API, which an account past its own usage limit still
answers. `pnpm ready --probe` adds the `probe` row: one minimal call on the `index` route, the one
row that sees that limit, and it spends a few tokens.

Each engine row names the command that checks it here. Run them once from `core/`, and again when
an engine's version moves:

```
cd ~/openferment/core
.venv/bin/python -m openferment_core.engine.conform biosteam
.venv/bin/python -c 'from openferment_core.fermos_engine import write_placeholder_inputs as w; w("/tmp/kinetics-inputs.json", by="<your name>")'
.venv/bin/python -m openferment_core.engine.conform kinetics --inputs /tmp/kinetics-inputs.json
```

and, once a project holds a train (saved in pureOS's Builder), `.venv/bin/python -m
openferment_core.engine.conform train --project <the project's id>`. Each makes the eight checks of
`docs/api/engines.md` on a database of its own, made on the same server and dropped after, and
keeps its verdict as one row of `openferment`, where the engine's row reads it.

Then, from another device on your tailnet, open the address `install.sh` printed (`https://<the
Mini's name>.<your tailnet>.ts.net`). Home lists the projects.

## 5. Carry alpha 1.0's records, once

If the Mini ran alpha 1.0, its review decisions are in `core/data/biorepo.json`, which the service
no longer reads, and `install.sh` stops at its deploy step until they are in a project. By then it
has made the database and named it in `core/.env`. Keep a copy of the file, migrate the database
and carry the records:

```
cd ~/openferment
cp core/data/biorepo.json ~/biorepo-alpha-1.0.json
pnpm db:migrate && pnpm db:import-alpha1 --name "Alpha 1.0 records" --by "<your name>"
```

The import prints the new project's id and what it carried, one count a kind; the decisions count
is the number of decisions in the file. A line beginning `refused:` says why, and the import has
written nothing. Once it has carried them, put the file back as committed and install again:

```
git checkout -- core/data/biorepo.json
scripts/host/install.sh
```

Then go to step 4, open the project from Home and check that it reads right; step 6 says which
project `OPENFERMENT_PROJECT` names. The copy in your home folder keeps the decisions as alpha 1.0
left them, and the other files the import read stay under `core/data/`, where git ignores them.

A checkout step 0 brought to `main` with `git reset --hard` holds the committed file, so
`install.sh` runs through, its migration done; carry the records from step 0's copy with `pnpm
db:import-alpha1 --name "Alpha 1.0 records" --by "<your name>" --data ~/openferment-alpha-1.0-data`.

## 6. The first real project

On Home, make a project; its address ends in `#/p/<its id>`. Set `OPENFERMENT_PROJECT=<its id>` in
`core/.env` for the project whose documents the nightly job extracts: the extraction waits while
none is named, and once one is named the whole job (the extraction, the nightly checks, Guild's
check proposals and their briefs) acts in that project alone; while none is named, the checks and
proposals act in every project. On the project's Intake page collect the documents by identifier
(the ethanol sources are `docs/corpus/ethanol-sources.txt`), extract each from the documents list,
and review the candidates in BioRepo. Studies runs the things of every engine registered here (the
library's plants and the composed flowsheet on `biosteam`, and each other engine's) and lists every
engine run; a run's page makes a scenario of your own values and a runbook; Flowsheets imports SFF
files; the catalogues screen (`/catalogues`) keeps the project's strains, products, Guild's skills
and Primer's lessons. `docs/reports/live-questions-2026-11.md` is a worked example, done in a
container.

## 7. Afterwards

| Task | Command |
|---|---|
| Bring the Mini to `main` and restart | `scripts/host/deploy.sh` (pulls, installs the packages and each engine `core/engines.local` names, fetches a genome-scale model the shelf gained, builds, migrates, restarts, checks health, runs `pnpm ready`) |
| The same, with the full offline gate before the migration and the restart | `scripts/host/deploy.sh --verify` (`pnpm verify`'s sixteen stages, about twenty minutes in this build's container; its tests make their databases on the server `OPENFERMENT_TEST_DATABASE_URL` names, else on the live database's server, else on this Mac's PostgreSQL as you) |
| Keep an engine installed beside the lock | its package directory, one a line, in `core/engines.local` (git ignores the file), each directory outside Desktop, Documents, Downloads and iCloud Drive, as the checkout is; `scripts/host/deploy.sh` then installs it again after each sync and restarts the service (`docs/api/engines.md`) |
| The proof, on a database of its own | from `~/openferment`: `pnpm exec playwright install chromium` once, then `pnpm build && OPENFERMENT_TEST_DATABASE_URL="postgresql://$(id -un)@127.0.0.1:5432/openferment_test" pnpm prove` (steps 1 to 10, offline; step 9 walks the built app in Chromium, step 10 makes every engine's conformance checks). For its run it installs each package under `examples/engines/` into `core/.venv` and leaves the environment as it found it, so run it while no deploy runs |
| Restart the service by hand, after a change to `core/.env` among other times | `sudo launchctl kickstart -k system/com.umutuzo.openferment`; the nightly job is `com.umutuzo.openferment.nightly`, and `scripts/host/nightly.sh` runs its work by hand |
| Make `core/.venv` again, after it was removed | `cd ~/openferment/core && uv sync --frozen --all-extras --python 3.13`; a deploy's sync keeps the environment's Python, and one made with no `--python` takes the newest Python uv finds |
| The service's log, and the nightly job's | `~/Library/Logs/openferment/server.log`, `~/Library/Logs/openferment/nightly.log` |
| A backup | not set up: choose where a dump goes, then add a step to `scripts/host/nightly.sh` in a commit on `main`, which the next `scripts/host/deploy.sh` brings: `"$(brew --prefix postgresql@17)/bin/pg_dump" -h 127.0.0.1 openferment > <there>`, the keg's full path, since Homebrew keeps `pg_dump` off the jobs' PATH. An edit made in the Mini's checkout stops each deploy at its check for uncommitted changes (PROGRESS.md, Blockers) |
| The tags alpha 1.0 and alpha 2.1 | once, from any machine: `git fetch origin && git tag alpha-1.0 d19224ff0b6eb809b21492d1b7a2e8fd895a0f44 && git tag alpha-2.1 fa1b7448a5b5e5a2b943b3fc9546f8a420a8ef10 && git push origin alpha-1.0 alpha-2.1` (PROGRESS.md, Blockers) |

## What is not covered

- `pnpm db:up` (compose.yaml, Docker's `pgvector/pgvector:pg17`) has never run in this build; CI
  runs the same image as a service container. On the Mini, Homebrew's PostgreSQL is the database.
- No step here has run on macOS in this build. The first install is the test of `install.sh`'s
  PostgreSQL steps (the keg's path, the service started at power-on, pgvector); a failure there
  says what it needs in words, and its fix belongs in `scripts/host/` with a line in PROGRESS.md.
