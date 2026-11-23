#!/bin/bash
# H13-01: README.md's "Run it" on a fresh clone with no key. Keyless, no model call, no database written.
#   1. session-start.sh's database step (pnpm prototype:up runs it) on a clone with no core/.env;
#   2. the service started as prototype:up starts it there: no OPENFERMENT_DATABASE_URL, the build served;
#   3. the setting db:migrate reads, with none named.
# Usage: bash h13_01_keyless.sh <checkout with core/.venv and dist/> [port, default 8932]
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
root="${1:?checkout}"; port="${2:-8932}"; here="$(cd "$(dirname "$0")" && pwd)"
[ -e "$root/core/.env" ] && { echo "the checkout holds core/.env; use a clean one"; exit 2; }

echo "== 1. session-start.sh's database step"
bh_env bash "$here/session_start_db.sh" "$root"

echo "== 2. the service with no database named, as prototype:up starts it on that clone"
data="$(mktemp -d)"
(cd "$root/core" && bh_env OPENFERMENT_DATABASE_URL= OPENFERMENT_DATA_DIR="$data" OPENFERMENT_DIST_DIR="$root/dist" \
  setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$port" --log-level warning \
  </dev/null >"$data/svc.log" 2>&1 &)
for _ in $(seq 1 120); do curl -sf --noproxy '*' "http://127.0.0.1:$port/api/health" >/dev/null 2>&1 && break; sleep 0.5; done
echo "-- GET /api/health (prototype:up's wait passes on this):"; curl -s --noproxy '*' "http://127.0.0.1:$port/api/health"; echo
echo "-- GET / :"; curl -s --noproxy '*' -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:$port/"
echo "-- GET /api/projects (Home):"; curl -s --noproxy '*' -w ' [%{http_code}]\n' "http://127.0.0.1:$port/api/projects"
echo "-- POST /api/projects:"; curl -s --noproxy '*' -w ' [%{http_code}]\n' -X POST "http://127.0.0.1:$port/api/projects" \
  -H 'content-type: application/json' -d '{"name":"Keyless","by":"a stranger"}'
bh_svc_stop "$port"; rm -rf "$data"

echo "== 3. what pnpm db:migrate reads (README line 41) with no database named"
(cd "$root/core" && bh_env OPENFERMENT_DATABASE_URL= .venv/bin/python -c '
from openferment_core.db.engine import DatabaseUnavailable, database_url
try:
    database_url(); print("an address")
except DatabaseUnavailable as e:
    print("refused:", e)')
