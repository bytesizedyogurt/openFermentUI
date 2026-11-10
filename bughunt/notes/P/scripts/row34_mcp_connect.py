"""Row 34 (2d488fb, 85c7a26): both MCP servers of .mcp.json connect at a session's start and answer over stdio.
Each server is started with the exact command .mcp.json names (uv run --project core --all-extras python -m ...),
from the repository's root, keyless, its database a test database, and timed to `initialize` and to `tools/list`.
Claude Code gives a stdio server 30 s to connect (MCP_TIMEOUT); this session's own start saw both time out.

usage: bh_py row34_mcp_connect.py DATABASE_URL [ROUNDS]
"""
import asyncio
import json
import os
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

URL = sys.argv[1]
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 1
ROOT = "/home/user/openFermentUI"
CONFIG = json.load(open(f"{ROOT}/.mcp.json"))["mcpServers"]


async def once(name: str) -> tuple[float, float, int]:
    spec = CONFIG[name]
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["OPENFERMENT_DATABASE_URL"] = URL
    params = StdioServerParameters(command=spec["command"], args=spec["args"], cwd=ROOT, env=env)
    t0 = time.monotonic()
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        t1 = time.monotonic()
        tools = (await s.list_tools()).tools
        t2 = time.monotonic()
    return t1 - t0, t2 - t0, len(tools)


for i in range(ROUNDS):
    for name in CONFIG:
        try:
            init, listed, n = asyncio.run(once(name))
            print(f"round {i + 1} {name}: initialize {init:.1f} s, tools/list {listed:.1f} s, {n} tools")
        except Exception as e:  # noqa: BLE001
            print(f"round {i + 1} {name}: {type(e).__name__}: {str(e)[:200]}")
