"""The sci-rag MCP server's document tools across projects (no model asked).

Usage (from core/): OPENFERMENT_DATABASE_URL=<bh_ db> .venv/bin/python -I mcp_scope.py PRIVATE_DOC SHARED_DOC
Reads, in projects delta, gamma and nothing: get_document and get_citations of gamma's private
document and of the shared one, search_corpus for the private passage's words, list_sources.
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, ".")
from openferment_core import literature_mcp, projects  # noqa: E402
from openferment_core.literature import kit  # noqa: E402

private_doc, shared_doc = sys.argv[1], sys.argv[2]


async def main() -> None:
    server = literature_mcp.build(kit.service("free"))
    tools = [t.name for t in await server.list_tools()]
    print("tools:", tools)
    for p in ("delta", "gamma", "nothing"):
        os.environ[projects.ENV] = p
        print(f"\n== {p}")
        for tool, args in (("get_document", {"document_id": private_doc}),
                           ("get_document", {"document_id": shared_doc}),
                           ("get_citations", {"document_id": private_doc}),
                           ("search_corpus", {"query": "xylanase loading private passage", "profile": "interactive"}),
                           ("list_sources", {})):
            try:
                got = await server.call_tool(tool, args)
                blocks = got[0] if isinstance(got, tuple) else got
                text = " ".join(getattr(b, "text", str(b)) for b in blocks)
                text = text.replace("\n", " ")
            except Exception as e:  # a refusal in words is the answer
                text = f"REFUSED {type(e).__name__}: {e}"
            print(f"  {tool}({list(args.values())[:1]}): {text[:400]}")


asyncio.run(main())
