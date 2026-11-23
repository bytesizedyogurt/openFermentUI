#!/usr/bin/env bash
# H14-09: Studies' Run it on a plant whose basis the project holds already answers with the kept row, and the card
# reads "Ran <plant>. Run <id>". The candidate holds that this breaks docs/api/runs.md:186-189.
# A fresh database, the service keyless on 127.0.0.1 (a port in 9190-9199), one project; Person One runs cornstover
# through POST /api/library/cornstover/run; Person Two then presses Run it on the built app's Studies page in
# headless Chromium; the runs are read back from GET /api/runs. The contract is checked as written: the second ask is
# answered from the held row, nothing is written, and the row's `by` and `at` stay the first asker's.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE="$BH_ROOT/bughunt/repro/H14-09"
DB=bh_r_h14_09_held; P=h14-09; PLANT=cornstover; ONE="Person One"; TWO="Person Two"
PORT=""
for p in 9190 9191 9192 9193 9194 9195 9196 9197 9198 9199; do
  [ -z "$(bh_port_pid $p)" ] && { PORT=$p; break; }
done
[ -n "$PORT" ] || { echo "no free port in 9190-9199"; echo "RESULT: NO-DEFECT (no port to serve on)"; exit 0; }
DATA="$BH_WORK/data-$DB"
SHOT="$BH_WORK/H14-09-card.png"
TMP=$(mktemp -d "$BH_WORK/H14-09.XXXX")
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$DATA" "$TMP" "$SHOT"; }
trap cleanup EXIT
rm -rf "$DATA"

O=$(bh_svc_start "$DB" "$PORT" 2>/dev/null) || { echo "RESULT: NO-DEFECT (the service did not start)"; exit 0; }
echo "service $O over fresh database $DB, no key"
bh_project "$O" "$P" >/dev/null
echo "step 1: project $P made"
H=(-H "X-OpenFerment-Project: $P" -H 'content-type: application/json')

# Step 2: the first asker keeps the run (BioSTEAM's worker computes it).
T0=$(date +%s)
curl -s --noproxy '*' --max-time 900 -X POST "$O/api/library/$PLANT/run" "${H[@]}" \
     -d "{\"configuration\":null,\"inputs\":[],\"by\":\"$ONE\"}" > "$TMP/first.json"
read -r ID1 ST1 BY1 AT1 <<<"$(python3 -c '
import json,sys
try: r=json.load(open(sys.argv[1]))["run"]
except Exception as e: print("- - - -"); sys.exit()
print(r["id"], r["status"], r["by"].replace(" ","_"), r["at"])' "$TMP/first.json")"
echo "step 2: POST /api/library/$PLANT/run by \"$ONE\" took $(( $(date +%s) - T0 )) s: run $ID1, status $ST1, by ${BY1//_/ }, at $AT1"
[ "$ST1" = done ] || { head -c 600 "$TMP/first.json"; echo; echo "RESULT: NO-DEFECT (the first run was not kept done)"; exit 0; }
N1=$(curl -s --noproxy '*' "$O/api/runs" "${H[@]}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
echo "step 3: GET /api/runs holds $N1 run(s)"
sleep 3

# Step 4: the second asker presses Run it on the same plant on the Studies page.
SCR=$(cd "$HERE" && node screen.mjs "$O" "$P" "$PLANT" "$TWO" "$SHOT" 2>&1 | tail -1)
echo "$SCR" > "$TMP/screen.json"
python3 - "$TMP/screen.json" <<'PY'
import json,sys
d=json.loads(open(sys.argv[1]).read() or "{}")
if d.get("error"): print("step 4: the page failed:", d["error"])
print(f'step 4: Studies as "{d.get("reviewer")}", Run it on the plant answered in {d.get("seconds")} s')
print(f'  the card: "{d.get("cardLine")}" (data-run {d.get("cardRun")}, data-status {d.get("cardStatus")})')
for r in d.get("tableRows") or []: print(f'  runs table row: {r}')
PY

# Step 5: the store after the second ask.
curl -s --noproxy '*' "$O/api/runs" "${H[@]}" > "$TMP/after.json"
read -r N2 BY2 AT2 <<<"$(python3 -c '
import json,sys
rs=json.load(open(sys.argv[1])); r=[x for x in rs if x["id"]==sys.argv[2]]
print(len(rs), (r[0]["by"] if r else "-").replace(" ","_"), r[0]["at"] if r else "-")' "$TMP/after.json" "$ID1")"
echo "step 5: GET /api/runs holds $N2 run(s); run $ID1 by ${BY2//_/ }, at $AT2"
read -r CARDRUN NAMES_ONE NAMES_TWO TABLE_TWO <<<"$(python3 -c '
import json,sys
d=json.loads(open(sys.argv[1]).read() or "{}")
line=d.get("cardLine") or ""
rows=d.get("tableRows") or []
print(d.get("cardRun") or "-", int(sys.argv[2] in line), int(sys.argv[3] in line), int(any(sys.argv[3] in r for r in rows)))' "$TMP/screen.json" "$ONE" "$TWO")"
CARD=$(python3 -c 'import json,sys; print((json.loads(open(sys.argv[1]).read() or "{}").get("cardLine") or "-"))' "$TMP/screen.json")

echo "step 6: the contract and the card's source at 2047f5a:"
git -C "$BH_ROOT" show 2047f5a:docs/api/runs.md | sed -n 186,189p | sed 's/^/  docs\/api\/runs.md: /'
git -C "$BH_ROOT" show 2047f5a:src/screens/ProformaStudies.tsx | sed -n 90p | sed 's/^ */  src\/screens\/ProformaStudies.tsx:90: /'
echo "  no document at 2047f5a asks the Studies card to name who kept a held run or when:"
echo "    grep for 'already ran|ran already|held already|kept already' in docs/api, docs/decisions, src/screens: $(git -C "$BH_ROOT" grep -n -i -E 'already ran|ran already|run already|held already|kept already' 2047f5a -- docs/api docs/decisions src/screens | grep -v -i 'runbook\|version\|protocol\|catalogue' | wc -l) hit(s) about runs"

echo "EXPECTED: (docs/api/runs.md:186-189) the second ask is answered from the held row as it was first kept, writing nothing, so the row's by and at stay the first asker's (\"$ONE\", $AT1); the card answers that run and links to its page, and the runs list shows it by \"$ONE\""
echo "OBSERVED: the card answers run $CARDRUN with \"$CARD\" (names \"$ONE\": $NAMES_ONE, names \"$TWO\": $NAMES_TWO); the store holds $N2 run(s) after (it held $N1), run $ID1 by ${BY2//_/ }, at $AT2; a table row by \"$TWO\": $TABLE_TWO"
BREAK=0
[ "$CARDRUN" = "$ID1" ] || BREAK=1
[ "$N2" = "$N1" ] || BREAK=1
[ "${BY2//_/ }" = "$ONE" ] || BREAK=1
[ "$AT2" = "$AT1" ] || BREAK=1
[ "$TABLE_TWO" = 0 ] || BREAK=1
[ "$NAMES_TWO" = 0 ] || BREAK=1
if [ "$BREAK" = 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "the card says \"Ran\" for the held row and names no keeper or time, as the candidate saw; the contract governs the store's answer, which holds, and the card claims nothing it contradicts"
  echo "RESULT: NO-DEFECT"
fi
exit 0
