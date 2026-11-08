#!/bin/bash
# Bring the Mini up to main and restart the service (OF-BLD-012 §B.7).
# Run as yourself, from anywhere; it asks for your password once, to restart.
#
#   scripts/host/deploy.sh                    pull, install (with each engine core/engines.local names), build, migrate, restart, check health, pnpm ready
#   scripts/host/deploy.sh --verify           the same, with pnpm verify (which builds) before the migration and the restart
#
# Since alpha 2.0 every record lives in PostgreSQL (ADR-001), and each deploy
# brings the database to the newest schema. core/data/biorepo.json holds the
# review decisions made here before then; the service no longer reads it, so
# decisions still in it are carried into a project first (`pnpm
# db:import-alpha1`), and deploy stops while the file differs from its
# committed version (docs/runbooks/live-host-install.md, step 5).
set -euo pipefail
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$REPO"

VERIFY=0 PULL=1 RESTART=1
for arg in "$@"; do
  case "$arg" in
    --verify) VERIFY=1 ;;
    --no-pull) PULL=0 ;;        # install.sh: build what is checked out
    --no-restart) RESTART=0 ;;  # install.sh: it starts the jobs itself
    *) die "unknown option $arg. Usage: deploy.sh [--verify]" ;;
  esac
done

refuse_unfinished_git

changed="$(git diff --name-only HEAD)"
if [ -n "$changed" ] && [ "$changed" != "core/data/biorepo.json" ]; then
  die "uncommitted changes in: ${changed//$'\n'/ }. A deploy pulls main over them. Commit or stash them first."
fi
if [ -n "$changed" ]; then
  [ -n "$(env_setting OPENFERMENT_DATABASE_URL)" ] ||
    die "core/data/biorepo.json holds review decisions made on this machine before alpha 2.0, which the service no longer reads, and core/.env names no database to carry them into yet. Run scripts/host/install.sh: it makes the database, names it in core/.env and stops here again (docs/runbooks/live-host-install.md, step 5)"
  die "core/data/biorepo.json holds review decisions made on this machine before alpha 2.0, which the service no longer reads. Carry them into a project first: copy the file outside the checkout, then pnpm db:migrate && pnpm db:import-alpha1 --name 'Alpha 1.0 records' --by '<your name>'. Once the import prints the project's id, put the file back as committed (git checkout -- core/data/biorepo.json) and run scripts/host/install.sh again (docs/runbooks/live-host-install.md, step 5)"
fi

if [ "$PULL" = 1 ]; then
  say "Pulling main"
  git pull --ff-only || die "this checkout and GitHub have diverged, usually over commits made here and not yet pushed. Push them, or rebase onto main, then deploy again"
fi

say "Installing packages"
pnpm install --frozen-lockfile
# Every extra: the service needs them (sim for the workers of geneOS, fermOS
# and Proforma, lit for the literature layer, agent for the MCP servers), and
# a sync is exact, so naming one extra would remove the others.
(cd core && uv sync --frozen --all-extras)
# A sync keeps only what core/uv.lock names: each engine this machine keeps
# beside it, named in core/engines.local, is installed again, every package
# the lock pins held at its locked version, so an engine moves no pin under
# the live service.
"$REPO/scripts/engines-local.sh" ||
  die "an engine core/engines.local names did not install again; the lines above say which. Mend its line, or take the engine out with its line and cd core && uv pip uninstall <distribution>"
# Each genome-scale model the shelf names, fetched once into core/data/models/
# and held to its pinned hash; a file already there at that hash is left as it
# is. The nightly job fails the night while one is missing.
(cd core && .venv/bin/python -m openferment_core.geneos fetch) ||
  echo "A model file did not fetch; the nightly job fails until pnpm geneos:fetch brings it"

if [ "$VERIFY" = 1 ]; then
  say "Running the offline gate (includes the build)"
  # The tests, the tools check and the smoke each make a database of their own
  # on the server OPENFERMENT_TEST_DATABASE_URL names, which each reads from the
  # environment. A deploy names it from the environment or core/.env, else the
  # server of the live database's address, else this Mac's PostgreSQL, each
  # reached as the address says (as yourself by default).
  OPENFERMENT_TEST_DATABASE_URL="$(env_setting OPENFERMENT_TEST_DATABASE_URL)"
  if [ -z "$OPENFERMENT_TEST_DATABASE_URL" ]; then
    named="$(env_setting OPENFERMENT_DATABASE_URL)"
    OPENFERMENT_TEST_DATABASE_URL="${named:+${named%/*}/openferment_test}"
  fi
  OPENFERMENT_TEST_DATABASE_URL="${OPENFERMENT_TEST_DATABASE_URL:-postgresql://$(id -un)@127.0.0.1:5432/openferment_test}"
  export OPENFERMENT_TEST_DATABASE_URL
  # The browser checks drive a Chromium; this fetches it the first time only.
  pnpm exec playwright install chromium
  pnpm verify
else
  say "Building the app"
  pnpm build
fi

# After the gate and the build, so a deploy that stops at either leaves the
# live database on the schema the running service reads.
say "Bringing the database to the newest schema"
(cd core && .venv/bin/python -m openferment_core.migrations migrate) ||
  die "the migration did not run; the lines above say why: PostgreSQL stopped, pgvector missing (brew install pgvector), or the address core/.env names (OPENFERMENT_DATABASE_URL) holds a role or database this PostgreSQL lacks"

if [ "$RESTART" = 1 ]; then
  [ -f "$DAEMONS/$SERVER.plist" ] || die "the service is not installed on this Mac yet. Run: scripts/host/install.sh"
  say "Restarting the service"
  sudo launchctl kickstart -k "system/$SERVER"
  wait_for_health
  say "Checking the live loop"
  run_ready
fi
