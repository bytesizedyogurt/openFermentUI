"""The concept graph over a project's passages: the build, and the reads a
project makes of it (ADR-002).

Sci RAG Kit keeps one concept graph for its whole store. An entity is one row
a name (`kg_entities`), holding the chunks and the documents a model named it
in and the first description a model wrote of it; a relationship is one row an
edge (`kg_relationships`), holding its evidence quote and the chunk that quote
came from; a chunk a build has read is stamped. The kit's own build reads every
chunk the store holds, whoever collected it.

THE BUILD. `build` reads the project's chunks that no build has read
(`pending`: the chunks of the documents the project holds, in the kit's order,
the document's content hash and then the chunk's index), ten to a batch within
one document (`batches`), each batch through the kit's own batch step
(`_extract_with_recovery`): one model call on the client the caller hands in, a
batch whose answer cannot be read halved down to one chunk, a batch that fails
left unstamped for the next build. A batch ends where its document ends: the
kit writes one description a name from the whole batch and files each entity
and edge against the passage numbers the model names, so a batch of one
document keeps every word of its answer inside a document that each project
holding any of its passages holds whole. A chunk of a document two projects
hold is read once and serves both.
Each batch reads the entities it names, merges their chunk and document lists
in Python and writes them back, with no lock of the kit's own, so two builds at
once could each write a list read before the other committed and lose a
document; the entity would then keep the description that document's passage
produced, which the scoped reads below show only while the entity's document
list is whole. So every transaction a build's batches open first takes one
advisory lock (`GRAPH_LOCK`, `_GraphWrite`): the batches of every build write
one after another, each reading what the last committed. The model call comes
before the batch's transaction, so it stays outside the lock.
`literature/` imports no `llm`, so the command hands in the client and `stop`,
a predicate read after each batch: its words (no key, the account's usage
limit, the day's cap) end the build, and the chunks it had yet to read wait for
the next one. Both run on the database loop (`db.run`), on the kit's pooled
engine.

THE SCOPED READS. A project reads what its own passages prove, by the rule the
kit's retrieval follows when it seeds its graph walk under a scope (the kit's
`retrieve/stages/graph.py`): a name and a passage compared in lower case, each
run of other characters one space.

- An entity is the project's when one of its evidence chunks is a passage of a
  document the project holds and that passage names it; the names the kit
  holds as aliases find nothing here. Its passage count counts those passages.
- An entity's description is shown when a model wrote one and every document
  the entity is named in is one the project holds; the kit keeps one
  description a name. An entity listed with no description carries one note,
  the same whichever of the two left it out (`DESCRIPTION_NOTE`).
- A relationship is the project's when its evidence chunk is the project's and
  that passage names both its ends. Its quote is shown when its words stand in
  that passage, compared as a name is, and withheld with a note otherwise.
- The kit matches each name a build extracts against every entity's aliases
  across the store, so a name another project's build kept as an alias joins
  that entity at build time. Where the project's passage holds that name
  alone, its reads list neither the name nor the edges that passage states of
  it, so another project's name for the entity stays out of them.
- A count counts the project's passages alone.

Communities stay unbuilt: the kit reads none under a scope. Entity resolution
stays off: it merges rows every project reads, and a merged row is read by none
of these. `NO_GRAPH` is what a read says of a project whose passages no build
has read, and `NO_PASSAGES` what it says of a project that holds no passage.
"""
from __future__ import annotations

import asyncio
import itertools
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from sci_rag.db.models import Chunk, Document
from sci_rag.graph.extractor import _MAX_PASSAGE_CHARS, ExtractionStats, _extract_with_recovery
from sci_rag.llm.client import LLMClient
from sqlalchemy import Connection, Row, String, bindparam, event, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, SessionTransaction

from .. import db
from . import kit

#: What a read says of a project whose passages no build has read.
NO_GRAPH = ("No concept graph is built over this project's passages yet: `pnpm lit:graph --project {project} "
            "--by <name>` builds it on the index route's model.")
#: What a read says of a project that holds no passage: a store that holds no
#: project of the id, a project with no document, documents with no chunk.
NO_PASSAGES = ("The project {project} holds no passage yet: its documents enter on Intake, and `pnpm lit:graph "
               "--project {project} --by <name>` then builds the concept graph over their passages.")
#: The note beside every entity a read lists with no description.
DESCRIPTION_NOTE = ("A read shows the kit's one description of a name when a model wrote one and every document "
                    "naming the entity is one this project holds.")
#: The note beside an edge whose quote a read leaves out.
EVIDENCE_WITHHELD = "Withheld: the quote's words do not stand in the passage this edge cites."
#: The most entities one read lists, as the kit's own tool bounds it.
MOST = 100
#: The ceiling the kit's batch step asks for a batch's answer (`_extract_batch`).
ANSWER_TOKENS = 8192
#: The PostgreSQL advisory lock every build batch's transaction holds: one key
#: for the instance's one concept graph, the bytes of "of:graph".
GRAPH_LOCK = int.from_bytes(b"of:graph", "big")


class _GraphWrite(Session):
    """A session whose every transaction first waits for `GRAPH_LOCK` and
    holds it until the transaction ends."""


@event.listens_for(_GraphWrite, "after_begin")
def _take_the_graph_lock(session: Session, transaction: SessionTransaction, connection: Connection) -> None:
    connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": GRAPH_LOCK})


def _writer(factory: async_sessionmaker[AsyncSession]) -> async_sessionmaker[AsyncSession]:
    """Sessions on `factory`'s engine whose transactions hold `GRAPH_LOCK`."""
    return async_sessionmaker(factory.kw["bind"], expire_on_commit=False, sync_session_class=_GraphWrite)


def no_graph(project_id: str) -> str:
    return NO_GRAPH.format(project=project_id)


def no_passages(project_id: str) -> str:
    return NO_PASSAGES.format(project=project_id)


def unread(project_id: str, chunks: int) -> str:
    """What a read says of a project whose passages no build has read: that
    it holds none (`NO_PASSAGES`), else the command that builds its graph."""
    return no_passages(project_id) if not chunks else no_graph(project_id)


# ── the build ──────────────────────────────────────────────────────────────


@dataclass
class Built(ExtractionStats):
    """The kit's counts for one build (`ExtractionStats`: chunks read and
    stamped, batches failed and split, entities made and enriched,
    relationships made), with the chunks it set out to read, the batches it
    handed to the kit's step, and the words `stop` ended it with."""

    chunks_pending: int = 0
    batches_run: int = 0
    stopped: str | None = None

    @property
    def chunks_left(self) -> int:
        """The chunks this build set out to read and left unstamped: a batch
        that failed, and those after a stop."""
        return self.chunks_pending - self.chunks_processed


def _on_the_database_loop(what: str) -> None:
    if not db.on_database_thread():
        raise RuntimeError(f"graph.{what} runs on the database loop: hand it to db.run")


async def pending(project_id: str, *, rebuild: bool = False,
                  limit: int | None = None) -> list[Row[tuple[str, str, str]]]:
    """The project's chunks that no build has read, as the kit's batch step
    takes them (chunk id, document id, content), in the kit's order; with
    `rebuild`, every chunk the project holds; with `limit`, the first that
    many."""
    _on_the_database_loop("pending")
    documents = list((await kit.visible(project_id)).documents)
    if not documents:
        return []
    statement = (
        select(Chunk.id, Chunk.document_id, Chunk.content)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.document_id.in_(documents))
        .order_by(Document.content_hash, Chunk.chunk_index)
    )
    if not rebuild:
        statement = statement.where(Chunk.graph_extracted_at.is_(None))
    if limit is not None:
        if limit < 1:
            raise ValueError("a limit counts one passage at least")
        statement = statement.limit(limit)
    async with kit.service().session_factory() as session:
        return list((await session.execute(statement)).all())


async def build(project_id: str, *, llm: LLMClient, batch_size: int = 10, limit: int | None = None,
                rebuild: bool = False, rate_limit_s: float = 0.2,
                stop: Callable[[], str | None] | None = None) -> Built:
    """Read the project's pending chunks into the concept graph, `batch_size`
    to a batch within one document (`batches`), each through the kit's own
    batch step on `llm` (the kit's `extraction` role), its writes under
    `GRAPH_LOCK`. `stop` is read after
    each batch, and words from it end the build there (`Built.stopped`)."""
    if batch_size < 1:
        raise ValueError("a batch holds one chunk at least")
    rows = await pending(project_id, rebuild=rebuild, limit=limit)
    cut = list(batches(rows, batch_size=batch_size))
    built = Built(chunks_pending=len(rows))
    service = kit.service()
    writer = _writer(service.session_factory)
    for n, batch in enumerate(cut, start=1):
        await _extract_with_recovery(batch, writer, llm, service.domain, built, rate_limit_s=rate_limit_s)
        built.batches_run += 1
        words = stop() if stop is not None else None
        if words:
            built.stopped = words
            break
        if rate_limit_s and n < len(cut):
            await asyncio.sleep(rate_limit_s)
    return built


def batches(rows: Sequence[Row[tuple[str, str, str]]], *,
            batch_size: int = 10) -> Iterator[Sequence[Row[tuple[str, str, str]]]]:
    """`rows` in batches of `batch_size` at most, each within one document:
    a document's chunks stand together in the kit's order, and a batch ends
    where its document ends."""
    if batch_size < 1:
        raise ValueError("a batch holds one chunk at least")
    for _, same in itertools.groupby(rows, key=lambda row: row[1]):
        held = list(same)
        for start in range(0, len(held), batch_size):
            yield held[start:start + batch_size]


def prompts(rows: Sequence[Row[tuple[str, str, str]]], *, batch_size: int = 10) -> list[str]:
    """The prompt the kit's batch step writes for each batch of `rows`
    (`batches`), as `_extract_batch` renders it (each passage cut at the
    kit's length): what a dry run measures, with no model asked."""
    domain = kit.service().domain
    out = []
    for batch in batches(rows, batch_size=batch_size):
        passages = "\n\n".join(f"{i}. {content[:_MAX_PASSAGE_CHARS]}"
                                for i, (_, _, content) in enumerate(batch, start=1))
        out.append(domain.render_prompt("entity_extraction", DOMAIN_NAME=domain.name,
                                        ENTITY_TYPES=domain.entity_types_block(),
                                        RELATION_TYPES=domain.relation_types_block(), PASSAGES=passages))
    return out


# ── the reads ──────────────────────────────────────────────────────────────


def _words(column: str) -> str:
    """`column` as the kit compares a name with a passage (stages/graph.py):
    lower case, each run of other characters one space, trimmed."""
    return f"btrim(regexp_replace(lower({column}), '[^[:alnum:]]+', ' ', 'g'))"


# The project's passages, each with its words padded by a space, and each
# pairing of an entity with a passage of the project's that names it. `where`
# narrows the entities before any passage is read.
_PASSAGES = f"""
    mine AS MATERIALIZED (
        SELECT c.id, c.document_id, c.chunk_index, ' ' || {_words('c.content')} || ' ' AS words
        FROM chunks c
        WHERE c.document_id = ANY(:documents)
    )"""


def _named(where: str = "") -> str:
    return f"""
    named AS MATERIALIZED (
        SELECT e.id AS entity_id, mine.id AS chunk_id
        FROM kg_entities e
        CROSS JOIN LATERAL unnest(e.chunk_ids) AS evidence(chunk_id)
        JOIN mine ON mine.id = evidence.chunk_id
        WHERE e.canonical_entity_id IS NULL
          AND {_words('e.name')} <> ''
          AND position(' ' || {_words('e.name')} || ' ' IN mine.words) > 0
          {where}
    )"""


_PROVEN = """
    proven AS MATERIALIZED (SELECT DISTINCT entity_id FROM named)"""

# An edge `r` whose own passage names both its ends.
_BOTH_ENDS = """EXISTS (SELECT 1 FROM named ns WHERE ns.entity_id = r.source_entity_id AND ns.chunk_id = r.chunk_id)
              AND EXISTS (SELECT 1 FROM named nt WHERE nt.entity_id = r.target_entity_id AND nt.chunk_id = r.chunk_id)"""

_DOCUMENTS = bindparam("documents", type_=ARRAY(String()))


def _sql(statement: str, **types: Any) -> Any:
    return text(statement).bindparams(_DOCUMENTS, *(bindparam(k, type_=v) for k, v in types.items()))


async def _coverage(session: AsyncSession, documents: Sequence[str]) -> tuple[int, int]:
    """The project's passages, and those of them a build has read."""
    chunks, read = (await session.execute(_sql(
        "SELECT count(*), count(graph_extracted_at) FROM chunks WHERE document_id = ANY(:documents)"
    ), {"documents": list(documents)})).one()
    return int(chunks), int(read)


def _partly(project: str, chunks: int, read: int) -> str | None:
    if 0 < read < chunks:
        return (f"The concept graph covers {read} of this project's {chunks} passages: `pnpm lit:graph --project "
                f"{project} --by <name>` reads the rest.")
    return None


def _note(*parts: str | None) -> dict[str, str]:
    said = " ".join(p for p in parts if p)
    return {"note": said} if said else {}


async def entities(session_factory: async_sessionmaker[AsyncSession], documents: Sequence[str], *, project: str,
                   name_contains: str = "", entity_type: str | None = None, limit: int = 20) -> dict[str, Any]:
    """The entities the project's passages name whose name holds
    `name_contains` (case aside), of `entity_type` when one is named, by name,
    `limit` at most (the kit's `search_entities`, read under the module's
    rule): each with its type, its description where the rule shows it, and
    its passage count (`evidence_chunk_count`, the project's passages that
    name it)."""
    limit = max(1, min(limit, MOST))
    async with session_factory() as session:
        chunks, read = await _coverage(session, documents) if documents else (0, 0)
        if not read:
            return {"entities": [], **_note(unread(project, chunks))}
        where = "AND strpos(lower(e.name), lower(:needle)) > 0"
        params: dict[str, Any] = {"documents": list(documents), "needle": name_contains, "limit": limit}
        if entity_type:
            where += " AND e.entity_type = :entity_type"
            params["entity_type"] = entity_type
        rows = (await session.execute(_sql(f"""
            WITH {_PASSAGES}, {_named(where)}
            SELECT e.name, e.entity_type, e.description, e.document_ids <@ :documents AS described,
                   count(*) AS passages
            FROM named JOIN kg_entities e ON e.id = named.entity_id
            GROUP BY e.id
            ORDER BY e.name
            LIMIT :limit
        """), params)).all()
    found = []
    for name, kind, description, described, passages in rows:
        shown = description if described and description else None
        entry: dict[str, Any] = {"name": name, "type": kind, "description": shown,
                                 "evidence_chunk_count": int(passages)}
        if shown is None:
            entry["description_note"] = DESCRIPTION_NOTE
        found.append(entry)
    missing = None
    if not found:
        asked = [f"of type {entity_type}"] if entity_type else []
        asked += [f'whose name holds "{name_contains}"'] if name_contains else []
        missing = " ".join(["No entity", *asked, "is named in this project's passages."])
    return {"entities": found, **_note(missing, _partly(project, chunks, read))}


async def relationships(session_factory: async_sessionmaker[AsyncSession], documents: Sequence[str],
                        entity_name: str, *, project: str) -> dict[str, Any]:
    """Every relationship of the project's entity named `entity_name` (case
    aside, aliases left out) that the project holds, its passage naming both
    its ends, each with its statement, its quote where the module's rule
    shows it, its confidence, its chunk, and the document and passage
    (`p<index>`) it stands in (the kit's `get_entity_relationships`, read
    under the rule)."""
    async with session_factory() as session:
        chunks, read = await _coverage(session, documents) if documents else (0, 0)
        if not read:
            return {"entity": entity_name, "found": False, "hint": unread(project, chunks)}
        params = {"documents": list(documents), "name": entity_name}
        found = (await session.execute(_sql(f"""
            WITH {_PASSAGES}, {_named("AND lower(e.name) = lower(:name)")}
            SELECT e.id, e.name, e.entity_type
            FROM kg_entities e
            WHERE e.id IN (SELECT entity_id FROM named)
            ORDER BY e.name
            LIMIT 1
        """), params)).first()
        if found is None:
            return {"entity": entity_name, "found": False,
                    "hint": f'No entity named in this project\'s passages is called "{entity_name}": '
                            "search_entities lists the names they hold."}
        entity_id, name, kind = found
        edges = (await session.execute(_sql(f"""
            WITH {_PASSAGES}, {_named()}
            SELECT s.name, r.relation_type, t.name, r.evidence, r.confidence, r.chunk_id, mine.document_id,
                   mine.chunk_index,
                   coalesce({_words('r.evidence')} <> ''
                            AND position(' ' || {_words('r.evidence')} || ' ' IN mine.words) > 0, false) AS quoted
            FROM kg_relationships r
            JOIN mine ON mine.id = r.chunk_id
            JOIN kg_entities s ON s.id = r.source_entity_id
            JOIN kg_entities t ON t.id = r.target_entity_id
            WHERE :entity IN (r.source_entity_id, r.target_entity_id)
              AND {_BOTH_ENDS}
            ORDER BY s.name, r.relation_type, t.name, mine.document_id, mine.chunk_index, r.id
        """), {"documents": list(documents), "entity": entity_id})).all()
    listed = []
    for source, relation, target, evidence, confidence, chunk_id, document_id, index, quoted in edges:
        edge: dict[str, Any] = {
            "statement": f"{source} {relation} {target}", "evidence": evidence if quoted else None,
            "confidence": confidence, "chunk_id": chunk_id, "document_id": document_id,
            "passage_id": kit.passage_id(index),
        }
        if evidence and not quoted:
            edge["evidence_note"] = EVIDENCE_WITHHELD
        listed.append(edge)
    return {"entity": name, "found": True, "type": kind, "relationships": listed,
            **_note(_partly(project, chunks, read))}


async def counts(session_factory: async_sessionmaker[AsyncSession], documents: Sequence[str]) -> dict[str, Any]:
    """The project's concept graph in numbers, under the module's rule: its
    passages and those a build has read (`chunks`, `chunks_read`), the entities
    they name and the relationships they hold, each by type."""
    shape: dict[str, Any] = {"chunks": 0, "chunks_read": 0, "entities": 0, "relationships": 0, "entity_types": {},
                             "relation_types": {}}
    if not documents:
        return shape
    async with session_factory() as session:
        shape["chunks"], shape["chunks_read"] = await _coverage(session, documents)
        if not shape["chunks_read"]:
            return shape
        rows = (await session.execute(_sql(f"""
            WITH {_PASSAGES}, {_named()}, {_PROVEN}
            SELECT 'entity', e.entity_type, count(*)
            FROM proven JOIN kg_entities e ON e.id = proven.entity_id
            GROUP BY e.entity_type
            UNION ALL
            SELECT 'relationship', r.relation_type, count(*)
            FROM kg_relationships r
            JOIN mine ON mine.id = r.chunk_id
            WHERE {_BOTH_ENDS}
            GROUP BY r.relation_type
        """), {"documents": list(documents)})).all()
    for what, kind, n in rows:
        shape["entity_types" if what == "entity" else "relation_types"][kind] = int(n)
    shape["entity_types"] = dict(sorted(shape["entity_types"].items()))
    shape["relation_types"] = dict(sorted(shape["relation_types"].items()))
    shape["entities"] = sum(shape["entity_types"].values())
    shape["relationships"] = sum(shape["relation_types"].values())
    return shape
