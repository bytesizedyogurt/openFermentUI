#!/usr/bin/env bash
# H1-04: the biosteam engine's doors run, and keep receipts for, a configuration and a plant GET /api/engines
# does not list (cellulosic_ethanol_v0 'AFEX, IB'; lactic). The head's service on bh_h1_r4, port 8812.
source /home/user/openFermentUI/bughunt/lib/env.sh
O=$(bh_svc_start bh_h1_r4 8812) || exit 1
bh_project "$O" h1r4 >/dev/null
H=(-H 'content-type: application/json' -H 'X-OpenFerment-Project: h1r4')
curl -s --noproxy '*' "$O/api/engines" "${H[@]}" | python3 -c "
import sys, json
for e in json.load(sys.stdin):
    if e['name'] == 'biosteam':
        print('listed:', {t['id']: t['configurations'] for t in e['things'] if t['id'] in ('cellulosic_ethanol_v0', 'lactic')}, 'lactic listed:', any(t['id'] == 'lactic' for t in e['things']))"
for body in '{"thing":"cellulosic_ethanol_v0","configuration":"AFEX, IB","by":"H1"}' '{"thing":"lactic","by":"H1"}'; do
  curl -s --noproxy '*' -m 900 -X POST "$O/api/engines/biosteam/run" "${H[@]}" -d "$body" -w ' [%{http_code}]\n'; done
psql "$BH_SERVER/bh_h1_r4" -AtXc "select id, engine, status, body->>'plant', coalesce(body->>'configuration','') from openferment.runs where project_id='h1r4'"
bh_svc_stop 8812; bh_db_drop bh_h1_r4
