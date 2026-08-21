"""Drive geneos_mcp over real stdio and print the transcript.

Spawns the server as a subprocess, the way an MCP host would, then walks the
WHOLE declared surface: initialize, tools/list, health, the three real read
tools (hit and deliberate miss), and the one declared refusal — whose isError
result is part of what this script proves, not a failure of it.

Run from servers/cell/:  .venv/bin/python scripts/smoke_client.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_DIR = Path(__file__).resolve().parents[1]
#: Trim long payloads so the transcript stays readable; the tools that matter
#: for shape are short, and the ones that are long are long because the corpus
#: is real.
MAX_CHARS = 1200


def show(label: str, result) -> None:
    print(f"\n=== {label} ===")
    if getattr(result, "isError", False):
        print("isError: true")
    for block in result.content:
        text = getattr(block, "text", None)
        if text is None:
            continue
        print(text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + "\n… truncated")


async def main() -> None:
    params = StdioServerParameters(
        command=str(SERVER_DIR / ".venv" / "bin" / "python"),
        args=["-m", "geneos_mcp.server"],
        cwd=str(SERVER_DIR),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("=== initialize ===")
            print(
                json.dumps(
                    {
                        "serverInfo": init.server_info.model_dump(
                            mode="json", exclude_none=True
                        ),
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
            show("list_strains", await session.call_tool("list_strains", {}))
            show("get_strain cw15 (hit)", await session.call_tool("get_strain", {"strain_id": "cw15"}))
            show(
                "get_strain nope (miss)",
                await session.call_tool("get_strain", {"strain_id": "nope"}),
            )
            show(
                "get_strain_records treesei",
                await session.call_tool("get_strain_records", {"strain_id": "treesei"}),
            )
            show(
                "get_strain_records nope (unknown host, notice says so)",
                await session.call_tool("get_strain_records", {"strain_id": "nope"}),
            )
            show(
                "predict_flux (declared, must refuse)",
                await session.call_tool(
                    "predict_flux", {"strain_id": "cw15", "objective": "BIOMASS_Chlamy_auto"}
                ),
            )

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
