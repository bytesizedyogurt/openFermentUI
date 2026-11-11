#!/usr/bin/env bash
# H8-08 (with H14-03): with no key, POST /api/literature/answer ends in an `error` event whose words are
# "ModelUnavailable: generation failed (see server logs)"; the words naming the missing key
# ("ANTHROPIC_API_KEY is not set ...") stay in the service log, and BioRepo Search shows the generic words.
# The head's own service on a fresh database, port 9510, keyless: llm.py refuses before any request leaves.
# usage, from the repository root: bash bughunt/repro/H8-08/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h8_08_svc
PORT=9510
P=h808
HERE=$BH_ROOT/bughunt/repro/H8-08
T=$BH_WORK/H8-08; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$T"; }
trap cleanup EXIT
c() { curl -s --noproxy '*' "$@"; }
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
Q='What does corn stover pretreatment release?'

echo "EXPECTED: with no key, POST /api/literature/answer ends in an \`error\` event that says there is no key"
echo "EXPECTED: (core/openferment_core/api.py:2149, docs/api/openapi.json:23239: \"with no key the stream says so in an"
echo "EXPECTED: \`error\`\"), in the service's own words as the extract route gives them: \"ANTHROPIC_API_KEY is not set ...\";"
echo "EXPECTED: BioRepo Search shows those words (src/lib/literature.ts:116: \"the service's words, a missing key among them\")"

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
HEALTH=$(c "$O/api/health")
HASKEY=$(echo "$HEALTH" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("hasKey"))')
echo "OBSERVED: GET /api/health hasKey $HASKEY"
if [ "$HASKEY" != "False" ]; then
  echo "OBSERVED: the service holds a key; the reproduction stops before any model call"; echo "RESULT: NO-DEFECT"; exit 0
fi
bh_project "$O" "$P" >/dev/null
DOC=$(c -X POST "$O/api/intake/paste" "${H[@]}" \
  -d '{"title":"H8-08 note","text":"Corn stover pretreatment releases xylose from the hemicellulose.","by":"h8-08 repro"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("documentId",""))')
HITS=0
for i in $(seq 1 30); do
  HITS=$(c "$O/api/literature/search?q=corn%20stover%20pretreatment" "${H[@]}" \
    | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("hits",[])))' 2>/dev/null || echo 0)
  [ "${HITS:-0}" -gt 0 ] && break; sleep 1
done
echo "OBSERVED: pasted document $DOC; search (no model) finds $HITS passage(s)"

# The stream, as the route sends it.
c -N -X POST "$O/api/literature/answer" "${H[@]}" -d "{\"question\":\"$Q\"}" --max-time 120 > "$T/stream.txt"
KINDS=$(grep '^event:' "$T/stream.txt" | sed 's/^event: *//' | tr '\n' ' ')
ERR=$(grep -A1 '^event: error' "$T/stream.txt" | grep '^data:' | tail -1 | sed 's/^data: *//')
echo "OBSERVED: the stream's events, in order: $KINDS"
echo "OBSERVED: the stream's error: $ERR"
sleep 1
LOGLINE=$(grep -h 'answer_generation_failed' "$BH_WORK/svc-$PORT.log" | tail -1 | cut -c1-260)
echo "OBSERVED: the service log: $LOGLINE"

# The same service's own words for the same missing key, on the extract route.
EX=$(c -X POST "$O/api/intake/$DOC/extract" "${H[@]}" -w '\n%{http_code}')
echo "OBSERVED: POST /api/intake/{id}/extract answers HTTP $(echo "$EX" | tail -1): $(echo "$EX" | head -1 | cut -c1-200)"

# The screen: BioRepo Search's Answer with citations.
SCREEN=$(cd "$HERE" && timeout 150 node screen.mjs "$O" "$P" "$Q" "$HERE/answer-nokey.png" 2>&1 | grep -E '^SCREEN' | tail -1)
echo "OBSERVED: BioRepo Search shows: ${SCREEN#SCREEN: }"

defect=0
if [ -n "$ERR" ] && echo "$ERR" | grep -q 'generation failed (see server logs)' \
   && ! echo "$ERR" | grep -qi 'key' && echo "$LOGLINE" | grep -q 'ANTHROPIC_API_KEY is not set'; then
  defect=1
fi
if [ $defect = 1 ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
