#!/usr/bin/env bash
# A biosteam scenario flowsheet (ethanol_glucose_v0) run with six fixed values (no range, so all 500 samples
# take the base case's inputs): its price.solvedPrice against its own quantiles, then two replays (the first
# in the worker the run warmed). The head's service on bh_h1_rs, port 8814; keyless.
source /home/user/openFermentUI/bughunt/lib/env.sh
T=$BH_WORK/H1; mkdir -p "$T"
[ -f "$T/r3-inputs.json" ] || { echo "run repro_h1_03.sh first (it writes r3-inputs.json)"; exit 2; }
O=$(bh_svc_start bh_h1_rs 8814) || exit 1
bh_project "$O" h1rs >/dev/null
body=$(python3 -c "import json; print(json.dumps({'thing':'ethanol_glucose_v0','by':'H1','inputs':json.load(open('$T/r3-inputs.json'))}))")
curl -s --noproxy '*' -m 900 -X POST "$O/api/engines/biosteam/run" -H 'content-type: application/json' -H 'X-OpenFerment-Project: h1rs' -d "$body" > "$T/rs-run.json"
python3 - "$T/rs-run.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); r = d["run"]; o = d["artifact"]["output"]
print("run", r["id"], r["status"], "precision stated: rtol 0, atol 0 (engines.md)")
print("price.solvedPrice", o["basePrice"], "| quantiles", o["quantiles"])
print("inputs set, each low = value = high:", [(i["name"], i["value"]) for i in d["artifact"]["inputs"] if i["name"] in ("yield", "yield low", "yield high")])
PY
A=$(python3 -c "import json; print(json.load(open('$T/rs-run.json'))['run']['artifactId'])")
for k in 1 2; do
  curl -s --noproxy '*' -m 900 -X POST "$O/api/biorepo/artifacts/$A/replay" -H 'X-OpenFerment-Project: h1rs' | python3 -c "
import sys, json; d = json.load(sys.stdin)
print('replay $k: identical', d['identical'], 'withinTolerance', d['withinTolerance'], 'differences', len(d['differences']), [(x['stored'], x['replayed']) for x in d['differences'] if x['path'] == 'basePrice'])"
done
bh_svc_stop 8814; bh_db_drop bh_h1_rs
