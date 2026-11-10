#!/usr/bin/env bash
# Each misbehaving thing of the probe engine asked at POST /api/engines/probe/run, then asked again,
# with the runs rows and the artifacts it left. usage: probe_things.sh ORIGIN PROJECT DB THING...
O=$1; P=$2; DB=$3; shift 3
for th in "$@"; do
  for k in 1 2; do
    printf '%s ask %s: ' "$th" "$k"
    curl -s --noproxy '*' -m 90 -X POST "$O/api/engines/probe/run" -H 'content-type: application/json' \
      -H "X-OpenFerment-Project: $P" -d "{\"thing\":\"$th\",\"by\":\"H1\"}" -o /tmp/h1probe.out -w '%{http_code} %{size_download}B ' ; head -c 400 /tmp/h1probe.out; echo
  done
  psql "postgresql://openferment:openferment@127.0.0.1:5432/$DB" -AtXc \
    "select 'runs row', id, status, coalesce(body->>'sffRefused',''), left(coalesce(body->>'refused',''),80) from openferment.runs where project_id='$P' and body->>'plant'='$th' and engine='probe'"
  psql "postgresql://openferment:openferment@127.0.0.1:5432/$DB" -AtXc \
    "select 'artifact', id, length(body::text) from openferment.artifacts where project_id='$P' and body->'output'->>'thing'='$th' and tool='engine.probe'"
done
