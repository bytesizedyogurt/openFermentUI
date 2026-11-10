# bughunt/lib/env.sh: source me. A keyless environment and small helpers for the alpha 2.2 bug hunt.
# Nothing here edits core/, src/, scripts/ or examples/. Every database it makes is a test database
# named bh_<something>; it never touches openferment_dev, openferment_dev_alpha21 or openferment.
export BH_ROOT=/home/user/openFermentUI
export BH_SERVER=postgresql://openferment:openferment@127.0.0.1:5432
export BH_DATA_SRC=/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/f/data
export BH_WORK=/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work
mkdir -p "$BH_WORK"

# Run a command keyless: the cloud session's model pins unset, no key in the environment, and an empty
# ANTHROPIC_API_KEY standing over core/.env (the service loads core/.env without overriding).
bh_env() {
  env -u OPENFERMENT_MODEL -u OPENFERMENT_FALLBACK_MODEL -u OPENFERMENT_INDEX_MODEL -u OPENFERMENT_EFFORT \
      -u OPENFERMENT_API_KEY -u OPENFERMENT_DATA_DIR ANTHROPIC_API_KEY= "$@"
}

# The repository's own Python, keyless.
bh_py() { (cd "$BH_ROOT/core" && bh_env .venv/bin/python "$@"); }

# bh_db_fresh NAME: drop NAME if it exists, make it again and migrate it to head (both schemas).
bh_db_fresh() {
  local n="$1"
  case "$n" in bh_*) ;; *) echo "bh_db_fresh: refusing a name outside bh_*: $n" >&2; return 2;; esac
  psql "$BH_SERVER/postgres" -qXc "DROP DATABASE IF EXISTS \"$n\" WITH (FORCE)" >/dev/null || return 1
  psql "$BH_SERVER/postgres" -qXc "CREATE DATABASE \"$n\"" >/dev/null || return 1
  (cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$n" .venv/bin/python -m openferment_core.migrations migrate) >/dev/null
}

# bh_db_drop NAME
bh_db_drop() {
  case "$1" in bh_*) ;; *) echo "bh_db_drop: refusing $1" >&2; return 2;; esac
  psql "$BH_SERVER/postgres" -qXc "DROP DATABASE IF EXISTS \"$1\" WITH (FORCE)" >/dev/null
}

# bh_data NAME: a private copy of the fetched caches (genome-scale models, the toolkit's reference files).
bh_data() { local d="$BH_WORK/data-$1"; [ -d "$d" ] || cp -R "$BH_DATA_SRC" "$d"; echo "$d"; }

# bh_svc_start NAME PORT: the service on 127.0.0.1:PORT over database NAME (made fresh first unless
# BH_KEEP_DB=1), its own data directory, the built app in dist/, keyless. BH_FIXTURES=1 adds the
# proof's offline mode (collectors refuse the network). Prints the origin; the log is $BH_WORK/svc-PORT.log.
bh_svc_start() {
  local n="$1" port="$2" data; data=$(bh_data "$n")
  [ "${BH_KEEP_DB:-0}" = 1 ] || bh_db_fresh "$n" || return 1
  local fx=(); [ "${BH_FIXTURES:-0}" = 1 ] && fx=(OPENFERMENT_FIXTURES=1 OPENFERMENT_FIXTURE_DIR="$data/fixtures")
  (
    cd "$BH_ROOT/core" || exit 1
    bh_env "${fx[@]}" OPENFERMENT_DATABASE_URL="$BH_SERVER/$n" OPENFERMENT_DATA_DIR="$data" \
      OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
      OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$port" \
      setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$port" \
      --log-level warning < /dev/null > "$BH_WORK/svc-$port.log" 2>&1 &
  )
  local i; for i in $(seq 1 240); do
    if curl -sf --noproxy '*' "http://127.0.0.1:$port/api/health" >/dev/null 2>&1; then
      bh_port_pid "$port" > "$BH_WORK/svc-$port.pid"; echo "http://127.0.0.1:$port"; return 0
    fi
    sleep 0.5
  done
  echo "bh_svc_start: no health answer on $port; see $BH_WORK/svc-$port.log" >&2; return 1
}

# bh_port_pid PORT: the pid listening on 127.0.0.1:PORT.
bh_port_pid() { lsof -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -1; }

# bh_svc_stop PORT: the service on PORT and every worker in its process group (setsid made it the leader).
bh_svc_stop() {
  local pid; pid=$(bh_port_pid "$1"); [ -n "$pid" ] || { rm -f "$BH_WORK/svc-$1.pid"; return 0; }
  local pg; pg=$(ps -o pgid= -p "$pid" | tr -d ' ')
  kill -TERM -- "-$pg" 2>/dev/null; local i; for i in 1 2 3 4 5 6 7 8 9 10; do
    [ -z "$(bh_port_pid "$1")" ] && break; sleep 0.5; done
  kill -KILL -- "-$pg" 2>/dev/null; rm -f "$BH_WORK/svc-$1.pid"
}

# bh_project ORIGIN ID [NAME]: make a project through the API; prints the answer.
bh_project() {
  curl -s --noproxy '*' -X POST "$1/api/projects" -H 'content-type: application/json' \
       -d "{\"id\":\"$2\",\"name\":\"${3:-$2}\",\"by\":\"${BH_BY:-bughunt}\"}"
}
