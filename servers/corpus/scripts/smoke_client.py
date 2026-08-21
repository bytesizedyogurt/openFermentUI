"""Drive biorepo_mcp over real stdio and print the transcript.

Spawns the server as a subprocess, the way an MCP host would, then walks the
WHOLE declared surface: initialize, tools/list, health, both real read tools
(hit and deliberate miss), and all three declared refusals — whose isError
results are part of what this script proves, not a failure of it.

Run from servers/corpus/:  .venv/bin/python scripts/smoke_client.py
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
        args=["-m", "biorepo_mcp.server"],
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
            show("list_papers", await session.call_tool("list_papers", {}))
            show("get_paper M5 (hit)", await session.call_tool("get_paper", {"paper_id": "M5"}))
            show(
                "get_paper ZZ9 (miss)",
                await session.call_tool("get_paper", {"paper_id": "ZZ9"}),
            )
            show(
                "list_records paper_id=M5",
                await session.call_tool("list_records", {"paper_id": "M5"}),
            )
            show(
                "list_records ids=[nope-1] (miss carries a notice)",
                await session.call_tool("list_records", {"ids": ["nope-1"]}),
            )
            show(
                "search_papers (declared, must refuse)",
                await session.call_tool(
                    "search_papers", {"query": "what biomass density is achievable?"}
                ),
            )
            show(
                "get_scope (declared, must refuse)",
                await session.call_tool("get_scope", {"config": {"density": 2.0}}),
            )
            show(
                "get_whitespace (declared, must refuse)",
                await session.call_tool("get_whitespace", {}),
            )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
