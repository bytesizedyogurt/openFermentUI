"""The generated Postgres DDL, read back with somebody else's SQL parser.

Split out of `test_seed.py` because it needs `sqlglot`, and a module-level
`importorskip` skips the module it is in: without this split, a machine with no
sqlglot would silently skip the tests that load the real corpus and prove the
append-only trigger fires, which are the ones that matter most.

Everything here PARSES the emitted SQL. Nothing here executes it — there is no
Postgres server in this environment, and `test_seed.py` says what is executed
instead and what that does and does not cover.
"""

from __future__ import annotations

from typing import Any

import pytest

import seed

sqlglot = pytest.importorskip("sqlglot", reason="sqlglot parses the emitted Postgres DDL")
from sqlglot import expressions as exp  # noqa: E402 — only importable after the skip


def _parsed() -> list[Any]:
    return [sqlglot.parse_one(s, read="postgres") for s in seed.schema_statements(seed.POSTGRES)]


def test_every_postgres_statement_parses() -> None:
    for statement, tree in zip(seed.schema_statements(seed.POSTGRES), _parsed(), strict=True):
        assert tree is not None, statement


def test_only_the_trigger_function_is_opaque_to_the_parser() -> None:
    """Honesty check on the previous test.

    sqlglot parses a plpgsql body as an opaque `Command` — it does not read
    inside `$of_append_only$ … $$`. Exactly one statement is allowed to be
    opaque, so if a future change hides a table behind something the parser
    cannot see, this fails.
    """
    opaque = [t for t in _parsed() if isinstance(t, exp.Command)]
    assert len(opaque) == 1
    assert "of_append_only" in opaque[0].sql()


def test_the_parsed_ddl_declares_the_columns_the_models_imply() -> None:
    """Read the emitted SQL back with somebody else's parser and compare.

    This is the strongest statement available without a server: not "the
    generator printed something", but "an independent SQL parser agrees the
    printed schema has exactly these columns, in this order".
    """
    by_name = {t.name: t for t in seed.tables()}
    seen: set[str] = set()
    for tree in _parsed():
        if not isinstance(tree, exp.Create) or tree.kind != "TABLE":
            continue
        name = tree.this.this.name
        schema = tree.find(exp.Schema)
        assert schema is not None
        found = [c.name for c in schema.expressions if isinstance(c, exp.ColumnDef)]
        assert found == [c.name for c in by_name[name].columns], name
        seen.add(name)
    assert seen == set(by_name)


def test_not_null_and_checks_survive_into_the_sql() -> None:
    table = next(
        t
        for t in _parsed()
        if isinstance(t, exp.Create) and t.kind == "TABLE" and t.this.this.name == "records"
    )
    schema = table.find(exp.Schema)
    assert schema is not None
    columns = {c.name: c for c in schema.expressions if isinstance(c, exp.ColumnDef)}

    def kinds(name: str) -> set[type[Any]]:
        return {type(c.kind) for c in columns[name].constraints}

    assert exp.NotNullColumnConstraint in kinds("id")
    assert exp.CheckColumnConstraint in kinds("provenance")
    # An optional field must NOT be NOT NULL, or `organism: str | None` would
    # stop being optional the moment it reached the database.
    assert exp.NotNullColumnConstraint not in kinds("organism")
    assert exp.NotNullColumnConstraint not in kinds("value_num")
    # The split-union rule is a table constraint, not a column one.
    constraints = [c for c in schema.expressions if isinstance(c, exp.Constraint)]
    assert any("value_one_arm" in c.sql() for c in constraints)


def test_the_current_view_exists_only_for_the_superseding_table() -> None:
    views = [t.this.this.name for t in _parsed() if isinstance(t, exp.Create) and t.kind == "VIEW"]
    assert views == ["records_current"]


def test_two_columns_of_one_name_are_refused_at_derivation() -> None:
    """Un-creatable DDL, caught where it is derived rather than at deploy.

    Nothing downstream would notice: the emitter prints it, `schema.sql` looks
    plausible, and Postgres rejects the whole file with `duplicate column name`
    when someone finally runs it. No model does this today — the guard exists so
    that the day one does, it fails naming the model and the field.
    """
    from pydantic import BaseModel

    from openferment_core.schema.ontology import AnalysisMethod
    from seed.columns import columns_for_model

    class SharesASuffix(BaseModel):
        # Two TEXT arms, so both want to be `x_txt`.
        x: AnalysisMethod | str | None = None

    with pytest.raises(ValueError, match="two columns named 'x_txt'"):
        columns_for_model(SharesASuffix)

    class DistinctSuffixes(BaseModel):
        # The shape ExtractionRecord.value actually uses: `_num` and `_txt`.
        v: float | str | None = None

    assert [c.name for c in columns_for_model(DistinctSuffixes)] == ["v_num", "v_txt"]
