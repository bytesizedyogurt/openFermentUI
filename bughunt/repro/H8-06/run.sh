#!/usr/bin/env bash
# H8-06: with no model reachable, a deep search (GET /api/literature/search?profile=deep) answers degradedStages []
# although its graph and HyDE stages fail on the model call (ModelUnavailable) and add nothing.
#
#   bash bughunt/repro/H8-06/run.sh        (from the repository root)
#
# A fresh database (bh_r_h8_06_deep, made by bh_db_fresh through bh_svc_start), the service on 127.0.0.1:10030,
# keyless: ANTHROPIC_API_KEY is empty, so llm.py refuses every model call with ModelUnavailable before any request
# leaves the machine. One project, one pasted passage, one deep search through the route; then the same search in
# process (traces.py) to read the kit's own stage traces and warnings. Ends with RESULT: DEFECT or RESULT: NO-DEFECT
# and exits 0; the service is stopped and the database and its data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h8_06_deep; PORT=10030; ORIGIN=http://127.0.0.1:$PORT; PROJECT=h8-06
OUT=$BH_WORK/H8-06; mkdir -p "$OUT"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB" "$OUT"; }
trap cleanup EXIT
api() { curl -s --noproxy '*' -H 'Content-Type: application/json' -H "X-OpenFerment-Project: $PROJECT" "$@"; }
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: a deep search whose graph and HyDE stages fail on their model call names them in degradedStages" \
     "(SearchResponse, docs/api/openapi.json:13180: \"the retrieval layers that timed out or failed, so a narrow result says why\")."

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$PROJECT" "H8-06 repro" >/dev/null
KEY=$(curl -s --noproxy '*' "$ORIGIN/api/health" | python3 -c "import json,sys; print(json.load(sys.stdin).get('hasKey'))" 2>/dev/null)
echo "OBSERVED: the service's health says hasKey: $KEY"
[ "$KEY" = False ] || finish "the service holds a key; this repro needs none"

PASTED=$(api -X POST "$ORIGIN/api/intake/paste" \
  -d '{"title":"Deep","text":"Corn stover pretreatment releases xylose.","by":"H8 Repro"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('status'))" 2>/dev/null)
[ "$PASTED" = ingested ] || finish "the pasted passage was not ingested ($PASTED)"

api -G "$ORIGIN/api/literature/search" --data-urlencode 'q=corn stover' --data-urlencode 'profile=deep' > "$OUT/route.json"
read -r PROFILE DEGRADED HITS < <(python3 -c "
import json,sys; r=json.load(open(sys.argv[1]))
print(r.get('profile'), json.dumps(r.get('degradedStages')).replace(' ',''), len(r.get('hits', [])))" "$OUT/route.json")
echo "OBSERVED: the route answers profile $PROFILE | degradedStages $DEGRADED | hits $HITS"

# The same call in process, over the same database, to read what each stage did.
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$BH_WORK/data-$DB" \
   .venv/bin/python -I "$HERE/traces.py" "$PROJECT" "corn stover") > "$OUT/probe.log" 2>&1
sed -E 's/\x1b\[[0-9;]*m//g' "$BH_WORK/svc-$PORT.log" | grep -E 'query_entity_extraction_failed|hyde_generation_failed' \
  | tee "$OUT/svc-warnings.log" | sed -E 's/  +/ /g; s/^/OBSERVED: the service logged, during the route call: /'
sed -E 's/\x1b\[[0-9;]*m//g' "$OUT/probe.log" | grep -E 'query_entity_extraction_failed|hyde_generation_failed' \
  | sed -E 's/  +/ /g; s/^/OBSERVED: in process, the kit logged: /'
TRACES=$(grep '^TRACES ' "$OUT/probe.log" | head -1 | cut -d' ' -f2-)
[ -n "$TRACES" ] || { sed 's/^/  probe: /' "$OUT/probe.log" | tail -20; finish "the in-process probe printed no traces"; }
echo "OBSERVED: in process, the kit's traces: $TRACES"

python3 - "$OUT/route.json" "$TRACES" "$OUT/svc-warnings.log" <<'PY'
import json, sys
route = json.load(open(sys.argv[1])); traces = json.loads(sys.argv[2]); log = open(sys.argv[3]).read()
stages = traces["stages"]
failed_model_calls = ("query_entity_extraction_failed" in log and "hyde_generation_failed" in log
                      and "ModelUnavailable" in log)
# The defect: the model calls behind graph and HyDE failed, their stages read 'empty' (no timeout, no error), and
# the route's degradedStages names neither.
defect = (route.get("profile") == "deep" and failed_model_calls
          and stages.get("graph") == "empty" and stages.get("hyde") == "empty"
          and not {"graph", "hyde"} & set(route.get("degradedStages", [])))
print("RESULT: " + ("DEFECT" if defect else "NO-DEFECT"))
PY
exit 0
