# Shared by install.sh, deploy.sh and nightly.sh (OF-BLD-012 Appendix B). Sourced, never run,
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

# Stop when a rebase or merge was left half-done: a file may hold conflict
# markers, and building on it would serve them.
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
    ! grep -qE '^ANTHROPIC_API_KEY=sk-ant-\.\.\.[[:space:]]*$' "$REPO/core/.env"
}

# A setting from core/.env, by name, for the names that are not the key
# (OPENFERMENT_DATABASE_URL, OPENFERMENT_PROJECT, OPENFERMENT_TEST_DATABASE_URL):
# the environment's value as it stands when it has one, else the file's last
# line for it, read as python-dotenv reads it (an `export` before the name,
# blanks around `=`, one pair of quotes, a ` #` comment after a bare value and
# a carriage return taken off); empty when neither names it, and the status 0
# either way, so a caller under `set -e` may assign it. Never reads the key.
env_setting() {
  local name="$1" value=""
  if [ -n "${!name:-}" ]; then
    value="${!name}"
  elif [ -f "$REPO/core/.env" ]; then
    value="$(grep -E "^[[:space:]]*(export[[:space:]]+)?${name}[[:space:]]*=" "$REPO/core/.env" | tail -1 | cut -d= -f2- | tr -d '\r')" || true
    value="${value#"${value%%[![:space:]]*}"}"
    case "$value" in
      \"*) value="${value#\"}"; value="${value%%\"*}" ;;
      \'*) value="${value#\'}"; value="${value%%\'*}" ;;
      *) value="${value%%[[:space:]]#*}"; value="${value%"${value##*[![:space:]]}"}" ;;
    esac
  fi
  printf '%s' "$value"
}

# PostgreSQL, the one store (alpha 2.0, ADR-001): Homebrew's postgresql@17
# with pgvector, answering on this Mac, a database named `openferment`, and
# its address in core/.env. Makes what is missing and says what it made.
ensure_database() {
  # Homebrew keeps postgresql@17 keg-only: its tools live under its own prefix,
  # which goes first on the path whenever the formula is installed.
  local keg
  if command -v brew >/dev/null && keg="$(brew --prefix --installed postgresql@17 2>/dev/null)"; then
    PATH="$keg/bin:$PATH"
  fi
  # `sudo brew services` starts it at power-on, as the server's LaunchDaemon
  # starts, and --sudo-service-user runs it as the owner of its data directory.
  local start
  start="sudo brew services start --sudo-service-user=$(id -un) postgresql@17"
  command -v pg_isready >/dev/null ||
    die "PostgreSQL is not installed. Run: brew install postgresql@17 pgvector && $start"
  pg_isready -q -h 127.0.0.1 ||
    die "PostgreSQL is not answering on 127.0.0.1. Run: $start"
  # Homebrew's LaunchAgent starts PostgreSQL at your login; an always-on host needs its LaunchDaemon.
  if [ -f "$HOME/Library/LaunchAgents/homebrew.mxcl.postgresql@17.plist" ] &&
    [ ! -f /Library/LaunchDaemons/homebrew.mxcl.postgresql@17.plist ]; then
    echo "PostgreSQL here starts at your login, so after a power cut the service waits for a login to reach its database."
    echo "For an always-on host: brew services stop postgresql@17 && $start"
  fi
  local named vector
  named="$(env_setting OPENFERMENT_DATABASE_URL)"
  case "$named" in
    */openferment_dev | */openferment_dev\?* | *://openferment:openferment@*)
      die "OPENFERMENT_DATABASE_URL names the developer's database of core/.env.example (role openferment, database openferment_dev), which this Mac's PostgreSQL lacks. Delete that line from core/.env and run this again: it then makes the live database, openferment, reached as $(id -un)" ;;
    ?*)
      echo "OPENFERMENT_DATABASE_URL names the database."
      return ;;
  esac
  # The kit's migration makes the vector extension (kit_alembic/env.py): ask
  # first, so a missing pgvector is named here in its own words.
  vector="$(psql -X -h 127.0.0.1 -d postgres -tAc "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")" ||
    die "psql could not ask PostgreSQL on 127.0.0.1 as $(id -un); the message above says why"
  [ "$vector" = 1 ] || die "pgvector is not installed for this PostgreSQL. Run: brew install pgvector, then run this again"
  psql -X -h 127.0.0.1 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'openferment'" | grep -q 1 ||
    createdb -h 127.0.0.1 openferment || die "createdb openferment failed; the message above says why"
  # On a line of its own, whether or not the file's last line ends in one.
  printf '\nOPENFERMENT_DATABASE_URL=postgresql://%s@127.0.0.1:5432/openferment\n' "$(id -un)" >> "$REPO/core/.env"
  chmod 600 "$REPO/core/.env"
  echo "Database openferment is ready, and its address is in core/.env."
}
