#!/usr/bin/env bash
# H9: the same question through POST /api/ask and through the openferment MCP server in its
# own process; the project's conversations counted after each. Keyless: both asks decline.
#   mcp_ask_turn.sh PORT
source /home/user/openFermentUI/bughunt/lib/env.sh
port="$1"; O=$(bh_svc_start bh_h9_mcpask "$port") || exit 1; bh_project "$O" pa >/dev/null
count() { curl -s --noproxy '*' "$O/api/conversations" -H 'X-OpenFerment-Project: pa' | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'; }
echo "before: $(count)"
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h9_mcpask" .venv/bin/python - <<'EOF' 2>/dev/null
import asyncio, json, os
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
CORE = "/home/user/openFermentUI/core"
env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
async def go():
    p = StdioServerParameters(command=f"{CORE}/.venv/bin/python", cwd=CORE, env=env,
                              args=["-m", "openferment_core.mcp_server", "--project", "pa"])
    async with stdio_client(p) as (r, w), ClientSession(r, w, client_info=types.Implementation(name="askbot", version="1")) as s:
        await s.initialize()
        got = await s.call_tool("ask_postdoc", {"question": "What does the project hold?"})
        print("MCP ask declined:", json.loads(got.content[0].text).get("declined"))
asyncio.run(go())
EOF
)
echo "after the MCP ask: $(count)"
curl -s --noproxy '*' -X POST "$O/api/ask" -H 'X-OpenFerment-Project: pa' -H 'content-type: application/json' \
  -d '{"question":"What does the project hold?"}' >/dev/null
echo "after POST /api/ask: $(count)"
bh_svc_stop "$port"; bh_db_drop bh_h9_mcpask
