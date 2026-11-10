#!/usr/bin/env bash
# Row 36 (b9ba0d2): a decision's provenance is computed from the decision, whatever label it carries (ADR-006's
# note of 8.5: "gold for a verified decision with a gold value, verified for any other verified one ... whatever
# label the request carried"). Two verified decisions, neither with a gold value, differing only in the label sent.
O=${1:-http://127.0.0.1:8950}
DB=${2:-postgresql://openferment:openferment@127.0.0.1:5432/bh_p_main}
C() { curl -s --noproxy "*" "$@"; }
J='content-type: application/json'
R=${3:-cl1-459ebc61efd946babec4d8065a1227ef-da35d515}
for prov in verified gold; do
  echo "== POST /api/biorepo/check: verified, label '$prov', gold null"
  C -X POST "$O/api/biorepo/check" -H 'X-OpenFerment-Project: pa' -H "$J" \
    -d '{"status":"verified","provenance":"'$prov'","gold":null,"reviewer":"Ada Moreno","recordId":"'$R'","at":"2026-11-10T23:10:00Z"}'; echo
done
echo "== POST /api/biorepo/decisions: verified, label 'gold', gold null"
C -X POST "$O/api/biorepo/decisions" -H 'X-OpenFerment-Project: pa' -H "$J" \
  -d '{"status":"verified","provenance":"gold","gold":null,"reviewer":"Ada Moreno","recordId":"'$R'","at":"2026-11-10T23:10:00Z"}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print({k:d.get(k) for k in ("status","provenance","gold")})'
echo "== the record row"; psql "$DB" -XAtc "select version, status, provenance from openferment.records where id='$R' order by version desc limit 1"
echo "== biorepo_read (the evidence pool Postdoc reads)"
C -X POST "$O/api/tools/biorepo_read" -H 'X-OpenFerment-Project: pa' -H "$J" -d '{"ids":["'$R'"],"words":"","kind":"","state":"","limit":5}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print([(r["id"][-8:], r.get("kind"), r.get("provenance")) for r in d["rows"]])'
echo "== the overlay the browser reads: the decision it applies (provenanceOf reads r.gold, null here, so verified)"
C "$O/api/biorepo/overlay" -H 'X-OpenFerment-Project: pa' | python3 -c 'import json,sys; d=json.load(sys.stdin); dec=d.get("decisions",{}).get("'$R'") or {}; print({k:dec.get(k) for k in ("status","provenance","gold")}, list(d.keys()))'
