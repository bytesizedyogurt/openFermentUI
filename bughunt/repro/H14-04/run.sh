#!/usr/bin/env bash
# H14-04: Witness with no gold value and one rejected candidate. A fresh database, the service keyless in the
# proof's fixture mode (the extract route reads a written response, no model is called), one pasted document,
# three candidates extracted from it, two accepted as written and one rejected. Then GET /api/witness/runs and
# the Witness screen of the built app in headless Chromium.
# Expected: with goldSize 0 the precision tile says undefined ("—"), as the callout above it and the recall tile
# do. Observed: the callout says precision is undefined without a gold set, and the tile shows 0.0 % on the
# gold tick.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE="$BH_ROOT/bughunt/repro/H14-04"
DB=bh_r_h14_04_wit; P=h14-04; BY="Repro H14-04"
PORT=""
for p in 9084 9085 9086 9087 9088 9089 9080 9081 9082 9083; do
  [ -z "$(bh_port_pid $p)" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "no free port in 9080-9089"; echo "RESULT: NO-DEFECT (no port to serve on)"; exit 0; }
DATA="$BH_WORK/data-$DB"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$DATA"; }
trap cleanup EXIT
rm -rf "$DATA"

O=$(BH_FIXTURES=1 bh_svc_start "$DB" "$PORT" 2>/dev/null) || { echo "RESULT: NO-DEFECT (the service did not start)"; exit 0; }
echo "service $O over fresh database $DB, fixture mode, no key"
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')
c() { curl -s --noproxy '*' "$@"; }
j() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }

bh_project "$O" "$P" >/dev/null
S1="In the batch run, the ethanol titre reached 41.7 g/L after 48 h."
S2="The ethanol yield on glucose was 0.45 g/g."
S3="The volumetric ethanol productivity was 0.87 g/L/h."
DOC=$(c -X POST "$O/api/intake/paste" "${H[@]}" -d "{\"title\":\"Batch note H14-04\",\"text\":\"$S1 $S2 $S3\",\"by\":\"$BY\",\"url\":\"\",\"licenceClass\":\"unknown\",\"licence\":\"\",\"reason\":\"witness check\"}" \
  | j 'print(d.get("documentId") or "")')
echo "step 1: pasted document $DOC"
SEC=""
for i in $(seq 1 30); do
  SEC=$(c "$O/api/biorepo/overlay" "${H[@]}" | j "p=d['papers'].get('$DOC') or {}; s=p.get('sections') or []; print(s[0]['id'] if s else '')")
  [ -n "$SEC" ] && break; sleep 1
done
echo "step 2: its passage $SEC"

mkdir -p "$DATA/fixtures/extract"
python3 - "$DATA/fixtures/extract/$DOC.json" "$SEC" "$S1" "$S2" "$S3" <<'PY'
import json, sys
path, sec, s1, s2, s3 = sys.argv[1:]
c = lambda f, v, u, q: {"sectionId": sec, "field": f, "value": v, "unit": u, "quote": q, "isPrimary": True, "confidence": 0.9}
json.dump({"_note": "bughunt H14-04 stand-in response: no model answered.",
           "raw": {"candidates": [c("ethanol_titre", 41.7, "g/L", s1), c("ethanol_yield_substrate", 0.45, "g/g", s2),
                                  c("ethanol_productivity", 0.87, "g/L/h", s3)]},
           "usage": {"models": ["bughunt-standin"]}}, open(path, "w"))
PY
IDS=$(c -X POST "$O/api/intake/$DOC/extract?force=true" "${H[@]}" | j 'print(" ".join(x["id"] for x in d.get("candidates", [])))')
set -- $IDS
echo "step 3: extracted through the service (fixture response): $# candidates anchored: $IDS"
[ $# -ge 3 ] || { echo "RESULT: NO-DEFECT (fewer than three candidates anchored; setup failed)"; exit 0; }

NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
for id in "$1" "$2"; do
  c -X POST "$O/api/biorepo/decisions" "${H[@]}" -d "{\"recordId\":\"$id\",\"status\":\"verified\",\"provenance\":\"verified\",\"reviewer\":\"$BY\",\"at\":\"$NOW\"}" \
    | j 'print("step 4: accepted as written:", d.get("recordId"), d.get("status"), "gold", d.get("gold"), "corrected", d.get("corrected"))'
done
c -X POST "$O/api/biorepo/decisions" "${H[@]}" -d "{\"recordId\":\"$3\",\"status\":\"rejected\",\"provenance\":\"unverified\",\"rejectReason\":\"wrong value\",\"reviewer\":\"$BY\",\"at\":\"$NOW\"}" \
  | j 'print("step 5: rejected:", d.get("recordId"), d.get("status"), d.get("rejectReason"))'

API=$(c "$O/api/witness/runs" "${H[@]}" | j 'r=d[0]; print(r["run"], len(r["results"]), len(r["falsePositives"]))')
read -r RUN NRES NFP <<<"$API"
echo "step 6: GET /api/witness/runs: run $RUN, results (values reviewers typed, scored) $NRES, falsePositives $NFP"

SCR=$(cd "$HERE" && node screen.mjs "$O" "$P" 2>&1 | tail -1)
echo "step 7: the Witness screen at /p/$P/biorepo/witness: $SCR"
read -r CALLOUT PVAL PTICK PLABEL RVAL COUNTS <<<"$(echo "$SCR" | python3 -c '
import json,re,sys
try: d=json.loads(sys.stdin.read())
except Exception: d={}
p=d.get("precision") or {}; r=d.get("recall") or {}
q=lambda s: (s or "-").replace(" ", "_")
print(q(" / ".join(d.get("callout") or [])), q(p.get("value")), q(p.get("tickClass")), q(p.get("label")), q(r.get("value")), q((re.match(r"tp \d+ · fp \d+ · fn \d+", (d.get("counts") or [""])[0]) or [""])[0]))')"

echo "EXPECTED: with no gold value (results $NRES) the callout says precision and recall are undefined without a gold set, and the precision tile says undefined (—), as the recall tile does"
echo "OBSERVED: callout \"${CALLOUT//_/ }\"; precision tile \"${PVAL//_/ }\" on ${PTICK} (\"${PLABEL//_/ }\"); recall tile \"${RVAL//_/ }\"; \"${COUNTS//_/ }\"; API results $NRES, falsePositives $NFP after two acceptances and one rejection"
if [ "$NRES" = 0 ] && [ "$NFP" = 1 ] && echo "$CALLOUT" | grep -q "undefined_without_a_gold_set" \
   && echo "$PVAL" | grep -Eq '^[0-9]' && [ "$RVAL" = "—" ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
