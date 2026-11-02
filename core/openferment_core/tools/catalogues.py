"""A project's catalogues, for Postdoc (alpha 2.1 stage D, debt 1; catalogues.py).

`catalogue_read` lists the strains, the products, Guild's skills or Primer's
lessons the project keeps, narrowed by words. `catalogue_write` keeps one
entry, marked as the model's (`by` is its id) and audited as its write,
through `writes.keep_catalogue`; an entry already held under the id is
replaced, and nothing here takes one out. A catalogue holds names and words,
never a measured value.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import ToolResult
from . import Tool, ToolContext, register

MAX_ROWS = 40
KIND_WORDS = "strain, product, skill or lesson"


class CatalogueReadInput(BaseModel):
    kind: str = Field(description=f"Which catalogue: {KIND_WORDS}.")
    words: str = Field(default="", max_length=200, description="Words to narrow the entries by: an id, a name, an alias; empty for all.")
    limit: int = Field(default=20, ge=1, le=MAX_ROWS, description="How many rows at most.")


def _read(inp: CatalogueReadInput, ctx: ToolContext) -> ToolResult:
    from .. import catalogues

    kind = inp.kind.strip().lower()
    if kind not in catalogues.KINDS:
        return ToolResult(error=f"catalogue_read refused: there is no catalogue of {kind!r}; the catalogues are {KIND_WORDS}")
    words = [w for w in inp.words.lower().split() if w]
    rows = []
    for e in catalogues.listed(kind):
        said = " ".join([e.id, e.name, *(e.aliases or []), e.species or "", e.category or "", e.family or ""]).lower()
        if words and not all(w in said for w in words):
            continue
        rows.append(e.model_dump(mode="json", exclude_none=True, exclude={"at"}))
    return ToolResult(summary={"kind": kind, "matched": len(rows), "entries": rows[: inp.limit],
                               "note": "catalogue_write keeps an entry, marked as yours."})


class CatalogueWriteInput(BaseModel):
    kind: str = Field(description=f"Which catalogue: {KIND_WORDS}.")
    id: str = Field(max_length=80, description="The entry's id: letters, digits, '.', '_', ':' or '-'.")
    name: str = Field(max_length=200, description="Its name as a person reads it.")
    species: str = Field(default="", max_length=200, description="A strain's species.")
    program: str = Field(default="", max_length=80, description="A strain's chemical set, as pureOS names it.")
    aliases: list[str] = Field(default_factory=list, description="A strain's other names, as papers give them.")
    category: str = Field(default="", max_length=80, description="A product's class, as the proposer's rules read it.")
    sequence: str = Field(default="", max_length=20000, description="A protein product's sequence, one letter a residue.")
    sequenceSource: str = Field(default="", max_length=400, description="Where the sequence was read, in words; a sequence needs it.")
    family: str = Field(default="", max_length=80, description="A skill's family.")
    summary: str = Field(default="", max_length=2000, description="What a skill is.")
    mastery: list[str] = Field(default_factory=list, description="What mastery of a skill means, a criterion an item.")
    skills: list[str] = Field(default_factory=list, description="The skill ids a lesson counts toward.")
    note: str = Field(default="", max_length=2000, description="What the entry rests on, in words: the document or record it came from.")


def _write(inp: CatalogueWriteInput, ctx: ToolContext) -> ToolResult:
    from .writes import keep_catalogue

    return keep_catalogue("catalogue_write", inp, ctx)


READ_TOOL = register(Tool(
    name="catalogue_read",
    description=(
        "Read one of the project's catalogues: its strains (each with its species, the chemical set its trains use "
        "and the other names papers give it), its products (each with its class and a protein's sequence), Guild's "
        "skills or Primer's lessons. Narrow by words. Returns the entries in words; a pureOS proposal's host is a "
        "strain read here."
    ),
    input_model=CatalogueReadInput, run=_read, strict=False,
))

WRITE_TOOL = register(Tool(
    name="catalogue_write",
    description=(
        "Keep one entry in the project's catalogue of strains, products, skills or lessons, marked as yours: a strain "
        "a document describes, with its species and the names papers give it; a product with its class; a skill or a "
        "lesson. Names and words only, never a measured value: a number a paper reports is a record. An entry already "
        "kept under the id is replaced; say in the note what the entry rests on."
    ),
    input_model=CatalogueWriteInput, run=_write, strict=False, writes=True,
))
