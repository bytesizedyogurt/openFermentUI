#!/usr/bin/env bash
# P-02: a verified decision with no gold value is kept and served gold when its label says gold, and the browser
# reads the same decision as verified. Run from the repository root: bash bughunt/repro/P-02/run.sh
# Keyless and offline (fixture collectors, a stand-in extraction). Its own database, port 10250, cleaned up on exit.
set -u
cd /home/user/openFermentUI || exit 0
# shellcheck disable=SC1091
source bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/P-02
DB=bh_r_p_02_main
PORT=10250
PROJECT=p02
WORK=$BH_WORK/P-02
ORIGIN=http://127.0.0.1:$PORT
mkdir -p "$WORK"
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB" "$WORK"
}
trap cleanup EXIT

echo "== 1. the rule alone: biorepo.provenance_of"
RULE=$(bh_py "$HERE/function_rule.py" 2>&1); echo "$RULE"

echo "== 2. the service over a fresh database ($DB) on $PORT, fixture collectors, keyless"
if ! BH_FIXTURES=1 bh_svc_start "$DB" "$PORT" >/dev/null 2>"$WORK/start.err"; then
  cat "$WORK/start.err"
  echo "the service did not start; see $BH_WORK/svc-$PORT.log"; tail -5 "$BH_WORK/svc-$PORT.log"
  echo "RESULT: NO-DEFECT"; exit 0
fi
bh_project "$ORIGIN" "$PROJECT" "P-02 reproduction" >/dev/null; echo
FIX="$BH_WORK/data-$DB/fixtures"
bh_py "$HERE/probe.py" "$ORIGIN" "$PROJECT" "$FIX" "$WORK/probe.json" 2>&1 | grep -v '^\s*$'
RID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("recordId",""))' "$WORK/probe.json" 2>/dev/null)
echo "record: $RID"

echo "== 3. the records table's row for it"
ROW=$(psql "$BH_SERVER/$DB" -XAtc "select version, status, provenance, coalesce(body->'decision'->>'gold','null') from openferment.records where id='$RID' order by version desc limit 1")
echo "openferment.records (version|status|provenance|gold): $ROW"

echo "== 4. the browser's provenanceOf on the decision the overlay serves"
BROWSER=$(node_modules/.bin/tsx "$HERE/browser_rule.ts" "$WORK/probe.json" 2>&1 | grep '^BROWSER'); echo "$BROWSER"

echo "== 5. the Intake screen in Chromium (the built app in dist/)"
SCREEN=$(ORIGIN=$ORIGIN PROJECT=$PROJECT RECORD=$RID node "$HERE/intake_screen.mjs" 2>&1 | grep '^SCREEN'); echo "$SCREEN"

# The verdict, read off what each step printed.
RULE_GOLD=$(echo "$RULE" | grep -c "label 'gold', gold None) = gold")
RULE_VER=$(echo "$RULE" | grep -c "label 'verified', gold None) = verified")
STORED=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("stored",{}).get("provenance"), (d.get("overlay") or {}).get("provenance"), (d.get("overlay") or {}).get("gold"), "|".join(str(r[2]) for r in d.get("pool",[])))' "$WORK/probe.json" 2>/dev/null)
read -r S_PROV O_PROV O_GOLD POOL_PROV <<<"$STORED"
ROW_PROV=$(echo "$ROW" | cut -d'|' -f3)
ROW_GOLD=$(echo "$ROW" | cut -d'|' -f4)
BROWSER_PROV=$(echo "$BROWSER" | sed -n 's/^BROWSER provenanceOf.* = \([a-z-]*\)$/\1/p')
echo
echo "EXPECTED: a verified decision with gold null is verified whatever its label (ADR-006 §8.5: 'gold' for a verified decision with a gold value, 'verified' for any other verified one, stored 'whatever label the request carried'); the stored decision, the records row, biorepo_read and the browser's provenanceOf all say verified"
echo "OBSERVED: provenance_of(verified, gold None) is $(echo "$RULE" | sed -n "s/.*label 'gold', gold None) = //p") under label gold and $(echo "$RULE" | sed -n "s/.*label 'verified', gold None) = //p") under label verified; POST /api/biorepo/decisions (label gold, gold null) answered provenance $S_PROV; openferment.records provenance $ROW_PROV with gold $ROW_GOLD; biorepo_read provenance $POOL_PROV; overlay decision provenance $O_PROV with gold $O_GOLD; browser provenanceOf on it $BROWSER_PROV; Intake screen: $(echo "$SCREEN" | sed 's/^SCREEN //' | paste -sd ';' -)"
if [ "$RULE_GOLD" = 1 ] && [ "$RULE_VER" = 1 ] && [ "$S_PROV" = gold ] && [ "$ROW_PROV" = gold ] \
   && [ "$POOL_PROV" = gold ] && [ "$O_GOLD" = None ] && [ "$BROWSER_PROV" = verified ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
