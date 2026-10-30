#!/bin/bash
# Bring the Mini up to main and restart the service (OF-BLD-012 §B.7).
# Run as yourself, from anywhere; it asks for your password once, to restart.
#
#   scripts/host/deploy.sh                    pull, install, migrate, build, restart, check health
#   scripts/host/deploy.sh --verify           the same, with the full offline gate first
#
# Since alpha 2.0 every record lives in PostgreSQL (ADR-001), and each deploy
# brings the database to the newest schema. core/data/biorepo.json holds the
# review decisions made here before then; the service no longer reads it, so
# decisions still in it are carried into a project first (`pnpm
# db:import-alpha1`), and deploy stops until they are.
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
  die "core/data/biorepo.json holds review decisions made on this machine before alpha 2.0, which the service no longer reads. Carry core/data into a project first: pnpm db:import-alpha1 --name 'Alpha 1.0 records' --by '<your name>'. Once the project reads right, put the file back as committed (git checkout -- core/data/biorepo.json) and deploy again"
fi

if [ "$PULL" = 1 ]; then
  say "Pulling main"
  git pull --ff-only || die "this checkout and GitHub have diverged, usually over commits made here and not yet pushed. Push them, or rebase onto main, then deploy again"
fi

say "Installing packages"
pnpm install --frozen-lockfile
# Every extra: the service's own workers need them (sim for geneOS, fermOS
# and Proforma, rag for the hybrid lane, agent for the MCP server), and a
# sync is exact, so naming one extra would remove the others.
(cd core && uv sync --frozen --all-extras)

say "Bringing the database to the newest schema"
(cd core && .venv/bin/python -m openferment_core.db migrate) ||
  die "the migration did not run; the lines above say why. Is PostgreSQL running, and does core/.env name it (OPENFERMENT_DATABASE_URL)?"

if [ "$VERIFY" = 1 ]; then
  say "Running the offline gate (includes the build)"
  # The browser checks drive a Chromium; this fetches it the first time only.
  pnpm exec playwright install chromium
  pnpm verify
else
  say "Building the app"
  pnpm build
fi

if [ "$RESTART" = 1 ]; then
  [ -f "$DAEMONS/$SERVER.plist" ] || die "the service is not installed on this Mac yet. Run: scripts/host/install.sh"
  say "Restarting the service"
  sudo launchctl kickstart -k "system/$SERVER"
  wait_for_health
  say "Checking the live loop"
  run_ready
fi
