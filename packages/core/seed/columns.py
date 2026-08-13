"""Model field → SQL column. This is where the DDL comes from.

Nothing in this package writes a `CREATE TABLE` by hand. A table is derived by
walking a Pydantic model's `model_fields` and mapping each annotation onto a
column, so a field added to a model appears in the DDL the next time it is
emitted and cannot be forgotten (CLAUDE.md, "Do not hand-maintain a type in
both"). The mapping is deliberately small and total:

    str                       TEXT
    bool                      BOOLEAN
    int                       BIGINT
    float                     DOUBLE
    StrEnum / Literal[str…]   TEXT     + CHECK (col IN (…))
    Literal[int…]             SMALLINT + CHECK (col IN (…))
    X | None                  the same column, nullable
    scalar | scalar           ONE COLUMN PER ARM + "exactly one is non-null"
    tuple[T, …] (fixed)       JSON     + CHECK on the array's length
    anything else             JSON

Two of those lines carry an argument.

**Enums are `TEXT` with a `CHECK`, not `CREATE TYPE … AS ENUM`.** Both are
derived from the same model and both refuse an invented value. The check
constraint wins on two counts: adding a member to `Provenance` regenerates as a
new `CHECK`, where a native enum would need an `ALTER TYPE` migration that this
generator does not write; and a check constraint survives translation to the
SQLite dialect, which is what makes the generated schema *executable* in a test
suite that has no Postgres server (see `dialect.py`).

**`float | str` becomes two columns, not one JSON column.**
`ExtractionRecord.value` is `float | str` because categorical records exist —
`kinase_identity` and `glycan_species` carry a string, and 30 of the 134 seeded
records do. Collapsing both arms into JSON would make `avg(value)` impossible
over the numeric ones, which is most of what a records table is for. Two typed
columns with a check that exactly one is populated keeps the numbers numeric,
keeps the strings strings, and makes the arm a record is on a fact the database
knows rather than something a reader has to infer from the value's shape.

Containers are JSON rather than SQL arrays for one reason: an array column has
to be adapted by the driver (`psycopg` turns a Python list into `text[]`), and
this phase has no Postgres server to prove that adaptation against. A JSON
column is packed by `json.dumps` in this process, which is testable here and
identical under both dialects. `jsonb` is queryable — `authors ? 'Kim'`,
`jsonb_array_elements_text(topics)` — so little is given up.
"""

from __future__ import annotations

import enum
import keyword
import operator
import types
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from functools import reduce
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

__all__ = [
    "Column",
    "Logical",
    "SplitGroup",
    "Table",
    "columns_for_model",
    "split_groups",
    "sql_column_name",
]


class Logical(enum.StrEnum):
    """A column type before any dialect has spelled it.

    `TIMESTAMP` is reachable only from a synthetic column; no model field maps
    to it, because no model field is a timestamp — `AuditEvent.at` is a string
    in the corpus and stays one.
    """

    TEXT = "text"
    SMALLINT = "smallint"
    BIGINT = "bigint"
    DOUBLE = "double"
    BOOLEAN = "boolean"
    JSON = "json"
    TIMESTAMP = "timestamp"


#: Suffix a split-union column gets, by the arm it holds. `value: float | str`
#: becomes `value_num` and `value_txt`.
_ARM_SUFFIX: dict[Logical, str] = {
    Logical.TEXT: "txt",
    Logical.DOUBLE: "num",
    Logical.BIGINT: "int",
    Logical.SMALLINT: "int",
    Logical.BOOLEAN: "bool",
}


@dataclass(frozen=True)
class Column:
    """One column, and everything a dialect needs to render it.

    `field` is the model field it was derived from, or None for the handful of
    synthetic columns (`registry.SYNTHETIC`), which must carry a `why`.
    """

    name: str
    logical: Logical
    nullable: bool
    field: str | None = None
    allowed: tuple[str | int, ...] | None = None
    json_arity: int | None = None
    identity: bool = False
    sql_default: str | None = None
    references: tuple[str, str] | None = None
    why: str | None = None

    @property
    def derived(self) -> bool:
        """True when a model field is responsible for this column existing."""
        return self.field is not None


@dataclass(frozen=True)
class SplitGroup:
    """The columns one `scalar | scalar` field became.

    `required` decides whether the table-level check reads "exactly one of these
    is non-null" or "at most one" — a `float | str` that may be absent is a
    different promise from one that may not.
    """

    field: str
    columns: tuple[str, ...]
    required: bool


@dataclass(frozen=True)
class Table:
    """A table, its columns, and the constraints that are not per-column."""

    name: str
    columns: tuple[Column, ...]
    model: type[BaseModel] | None = None
    primary_key: tuple[str, ...] = ()
    unique: tuple[tuple[str, ...], ...] = ()
    indexes: tuple[tuple[str, ...], ...] = ()
    #: The split-union fields. Rendered as table-level CHECKs because they span
    #: columns.
    splits: tuple[SplitGroup, ...] = ()
    append_only: bool = False
    doc: str = ""
    #: Model fields deliberately not given a column here, with the reason.
    externalised: dict[str, str] = dataclass_field(default_factory=dict)

    def by_name(self, name: str) -> Column:
        for col in self.columns:
            if col.name == name:
                return col
        raise KeyError(f"{self.name} has no column {name!r}")

    @property
    def identity_column(self) -> Column | None:
        for col in self.columns:
            if col.identity:
                return col
        return None


def sql_column_name(field_name: str) -> str:
    """Undo the trailing-underscore escape Python needs and SQL does not.

    `AuditEvent.from_` exists only because `from` is a Python keyword; on the
    wire it is `from` (an explicit Pydantic alias) and in SQL it is `"from"`,
    quoted like every other identifier this package emits. The rule is
    mechanical — strip one trailing underscore when what is left is a Python
    keyword — so a future `class_` or `import_` needs no new special case.
    """
    if field_name.endswith("_") and keyword.iskeyword(field_name[:-1]):
        return field_name[:-1]
    return field_name


def _split_optional(annotation: Any) -> tuple[Any, bool]:
    """Peel `| None` off an annotation, reporting whether it was there."""
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        args = get_args(annotation)
        arms = tuple(a for a in args if a is not type(None))
        if len(arms) == len(args):
            return annotation, False
        if len(arms) == 1:
            return arms[0], True
        # Rebuilt with `|` rather than `Union[...]`: this is a value being
        # constructed at runtime, not an annotation being written.
        return reduce(operator.or_, arms), True
    return annotation, False


def _literal_type(annotation: Any) -> tuple[Logical, tuple[str | int, ...]] | None:
    """`Literal['a', 'b']` and `Literal[1, 2]`, which the models use for both."""
    if get_origin(annotation) is not Literal:
        return None
    members = get_args(annotation)
    if all(isinstance(m, str) for m in members):
        return Logical.TEXT, tuple(str(m) for m in members)
    if all(isinstance(m, bool) for m in members):
        return None
    if all(isinstance(m, int) for m in members):
        return Logical.SMALLINT, tuple(int(m) for m in members)
    return None


def _scalar_type(annotation: Any) -> tuple[Logical, tuple[str | int, ...] | None] | None:
    """The logical type of a scalar annotation, or None if it is not scalar.

    Order matters: `bool` is a subclass of `int` in Python and must be tested
    first, or every boolean in the schema becomes a `BIGINT`.
    """
    if annotation is bool:
        return Logical.BOOLEAN, None
    if annotation is str:
        return Logical.TEXT, None
    if annotation is int:
        return Logical.BIGINT, None
    if annotation is float:
        return Logical.DOUBLE, None
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return Logical.TEXT, tuple(str(m.value) for m in annotation)
    literal = _literal_type(annotation)
    if literal is not None:
        return literal
    return None


def _fixed_tuple_arity(annotation: Any) -> int | None:
    """`tuple[float, float]` is a pair and the database can say so.

    `ParameterDef.range` is the only one in the seeded models, and a range that
    can hold three numbers is not a range.
    """
    if get_origin(annotation) is not tuple:
        return None
    args = get_args(annotation)
    if not args or Ellipsis in args:
        return None
    return len(args)


def _columns_for_field(name: str, info: FieldInfo) -> tuple[Column, ...]:
    annotation, optional = _split_optional(info.annotation)
    nullable = optional or not info.is_required()
    column_name = sql_column_name(name)

    scalar = _scalar_type(annotation)
    if scalar is not None:
        logical, allowed = scalar
        return (
            Column(
                name=column_name,
                logical=logical,
                nullable=nullable,
                field=name,
                allowed=allowed,
            ),
        )

    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        arms = [(_scalar_type(a), a) for a in get_args(annotation)]
        if all(s is not None for s, _ in arms):
            out: list[Column] = []
            for scalar_arm, _ in arms:
                assert scalar_arm is not None
                logical, allowed = scalar_arm
                out.append(
                    Column(
                        name=f"{column_name}_{_ARM_SUFFIX[logical]}",
                        logical=logical,
                        # Nullable per column; the table-level check is what
                        # says exactly one of them holds the value.
                        nullable=True,
                        field=name,
                        allowed=allowed,
                    )
                )
            return tuple(out)

    return (
        Column(
            name=column_name,
            logical=Logical.JSON,
            nullable=nullable,
            field=name,
            json_arity=_fixed_tuple_arity(annotation),
        ),
    )


def columns_for_model(
    model: type[BaseModel],
    *,
    skip: frozenset[str] = frozenset(),
) -> tuple[Column, ...]:
    """Every column a model implies, in the model's own field order.

    `skip` names fields that are externalised into a child table — today only
    `ExtractionRecord.audit`, which becomes `audit_event`. A skipped field is
    recorded on the `Table` with its reason, so "this model field has no
    column" is a stated decision rather than an omission.
    """
    out: list[Column] = []
    for name, info in model.model_fields.items():
        if name in skip:
            continue
        out.extend(_columns_for_field(name, info))

    # Two columns of one name is un-creatable DDL, and it is derived rather than
    # written, so nothing downstream would catch it: the emitter would print it,
    # `schema.sql` would look fine, and Postgres would reject the whole file with
    # `duplicate column name` at deploy time.
    #
    # Three annotation shapes reach it. A union whose arms share a suffix —
    # `AnalysisMethod | str` (two TEXT arms, both `_txt`) or `int | Literal[1, 2]`
    # (BIGINT and SMALLINT, both `_int`). And a model field named `row_id`, which
    # collides with the synthetic identity column. No model does any of this
    # today; the point is that if one starts to, it fails HERE, naming the model
    # and the field, rather than at deploy.
    seen: dict[str, str] = {}
    for col in out:
        if col.name in seen:
            raise ValueError(
                f"{model.__name__} derives two columns named {col.name!r} "
                f"(from fields {seen[col.name]!r} and {col.field or col.name!r}). "
                "A union whose arms share a column suffix, or a field colliding with a "
                "synthetic column, produces DDL Postgres will not create. Rename the field "
                "or give the arms distinct suffixes."
            )
        seen[col.name] = col.field or col.name
    return tuple(out)


def split_groups(model: type[BaseModel], columns: tuple[Column, ...]) -> tuple[SplitGroup, ...]:
    """Which columns came from one `scalar | scalar` field.

    Two or more columns sharing a `field` is exactly that case, and there is no
    other way for it to arise: every other annotation yields one column.
    """
    seen: dict[str, list[str]] = {}
    for col in columns:
        if col.field is not None:
            seen.setdefault(col.field, []).append(col.name)
    return tuple(
        SplitGroup(field=name, columns=tuple(cols), required=model.model_fields[name].is_required())
        for name, cols in seen.items()
        if len(cols) > 1
    )
