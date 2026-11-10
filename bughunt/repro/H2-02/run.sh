#!/usr/bin/env bash
# H2-02: a Proforma scenario run of ethanol_glucose_v0 (the biosteam engine states its precision as rtol 0,
# atol 0) replays identically in the worker that computed it and with last-digit differences once the
# service restarts over the same database.
#   bash bughunt/repro/H2-02/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h2_02_rep
PORT=""
for p in $(seq 9020 9029); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "no free port in 9020-9029"; echo "RESULT: NO-DEFECT"; exit 0; }
O=http://127.0.0.1:$PORT; P=h2-02
W=$(mktemp -d "$BH_WORK/H2-02-run.XXXXXX")
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$W" "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"; }
trap cleanup EXIT

api() {  # api METHOD PATH [JSON | @file]: the body on stdout
  local m="$1" path="$2" body="${3:-}"
  local args=(-s --noproxy '*' -X "$m" -H "X-OpenFerment-Project: $P" "$O$path")
  [ -n "$body" ] && args+=(-H 'content-type: application/json' --data-binary "$body")
  curl "${args[@]}"
}

bh_db_fresh "$DB" || { echo "bh_db_fresh failed"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $(BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PORT")  database: $DB (fresh)"
bh_project "$O" "$P" >/dev/null

# An unsaved scenario of ethanol_glucose_v0, every input a person's placeholder, 20 samples.
python3 -I - "$W" <<'PY'
import json, sys
o = {"kind": "person-assumption", "by": "Repro H2-02", "at": "2026-11-10", "note": "a placeholder the repro sets"}
vals = {"feed_glucose_conc": (100, "g L-1"), "titre": (50, "g L-1"), "yield": (0.45, "g g-1"),
        "productivity": (2, "g L-1 h-1"), "plant_scale": (50000, "t yr-1"), "glucose_price": (0.3, "USD kg-1")}
inputs = [{"name": k, "quantity": {"value": v, "unit": u, "origin": o}} for k, (v, u) in vals.items()]
json.dump({"scenarioId": "ethanol_glucose_v0", "flowsheet": "ethanol_glucose_v0", "inputs": inputs,
           "by": "Repro H2-02", "samples": 20}, open(sys.argv[1] + "/req.json", "w"))
PY
if [ "${LIB:-0}" = 1 ]; then api POST /api/library/cornstover/run '{"by":"Repro H2-02"}' > "$W/lib.json"; echo "library run first (LIB=1)"; fi
api POST /api/proforma/run "@$W/req.json" > "$W/run.json"
AID=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['artifactId'])" "$W/run.json" 2>/dev/null)
[ -n "$AID" ] || { echo "the Proforma run did not answer an artifact:"; head -c 600 "$W/run.json"; echo; echo "RESULT: NO-DEFECT"; exit 0; }
echo "Proforma run kept: artifact $AID (tool proforma.run)"
api POST "/api/biorepo/artifacts/$AID/replay" '{}' > "$W/replay1.json"
api GET /api/engines > "$W/engines.json"

bh_svc_stop "$PORT"
echo "service restarted: $(BH_KEEP_DB=1 BH_FIXTURES=1 bh_svc_start "$DB" "$PORT")  (same database)"
api POST "/api/biorepo/artifacts/$AID/replay" '{}' > "$W/replay2.json"

python3 -I - "$W" <<'PY' || echo "RESULT: NO-DEFECT (the steps did not complete; see the lines above)"
import json, sys
w = sys.argv[1]
eng = json.load(open(f"{w}/engines.json"))
thing = next(t for e in eng if e["name"] == "biosteam" for t in e["things"] if t["id"] == "ethanol_glucose_v0")
prec = thing["precision"]
print(f"GET /api/engines: biosteam thing ethanol_glucose_v0 (kind {thing['kind']}) precision {prec}")
r1, r2 = json.load(open(f"{w}/replay1.json")), json.load(open(f"{w}/replay2.json"))
def say(tag, r):
    print(f"{tag}: identical {r['identical']}, withinTolerance {r['withinTolerance']}, "
          f"tolerance {r.get('tolerance')}, {len(r['differences'])} differences")
    for d in r["differences"]:
        s, p = d["stored"], d["replayed"]
        rel = abs(p - s) / abs(s) if isinstance(s, (int, float)) and isinstance(p, (int, float)) and s else None
        print(f"    {d['path']}: stored {s!r} replayed {p!r}" + (f"  (relative {rel:.1e})" if rel is not None else ""))
say("replay in the worker that ran it", r1)
say("replay after the service restarts", r2)
print(f"EXPECTED: the engine states rtol {prec['rtol']}, atol {prec['atol']} for ethanol_glucose_v0 and the docs say its "
      "replay holds every output identically, so each replay answers identical true (withinTolerance true)")
print(f"OBSERVED: same worker identical {r1['identical']}; after a restart identical {r2['identical']}, withinTolerance "
      f"{r2['withinTolerance']}, {len(r2['differences'])} differences at paths "
      f"{', '.join(d['path'] for d in r2['differences'])}")
defect = (prec == {"rtol": 0.0, "atol": 0.0} and not r2["identical"] and not r2["withinTolerance"]
          and all(isinstance(d["stored"], (int, float)) for d in r2["differences"]))
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
exit 0
