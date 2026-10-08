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

# True when core/.env holds something shaped like a real key. Never prints it.
has_key() {
  [ -f "$REPO/core/.env" ] &&
    grep -qE '^ANTHROPIC_API_KEY=sk-ant-' "$REPO/core/.env" &&
    ! grep -qE '^ANTHROPIC_API_KEY=sk-ant-\.\.\.\s*$' "$REPO/core/.env"
}
