#!/usr/bin/env bash
# Row 2 (fa9782e, 53c123c): a key named in X-OpenFerment-Key serves the request's model calls and is kept nowhere;
# OPENFERMENT_LOCAL_BASE_URL serves a local model in single calls. A stub on 127.0.0.1:8951 stands for both
# endpoints; the service on 8952 reaches it through ANTHROPIC_BASE_URL, with every proxy pointed at a dead port,
# so nothing leaves the machine. The key is a needle, no key.
source /home/user/openFermentUI/bughunt/lib/env.sh
P=/home/user/openFermentUI/bughunt/notes/P/scripts
W=$BH_WORK/P; mkdir -p "$W"
NEEDLE="needle-of-hunt-P-row-two-4b7e1d"
STUBLOG=$W/stub-8951.jsonl; : > "$STUBLOG"
C() { curl -s --noproxy "*" "$@"; }

lsof -t -iTCP:8951 -sTCP:LISTEN >/dev/null 2>&1 || { setsid "$BH_ROOT/core/.venv/bin/python" "$P/stub_models.py" 8951 "$STUBLOG" >/dev/null 2>&1 < /dev/null & sleep 1; }

DB=bh_p_key; bh_db_fresh $DB
data=$(bh_data $DB)
(
  cd "$BH_ROOT/core" || exit 1
  bh_env ANTHROPIC_BASE_URL=http://127.0.0.1:8951 OPENFERMENT_LOCAL_BASE_URL=http://127.0.0.1:8951/v1 \
    https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 \
    no_proxy=127.0.0.1,localhost NO_PROXY=127.0.0.1,localhost \
    OPENFERMENT_FIXTURES=1 OPENFERMENT_FIXTURE_DIR="$data/fixtures" \
    OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$data" OPENFERMENT_SFF_LIBRARY="$data/sff-library" \
    OPENFERMENT_DIST_DIR="$BH_ROOT/dist" OPENFERMENT_PORT=8952 \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port 8952 --log-level debug \
    < /dev/null > "$W/svc-8952.log" 2>&1 &
)
for i in $(seq 1 240); do C -sf http://127.0.0.1:8952/api/health >/dev/null && break; sleep 0.5; done
O=http://127.0.0.1:8952
bh_project $O pk >/dev/null
echo "== ask on the named key"
C -X POST $O/api/ask -H 'X-OpenFerment-Project: pk' -H 'content-type: application/json' \
  -H "X-OpenFerment-Key: $NEEDLE" -d '{"question":"What does the plant solve?"}' > "$W/ask.json"
head -c 600 "$W/ask.json"; echo
echo "== ask/stream on the named key"
C -N --max-time 60 -X POST $O/api/ask/stream -H 'X-OpenFerment-Project: pk' -H 'content-type: application/json' \
  -H "X-OpenFerment-Key: $NEEDLE" -d '{"question":"And what does it cost?"}' > "$W/askstream.txt"
tail -c 400 "$W/askstream.txt"; echo
echo "== ask with no key (core/.env's is empty here)"
C -X POST $O/api/ask -H 'X-OpenFerment-Project: pk' -H 'content-type: application/json' -d '{"question":"q"}' | head -c 400; echo
echo "== the stub saw"
cat "$STUBLOG" | sed "s/$NEEDLE/<NEEDLE>/g"
echo "== the needle in the service log, the responses, the events, every row of both schemas"
grep -c "$NEEDLE" "$W/svc-8952.log" "$W/ask.json" "$W/askstream.txt"
C --max-time 3 "$O/api/events?project=pk" > "$W/events.txt"; grep -c "$NEEDLE" "$W/events.txt"
psql "$BH_SERVER/$DB" -XAtc "select table_schema||'.'||table_name from information_schema.tables where table_schema in ('openferment','sci_rag') and table_type='BASE TABLE'" | while read t; do
  s=${t%%.*}; n=${t#*.}; c=$(psql "$BH_SERVER/$DB" -XAtc "select count(*) from \"$s\".\"$n\" r where cast(r as text) like '%$NEEDLE%'"); [ "$c" != 0 ] && echo "row holds needle: $t $c"; done
echo "== audit rows of the override"
C "$O/api/audit?action=key_override" -H 'X-OpenFerment-Project: pk'; echo
