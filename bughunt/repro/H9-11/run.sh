#!/usr/bin/env bash
# H9-11: the same question asked through the openferment MCP server in its own process and at
# POST /api/ask, on one fresh database; after each, the project's conversations, turns and
# tool calls are counted, and the event stream is watched for turn events.
# Keyless: both asks decline for want of a key, before any model call; a declined plan is an
# answer (docs/api/postdoc.md), so each door has the same question and the same answer to keep.
#   bash bughunt/repro/H9-11/run.sh        (from the repository root)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
DB=bh_r_h9_11_mcpask; PORT=10051; P=h911
Q="What does the project hold?"
T=$(mktemp -d "$BH_WORK/h9-11-XXXXXX"); EV=""
cleanup() {
  [ -n "$EV" ] && kill "$EV" 2>/dev/null
  bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$T" "$BH_WORK/data-$DB"
}
trap cleanup EXIT

O=$(bh_svc_start "$DB" "$PORT") || { echo "OBSERVED: the service did not start (setup)"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_project "$O" "$P" >/dev/null
H=(-H "X-OpenFerment-Project: $P")
convs() { curl -s --noproxy '*' "$O/api/conversations" "${H[@]}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'; }
rows() { psql "$BH_SERVER/$DB" -tAXc "SELECT (SELECT count(*) FROM openferment.turns WHERE project_id='$P'),
                                             (SELECT count(*) FROM openferment.tool_calls WHERE project_id='$P')" | tr '|' ' '; }
turn_events() { grep -c '^event: turn\.' "$T/events.txt"; }

# The project's event stream, read for the whole run.
curl -sN --noproxy '*' --max-time 300 "$O/api/events" "${H[@]}" > "$T/events.txt" 2>/dev/null & EV=$!
sleep 1

c0=$(convs); read -r t0 k0 <<< "$(rows)"
echo "before: conversations=$c0 turns=$t0 tool_calls=$k0 turn_events=$(turn_events)"

# 1. ask_postdoc through the MCP server in its own process (no --service), on the same database.
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$BH_WORK/data-$DB" \
  .venv/bin/python - "$P" "$Q" > "$T/mcp.out" 2> "$T/mcp.err" <<'EOF'
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation
CORE = "/home/user/openFermentUI/core"
env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
async def go():
    p = StdioServerParameters(command=f"{CORE}/.venv/bin/python", cwd=CORE, env=env,
                              args=["-m", "openferment_core.mcp_server", "--project", sys.argv[1]])
    async with stdio_client(p) as (r, w), ClientSession(r, w, client_info=Implementation(name="h911bot", version="1")) as s:
        await s.initialize()
        got = json.loads((await s.call_tool("ask_postdoc", {"question": sys.argv[2]})).content[0].text)
        print(json.dumps({"question": got.get("question"), "declined": got.get("declined"),
                          "conversationId": got.get("conversationId"), "turnId": got.get("turnId")}))
asyncio.run(go())
EOF
)
echo "MCP ask_postdoc answered: $(cat "$T/mcp.out")"
sleep 1
c1=$(convs); read -r t1 k1 <<< "$(rows)"; e1=$(turn_events)
echo "after the MCP ask: conversations=$c1 turns=$t1 tool_calls=$k1 turn_events=$e1"

# 2. The same question at POST /api/ask.
curl -s --noproxy '*' -X POST "$O/api/ask" "${H[@]}" -H 'content-type: application/json' \
  -d "{\"question\":\"$Q\"}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("POST /api/ask answered:", json.dumps({k: d.get(k) for k in ("question","declined","conversationId","turnId")}))'
sleep 1
c2=$(convs); read -r t2 k2 <<< "$(rows)"; e2=$(turn_events)
echo "after POST /api/ask: conversations=$c2 turns=$t2 tool_calls=$k2 turn_events=$e2"

# The in-process branch, as the tree holds it.
echo "mcp_server.py, the in-process ask:"
grep -n "postdoc_agent.ask(" "$BH_ROOT/core/openferment_core/mcp_server.py" | sed 's/^/  /'
echo "api.py, the HTTP ask:"
grep -n "_conversations.begin(\|_ask_agent(question, on_step" "$BH_ROOT/core/openferment_core/api.py" | sed 's/^/  /'

echo "EXPECTED: the MCP ask kept as the REST ask is: one conversation and one turn after it, and turn events on the project's stream"
echo "OBSERVED: MCP ask -> conversations $c0->$c1, turns $t0->$t1, turn events $e1; REST ask -> conversations $c1->$c2, turns $t1->$t2, turn events $((e2 - e1))"
if [ -s "$T/mcp.out" ] && [ "$c1" = "$c0" ] && [ "$t1" = "$t0" ] && [ "$c2" -gt "$c1" ] && [ "$t2" -gt "$t1" ]; then
  echo "RESULT: DEFECT"
else
  [ -s "$T/mcp.out" ] || { echo "the MCP client said:"; tail -5 "$T/mcp.err"; }
  echo "RESULT: NO-DEFECT"
fi
exit 0
