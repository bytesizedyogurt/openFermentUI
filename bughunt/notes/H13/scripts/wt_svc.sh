# H13: source after bughunt/lib/env.sh. wt_svc_start DB PORT starts the service from H13's worktree
# (its own core/.venv, so an engine installed there is listed) over database DB (made fresh unless
# BH_KEEP_DB=1), keyless, the offline collectors on, the worktree's build served. bh_svc_stop PORT stops it.
WT="$BH_WORK/H13/wt"
wt_svc_start() {
  local n="$1" port="$2" data="$BH_WORK/H13/data-$1"
  mkdir -p "$data"
  [ "${BH_KEEP_DB:-0}" = 1 ] || bh_db_fresh "$n" || return 1
  (
    cd "$WT/core" || exit 1
    bh_env OPENFERMENT_FIXTURES=1 OPENFERMENT_DATABASE_URL="$BH_SERVER/$n" OPENFERMENT_DATA_DIR="$data" \
      OPENFERMENT_DIST_DIR="$WT/dist" OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$port" \
      setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$port" \
      --log-level warning < /dev/null > "$BH_WORK/svc-$port.log" 2>&1 &
  )
  local i; for i in $(seq 1 240); do
    if curl -sf --noproxy '*' "http://127.0.0.1:$port/api/health" >/dev/null 2>&1; then
      echo "http://127.0.0.1:$port"; return 0
    fi
    sleep 0.5
  done
  echo "wt_svc_start: no health answer on $port" >&2; return 1
}
