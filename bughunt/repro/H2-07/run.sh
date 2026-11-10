#!/usr/bin/env bash
# H2-07: the same values on the same plant, asked once with no configuration and once naming the plant's
# default, are kept as two study scenarios, which run as one runs row naming the first alone.
# A fresh database and service (keyless, fixtures on), one project, cane's default read from GET /api/engines,
# two POST /api/studies/scenarios with one person-assumption value (tea.IRR 0.12), each run once, then the
# runs and scenarios read back. scenarios.scenario_id is then called on the first scenario's kept values
# with the configuration its run resolved to, to show the id a resolved key would give.
#   bash bughunt/repro/H2-07/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
DB=bh_r_h2_07_scenarios
PORT=""
for p in $(seq 9790 9799); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "no free port in 9790-9799"; echo "RESULT: NO-DEFECT"; exit 0; }
O=http://127.0.0.1:$PORT; P=h2-07
mkdir -p "$BH_WORK/H2-07"
W=$(mktemp -d "$BH_WORK/H2-07/run.XXXXXX")
cleanup() {
  bh_svc_stop "$PORT"; PGOPTIONS='-c client_min_messages=warning' bh_db_drop "$DB"
  rm -rf "$W" "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"; rmdir "$BH_WORK/H2-07" 2>/dev/null || true
}
trap cleanup EXIT

api() {  # api METHOD PATH [JSON]: the body to $W/NAME.json, the status printed
  local name="$1" m="$2" path="$3" body="${4:-}"
  local args=(-s --noproxy '*' -X "$m" -H "X-OpenFerment-Project: $P" -o "$W/$name.json" -w '%{http_code}' "$O$path")
  [ -n "$body" ] && args+=(-H 'content-type: application/json' --data-binary "$body")
  curl "${args[@]}"
}
jget() { python3 -I -c "import json,sys; d=json.load(open(sys.argv[1])); print(d$2)" "$W/$1.json" 2>/dev/null; }

(export PGOPTIONS='-c client_min_messages=warning'; bh_db_fresh "$DB") || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $(BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PORT")  database: $DB (fresh)"
bh_project "$O" "$P" >/dev/null

echo "GET /api/engines $(api engines GET /api/engines)"
DEF=$(python3 -I -c "
import json,sys
for e in json.load(open(sys.argv[1])):
    for t in e.get('things') or []:
        if e['name']=='biosteam' and t['id']=='cane': print(t['defaultConfiguration']); sys.exit()
" "$W/engines.json")
echo "cane on the biosteam engine: defaultConfiguration $DEF"

V='[{"key":"tea.IRR","quantity":{"value":0.12,"unit":"","origin":{"kind":"person-assumption","by":"Repro H2-07","at":"2026-11-10","note":"a placeholder the reproduction sets"}}}]'
echo "POST /api/studies/scenarios (no configuration) $(api a POST /api/studies/scenarios "{\"title\":\"cane, no configuration named\",\"plant\":\"cane\",\"values\":$V,\"by\":\"Repro H2-07\"}")"
echo "POST /api/studies/scenarios (configuration $DEF) $(api b POST /api/studies/scenarios "{\"title\":\"cane $DEF\",\"plant\":\"cane\",\"configuration\":\"$DEF\",\"values\":$V,\"by\":\"Repro H2-07\"}")"
echo "POST /api/studies/scenarios (no configuration, asked again) $(api a2 POST /api/studies/scenarios "{\"title\":\"cane, asked again\",\"plant\":\"cane\",\"values\":$V,\"by\":\"Repro H2-07\"}")"
A=$(jget a "['id']"); B=$(jget b "['id']"); A2=$(jget a2 "['id']")
echo "  scenario A $A configuration $(jget a "['configuration']"); scenario B $B configuration $(jget b "['configuration']"); A asked again $A2"
echo "POST /api/studies/scenarios/$A/run $(api ra POST "/api/studies/scenarios/$A/run" '{"by":"Repro H2-07"}')"
echo "POST /api/studies/scenarios/$B/run $(api rb POST "/api/studies/scenarios/$B/run" '{"by":"Repro H2-07"}')"
echo "GET /api/runs $(api runs GET /api/runs)"
echo "GET /api/studies/scenarios $(api list GET /api/studies/scenarios)"
echo "GET /api/studies/scenarios/$B $(api gb GET "/api/studies/scenarios/$B")"

# The id scenarios.scenario_id gives A's kept values with the configuration A's run ran in (read only).
RCFG=$(jget ra "['run']['configuration']")
(cd "$BH_ROOT/core" && bh_env .venv/bin/python -I -c "
import json, sys
from openferment_core.models import ScenarioValue
from openferment_core.studies.scenarios import scenario_id
a = json.load(open(sys.argv[1])); cfg = sys.argv[2]
vals = [ScenarioValue.model_validate(v) for v in a['values']]
print(json.dumps({'as_made': scenario_id(a['plant'], a['configuration'], vals),
                  'resolved': scenario_id(a['plant'], cfg, vals)}))
" "$W/a.json" "$RCFG") > "$W/ids.json" 2> "$W/ids.err" || { echo "scenario_id call failed:"; cat "$W/ids.err"; }

python3 -I - "$W" "$DEF" <<'PY' || echo "RESULT: NO-DEFECT (the steps did not complete; see the lines above)"
import json, sys
w, default = sys.argv[1], sys.argv[2]
r = lambda n: json.load(open(f"{w}/{n}.json"))
a, b, a2, ra, rb, runs, listed, gb = (r(n) for n in ("a", "b", "a2", "ra", "rb", "runs", "list", "gb"))
ids = r("ids")
run_a, run_b = ra["run"], rb["run"]
print(f"scenario A {a['id']}: plant {a['plant']}, configuration {a['configuration']!r}, values {[(v['key'], v['quantity']['value']) for v in a['values']]}")
print(f"scenario B {b['id']}: plant {b['plant']}, configuration {b['configuration']!r}, values {[(v['key'], v['quantity']['value']) for v in b['values']]}")
print(f"the same ask as A made again: {a2['id']} (one scenario with A: {a2['id'] == a['id']})")
print(f"A's run: {run_a['id']}, configuration {run_a['configuration']}, scenarioId {run_a['scenarioId']}, status {run_a['status']}")
print(f"B's run: {run_b['id']}, configuration {run_b['configuration']}, scenarioId {run_b['scenarioId']}, status {run_b['status']}")
print(f"GET /api/runs: {[(x['id'], x['configuration'], x['scenarioId']) for x in runs]}")
print(f"GET /api/studies/scenarios: {[(x['id'], x['configuration'], x['runIds']) for x in listed]}")
print(f"GET /api/studies/scenarios/{b['id']}: runIds {gb['runIds']}")
print(f"scenarios.scenario_id on A's kept values: configuration as made {ids['as_made']}, "
      f"configuration its run resolved to ({run_a['configuration']}) {ids['resolved']}")
print(f"EXPECTED: the same values on the same plant in the configuration a run resolves to ({default}) are one "
      f"scenario (docs/api/studies.md:14): asked with no configuration and asked naming {default}, one id, "
      f"one scenario listed, and the run's scenarioId that scenario")
print(f"OBSERVED: two scenarios, {a['id']} (configuration {a['configuration']!r}) and {b['id']} (configuration "
      f"{b['configuration']!r}); both ran as the one run {run_a['id']} in configuration {run_a['configuration']}, "
      f"whose scenarioId names {run_a['scenarioId']} alone, and {b['id']}'s runIds list it too; the id keyed on "
      f"the resolved configuration would be {ids['resolved']}")
defect = (a["id"] != b["id"] and a["values"] == b["values"] and a["plant"] == b["plant"]
          and a["configuration"] is None and b["configuration"] == default
          and run_a["id"] == run_b["id"] and run_a["configuration"] == default
          and len(runs) == 1 and len(listed) == 2
          and run_b["scenarioId"] == a["id"] and run_a["id"] in gb["runIds"]
          and a2["id"] == a["id"] and ids["as_made"] == a["id"] and ids["resolved"] == b["id"])
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
exit 0
