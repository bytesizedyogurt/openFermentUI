#!/usr/bin/env bash
# Rows 9 and 26: a runbook and a deposition kept through PUT /api/state (StateKept); GET /api/state answers a
# ProjectState; runbooks_read lists the deposition and the reading; DELETE answers a StateTakenBack; a deposition
# is refused a DELETE; the other project reads none of it.
O=${1:-http://127.0.0.1:8950}
C() { curl -s --noproxy "*" "$@"; }
J='content-type: application/json'
AT=2026-11-10T00:00:00Z
RB='{"by":"Ada Moreno","value":{"id":"rb-p9","title":"A placeholder runbook","kind":"research","status":"draft","lockedAt":null,"productId":null,"strainId":null,"predictions":[],"stages":[],"measurementSchema":[{"id":"m-p9","label":"A placeholder measure","unit":"g/L","timepoint":"harvest","predictionId":null}]}}'
echo "== PUT runbook"; C -X PUT "$O/api/state/runbooks/rb-p9" -H 'X-OpenFerment-Project: pa' -H "$J" -d "$RB" | head -c 300; echo
DEP='{"by":"Ada Moreno","value":{"id":"dep-p9","runbookId":"rb-p9","protocolId":null,"operatorId":null,"reconciliation":null,"state":"running","startedAt":"'$AT'","closedAt":null,"observations":[],"sampleTimes":{"de-p9":1},"entries":[{"id":"de-p9","measureId":"m-p9","stepId":"s-a","at":"'$AT'","value":1.5,"unit":"g/L","raw":"1.5","confirmed":true}]}}'
echo "== PUT deposition"; C -X PUT "$O/api/state/depositions/dep-p9" -H 'X-OpenFerment-Project: pa' -H "$J" -d "$DEP" | head -c 300; echo
echo "== GET /api/state keys in pa and pb"
C "$O/api/state" -H 'X-OpenFerment-Project: pa' | python3 -c 'import json,sys; d=json.load(sys.stdin); print({k:(len(v) if hasattr(v,"__len__") else v) for k,v in d.items()})'
C "$O/api/state" -H 'X-OpenFerment-Project: pb' | python3 -c 'import json,sys; d=json.load(sys.stdin); print({k:(len(v) if hasattr(v,"__len__") else v) for k,v in d.items()})'
echo "== runbooks_read in pa"
C -X POST "$O/api/tools/runbooks_read" -H 'X-OpenFerment-Project: pa' -H "$J" -d '{"ids":[],"words":"","kind":"","state":"","limit":20}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("error"), [(r["kind"], r["id"]) for r in d.get("rows",[])], "partial:", (d.get("summary") or {}).get("partial"))'
echo "== runbooks_read in pb"
C -X POST "$O/api/tools/runbooks_read" -H 'X-OpenFerment-Project: pb' -H "$J" -d '{"ids":[],"words":"","kind":"","state":"","limit":20}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("error"), [(r["kind"], r["id"]) for r in d.get("rows",[])])'
echo "== DELETE deposition (kept as made) and DELETE runbook"
C -X DELETE "$O/api/state/depositions/dep-p9?by=Ada%20Moreno" -H 'X-OpenFerment-Project: pa' -w ' %{http_code}\n'
C -X DELETE "$O/api/state/runbooks/rb-p9-none?by=Ada%20Moreno" -H 'X-OpenFerment-Project: pa' -w ' %{http_code}\n'
echo "== readings a run may take, in g/L"
C "$O/api/depositions/readings?unit=g/L" -H 'X-OpenFerment-Project: pa' | head -c 400; echo
