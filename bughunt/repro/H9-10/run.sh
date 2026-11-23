#!/usr/bin/env bash
# H9-10: Postdoc's loop asks at most two models of the plan route. With OPENFERMENT_ROUTES naming the
# plan route claude-opus-5-5, claude-sonnet-5-5, claude-haiku-5-5 and the first two unavailable, the
# question declines after the second; GET /api/health names sonnet and haiku as the fallbacks, and
# docs/api/postdoc.md says a route's models are tried in order, each after the one before it declines
# or is unavailable.
#
# A fresh database and project. GET /api/health is read in process; postdoc_agent.ask runs twice with a
# stand-in for the model (the converse hook core/tests/test_postdoc_agent.py uses): a control with opus
# alone unavailable, then the case with opus and sonnet unavailable. No model is asked, the model API's
# address is a closed loopback port, nothing is spent.
#   bash bughunt/repro/H9-10/run.sh        (from the repository root)
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
HERE=/home/user/openFermentUI/bughunt/repro/H9-10
DB=bh_r_h9_10_loop; PROJECT=h9-10
W="$BH_WORK/H9-10"; rm -rf "$W"; mkdir -p "$W/data"
OUT="$W/repro.out"
ROUTE='{"plan": {"models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"], "effort": "high"}}'

cleanup() {
  bh_db_drop "$DB" >/dev/null 2>&1
  rm -rf "$W"
}
trap cleanup EXIT

echo "## commit under test: $(git -C "$BH_ROOT" rev-parse --short HEAD); core/ and docs/ against 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a HEAD -- core docs && echo unchanged || echo CHANGED)"

# 1. A fresh database, migrated to head.
bh_db_fresh "$DB" 2>/dev/null || { echo "RESULT: NO-DEFECT (setup failed: database)"; exit 0; }

# 2. Health and the loop over that database, keyless, the plan route of three models.
(
  cd "$BH_ROOT/core" || exit 1
  bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$W/data" \
    OPENFERMENT_SFF_LIBRARY="$W/data/sff-library" OPENFERMENT_ROUTES="$ROUTE" OPENFERMENT_LOCAL_BASE_URL= \
    ANTHROPIC_BASE_URL=http://127.0.0.1:9959 PYTHONDONTWRITEBYTECODE=1 \
    .venv/bin/python "$HERE/repro.py" "$PROJECT"
) > "$OUT" 2>&1

# 3. The contract's words and the loop's cap.
echo "## the contract"
grep -n "its default route: the models tried in order, each after the one before it declines or" "$BH_ROOT/docs/api/postdoc.md"
grep -n "unavailable, and the effort they think at" "$BH_ROOT/docs/api/postdoc.md"
grep -n "several models,$" "$BH_ROOT/docs/api/postdoc.md"; grep -n "^comma-separated, tried in order) over the models of" "$BH_ROOT/docs/api/postdoc.md"
grep -n "list, tried in order) is the chain of the answering families" "$BH_ROOT/core/openferment_core/llm.py"
grep -n "The models the route moves to, in order, when its first declines or" "$BH_ROOT/core/openferment_core/api.py"
grep -n "The models are the plan route's, the one Postdoc's loop answers on" "$BH_ROOT/core/openferment_core/api.py"
echo "## the loop"
grep -n "restarts the question once on the next model" "$BH_ROOT/core/openferment_core/postdoc_agent.py"
grep -n "for i, model in enumerate(models\[:2\]):" "$BH_ROOT/core/openferment_core/postdoc_agent.py"
grep -n "i + 1 >= min(len(models), 2)" "$BH_ROOT/core/openferment_core/postdoc_agent.py"

summary=$(grep '^SUMMARY ' "$OUT" | sed 's/^SUMMARY //')
if [ -z "$summary" ]; then
  echo "the repro did not finish; its output:"; tail -20 "$OUT"
  echo "RESULT: NO-DEFECT (setup failed: the repro)"; exit 0
fi

echo "## what ran"
SUMMARY="$summary" python3 - <<'PY'
import json, os
s = json.loads(os.environ["SUMMARY"])
print("plan route (llm.chain):", s["route"])
print("GET /api/health: model", repr(s["health"]["model"]), "fallbackModel", repr(s["health"]["fallbackModel"]))
for k in ("control", "case"):
    r = s[k]
    print(f"{k}: unavailable {r['unavailable']}; asked {r['asked']}; declined {r['declined']!r}")
    for step in r["steps"]:
        print("   step:", step)
PY

verdict=$(SUMMARY="$summary" python3 - <<'PY'
import json, os
s = json.loads(os.environ["SUMMARY"])
three = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]
route_ok = s["route"] == three
health_names = s["health"]["fallbackModel"] == "claude-sonnet-5-5, claude-haiku-5-5"
control_ok = s["control"]["asked"] == three[:2] and s["control"]["steps"][-1].startswith("Answered:")
case = s["case"]
capped = (case["asked"] == three[:2] and "claude-haiku-5-5" not in case["asked"]
          and case["steps"][-1].startswith("No answer:"))
print("DEFECT" if (route_ok and health_names and control_ok and capped) else "NO-DEFECT")
PY
)

echo "EXPECTED: with the plan route opus, sonnet, haiku (health's fallbacks 'claude-sonnet-5-5, claude-haiku-5-5') and opus and sonnet unavailable, the loop asks opus, then sonnet, then haiku, and haiku's plan is the answer (the last step 'Answered: …', as the control's sonnet plan is)"
echo "OBSERVED: $(SUMMARY="$summary" python3 -c 'import json,os; s=json.loads(os.environ["SUMMARY"]); c=s["case"]; print("health fallbackModel %r; asked %s; declined %r; last step %r" % (s["health"]["fallbackModel"], c["asked"], c["declined"], c["steps"][-1]))')"
echo "RESULT: $verdict"
exit 0
