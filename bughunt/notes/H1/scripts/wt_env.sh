# H1's helpers over bughunt/lib/env.sh: the service started from H1's own worktree (its venv holds
# the mirror engine and any stand-in engine H1 installs), keyless, on a bh_h1_* database.
# source /home/user/openFermentUI/bughunt/lib/env.sh; source this file.
export H1=$BH_WORK/H1
export WT=$H1/wt
# wt_py ARGS: the worktree's Python, keyless, in the worktree's core/.
wt_py() { (cd "$WT/core" && bh_env .venv/bin/python "$@"); }
# wt_svc_start DB PORT: as bh_svc_start, from the worktree's core (DB made fresh unless BH_KEEP_DB=1).
wt_svc_start() {
  local n="$1" port="$2" data; data=$(bh_data "$n")
  case "$n" in bh_h1_*) ;; *) echo "refusing $n" >&2; return 2;; esac
  [ "${BH_KEEP_DB:-0}" = 1 ] || bh_db_fresh "$n" || return 1
  (
    cd "$WT/core" || exit 1
    bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$n" OPENFERMENT_DATA_DIR="$data" \
      OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
      OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$port" \
      setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$port" \
      --log-level warning < /dev/null > "$BH_WORK/svc-$port.log" 2>&1 &
  )
  local i; for i in $(seq 1 240); do
    if curl -sf --noproxy '*' "http://127.0.0.1:$port/api/health" >/dev/null 2>&1; then
      echo "http://127.0.0.1:$port"; return 0; fi
    sleep 0.5
  done
  echo "wt_svc_start: no health answer on $port; see $BH_WORK/svc-$port.log" >&2; return 1
}
# j METHOD PATH [BODY]: one JSON call to the service at $O in project $P.
j() { curl -s --noproxy '*' -X "$1" "$O$2" -H 'content-type: application/json' -H "X-OpenFerment-Project: $P" \
        ${3:+-d "$3"} -w '\n[%{http_code}]\n'; }
# wt_conform DB ENGINE ARGS...: conform from the worktree, its verdict kept in bh_h1_* database DB,
# with H1's private data directory (the library shelf, the SFF reference files).
wt_conform() {
  local n="$1"; shift; local data; data=$(bh_data "$n")
  case "$n" in bh_h1_*) ;; *) echo "refusing $n" >&2; return 2;; esac
  (cd "$WT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$n" OPENFERMENT_DATA_DIR="$data" \
     OPENFERMENT_SFF_LIBRARY="$data/sff-library" .venv/bin/python -m openferment_core.engine.conform "$@")
}
