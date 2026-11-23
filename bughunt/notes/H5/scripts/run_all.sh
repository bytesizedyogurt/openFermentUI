#!/usr/bin/env bash
# H5: every probe from a fresh database. A service on 127.0.0.1:${PORT:-8851} over bh_h5_${NAME:-fresh} with the
# offline collectors and a /rag test key (a test value, no secret), projects bh-a (filled) and bh-b (empty), then
# the probes, each writing under $H5_OUT. Stops the service and drops the database at the end unless KEEP=1.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
PORT=${PORT:-8851}; NAME=bh_h5_${NAME:-fresh}
export H5_ORIGIN=http://127.0.0.1:$PORT
export H5_OUT=${H5_OUT:-$BH_WORK/H5/fresh}; mkdir -p "$H5_OUT"
S=/home/user/openFermentUI/bughunt/notes/H5/scripts
D=$(bh_data "$NAME"); [ -d "$D/fixtures" ] || cp -R /home/user/openFermentUI/core/tests/fixtures "$D/fixtures"
BH_FIXTURES=1 OPENFERMENT_RAG_KEY=bh-h5-ragkey-not-a-secret bh_svc_start "$NAME" "$PORT" || exit 1
cd /home/user/openFermentUI/core
py() { bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$NAME" .venv/bin/python "$@"; }
py "$S/fill.py" > "$H5_OUT/fill.log" 2>&1 || { tail -3 "$H5_OUT/fill.log"; exit 1; }
for step in "${@:-probe_ops probe_tools sse race race_tool shared_doc graph_reads kind_collision train_collision}"; do
  for s in $step; do echo "== $s"; py "$S/$s.py" > "$H5_OUT/$s.log" 2>&1; tail -4 "$H5_OUT/$s.log"; done
done
[ "${KEEP:-0}" = 1 ] || { bh_svc_stop "$PORT"; bh_db_drop "$NAME"; }
