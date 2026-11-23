#!/usr/bin/env bash
# H9-12: a 400-digit JSON integer as a quantity's value makes tools.run raise OverflowError in
# numbers_in before its try, so the REST tool door answers a 500 and MCP a wordless isError.
#   bash bughunt/repro/H9-12/run.sh        (from the repository root; exits 0 either way)
# A fresh test database, a keyless service on 127.0.0.1:10350, one project, then study_scenario
# with a 1e309 value (the control: refused in words) and a 400-digit integer value, at three doors:
# tools.run in process, POST /api/tools/study_scenario, and the MCP server over raw JSON-RPC.
# No model call, no network beyond loopback.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h9_12_door
PORT=10350
PROJ=h9-12
HERE=/home/user/openFermentUI/bughunt/repro/H9-12
LOG="$BH_WORK/svc-$PORT.log"
cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT

O=$(bh_svc_start "$DB" "$PORT") \
  || { echo "the service did not start"; echo "RESULT: NO-DEFECT (the service could not be started)"; exit 0; }
echo "database: $DB (fresh, migrated to head); service: $O"
echo "project: $(bh_project "$O" "$PROJ" | cut -c1-120)"
echo

echo "## 1. tools.run in this process (its docstring: \"nothing here raises\")"
DIRECT=$(OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" bh_py "$HERE/direct_call.py" "$PROJ" 2>&1)
echo "$DIRECT"
echo

echo "## 2. POST /api/tools/study_scenario?by=Edge%20Tester"
H=(-H "X-OpenFerment-Project: $PROJ" -H 'content-type: application/json')
BIG=$(python3 -c "print('9'*400)")
body() { printf '{"title":"t","plant":"zz","values":[{"key":"k","quantity":{"value":%s,"unit":"g/L"}}]}' "$1"; }
REST_CTRL=$(curl -s --noproxy '*' -w ' [%{http_code}]' -X POST "$O/api/tools/study_scenario?by=Edge%20Tester" \
  "${H[@]}" -d "$(body 1e309)")
echo "1e309 value (control): $(echo "$REST_CTRL" | cut -c1-400)"
REST_BIG=$(curl -s --noproxy '*' -w ' [%{http_code}]' -X POST "$O/api/tools/study_scenario?by=Edge%20Tester" \
  "${H[@]}" -d "$(body "$BIG")")
echo "400-digit integer value: $(echo "$REST_BIG" | cut -c1-400)"
OVER_LOG=$(grep -c "OverflowError" "$LOG" 2>/dev/null); OVER_LOG=${OVER_LOG:-0}
echo "service log lines naming OverflowError: $OVER_LOG"
grep -n -E "OverflowError|tools/__init__.py" "$LOG" | tail -4
echo

echo "## 3. the MCP server in its own process, raw JSON-RPC tools/call"
MCP=$(bh_py "$HERE/mcp_call.py" "$BH_SERVER/$DB" "$PROJ" 2>&1)
echo "$MCP"
echo

REFUSED_WORDS='NaN or infinite, and a number a tool takes is finite; nothing ran'
d_ctrl=$(echo "$DIRECT" | grep -c "^DIRECT 1e309.*returned a ToolResult.*$REFUSED_WORDS")
d_big=$(echo "$DIRECT" | grep -c "^DIRECT 400-digit.*raised OverflowError")
r_ctrl=$(echo "$REST_CTRL" | grep -c "$REFUSED_WORDS.*\[200\]$")
r_big=$(echo "$REST_BIG" | grep -c "\[500\]$")
m_ctrl=$(echo "$MCP" | grep -c "^CASE 1e309.*isError=False.*NaN or infinite")
m_big=$(echo "$MCP" | grep -c "^CASE 400-digit.*isError=True")
echo "EXPECTED: study_scenario with a 400-digit integer as a quantity's value is refused as the 1e309 control is: tools.run returns a ToolResult whose error says the value is no finite number, POST /api/tools/study_scenario answers 200 with that ToolResult, and MCP answers that ToolResult as JSON with isError false (tools/__init__.py:503 \"nothing here raises\"; docs/TOOLS.md:896)."
echo "OBSERVED: control refused in words at each door (direct=$d_ctrl rest=$r_ctrl mcp=$m_ctrl); the 400-digit integer: tools.run raised OverflowError ($d_big), REST answered $(echo "$REST_BIG" | grep -o '\[[0-9]*\]$') '$(echo "$REST_BIG" | sed 's/ \[[0-9]*\]$//' | cut -c1-60)' with $OVER_LOG OverflowError lines in the service log, MCP answered $(echo "$MCP" | grep '^CASE 400-digit' | sed 's/^CASE 400-digit integer value | //' | cut -c1-120)."
if [ "$d_ctrl" = 1 ] && [ "$r_ctrl" = 1 ] && [ "$m_ctrl" = 1 ] && [ "$d_big" = 1 ] && [ "$r_big" = 1 ] && [ "$m_big" = 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
