#!/bin/bash
# no-database-service.sh: the head's service started as the LaunchDaemon starts it after an install from a shell
# that exported OPENFERMENT_DATABASE_URL (env-url-install.sh): no database address in its environment and none in
# core/.env. An empty OPENFERMENT_DATABASE_URL stands for "none" (load_dotenv never overrides a set name, so the
# repository's core/.env is not read for it, and no database is reached). Asks /api/health, which install.sh's
# wait_for_health asks, and /api/projects, the list Home reads.
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
data=$(bh_data bh_h11_nodb)
(
  cd /home/user/openFermentUI/core || exit 1
  bh_env OPENFERMENT_DATABASE_URL= OPENFERMENT_DATA_DIR="$data" OPENFERMENT_SFF_LIBRARY="$data/sff-library" \
    OPENFERMENT_DIST_DIR=/home/user/openFermentUI/dist ANTHROPIC_BASE_URL=http://127.0.0.1:8919 \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port 8913 --log-level warning \
    < /dev/null > "$BH_WORK/svc-8913.log" 2>&1 &
)
for _ in $(seq 1 240); do curl -sf --noproxy '*' http://127.0.0.1:8913/api/health >/dev/null 2>&1 && break; sleep 0.5; done
echo "GET /api/health -> $(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' http://127.0.0.1:8913/api/health) $(curl -s --noproxy '*' http://127.0.0.1:8913/api/health)"
echo "GET /api/projects -> $(curl -s --noproxy '*' -w ' %{http_code}' http://127.0.0.1:8913/api/projects | cut -c1-300)"
bh_svc_stop 8913
