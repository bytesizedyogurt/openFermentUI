#!/usr/bin/env bash
# H9: the spend gate at the tool door. With the day's cap too small for an extraction,
# intake_write extract should become a spend proposal (tools/gates.py, docs/TOOLS.md's gate
# table); it answers an error and proposes nothing. The model API is a loopback stand-in.
#   spend_gate.sh PORT STANDIN_PORT
source /home/user/openFermentUI/bughunt/lib/env.sh
port="$1"; standin="$2"; S=/home/user/openFermentUI/bughunt/notes/H9/scripts; W="$BH_WORK/H9"; mkdir -p "$W"
: > "$W/standin-$standin.jsonl"
nohup python3 "$S/standin_model_api.py" "$standin" "$W/standin-$standin.jsonl" 400 >/dev/null 2>&1 &
sleep 0.5
bash "$S/start_svc.sh" bh_h9_spendgate "$port" "$standin" ANTHROPIC_API_KEY=BUGHUNT-ENVKEY-gate \
     OPENFERMENT_DAILY_BUDGET_USD=0.001 >/dev/null || exit 1
O="http://127.0.0.1:$port"; bh_project "$O" pg >/dev/null
DOC=$(curl -s --noproxy '*' -X POST "$O/api/intake/paste" -H 'X-OpenFerment-Project: pg' -H 'content-type: application/json' \
  -d '{"title":"Notes","text":"Yeast ferments glucose to ethanol. Xylose is not consumed.","by":"Tester Person"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["documentId"])')
echo "## intake_write extract, a person at the tool door"
curl -s --noproxy '*' -X POST "$O/api/tools/intake_write?by=Alice%20Person" -H 'X-OpenFerment-Project: pg' \
  -H 'content-type: application/json' -d "{\"action\":\"extract\",\"target\":\"$DOC\",\"fields\":{},\"note\":\"extract it\"}" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("summary:", d["summary"], "| error:", d["error"], "| auditIds:", d.get("auditIds"))'
echo "## the project's proposals"; curl -s --noproxy '*' "$O/api/proposals" -H 'X-OpenFerment-Project: pg'; echo
echo "## model requests that reached the stand-in: $(wc -l < "$W/standin-$standin.jsonl")"
bh_svc_stop "$port"; pkill -f "standin_model_api.py $standin"; bh_db_drop bh_h9_spendgate
