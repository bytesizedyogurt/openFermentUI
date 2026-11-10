"""Cause check for H5-01, in process, against a database the service already set up (projects bh-a, bh-b
and the shared seed). Reads B's scope as _narrowed reads it, then has A paste a note, then retrieves with
that scope (the order a race gives), then with a scope read afresh."""
import sys
from openferment_core import db, intake
from openferment_core.literature import kit
from openferment_core import projects

MARK = "CAUSEMARKH501"
async def narrowed():
    with projects.using("bh-b"):
        return await kit._narrowed(None)

stale = db.run(narrowed())
print("B's scope read first: sources", stale.sources, "excluded", len(stale.exclude_document_ids))
out = intake.paste("A cause note", f"{MARK} is in A's private cause note.", project_id="bh-a", by="alice")
print("A pastes:", out.status, out.documentId)

async def retrieve(scope):
    return await kit.service().retriever.retrieve(f"{MARK} cause note", profile="interactive", limit=10, scope=scope)

r1 = db.run(retrieve(stale))
print("retrieval with the scope read before A's paste:", [i.document_id for i in r1.items if MARK in (i.content or "")])
fresh = db.run(narrowed())
r2 = db.run(retrieve(fresh))
print("retrieval with a scope read after:", [i.document_id for i in r2.items if MARK in (i.content or "")])
