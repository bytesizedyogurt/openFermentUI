#!/bin/bash
# openFerment, running on this computer, from one command.
#
#   bash start.sh              start everything and open the app
#   bash start.sh --check      set everything up, say what is ready, start nothing
#   bash start.sh --stop       stop a database this script left running
#
# What it does, in order:
#   1. finds the tools it needs (uv, PostgreSQL with pgvector, Graphviz) and,
#      on a Mac with Homebrew, installs the ones that are missing;
#   2. installs the Python packages into core/.venv (uv sync);
#   3. starts a PostgreSQL database of this folder's own, kept in
#      .openferment/pg and listening on 127.0.0.1 alone, on a port of its own,
#      so no other PostgreSQL on this computer and no other openFerment is
#      touched. When core/.env already names a database, that one is used and
#      none is started;
#   4. asks once for an Anthropic key when core/.env holds none (Enter skips:
#      the plants, flowsheets and TEA run without one; Postdoc waits for it);
#   5. migrates the database, says what is ready, starts the service on
#      127.0.0.1 and opens the app in the browser.
#
# Ctrl-C stops the service and the database this script started. Everything a
# person keeps lives in .openferment/ and core/data/, inside this folder.
#
# The service listens on loopback alone, as every way of starting it does.
# Written for the bash 3.2 that macOS ships.
set -uo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO" || exit 1

HOST=127.0.0.1
STATE="$REPO/.openferment"
PGDATA="$STATE/pg"
PGLOG="$STATE/postgres.log"
PGPORT_FILE="$STATE/pg.port"
DB_NAME=openferment
MODE="${1:-}"

say() { printf '\n── %s\n' "$*"; }
note() { printf '   %s\n' "$*"; }
die() { printf '\n✗ %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }
# Free when nothing accepts a connection on it.
port_free() { ! (exec 3<>"/dev/tcp/$HOST/$1") 2>/dev/null; }
first_free() { # first_free <from> <how many>
  local p="$1" end=$(( $1 + $2 ))
  while [ "$p" -lt "$end" ]; do
    if port_free "$p"; then echo "$p"; return 0; fi
    p=$(( p + 1 ))
  done
  return 1
}
env_has() { [ -e core/.env ] && grep -Eq "^$1=.+" core/.env; }

case "$MODE" in
  "" | --check | --stop) ;;
  *) die "unknown option $MODE. Usage: bash start.sh [--check | --stop]" ;;
esac
[ "$(id -u)" != 0 ] || die "run this as yourself, without sudo: PostgreSQL refuses to run as root."

# ── PostgreSQL's programs, with pgvector ───────────────────────────────
# The newest PostgreSQL on this computer that has the pgvector extension.
pg_bin() {
  local candidates="" d
  if have brew; then
    for v in 18 17 16; do
      d="$(brew --prefix "postgresql@$v" 2>/dev/null)/bin"
      [ -x "$d/initdb" ] && candidates="$candidates $d"
    done
  fi
  for d in /usr/lib/postgresql/*/bin /usr/pgsql-*/bin /Applications/Postgres.app/Contents/Versions/latest/bin; do
    [ -x "$d/initdb" ] && candidates="$d $candidates"   # later versions sort last, so they end up first
  done
  if have initdb && have pg_config; then candidates="$candidates $(dirname "$(command -v initdb)")"; fi
  for d in $candidates; do
    [ -x "$d/pg_config" ] || continue
    if [ -e "$("$d/pg_config" --sharedir)/extension/vector.control" ]; then echo "$d"; return 0; fi
  done
  return 1
}

stop_database() {
  [ -e "$PGDATA/postmaster.pid" ] || return 0
  local bin
  bin="$(pg_bin)" || return 0
  "$bin/pg_ctl" -D "$PGDATA" -m fast -w stop >/dev/null 2>&1 || true
}

if [ "$MODE" = --stop ]; then
  if [ -e "$PGDATA/postmaster.pid" ]; then stop_database; say "The database in .openferment/pg is stopped."
  else say "No database of this folder's is running."; fi
  exit 0
fi

# ── 1. the tools ───────────────────────────────────────────────────────
say "Checking the tools"
missing=""
have uv || missing="$missing uv"
pg_bin >/dev/null || missing="$missing postgresql@17 pgvector"
have dot || missing="$missing graphviz"
if [ -n "$missing" ]; then
  if [ "$(uname -s)" = Darwin ] && have brew; then
    note "installing with Homebrew:$missing"
    # shellcheck disable=SC2086
    brew install $missing || die "brew install failed for:$missing"
  elif [ "$(uname -s)" = Darwin ]; then
    die "missing:$missing. Install Homebrew from https://brew.sh, then run this again and it installs them."
  else
    die "missing:$missing. On Debian or Ubuntu: sudo apt install postgresql postgresql-16-pgvector graphviz, and uv from https://docs.astral.sh/uv/. Then run this again."
  fi
fi
have uv || die "uv is still not on the PATH. Open a new terminal window and run this again."
note "uv $(uv --version 2>/dev/null | awk '{print $2}')"
have dot && note "Graphviz $(dot -V 2>&1 | awk '{print $5}')" || note "Graphviz is missing: runs still work, BioSTEAM's own diagrams are skipped"

# ── 2. the Python packages ─────────────────────────────────────────────
say "Installing the Python packages (the first time takes a few minutes)"
(cd core && uv sync --all-extras --quiet) || die "uv sync failed. It needs the internet the first time."
note "core/.venv is ready"

# ── 3. the database ────────────────────────────────────────────────────
OWN_DB=""
started_db=""
if env_has OPENFERMENT_DATABASE_URL; then
  say "The database"
  note "core/.env names a database, so that one is used and none is started here"
else
  say "The database, this folder's own"
  BIN="$(pg_bin)" || die "no PostgreSQL with the pgvector extension was found after installing. Run: brew install postgresql@17 pgvector"
  note "PostgreSQL $("$BIN/pg_config" --version | awk '{print $2}') at $BIN"
  mkdir -p "$STATE"
  if [ ! -e "$PGDATA/PG_VERSION" ]; then
    "$BIN/initdb" -D "$PGDATA" -U openferment --auth=trust -E UTF8 --locale=C >/dev/null \
      || die "initdb could not make the database in $PGDATA"
    note "made a new database in .openferment/pg"
  fi
  if [ -e "$PGDATA/postmaster.pid" ] && "$BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
    PGPORT="$(cat "$PGPORT_FILE" 2>/dev/null || true)"
    [ -n "$PGPORT" ] || die "a database is running from .openferment/pg and its port is not on file. Run: bash start.sh --stop, then start again."
    note "it is running already, on port $PGPORT"
  else
    PGPORT="$(first_free 54329 20)" || die "no free port between 54329 and 54348 for the database"
    # Loopback alone. Its socket goes in a directory of its own under /tmp: a
    # socket's path may be about a hundred characters, and macOS's TMPDIR is long.
    SOCK="$(mktemp -d /tmp/openferment-pg.XXXXXX)"
    "$BIN/pg_ctl" -D "$PGDATA" -l "$PGLOG" -w -t 60 \
      -o "-p $PGPORT -c listen_addresses=$HOST -c unix_socket_directories=$SOCK" start >/dev/null \
      || die "PostgreSQL did not start. Its log: $PGLOG"
    echo "$PGPORT" > "$PGPORT_FILE"
    started_db=1
    note "started on $HOST:$PGPORT"
  fi
  if ! "$BIN/psql" -h "$HOST" -p "$PGPORT" -U openferment -d postgres -Atc \
      "select 1 from pg_database where datname = '$DB_NAME'" 2>/dev/null | grep -q 1; then
    "$BIN/createdb" -h "$HOST" -p "$PGPORT" -U openferment "$DB_NAME" || die "could not create the database $DB_NAME"
  fi
  OWN_DB=1
  export OPENFERMENT_DATABASE_URL="postgresql://openferment@$HOST:$PGPORT/$DB_NAME"
fi

svc=""
stop_all() {
  [ -z "$svc" ] || kill "$svc" 2>/dev/null
  wait 2>/dev/null
  if [ -n "$started_db" ]; then stop_database; printf '\n── Stopped. Your work is kept in .openferment/ and core/data/.\n'; fi
}
trap stop_all EXIT
trap 'exit 130' INT TERM

# ── 4. the key ─────────────────────────────────────────────────────────
say "The Anthropic key"
if env_has ANTHROPIC_API_KEY; then
  note "core/.env holds a key"
elif [ "$MODE" != --check ] && [ -t 0 ]; then
  note "Postdoc needs an Anthropic API key (console.anthropic.com → API keys). The plants, the"
  note "flowsheets and the TEA run without one. It is kept in core/.env on this computer alone."
  printf '   Paste the key and press Enter, or press Enter to skip: '
  IFS= read -rs key || key=""
  printf '\n'
  key="$(printf '%s' "$key" | tr -d '[:space:]')"
  if [ -n "$key" ]; then
    (umask 177 && printf 'ANTHROPIC_API_KEY=%s\n' "$key" >> core/.env)
    chmod 600 core/.env
    note "kept in core/.env (mode 600)"
  else
    note "skipped. To add one later: run this again, or put ANTHROPIC_API_KEY=… in core/.env"
  fi
  unset key
else
  note "core/.env holds no key: Postdoc waits for one"
fi

# ── 5. migrate, say what is ready, start ───────────────────────────────
say "Migrating the database"
(cd core && uv run --all-extras python -m openferment_core.migrations migrate) || die "the migration failed"

[ -e dist/index.html ] || {
  have pnpm || die "the built app (dist/) is missing and pnpm is not installed to build it. Download the package again, or: brew install pnpm"
  say "Building the app"
  pnpm install --frozen-lockfile && pnpm build || die "the build failed"
}

say "What is ready"
(cd core && uv run python -m openferment_core.ready) || true
note "A ✗ on the key row means Postdoc waits for a key; the plants, flowsheets and TEA run without it."
note "The service row is checked before the service starts, so it reads as not answering here."

if [ "$MODE" = --check ]; then
  say "Checked. Run: bash start.sh"
  exit 0
fi

PORT="$(first_free 8000 20)" || die "no free port between 8000 and 8019 for the service"
say "Starting the service on $HOST:$PORT (BioSTEAM takes about half a minute to load the first time)"
(cd core && exec uv run uvicorn openferment_core.api:app --host "$HOST" --port "$PORT" --log-level warning) &
svc=$!
ok=""
for _ in $(seq 1 360); do
  curl -fsS "http://$HOST:$PORT/api/health" >/dev/null 2>&1 && { ok=1; break; }
  kill -0 "$svc" 2>/dev/null || die "the service stopped before it answered"
  sleep 0.5
done
[ -n "$ok" ] || die "the service did not answer within three minutes"

URL="http://$HOST:$PORT/"
printf '\n   openFerment is running.\n\n   Open  %s\n\n   Ctrl-C here stops it.\n\n' "$URL"
if have open; then open "$URL" 2>/dev/null || true
elif have xdg-open; then xdg-open "$URL" >/dev/null 2>&1 || true
fi

while kill -0 "$svc" 2>/dev/null; do sleep 1; done
die "the service stopped"
