"""Sci RAG Kit as openFerment runs it (ADR-002; execution prompt §8.2).

The kit does the literature work: it parses and chunks a document, embeds the
chunks, stores them in schema `sci_rag`, retrieves over five layers and writes
cited answers. This module builds its objects once per process and decides
what each project sees. Every kit object is handed FastEmbed for vectors and
the model client the composition root installed (`install_model`: the
service installs `llm.kit_client`, so every model call the kit makes goes
through llm.py, under the day's cap). `literature/` imports no `llm` (§7.2).

THE PROJECT IS THE SCOPE. A document a project collects is stored with source
`project:<id>:<collector>` (`source`), and `documents_link` holds a row for
each project that holds it, with the selection that brought it in. A document
the kit already holds (the same text, whoever collected it) is linked, not
stored again, so `documents_link` is the authority on who holds what. Every
read a project makes is narrowed to its linked documents: their sources go to
the kit as its `sources` allowlist, and every other document from those
sources as `exclude_document_ids` (`visible`). A project that holds nothing
sees nothing; the kit denies an empty allowlist outright.

`ProjectService` is the kit's own `RagService` with that narrowing applied to
every read, so the calls below, the kit's REST app at /rag (`rest_app`) and
its MCP server (`mcp.py`) answer alike for one project. A request to /rag
names its project as every /api request does (api.py); the MCP server acts in
OPENFERMENT_PROJECT.

TWO KINDS OF ENGINE. asyncpg ties a connection to the event loop that opened
it. The calls openFerment makes run on the database loop (`db.run`) through a
pooled engine, which is also installed as the kit's own so its ingester uses
it. /rag and the MCP server run on loops of their own and get an engine that
keeps no connection between sessions. Which documents a project holds is
always read through openFerment's own session (`db.session`), the one a
test's transaction binds.
"""
from __future__ import annotations

import dataclasses
import json
import os
import secrets
import threading
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar

from sci_rag.answer import AnswerEngine
from sci_rag.config import Settings
from sci_rag.db import engine as kit_engine
from sci_rag.db import models as kit_models
from sci_rag.db.models import Chunk, Document, DocumentCitation
from sci_rag.domain import load_domain
from sci_rag.embed.provider import EmbeddingProvider
from sci_rag.ingest.ingester import IngestOutcome, ingest_entries
from sci_rag.ingest.manifest import CorpusEntry
from sci_rag.llm.client import LLMClient
from sci_rag.retrieve import Retriever
from sci_rag.retrieve.types import RetrievalResult, RetrievalScope
from sci_rag.server.errors import ApiError
from sci_rag.server.service import RagService
from sqlalchemy import Column, MetaData, String, Table, Text, func, pool, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from .. import db, projects
from ..db import models as t
from . import DOMAIN_DIR, EMBEDDING_CACHE, EMBEDDING_DIM, EMBEDDING_MODEL, HERE
from .fastembed import FastEmbedProvider

T = TypeVar("T")

#: The kit's tables, and the search path its engines are given: its own schema
#: first, then `public`, where the vector extension keeps its type.
SCHEMA = "sci_rag"
SEARCH_PATH = f"{SCHEMA}, public"
#: The kit's six migrations, vendored with its licence (kit_alembic/).
MIGRATIONS = HERE / "kit_alembic"
#: Where a document came from: the last part of its source.
COLLECTORS = ("europepmc", "osti", "sgd", "upload", "paste")
#: The key a client of /rag sends (`Authorization: Bearer <key>`), from
#: core/.env. With none set, /rag still asks for a key, and accepts none.
RAG_KEY = "OPENFERMENT_RAG_KEY"
#: What that key may do: search, answer and read the catalogue. A model key of
#: the caller's own (the kit's `byo_llm`) is not among them: the model is
#: reached through llm.py alone.
RAG_SCOPES = ("retrieval:query", "retrieval:answer", "corpus:read")

if kit_models.EMBEDDING_DIM != EMBEDDING_DIM:
    raise ImportError(
        f"sci_rag.db.models was imported with dimension {kit_models.EMBEDDING_DIM}, not {EMBEDDING_DIM}: "
        "the kit was imported before openferment_core.literature set its settings"
    )

# The kit's `documents` table, as openFerment's own session reads it: that
# session's search path is `public`, so the schema is named.
_documents = Table(
    "documents",
    MetaData(schema=SCHEMA),
    Column("id", String(32), primary_key=True),
    Column("source", Text),
)


class KitUnavailable(RuntimeError):
    """A kit call needs a model and none is installed."""


def source(project_id: str, collector: str) -> str:
    """The kit's `source` for a document `project_id` collected."""
    if collector not in COLLECTORS:
        raise ValueError(f"unknown collector {collector!r}; the collectors are {', '.join(COLLECTORS)}")
    return f"project:{project_id}:{collector}"


# ── settings, model and embedder ───────────────────────────────────────────


_LOCK = threading.RLock()
_STATE: dict[str, Any] = {}
_MODEL: Callable[[str], LLMClient] | None = None
# Counts the times the kit's engines were closed or its embedder changed, so
# what was built on them (the /rag app) knows to build again.
_GENERATION = 0


def generation() -> int:
    return _GENERATION


def install_model(factory: Callable[[str], LLMClient] | None) -> None:
    """The model client the kit generates with, by the kit's role (`answer`,
    `extraction`, `judge`). The composition root installs it; None removes
    it, and a kit call that needs a model then refuses in words."""
    global _MODEL
    _MODEL = factory


def model(role: str = "answer") -> LLMClient:
    if _MODEL is None:
        raise KitUnavailable("no model client is installed for the literature layer (the service installs llm.kit_client)")
    return _MODEL(role)


class _ModelOnDemand(LLMClient):
    """The installed model client, looked up each time the kit generates: a
    search that generates nothing needs none, and a client installed after
    the service was built is the one used."""

    def __init__(self, role: str) -> None:
        self.role = role

    def describe(self) -> str:
        return model(self.role).describe() if _MODEL is not None else "none installed"

    async def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2,
                       max_tokens: int = 2048, json_mode: bool = False) -> str:
        return await model(self.role).generate(
            prompt, system=system, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode
        )

    def stream(self, prompt: str, *, system: str | None = None, temperature: float = 0.2,
               max_tokens: int = 2048) -> AsyncIterator[str]:
        return model(self.role).stream(prompt, system=system, temperature=temperature, max_tokens=max_tokens)

    async def generate_json(self, prompt: str, *, system: str | None = None, max_tokens: int = 4096) -> Any:
        return await model(self.role).generate_json(prompt, system=system, max_tokens=max_tokens)


def use_database(url: URL | str | None) -> None:
    """Point the kit at `url` (the tests' database, a command's own) in place
    of OPENFERMENT_DATABASE_URL; None goes back to it. Closes the engines made
    for the old address."""
    dispose()
    with _LOCK:
        if url is None:
            _STATE.pop("url", None)
        else:
            _STATE["url"] = db.as_async(url)


def _url() -> URL:
    held = _STATE.get("url")
    return held if held is not None else db.database_url()


def _api_keys() -> str:
    """The kit's key map for /rag. With no key in core/.env, one made here and
    never shown, so /rag refuses every request; the kit given no keys at all
    would answer every request open."""
    key = os.environ.get(RAG_KEY, "").strip() or secrets.token_urlsafe(32)
    return json.dumps({key: {"scopes": list(RAG_SCOPES)}})


class _Settings(Settings):
    """The kit's settings from the values given and the kit's defaults alone:
    neither the environment's SCI_RAG_* names nor a .env in the working
    directory reach them."""

    @classmethod
    def settings_customise_sources(cls, settings_cls: Any, init_settings: Any, *_: Any, **__: Any) -> tuple[Any, ...]:
        return (init_settings,)


def settings() -> Settings:
    """The kit's settings, from openFerment's values and the kit's defaults."""
    with _LOCK:
        held = _STATE.get("settings")
        if held is None:
            held = _Settings(
                database_url=_url().render_as_string(hide_password=False),
                embedding_provider="local-hash",
                embedding_model=EMBEDDING_MODEL,
                embedding_dim=EMBEDDING_DIM,
                domain_dir=DOMAIN_DIR,
                api_keys=_api_keys(),
                # /rag serves this machine; no other origin is invited to read it.
                cors_origins="",
            )
            _STATE["settings"] = held
        return held


def embedder() -> FastEmbedProvider:
    """FastEmbed, built once; its model loads on the first text it embeds."""
    with _LOCK:
        held = _STATE.get("embedder")
        if held is None:
            held = _STATE["embedder"] = FastEmbedProvider(EMBEDDING_MODEL, dim=EMBEDDING_DIM, cache_dir=EMBEDDING_CACHE)
        return held


def use_embedder(provider: EmbeddingProvider | None) -> None:
    """Embed with `provider` in place of FastEmbed; None goes back to it. The
    tests outside the `lit` marker embed with the kit's deterministic local
    one, which needs no model file."""
    global _GENERATION
    with _LOCK:
        held = _STATE.get("embedder")
        if provider is None and (held is None or isinstance(held, FastEmbedProvider)):
            return
        if provider is not None and held is provider:
            return
        if provider is None:
            _STATE.pop("embedder", None)
        else:
            _STATE["embedder"] = provider
        for key in ("loop_service", "free_service"):
            _STATE.pop(key, None)
        _GENERATION += 1


def _answer_for_the_kit() -> None:
    """The kit's own factories answer with openFerment's embedder and model,
    for any kit path that asks them rather than using what it was handed
    (ADR-002). The names its modules imported are replaced as well."""
    import sci_rag.answer.generator as generator
    import sci_rag.embed as embed
    import sci_rag.llm as kit_llm
    import sci_rag.retrieve.retriever as retriever

    def get_embedder(_settings: Any = None) -> FastEmbedProvider:
        return embedder()

    def get_llm(_settings: Any = None, *, role: str = "answer", api_key_override: str | None = None,
                **_: Any) -> LLMClient:
        if api_key_override:
            raise KitUnavailable("a model key of the caller's own is not accepted; the model is reached through llm.py")
        return _ModelOnDemand(role)

    for module in (embed, retriever):
        module.get_embedder = get_embedder  # type: ignore[attr-defined]
    for module in (kit_llm, retriever, generator):
        module.get_llm = get_llm  # type: ignore[attr-defined]


# ── engines and services ───────────────────────────────────────────────────


def _engine(kind: str) -> AsyncEngine:
    """'loop': pooled, used on the database loop alone, and the kit's own.
    'free': no pool, for a loop of its own (/rag, the MCP server)."""
    with _LOCK:
        held = _STATE.get(f"{kind}_engine")
        if held is None:
            if kind == "loop":
                held = db.make_engine(_url(), search_path=SEARCH_PATH, pool_size=5, max_overflow=5, pool_pre_ping=True)
                kit_engine._engine = held
                kit_engine._session_factory = async_sessionmaker(held, expire_on_commit=False)
            else:
                held = db.make_engine(_url(), search_path=SEARCH_PATH, poolclass=pool.NullPool)
            _STATE[f"{kind}_engine"] = held
        return held


def service(kind: str = "loop") -> ProjectService:
    """The kit's service in this process: 'loop' for the calls made through
    `db.run`, 'free' for /rag and the MCP server."""
    with _LOCK:
        held = _STATE.get(f"{kind}_service")
        if held is None:
            _answer_for_the_kit()
            s = settings()
            retriever = Retriever(
                settings=s,
                domain=load_domain(DOMAIN_DIR),
                embedder=embedder(),
                llm=_ModelOnDemand("extraction"),
                session_factory=async_sessionmaker(_engine(kind), expire_on_commit=False),
            )
            held = _STATE[f"{kind}_service"] = ProjectService(
                settings=s, retriever=retriever,
                answer_engine=AnswerEngine(settings=s, retriever=retriever, llm=_ModelOnDemand("answer")),
            )
        return held


def dispose() -> None:
    """Close the kit's engines and forget what was built on them."""
    global _GENERATION
    with _LOCK:
        _GENERATION += 1
        engines = [_STATE.pop(k) for k in ("loop_engine", "free_engine") if k in _STATE]
        for key in ("loop_service", "free_service", "settings"):
            _STATE.pop(key, None)
        if kit_engine._engine in engines:
            kit_engine._engine = None
            kit_engine._session_factory = None
    for e in engines:
        db.run(e.dispose())


# ── which documents a project sees ─────────────────────────────────────────


async def _on_db(coro: Coroutine[Any, Any, T]) -> T:
    """Await `coro` on the database loop, from that loop or another."""
    if db.on_database_thread():
        return await coro
    return await db.arun(coro)


@dataclass(frozen=True)
class Visible:
    """What one project sees of the kit."""

    documents: tuple[str, ...]
    sources: tuple[str, ...]
    excluded: tuple[str, ...]


async def visible(project_id: str) -> Visible:
    """The project's documents, their sources, and the other documents those
    sources hold: another project's, where it shares a document with this one."""
    link = t.documents_link
    async with db.session() as s:
        held = [r[0] for r in (await s.execute(
            select(link.c.document_id).where(link.c.project_id == project_id).order_by(link.c.document_id)
        )).all()]
        if not held:
            return Visible((), (), ())
        sources = sorted(r[0] for r in (await s.execute(
            select(_documents.c.source).where(_documents.c.id.in_(held)).distinct()
        )).all())
        mine = set(held)
        others = sorted(r[0] for r in (await s.execute(
            select(_documents.c.id).where(_documents.c.source.in_(sources))
        )).all() if r[0] not in mine)
    return Visible(tuple(held), tuple(sources), tuple(others))


async def linked(project_id: str, document_id: str) -> dict[str, Any] | None:
    """The link row of a document the project holds, or None."""
    link = t.documents_link
    async with db.session() as s:
        row = (await s.execute(
            select(link).where(link.c.project_id == project_id, link.c.document_id == document_id)
        )).mappings().first()
    return dict(row) if row else None


async def _link(project_id: str, document_id: str, selection: dict[str, Any], by: str) -> bool:
    """Link a document to a project: False when the project held it already,
    and the first selection stays."""
    async with db.session() as s:
        result = await s.execute(
            pg_insert(t.documents_link)
            .values(project_id=project_id, document_id=document_id, selection=selection, created_by=by)
            .on_conflict_do_nothing(index_elements=["project_id", "document_id"])
        )
        return bool(result.rowcount)


def _project() -> str:
    found = projects.current_or_none()
    if found is None:
        raise ApiError(
            422, "project_required", "No project named",
            f"Name the project in the {projects.HEADER} header, or set {projects.ENV} for a command.",
        )
    return found


async def _narrowed(base: RetrievalScope | None) -> RetrievalScope:
    seen = await _on_db(visible(_project()))
    scope = base or RetrievalScope()
    sources = seen.sources if scope.sources is None else tuple(x for x in scope.sources if x in seen.sources)
    return dataclasses.replace(
        scope, sources=sources, exclude_document_ids=tuple(sorted({*scope.exclude_document_ids, *seen.excluded}))
    )


async def _held(document_id: str) -> None:
    if await _on_db(linked(_project(), document_id)) is None:
        raise ApiError(404, "document_not_found", "No such document", document_id)


class ProjectService(RagService):
    """The kit's service, with every read inside the current project."""

    async def retrieve(self, query: str, *, profile: str = "interactive", top_k: int = 8,
                       license_classes: list[str] | None = None, sources: list[str] | None = None,
                       year_min: int | None = None, year_max: int | None = None,
                       authors: list[str] | None = None, journals: list[str] | None = None,
                       exclude_dois: list[str] | None = None, include_graph: bool | None = None,
                       include_community: bool | None = None, include_hyde: bool | None = None,
                       include_rerank: bool | None = None) -> RetrievalResult:
        scope = await _narrowed(self.scope_from(
            license_classes, sources, year_min=year_min, year_max=year_max, authors=authors,
            journals=journals, exclude_dois=exclude_dois,
        ))
        return await self.retriever.retrieve(
            query, profile=profile, limit=top_k, scope=scope, include_graph=include_graph,
            include_community=include_community, include_hyde=include_hyde, include_rerank=include_rerank,
        )

    def answer_stream(self, query: str, *, profile: str = "deep", top_k: int = 8, max_tokens: int = 2048,
                      license_classes: list[str] | None = None, sources: list[str] | None = None,
                      year_min: int | None = None, year_max: int | None = None,
                      authors: list[str] | None = None, journals: list[str] | None = None,
                      exclude_dois: list[str] | None = None, api_key_override: str | None = None,
                      include_compression: bool | None = None) -> AsyncIterator[Any]:
        if api_key_override:
            raise ApiError(403, "own_model_key_refused", "A model key of the caller's own is not accepted",
                           "The model is reached through openFerment's llm.py alone.")
        base = self.scope_from(
            license_classes, sources, year_min=year_min, year_max=year_max, authors=authors,
            journals=journals, exclude_dois=exclude_dois, exclude_retracted=True,
        )

        async def events() -> AsyncIterator[Any]:
            scope = await _narrowed(base)
            async for event in self.engine.answer_stream(
                query, profile=profile, limit=top_k, max_tokens=max_tokens, scope=scope,
                include_compression=include_compression,
            ):
                yield event

        return events()

    async def list_documents(self, *, page: int = 1, page_size: int = 20, search: str | None = None,
                             source: str | None = None, license_class: str | None = None) -> tuple[list[Document], int]:
        seen = await _on_db(visible(_project()))
        conditions = [Document.id.in_(seen.documents)]
        if search:
            conditions.append(Document.title.ilike(f"%{search}%"))
        if source:
            conditions.append(Document.source == source)
        if license_class:
            conditions.append(Document.license_class == license_class)
        async with self.session_factory() as session:
            total = await session.scalar(select(func.count(Document.id)).where(*conditions))
            rows = (await session.execute(
                select(Document).where(*conditions).order_by(Document.ingested_at.desc(), Document.id)
                .offset((page - 1) * page_size).limit(page_size)
            )).scalars().all()
        return list(rows), int(total or 0)

    async def get_document(self, document_id: str, *, preview_chunks: int = 8,
                           preview_chars: int = 240) -> tuple[Document, list[Chunk]]:
        await _held(document_id)
        return await super().get_document(document_id, preview_chunks=preview_chunks, preview_chars=preview_chars)

    async def get_citations(self, document_id: str) -> dict[str, Any]:
        """The document's references and the documents citing it; another
        document is named only when the project holds it too."""
        await _held(document_id)
        found = await super().get_citations(document_id)
        mine = set((await _on_db(visible(_project()))).documents)
        for ref in found["references"]:
            if ref["document_id"] is not None and ref["document_id"] not in mine:
                ref.update(document_id=None, title=None, resolved=False)
        found["cited_by"] = [c for c in found["cited_by"] if c["document_id"] in mine]
        return found

    async def stats(self) -> dict[str, Any]:
        """The project's documents and chunks. The concept graph (entities,
        relationships, communities) is the instance's, counted whole."""
        counts = await super().stats()
        ids = (await _on_db(visible(_project()))).documents
        async with self.session_factory() as session:
            counts["documents"] = len(ids)
            counts["chunks"] = int(await session.scalar(
                select(func.count(Chunk.id)).where(Chunk.document_id.in_(ids))) or 0)
            counts["citations"] = int(await session.scalar(
                select(func.count(DocumentCitation.id)).where(DocumentCitation.citing_document_id.in_(ids))) or 0)
            counts["license_classes"] = dict((await session.execute(
                select(Document.license_class, func.count(Document.id)).where(Document.id.in_(ids))
                .group_by(Document.license_class))).all())
            counts["sources"] = dict((await session.execute(
                select(Document.source, func.count(Document.id)).where(Document.id.in_(ids))
                .group_by(Document.source))).all())
            counts["embedding_versions"] = {
                (version or "none"): n for version, n in (await session.execute(
                    select(Chunk.embedding_version, func.count(Chunk.id)).where(Chunk.document_id.in_(ids))
                    .group_by(Chunk.embedding_version))).all()
            }
        return counts


# ── what openFerment calls ─────────────────────────────────────────────────


@dataclass(frozen=True)
class Stored:
    """One entry's outcome: the kit's document, and whether this project
    held it before."""

    status: str  # "ingested", "linked" (the kit held it), "held" (so did the project), "failed"
    document_id: str | None
    detail: str = ""
    chunks: int = 0


async def _store(entries: list[CorpusEntry], *, project_id: str, selections: list[dict[str, Any]],
                 by: str) -> list[Stored]:
    stored: list[Stored] = []
    for entry, selection in zip(entries, selections, strict=True):
        outcome: IngestOutcome = (await ingest_entries([entry], embedder=embedder())).outcomes[0]
        if outcome.status == "skipped_duplicate" and outcome.document_id is None:
            # Another process stored the same text between the kit's check
            # and its commit; asked again, the kit names that document.
            outcome = (await ingest_entries([entry], embedder=embedder())).outcomes[0]
        if outcome.document_id is None:
            stored.append(Stored("failed", None, outcome.detail))
            continue
        if outcome.status == "ingested" and selection.get("sourceRef"):
            # A file written for the ingester has no address worth keeping;
            # the document points back to how it came instead.
            async with kit_engine.session_scope() as session:
                await session.execute(
                    update(Document).where(Document.id == outcome.document_id).values(source_ref=selection["sourceRef"])
                )
        new = await _link(project_id, outcome.document_id, selection, by)
        status = "ingested" if outcome.status == "ingested" else ("linked" if new else "held")
        stored.append(Stored(status, outcome.document_id, outcome.detail, outcome.chunk_count))
    return stored


def ingest(entries: list[CorpusEntry], *, project_id: str, selections: list[dict[str, Any]], by: str) -> list[Stored]:
    """Store each entry in the kit and link it to the project, entry by entry:
    one that fails leaves the others stored. `selections` says, for each,
    what was chosen and from where; it is kept on the link, and its
    `sourceRef`, when it has one, is where a newly stored document points
    back to in place of the file it was read from."""
    _engine("loop")
    return db.run(_store(entries, project_id=project_id, selections=selections, by=by))


def retrieve(query: str, *, project_id: str, top_k: int = 8, profile: str = "interactive",
             **kw: Any) -> RetrievalResult:
    """The kit's retrieval over the project's documents."""

    async def go() -> RetrievalResult:
        with projects.using(project_id):
            return await service().retrieve(query, top_k=top_k, profile=profile, **kw)

    return db.run(go())


def document(document_id: str, *, project_id: str, preview_chunks: int = 10_000) -> tuple[Document, list[Chunk]]:
    """A document the project holds, with its chunks in order. ApiError 404
    for one it does not hold."""

    async def go() -> tuple[Document, list[Chunk]]:
        with projects.using(project_id):
            return await service().get_document(document_id, preview_chunks=preview_chunks)

    return db.run(go())


def documents(project_id: str) -> list[tuple[Document, dict[str, Any]]]:
    """Every document the project holds, newest link first, each with its link."""

    async def go() -> list[tuple[Document, dict[str, Any]]]:
        link = t.documents_link
        async with db.session() as s:
            links = [dict(r) for r in (await s.execute(
                select(link).where(link.c.project_id == project_id).order_by(link.c.created_at.desc())
            )).mappings().all()]
        if not links:
            return []
        async with async_sessionmaker(_engine("loop"), expire_on_commit=False)() as session:
            found = {d.id: d for d in (await session.execute(
                select(Document).where(Document.id.in_([x["document_id"] for x in links]))
            )).scalars().all()}
        return [(found[x["document_id"]], x) for x in links if x["document_id"] in found]

    return db.run(go())


def stats(project_id: str) -> dict[str, Any]:
    async def go() -> dict[str, Any]:
        with projects.using(project_id):
            return await service().stats()

    return db.run(go())


def rest_app() -> Any:
    """The kit's REST app, for /rag: its routes, its key check and its error
    shape over `service('free')`. Its MCP endpoint is left out; the MCP
    server runs on its own (`python -m openferment_core.literature.mcp`)."""
    from sci_rag.server.app import create_app
    from starlette.routing import Mount

    app = create_app(settings=settings(), service=service("free"))
    app.router.routes = [r for r in app.router.routes if not (isinstance(r, Mount) and r.path == "/mcp")]
    return app
