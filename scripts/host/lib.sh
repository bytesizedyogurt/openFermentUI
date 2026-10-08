# Shared by install.sh and deploy.sh (OF-BLD-012 Appendix B). Sourced, never run,
# so its names are used by the scripts that source it.
# shellcheck disable=SC2034
# shellcheck shell=bash

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVER=com.umutuzo.openferment
NIGHTLY=com.umutuzo.openferment.nightly
DAEMONS="${OPENFERMENT_LAUNCHD_DIR:-/Library/LaunchDaemons}"  # the override is for test_host
LOGS="$HOME/Library/Logs/openferment"

# Host and port: what the environment says, else what the installed server
# job was given, else loopback:8000. So a deploy restarts and checks the job
# on the address it was installed with, whatever this shell has set.
INSTALLED_HOST="" INSTALLED_PORT=""
if [ -r "$DAEMONS/$SERVER.plist" ] && [ -x "$REPO/core/.venv/bin/python" ]; then
  read -r INSTALLED_HOST INSTALLED_PORT < <(
    "$REPO/core/.venv/bin/python" "$REPO/scripts/host/launchd.py" --read "$DAEMONS/$SERVER.plist" 2>/dev/null
  ) || true
fi
PORT="${OPENFERMENT_PORT:-${INSTALLED_PORT:-8000}}"
HOST="${OPENFERMENT_HOST:-${INSTALLED_HOST:-127.0.0.1}}"

# Where this machine asks for /api/health: loopback when the server listens
# there or everywhere, else the one address it listens on. launchd.py's
# poll_host is the same rule for `pnpm ready`; test_host holds them equal.
poll_host() {
  case "$1" in
    127.0.0.1 | localhost | 0.0.0.0 | "") echo 127.0.0.1 ;;
    :: | ::1) echo "[::1]" ;;
    *:*) echo "[$1]" ;;
    *) echo "$1" ;;
  esac
}
POLL="$(poll_host "$HOST")"

# install.sh only. The host is what OPENFERMENT_HOST says this time, else
# loopback; never what an earlier install was given, because listening wider
# than loopback is a choice made each time, never a default that lingers.
install_address() {
  HOST="${OPENFERMENT_HOST:-127.0.0.1}"
  POLL="$(poll_host "$HOST")"
  if [ -n "$INSTALLED_HOST" ] && [ "$INSTALLED_HOST" != "$HOST" ]; then
    echo "The server listened on $INSTALLED_HOST and will now listen on $HOST. Set OPENFERMENT_HOST to choose otherwise."
  fi
}

say() { printf '\n── %s\n' "$*"; }
die() { printf '\n✗ %s\n' "$*" >&2; exit 1; }

# Ask /api/health until it answers, for up to 30 seconds, and print what it says.
wait_for_health() {
  local body
  for _ in $(seq 1 30); do
    if body="$(curl -fsS "http://${POLL}:${PORT}/api/health" 2>/dev/null)"; then
      printf '%s\n' "$body"
      return 0
    fi
    sleep 1
  done
  die "the service did not answer /api/health within 30 s. Its log: tail -50 \"$LOGS/server.log\""
}

# Teach this clone to merge core/data/biorepo.json by record (.gitattributes
# names the driver; scripts/host/merge_biorepo.py is it). Idempotent.
# The same registration `pnpm install` makes (scripts/register-merge-driver.mjs).
register_merge_driver() {
  git -C "$REPO" config merge.biorepo.name "BioRepo decisions, merged by record"
  git -C "$REPO" config merge.biorepo.driver "sh scripts/host/merge-biorepo %O %A %B"
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
  (cd "$REPO/core" && OPENFERMENT_PORT="$PORT" OPENFERMENT_POLL_HOST="$POLL" .venv/bin/python -m openferment_core.ready) ||
    echo "Something above needs fixing. Run pnpm ready again once it is."
}

# Tailscale's CLI, as yourself, else with sudo: the background-service
# variant (tailscaled) answers changes from root or its operator only.
tailscale_cli() {
  tailscale "$@" 2>/dev/null || sudo tailscale "$@"
}

# True when core/.env holds something shaped like a real key. Never prints it.
has_key() {
  [ -f "$REPO/core/.env" ] &&
    grep -qE '^ANTHROPIC_API_KEY=sk-ant-' "$REPO/core/.env" &&
    ! grep -qE '^ANTHROPIC_API_KEY=sk-ant-\.\.\.\s*$' "$REPO/core/.env"
}
