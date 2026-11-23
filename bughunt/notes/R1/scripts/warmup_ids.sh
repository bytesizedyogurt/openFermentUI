#!/usr/bin/env bash
# R1: the three warm-up runs docs/reports/live-questions-2026-11.md names (5 November, alpha 2.2 stage F), run again on a
# fresh service at the head, keyless, and their ids printed beside the report's.
# Usage: bash warmup_ids.sh ORIGIN PROJECT
O="$1"; P="$2"; H="X-OpenFerment-Project: $P"
run() { curl -s --noproxy '*' -X POST "$O/api/engines/biosteam/run" -H "$H" -H 'content-type: application/json' --max-time 600 -d "$1"; }
for spec in 'cornstover||bfda026530692adc' 'cellulosic_ethanol_v0|dilute acid, IB|e7efa2505b4633de' 'cellulosic_ethanol_v0|hot water, IB|784c94d9bd67d20e'; do
  IFS='|' read -r thing conf want <<<"$spec"
  if [ -n "$conf" ]; then body="{\"thing\":\"$thing\",\"configuration\":\"$conf\",\"inputs\":[],\"by\":\"R1\"}"; else body="{\"thing\":\"$thing\",\"inputs\":[],\"by\":\"R1\"}"; fi
  t0=$(date +%s.%N); out=$(run "$body"); t1=$(date +%s.%N)
  got=$(printf '%s' "$out" | python3 -c "import json,sys
try:
  d=json.load(sys.stdin); r=d.get('run',d); print(r.get('id') or r.get('artifactId') or d.get('id'), r.get('status'), (r.get('artifact') or {}).get('provenance') if isinstance(r.get('artifact'),dict) else '')
except Exception as e: print('unparsed', e)")
  echo "$thing [$conf]: got $got, report says $want ($(python3 -c "print(round($t1-$t0,1))") s)"
done
