#!/usr/bin/env bash
# H9: the head's service on 127.0.0.1:PORT over database NAME (made fresh), with the model
# API pointed at a loopback stand-in and extra settings given as NAME=VALUE arguments.
#   start_svc.sh NAME PORT STANDIN_PORT [SETTING=VALUE ...]
# ANTHROPIC_BASE_URL always names the stand-in, so no request can leave the machine.
source /home/user/openFermentUI/bughunt/lib/env.sh
n="$1"; port="$2"; standin="$3"; shift 3
data=$(bh_data "$n")
[ "${BH_KEEP_DB:-0}" = 1 ] || bh_db_fresh "$n" || exit 1
(
  cd "$BH_ROOT/core" || exit 1
  bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$n" OPENFERMENT_DATA_DIR="$data" \
    OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
    OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$port" \
    OPENFERMENT_ROUTES= OPENFERMENT_LOCAL_BASE_URL= OPENFERMENT_WORKSPACE_ID= \
    "$@" ANTHROPIC_BASE_URL="http://127.0.0.1:$standin" \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$port" \
    --log-level warning < /dev/null > "$BH_WORK/svc-$port.log" 2>&1 &
)
for i in $(seq 1 240); do
  if curl -sf --noproxy '*' "http://127.0.0.1:$port/api/health" >/dev/null 2>&1; then
    bh_port_pid "$port" > "$BH_WORK/svc-$port.pid"; echo "http://127.0.0.1:$port"; exit 0
  fi
  sleep 0.5
done
echo "start_svc: no health answer on $port; see $BH_WORK/svc-$port.log" >&2; exit 1
