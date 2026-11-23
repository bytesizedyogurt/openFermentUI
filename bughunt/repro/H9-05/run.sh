#!/usr/bin/env bash
# H9-05: the ask cap does not hold. A round's ceiling is sized to spend every dollar the budget has left,
# so the MIN_TOKENS answer the loop holds back is paid for past OPENFERMENT_ASK_BUDGET_USD; a zero budget
# still asks for tools and makes two model calls.
# Postdoc's own loop (postdoc_agent.ask) on a fresh test database, a stand-in converse, no service, keyless,
# no model call, the network refused in the process.
# usage, from the repository root: bash bughunt/repro/H9-05/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H9-05
DB=bh_r_h9_05_ask
T=$BH_WORK/H9-05; mkdir -p "$T"
cleanup() { bh_db_drop "$DB"; rm -rf "$T"; }
trap cleanup EXIT
touch "$T/marker"

if git -C "$BH_ROOT" diff --quiet 2047f5a -- core src scripts examples; then
  echo "TREE: core/, src/, scripts/ and examples/ match 2047f5a"
else
  echo "TREE: core/, src/, scripts/ or examples/ differ from 2047f5a"
fi

echo "EXPECTED: at every ask budget, the question's total cost stays at or under OPENFERMENT_ASK_BUDGET_USD whenever"
echo "EXPECTED: each turn costs at most the code's own worst case for it (llm.worst_case_usd: its request at two"
echo "EXPECTED: characters a token, every output token its max_tokens allows); ADR-008:101-102 'the loop stops asking"
echo "EXPECTED: for tools when what it spent and what the answer could cost reach the question's budget, so the answer"
echo "EXPECTED: is paid for within it'; postdoc_agent.py:545-546 'so the answer is always paid for within the question's"
echo "EXPECTED: budget'. At a zero budget the loop asks for no tools, so at most the one answer turn is made."

bh_db_fresh "$DB" || { echo "OBSERVED: the test database could not be made"; echo "RESULT: NO-DEFECT"; exit 0; }
(cd "$BH_ROOT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 OPENFERMENT_ROUTES= \
   OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" .venv/bin/python "$HERE/ask_cap.py" 0 0.75 2.00) 2>&1 | tee "$T/out.log"

python3 - "$T/out.log" > "$T/verdict" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
past = [r for r in rows if r["pastTheBudget"] and r["everyTurnAtOrUnderItsWorstCase"]]
for r in rows:
    turns = ", ".join(f"({t['tool_choice']}, {t['max_tokens']} tokens, {t['costUsd']:.4f} USD)" for t in r["turns"])
    print(f"OBSERVED: budget {r['askBudgetUsd']} USD: {r['modelTurns']} model turns {turns}; total {r['spentUsd']:.4f} USD;"
          f" stopped '{r['stopped']}'; every turn at or under its worst case: {r['everyTurnAtOrUnderItsWorstCase']}")
zero = next((r for r in rows if float(r["askBudgetUsd"]) == 0), None)
zero_tools = bool(zero and zero["turns"] and zero["turns"][0]["tool_choice"] == "auto")
print(f"OBSERVED: {len(past)} of {len(rows)} budgets ended past the cap; at budget 0 the first turn asked for tools: {zero_tools}")
print("VERDICT", "DEFECT" if rows and (past or zero_tools) else "NO-DEFECT")
PY
grep '^OBSERVED' "$T/verdict"

changed=$(find "$BH_ROOT/core" "$BH_ROOT/src" "$BH_ROOT/scripts" "$BH_ROOT/examples" -newer "$T/marker" -type f 2>/dev/null | wc -l)
echo "TREE: $changed file(s) under core/, src/, scripts/ or examples/ written during the run"

if grep -q '^VERDICT DEFECT' "$T/verdict"; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
