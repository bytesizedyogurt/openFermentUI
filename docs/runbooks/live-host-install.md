# Installing openFerment on the live host

Alpha 2.1, stage E (execution prompt of 2 November 2026, §3): the live instance is one Mac mini
serving its owner on loopback (CLAUDE.md, working assumptions). This session ran in a Linux
container, so nothing here has run on the Mini; the scripts it calls have run only as `bash -n`
(PROGRESS.md, Known debts). Follow it in order the first time; afterwards `scripts/host/deploy.sh`
alone brings the Mini to `main`.

Every step runs as yourself in Terminal, from the checkout, never with `sudo` (the scripts ask for
your password where they need it). Nothing here prints the key.

## 0. What the Mini needs first

| Need | How | Check |
|---|---|---|
| macOS with Homebrew | https://brew.sh | `brew --version` |
| Node 20 and pnpm | `brew install node pnpm` | `node --version`, `pnpm --version` |
| uv (Python) | `brew install uv` | `uv --version` (the service runs on 3.12 or 3.13) |
| PostgreSQL 17 with pgvector | `brew install postgresql@17 pgvector && brew services start postgresql@17` | `pg_isready -h 127.0.0.1` answers "accepting connections" |
| Tailscale, signed in | the Mac App Store or `brew install tailscale` | `tailscale status` lists the Mini |
| The checkout outside Desktop, Documents and Downloads | `git clone https://github.com/bytesizedyogurt/openFermentUI ~/openFermentUI` | macOS privacy protection stops background jobs reading those three folders |

## 1. The key, and the account's limit

1. Make an API key in the Anthropic console for the workspace openFerment should spend in.
2. In the console's limits, set a monthly limit you mean to keep. **The account's own limit is
   separate from openFerment's daily cap**: on 2 November 2026 the account behind this build's key
   reached its limit, and every call answered HTTP 400 until the date it named (PROGRESS.md,
   Blockers). openFerment now says so in those words.
3. Write `core/.env` (it is gitignored; keep it mode 600):

   ```
   cd ~/openFermentUI/core
   cp .env.example .env && chmod 600 .env
   ```

   and set, at least:

   ```
   ANTHROPIC_API_KEY=<the key>
   OPENFERMENT_MODEL=claude-opus-5-5
   OPENFERMENT_FALLBACK_MODEL=claude-sonnet-5-5
   OPENFERMENT_INDEX_MODEL=claude-haiku-5-5
   OPENFERMENT_EFFORT=high
   OPENFERMENT_DAILY_BUDGET_USD=150
   OPENFERMENT_ASK_BUDGET_USD=6
   ```

   `OPENFERMENT_ROUTES` (the routing table as JSON, `core/.env.example` shows its shape) is
   optional; the four model settings above set every family. `docs/reports/model-routing-2026-11.md`
   recommends a judge route with Sonnet behind Opus, since Opus declines some yeast answers.
   The database line is written by the install script in step 3 when it is absent.

## 2. Install the packages and build

```
cd ~/openFermentUI
pnpm install --frozen-lockfile
cd core && uv sync --all-extras && cd ..
pnpm build
```

`uv sync --all-extras` installs every extra the service needs: `sim` (BioSTEAM and the workers),
`lit` (Sci RAG Kit with FastEmbed, and the kit's OpenAI-compatible adapter for a local model),
`agent` (the MCP servers). The first FastEmbed use fetches the embedding model from Hugging Face
once into `.cache/fastembed`.

## 3. The database, the jobs, the network

```
scripts/host/install.sh
```

In order, it: checks the tools and where the checkout lives; makes the database `openferment` on
`127.0.0.1` and names it in `core/.env` when no database is named there; runs `deploy.sh
--no-pull --no-restart`, which installs the packages, migrates both schemas (`openferment` and the
kit's `sci_rag`) and builds the app, so step 2 is done again here and does no harm; sets the power
settings an always-on machine needs (never
sleep, restart after a power failure, wake for network access); installs two LaunchDaemons, the
server (at power-on, before anyone logs in) and the 03:00 extraction; waits for `/api/health`; and
publishes the port to your own devices with `tailscale serve`. The service binds `127.0.0.1` and
nothing else; `tailscale serve` is how your phone and laptop reach it, and a request through
Tailscale Funnel, from the public internet, changes nothing and may not name a key.

`scripts/host/install.sh --uninstall` stops both jobs and removes them; the checkout, `core/.env`
and the database stay.

## 4. Check it

```
pnpm ready
```

reads, in rows, whether the service can run: the database and both schemas, pgvector, the
embedder, the model routes and the key. Every row should be `ok` or a `warn` you understand.
`pnpm ready` checks the key by listing the models, which an account past its usage limit still
answers; the first model call says if the limit is reached.

Then, from another device on your tailnet, open the address `install.sh` printed (`https://<the
Mini's name>.<your tailnet>.ts.net`). Home lists the projects.

## 5. Carry alpha 1.0's records, once

If the Mini ran alpha 1.0, its review decisions are in `core/data/biorepo.json`, which the service
no longer reads. Before the first deploy:

```
pnpm db:import-alpha1 --name "Alpha 1.0 records" --by "<your name>"
```

It prints the new project's id; set `OPENFERMENT_PROJECT=<that id>` in `core/.env` for the nightly
extraction. Once the project reads right, put the file back as committed
(`git checkout -- core/data/biorepo.json`); `deploy.sh` stops until that is done.

## 6. The first real project

On Home, make a project; on its Intake page collect the documents by identifier (the ethanol
sources are `docs/corpus/ethanol-sources.txt`), extract each from the documents list, and review
the candidates in BioRepo. Studies runs any plant of the installed package or the composed
flowsheet; a run's page makes a scenario of your own values and a runbook; Flowsheets imports SFF
files. `docs/reports/live-questions-2026-11.md` is a worked example, done in a container.

## 7. Afterwards

| Task | Command |
|---|---|
| Bring the Mini to `main` and restart | `scripts/host/deploy.sh` (pulls, installs, migrates, builds, restarts, checks health) |
| The same, with the full offline gate first | `scripts/host/deploy.sh --verify` |
| The service's log, and the nightly extraction's | `~/Library/Logs/openferment/server.log`, `~/Library/Logs/openferment/nightly.log` |
| A backup | not set up: choose where a dump goes, then add `pg_dump openferment > <there>` to `scripts/host/nightly.sh` (PROGRESS.md, Blockers) |
| The tag alpha 1.0 | once, from any machine: `git fetch origin && git tag alpha-1.0 d19224ff0b6eb809b21492d1b7a2e8fd895a0f44 && git push origin alpha-1.0` |

## What is not covered

- `pnpm db:up` (Docker's `pgvector/pgvector:pg17`) has not run anywhere but CI; on the Mini,
  Homebrew's PostgreSQL is the database.
- No step here has run on macOS in this build. The first install is the test of `install.sh`'s
  PostgreSQL steps; a failure there says what it needs in words, and its fix belongs in
  `scripts/host/` with a line in PROGRESS.md.
