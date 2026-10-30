#!/bin/bash
# Bring the Mini up to main and restart the service (OF-BLD-012 §B.7).
# Run as yourself, from anywhere; it asks for your password once, to restart.
#
#   scripts/host/deploy.sh                    pull, install, build, restart, check health
#   scripts/host/deploy.sh --verify           the same, with the full offline gate first
#
# Guild writes review decisions into core/data/biorepo.json in this checkout,
# a committed file until stage 2 of alpha 2.0 moves them into PostgreSQL. A
# pull over uncommitted decisions could fail halfway, so deploy stops until a
# person commits and pushes them.
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
  die "core/data/biorepo.json holds review decisions made in Guild on this machine that are not committed yet. Commit and push it first: git add core/data/biorepo.json && git commit -m 'Guild decisions' && git push"
fi

if [ "$PULL" = 1 ]; then
  say "Pulling main"
  git pull --ff-only || die "this checkout and GitHub have diverged, usually over decisions committed here and not yet pushed. Push them, or rebase onto main, then deploy again"
fi

say "Installing packages"
pnpm install --frozen-lockfile
# Every extra: the service's own workers need them (sim for geneOS, fermOS
# and Proforma, rag for the hybrid lane, agent for the MCP server), and a
# sync is exact, so naming one extra would remove the others.
(cd core && uv sync --frozen --all-extras)

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
