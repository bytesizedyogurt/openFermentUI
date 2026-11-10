#!/usr/bin/env bash
# H3-02: Rule 1's detector (validate.find_number) lets numbers written in words through, and validate_plan
# keeps such a claim with its cited record's class (verified).
# Run from the repository root: bash bughunt/repro/H3-02/run.sh
# The defect lives in pure functions (find_number, validate_plan, evidence_pool.build, held_to_rule_one) that
# read no database and call no service, model or network, so this makes none: repro.py runs them on the tree
# as it stands, keyless, with bytecode writing off. Nothing to clean up. Exits 0 either way.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
HERE=/home/user/openFermentUI/bughunt/repro/H3-02
if git -C "$BH_ROOT" diff --quiet 2047f5a -- core/openferment_core; then
  echo "tree: core/openferment_core matches 2047f5a (HEAD $(git -C "$BH_ROOT" rev-parse --short HEAD))"
else
  echo "tree: core/openferment_core differs from 2047f5a"
fi
OUT=$(cd "$BH_ROOT/core" && bh_env .venv/bin/python -I "$HERE/repro.py" 2>&1)
echo "$OUT" | grep -v '^H302_'
COUNTS=$(echo "$OUT" | sed -n 's/^H302_COUNTS: //p')
VERDICT=$(echo "$OUT" | sed -n 's/^H302_VERDICT: \([A-Z-]*\).*/\1/p')
echo
echo "EXPECTED: each claim whose words state a number (two dollars per gallon, ten per cent, ten tonnes, two thirds, hundreds of litres, a superscript two) dropped and counted with its reason, as its twin in digits or in a caught word is (CLAUDE.md:55; ADR-006:26; validate.py:12, :58, :137)"
echo "OBSERVED: ${COUNTS:-no counts: repro.py did not finish}"
if [ "$VERDICT" = DEFECT ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
