# Shared by install.sh and deploy.sh (OF-BLD-012 Appendix B). Sourced, never run,
# so its names are used by the scripts that source it.
# shellcheck disable=SC2034
# shellcheck shell=bash

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVER=com.umutuzo.openferment
NIGHTLY=com.umutuzo.openferment.nightly
DAEMONS=/Library/LaunchDaemons
PORT="${OPENFERMENT_PORT:-8000}"
HOST="${OPENFERMENT_HOST:-127.0.0.1}"
LOGS="$HOME/Library/Logs/openferment"

say() { printf '\n── %s\n' "$*"; }
die() { printf '\n✗ %s\n' "$*" >&2; exit 1; }

# Ask /api/health until it answers, for up to 30 seconds, and print what it says.
wait_for_health() {
  local body
  for _ in $(seq 1 30); do
    if body="$(curl -fsS "http://127.0.0.1:${PORT}/api/health" 2>/dev/null)"; then
      printf '%s\n' "$body"
      return 0
    fi
    sleep 1
  done
  die "the service did not answer /api/health within 30 s. Its log: tail -50 \"$LOGS/server.log\""
}

# Teach this clone to merge core/data/biorepo.json by record (.gitattributes
# names the driver; scripts/host/merge_biorepo.py is it). Idempotent.
register_merge_driver() {
  local py="$REPO/core/.venv/bin/python"
  [ -x "$py" ] || py=python3
  git -C "$REPO" config merge.biorepo.name "BioRepo decisions, merged by record"
  git -C "$REPO" config merge.biorepo.driver "\"$py\" scripts/host/merge_biorepo.py %O %A %B"
}

# Stop when a rebase or merge was left half-done: the decisions file may hold
# conflict markers, and building on it would commit them.
refuse_unfinished_git() {
  local p
  for p in rebase-merge rebase-apply MERGE_HEAD; do
    if [ -e "$(git -C "$REPO" rev-parse --git-path "$p")" ]; then
      die "a git rebase or merge was left unfinished in $REPO. Run: git rebase --abort (or git merge --abort), then deploy again"
    fi
  done
}

# pnpm ready, from the service's own environment. Prints its report and never
# stops the caller: install and deploy have done their work by the time it runs.
run_ready() {
  (cd "$REPO/core" && OPENFERMENT_PORT="$PORT" .venv/bin/python -m openferment_core.ready) ||
    echo "Something above needs fixing. Run pnpm ready again once it is."
}

# True when core/.env holds something shaped like a real key. Never prints it.
has_key() {
  [ -f "$REPO/core/.env" ] &&
    grep -qE '^ANTHROPIC_API_KEY=sk-ant-' "$REPO/core/.env" &&
    ! grep -qE '^ANTHROPIC_API_KEY=sk-ant-\.\.\.\s*$' "$REPO/core/.env"
}
