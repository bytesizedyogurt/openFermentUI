#!/bin/bash
# H10's candidates from a fresh database, keyless, on 127.0.0.1:8905 with OPENFERMENT_RAG_KEY unset.
#   bash bughunt/notes/H10/scripts/repro_all.sh [01|02|03|04|05|all]
# Starts the head's service over bh_h10_repro, makes project r1, runs the probe for each candidate,
# stops the service and drops the database.
set -u
which="${1:-all}"
HERE="$(cd "$(dirname "$0")" && pwd)"
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_h10_repro; PORT=8905; O="http://127.0.0.1:$PORT"
export OPENFERMENT_RAG_KEY=''
bh_svc_start "$DB" "$PORT" >/dev/null || exit 1
unset OPENFERMENT_RAG_KEY
trap 'bh_svc_stop $PORT; bh_db_drop $DB' EXIT
bh_project "$O" r1 >/dev/null
J='content-type: application/json'
run() { [ "$which" = all ] || [ "$which" = "$1" ]; }

if run 01; then
  echo "== H10-01: a page under a rebound public name reads the project; its write is refused"
  curl -s --noproxy '*' -X POST "$O/api/guild/people" -H "$J" -H 'X-OpenFerment-Project: r1' \
    -d '{"id":"p-ada","name":"Ada Example","title":"Bench scientist","role":"lead","joinedAt":"2026-01-01","addedAt":"2026-01-01T00:00:00Z"}' >/dev/null
  bash "$HERE/rebind_read.sh" "$O" r1
fi
if run 02; then
  echo "== H10-02: a NUL character in an id, a filter or a text field"
  bh_py "$HERE/nul_probe.py" "$O" r1
fi
if run 03; then
  echo "== H10-03: /rag with no key set"
  curl -s --noproxy '*' -m 120 -X POST "$O/api/intake/paste" -H "$J" -H 'X-OpenFerment-Project: r1' \
    -d '{"title":"A pasted note","text":"A placeholder note the hunt pastes so the project holds one document.","by":"bughunt","licenceClass":"unknown"}' >/dev/null
  bash "$HERE/rag_probe.sh" "$O" r1
  echo "-- the chunks were embedded by:"
  psql "$BH_SERVER/$DB" -XAtc "select embedding_version, count(*) from sci_rag.chunks group by 1"
fi
if run 04; then
  echo "== H10-04: the type of every body column"
  psql "$BH_SERVER/$DB" -XAtc "select data_type, count(*) from information_schema.columns where table_schema='openferment' and column_name='body' group by 1"
  grep -n 'JSONB' /home/user/openFermentUI/CLAUDE.md /home/user/openFermentUI/docs/decisions/ADR-001-postgresql.md
fi
if run 05; then
  echo "== H10-05: a .localhost name passes the guard; guard.py's list of names leaves it out"
  curl -s --noproxy '*' -o /dev/null -w 'POST under evil.localhost: %{http_code} (422 = reached the endpoint)\n' -X POST "$O/api/biorepo/check" \
    -H "$J" -H "Host: evil.localhost:$PORT" -H "Origin: http://evil.localhost:$PORT" -d '{}'
  sed -n 22,24p /home/user/openFermentUI/core/openferment_core/guard.py
  grep -n '^OWN_SUFFIXES' /home/user/openFermentUI/core/openferment_core/guard.py
fi
