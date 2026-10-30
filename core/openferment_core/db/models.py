"""The `openferment` schema's tables (execution prompt §7.4; migration 0001).

Every scientific row carries `project_id`, `created_by` (a person, a model id
or `system`) and `created_at`. The keys a store looks a row up by are columns;
the rest of the row is `body`, the Pydantic model of `models.py` dumped as
JSON, so the Pydantic models stay the one description of a record's content
and these tables hold and index it. The content columns are `json`, which
keeps the text as written: an object's keys keep their order (a simulation's
series are drawn in it) and a negative zero stays one. Nothing here queries
inside a body. Artifact ids keep the sha256 of their
canonical inputs, so replay works unchanged.

Tables are SQLAlchemy Core: the stores read and write whole rows by key and
need no object mapping.
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP

from .engine import SCHEMA

metadata = MetaData(
    schema=SCHEMA,
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s",
        "pk": "pk_%(table_name)s",
    },
)


def _when(name: str = "created_at") -> Column:
    # The moment the row is written: now() would give every row of one
    # transaction its start.
    return Column(name, TIMESTAMP(timezone=True), nullable=False, server_default=func.clock_timestamp())


def _project(primary: bool = False) -> Column:
    return Column(
        "project_id",
        Text,
        ForeignKey(f"{SCHEMA}.projects.id", ondelete="RESTRICT"),
        nullable=False,
        primary_key=primary,
        index=not primary,
    )


def _body() -> Column:
    return Column("body", JSON, nullable=False)


def _scoped(name: str, *columns: Column | Index | ForeignKeyConstraint, updated: bool = False) -> Table:
    """A project's table of rows kept whole by id: (project_id, id) is the key."""
    extra = [_when("updated_at")] if updated else []
    return Table(
        name,
        metadata,
        _project(primary=True),
        Column("id", Text, primary_key=True),
        *columns,
        _body(),
        Column("created_by", Text, nullable=False),
        _when(),
        *extra,
    )


# ── Projects (ADR-005) ─────────────────────────────────────────────────────

projects = Table(
    "projects",
    metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("description", Text, nullable=False, server_default=""),
    # What a project sets for itself: Guild's policy, today.
    Column("settings", JSON, nullable=False, server_default=text("'{}'::json")),
    Column("created_by", Text, nullable=False),
    _when(),
)

# A stub until accounts exist (§13 question 9).
project_members = Table(
    "project_members",
    metadata,
    _project(primary=True),
    Column("person", Text, primary_key=True),
    Column("role", Text, nullable=False, server_default="member"),
    _when(),
)

# ── Literature (stage 3 fills these) ──────────────────────────────────────

documents_link = Table(
    "documents_link",
    metadata,
    _project(primary=True),
    # The kit's document id, in schema sci_rag.
    Column("document_id", Text, primary_key=True),
    # The selection that stored it: who chose it, from what, and why.
    Column("selection", JSON, nullable=False),
    Column("created_by", Text, nullable=False),
    _when(),
)

records = Table(
    "records",
    metadata,
    _project(primary=True),
    Column("id", Text, primary_key=True),
    Column("version", Integer, primary_key=True, server_default="1"),
    Column("document_id", Text, nullable=False),
    Column("field", Text, nullable=False),
    Column("value", Float),
    Column("value_text", Text),
    Column("unit", Text),
    Column("basis", Text),
    Column("quote", Text, nullable=False),
    Column("section", Text),
    Column("status", Text, nullable=False),
    Column("provenance", Text, nullable=False),
    _body(),
    Column("created_by", Text, nullable=False),
    _when(),
    Index(None, "project_id", "field"),
    Index(None, "project_id", "document_id"),
)

# One row per decision, in the order made; the newest for a record holds.
decisions = Table(
    "decisions",
    metadata,
    Column("seq", BigInteger, Identity(), primary_key=True),
    _project(),
    Column("record_id", Text, nullable=False),
    _body(),
    # The candidate the decision was about, as it stood when decided: a
    # later extraction run replaces the candidates, and a decision about a
    # candidate nobody can see any more would be a decision about nothing.
    Column("record", JSON),
    Column("created_by", Text, nullable=False),
    _when(),
    Index(None, "project_id", "record_id"),
)

# An extraction run's output for one document, awaiting review.
candidates = Table(
    "candidates",
    metadata,
    _project(primary=True),
    Column("document_id", Text, primary_key=True),
    # `model` for the extraction model's run, `hand` for a person's entries.
    Column("source", Text, primary_key=True),
    _body(),
    Column("created_by", Text, nullable=False),
    _when(),
    _when("updated_at"),
)

# ── Engine and studies (stages 4 and 5 fill these) ────────────────────────

flowsheets = _scoped(
    "flowsheets",
    Column("schema_version", Text, nullable=False),
    Column("recipe", Text),
)

runs = _scoped(
    "runs",
    Column("flowsheet_id", Text),
    Column("scenario_id", Text),
    Column("status", Text, nullable=False),
    Index(None, "project_id", "scenario_id"),
)

artifacts = _scoped(
    "artifacts",
    Column("tool", Text, nullable=False),
    Column("version", Text, nullable=False),
    Column("output_hash", Text, nullable=False),
    Index(None, "project_id", "tool"),
)

scenarios = _scoped("scenarios", Column("pinned", Boolean, nullable=False, server_default="false"), updated=True)

comparisons = _scoped("comparisons")

# A parameter override (D3): one value per key within a scope.
overrides = Table(
    "overrides",
    metadata,
    _project(primary=True),
    Column("scope", Text, primary_key=True),
    Column("key", Text, primary_key=True),
    _body(),
    Column("created_by", Text, nullable=False),
    _when(),
)

fits = _scoped("fits")

# pureOS trains: `made` in the Builder, `kept` from a model's run.
trains = _scoped("trains", Column("kind", Text, nullable=False), updated=True)

runbooks = _scoped("runbooks", updated=True)

runbook_locks = Table(
    "runbook_locks",
    metadata,
    _project(primary=True),
    Column("runbook_id", Text, primary_key=True),
    Column("lock_hash", Text, nullable=False),
    Column("locked_at", TIMESTAMP(timezone=True), nullable=False),
    Column("created_by", Text, nullable=False),
    _when(),
)

depositions = _scoped("depositions", Column("runbook_id", Text), Index(None, "project_id", "runbook_id"))

measured_evidence = _scoped("measured_evidence")

# ── Postdoc ───────────────────────────────────────────────────────────────

conversations = _scoped("conversations", Column("title", Text, nullable=False, server_default=""), updated=True)

turns = _scoped(
    "turns",
    Column("conversation_id", Text, nullable=False),
    Column("seq", Integer, nullable=False),
    Column("status", Text, nullable=False),
    ForeignKeyConstraint(
        ["project_id", "conversation_id"],
        [f"{SCHEMA}.conversations.project_id", f"{SCHEMA}.conversations.id"],
        ondelete="CASCADE",
    ),
    Index(None, "project_id", "conversation_id", "seq"),
    updated=True,
)

tool_calls = Table(
    "tool_calls",
    metadata,
    Column("seq", BigInteger, Identity(), primary_key=True),
    _project(),
    Column("turn_id", Text),
    Column("tool", Text, nullable=False),
    Column("input", JSON, nullable=False),
    Column("result", JSON),
    Column("created_by", Text, nullable=False),
    _when(),
)

proposals = _scoped("proposals", Column("state", Text, nullable=False), updated=True)

jobs = _scoped("jobs", Column("kind", Text, nullable=False), Column("state", Text, nullable=False), updated=True)

# ── Guild and Primer ──────────────────────────────────────────────────────

guild_people = _scoped("guild_people", updated=True)

guild_evidence = _scoped(
    "guild_evidence",
    Column("person_id", Text, nullable=False),
    Column("skill_id", Text, nullable=False),
    Index(None, "project_id", "person_id"),
    updated=True,
)

guild_checks = _scoped("guild_checks", Column("state", Text, nullable=False), updated=True)

practice_scenarios = _scoped("practice_scenarios")

practice_sessions = _scoped("practice_sessions", updated=True)

# ── Every write, and every model call's cost ──────────────────────────────

audit = Table(
    "audit",
    metadata,
    Column("seq", BigInteger, Identity(), primary_key=True),
    # Null for what belongs to no project: a project's own creation, the budget.
    Column("project_id", Text, ForeignKey(f"{SCHEMA}.projects.id", ondelete="RESTRICT"), index=True),
    # `model`, `person` or `system`; `who` is the model id or the person's name.
    Column("agent", Text, nullable=False),
    Column("who", Text, nullable=False),
    Column("module", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("state", Text, nullable=False),
    Column("target", Text),
    # The whole AuditEntry.
    _body(),
    _when(),
)

# The day's spend against the cap (spend.py): reservations, then what they cost.
spend = Table(
    "spend",
    metadata,
    Column("seq", BigInteger, Identity(), primary_key=True),
    Column("day", Date, nullable=False, index=True),
    Column("role", Text, nullable=False),
    Column("usd", Numeric(14, 6), nullable=False),
    # `reserved` until settled; `settled` and `charged` are spent.
    Column("state", Text, nullable=False),
    Column("reservation", Text, unique=True),
    # The project the call was made in, when there was one: an attribution,
    # kept without a foreign key, because the cap is the machine's and a call
    # is charged even where its project is not a row (a live test's).
    Column("project_id", Text),
    _when(),
    Column("expires_at", TIMESTAMP(timezone=True)),
)
