#!/usr/bin/env bash
# H4-07: ethanol_glucose_v0 takes a titre at harvest that its beer never reaches (candidate, S3).
# Run from the repository root: bash bughunt/repro/H4-07/run.sh
# A fresh database bh_r_h4_07_run, a keyless service on a free port among 127.0.0.1:10010-10019, one project, one
# scenario run of ethanol_glucose_v0 through POST /api/engines/biosteam/run with feed 150 g/L, titre 70 g/L, yield
# 0.45 g/g and productivity 2 g/L/h (titre above feed x yield = 67.5), then the shelf and the parameter panel's
# specs the service serves for the same flowsheet. judge.py sets the run's read-back beside the titre input's own
# declared description. Then the service stopped, the database dropped, the data copy and run files removed.
# Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H4-07
DB=bh_r_h4_07_run
PJ=h407
PY="$BH_ROOT/core/.venv/bin/python"
OUT=$BH_WORK/H4-07/out
PORT=""
for p in 10010 10011 10012 10013 10014 10015 10016 10017 10018 10019; do
  [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 10010-10019"; echo "OBSERVED: none free"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$OUT"; rmdir "$BH_WORK/H4-07" 2>/dev/null
}
trap cleanup EXIT
rm -rf "$OUT"; mkdir -p "$OUT"
ORIGIN=$(bh_svc_start "$DB" "$PORT") || {
  echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless), tree at $(git -C "$BH_ROOT" rev-parse --short HEAD);" \
  "files of core, src, scripts and examples differing from 2047f5a: $(git -C "$BH_ROOT" diff --name-only 2047f5a -- core src scripts examples | wc -l)"
bh_project "$ORIGIN" "$PJ" "H4-07" >/dev/null
q() { printf '{"name":"%s","quantity":{"value":%s,"unit":"%s","origin":{"kind":"person-assumption","by":"h407","at":"2026-11-10"}}}' "$1" "$2" "$3"; }
BODY=$(printf '{"thing":"ethanol_glucose_v0","by":"h407","inputs":[%s,%s,%s,%s,%s,%s]}' \
  "$(q feed_glucose_conc 150.0 'g L-1')" "$(q titre 70.0 'g L-1')" "$(q yield 0.45 'g g-1')" \
  "$(q productivity 2.0 'g L-1 h-1')" "$(q plant_scale 100000.0 't yr-1')" "$(q glucose_price 0.4 'USD kg-1')")
H=(-H 'content-type: application/json' -H "X-OpenFerment-Project: $PJ")
curl -s --noproxy '*' --max-time 900 -X POST "$ORIGIN/api/engines/biosteam/run" "${H[@]}" -d "$BODY" > "$OUT/run.json"
curl -s --noproxy '*' --max-time 60 "$ORIGIN/api/proforma/shelf" "${H[@]}" > "$OUT/shelf.json"
curl -s --noproxy '*' --max-time 60 "$ORIGIN/api/params/proforma:h407new?flowsheet=ethanol_glucose_v0" "${H[@]}" > "$OUT/params.json"
bh_env "$PY" -I "$HERE/judge.py" "$OUT/run.json" "$OUT/shelf.json" "$OUT/params.json" "$BH_ROOT" \
  || { echo "OBSERVED: judge.py failed"; echo "RESULT: NO-DEFECT"; }
exit 0
