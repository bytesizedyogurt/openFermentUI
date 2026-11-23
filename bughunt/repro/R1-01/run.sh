#!/usr/bin/env bash
# R1-01: docs/PROGRESS.md's D8 departure row names `GET /api/artifacts` as the route the reference screen
# reads the project's kept reference runs from; the service serves no such route.
# Static half: the row, the generated schema, the app's own route table, the client's call.
# Live half: the head's service on a fresh database, port 10930, asked both paths; keyless, no model call.
# usage, from the repository root: bash bughunt/repro/R1-01/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_r1_01_svc
PORT=10930
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB"; }
trap cleanup EXIT
cd "$BH_ROOT" || exit 0

echo "EXPECTED: the D8 departure row in docs/PROGRESS.md names the route the reference screen reads kept"
echo "EXPECTED: reference runs from, a route the service serves: GET /api/biorepo/artifacts?tool= (src/lib/proforma.ts:169-171)."

# The D8 row that retires the two routes and names what the reference screen reads instead.
rowline=$(grep -n 'alpha 2.2 D8, C.6' docs/PROGRESS.md | grep 'proforma/reference/{id}' | head -1 | cut -d: -f1)
echo "--- the row (docs/PROGRESS.md:$rowline), the routes it names for the reference screen:"
sed -n "${rowline}p" docs/PROGRESS.md | grep -o '`GET /api/[^`]*`' | sed "s/^/    /"
named=$(sed -n "${rowline}p" docs/PROGRESS.md | grep -c '(`GET /api/artifacts`)')

echo "--- docs/api/openapi.json, every path holding 'artifacts':"
inschema=$(python3 - <<'PY'
import json
paths = json.load(open("docs/api/openapi.json"))["paths"]
for p in paths:
    if "artifacts" in p: print("   ", p, sorted(paths[p]))
print("IN_SCHEMA", "/api/artifacts" in paths)
PY
)
echo "$inschema" | grep -v IN_SCHEMA
s_schema=$(echo "$inschema" | awk '/IN_SCHEMA/{print $2}')

echo "--- the app's route table (openferment_core.api:app.routes, outside the schema too):"
inapp=$(bh_py -c "
from openferment_core.api import app
ps = sorted({getattr(r, 'path', '') for r in app.routes})
print('   ', len(ps), 'routes;', [p for p in ps if 'artifacts' in p])
print('IN_APP', '/api/artifacts' in ps)
" 2>/dev/null)
echo "$inapp" | grep -v IN_APP
s_app=$(echo "$inapp" | awk '/IN_APP/{print $2}')

echo "--- api.py decorators naming an artifacts path:"
grep -nE '@app\.(get|post|put|delete|patch)\("/api/[a-z/]*artifacts' core/openferment_core/api.py | sed 's/, response_model.*//; s/^/    /'
deco=$(grep -cE '@app\.(get|post|put|delete|patch)\("/api/artifacts["/]' core/openferment_core/api.py)

echo "--- what the reference screen calls (ProformaReference.tsx keptReferenceRuns -> lib/proforma.ts):"
grep -n 'keptReferenceRuns(ctrl.signal)' src/screens/ProformaReference.tsx | sed 's/^/    ProformaReference.tsx:/'
grep -n "call<Artifact\[\]>(\`/api/biorepo/artifacts?" src/lib/proforma.ts | sed 's/^/    proforma.ts:/'
client=$(grep -rnE "['\`]/api/artifacts['?\`/]" src | wc -l)
echo "    client files naming /api/artifacts: $client"

echo "--- live: the service on a fresh database, both paths asked in one project"
O=$(bh_svc_start "$DB" "$PORT") || O=""
if [ -n "$O" ]; then
  bh_project "$O" r101 >/dev/null
  a=$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -H 'X-OpenFerment-Project: r101' "$O/api/artifacts")
  b=$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -H 'X-OpenFerment-Project: r101' \
        "$O/api/biorepo/artifacts?tool=proforma.reference&tool=proforma_benchmark")
  echo "    GET /api/artifacts -> $a; GET /api/biorepo/artifacts?tool=proforma.reference&tool=proforma_benchmark -> $b"
else
  a=none; b=none; echo "    the service did not start"
fi

echo "OBSERVED: the row names (\`GET /api/artifacts\`) [$named]; in openapi.json: $s_schema; in the app's routes: $s_app;"
echo "OBSERVED: api.py decorators for it: $deco; client calls of it: $client; live GET /api/artifacts -> $a, the screen's route -> $b"
if [ "$named" -ge 1 ] && [ "$s_schema" = False ] && [ "$s_app" = False ] && [ "$deco" -eq 0 ] && [ "$a" != 200 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
