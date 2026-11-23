#!/usr/bin/env bash
# P-03: Guild's review strip says the records it hides sit "on papers with no PMCID, DOI or PMID, which
# biorepo.write refuses"; the filter hides records on documents the project does not hold (paperHeld) and
# biorepo.write keeps a decision on a held document with no identifier.
# The static part greps the tree; the live part is the head's own service on 127.0.0.1:10120 over a fresh
# database, fixture mode (no model, no network), keyless. Nothing under core/, src/, scripts/ or examples/ changes.
# usage, from the repository root: bash bughunt/repro/P-03/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=$BH_ROOT/bughunt/repro/P-03
DB=bh_r_p_03_svc
PORT=10120
T=$BH_WORK/P-03/run.$$; mkdir -p "$T"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB" 2>/dev/null; rm -rf "$BH_WORK/data-$DB" "$T"; rmdir "$BH_WORK/P-03" 2>/dev/null; }
trap cleanup EXIT
cd "$BH_ROOT" || exit 0

echo "EXPECTED: the strip under Guild's 'Papers the service can keep' box names the rule the filter applies,"
echo "EXPECTED: records on documents the project does not hold, the rule paperHeld and biorepo.write's 'paper' share"
echo "EXPECTED: (docs/PROGRESS.md:601, paid at 5287542; core/openferment_core/biorepo.py:26)."

echo "== the contract"
grep -no "The client's review path kept alpha 1.0's curated-record machinery\|its committed file's rule that a decision needs a PMCID, DOI or PMID | alpha 2.0, 8.5 | .5287542." docs/PROGRESS.md
grep -n "paper      the record's paper is not a document the project holds" core/openferment_core/biorepo.py
grep -n "such records were hidden from the default queue, though \`biorepo.write\` keeps a decision on" docs/PROGRESS.md
grep -n "service's now (\`paperHeld\`)" docs/PROGRESS.md | cut -c1-60
echo "== the strip's words and the filter they describe"
grep -n "papers with no PMCID, DOI or PMID, which" src/screens/Guild.tsx
grep -n "biorepo.write</code> refuses" src/screens/Guild.tsx
sed -n '208,216p' src/screens/Guild.tsx | sed 's/^/Guild.tsx: /'
echo "== the rule the filter applies"
grep -n -A2 "^export function paperHeld" src/lib/review.ts
grep -n "which is not a document this project holds" core/openferment_core/biorepo.py
echo "== the comments that kept the old rule"
grep -n "a paper with no identifier" src/lib/review.ts
grep -n "A paper with no identifier is still reviewable here" src/lib/review.ts

words=$(grep -c "papers with no PMCID, DOI or PMID, which" src/screens/Guild.tsx)
body=$(awk '/^export function paperHeld/{f=1} f{print} f&&/^}/{exit}' src/lib/review.ts)
reads_id=$(printf '%s\n' "$body" | grep -ciE "doi|pmcid|pmid")
held_rule=$(printf '%s\n' "$body" | grep -c "return paper !== undefined;")
comments=$(grep -ci "paper with no identifier" src/lib/review.ts)

echo "== live: a project holding two uploads with no PMCID, DOI or PMID; a decision through biorepo.write"
O=$(BH_FIXTURES=1 bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" p03 >/dev/null
bh_py "$HERE/seed.py" "$O" p03 "$BH_WORK/data-$DB/fixtures" "$T/overlay.json" | tee "$T/seed.log"
echo "== live: Guild's filter (Guild.tsx:208-216) over the project's overlay, with the tree's paperHeld"
timeout 180 node_modules/.bin/tsx "$HERE/filter.ts" "$T/overlay.json" | tee "$T/filter.log"

kept=$(grep -cE "^DECISION: .*doi=None pmcid=None\) answered HTTP 200" "$T/seed.log")
no_id_held=$(grep -c "^HELD: .* doi=None pmcid=None" "$T/seed.log")
shown=$(sed -n 's/.*shown with no PMCID or DOI=\([0-9]*\).*/\1/p' "$T/filter.log")
hid=$(sed -n 's/.*hidden though it has a DOI and PMCID=\([0-9]*\).*/\1/p' "$T/filter.log")

echo "OBSERVED: src/screens/Guild.tsx:627 says hidden records sit on papers with no PMCID, DOI or PMID ($words line),"
echo "OBSERVED: and paperHeld (src/lib/review.ts:215-217) is 'return paper !== undefined;' ($held_rule line), reading no identifier ($reads_id lines name one)."
echo "OBSERVED: the project holds $no_id_held documents with no DOI or PMCID; biorepo.write kept a decision on one ($kept answered HTTP 200);"
echo "OBSERVED: the filter shows ${shown:-0} waiting record(s) on such a document and hides ${hid:-0} on a paper with a DOI and PMCID the project does not hold;"
echo "OBSERVED: review.ts still speaks of 'a paper with no identifier' in $comments comment(s) (:224, :310)."
if [ "${words:-0}" -ge 1 ] && [ "${reads_id:-1}" -eq 0 ] && [ "${held_rule:-0}" -eq 1 ] \
   && [ "${kept:-0}" -ge 1 ] && [ "${shown:-0}" -ge 1 ] && [ "${hid:-0}" -ge 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
