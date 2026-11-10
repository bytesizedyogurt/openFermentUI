#!/usr/bin/env bash
# H9: OPENFERMENT_ROUTES set to tables that cannot route, and what the service, its ask
# route, the model-calling routes and `ready --offline` say. The model API is the loopback
# stand-in on STANDIN (its record shows whether any request left), so nothing leaves.
#   routes_invalid.sh PORT STANDIN OUTDIR
source /home/user/openFermentUI/bughunt/lib/env.sh
port="$1"; standin="$2"; out="$3"; mkdir -p "$out"
S=/home/user/openFermentUI/bughunt/notes/H9/scripts
O="http://127.0.0.1:$port"
declare -A TABLES=(
  [malformed]='{"plan": {"models": ["claude-opus-5-5"]'
  [unknown-family]='{"planner": {"models": ["claude-opus-5-5"]}}'
  [unknown-model]='{"plan": {"models": ["claude-nonexistent-9"]}}'
  [unknown-provider]='{"plan": {"models": ["acme:big-model"]}}'
  [bad-effort]='{"plan": {"effort": "extreme"}}'
  [empty-models]='{"plan": {"models": []}}'
  [extract-empty-models]='{"extract": {"models": []}}'
)
for name in malformed unknown-family unknown-model unknown-provider bad-effort empty-models extract-empty-models; do
  table="${TABLES[$name]}"
  d="$out/$name"; mkdir -p "$d"; : > "$d/standin.jsonl"
  bh_svc_stop "$port"; pkill -f "standin_model_api.py $standin" ; sleep 0.5
  nohup python3 "$S/standin_model_api.py" "$standin" "$d/standin.jsonl" 400 > /dev/null 2>&1 &
  sleep 0.5
  bash "$S/start_svc.sh" bh_h9_routes "$port" "$standin" ANTHROPIC_API_KEY=BUGHUNT-ENVKEY-routes \
       OPENFERMENT_ROUTES="$table" > "$d/start.txt" 2>&1 || { echo "$name: no start"; cat "$d/start.txt"; continue; }
  bh_project "$O" pr > /dev/null
  doc=$(curl -s --noproxy '*' -X POST "$O/api/intake/paste" -H 'X-OpenFerment-Project: pr' -H 'content-type: application/json' \
        -d '{"title":"Notes","text":"Yeast ferments glucose to ethanol. Xylose is not consumed.","by":"Tester Person"}' \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("documentId",""))')
  P=(-H 'X-OpenFerment-Project: pr' -H 'content-type: application/json')
  {
    echo "## table: $table"
    echo "## GET /api/health"; curl -s --noproxy '*' -w ' [%{http_code}]' "$O/api/health"; echo
    echo "## POST /api/ask"; curl -s --noproxy '*' -w ' [%{http_code}]' -X POST "$O/api/ask" "${P[@]}" -d '{"question":"What does the yeast ferment?"}' | cut -c1-700; echo
    echo "## POST /api/ask/stream"; curl -s --noproxy '*' -w ' [%{http_code}]' -X POST "$O/api/ask/stream" "${P[@]}" -d '{"question":"What does the yeast ferment?"}' | tail -c 600; echo
    echo "## POST /api/intake/$doc/extract"; curl -s --noproxy '*' -w ' [%{http_code}]' -X POST "$O/api/intake/$doc/extract" "${P[@]}" | cut -c1-500; echo
    echo "## POST /api/literature/answer"; curl -s --noproxy '*' -w ' [%{http_code}]' -X POST "$O/api/literature/answer" "${P[@]}" -d '{"question":"What does the yeast ferment?"}' | tail -c 400; echo
    echo "## GET /api/literature/search deep"; curl -s --noproxy '*' -w ' [%{http_code}]' "$O/api/literature/search?q=xylose&profile=deep" "${P[@]}" | cut -c1-300; echo
    echo "## POST /api/tools/intake_write extract (assistant)"; curl -s --noproxy '*' -w ' [%{http_code}]' -X POST "$O/api/tools/intake_write" "${P[@]}" -H 'X-OpenFerment-Assistant: routebot/1' -d "{\"action\":\"extract\",\"target\":\"$doc\",\"fields\":{},\"note\":\"extract\"}" | cut -c1-500; echo
    echo "## POST /api/tools/home_write note (assistant)"; curl -s --noproxy '*' -w ' [%{http_code}]' -X POST "$O/api/tools/home_write" "${P[@]}" -H 'X-OpenFerment-Assistant: routebot/1' -d '{"action":"note","target":"","fields":{},"note":"a note"}' | cut -c1-400; echo
  } > "$d/answers.txt" 2>&1
  echo "## ready --offline" > "$d/ready.txt"
  (cd "$BH_ROOT/core" && timeout 300 bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h9_routes" OPENFERMENT_PORT="$port" \
     OPENFERMENT_ROUTES="$table" OPENFERMENT_DATA_DIR="$(bh_data bh_h9_routes)" ANTHROPIC_BASE_URL="http://127.0.0.1:$standin" \
     .venv/bin/python -m openferment_core.ready --offline --no-workers) >> "$d/ready.txt" 2>&1
  echo "exit $?" >> "$d/ready.txt"
  grep -c "ERROR\|Traceback" "$BH_WORK/svc-$port.log" > "$d/log-errors.txt"; cp "$BH_WORK/svc-$port.log" "$d/svc.log"
  echo "$name: model requests that reached the stand-in: $(wc -l < "$d/standin.jsonl")"
done
bh_svc_stop "$port"; pkill -f "standin_model_api.py $standin"
