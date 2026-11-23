"""Row 4 (19d129a): the sci-rag server's search_entities and get_entity_relationships read the project's graph
alone. A graph is written straight into a test database's kit tables, as a build would leave it (one entity and
edge on project pa's passage, one entity on pb's), every passage marked read, and the sci-rag server is asked over
stdio, as .mcp.json starts it, in each project.

usage: bh_py row04_graph_scope.py DATABASE_URL PA_DOC PB_DOC
"""
import asyncio
import json
import os
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

URL, PA_DOC, PB_DOC = sys.argv[1:4]


def sql(q: str) -> str:
    return subprocess.run(["psql", URL, "-XAtc", q], text=True, capture_output=True, check=True).stdout.strip()


pa_chunk = sql(f"select id from sci_rag.chunks where document_id='{PA_DOC}' and content ilike '%rice straw%' limit 1")
pb_chunk = sql(f"select id from sci_rag.chunks where document_id='{PB_DOC}' limit 1")
sql("delete from sci_rag.kg_relationships; delete from sci_rag.kg_entities")
sql(f"""insert into sci_rag.kg_entities (id,name,entity_type,description,aliases,document_ids,chunk_ids) values
 ('e_pa_1','rice straw','feedstock','pa-only description','{{}}','{{{PA_DOC}}}','{{{pa_chunk}}}'),
 ('e_pa_2','Colusa','location','pa-only description two','{{}}','{{{PA_DOC}}}','{{{pa_chunk}}}'),
 ('e_pb_1','zyxwort moss','organism','pb-only description','{{}}','{{{PB_DOC}}}','{{{pb_chunk}}}'),
 ('e_pb_2','quillstone ponds','location','pb-only description two','{{}}','{{{PB_DOC}}}','{{{pb_chunk}}}')""")
sql(f"""insert into sci_rag.kg_relationships (id,source_entity_id,target_entity_id,relation_type,evidence,confidence,
 document_id,chunk_id) values
 ('r_pa','e_pa_1','e_pa_2','located_in','rice straw','0.9','{PA_DOC}','{pa_chunk}'),
 ('r_pb','e_pb_1','e_pb_2','grows_near','zyxwort moss grows near quillstone ponds','0.9','{PB_DOC}','{pb_chunk}')""")
sql("update sci_rag.chunks set graph_extracted_at = now()")


async def ask(project: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["OPENFERMENT_DATABASE_URL"] = URL
    params = StdioServerParameters(command=sys.executable, cwd="/home/user/openFermentUI/core", env=env,
                                   args=["-m", "openferment_core.literature_mcp", "--project", project])
    out = {}
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        out["tools"] = sorted(t.name for t in (await s.list_tools()).tools)
        for name, args in [("search_entities", {"name_contains": ""}),
                           ("search_entities", {"name_contains": "zyx"}),
                           ("search_entities", {"name_contains": "rice"}),
                           ("get_entity_relationships", {"entity_name": "rice straw"}),
                           ("get_entity_relationships", {"entity_name": "zyxwort moss"})]:
            res = await s.call_tool(name, args)
            out[f"{name} {json.dumps(args)}"] = res.content[0].text if res.content else None
    return out


for p in ("pa", "pb"):
    print("=== project", p)
    for k, v in asyncio.run(ask(p)).items():
        print(k, "->", v if isinstance(v, list) else (v or "")[:400])
