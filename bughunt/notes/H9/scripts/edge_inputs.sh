#!/usr/bin/env bash
# H9: three inputs at the REST tool door that answer with no words: a 400-digit integer in
# a quantity's value, a lone surrogate escape in a string, a NUL in an id.
#   edge_inputs.sh ORIGIN PROJECT
O="$1"; P="$2"
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
BIG=$(python3 -c "print('9'*400)")
echo "## study_scenario, a 400-digit integer as a quantity's value"
curl -s --noproxy '*' -w ' [%{http_code}]\n' -X POST "$O/api/tools/study_scenario?by=Edge%20Tester" "${H[@]}" \
  -d "{\"title\":\"t\",\"plant\":\"x\",\"values\":[{\"key\":\"k\",\"quantity\":{\"value\":$BIG,\"unit\":\"g\"}}]}"
echo "## search_records, a lone surrogate escape in the query"
curl -s --noproxy '*' -w ' [%{http_code}]\n' -X POST "$O/api/tools/search_records" "${H[@]}" \
  -d '{"query":"a\ud800b","field":"x","organism":"x","limit":5}'
echo "## engine_report, a NUL in the run id"
curl -s --noproxy '*' -w ' [%{http_code}]\n' -X POST "$O/api/tools/engine_report" "${H[@]}" \
  -d '{"run":"a\u0000b"}' | cut -c1-500
