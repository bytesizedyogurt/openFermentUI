"""The documents a project holds, for Postdoc (alpha 2.0 stage 6; ADR-002).

`literature_sources` lists them as Intake does: each document's title, year,
the collector that brought it, its licence class and how many passages the
kit holds of it. `literature_document` reads one: its citation, its sections
in order, and the passages of one section, each citable by a whole sentence
exactly as `search_passages`' are (`<document id>:<passage id>:0`, checked by
`quotes.is_whole_sentence`). A document enters a project only when a person
selects it (Intake); nothing here collects one.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import Passage, ToolResult
from . import Tool, ToolContext, register

MAX_ROWS = 40
# At most this many passages of a section, each cut to this many characters in
# the summary; the passages travel whole in `ToolResult.passages`.
MAX_PASSAGES = 6
TEXT_CHARS = 900


class LiteratureSourcesInput(BaseModel):
    words: str = Field(default="", max_length=200, description="Words to narrow by (a title's words); empty for all.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


def _sources(inp: LiteratureSourcesInput, ctx: ToolContext) -> ToolResult:
    from .. import intake

    words = [w for w in inp.words.lower().split() if w]
    rows = [{"documentId": did, **held} for did, held in intake.held().items()
            if all(w in str(held.get("title") or "").lower() for w in words)]
    return ToolResult(summary={"matched": len(rows), "documents": rows[: inp.limit],
                               "note": "Read one with literature_document; search them with search_passages."})


class LiteratureDocumentInput(BaseModel):
    document: str = Field(max_length=200, description="A document's id, as literature_sources gives it.")
    section: str = Field(default="", max_length=400,
                         description="A section's heading as this tool lists it, whose passages to read; empty for "
                                     "the list of sections alone.")


def _document(inp: LiteratureDocumentInput, ctx: ToolContext) -> ToolResult:
    from .. import projects
    from ..literature import kit

    did = inp.document.strip()
    try:
        held = kit.passages(did, project_id=projects.current())
    except Exception as e:  # the kit answers a document the project lacks with its own 404
        return ToolResult(error=f"literature_document refused: the project holds no readable document {did!r} "
                                f"({type(e).__name__})")
    doc = held.document
    headings: list[str] = []
    for p in held.sections:
        if p["heading"] not in headings:
            headings.append(p["heading"])
    want = inp.section.strip()
    chosen = [p for p in held.sections if want and p["heading"] == want][:MAX_PASSAGES]
    if want and not chosen:
        return ToolResult(error=f"literature_document refused: {did} has no section headed {want!r}; its sections "
                                f"are listed when no section is named")
    passages = [Passage(id=f"{did}:{p['id']}:0", paperId=did, sectionId=p["id"], heading=p["heading"],
                        kind="table" if p["isTable"] else "prose", text=p["text"], start=0, end=len(p["text"]))
                for p in chosen]
    return ToolResult(
        summary={
            "documentId": did, "title": doc.title, "authors": list(doc.authors or [])[:6],
            "year": doc.publication_year, "journal": doc.journal, "doi": doc.doi,
            "licenceClass": doc.license_class, "sections": headings[:MAX_ROWS],
            "passages": [{"passageId": x.id, "heading": x.heading, "kind": x.kind,
                          "text": x.text[:TEXT_CHARS] + ("…" if len(x.text) > TEXT_CHARS else "")} for x in passages],
        },
        passages=passages,
    )


SOURCES_TOOL = register(Tool(
    name="literature_sources",
    description=(
        "List the documents the project holds: each one's id, title, year, the collector that brought it, its "
        "licence class and how many passages the literature index keeps of it. Narrow by words in the title. A "
        "document enters the project only when a person selects it."
    ),
    input_model=LiteratureSourcesInput, run=_sources, strict=False,
))

DOCUMENT_TOOL = register(Tool(
    name="literature_document",
    description=(
        "Read one document the project holds: its citation (title, authors, year, journal, DOI, licence class) "
        "and its sections in order; name a section by its heading to read its passages, each with a passage id "
        "a claim quotes by a whole sentence, as search_passages' passages are quoted."
    ),
    input_model=LiteratureDocumentInput, run=_document, strict=False,
))
