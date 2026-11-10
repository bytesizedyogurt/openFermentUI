#!/usr/bin/env bash
# H9: the whole key-override run from a fresh database. A stand-in model API on STANDIN
# records every request; the service runs with ANTHROPIC_BASE_URL at it, an env key that is a
# sentinel of its own, and a request key (X-OpenFerment-Key) that is another. Afterwards the
# request sentinel is looked for in the service log, every response, the event stream, a
# pg_dump of the database, the built bundle and the stand-in's record.
#   key_override_run.sh PORT STANDIN_PORT
source /home/user/openFermentUI/bughunt/lib/env.sh
port="$1"; standin="$2"; S=/home/user/openFermentUI/bughunt/notes/H9/scripts; W="$BH_WORK/H9/keyrun"
rm -rf "$W"; mkdir -p "$W"
ENVKEY="BUGHUNT-ENVKEY-$(openssl rand -hex 8)"; SENT="BUGHUNT-SENTINEL-$(openssl rand -hex 12)"
nohup python3 "$S/standin_model_api.py" "$standin" "$W/standin.jsonl" 400 >/dev/null 2>&1 &
sleep 0.5
bash "$S/start_svc.sh" bh_h9_keyrun "$port" "$standin" ANTHROPIC_API_KEY="$ENVKEY" OPENFERMENT_RAG_KEY=bh-h9-ragkey >/dev/null || exit 1
O="http://127.0.0.1:$port"; bh_project "$O" pk >/dev/null
DOC=$(curl -s --noproxy '*' -X POST "$O/api/intake/paste" -H 'X-OpenFerment-Project: pk' -H 'content-type: application/json' \
  -d '{"title":"Ethanol fermentation notes","text":"Saccharomyces cerevisiae ferments glucose to ethanol under anaerobic conditions. Xylose is not consumed by the wild type strain.","by":"Tester Person"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["documentId"])')
(cd "$BH_ROOT/core" && bh_env .venv/bin/python "$S/key_sentinel.py" "$O" pk "$DOC" "$SENT" "$ENVKEY" "$W/standin.jsonl" "$W")
echo "## where the request's sentinel appears (each count should be 0 but the stand-in's)"
echo "service log: $(grep -c "$SENT" "$BH_WORK/svc-$port.log")"
echo "responses: $(cat "$W"/*.response.txt | grep -c "$SENT")"
echo "event stream: $(grep -c "$SENT" "$W/events.txt")"
pg_dump -d "$BH_SERVER/bh_h9_keyrun" > "$W/dump.sql" 2>/dev/null; echo "database dump: $(grep -c "$SENT" "$W/dump.sql")"
echo "built bundle: $(grep -rl "$SENT" "$BH_ROOT/dist" | wc -l)"
echo "stand-in record (the model requests): $(grep -c "$SENT" "$W/standin.jsonl") of $(wc -l < "$W/standin.jsonl")"
bh_svc_stop "$port"; pkill -f "standin_model_api.py $standin"; bh_db_drop bh_h9_keyrun
