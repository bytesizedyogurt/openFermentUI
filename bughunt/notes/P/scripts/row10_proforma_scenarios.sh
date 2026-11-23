#!/usr/bin/env bash
# Row 10 (f5405f8): GET /api/proforma/scenarios lists a kept custom_train_v1 scenario whose parts cannot stand with
# its refusal in words (it answered 500 before), and binds a shelf scenario. Two scenarios kept through PUT /api/state.
O=${1:-http://127.0.0.1:8950}
C() { curl -s --noproxy "*" "$@"; }
J='content-type: application/json'
for row in \
 '{"id":"sc-p10a","modelId":"custom_train_v1","flowsheetId":"custom_train_v1","kind":"biosteam","name":"A placeholder composite","description":"","product":"ethanol","pinned":false,"vessel":"00000000deadbeef","trainRun":"00000000feedface"}' \
 '{"id":"sc-p10b","modelId":"custom_train_v1","flowsheetId":"custom_train_v1","kind":"biosteam","name":"A placeholder composite with no parts","description":"","product":"ethanol","pinned":false}' \
 '{"id":"sc-p10c","modelId":"ethanol_glucose_v0","flowsheetId":"ethanol_glucose_v0","kind":"biosteam","name":"A placeholder shelf scenario","description":"","product":"ethanol","pinned":false}'; do
  id=$(echo "$row" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
  C -X PUT "$O/api/state/scenarios/$id" -H 'X-OpenFerment-Project: pa' -H "$J" -d '{"by":"Ada Moreno","value":'"$row"'}' -o /dev/null -w "PUT $id %{http_code}\n"
done
C "$O/api/proforma/scenarios" -H 'X-OpenFerment-Project: pa' -w '\nHTTP %{http_code}\n' | python3 -c '
import json,sys
raw=sys.stdin.read(); body,code=raw.rsplit("\nHTTP ",1); print("HTTP", code.strip())
for s in json.loads(body): print(s.get("id"), "| refused:", (s.get("refused") or "")[:200], "| inputs:", len(s.get("inputs") or []))'
echo "== pb lists none"; C "$O/api/proforma/scenarios" -H 'X-OpenFerment-Project: pb'; echo
