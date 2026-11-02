"""Intake: what a project reads, collected into Sci RAG Kit (ADR-002;
OF-BLD-012 §5).

A person names a paper, a report or a strain entry by its identifier, uploads
a file or pastes text; `collect` hands it to the collector that serves it
(literature/collectors.py), stores it in the kit and links it to the project
(literature/kit.py), and says what happened in words: stored, linked (the kit
held the same text already), held (so did the project), or not collected and
why. A failure is a result, never an exception: the Intake board renders it.

What the project holds is the kit's (`overlay_papers`): its passages, which
extraction reads and every quote anchors to (extract.py), its citation and
its licence. Nothing is cached beside it.
"""
from __future__ import annotations

from pathlib import Path
from typing import get_args

from .literature import collectors, kit
from .literature.collectors import (
    EUROPE_PMC,
    FIXTURE_DIR,
    FIXTURE_ROOT,
    Collected,
    NetworkRefused,
    NotCollected,
    NotFetched,
    Transient,
    _env_path,
    _get,
    fetch_fulltext,
    fetch_pdf,
    fetch_sgd,
    fixtures_only,
    resolve_pmcid,
    source_of,
    split_jats,
    split_pdf,
    split_sgd,
)
from .models import CollectOutcome, FetchedSection, FetchSource, OverlayPaper

__all__ = [
    "EUROPE_PMC", "FIXTURE_DIR", "FIXTURE_ROOT", "NetworkRefused", "NotCollected", "NotFetched", "Transient",
    "_get", "fetch_fulltext", "fetch_pdf", "fetch_sgd", "fixtures_only", "resolve_pmcid", "source_of",
    "split_jats", "split_pdf", "split_sgd",
]

_CORE = Path(__file__).parent.parent
# Where the service keeps what it fetches that is not literature: the
# genome-scale models geneOS reads (geneos_models.py).
DATA_DIR = _env_path("OPENFERMENT_DATA_DIR", _CORE / "data")


# ── collection into a project ──────────────────────────────────────────


def _outcome(collected: Collected, status: str, *, document_id: str | None = None, chunks: int = 0,
             reason: str | None = None) -> CollectOutcome:
    return CollectOutcome(
        status=status, documentId=document_id, collector=collected.collector, identifier=collected.identifier,
        title=collected.citation.title, licenceClass=collected.licence_class, licence=collected.licence,
        sections=collected.sections, tables=collected.tables, chunks=chunks, reason=reason,
    )


def store(collected: Collected, *, project_id: str, by: str, reason: str = "") -> CollectOutcome:
    """Store a collected document in the kit and link it to the project."""
    from sci_rag.ingest.manifest import CorpusEntry

    citation = collected.citation
    selection = collected.selection(reason)
    if collected.url is None:
        selection["sourceRef"] = f"{collected.collector}:{collected.identifier}"
    with collectors.folder() as tmp:
        entry = CorpusEntry(
            path=collected.write(Path(tmp)),
            title=citation.title or None,
            authors=citation.authors,
            year=citation.year,
            doi=citation.doi,
            journal=citation.journal,
            url=collected.url,
            license_class=collected.licence_class,
            license_source=(collected.licence.href or collected.licence.text) if collected.licence else None,
            source=kit.source(project_id, collected.collector),
        )
        [stored] = kit.ingest([entry], project_id=project_id, selections=[selection], by=by)
    if stored.status == "failed":
        return _outcome(collected, "failed", reason=f"the kit did not store it: {stored.detail}")
    return _outcome(collected, stored.status, document_id=stored.document_id, chunks=stored.chunks)


def _refused(collector: str, identifier: str, e: NotCollected) -> CollectOutcome:
    return CollectOutcome(
        status="failed", collector=collector, identifier=identifier, title="", licenceClass="unknown",
        reason=str(e), transient=e.transient,
    )


def collect(identifier: str, *, project_id: str, by: str, reason: str = "") -> CollectOutcome:
    """A paper, a report or a strain entry by its identifier, into the project."""
    try:
        collected = collectors.by_identifier(identifier)
    except NotCollected as e:
        return _refused("identifier", identifier.strip(), e)
    return store(collected, project_id=project_id, by=by, reason=reason)


def upload(filename: str, data: bytes, *, project_id: str, by: str, title: str = "", licence_class: str = "unknown",
           licence: str = "", reason: str = "") -> CollectOutcome:
    """A file a person uploaded, into the project."""
    try:
        collected = collectors.uploaded(filename, data, title=title, licence_class=licence_class, licence=licence)
    except NotCollected as e:
        return _refused("upload", filename, e)
    return store(collected, project_id=project_id, by=by, reason=reason)


def paste(title: str, text: str, *, project_id: str, by: str, url: str = "", licence_class: str = "unknown",
          licence: str = "", reason: str = "") -> CollectOutcome:
    """Text a person pasted, into the project."""
    try:
        collected = collectors.pasted(title, text, url=url, licence_class=licence_class, licence=licence)
    except NotCollected as e:
        return _refused("paste", title.strip(), e)
    return store(collected, project_id=project_id, by=by, reason=reason)


# ── what the project holds ─────────────────────────────────────────────


def overlay_papers(project_id: str) -> dict[str, OverlayPaper]:
    """Every document the project holds, as the overlay's `papers` (§2.1):
    its passages as its sections, its citation, its licence as the source
    stated it and its class, and who served it."""
    sources = set(get_args(FetchSource))
    out: dict[str, OverlayPaper] = {}
    for document, link, passages in kit.held(project_id):
        selection = link["selection"] or {}
        stated = selection.get("licence") or {}
        collector = selection.get("collector")
        out[document.id] = OverlayPaper(
            ingest="complete",
            textSource="full-text",
            sections=[FetchedSection(id=p["id"], heading=p["heading"], text=p["text"]) for p in passages],
            license=stated.get("href") or stated.get("text") or document.license_source,
            fetchedAt=link["created_at"].isoformat(),
            source=collector if collector in sources else "upload",
            title=document.title,
            authors=list(document.authors or []),
            year=document.publication_year,
            journal=document.journal,
            doi=document.doi,
            pmcid=selection.get("pmcid"),
            url=selection.get("url") or document.source_ref,
            licenceClass=document.license_class,
        )
    return out


def held(project_id: str | None = None) -> dict[str, dict[str, object]]:
    """What the project holds, a line a document: its title, year, collector,
    licence class and how many passages, for Intake's module rows."""
    from . import projects

    return {
        document.id: {
            "title": document.title,
            "year": document.publication_year,
            "collector": (link["selection"] or {}).get("collector"),
            "licenceClass": document.license_class,
            "passages": document.chunk_count,
        }
        for document, link in kit.documents(project_id or projects.current())
    }
