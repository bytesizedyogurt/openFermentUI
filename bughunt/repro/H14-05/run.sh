#!/usr/bin/env bash
# H14-05: Home's BioRepo destination line says "gold set not yet annotated" beside a Gold set tile that counts one.
# A fresh database, the service keyless on 127.0.0.1 (a port in 9780-9789), one pasted document, one candidate
# written by hand through the tool door (no model), the candidate promoted to the gold set through
# POST /api/biorepo/decisions, then Home of the built app read in headless Chromium.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE="$BH_ROOT/bughunt/repro/H14-05"
DB=bh_r_h14_05_home; P=h14-05; BY="Repro H14-05"
PORT=""
for p in 9780 9781 9782 9783 9784 9785 9786 9787 9788 9789; do
  [ -z "$(bh_port_pid $p)" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "no free port in 9780-9789"; echo "RESULT: NO-DEFECT (no port to serve on)"; exit 0; }
DATA="$BH_WORK/data-$DB"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$DATA"; }
trap cleanup EXIT
rm -rf "$DATA"

O=$(bh_svc_start "$DB" "$PORT" 2>/dev/null) || { echo "RESULT: NO-DEFECT (the service did not start)"; exit 0; }
echo "service $O over fresh database $DB, no key"
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
c() { curl -s --noproxy '*' "$@"; }
j() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }

bh_project "$O" "$P" >/dev/null
S1="The strain reached an ethanol titre of 41.7 g/L after 48 h on glucose."
DOC=$(c -X POST "$O/api/intake/paste" "${H[@]}" -d "{\"title\":\"Bench note H14-05\",\"text\":\"$S1\",\"by\":\"$BY\",\"url\":\"\",\"licenceClass\":\"unknown\",\"licence\":\"\",\"reason\":\"home check\"}" \
  | j 'print(d.get("documentId") or "")')
echo "step 1: pasted document $DOC"
SEC=""
for i in $(seq 1 30); do
  SEC=$(c "$O/api/biorepo/overlay" "${H[@]}" | j "p=d['papers'].get('$DOC') or {}; s=p.get('sections') or []; print(s[0]['id'] if s else '')")
  [ -n "$SEC" ] && break; sleep 1
done
echo "step 2: its passage $SEC"

CID=$(c -X POST "$O/api/tools/biorepo_write?by=Repro%20H14-05" "${H[@]}" \
  -d "{\"action\":\"candidate\",\"target\":\"\",\"fields\":{\"paperId\":\"$DOC\",\"sectionId\":\"$SEC\",\"field\":\"ethanol_titre\",\"value\":\"41.7\",\"unit\":\"g/L\",\"quote\":\"$S1\"},\"note\":\"home check\"}" \
  | j 'print((d.get("summary") or {}).get("candidateId") or "")')
echo "step 3: candidate written by hand through the tool door: $CID"
[ -n "$CID" ] || { echo "RESULT: NO-DEFECT (no candidate was written; setup failed)"; exit 0; }

NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
c -X POST "$O/api/biorepo/decisions" "${H[@]}" \
  -d "{\"recordId\":\"$CID\",\"status\":\"verified\",\"provenance\":\"gold\",\"gold\":{\"value\":41.7,\"unit\":\"g/L\"},\"reviewer\":\"$BY\",\"at\":\"$NOW\"}" \
  | j 'print("step 4: promoted to the gold set:", d.get("recordId"), d.get("status"), "provenance", d.get("provenance"), "gold", d.get("gold"))'
NGOLD=$(c "$O/api/biorepo/overlay" "${H[@]}" | j 'print(sum(1 for r in (d.get("records") or {}).values() if r.get("gold")) if isinstance(d.get("records"),dict) else sum(1 for r in (d.get("records") or []) if r.get("gold")))' 2>/dev/null || echo "?")
echo "step 5: GET /api/biorepo/overlay holds $NGOLD record(s) with a gold value"

SCR=$(cd "$HERE" && node screen.mjs "$O" "$P" 2>&1 | tail -1)
echo "step 6: Home of the built app in Chromium (project $P): $SCR"
read -r GOLDN GOLDSUB BIOLINE <<<"$(echo "$SCR" | python3 -c '
import json,sys
try: d=json.loads(sys.stdin.read())
except Exception: d={}
g=d.get("goldTile") or []; b=d.get("bioRepo") or []
q=lambda s: (s or "-").replace(" ", "_")
print(q(g[1] if len(g)>1 else ""), q(g[2] if len(g)>2 else ""), q(b[2] if len(b)>2 else ""))')"

echo "step 7: the line's source at 2047f5a, written for every count:"
git -C "$BH_ROOT" show 2047f5a:src/screens/Home.tsx | grep -n "gold set not yet annotated" | sed 's/^/  src\/screens\/Home.tsx:/'
echo "EXPECTED: with one gold value on the Gold set tile, the BioRepo destination line counts the gold values or leaves the gold set out (Home.tsx:235-237: \"What each destination actually has, right now ... Counted from the store's lists\")"
echo "OBSERVED: Gold set tile \"${GOLDN//_/ }\" with \"${GOLDSUB//_/ }\"; BioRepo destination line \"${BIOLINE//_/ }\""
if [ "$GOLDN" = 1 ] && echo "$BIOLINE" | grep -q "gold_set_not_yet_annotated"; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
