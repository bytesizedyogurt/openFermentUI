#!/usr/bin/env bash
# Row 25 (7e178bb): a Proforma door takes a deposition's reading in its own value and unit and sets it in the
# parameter's unit, the conversion stated in the note. The reading dep-p9/de-p9 is 1.5 g/L; titre is in g L-1.
# Also a reading sent in a unit that does not match the reading, and one sent to pb, which holds no such reading.
O=${1:-http://127.0.0.1:8950}
C() { curl -s --noproxy "*" "$@"; }
enc() { python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$1"; }
M='[{"name":"titre","quantity":{"value":1.5,"unit":"g/L","origin":{"kind":"measurement","by":"Ada Moreno","at":"2026-11-10T00:00:00Z","ref":"dep-p9/de-p9"}}}]'
echo "== bind in pa with the reading in its own unit"
C "$O/api/proforma/bind?flowsheet=ethanol_glucose_v0&inputs=$(enc "$M")" -H 'X-OpenFerment-Project: pa' | python3 -c '
import json,sys; d=json.load(sys.stdin)
for i in d.get("inputs",[]):
    if i["key"]=="titre": print({k:i.get(k) for k in ("key","unit","binding","value","low","high","sampling","source")})
' 2>&1 | head -5
echo "== the reading sent in mg/mL (another unit the reading was not kept in)"
M2=$(echo "$M" | sed 's#"value":1.5,"unit":"g/L"#"value":1.5,"unit":"mg/mL"#')
C "$O/api/proforma/bind?flowsheet=ethanol_glucose_v0&inputs=$(enc "$M2")" -H 'X-OpenFerment-Project: pa' -w ' HTTP %{http_code}\n' | tail -c 300
echo "== the reading sent in pb"
C "$O/api/proforma/bind?flowsheet=ethanol_glucose_v0&inputs=$(enc "$M")" -H 'X-OpenFerment-Project: pb' -w ' HTTP %{http_code}\n' | tail -c 300
echo "== the ceiling check in pa"
C "$O/api/proforma/ceiling-check?scenarioId=sc-p10c&inputs=$(enc '[{"name":"yield","quantity":{"value":0.4,"unit":"g g-1","origin":{"kind":"person-assumption","by":"Ada Moreno","at":"2026-11-10T00:00:00Z"}}}]')" -H 'X-OpenFerment-Project: pa' -w ' HTTP %{http_code}\n' | tail -c 400
