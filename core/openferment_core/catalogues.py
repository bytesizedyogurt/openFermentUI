"""A project's catalogues (alpha 2.1 stage D, debt 1): the strains and their
aliases, the products, Guild's skills and Primer's lessons.

Alpha 2.0 deleted the TypeScript catalogues these came from with the seed
(ADR-010), and every reader of them read an empty list: no host on file for a
pureOS proposal, no skill for a Guild entry, no product for ProtParam. Each
is now a kind of row in the project's `catalogue` table, kept whole as a
`CatalogueEntry`, with who added it and where it came from:

    strain    a strain the project works with, its species, the chemical set
              its trains use (pureOS's `program`) and the other names papers
              give it; a pureOS proposal's host is a strain of this kind
    product   a product a train recovers or ProtParam reads: its class
              (`category`, one of the classes pureOS's proposer reads), where
              the cells leave it (`location`: secreted, or intracellular) and,
              for a protein, its sequence
    skill     a Guild skill: its family, what it is and what mastery means,
              and its policy: how critical it is, how many days a
              qualification stands, how many supervised runs come before a
              witnessed check, and the skills it needs first (`prerequisites`);
              Guild rates nobody on a skill kept with no policy
              (competence.unrated)
    lesson    a Primer lesson and the skills it counts toward

The readers take them in the shapes they always read (`as_*`): geneOS's hosts
and the strain aliases (module_stores), ProtParam's products, the proposer's
catalogue, Guild's projection. A catalogue holds names and words, never a
measured value: a number a paper reports is a record (ADR-006).

Entries arrive by the route (`POST /api/catalogues/{kind}`, which the
catalogues screen at /catalogues sends), by Postdoc's `catalogue_write`
(marked as the model's), or by Intake from a file of entries
(`POST /api/intake/catalogue`, JSON or CSV). Nothing here deletes an entry:
taking a person's entry out of a live instance is the owner's call. A skill's
policy is a person's to write: the route and a file take it, and
`catalogue_write` takes no number.

WHO KEPT AN ENTRY (alpha 2.2 D.0). Each entry names its keeper (`by`), the
lane it was kept in (`agent`): `person` for the route, a file and a call
naming `?by=`, `model` for a model's or an outside assistant's
`catalogue_write`; and, in the model's lane, the door it came in by (`via`:
`postdoc` for Postdoc's loop, `mcp` for the MCP server in its own process,
`http` for the HTTP endpoint's assistant header). A person's keep replaces
whatever the id holds. A model's write replaces an entry kept in the model's
lane under its own name through the same kind of door, Postdoc's entry by
Postdoc and an outside assistant's by that assistant, and refuses every other
in words naming the entry and who kept it, with nothing written: a model
never replaces an entry a person kept, and an assistant that declares
Postdoc's model id leaves Postdoc's entries as they are. A keeper's name is
read as `tools.caller_name` writes one, at every door.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, ValidationError, ValidationInfo, field_validator, model_validator
from sqlalchemy import select

from . import db, projects
from .competence import POLICY as SKILL_POLICY
from .db import models as t
from .db import rows

CatalogueKind = Literal["strain", "product", "skill", "lesson"]
KINDS: tuple[str, ...] = ("strain", "product", "skill", "lesson")
# A product's class, as pureOS's proposer reads one (pureos/proposer.py
# CLASS_OF_CATEGORY, each a protein, a small molecule or a polymer);
# test_catalogues.py holds the two to one list. Each class is a word.
ProductCategory = Literal["molecular_biology_enzyme", "diagnostic", "research_protein", "food_protein",
                          "sweet_protein", "structural_protein", "industrial_enzyme", "therapeutic_protein", "hmo",
                          "terpene", "glycoside", "biopolymer"]
PRODUCT_CATEGORIES: tuple[str, ...] = get_args(ProductCategory)
# Where the cells leave a product, as the proposer's rules split on it.
ProductLocation = Literal["secreted", "intracellular"]
# The longest a qualification may stand, in days: a hundred years, so the day
# it lapses stays a calendar date (Python's dates end with the year 9999).
MAX_RECENCY_DAYS = 36500
# The twenty amino acids a protein's sequence is written in, one letter each.
RESIDUES = frozenset("ACDEFGHIKLMNPQRSTVWY")
MAX_FILE_ROWS = 2000


class CatalogueRefused(ValueError):
    """An entry or a file the catalogue will not keep, in words."""


class CatalogueEntryNotFound(KeyError):
    pass


class CatalogueEntry(BaseModel):
    """One entry of a project's catalogue; the fields a kind does not use stay empty."""

    kind: CatalogueKind
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
    name: str = Field(min_length=1, max_length=200)
    # A strain: its species, the chemical set its trains use, its other names.
    species: str | None = Field(default=None, max_length=200)
    program: str | None = Field(default=None, max_length=80)
    aliases: list[str] = Field(default_factory=list, max_length=40)
    # A product: its class as the proposer's rules read it, where the cells
    # leave it (secreted, or kept inside them), and a protein's sequence.
    category: ProductCategory | None = None
    location: ProductLocation | None = None
    sequence: str | None = Field(default=None, max_length=20000)
    # Where the sequence was read, in words (a UniProt entry, a paper's table):
    # ProtParam computes from a sequence that names it, and from no other.
    sequenceSource: str | None = Field(default=None, max_length=400)
    # A skill: its family, what it is, what mastery of it means.
    family: str | None = Field(default=None, max_length=80)
    summary: str | None = Field(default=None, max_length=2000)
    mastery: list[str] = Field(default_factory=list, max_length=40)
    # A skill's policy (SKILL_POLICY), as Guild's levels read it: a critical
    # skill is one where a mistake hurts a person or loses a batch; how many
    # days a qualification stands with nobody seeing the person perform; how
    # many cosigned runs come before a witnessed check can qualify; and the
    # skills that must be at Supervised or above first, by their ids. All
    # three of the first or none: Guild rates nobody on a skill with none.
    criticality: Literal["routine", "critical"] | None = None
    recencyDays: int | None = Field(default=None, ge=1, le=MAX_RECENCY_DAYS)
    supervisedRuns: int | None = Field(default=None, ge=0)
    prerequisites: list[str] = Field(default_factory=list, max_length=40)
    # A lesson: the skills it counts toward, by their ids.
    skills: list[str] = Field(default_factory=list, max_length=40)
    note: str | None = Field(default=None, max_length=2000)
    # Where the entry came from, in words: a person, a document, a file.
    source: str | None = Field(default=None, max_length=400)
    by: str = Field(default="", max_length=200)
    # The lane it was kept in, as the audit names one: `person` for a
    # person's keep, `model` for a model's or an outside assistant's write.
    # The service writes it over whatever an entry sent holds; an entry
    # kept before the service wrote it reads it from its source (`keeper`).
    agent: Literal["model", "person"] | None = None
    # The door a model's write came in by, as its audit row names it:
    # `postdoc`, `mcp` or `http` (tools.ToolContext.door); none for a
    # person's keep. The service writes it too; an entry kept before reads
    # it from its source (`door`).
    via: Literal["postdoc", "mcp", "http"] | None = None
    at: str = ""

    @field_validator("aliases", "mastery", "skills", "prerequisites")
    @classmethod
    def _words(cls, v: list[str]) -> list[str]:
        out = [w.strip() for w in v if w and w.strip()]
        return list(dict.fromkeys(out))

    @field_validator("category", mode="before")
    @classmethod
    def _a_products_class(cls, v: Any, info: ValidationInfo) -> Any:
        """A product's class, one of those the proposer reads, in words when it
        is another; blank reads as none stated."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        if info.data.get("kind") != "product":
            raise ValueError("a category belongs to a product: the class pureOS's proposer reads")
        if v not in PRODUCT_CATEGORIES:
            raise ValueError(f"a product's category is one of the classes pureOS's proposer reads "
                             f"({', '.join(PRODUCT_CATEGORIES)}), and {v!r} is outside them")
        return v

    @model_validator(mode="after")
    def _fits_its_kind(self) -> "CatalogueEntry":
        if self.sequence is not None:
            if self.kind != "product":
                raise ValueError("a sequence belongs to a product")
            seq = "".join(self.sequence.split()).upper()
            bad = sorted(set(seq) - RESIDUES)
            if not seq or bad:
                raise ValueError(f"a protein's sequence is written in the twenty residues' letters; it holds {''.join(bad) or 'nothing'}")
            if not (self.sequenceSource or "").strip():
                raise ValueError("a sequence enters with where it was read (sequenceSource)")
            self.sequence = seq
        if self.skills and self.kind != "lesson":
            raise ValueError("the skills an entry counts toward belong to a lesson")
        if (self.aliases or self.species or self.program) and self.kind != "strain":
            raise ValueError("a species, a chemical set and other names belong to a strain")
        if self.location is not None and self.kind != "product":
            raise ValueError("a location belongs to a product: where the cells leave it")
        policy = [k for k in SKILL_POLICY if getattr(self, k) is not None]
        if (self.mastery or self.family or policy or self.prerequisites) and self.kind != "skill":
            raise ValueError("a family, what mastery means and a policy belong to a skill")
        if (policy or self.prerequisites) and len(policy) < len(SKILL_POLICY):
            left = _listed_words([k for k in SKILL_POLICY if getattr(self, k) is None])
            raise ValueError(f"a skill's policy names {_listed_words(list(SKILL_POLICY))} together, and this one "
                             f"leaves out {left}")
        if self.id in self.prerequisites:
            raise ValueError("a skill's prerequisites are other skills, and this one names itself")
        return self


def _listed_words(names: list[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _now() -> str:
    """A keep's time, ISO 8601 in UTC, written as the audit writes its rows'
    (`+00:00`), so a client sets the two side by side."""
    return datetime.now(timezone.utc).isoformat()


def _name(by: str | None) -> str:
    """A keeper's name as every door reads one (tools.caller_name): control,
    format and surrogate characters dropped, whitespace collapsed, at most
    200 characters."""
    from .tools import caller_name

    return caller_name(by or "")


def _row_id(kind: str, entry_id: str) -> str:
    return f"{kind}/{entry_id}"


def _kind(kind: str) -> str:
    if kind not in KINDS:
        raise CatalogueRefused(f"there is no catalogue of {kind!r}: the catalogues are {', '.join(KINDS)}")
    return kind


# ── the store ──────────────────────────────────────────────────────────


def _door_of_source(entry: CatalogueEntry) -> str | None:
    """The door a model's entry kept before the service wrote `via` came in
    by, read from its source as catalogue_write wrote one then."""
    if entry.source == f"Postdoc ({entry.by})":
        return "postdoc"
    if entry.source == f"{entry.by}, over MCP":
        return "mcp"
    if entry.source == f"{entry.by}, at the HTTP endpoint":
        return "http"
    return None


def keeper(entry: CatalogueEntry) -> str:
    """The lane an entry was kept in, `model` or `person`: its `agent`. An
    entry kept before the service wrote that field holds a model's write in
    its source alone, as catalogue_write wrote one then (`<name>, over MCP`,
    `Postdoc (<name>)`); every other such entry is a person's."""
    if entry.agent is not None:
        return entry.agent
    return "model" if _door_of_source(entry) else "person"


def door(entry: CatalogueEntry) -> str | None:
    """The door a model's entry came in by (`postdoc`, `mcp` or `http`), its
    `via`, else read from its source; None for a person's entry."""
    if keeper(entry) != "model":
        return None
    return entry.via or _door_of_source(entry) or "postdoc"


def _side(entry: CatalogueEntry) -> str:
    """Whose an entry of the model's lane is: Postdoc's, or an outside
    assistant's, through either of the assistant's doors."""
    return "postdoc" if door(entry) == "postdoc" else "assistant"


def _as_kept(body: dict[str, Any]) -> CatalogueEntry:
    entry = CatalogueEntry.model_validate(body)
    if entry.agent is not None and (entry.agent == "person" or entry.via is not None):
        return entry
    return entry.model_copy(update={"agent": keeper(entry), "via": door(entry)})


async def _listed(project_id: str, kind: str) -> list[CatalogueEntry]:
    async with db.session() as s:
        bodies = await rows.bodies(s, t.catalogue, project_id, t.catalogue.c.kind == kind)
    return sorted((_as_kept(b) for b in bodies), key=lambda e: e.id)


def listed(kind: str) -> list[CatalogueEntry]:
    """The open project's entries of one kind, by id, each with the lane it was kept in."""
    return db.run(_listed(projects.current(), _kind(kind)))


def get(kind: str, entry_id: str) -> CatalogueEntry:
    found = next((e for e in listed(kind) if e.id == entry_id), None)
    if found is None:
        raise CatalogueEntryNotFound(f"the project's {kind} catalogue holds no {entry_id}")
    return found


def _taken(held: CatalogueEntry) -> str:
    lane = ("a person's" if keeper(held) == "person" else "Postdoc's" if _side(held) == "postdoc"
            else "an outside assistant's")
    return (f"the project's {held.kind} catalogue holds {held.id}, kept by {held.by} in {lane} name; a model's write "
            "replaces only an entry it kept itself, under its own name and through its own kind of door (Postdoc's "
            "loop, or an outside assistant's), so nothing was written. Keep this entry under an id of its own")


async def _keep(project_id: str, entries: list[CatalogueEntry]) -> None:
    async with db.session() as s:
        # One keep at a time in the project's catalogues: a person's keep
        # never lands between a model's check and its write.
        await db.lock(s, "catalogue", project_id)
        for e in entries:
            row_id = _row_id(e.kind, e.id)
            if e.agent == "model":
                held = await rows.body(s, t.catalogue, project_id, row_id)
                if held is not None:
                    was = CatalogueEntry.model_validate(held)
                    if keeper(was) != "model" or was.by != e.by or _side(was) != _side(e):
                        raise CatalogueRefused(_taken(was))
            await rows.put(s, t.catalogue, project_id, row_id, e.model_dump(mode="json"), by=e.by, kind=e.kind)


def keep(entry: CatalogueEntry, *, by: str, agent: Literal["model", "person"] = "person",
         via: str | None = None) -> CatalogueEntry:
    """An entry kept in the open project's catalogue of its kind, in the name
    of `by` (read as `_name` reads one), in the lane `agent` names, a model's
    through the door `via` names (postdoc when it names none). A person's
    keep replaces an entry already held under the id. A model's replaces one
    it kept itself under the same name through the same kind of door, and is
    refused in words for any other (CatalogueRefused), nothing written."""
    who = _name(by)
    if not who:
        raise CatalogueRefused("a catalogue entry is kept in a person's or a model's name")
    through = (via or "postdoc") if agent == "model" else None
    kept = entry.model_copy(update={"by": who, "at": _now(), "agent": agent, "via": through})
    db.run(_keep(projects.current(), [kept]))
    return kept


def _first_error(err: ValidationError) -> str:
    first = err.errors()[0]
    where = ".".join(str(p) for p in first.get("loc", ())) or "the entry"
    return f"{where}: {str(first.get('msg')).removeprefix('Value error, ')}"


def keep_fields(kind: str, fields: dict[str, Any], *, by: str, source: str,
                agent: Literal["model", "person"], via: str | None = None) -> CatalogueEntry:
    """An entry made from fields and kept in the lane `agent` names, through
    the door `via` names, for a caller that holds no entry
    (`catalogue_write`): refused in words when the kind does not take them,
    and, for a model's write, when the id holds an entry another kept
    (`keep`)."""
    try:
        entry = CatalogueEntry.model_validate({**fields, "kind": _kind(kind), "source": source})
    except ValidationError as e:
        raise CatalogueRefused(_first_error(e)) from None
    return keep(entry, by=by, agent=agent, via=via)


# ── from a file (Intake) ───────────────────────────────────────────────


class CatalogueIntake(BaseModel):
    """What a file of entries came to: the ids kept, and each row refused with why."""

    kind: CatalogueKind
    kept: list[str] = Field(default_factory=list)
    refused: list[str] = Field(default_factory=list)


_LISTS = ("aliases", "mastery", "skills", "prerequisites")


def _rows_of(data: bytes, filename: str) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CatalogueRefused(f"{filename} is not UTF-8 text; a catalogue file is JSON or CSV") from None
    stripped = text.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            loaded = json.loads(text)
        except ValueError as e:
            raise CatalogueRefused(f"{filename} is not JSON: {e}") from None
        found = loaded.get("entries") if isinstance(loaded, dict) else loaded
        if not isinstance(found, list) or not all(isinstance(r, dict) for r in found):
            raise CatalogueRefused(f"{filename} holds no list of entries (a list of objects, or one under 'entries')")
        return found
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "id" not in reader.fieldnames or "name" not in reader.fieldnames:
        raise CatalogueRefused(f"{filename} is a CSV with no 'id' and 'name' columns")
    out = []
    for r in reader:
        row: dict[str, Any] = {k: (v or "").strip() for k, v in r.items() if k}
        for k in _LISTS:
            if k in row:
                row[k] = [w.strip() for w in row[k].split(";") if w.strip()]
        out.append({k: v for k, v in row.items() if v not in ("", [])})
    return out


def intake(kind: str, data: bytes, filename: str, *, by: str) -> CatalogueIntake:
    """A file of entries of one kind kept in the open project's catalogue:
    every row that is an entry kept in the name of `by` with the file as its
    source, every other row refused with its reason. A list holds its items
    in JSON; in CSV it is one column with the items split by `;`."""
    _kind(kind)
    who = _name(by)
    if not who:
        raise CatalogueRefused("a catalogue file is taken in a person's name")
    found = _rows_of(data, filename or "the file")
    if len(found) > MAX_FILE_ROWS:
        raise CatalogueRefused(f"{filename} holds {len(found)} rows; a file takes {MAX_FILE_ROWS} at most")
    out = CatalogueIntake(kind=kind)  # type: ignore[arg-type]
    good: list[CatalogueEntry] = []
    at = _now()
    for i, r in enumerate(found, start=1):
        try:
            e = CatalogueEntry.model_validate({**r, "kind": kind, "by": who, "at": at, "agent": "person", "via": None,
                                               "source": r.get("source") or f"the file {filename}"})
        except ValidationError as err:
            out.refused.append(f"row {i}: {_first_error(err)}")
            continue
        good.append(e)
        out.kept.append(e.id)
    if good:
        db.run(_keep(projects.current(), good))
    return out


# ── the readers' shapes ────────────────────────────────────────────────


def _entries(kind: str) -> list[CatalogueEntry]:
    """The open project's entries, or none where no project is open."""
    try:
        return listed(kind)
    except projects.ProjectRequired:
        return []


def as_hosts() -> list[dict[str, Any]]:
    """The strains as geneOS's hosts and the proposer's: id, name, species,
    the chemical set and the other names."""
    return [{"id": e.id, "name": e.name, "species": e.species, "program": e.program, "aliases": list(e.aliases)}
            for e in _entries("strain")]


def as_strain_aliases() -> dict[str, str]:
    """Each other name of a strain, and its name, lower-cased, to its id."""
    out: dict[str, str] = {}
    for e in _entries("strain"):
        for name in (e.name, *e.aliases):
            out.setdefault(name.strip().lower(), e.id)
    return out


def as_products() -> list[dict[str, Any]]:
    """The products as ProtParam and the proposer read them: the proposer
    reads a product's class and where the cells leave it."""
    return [{"id": e.id, "name": e.name, "category": e.category, "location": e.location, "sequence": e.sequence,
             "sequenceSource": e.sequenceSource, "source": e.source} for e in _entries("product")]


def as_skills() -> list[dict[str, Any]]:
    """The skills as Guild reads them (guild.projection): what each is and
    what mastery means, and the policy its levels read, None where the entry
    holds none (competence.unrated)."""
    return [{"id": e.id, "name": e.name, "family": e.family, "summary": e.summary, "mastery": list(e.mastery),
             "criticality": e.criticality, "recencyDays": e.recencyDays, "supervisedRuns": e.supervisedRuns,
             "prerequisites": list(e.prerequisites)} for e in _entries("skill")]


def as_lessons() -> list[dict[str, Any]]:
    return [{"lessonId": e.id, "id": e.id, "title": e.name, "skills": list(e.skills)} for e in _entries("lesson")]


async def _count(project_id: str) -> dict[str, int]:
    async with db.session() as s:
        found = (await s.execute(select(t.catalogue.c.kind).where(t.catalogue.c.project_id == project_id))).scalars()
        out = {k: 0 for k in KINDS}
        for k in found:
            out[k] = out.get(k, 0) + 1
        return out


def counts() -> dict[str, int]:
    """How many entries the open project's catalogues hold, by kind."""
    return db.run(_count(projects.current()))
