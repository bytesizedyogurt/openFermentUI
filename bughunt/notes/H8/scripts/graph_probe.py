"""The concept graph's scoped reads over two projects that share a document, and one with none.

Usage (from core/): OPENFERMENT_DATABASE_URL=<bh_ test db> .venv/bin/python -I graph_probe.py SHARED_DOC PRIVATE_DOC
After share_probe.py: SHARED_DOC is the document gamma and delta both hold, PRIVATE_DOC gamma's own.
A build asks a model, so this writes the rows a build would write (four entities, three edges)
straight into the test database's kit tables, stamps the two chunks read, and then reads through
the MCP server's own graph tools (literature_mcp.build over kit.service('free')), for each project.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, ".")
import asyncpg  # noqa: E402

shared_doc, private_doc = sys.argv[1], sys.argv[2]
url = os.environ["OPENFERMENT_DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
assert "/bh_" in url, "a bh_ test database alone"


async def seed() -> None:
    conn = await asyncpg.connect(url)
    rows = await conn.fetch("SELECT id, document_id FROM sci_rag.chunks WHERE document_id = ANY($1)",
                            [shared_doc, private_doc])
    chunk = {r["document_id"]: r["id"] for r in rows}
    sc, pc = chunk[shared_doc], chunk[private_doc]
    await conn.execute("DELETE FROM sci_rag.kg_relationships")
    await conn.execute("DELETE FROM sci_rag.kg_entities")
    ents = {
        "corn stover": ("feedstock", "described from the shared passage", [sc], [shared_doc]),
        "xylanase": ("enzyme", "GAMMA-PRIVATE description written from gamma's own passage", [pc], [private_doc]),
        "glucose": ("chemical", "GAMMA-MIXED description written over both documents", [sc, pc],
                    [shared_doc, private_doc]),
        "saccharification": ("process", "described from the shared passage", [sc], [shared_doc]),
    }
    ids = {}
    for name, (kind, desc, chunks, docs) in ents.items():
        ids[name] = uuid.uuid4().hex
        await conn.execute("INSERT INTO sci_rag.kg_entities (id, name, entity_type, description, aliases, "
                           "document_ids, chunk_ids) VALUES ($1,$2,$3,$4,$5,$6,$7)",
                           ids[name], name, kind, desc, [], docs, chunks)
    edges = [("saccharification", "produces", "glucose", "the saccharification step releases glucose", sc, shared_doc),
             ("xylanase", "acts_on", "corn stover", "GAMMA-PRIVATE quote", pc, private_doc),
             ("glucose", "inhibits", "xylanase", "GAMMA-PRIVATE edge quote", pc, private_doc)]
    for s_, rel, t_, ev, ch, doc in edges:
        await conn.execute("INSERT INTO sci_rag.kg_relationships (id, source_entity_id, target_entity_id, "
                           "relation_type, evidence, confidence, document_id, chunk_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                           uuid.uuid4().hex, ids[s_], ids[t_], rel, ev, 0.9, doc, ch)
    await conn.execute("UPDATE sci_rag.chunks SET graph_extracted_at = now() WHERE id = ANY($1)", [sc, pc])
    await conn.close()


asyncio.run(seed())

from openferment_core import literature_mcp, projects  # noqa: E402
from openferment_core.literature import kit  # noqa: E402


async def read(project: str) -> None:
    os.environ[projects.ENV] = project
    server = literature_mcp.build(kit.service("free"))
    print(f"\n== {project}")
    for tool, args in (("search_entities", {"name_contains": ""}),
                       ("get_entity_relationships", {"entity_name": "glucose"}),
                       ("get_entity_relationships", {"entity_name": "xylanase"}),
                       ("corpus_stats", {})):
        try:
            got = await server.call_tool(tool, args)
            blocks = got[0] if isinstance(got, tuple) else got
            text = " ".join(getattr(b, "text", str(b)) for b in blocks)
        except Exception as e:  # a refusal in words is the answer
            text = f"REFUSED {type(e).__name__}: {e}"
        print(f"  {tool}({args}): {text[:900]}")


async def main() -> None:
    for p in ("gamma", "delta", "nothing"):
        await read(p)


asyncio.run(main())
