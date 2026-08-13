"""What is loaded, where it lands, and the five columns no model implies.

Everything in this module is a DECLARATION rather than a derivation, and it is
kept in one short file so that the boundary is visible: the *shape* of every
table comes from the Pydantic models (see `columns.py`), and what is written
here is only the policy the models cannot state — which collections exist, what
their tables are called, which table is append-only, which field is externalised
into a child table, and the bookkeeping columns an append-only store needs that
are not facts about the corpus.

The synthetic columns each carry a `why`. A test asserts that every column in
the emitted schema is either derived from a model field or declared here with a
reason, so an undocumented hand-written column cannot survive review.

── NO CROSS-ENTITY FOREIGN KEYS, DELIBERATELY ─────────────────────────────
`records.paper_id` is not a `REFERENCES papers (id)`, and neither are
`cites_record_id`, `source_record_id` or the ids inside a scenario assumption.
One reason, and it is enough.

The models do not state those relationships — `paper_id` is a `str` — so a
foreign key would have to be inferred from the name, and "any column ending in
`_id` points at the table its prefix names" is a guess that is wrong the first
time a `component_tag` or a `curation_ref` looks like one. The relationship the
schema does not declare is not the schema's to enforce.

This used to give a second reason and call it the real one: that a foreign key
would reject a record whose paper is catalogued but not yet ingested. That is
not true of this corpus and was never measured. `catalogued` describes how much
of a paper has been INGESTED; the paper is a row in `papers` either way, so the
constraint would be satisfied. Measured on the seeded corpus: 0 of 134 records
name a paper absent from `papers.json`, no `citesRecordId` dangles, and all 15
scenario-assumption record references resolve. The state that argument describes
is one the corpus may reach, and it was written as a state the corpus is in.

Which is not an argument FOR adding the key later: when the corpus does hold a
reference it cannot satisfy, reporting it is the referee's job, and a loader
that refuses the whole corpus over one dangling id has made the gap harder to
see rather than easier. But that is a claim about what SHOULD happen, and it is
not evidence about what does. The one
foreign key that IS emitted — `audit_event.record_row_id` — is structural: it is
a parent link the loader creates itself, not a claim about the literature.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from openferment_core import schema as S

from .columns import Column, Logical, Table, columns_for_model, split_groups

__all__ = [
    "AUDIT",
    "COLLECTIONS",
    "Collection",
    "tables",
]


@dataclass(frozen=True)
class Collection:
    """One `data/corpus/<name>.json` file and the table it loads into.

    `name` is the file stem AND the key `src/data/source.ts` fetches under the
    "api" backend (`GET {base}/{name}.json`), so the three pieces agree without
    a fourth naming scheme in the middle.
    """

    name: str
    table: str
    model: type[BaseModel]
    append_only: bool = False
    doc: str = ""


COLLECTIONS: tuple[Collection, ...] = (
    Collection("papers", "papers", S.Paper, doc="Corpus entries (OF-COR-001 §1)."),
    Collection(
        "records",
        "records",
        S.ExtractionRecord,
        append_only=True,
        doc=(
            "Extraction records. APPEND-ONLY: a correction is a new row whose "
            "`supersedes` points at the row it replaces."
        ),
    ),
    Collection("ontology", "ontology", S.ParameterDef, doc="Parameter ontology v1 (§17)."),
    Collection("strains", "strains", S.Strain, doc="Hosts a measurement was made in."),
    Collection("protocols", "protocols", S.Protocol, doc="Protocols and their versions."),
    Collection(
        "scenarios", "scenarios", S.Scenario, doc="Cost scenarios. COST_MODELS stays in TS."
    ),
    Collection("learn", "learn_modules", S.LearnModule, doc="Learn track modules."),
)


@dataclass(frozen=True)
class ChildTable:
    """A list-valued field lifted out of its parent into a table of its own."""

    parent: str
    field: str
    table: str
    model: type[BaseModel]
    append_only: bool
    why: str
    doc: str


AUDIT = ChildTable(
    parent="records",
    field="audit",
    table="audit_event",
    model=S.AuditEvent,
    append_only=True,
    why=(
        "The migration brief asks for 'an audit_event table mirroring AuditEvent'. "
        "Kept as the ONLY home for the audit trail rather than mirrored alongside a "
        "JSON copy on `records`: two copies of the same events is two things to keep "
        "in step, which is the failure this migration exists to remove. A record's "
        "`audit` list is reassembled from these rows in `ordinal` order on the way out."
    ),
    doc=(
        "One AuditEvent, mirroring `ExtractionRecord.audit`. Append-only: the audit "
        "trail of an append-only table cannot itself be editable."
    ),
)


#: Columns that no model field implies. Every one of them exists because the
#: store is append-only or because a JSON array has an order that SQL rows do
#: not. These five are the honest answer to "what could not be derived".
SYNTHETIC: dict[str, tuple[Column, ...]] = {
    "records": (
        Column(
            name="row_id",
            logical=Logical.BIGINT,
            nullable=False,
            identity=True,
            why=(
                "Surrogate key. `ExtractionRecord.id` stops being unique the moment a "
                "correction is appended — the corrected row carries the SAME record id "
                "— so the natural key cannot be the primary key. Nothing outside this "
                "table's own supersession chain refers to a row_id."
            ),
        ),
        Column(
            name="supersedes",
            logical=Logical.BIGINT,
            nullable=True,
            references=("records", "row_id"),
            why=(
                "The correction link, pointing BACKWARD from the new row to the one it "
                "replaces. Backward because the alternative — a `superseded_by` on the "
                "older row — would have to be filled in by an UPDATE, and UPDATE is "
                "exactly what this table forbids. UNIQUE, so a chain cannot fork and "
                "leave `records_current` ambiguous."
            ),
        ),
        Column(
            name="inserted_at",
            logical=Logical.TIMESTAMP,
            nullable=False,
            sql_default="now",
            why=(
                "When the row reached the store. NOT the same clock as `AuditEvent.at`, "
                "which is corpus data about when a curator acted; this one is the "
                "database's own record of arrival order and is the only thing that can "
                "order two rows the loader wrote in the same batch."
            ),
        ),
    ),
    "audit_event": (
        Column(
            name="record_row_id",
            logical=Logical.BIGINT,
            nullable=False,
            references=("records", "row_id"),
            why=(
                "Parent link for the externalised array. Points at the ROW, not at the "
                "record id: two rows may share a record id across a correction, and an "
                "audit event belongs to one of them."
            ),
        ),
        Column(
            name="ordinal",
            logical=Logical.BIGINT,
            nullable=False,
            why=(
                "Position in `ExtractionRecord.audit`. A JSON array is ordered and SQL "
                "rows are not, so without this the trail comes back in whatever order "
                "the plan produced and the record no longer round-trips."
            ),
        ),
    ),
}


def _collection_table(collection: Collection) -> Table:
    skip = frozenset({AUDIT.field}) if collection.table == AUDIT.parent else frozenset()
    derived = columns_for_model(collection.model, skip=skip)
    synthetic = SYNTHETIC.get(collection.table, ())

    identity = tuple(c for c in synthetic if c.identity)
    trailing = tuple(c for c in synthetic if not c.identity)
    columns = identity + derived + trailing

    splits = split_groups(collection.model, derived)

    if collection.append_only:
        return Table(
            name=collection.table,
            columns=columns,
            model=collection.model,
            primary_key=(),  # the identity column carries it inline
            unique=(("supersedes",),),
            indexes=(("id",), ("paper_id",)),
            splits=splits,
            append_only=True,
            doc=collection.doc,
            externalised={AUDIT.field: AUDIT.why} if skip else {},
        )

    return Table(
        name=collection.table,
        columns=columns,
        model=collection.model,
        primary_key=("id",),
        splits=splits,
        doc=collection.doc,
    )


def _audit_table() -> Table:
    derived = columns_for_model(AUDIT.model)
    synthetic = SYNTHETIC[AUDIT.table]
    return Table(
        name=AUDIT.table,
        columns=synthetic + derived,
        model=AUDIT.model,
        primary_key=(synthetic[0].name, synthetic[1].name),
        append_only=AUDIT.append_only,
        doc=AUDIT.doc,
    )


def tables() -> tuple[Table, ...]:
    """Every table in the seed schema, in creation order.

    `records` precedes `audit_event` because the child references the parent.
    """
    out = [_collection_table(c) for c in COLLECTIONS]
    out.append(_audit_table())
    return tuple(out)
