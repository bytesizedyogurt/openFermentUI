#!/usr/bin/env bash
# H2-01: a comparison row takes the first run's unit for every run's value of a name and reckons the
# change across two units. Two kinetics fits of the same readings, the product in g L-1 and in mg L-1
# (x1000), each forecast; a comparison of the two forecast runs.
#   bash bughunt/repro/H2-01/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
DB=bh_r_h2_01_cmp
PORT=""
for p in $(seq 9600 9609); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "no free port in 9600-9609"; echo "RESULT: NO-DEFECT"; exit 0; }
O=http://127.0.0.1:$PORT; P=h2-01
W=$(mktemp -d "$BH_WORK/H2-01-run.XXXXXX")
cleanup() { bh_svc_stop "$PORT"; PGOPTIONS='-c client_min_messages=warning' bh_db_drop "$DB"; rm -rf "$W" "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"; }
trap cleanup EXIT

api() {  # api METHOD PATH [JSON | @file]: the body on stdout
  local m="$1" path="$2" body="${3:-}"
  local args=(-s --noproxy '*' -X "$m" -H "X-OpenFerment-Project: $P" "$O$path")
  [ -n "$body" ] && args+=(-H 'content-type: application/json' --data-binary "$body")
  curl "${args[@]}"
}

(export PGOPTIONS='-c client_min_messages=warning'; bh_db_fresh "$DB") || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $(BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PORT")  database: $DB (fresh)"
bh_project "$O" "$P" >/dev/null

# The same logistic readings twice: the product series in g L-1, then the same numbers x1000 in mg L-1.
python3 -I - "$W" <<'PY'
import json, math, sys
w = sys.argv[1]
ts = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24]
X = lambda t: 5.0 / (1 + (5.0 - 0.1) / 0.1 * math.exp(-0.4 * t))
for name, unit, scale in (("g", "g L-1", 1), ("mg", "mg L-1", 1000)):
    series = [
        {"measureId": "m-x", "label": "biomass", "unit": "g L-1", "role": "biomass",
         "points": [{"t": t, "value": round(X(t), 5), "entryId": f"x{t}", "confirmed": True} for t in ts]},
        {"measureId": "m-p", "label": "ethanol", "unit": unit, "role": "product",
         "points": [{"t": t, "value": round(4.0 * (X(t) - 0.1) * scale, 5), "entryId": f"p{t}", "confirmed": True} for t in ts]},
        {"measureId": "m-s", "label": "glucose", "unit": "g L-1", "role": "substrate",
         "points": [{"t": t, "value": round(max(0.0, 60 - 10 * (X(t) - 0.1)), 5), "entryId": f"s{t}", "confirmed": True} for t in ts]},
    ]
    json.dump({"depositionId": f"dep-{name}", "series": series}, open(f"{w}/fit_{name}.json", "w"))
PY

jget() { python3 -I -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
FG=$(api POST /api/fermos/fit "@$W/fit_g.json" | jget "['kineticArtifactId']")
FM=$(api POST /api/fermos/fit "@$W/fit_mg.json" | jget "['kineticArtifactId']")
RG=$(api POST /api/fermos/forecast "{\"fitArtifactId\":\"$FG\",\"by\":\"Repro H2-01\"}" | jget "['artifactId']")
RM=$(api POST /api/fermos/forecast "{\"fitArtifactId\":\"$FM\",\"by\":\"Repro H2-01\"}" | jget "['artifactId']")
echo "fits: $FG (g L-1), $FM (mg L-1); forecast runs: $RG, $RM"
api GET "/api/runs/$RG" > "$W/run_g.json"
api GET "/api/runs/$RM" > "$W/run_m.json"
api POST /api/studies/comparisons "{\"title\":\"two forecasts of one series\",\"runIds\":[\"$RG\",\"$RM\"],\"by\":\"Repro H2-01\"}" > "$W/cmp.json"
curl -s --noproxy '*' -H "X-OpenFerment-Project: $P" "$O/api/studies/export?by=Repro%20H2-01" -o "$W/pkg.zip"

python3 -I - "$W" <<'PY' || echo "RESULT: NO-DEFECT (the steps did not complete; see the lines above)"
import json, sys
w = sys.argv[1]
def final(path):
    r = json.load(open(path))["run"]
    v = next(v for v in r["outputs"]["values"] if v["name"] == "finals.product")
    return r["id"], v["quantity"]["value"], v["quantity"]["unit"]
(ig, vg, ug), (im, vm, um) = final(f"{w}/run_g.json"), final(f"{w}/run_m.json")
print(f"GET /api/runs/{ig}: finals.product = {vg} {ug}")
print(f"GET /api/runs/{im}: finals.product = {vm} {um}")
row = next(r for r in json.load(open(f"{w}/cmp.json"))["artifact"]["output"]["rows"] if r["key"] == "values.finals.product")
import zipfile
md = zipfile.ZipFile(f"{w}/pkg.zip").read("study.md").decode()
print("export study.md:", next(l for l in md.splitlines() if "values.finals.product" in l))
print(f"comparison row: key {row['key']}  unit {row['unit']!r}  values {row['values']}  change {row['change']}")
held_change = (vm * (0.001 if (ug, um) == ("g L-1", "mg L-1") else 1) - vg) / abs(vg)
print(f"EXPECTED: the two runs' values stay in their own units (a row a unit) or are held to one unit before "
      f"the change: run 2's {vm} {um} is {vm/1000:.4f} g L-1, a change of {held_change:+.4f} from run 1's {vg} {ug}")
print(f"OBSERVED: one row in {row['unit']!r} holds run 2's {row['values'][1]} (stated {um}), "
      f"its change {row['change'][1]:+.4f} ({row['change'][1]*100:+.2f} %)")
defect = (ug != um and row["unit"] == ug and row["values"][1] == vm
          and isinstance(row["change"][1], (int, float)) and abs(row["change"][1] - held_change) > 0.01)
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
exit 0
