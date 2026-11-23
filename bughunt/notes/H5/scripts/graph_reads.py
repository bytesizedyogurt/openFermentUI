"""H5: the concept-graph reads of B and A over the hand-made graph of graph_rows.sql, through the sci-rag
MCP server (search_entities, get_entity_relationships, corpus_stats) and GET /api/literature/stats."""
import asyncio
import json
import os
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import call, j


async def reads(project):
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    params = StdioServerParameters(command=sys.executable, args=["-m", "openferment_core.literature_mcp", "--project", project],
                                   env=dict(os.environ), cwd="/home/user/openFermentUI/core")
    out = {}
    async with stdio_client(params) as streams, ClientSession(*streams) as s:
        await s.initialize()
        for name, args in (("search_entities", {"name_contains": ""}),
                           ("get_entity_relationships", {"entity_name": "Zymomonas xylofermentans"}),
                           ("get_entity_relationships", {"entity_name": "RACEMARKZQ"}),
                           ("get_entity_relationships", {"entity_name": "xylose"}),
                           ("corpus_stats", {})):
            res = await s.call_tool(name, args)
            out[f"{name} {json.dumps(args)}"] = " ".join(getattr(c, "text", "") for c in res.content)
    return out


# Set up: A pastes a note of its own; B pastes the text of A's 'A secret paper' (so B holds that document);
# then the hand-made graph rows (graph_rows.sql) on the database this process is pointed at.
import subprocess
TEXT = ("Zymomonas xylofermentans SECRETWORDA produced ethanol at a titre of 41 g/L from xylose in fed-batch culture.\n\n"
        "The second section says the strain SECRETWORDA tolerated 8 percent ethanol.")
print(j(call("POST", "/api/intake/paste", "bh-a", json={"title": "A graph note", "by": "alice",
      "text": "RACEMARKZQ appears in A's private race note, with xylose."})).get("status"))
print(j(call("POST", "/api/intake/paste", "bh-b", json={"title": "B's copy", "by": "bob", "text": TEXT})).get("status"))
url = os.environ["OPENFERMENT_DATABASE_URL"].replace("+asyncpg", "")
print(subprocess.run(["psql", url, "-X", "-q", "-f", os.path.join(os.path.dirname(__file__), "graph_rows.sql")],
                     capture_output=True, text=True).stderr or "graph rows written")
for p in ("bh-b", "bh-a"):
    print("=====", p)
    for k, v in asyncio.run(reads(p)).items():
        print("--", k, "\n", v[:1500])
    print("-- /api/literature/stats", j(call("GET", "/api/literature/stats", p)))
