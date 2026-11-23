#!/usr/bin/env bash
# main_svc.sh start|stop DB PORT: alpha 2.1's service (main at 112eb8b, the worktree wt-main) on
# 127.0.0.1:PORT over the test database DB, keyless, in fixture mode (the collectors refuse the network),
# with its own data directory (a copy of the fetched caches). Log: $BH_WORK/H6/svc-main-PORT.log.
source /home/user/openFermentUI/bughunt/lib/env.sh
WT=$BH_WORK/H6/wt-main
cmd=$1 db=$2 port=$3
case "$db" in bh_h6_*) ;; *) echo "refusing database $db" >&2; exit 2;; esac
case "$port" in 886[0-9]) ;; *) echo "refusing port $port" >&2; exit 2;; esac
if [ "$cmd" = stop ]; then bh_svc_stop "$port"; exit 0; fi
data=$(bh_data "h6main-$db")
mkdir -p "$data/fixtures"
(
  cd "$WT/core" || exit 1
  bh_env OPENFERMENT_FIXTURES=1 OPENFERMENT_FIXTURE_DIR="$data/fixtures" \
    OPENFERMENT_DATABASE_URL="$BH_SERVER/$db" OPENFERMENT_DATA_DIR="$data" \
    OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$WT/dist" \
    OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$port" \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$port" \
    --log-level warning < /dev/null > "$BH_WORK/H6/svc-main-$port.log" 2>&1 &
)
for i in $(seq 1 240); do
  if curl -sf --noproxy '*' "http://127.0.0.1:$port/api/health" >/dev/null 2>&1; then
    echo "http://127.0.0.1:$port $data"; exit 0
  fi
  sleep 0.5
done
echo "no health answer on $port; see $BH_WORK/H6/svc-main-$port.log" >&2; exit 1
