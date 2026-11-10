#!/usr/bin/env bash
# H9-04: Postdoc's validator keeps a claim whose words state a quantity as "doubled", "halved",
# "quadrupled", "Table IV", "x10", "pH7" or "pH-4". The plan prompt names "Ethanol titre
# roughly doubled under anaerobic conditions" as a claim discarded whole; CLAUDE.md's R line says a
# claim with a number in its words is dropped and counted.
#
# A fresh database and project hold one pasted sentence. postdoc_agent.ask runs with a scripted stand-in
# for the model (the converse hook core/tests/test_postdoc_agent.py uses): one search_passages call over
# the project's document, then a plan whose claims quote that sentence word for word. No model is asked,
# no request leaves the machine, nothing is spent. Then the static half: the words the validator lacks.
#   bash bughunt/repro/H9-04/run.sh        (from the repository root)
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
HERE=/home/user/openFermentUI/bughunt/repro/H9-04
DB=bh_r_h9_04_loop; PROJECT=h9-04
W="$BH_WORK/H9-04"; rm -rf "$W"; mkdir -p "$W/data"
OUT="$W/repro.out"

cleanup() {
  bh_db_drop "$DB" >/dev/null 2>&1
  rm -rf "$W"
}
trap cleanup EXIT

echo "## commit under test: $(git -C "$BH_ROOT" rev-parse --short HEAD); core/ against 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a HEAD -- core && echo unchanged || echo CHANGED)"

# 1. A fresh database, migrated to head.
bh_db_fresh "$DB" || { echo "RESULT: NO-DEFECT (setup failed: database)"; exit 0; }

# 2. The loop over that database, keyless; the model API's address is a closed loopback port.
(
  cd "$BH_ROOT/core" || exit 1
  bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$W/data" \
    OPENFERMENT_SFF_LIBRARY="$W/data/sff-library" OPENFERMENT_ROUTES= OPENFERMENT_LOCAL_BASE_URL= \
    ANTHROPIC_BASE_URL=http://127.0.0.1:9959 PYTHONDONTWRITEBYTECODE=1 \
    .venv/bin/python "$HERE/repro.py" "$PROJECT"
) > "$OUT" 2>&1
grep -v '^20[0-9][0-9]-' "$OUT"

# 3. The static half: the contract's words, and the validator's lists.
echo "## the contract"
grep -n "a claim with a number in its words is dropped and counted" "$BH_ROOT/CLAUDE.md"
grep -n "NEVER WRITE A NUMBER IN CLAIM TEXT\|A claim containing a number is discarded whole\|roughly doubled under anaerobic" \
  "$BH_ROOT/core/openferment_core/postdoc/plan.py"
grep -n "a pH, a rate of return, a table or figure\|number or a concentration in claim text or in a gap discards it" \
  "$BH_ROOT/core/openferment_core/postdoc_agent.py"
echo "## the validator: validate_plan's number rule, the word list, the identifier carve-out"
grep -n "if found := find_number(text):" "$BH_ROOT/core/openferment_core/validate.py"
grep -n '"once twice thrice"\|^_IDENTIFIER = \|^STEP_WORDS = ' "$BH_ROOT/core/openferment_core/validate.py"
for w in doubled halved quadrupled; do
  printf '  %-10s in validate.py: %s\n' "$w" "$(grep -c "$w" "$BH_ROOT/core/openferment_core/validate.py")"
done
echo "## the practice drafts' extra check, which says find_number lets these through"
grep -n "What validate.find_number lets through\|double\[sd\]" "$BH_ROOT/core/openferment_core/practice.py"
grep -n "def test_bench_quantities_the_shared_validator_lets_through_are_refused_here" "$BH_ROOT/core/tests/test_practice.py"

summary=$(grep '^SUMMARY ' "$OUT" | sed 's/^SUMMARY //')
if [ -z "$summary" ]; then
  echo "the loop did not finish; its output:"; tail -20 "$OUT"
  echo "RESULT: NO-DEFECT (setup failed: the loop)"; exit 0
fi
read -r kept total cdrop ctotal gapkept cited design < <(python3 -c '
import json, sys
s = json.loads(sys.argv[1])
print(s["defectKept"], s["defectTotal"], s["controlDropped"], s["controlTotal"], int(s["gapDoubledKept"]),
      int(s["passageCited"]), s["byDesignKept"])' "$summary")

echo "EXPECTED: each of the $total claims whose words state a quantity (doubled, halved, quadrupled, Table IV, x10, pH7, pH-4) dropped and counted, rejected $total, its reason naming the word, as the $ctotal controls (twofold, tenfold, pH 7) are; the gap saying \"doubled at pH7\" dropped as the gap saying \"twofold\" is"
echo "OBSERVED: $kept of $total such claims kept, each citing the project's passage with no typed value; $cdrop of $ctotal controls dropped; the \"doubled at pH7\" gap kept=$([ "$gapkept" = 1 ] && echo true || echo false); passage cited=$([ "$cited" = 1 ] && echo true || echo false); for reference, $design of 2 phase-label claims (phase 3, phase III) kept, as the step-label rule means"
if [ "$cited" = 1 ] && [ "$cdrop" = "$ctotal" ] && [ "$kept" -ge 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
