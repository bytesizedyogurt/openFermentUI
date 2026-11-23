#!/usr/bin/env bash
# H3-07: units.normalize folds an upper-case SI prefix onto the lower-case one, so Mg (megagram) reads as mg,
# ML (megalitre) as mL, Mm as millimolar, S as seconds and G as grams; convert(1, 'Mg', 'kg') answers 1e-06.
#   bash bughunt/repro/H3-07/run.sh        (from the repository root; exits 0 either way)
# A fresh test database (bh_r_h3_07_svc, migrated to head) under the service on 127.0.0.1:9390, keyless, no
# worker started, no model call, no network beyond loopback. repro.py runs with the repository's Python: the unit
# engine (part A) and the lesson catalogue's door (part B). browser.ts runs src/engine/units.ts under tsx (part C).
# On exit the service stops, the database is dropped and the data copy is removed.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
export PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h3_07_svc
PORT=9390
HERE=/home/user/openFermentUI/bughunt/repro/H3-07
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$BH_WORK/svc-$PORT.log"; }
trap cleanup EXIT

O=$(bh_svc_start "$DB" "$PORT") || { echo "the service did not start"; echo "RESULT: NO-DEFECT (the service could not start)"; exit 0; }
echo "service: $O over $DB (fresh, migrated to head)"
bh_project "$O" h3-07 "H3-07 units" >/dev/null
echo
OUT=$(bh_py "$HERE/repro.py" "$O" 2>&1)
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|PYRESULT):'
echo "== Part C: the browser's engine (src/engine/units.ts) and the Primer's grading =="
BOUT=$(cd "$BH_ROOT" && bh_env node_modules/.bin/tsx "$HERE/browser.ts" 2>&1)
echo "$BOUT" | grep -v '^BROWSER_FOLDED'
BF=$(echo "$BOUT" | sed -n 's/^BROWSER_FOLDED \([0-9]*\) of \([0-9]*\)$/\1 \2/p')
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "OBSERVED: the browser's normalizeUnit folds ${BF% *} of ${BF#* } probes the same way (src/engine/units.ts:377-389), and the Primer grades '2000 kg' $(echo "$BOUT" | sed -n 's/.*types "2000 kg" against the answer 2 Mg -> \(.*\)$/\1/p') and '2 mg' $(echo "$BOUT" | sed -n 's/.*types "2 mg" against the answer 2 Mg -> \(.*\)$/\1/p') against an answer of 2 Mg"
if echo "$OUT" | grep -q '^PYRESULT: DEFECT$'; then
  echo "RESULT: DEFECT"
elif echo "$OUT" | grep -q '^PYRESULT: NO-DEFECT$'; then
  echo "RESULT: NO-DEFECT"
else
  echo "RESULT: NO-DEFECT (the script did not complete; see the lines above)"
fi
exit 0
