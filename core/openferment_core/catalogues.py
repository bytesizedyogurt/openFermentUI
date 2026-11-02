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
              (`category`) and, for a protein, its sequence
    skill     a Guild skill: its family, what it is and what mastery means
    lesson    a Primer lesson and the skills it counts toward

The readers take them in the shapes they always read (`as_*`): geneOS's hosts
and the strain aliases (module_stores), ProtParam's products, the proposer's
catalogue, Guild's projection. A catalogue holds names and words, never a
measured value: a number a paper reports is a record (ADR-006).

Entries arrive by the route (`POST /api/catalogues/{kind}`), by Postdoc's
`catalogue_write` (marked as the model's), or by Intake from a file of entries
(`POST /api/intake/catalogue`, JSON or CSV). Nothing here deletes an entry:
taking a person's entry out of a live instance is the owner's call.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select

from . import db, projects
from .db import models as t
from .db import rows

CatalogueKind = Literal["strain", "product", "skill", "lesson"]
KINDS: tuple[str, ...] = ("strain", "product", "skill", "lesson")
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
    # A product: its class as the proposer's rules read it, and a protein's sequence.
    category: str | None = Field(default=None, max_length=80)
    sequence: str | None = Field(default=None, max_length=20000)
    # Where the sequence was read, in words (a UniProt entry, a paper's table):
    # ProtParam computes from a sequence that names it, and from no other.
    sequenceSource: str | None = Field(default=None, max_length=400)
    # A skill: its family, what it is, what mastery of it means.
    family: str | None = Field(default=None, max_length=80)
    summary: str | None = Field(default=None, max_length=2000)
    mastery: list[str] = Field(default_factory=list, max_length=40)
    # A lesson: the skills it counts toward, by their ids.
    skills: list[str] = Field(default_factory=list, max_length=40)
    note: str | None = Field(default=None, max_length=2000)
    # Where the entry came from, in words: a person, a document, a file.
    source: str | None = Field(default=None, max_length=400)
    by: str = Field(default="", max_length=200)
    at: str = ""

    @field_validator("aliases", "mastery", "skills")
    @classmethod
    def _words(cls, v: list[str]) -> list[str]:
        out = [w.strip() for w in v if w and w.strip()]
        return list(dict.fromkeys(out))

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
        if (self.mastery or self.family) and self.kind != "skill":
            raise ValueError("a family and what mastery means belong to a skill")
        return self


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _row_id(kind: str, entry_id: str) -> str:
    return f"{kind}/{entry_id}"


def _kind(kind: str) -> str:
    if kind not in KINDS:
        raise CatalogueRefused(f"there is no catalogue of {kind!r}: the catalogues are {', '.join(KINDS)}")
    return kind


# ── the store ──────────────────────────────────────────────────────────


async def _listed(project_id: str, kind: str) -> list[CatalogueEntry]:
    async with db.session() as s:
        bodies = await rows.bodies(s, t.catalogue, project_id, t.catalogue.c.kind == kind)
    return sorted((CatalogueEntry.model_validate(b) for b in bodies), key=lambda e: e.id)


def listed(kind: str) -> list[CatalogueEntry]:
    """The open project's entries of one kind, by id."""
    return db.run(_listed(projects.current(), _kind(kind)))


def get(kind: str, entry_id: str) -> CatalogueEntry:
    found = next((e for e in listed(kind) if e.id == entry_id), None)
    if found is None:
        raise CatalogueEntryNotFound(f"the project's {kind} catalogue holds no {entry_id}")
    return found


async def _keep(project_id: str, entries: list[CatalogueEntry]) -> None:
    async with db.session() as s:
        for e in entries:
            await rows.put(s, t.catalogue, project_id, _row_id(e.kind, e.id), e.model_dump(mode="json"), by=e.by,
                           kind=e.kind)


def keep(entry: CatalogueEntry, *, by: str) -> CatalogueEntry:
    """An entry kept in the open project's catalogue of its kind, in the name
    of `by`; an entry already held under the id is replaced by it."""
    who = (by or "").strip()
    if not who:
        raise CatalogueRefused("a catalogue entry is kept in a person's or a model's name")
    kept = entry.model_copy(update={"by": who, "at": _now()})
    db.run(_keep(projects.current(), [kept]))
    return kept


def _first_error(err: ValidationError) -> str:
    first = err.errors()[0]
    where = ".".join(str(p) for p in first.get("loc", ())) or "the entry"
    return f"{where}: {first.get('msg')}"


def keep_fields(kind: str, fields: dict[str, Any], *, by: str, source: str) -> CatalogueEntry:
    """An entry made from fields and kept, for a caller that holds no entry
    (Postdoc's `catalogue_write`): refused in words when the kind does not
    take them."""
    try:
        entry = CatalogueEntry.model_validate({**fields, "kind": _kind(kind), "source": source})
    except ValidationError as e:
        raise CatalogueRefused(_first_error(e)) from None
    return keep(entry, by=by)


# ── from a file (Intake) ───────────────────────────────────────────────


class CatalogueIntake(BaseModel):
    """What a file of entries came to: the ids kept, and each row refused with why."""

    kind: CatalogueKind
    kept: list[str] = Field(default_factory=list)
    refused: list[str] = Field(default_factory=list)


_LISTS = ("aliases", "mastery", "skills")


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
    who = (by or "").strip()
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
            e = CatalogueEntry.model_validate({**r, "kind": kind, "by": who, "at": at,
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
    """The products as ProtParam and the proposer read them."""
    return [{"id": e.id, "name": e.name, "category": e.category, "sequence": e.sequence,
             "sequenceSource": e.sequenceSource, "source": e.source} for e in _entries("product")]


def as_skills() -> list[dict[str, Any]]:
    return [{"id": e.id, "name": e.name, "family": e.family, "summary": e.summary, "mastery": list(e.mastery)}
            for e in _entries("skill")]


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
