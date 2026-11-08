"""A project's catalogues, for Postdoc (alpha 2.1 stage D, debt 1; catalogues.py).

`catalogue_read` lists the strains, the products, Guild's skills or Primer's
lessons the project keeps, narrowed by words. `catalogue_write` keeps one
entry, marked as its caller's (`by` is the model's id or the client's name)
and audited as its write, through `writes.keep_catalogue`. A model's write
replaces an entry it kept itself under the same name through the same kind
of door (Postdoc's loop, or an outside assistant's) and is refused in words
over any other keeper's (alpha 2.2 D.0, catalogues.keep); nothing here takes
an entry out. A catalogue holds names and words, never a measured value, and
a skill's policy (its numbers) is a person's to write on the catalogues
screen, so `catalogue_write` keeps a skill with none (alpha 2.2 E.8). A
lesson's body (its minutes, blocks and checkpoint) is a person's to write
there too: `catalogue_write` keeps a lesson with none, and `catalogue_read`
lists a lesson with its body left to the catalogues screen and Primer
(alpha 2.2 E.12a, ADR-018).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..catalogues import PRODUCT_CATEGORIES
from ..models import ToolResult
from . import Tool, ToolContext, register

MAX_ROWS = 40
ROWS = 20
KIND_WORDS = "strain, product, skill or lesson"


class CatalogueReadInput(BaseModel):
    kind: str = Field(description=f"Which catalogue: {KIND_WORDS}.")
    words: str = Field(default="", max_length=200, description="Words to narrow the entries by: an id, a name, an alias; empty for all.")
    limit: int = Field(default=ROWS, ge=1, le=MAX_ROWS, description=(
        f"How many entries at most, 1 to {MAX_ROWS}, {ROWS} when left out; a limit outside those bounds refuses the "
        "call."))


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
        # A lesson's body is long, and the catalogues screen and Primer show it.
        rows.append(e.model_dump(mode="json", exclude_none=True, exclude={"blocks", "checkpoint"}))
    return ToolResult(summary={"kind": kind, "matched": len(rows), "entries": rows[: inp.limit],
                               "note": "catalogue_write keeps an entry, marked as yours."})


class CatalogueWriteInput(BaseModel):
    kind: str = Field(description=f"Which catalogue: {KIND_WORDS}.")
    id: str = Field(max_length=80, description=(
        "The entry's id: a letter or a digit first, then letters, digits, '.', '_', ':' or '-', at most 80 "
        "characters."))
    name: str = Field(max_length=200, description="Its name as a person reads it.")
    species: str = Field(default="", max_length=200, description="A strain's species.")
    program: str = Field(default="", max_length=80, description="A strain's chemical set, as pureOS names it.")
    aliases: list[str] = Field(default_factory=list, description="A strain's other names, as papers give them.")
    category: str = Field(default="", max_length=80, description=(
        "A product's class, one of those pureOS's proposer reads: " + ", ".join(PRODUCT_CATEGORIES) + "."))
    location: str = Field(default="", max_length=20, description=(
        "Where the cells leave a product, as a document states it: secreted, or intracellular."))
    sequence: str = Field(default="", max_length=20000, description="A protein product's sequence, one letter a residue.")
    sequenceSource: str = Field(default="", max_length=400, description="Where the sequence was read, in words; a sequence needs it.")
    family: str = Field(default="", max_length=80, description="A skill's family.")
    summary: str = Field(default="", max_length=2000, description="What the entry is, in words; a skill's what the skill is.")
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
        "and the other names papers give it), its products (each with its class, where the cells leave it and a "
        "protein's sequence), Guild's skills (each with the policy a person wrote for it, when one did) or Primer's "
        "lessons (each with the skills it counts toward and the minutes it takes; its body, the blocks and the "
        "checkpoint a person writes, is left to the catalogues screen and Primer). Narrow by words. Returns {kind, "
        "matched, entries, note}: matched counts every "
        f"entry the words match, and entries holds the first limit of them ({ROWS} when limit is left out, at most "
        f"{MAX_ROWS}), in id order, each an entry with its fields as kept and its null fields left out: its kind, "
        "id, name and the fields of its kind, who kept it (by), the lane it was kept in (agent: person or model), "
        "the door a model's entry came in by (via: postdoc, mcp or http), where it came from (source) and when it "
        "was kept (at, ISO 8601 in UTC, as the audit writes its rows' times). A pureOS proposal's host is a strain "
        "read here."
    ),
    input_model=CatalogueReadInput, run=_read, strict=False,
))

WRITE_TOOL = register(Tool(
    name="catalogue_write",
    description=(
        "Keep one entry in the project's catalogue of strains, products, skills or lessons, marked as yours: a strain "
        "a document describes, with its species and the names papers give it; a product with its class; a skill or a "
        "lesson. Names and words only, never a measured value: a number a paper reports is a record. An entry you "
        "kept yourself under the id, in your own name and through the same kind of door (Postdoc's loop, or an "
        "outside assistant's: MCP or the HTTP endpoint's assistant header), is replaced; an entry a person or "
        "another caller kept under it stays as it is, and the call is refused in words naming the entry and who "
        "kept it, so keep yours under an id of its own, one that starts with your name, its / written as a dot "
        "(example-agent.0.1-a-skill for example-agent/0.1). Say in the note what the entry rests on. A strain's own "
        "fields are species, program and aliases; a product's are category (one of the classes pureOS's proposer "
        "reads), location, sequence and sequenceSource; a skill's are family and mastery; a lesson's is skills; "
        "every kind takes name, summary and note, and a field of another kind is refused in words. A skill kept here "
        "holds no policy, which a person writes on the catalogues screen, and Guild rates nobody on it until one "
        "does; a lesson kept here holds no body (its minutes, blocks and checkpoint), which a person writes there "
        "too. The result's summary is the entry as kept, its null fields left out and "
        "a protein's sequence left to catalogue_read: its kind, id, name and fields, its own note, by (the name "
        "you are kept under), agent (model), via (the door: postdoc, mcp or http), source and at, beside state "
        "(open) and meaning (the service's word on the keep). Its audit row names the module that reads the kind "
        "(geneos for a strain, pureos a product, guild a skill, primer a lesson), action catalogue_write, state "
        "open, target <kind>/<id>, the caller as agent and who, your note as detail.note and the door as "
        "detail.via; the result's auditIds names that row by its id."
    ),
    input_model=CatalogueWriteInput, run=_write, strict=False, writes=True,
))
