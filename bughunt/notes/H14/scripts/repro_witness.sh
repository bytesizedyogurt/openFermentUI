#!/usr/bin/env bash
# H14: Witness shows PRECISION 0.0% with no gold value, beside "No gold annotations yet ... Precision and recall are
# undefined without a gold set", once a reviewer rejects one candidate and accepts others. A copy of the development
# database (read with pg_dump alone) on port 8945: accept two candidates, reject one, open Witness.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
PORT=8945; DB=bh_h14_wit; P=ethanol
psql "$BH_SERVER/postgres" -qXc "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE)" && psql "$BH_SERVER/postgres" -qXc "CREATE DATABASE \"$DB\""
pg_dump -Fc -d "$BH_SERVER/openferment_dev" | pg_restore --no-owner -d "$BH_SERVER/$DB" 2>/dev/null
O=$(BH_KEEP_DB=1 bh_svc_start $DB $PORT) || exit 1
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
c() { curl -s --noproxy '*' "$@"; }
IDS=$(c "$O/api/biorepo/overlay" "${H[@]}" | python3 -c '
import json,sys
d=json.load(sys.stdin); recs=d["records"]; recs = list(recs.values()) if isinstance(recs, dict) else recs
held={r["id"] for r in recs}
print(" ".join([c["id"] for c in d["candidates"] if c["id"] not in held][:3]))')
set -- $IDS
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
for id in "$1" "$2"; do c -X POST "$O/api/biorepo/decisions" "${H[@]}" -d "{\"recordId\":\"$id\",\"status\":\"verified\",\"provenance\":\"verified\",\"reviewer\":\"Hunt Fourteen\",\"at\":\"$NOW\"}" >/dev/null; done
c -X POST "$O/api/biorepo/decisions" "${H[@]}" -d "{\"recordId\":\"$3\",\"status\":\"rejected\",\"provenance\":\"unverified\",\"rejectReason\":\"wrong value\",\"reviewer\":\"Hunt Fourteen\",\"at\":\"$NOW\"}" >/dev/null
echo "== GET /api/witness/runs"; c "$O/api/witness/runs" "${H[@]}" | python3 -c 'import json,sys; r=json.load(sys.stdin)[0]; print("results", len(r["results"]), "falsePositives", len(r["falsePositives"]))'
echo "== the Witness screen"
(cd "$BH_ROOT/bughunt/notes/H14/scripts" && node read_screen.mjs "$O" "$P" /biorepo/witness "No gold annotations|Precision and recall are undefined|^PRECISION|^tp " scr-witness-nogold)
bh_svc_stop $PORT; bh_db_drop $DB
