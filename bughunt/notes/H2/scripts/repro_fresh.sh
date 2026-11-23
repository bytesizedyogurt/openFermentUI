#!/usr/bin/env bash
# H2's candidates from a fresh database, one section a candidate, on port 8823 (database bh_h2_fresh).
#   bash repro_fresh.sh                 (stops the service and drops the database at the end; KEEP=1 keeps both)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
S=/home/user/openFermentUI/bughunt/notes/H2/scripts
PORT=${PORT:-8823}; DB=${DB:-bh_h2_fresh}; O=http://127.0.0.1:$PORT; P=fresh; W=$BH_WORK/H2/fresh-$PORT; mkdir -p "$W"; cd "$W"
api() { python3 -I "$S/api.py" "$O" "$P" "$@" 2>/dev/null; }
BH_FIXTURES=1 bh_svc_start "$DB" "$PORT" >/dev/null || exit 1
bh_project "$O" "$P" >/dev/null

echo "== H2-01: one comparison row holds values in two units, its change reckoned across them"
python3 -I "$S/make_fit.py" fit_g.json dep-g "g L-1" 1
python3 -I "$S/make_fit.py" fit_mg.json dep-mg "mg L-1" 1000
FG=$(api POST /api/fermos/fit @fit_g.json | python3 -c "import json,sys; print(json.load(sys.stdin)['kineticArtifactId'])")
FM=$(api POST /api/fermos/fit @fit_mg.json | python3 -c "import json,sys; print(json.load(sys.stdin)['kineticArtifactId'])")
RG=$(api POST /api/fermos/forecast "{\"fitArtifactId\":\"$FG\",\"by\":\"Hunter H2\"}" | python3 -c "import json,sys; print(json.load(sys.stdin)['artifactId'])")
RM=$(api POST /api/fermos/forecast "{\"fitArtifactId\":\"$FM\",\"by\":\"Hunter H2\"}" | python3 -c "import json,sys; print(json.load(sys.stdin)['artifactId'])")
api GET "/api/runs/$RM" | python3 -c "
import json,sys; r=json.load(sys.stdin)['run']; print('  run', r['id'], [ (v['name'], v['quantity']['value'], v['quantity']['unit']) for v in r['outputs']['values'] if v['name']=='finals.product'])"
api POST /api/studies/comparisons "{\"title\":\"two forecasts\",\"runIds\":[\"$RG\",\"$RM\"],\"by\":\"Hunter H2\"}" > cmp.json
python3 -c "
import json; a=json.load(open('cmp.json'))['artifact']
for r in a['output']['rows']: print('  row', r['key'], 'unit', repr(r['unit']), 'values', r['values'], 'change', r['change'])"

echo "== H2-03, H2-04: a locked runbook through the state door"
bh_env /home/user/openFermentUI/core/.venv/bin/python -I "$S/lock_probe.py" "$O" "$P" "$RG" values.finals.product values.finals.biomass

echo "== H2-05: the export package leaves out the kinetic fits its forecast runs rest on"
curl -s --noproxy '*' -H "X-OpenFerment-Project: $P" "$O/api/studies/export?by=Hunter%20H2" -o pkg.zip
mkdir -p pkg && mv pkg.zip pkg/ && (cd pkg && python3 -I -S "$S/open_export.py" pkg.zip | grep -A3 "rests on")

echo "== H2-06: oilcane's package test read with no configuration, beside its run with none"
api GET /api/library/oilcane/regression | python3 -c "import json,sys; print('  GET /api/library/oilcane/regression ->', json.load(sys.stdin))"
api GET "/api/library/oilcane/regression?configuration=S1" | python3 -c "import json,sys; d=json.load(sys.stdin); print('  ?configuration=S1 ->', d['test'], len(d['values']), 'values')"
api POST /api/library/oilcane/run '{"by":"Hunter H2"}' | python3 -c "import json,sys; r=json.load(sys.stdin)['run']; print('  POST /api/library/oilcane/run {} -> configuration', r['configuration'], 'held to the test:', r['outputs'].get('regression'))"

echo "== H2-07: two scenarios for the same values on the same plant in the same configuration"
V='[{"key":"tea.IRR","quantity":{"value":0.12,"unit":"","origin":{"kind":"person-assumption","by":"Hunter H2","at":"2026-11-10","note":"a placeholder the hunt sets"}}}]'
A=$(api POST /api/studies/scenarios "{\"title\":\"cane, no configuration named\",\"plant\":\"cane\",\"values\":$V,\"by\":\"Hunter H2\"}" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
B=$(api POST /api/studies/scenarios "{\"title\":\"cane S1\",\"plant\":\"cane\",\"configuration\":\"S1\",\"values\":$V,\"by\":\"Hunter H2\"}" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
api POST "/api/studies/scenarios/$A/run" '{"by":"Hunter H2"}' | python3 -c "import json,sys; r=json.load(sys.stdin)['run']; print('  scenario $A ran as', r['id'], r['configuration'], 'scenarioId', r['scenarioId'])"
api POST "/api/studies/scenarios/$B/run" '{"by":"Hunter H2"}' | python3 -c "import json,sys; r=json.load(sys.stdin)['run']; print('  scenario $B ran as', r['id'], r['configuration'], 'scenarioId', r['scenarioId'])"

echo "== H2-08: a comparison asked again with a blank title loses the title it was kept with"
api POST /api/studies/comparisons "{\"title\":\"   \",\"runIds\":[\"$RG\",\"$RM\"],\"by\":\"Someone Else\"}" | python3 -c "import json,sys; c=json.load(sys.stdin)['comparison']; print('  kept as', c['id'], 'title', repr(c['title']), 'by', c['by'])"

bh_svc_stop "$PORT"; [ "${KEEP:-0}" = 1 ] || bh_db_drop "$DB"
