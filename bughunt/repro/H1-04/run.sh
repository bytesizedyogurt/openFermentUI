#!/usr/bin/env bash
# H1-04: a scenario flowsheet run (ethanol_glucose_v0) with six fixed values keeps a base price its own
# samples contradict, and its replay in the same service differs where the stated precision is rtol 0, atol 0.
# Usage, from the repository root: bash bughunt/repro/H1-04/run.sh
# The head's own service and venv on a fresh test database, keyless, a port in 9000-9009; nothing under core/,
# src/, scripts/ or examples/ is touched. Exits 0 whatever it finds; its last line is RESULT: DEFECT or NO-DEFECT.
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h1_04_svc
OUT=$(mktemp -d "$BH_WORK/H1-04.XXXXXX")
PORT=""
cleanup() {
  [ -n "$PORT" ] && bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$OUT"
}
trap cleanup EXIT

verdict() { echo "RESULT: $1"; exit 0; }

# start_ours: the head's service over $DB on a port of 9000-9009 nothing listens on; PORT and O are set only
# when the listener is ours (its environment names our database), so cleanup never stops another's service.
start_ours() {
  local p q o pid; PORT=""; O=""
  for q in $(seq 9000 9009); do [ -z "$(bh_port_pid "$q")" ] && { p=$q; break; }; done
  [ -n "$p" ] || { echo "no free port in 9000-9009"; return 1; }
  o=$(bh_svc_start "$DB" "$p") || { echo "the service did not start on $p"; return 1; }
  pid=$(bh_port_pid "$p")
  tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep -q "^OPENFERMENT_DATABASE_URL=.*/$DB\$" \
    || { echo "port $p is served by another process"; return 1; }
  PORT=$p; O=$o
}
rm -rf "$BH_WORK/data-$DB"
start_ours || verdict NO-DEFECT
echo "service $O over fresh database $DB"
bh_project "$O" h1r04 >/dev/null
H=(-H 'content-type: application/json' -H 'X-OpenFerment-Project: h1r04')

# 1. The precision the engine states for the thing, as served.
curl -s --noproxy '*' "$O/api/engines" "${H[@]}" > "$OUT/engines.json"
python3 - "$OUT/engines.json" <<'PY'
import json, sys
for e in json.load(open(sys.argv[1])):
    for t in e.get("things", []):
        if e["name"] == "biosteam" and t["id"] == "ethanol_glucose_v0":
            print("stated precision of biosteam/ethanol_glucose_v0 (GET /api/engines):", t["precision"])
PY

# 2. One run, every input fixed (no low or high, so each of the 500 samples takes the base case's inputs).
python3 - > "$OUT/run-body.json" <<'PY'
import json
o = {"kind": "person-assumption", "by": "H1-04 repro", "at": "2026-11-10"}
six = [("feed_glucose_conc", 100, "g L-1"), ("titre", 50, "g L-1"), ("yield", 0.4, "g g-1"),
       ("productivity", 1, "g L-1 h-1"), ("plant_scale", 1000, "t yr-1"), ("glucose_price", 0.5, "USD kg-1")]
print(json.dumps({"thing": "ethanol_glucose_v0", "by": "H1-04 repro",
                  "inputs": [{"name": n, "quantity": {"value": v, "unit": u, "origin": o}} for n, v, u in six]}))
PY
t0=$(date +%s)
code=$(curl -s --noproxy '*' -m 1500 -o "$OUT/run.json" -w '%{http_code}' -X POST "$O/api/engines/biosteam/run" \
       "${H[@]}" --data @"$OUT/run-body.json")
echo "POST /api/engines/biosteam/run -> HTTP $code in $(( $(date +%s) - t0 )) s"
[ "$code" = 200 ] || { head -c 600 "$OUT/run.json"; echo; verdict NO-DEFECT; }
A=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['run']['artifactId'])" "$OUT/run.json")

# 3. Replay the kept artifact in the same service (its Proforma worker already holds the built plant).
t0=$(date +%s)
code=$(curl -s --noproxy '*' -m 1500 -o "$OUT/replay.json" -w '%{http_code}' -X POST \
       "$O/api/biorepo/artifacts/$A/replay" -H 'X-OpenFerment-Project: h1r04')
echo "POST /api/biorepo/artifacts/$A/replay -> HTTP $code in $(( $(date +%s) - t0 )) s"
[ "$code" = 200 ] || { head -c 600 "$OUT/replay.json"; echo; verdict NO-DEFECT; }

# 4. The same artifact replayed once more after a restart, so the replay's case is the first a fresh
#    Proforma worker evaluates (as the run's base case was). Reported beside the verdict; step 3 decides it.
bh_svc_stop "$PORT"; PORT=""
if BH_KEEP_DB=1 start_ours; then
  t0=$(date +%s)
  code=$(curl -s --noproxy '*' -m 1500 -o "$OUT/replay-fresh.json" -w '%{http_code}' -X POST \
         "$O/api/biorepo/artifacts/$A/replay" -H 'X-OpenFerment-Project: h1r04')
  echo "after a restart, POST /api/biorepo/artifacts/$A/replay -> HTTP $code in $(( $(date +%s) - t0 )) s"
fi
[ -s "$OUT/replay-fresh.json" ] || echo '{}' > "$OUT/replay-fresh.json"

python3 - "$OUT/run.json" "$OUT/replay.json" "$OUT/replay-fresh.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); rp = json.load(open(sys.argv[2]))
r, o = d["run"], d["artifact"]["output"]
q = o["quantiles"]
base = o["basePrice"]
print("run", r["id"], r["status"], "| artifact", r["artifactId"], "| samples", o["samples"], "feasible", o["feasible"])
print("specs: every input fixed:", sorted(o["base"].items()))
print("price.solvedPrice (basePrice):", base, "USD/kg")
print("quantiles of the 500 samples of the same inputs:", q)
diffs = rp["differences"]
bp = [(x["stored"], x["replayed"]) for x in diffs if x["path"] == "basePrice"]
print("replay: identical", rp["identical"], "| withinTolerance", rp["withinTolerance"], "| tolerance", rp.get("tolerance"),
      "| differences", len(diffs))
print("replay basePrice stored -> replayed:", bp[0] if bp else "(same)")
print("first differences:", [(x["path"], x["stored"], x["replayed"]) for x in diffs[:4]])
fr = json.load(open(sys.argv[3]))
if "identical" in fr:
    fd = fr["differences"]
    fbp = [(x["stored"], x["replayed"]) for x in fd if x["path"] == "basePrice"]
    print("replay in a freshly started worker: identical", fr["identical"], "| withinTolerance", fr["withinTolerance"],
          "| differences", len(fd), "| basePrice", "stored -> replayed " + str(fbp[0]) if fbp else "the same",
          "|", [(x["path"], x["stored"], x["replayed"]) for x in fd[:3]])
else:
    print("replay in a freshly started worker: not run")
spread = [v for v in q.values() if v != base]
print("EXPECTED: every sample of the same six fixed inputs prices as the base case does (each quantile equal to "
      "basePrice), and the replay is identical (precision rtol 0, atol 0)")
print(f"OBSERVED: basePrice {base}; {len(spread)} of {len(q)} quantiles differ from it ({q.get('p50')}); replay "
      f"identical {rp['identical']}, withinTolerance {rp['withinTolerance']}, {len(diffs)} differences"
      + (f", basePrice {bp[0][0]} -> {bp[0][1]}" if bp else ""))
defect = bool(spread) or not rp["identical"] or not rp["withinTolerance"]
open(sys.argv[2] + ".verdict", "w").write("DEFECT" if defect else "NO-DEFECT")
PY
verdict "$(cat "$OUT/replay.json.verdict" 2>/dev/null || echo NO-DEFECT)"
