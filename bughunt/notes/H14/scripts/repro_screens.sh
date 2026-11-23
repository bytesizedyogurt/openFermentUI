#!/usr/bin/env bash
# H14: three screen findings from one fresh database (bh_h14_scr, port 8944), keyless.
#  1. POST /api/literature/answer with no key: the stream's error says "ModelUnavailable: generation failed (see
#     server logs)" while the service log holds "ANTHROPIC_API_KEY is not set" (api.py:2149 promises the stream says so).
#  2. (Witness: repro_witness.sh, on a copy of the development database, since a hand-written candidate is never
#     scored and an extraction needs a model.)
#  3. Home with one gold record: the GOLD SET tile counts 1 and the BioRepo destination says "gold set not yet
#     annotated"; the Postdoc destination says "live" while /api/health says hasKey false.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
PORT=8944; DB=bh_h14_scr; P=screens-check; O=$(bh_svc_start $DB $PORT) || exit 1
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
c() { curl -s --noproxy '*' "$@"; }
bh_project "$O" "$P" >/dev/null
DOCID=$(c -X POST "$O/api/intake/paste" "${H[@]}" -d '{"title":"Bench note","text":"The strain reached an ethanol titre of 41.7 g/L after 48 h on glucose. A second batch reached 38.2 g/L.","by":"Hunt Fourteen","url":"","licenceClass":"unknown","licence":"","reason":"screens check"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["documentId"])')
for i in $(seq 1 30); do
  SEC=$(c "$O/api/biorepo/overlay" "${H[@]}" | python3 -c 'import json,sys; ps=list(json.load(sys.stdin)["papers"].values()); print(ps[0]["sections"][0]["id"] if ps and ps[0].get("sections") else "")')
  [ -n "$SEC" ] && break; sleep 1
done
echo "== 1. the literature answer with no key"
c -N -X POST "$O/api/literature/answer" "${H[@]}" -d '{"question":"What ethanol titre did the strain reach?"}' --max-time 60 | grep -A1 '^event: error'
grep -h "answer_generation_failed" "$BH_WORK/svc-$PORT.log" | tail -1 | cut -c1-220
echo "== two candidates by hand (no model): one rejected, one flagged gold"
mk() { c -X POST "$O/api/tools/biorepo_write?by=Hunt%20Fourteen" "${H[@]}" -d "{\"action\":\"candidate\",\"target\":\"\",\"fields\":{\"paperId\":\"$DOCID\",\"sectionId\":\"$SEC\",\"field\":\"ethanol_titre\",\"value\":\"$1\",\"unit\":\"g/L\",\"quote\":\"$2\"},\"note\":\"screens check\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["summary"]["candidateId"])'; }
C1=$(mk 41.7 "The strain reached an ethanol titre of 41.7 g/L after 48 h on glucose.")
C2=$(mk 38.2 "A second batch reached 38.2 g/L.")
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
c -X POST "$O/api/biorepo/decisions" "${H[@]}" -d "{\"recordId\":\"$C2\",\"status\":\"rejected\",\"provenance\":\"unverified\",\"rejectReason\":\"wrong value\",\"reviewer\":\"Hunt Fourteen\",\"at\":\"$NOW\"}" | cut -c1-160; echo
c -X POST "$O/api/biorepo/decisions" "${H[@]}" -d "{\"recordId\":\"$C1\",\"status\":\"verified\",\"provenance\":\"gold\",\"gold\":{\"value\":41.7,\"unit\":\"g/L\"},\"reviewer\":\"Hunt Fourteen\",\"at\":\"$NOW\"}" | cut -c1-160; echo
echo "== 3. Home, one gold record"
c "$O/api/health"; echo
(cd "$BH_ROOT/bughunt/notes/H14/scripts" && node read_screen.mjs "$O" "$P" HOME "GOLD SET|gold set not yet|live through" scr-home-gold)
bh_svc_stop $PORT; bh_db_drop $DB
