#!/usr/bin/env bash
# H2-02: a Proforma scenario run (precision rtol 0, atol 0) replays outside its precision in a fresh worker.
# From a fresh database: a library run, then a Proforma run, replayed in the same worker (identical), then the
# service restarted and the same artifact replayed (last-digit differences, withinTolerance false).
#   bash repro_proforma_replay.sh            (port 8822, database bh_h2_rep; both dropped/stopped at the end)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
S=/home/user/openFermentUI/bughunt/notes/H2/scripts
PORT=${PORT:-8822}; DB=${DB:-bh_h2_rep}; O=http://127.0.0.1:$PORT; W=$BH_WORK/H2/rep-$PORT; mkdir -p "$W"
BH_FIXTURES=1 bh_svc_start "$DB" "$PORT" >/dev/null || exit 1
bh_project "$O" rep >/dev/null
python3 -I "$S/api.py" "$O" rep POST /api/library/cornstover/run '{"by":"Hunter H2"}' > "$W/lib.json" 2>/dev/null
python3 - "$W" <<'EOF'
import json, sys
o = {"kind": "person-assumption", "by": "Hunter H2", "at": "2026-11-10", "note": "a placeholder the hunt sets"}
vals = {"feed_glucose_conc": (100, "g L-1"), "titre": (50, "g L-1"), "yield": (0.45, "g g-1"),
        "productivity": (2, "g L-1 h-1"), "plant_scale": (50000, "t yr-1"), "glucose_price": (0.3, "USD kg-1")}
inputs = [{"name": k, "quantity": {"value": v, "unit": u, "origin": o}} for k, (v, u) in vals.items()]
json.dump({"scenarioId": "ethanol_glucose_v0", "flowsheet": "ethanol_glucose_v0", "inputs": inputs, "by": "Hunter H2",
           "samples": 20}, open(sys.argv[1] + "/req.json", "w"))
EOF
python3 -I "$S/api.py" "$O" rep POST /api/proforma/run "@$W/req.json" > "$W/run.json" 2>/dev/null
AID=$(python3 -c "import json; print(json.load(open('$W/run.json'))['artifactId'])")
say() { python3 -c "
import json; d=json.load(open('$1')); print('$2', 'identical', d['identical'], 'withinTolerance', d['withinTolerance'], 'tolerance', d.get('tolerance'), len(d['differences']), 'differences', [(x['path'], x['stored'], x['replayed']) for x in d['differences'][:3]])"; }
python3 -I "$S/api.py" "$O" rep POST "/api/biorepo/artifacts/$AID/replay" '{}' > "$W/replay1.json" 2>/dev/null
say "$W/replay1.json" "run $AID, replayed in the worker that ran it:"
bh_svc_stop "$PORT"
BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PORT" >/dev/null || exit 1
python3 -I "$S/api.py" "$O" rep POST "/api/biorepo/artifacts/$AID/replay" '{}' > "$W/replay2.json" 2>/dev/null
say "$W/replay2.json" "run $AID, replayed after the service restarts:"
python3 -I "$S/api.py" "$O" rep GET "/api/engines" 2>/dev/null | python3 -c "
import json,sys; t=[t for e in json.load(sys.stdin) if e['name']=='biosteam' for t in e['things'] if t['id']=='ethanol_glucose_v0'][0]; print('the engine states for ethanol_glucose_v0: precision', t['precision'])"
bh_svc_stop "$PORT"; [ "${KEEP:-0}" = 1 ] || bh_db_drop "$DB"
