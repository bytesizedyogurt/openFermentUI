#!/bin/bash
# /rag with OPENFERMENT_RAG_KEY unset (start the service with OPENFERMENT_RAG_KEY= in its environment):
# which routes answer with no key, and what the corpus manifest says about this mount.
# Usage: bash rag_probe.sh http://127.0.0.1:8903 q1
O="$1"; P="$2"
for path in /rag/v1/status /rag/v1/documents /rag/health /rag/v1/corpus-manifest /rag/docs /rag/openapi.json; do
  printf '%-26s ' "GET $path"
  curl -s --noproxy '*' -o /dev/null -H "X-OpenFerment-Project: $P" -w '%{http_code}\n' "$O$path"
done
printf '%-26s ' "GET /rag/"; curl -s --noproxy '*' -o /dev/null -w '%{http_code} -> %{redirect_url}\n' "$O/rag/"
echo "-- the manifest, with no key:"
curl -s --noproxy '*' -H "X-OpenFerment-Project: $P" "$O/rag/v1/corpus-manifest" | python3 -c '
import json, sys
m = json.load(sys.stdin)
print("stats", m["stats"]); print("embedding", m["embedding"]); print("endpoints", m["endpoints"]); print("features", m["features"])'
echo "-- what those endpoints answer:"
for path in /v1/status /mcp /mcp/ /rag/mcp/; do
  printf '%-12s ' "$path"; curl -s --noproxy '*' -o /dev/null -w '%{http_code}\n' "$O$path"
done
