#!/usr/bin/env bash
# H1-09: GET /api/engines says biosteam's and train's worker is `ready` while no Proforma worker process lives.
# The head's service on bh_h1_r9, port 8813: one library run warms the worker, the worker is killed, the listing read.
source /home/user/openFermentUI/bughunt/lib/env.sh
O=$(bh_svc_start bh_h1_r9 8813) || exit 1
bh_project "$O" h1r9 >/dev/null
curl -s --noproxy '*' -m 900 -X POST "$O/api/engines/biosteam/run" -H 'content-type: application/json' -H 'X-OpenFerment-Project: h1r9' -d '{"thing":"corn","by":"H1"}' -o /dev/null -w 'corn run %{http_code}\n'
svc=$(bh_port_pid 8813); w=$(pgrep -P "$svc" -f proforma_worker | head -1); kill -KILL "$w"; sleep 1
echo "Proforma workers alive under the service: $(pgrep -P "$svc" -f proforma_worker | wc -l)"
curl -s --noproxy '*' "$O/api/engines" -H 'X-OpenFerment-Project: h1r9' | python3 -c "import sys,json; [print(e['name'], 'workerStatus', e['workerStatus']) for e in json.load(sys.stdin) if e['name'] in ('biosteam','train')]"
bh_svc_stop 8813; bh_db_drop bh_h1_r9
