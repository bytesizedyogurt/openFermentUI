#!/usr/bin/env bash
# A library run in flight on the biosteam engine (POST /api/engines/biosteam/run), its Proforma worker
# (the child of the service on PORT) killed with SIGKILL after DELAY s; then the answer, the rows,
# GET /api/engines' workerStatus for biosteam and train, and the same request asked again.
# usage: kill_proforma.sh PORT PROJECT DB PLANT DELAY
PORT=$1; P=$2; DB=$3; PLANT=$4; DELAY=${5:-6}; O=http://127.0.0.1:$PORT
svc=$(lsof -t -iTCP:$PORT -sTCP:LISTEN | head -1)
curl -s --noproxy '*' -m 900 -X POST "$O/api/engines/biosteam/run" -H 'content-type: application/json' -H "X-OpenFerment-Project: $P" -d "{\"thing\":\"$PLANT\",\"by\":\"H1\"${CFG:+,\"configuration\":\"$CFG\"}}" -w ' [%{http_code}]\n' > /tmp/h1kp.out &
sleep "$DELAY"
w=$(pgrep -P "$svc" -f proforma_worker | head -1); echo "service $svc, killing its Proforma worker $w"; kill -KILL "$w"
wait
echo "answer: $(head -c 400 /tmp/h1kp.out)"
psql "postgresql://openferment:openferment@127.0.0.1:5432/$DB" -AtXc "select 'rows for $PLANT: '||count(*) from openferment.runs where project_id='$P' and engine='biosteam' and body->>'plant'='$PLANT'"
echo "worker alive now: $(pgrep -P "$svc" -f proforma_worker | wc -l)"
curl -s --noproxy '*' "$O/api/engines" -H "X-OpenFerment-Project: $P" | python3 -c "import sys,json; [print('workerStatus', e['name'], e['workerStatus']) for e in json.load(sys.stdin) if e['name'] in ('biosteam','train')]"
curl -s --noproxy '*' "$O/api/proforma/simulator" -H "X-OpenFerment-Project: $P" -w ' [%{http_code}]\n' | head -c 300; echo
echo "asked again:"; curl -s --noproxy '*' -m 900 -X POST "$O/api/engines/biosteam/run" -H 'content-type: application/json' -H "X-OpenFerment-Project: $P" -d "{\"thing\":\"$PLANT\",\"by\":\"H1\"${CFG:+,\"configuration\":\"$CFG\"}}" -w ' [%{http_code}]\n' | head -c 300; echo
