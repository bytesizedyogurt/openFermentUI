#!/usr/bin/env bash
# A probe run in flight (thing slow, 5 s), its worker killed with SIGKILL after 1.5 s; then the answer,
# the rows the run left, the job events, and the same request asked again.
# usage: kill_midrun.sh ORIGIN PROJECT DB SECONDS
O=$1; P=$2; DB=$3; S=${4:-5}
body="{\"thing\":\"slow\",\"by\":\"H1\",\"inputs\":[{\"name\":\"seconds\",\"quantity\":{\"value\":$S,\"unit\":\"s\",\"origin\":{\"kind\":\"person-assumption\",\"by\":\"H1\",\"at\":\"2026-11-10\"}}}]}"
curl -s --noproxy '*' -m 60 -X POST "$O/api/engines/probe/run" -H 'content-type: application/json' -H "X-OpenFerment-Project: $P" -d "$body" -w ' [%{http_code}]\n' > /tmp/h1kill.out &
sleep 1.5
pids=$(pgrep -f 'h1probe.worker$' | tr '\n' ' '); echo "killing every probe worker: $pids"; kill -KILL $pids
wait
echo "answer: $(head -c 600 /tmp/h1kill.out)"
psql "postgresql://openferment:openferment@127.0.0.1:5432/$DB" -AtXc "select 'rows for slow '||count(*) from openferment.runs where project_id='$P' and engine='probe' and body->>'plant'='slow'"
psql "postgresql://openferment:openferment@127.0.0.1:5432/$DB" -AtXc "select 'artifacts for slow '||count(*) from openferment.artifacts where project_id='$P' and tool='engine.probe' and body->'output'->>'thing'='slow'"
echo "asked again:"; curl -s --noproxy '*' -m 60 -X POST "$O/api/engines/probe/run" -H 'content-type: application/json' -H "X-OpenFerment-Project: $P" -d "$body" -w ' [%{http_code}]\n' | head -c 300; echo
psql "postgresql://openferment:openferment@127.0.0.1:5432/$DB" -AtXc "select 'rows for slow '||count(*)||' status '||string_agg(status, ',') from openferment.runs where project_id='$P' and engine='probe' and body->>'plant'='slow'"
