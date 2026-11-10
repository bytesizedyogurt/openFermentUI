#!/usr/bin/env bash
# H2-05: the study export package names, in a forecast run's basis, a kinetic fit it does not hold.
# A fresh database and service, one kinetic fit of logistic readings (POST /api/fermos/fit, kept as an
# artifact), its forecast kept as a run of the kinetics engine (POST /api/fermos/forecast), then the
# package (GET /api/studies/export), opened with the standard library alone (python3 -I -S).
#   bash bughunt/repro/H2-05/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
DB=bh_r_h2_05_export
PORT=""
for p in $(seq 9980 9989); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "no free port in 9980-9989"; echo "RESULT: NO-DEFECT"; exit 0; }
O=http://127.0.0.1:$PORT; P=h2-05
mkdir -p "$BH_WORK/H2-05"
W=$(mktemp -d "$BH_WORK/H2-05/run.XXXXXX")
cleanup() {
  bh_svc_stop "$PORT"; PGOPTIONS='-c client_min_messages=warning' bh_db_drop "$DB"
  rm -rf "$W" "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"; rmdir "$BH_WORK/H2-05" 2>/dev/null || true
}
trap cleanup EXIT

api() {  # api METHOD PATH [JSON | @file]: the body on stdout, the status as the last line
  local m="$1" path="$2" body="${3:-}"
  local args=(-s --noproxy '*' -X "$m" -H "X-OpenFerment-Project: $P" -w '\n%{http_code}' "$O$path")
  [ -n "$body" ] && args+=(-H 'content-type: application/json' --data-binary "$body")
  curl "${args[@]}"
}
body() { sed '$d'; }  # the body without the status line
jget() { python3 -I -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }

(export PGOPTIONS='-c client_min_messages=warning'; bh_db_fresh "$DB") || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $(BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PORT")  database: $DB (fresh)"
bh_project "$O" "$P" >/dev/null

# One run's readings: logistic biomass, product and substrate series (the hunt's make_fit.py, inline).
python3 -I - "$W" <<'PY'
import json, math, sys
ts = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24]
X = lambda t: 5.0 / (1 + (5.0 - 0.1) / 0.1 * math.exp(-0.4 * t))
series = [
    {"measureId": "m-x", "label": "biomass", "unit": "g L-1", "role": "biomass",
     "points": [{"t": t, "value": round(X(t), 5), "entryId": f"x{t}", "confirmed": True} for t in ts]},
    {"measureId": "m-p", "label": "ethanol", "unit": "g L-1", "role": "product",
     "points": [{"t": t, "value": round(4.0 * (X(t) - 0.1), 5), "entryId": f"p{t}", "confirmed": True} for t in ts]},
    {"measureId": "m-s", "label": "glucose", "unit": "g L-1", "role": "substrate",
     "points": [{"t": t, "value": round(max(0.0, 60 - 10 * (X(t) - 0.1)), 5), "entryId": f"s{t}", "confirmed": True} for t in ts]},
]
json.dump({"depositionId": "dep-h2-05", "series": series}, open(f"{sys.argv[1]}/fit_req.json", "w"))
PY
api POST /api/fermos/fit "@$W/fit_req.json" > "$W/fit.txt"
FIT=$(body < "$W/fit.txt" | jget "['kineticArtifactId']")
api POST /api/fermos/forecast "{\"fitArtifactId\":\"$FIT\",\"by\":\"Repro H2-05\"}" > "$W/forecast.txt"
RUN=$(body < "$W/forecast.txt" | jget "['artifactId']")
api GET "/api/runs/$RUN" > "$W/run.txt"
curl -s --noproxy '*' -H "X-OpenFerment-Project: $P" -w '%{http_code}' -o "$W/pkg.zip" \
     "$O/api/studies/export?by=Repro%20H2-05" > "$W/export.status"
echo "fit: POST /api/fermos/fit $(tail -1 "$W/fit.txt"), kinetic fit $FIT"
echo "forecast: POST /api/fermos/forecast $(tail -1 "$W/forecast.txt"), run $RUN; GET /api/runs/$RUN $(tail -1 "$W/run.txt")"
echo "export: GET /api/studies/export $(cat "$W/export.status"), $(wc -c < "$W/pkg.zip") bytes"

# What the service answered for the fit and the run, beside what the package holds (standard library alone).
python3 -I - "$W" "$FIT" "$RUN" <<'PY' > "$W/served.json"
import json, sys
w, fit, run = sys.argv[1:4]
def read(name):
    b, _, s = open(f"{w}/{name}.txt").read().rpartition("\n")
    return json.loads(b)
f = read("fit")["kinetic"]
r = read("run")
print(json.dumps({"fit": fit, "run": run, "params": {p["name"]: p["value"] for p in f["params"]},
                  "runInputs": [(i.get("key") or i.get("name"), i["quantity"]["value"] if "quantity" in i else i.get("value"))
                                for i in r["run"]["inputs"]],
                  "configuration": r["run"].get("configuration")}))
PY

cd "$W" && python3 -I -S - "$W/pkg.zip" "$W/served.json" <<'PY' || echo "RESULT: NO-DEFECT (the steps did not complete; see the lines above)"
import json, sys, zipfile
pkg, served = sys.argv[1], json.load(open(sys.argv[2]))
fit, run = served["fit"], served["run"]
z = zipfile.ZipFile(pkg)
held = json.loads(z.read("study.json"))
arts = held["artifacts"]
print("python -I -S, site imported:", "site" in sys.modules)
print("package members:", sorted(z.namelist()))
r = next((x for x in held["runs"] if x["id"] == run), None)
print(f"study.json runs: {[x['id'] for x in held['runs']]}; run {run}: engine {r and r.get('engine')}, "
      f"configuration {r and r.get('configuration')}, artifactId {r and r.get('artifactId')}")
print(f"study.json artifacts: {[(k, a['tool']) for k, a in arts.items()]}")
fa = arts.get(r["artifactId"]) if r else None
names = [(i["name"], i["value"], i["source"]) for i in fa["inputs"]] if fa else []
print(f"the run's artifact {r and r['artifactId']} ({fa and fa['tool']}): basis {names}")
rested = sorted({i["source"]["id"] for a in arts.values() for i in a["inputs"]
                 if i["source"]["kind"] == "artifact" and i["source"].get("id")})
absent = [k for k in rested if k not in arts]
print(f"artifacts a kept artifact's basis names (source kind 'artifact'): {rested}; absent from study.json: {absent}")
mentions = {n: z.read(n).decode("utf-8", "replace").count(fit) for n in z.namelist()}
print(f"times the fit's id {fit} appears, member by member: {mentions}")
print(f"the fit as the service kept it: params {served['params']}")
text = "".join(z.read(n).decode("utf-8", "replace") for n in z.namelist())
# As study.json writes a float (repr) and as study.md writes one (ten significant digits).
held_params = {k: (repr(v) in text or f"{v:.10g}" in text) for k, v in served["params"].items()}
print(f"each fitted parameter's value found anywhere in the package (repr or .10g): {held_params}")
print(f"the run's inputs as GET /api/runs/{run} serves them: {served['runInputs']}; configuration {served['configuration']}")
print(f"EXPECTED: study.json's artifacts hold the kinetic fit {fit} the forecast run's basis names (input 'kinetic fit', "
      f"source artifact), with its parameters, covariance and the readings it was fitted on, so the forecast's band "
      f"traces back to its source and calculation in the package alone (CLAUDE.md:8; docs/api/studies.md:234)")
print(f"OBSERVED: study.json's artifacts hold {sorted(arts)}; the forecast's basis names {absent or '(none absent)'}, "
      f"which no member of the package holds: the fit's id appears only as a reference "
      f"({sum(mentions.values())} times), and of its parameters {[k for k, v in held_params.items() if not v]} "
      f"appear nowhere in the package")
defect = (r is not None and fa is not None and fit in absent and fit in rested
          and any(n == "kinetic fit" and s.get("id") == fit for n, _, s in names)
          and not all(held_params.values()))
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
exit 0
