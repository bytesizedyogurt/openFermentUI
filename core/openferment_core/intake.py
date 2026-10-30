"""Intake: what a project reads, collected into Sci RAG Kit (ADR-002;
OF-BLD-012 §5).

A person names a paper, a report or a strain entry by its identifier, uploads
a file or pastes text; `collect` hands it to the collector that serves it
(literature/collectors.py), stores it in the kit and links it to the project
(literature/kit.py), and says what happened in words: stored, linked (the kit
held the same text already), held (so did the project), or not collected and
why. A failure is a result, never an exception: the Intake board renders it.

THE FULL-TEXT CACHE, UNTIL EXTRACTION READS THE KIT. Extraction (extract.py)
still reads a paper's sections from `core/data/fulltext/{paperId}.json`,
which `fetch_paper` writes for a paper of the corpus. That cache and the
functions below `collect` stay until extraction reads the kit's text (stage
3, step 2); the fetching and the splitting are the collectors'.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from . import atomic
from .literature import collectors
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
from .models import CollectOutcome, FetchResult, FetchSource, IntakeStatus, OverlayPaper

__all__ = [
    "EUROPE_PMC", "FIXTURE_DIR", "FIXTURE_ROOT", "NetworkRefused", "NotCollected", "NotFetched", "Transient",
    "_get", "fetch_fulltext", "fetch_pdf", "fetch_sgd", "fixtures_only", "resolve_pmcid", "source_of",
    "split_jats", "split_pdf", "split_sgd",
]

_CORE = Path(__file__).parent.parent
DATA_DIR = _env_path("OPENFERMENT_DATA_DIR", _CORE / "data")
FULLTEXT_DIR = DATA_DIR / "fulltext"


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

    from .literature import kit

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


# ── the full-text cache, until extraction reads the kit (stage 3, step 2) ──


def _fetch_elsewhere(paper: dict[str, Any], source: FetchSource) -> FetchResult:
    """A paper whose text is held outside Europe PMC, fetched at its
    `sourceUrl` and split by its source's rule. Cached as `fetch_paper`
    caches: a miss as a miss, an outage not at all."""
    paper_id = str(paper["id"])
    url = str(paper.get("sourceUrl") or "").strip()
    now = datetime.now(timezone.utc).isoformat()
    try:
        if source == "osti":
            result = split_pdf(fetch_pdf(url), paper_id=paper_id, source_url=url)
        else:
            result = split_sgd(fetch_sgd(url), paper_id=paper_id)
    except (httpx.TransportError, Transient) as e:
        return FetchResult(
            paperId=paper_id, status="failed:fetch", fetchedAt=now, source=source,
            reason=f"not cached — try again: {e}",
        )
    except (httpx.HTTPError, NetworkRefused, NotFetched) as e:
        return _persist(FetchResult(
            paperId=paper_id, status="failed:fetch", reason=str(e), fetchedAt=now, source=source,
        ))
    return _persist(result)


# ── persistence ────────────────────────────────────────────────────────


def _path(paper_id: str) -> Path:
    return FULLTEXT_DIR / f"{paper_id}.json"


def cached(paper_id: str) -> FetchResult | None:
    path = _path(paper_id)
    if not path.exists():
        return None
    return FetchResult.model_validate_json(path.read_text(encoding="utf-8"))


def _persist(result: FetchResult) -> FetchResult:
    atomic.write_text(_path(result.paperId), result.model_dump_json(indent=2) + "\n")
    return result


def fetch_paper(paper: dict[str, Any], *, force: bool = False) -> FetchResult:
    """Resolve, fetch, split, persist. Returns the cached result when one
    exists unless `force`, so the batch is idempotent and a miss is not
    re-asked.

    A MISS is cached: no open-access text, a 404, a document with nothing in
    it. An OUTAGE is not — a timeout, a connection that dropped, a 5xx that
    survived the retry — because that is the network's condition and not the
    paper's, and a batch that cached it would show every paper a brief outage
    touched as halted until somebody forced each one by hand.

    A paper whose `sourceUrl` is on OSTI or the Saccharomyces Genome
    Database is fetched there, under the same rules (`_fetch_elsewhere`)."""
    paper_id = str(paper["id"])
    if not force:
        hit = cached(paper_id)
        if hit is not None:
            return hit
    source = source_of(paper)
    if source != "europepmc":
        return _fetch_elsewhere(paper, source)

    now = datetime.now(timezone.utc).isoformat()
    try:
        pmcid = resolve_pmcid(paper)
    except (httpx.TransportError, Transient) as e:
        return FetchResult(
            paperId=paper_id, status="failed:fetch", fetchedAt=now,
            reason=f"PMCID lookup failed, not cached — try again: {e}",
        )
    except (httpx.HTTPError, NetworkRefused, ValueError) as e:
        return _persist(FetchResult(
            paperId=paper_id, status="failed:fetch", reason=f"PMCID lookup failed: {e}", fetchedAt=now,
        ))
    if not pmcid:
        what = paper.get("doi") or paper.get("pmid") or "no identifier"
        return _persist(FetchResult(
            paperId=paper_id, status="failed:fetch", fetchedAt=now,
            reason=f"no open-access full text on Europe PMC for {what}",
        ))
    try:
        xml = fetch_fulltext(pmcid)
    except (httpx.TransportError, Transient) as e:
        return FetchResult(
            paperId=paper_id, pmcid=pmcid, status="failed:fetch", fetchedAt=now,
            reason=f"not cached — try again: {e}",
        )
    except (httpx.HTTPError, NetworkRefused) as e:
        return _persist(FetchResult(
            paperId=paper_id, pmcid=pmcid, status="failed:fetch", reason=str(e), fetchedAt=now,
        ))
    return _persist(split_jats(xml, paper_id=paper_id, pmcid=pmcid))


def status_of(paper_id: str) -> IntakeStatus | None:
    """A paper's fetch state, summarised for `GET /api/intake/status`."""
    result = cached(paper_id)
    if result is None:
        return None
    return IntakeStatus(
        paperId=paper_id,
        pmcid=result.pmcid,
        ingest=result.status,
        textSource="full-text" if result.status == "complete" else "curation-note",
        sections=len(result.sections),
        tables=sum(1 for s in result.sections if s.id.startswith("t")),
        license=(result.license.href or result.license.text) if result.license else None,
        fetchedAt=result.fetchedAt,
        reason=result.reason,
        source=result.source,
    )


def all_statuses() -> dict[str, IntakeStatus]:
    if not FULLTEXT_DIR.exists():
        return {}
    out: dict[str, IntakeStatus] = {}
    for path in sorted(FULLTEXT_DIR.glob("*.json")):
        status = status_of(path.stem)
        if status is not None:
            out[path.stem] = status
    return out


def overlay_papers() -> dict[str, OverlayPaper]:
    """Every cached fetch as the overlay's `papers` map (§2.1).

    A success carries the paper's own sections and the licence string; a
    failure carries its status and reason and no sections, so the store keeps
    the seed's curation note for it and the board can say why it halted.
    """
    out: dict[str, OverlayPaper] = {}
    if not FULLTEXT_DIR.exists():
        return out
    for path in sorted(FULLTEXT_DIR.glob("*.json")):
        result = cached(path.stem)
        if result is None:
            continue
        ok = result.status == "complete"
        out[path.stem] = OverlayPaper(
            ingest=result.status,
            textSource="full-text" if ok else "curation-note",
            sections=result.sections if ok else [],
            license=(result.license.href or result.license.text) if result.license else None,
            fetchedAt=result.fetchedAt,
            reason=result.reason,
            source=result.source,
        )
    return out


# ── batch ──────────────────────────────────────────────────────────────


def _papers() -> list[dict[str, Any]]:
    from .corpus import load_corpus

    return load_corpus().papers


def fetch_all(papers: list[dict[str, Any]], *, force: bool = False) -> list[FetchResult]:
    """Every paper with a PMCID first, then the DOI-only and PMID-only ones
    through `resolve_pmcid`, and those with a source address of their own
    among them. Papers with no identifier and no address are skipped without
    a request — there is nothing to ask."""
    ordered = sorted(
        (p for p in papers if p.get("pmcid") or p.get("doi") or p.get("pmid") or p.get("sourceUrl")),
        key=lambda p: (0 if p.get("pmcid") else 1, str(p["id"])),
    )
    return [fetch_paper(p, force=force) for p in ordered]


def _print_table(results: list[FetchResult]) -> None:
    print(f"{'id':<6} {'pmcid':<13} {'sections':>8} {'tables':>6}  {'licence':<44} {'bytes':>8}  status")
    for r in results:
        tables = sum(1 for s in r.sections if s.id.startswith("t"))
        lic = ((r.license.href or r.license.text or "") if r.license else "")[:44]
        where = r.pmcid or (r.source if r.source != "europepmc" else "-")
        print(
            f"{r.paperId:<6} {where:<13} {len(r.sections):>8} {tables:>6}  {lic:<44} "
            f"{r.bytes:>8}  {r.status}{' — ' + r.reason if r.reason else ''}"
        )
    ok = sum(1 for r in results if r.status == "complete")
    print(f"\n{ok} of {results and len(results)} fetched with full text")


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
    force = "--force" in argv
    if "--all" in argv:
        results = fetch_all(_papers(), force=force)
        _print_table(results)
        # A miss is an answer and is cached; an outage is not (fetch_paper).
        # A result the cache does not hold is one this run could not get, and
        # the batch exits 1 for it so the nightly log shows a failed night
        # as one (OF-BLD-012 §B.8).
        unreached = [r.paperId for r in results if cached(r.paperId) != r]
        if unreached:
            print(f"{len(unreached)} not reached, will be asked again: {', '.join(unreached)}")
        return 1 if unreached else 0
    ids = [a for a in argv if not a.startswith("--")]
    if not ids:
        print("usage: python -m openferment_core.intake --all [--force] | <paperId> [...]")
        return 2
    by_id = {p["id"]: p for p in _papers()}
    results = []
    for paper_id in ids:
        if paper_id not in by_id:
            print(f"{paper_id}: not in the corpus")
            return 1
        results.append(fetch_paper(by_id[paper_id], force=force))
    _print_table(results)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
