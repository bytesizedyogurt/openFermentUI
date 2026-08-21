"""Drive fermos_mcp over real stdio and print the transcript.

Spawns the server as a subprocess (the same way an MCP host would), then walks
the whole declared surface: initialize, tools/list, the health tool, both real
tools (hit and deliberate miss), and both stubs — which must REFUSE, so their
isError results are part of what this script proves, not a failure of it.

Run from servers/process/:  .venv/bin/python scripts/smoke_client.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_DIR = Path(__file__).resolve().parents[1]


def show(label: str, result) -> None:
    print(f"\n=== {label} ===")
    is_error = getattr(result, "isError", False)
    if is_error:
        print("isError: true")
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            print(text)


async def main() -> None:
    params = StdioServerParameters(
        command=str(SERVER_DIR / ".venv" / "bin" / "python"),
        args=["-m", "fermos_mcp.server"],
        cwd=str(SERVER_DIR),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("=== initialize ===")
            print(
                json.dumps(
                    {
                        "serverInfo": init.server_info.model_dump(mode="json", exclude_none=True),
                        "protocolVersion": init.protocol_version,
                    },
                    indent=2,
                )
            )

            tools = await session.list_tools()
            print("\n=== tools/list ===")
            for t in tools.tools:
                print(f"- {t.name}: {(t.description or '').splitlines()[0]}")

            show("health", await session.call_tool("health", {}))
            show("list_scenarios", await session.call_tool("list_scenarios", {}))
            show(
                "get_scenario sc-s2 (hit)",
                await session.call_tool("get_scenario", {"scenario_id": "sc-s2"}),
            )
            show(
                "get_scenario sc-s9 (miss)",
                await session.call_tool("get_scenario", {"scenario_id": "sc-s9"}),
            )
            show(
                "submit_evaluation (stub, must refuse)",
                await session.call_tool(
                    "submit_evaluation",
                    {"params": {"scenarioId": "sc-s1", "config": {"density": 2.0}}},
                ),
            )
            show(
                "get_evaluation (stub, must refuse)",
                await session.call_tool("get_evaluation", {"job_id": "job-000"}),
            )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
