#!/bin/bash
# Bring the Mini up to main and restart the service (OF-BLD-012 §B.7).
# Run as yourself, from anywhere; it asks for your password once, to restart.
#
#   scripts/host/deploy.sh                    pull, install, build, restart, check health
#   scripts/host/deploy.sh --verify           the same, with the full offline gate first
#   scripts/host/deploy.sh --keep-decisions   first commit and push the review decisions
#                                             Guild wrote on this machine, then the same
#
# Guild writes review decisions into core/data/biorepo.json in this checkout.
# That file is committed, so pushing it is the backup (§B.8). A pull over
# uncommitted decisions could fail halfway, so deploy stops until they are
# committed, and --keep-decisions is the one-word way to do that.
set -euo pipefail
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"
cd "$REPO"

VERIFY=0 KEEP=0 PULL=1 RESTART=1
for arg in "$@"; do
  case "$arg" in
    --verify) VERIFY=1 ;;
    --keep-decisions) KEEP=1 ;;
    --no-pull) PULL=0 ;;        # install.sh: build what is checked out
    --no-restart) RESTART=0 ;;  # install.sh: it starts the jobs itself
    *) die "unknown option $arg. Usage: deploy.sh [--verify] [--keep-decisions]" ;;
  esac
done

refuse_unfinished_git
register_merge_driver

changed="$(git diff --name-only HEAD)"
if [ -n "$changed" ] && [ "$changed" != "core/data/biorepo.json" ]; then
  die "uncommitted changes in: ${changed//$'\n'/ }. A deploy pulls main over them. Commit or stash them first."
fi
if [ -n "$changed" ] && [ "$KEEP" = 0 ]; then
  die "core/data/biorepo.json holds review decisions made in Guild on this machine that are not committed yet. Run: scripts/host/deploy.sh --keep-decisions"
fi

if [ "$KEEP" = 1 ]; then
  if [ -n "$changed" ]; then
    say "Committing the review decisions made on this machine"
    git add core/data/biorepo.json
    git commit -m "BioRepo: review decisions from the Mini, $(date +%F)"
  fi
  # Decisions made elsewhere since are merged in by record (merge_biorepo.py).
  # If the two sides decided the same record differently, put the file back
  # the way this machine had it, so the service keeps reading valid JSON.
  if ! git pull --rebase; then
    git rebase --abort 2>/dev/null || true
    die "the records listed above were withdrawn on one machine and changed on the other, or decided at the same instant, which only a person can settle. This machine's decisions are kept, committed here and in the file the service reads. Make both machines agree on those records in Guild, then run deploy.sh --keep-decisions again"
  fi
  git push || die "the decisions are committed here but could not be pushed. Check this machine can push (pnpm ready), then run deploy.sh --keep-decisions again"
fi

if [ "$PULL" = 1 ]; then
  say "Pulling main"
  git pull --ff-only || die "this checkout and GitHub have diverged, usually over decisions committed here and not yet pushed. Run: scripts/host/deploy.sh --keep-decisions"
fi

say "Installing packages"
pnpm install --frozen-lockfile
(cd core && uv sync --frozen --extra dev)

say "Projecting the seed for the service"
pnpm export:corpus

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
