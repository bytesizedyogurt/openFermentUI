#!/usr/bin/env bash
# Rows 17, 36, 37: each decision writes the record as the next version of its openferment.records row and an undo
# the candidate as extracted; a decision's provenance is computed from the decision, whatever label it sends; the
# evidence pool (biorepo_read, search_records) applies the standing decisions.
O=${1:-http://127.0.0.1:8950}
DB=${2:-postgresql://openferment:openferment@127.0.0.1:5432/bh_p_main}
C() { curl -s --noproxy "*" "$@"; }
J='content-type: application/json'
R2=cl1-dce0b47561a14628b022400f6f75ecef-fbf9a747
AT=2026-11-10T23:00:00Z
for prov in gold assumed unverified; do
  echo "== a verified decision on $R2 sending provenance '$prov' and no gold value"
  C -X POST "$O/api/biorepo/decisions" -H 'X-OpenFerment-Project: pa' -H "$J" \
    -d '{"status":"verified","provenance":"'$prov'","reviewer":"Ada Moreno","recordId":"'$R2'","at":"'$AT'"}' | head -c 250; echo
done
echo "== records rows of $R2 (version, status, provenance)"
psql "$DB" -XAtc "select version, status, provenance, created_by from openferment.records where id='$R2' order by version"
echo "== biorepo_read kind record, before the undo"
C -X POST "$O/api/tools/biorepo_read" -H 'X-OpenFerment-Project: pa' -H "$J" -d '{"ids":[],"words":"","kind":"record","state":"","limit":20}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print([(r["id"][-8:], r.get("provenance"), r.get("state")) for r in d["rows"]])'
echo "== the undo: status unverified, nothing typed"
C -X POST "$O/api/biorepo/decisions" -H 'X-OpenFerment-Project: pa' -H "$J" \
  -d '{"status":"unverified","provenance":"unverified","reviewer":"Ada Moreno","recordId":"'$R2'","at":"2026-11-10T23:01:00Z"}' | head -c 250; echo
psql "$DB" -XAtc "select version, status, provenance, left(body::text,120) from openferment.records where id='$R2' order by version"
echo "== biorepo_read kind record and candidate, after the undo"
for k in record candidate; do C -X POST "$O/api/tools/biorepo_read" -H 'X-OpenFerment-Project: pa' -H "$J" -d '{"ids":[],"words":"","kind":"'$k'","state":"","limit":20}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print("'$k'", [(r["id"][-8:], r.get("provenance"), r.get("state")) for r in d["rows"]])'; done
echo "== search_records kinds"
C -X POST "$O/api/tools/search_records" -H 'X-OpenFerment-Project: pa' -H "$J" -d '{"query":"","field":null,"organism":null,"limit":10}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("error"), [(h["recordId"][-8:], h["kind"], h.get("provenance")) for h in d["summary"]["records"]])'
