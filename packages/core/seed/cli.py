"""Command line for the seed loader.

    python3 packages/core/seed/cli.py emit                 # regenerate schema.sql
    python3 packages/core/seed/cli.py check                # is schema.sql current?
    python3 packages/core/seed/cli.py load --dsn …         # into Postgres
    python3 packages/core/seed/cli.py load --sqlite out.db # into a local file

`check` is the gate that keeps the generated schema honest: it re-emits from the
models and diffs against the checked-in file, so a model change that nobody
regenerated fails rather than drifts. The test suite runs the same comparison.

Run straight out of the tree, the way `scripts/emit_schema.py` and
`scripts/validate_fixtures.py` are — the package is not installed in the repo's
CI path.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

if __package__ in (None, ""):  # invoked as a path, not as a module
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.ddl import emit
from seed.dialect import POSTGRES, SQLITE, Dialect
from seed.loader import load, read_corpus

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CORPUS = REPO / "data" / "corpus"
DEFAULT_OUT = HERE / "schema.sql"

DIALECTS: dict[str, Dialect] = {"postgres": POSTGRES, "sqlite": SQLITE}


def _emit(args: argparse.Namespace) -> int:
    dialect = DIALECTS[args.dialect]
    out = Path(args.out) if args.out else DEFAULT_OUT
    out.write_text(emit(dialect), "utf-8")
    print(f"  {out}")
    return 0


def _check(args: argparse.Namespace) -> int:
    dialect = DIALECTS[args.dialect]
    out = Path(args.out) if args.out else DEFAULT_OUT
    if not out.exists():
        print(f"✗ {out} does not exist. Run `emit`.")
        return 1
    current = out.read_text("utf-8")
    fresh = emit(dialect)
    if current == fresh:
        print(f"✓ {out.name} matches the models.")
        return 0
    diff = difflib.unified_diff(
        current.splitlines(), fresh.splitlines(), "checked in", "from the models", lineterm=""
    )
    print(f"✗ {out} no longer matches the Pydantic models:\n")
    for line in list(diff)[:80]:
        print(f"  {line}")
    print("\n  The models are the source. Run `emit`, do not edit the SQL.")
    return 1


def _load(args: argparse.Namespace) -> int:
    corpus = read_corpus(Path(args.corpus))
    print("openFerment seed")
    print("────────────────")
    for name, count in corpus.counts().items():
        print(f"  {name:<12} {count:>4} parsed")

    if args.sqlite:
        import sqlite3

        connection = sqlite3.connect(args.sqlite)
        connection.execute("PRAGMA foreign_keys = ON")
        if args.create:
            connection.executescript(emit(SQLITE))
        cursor = connection.cursor()
        written = load(cursor, corpus, SQLITE, append=args.append)
        connection.commit()
        connection.close()
    else:
        try:
            import psycopg  # type: ignore[import-not-found]
        except ModuleNotFoundError:
            print(
                "\n✗ psycopg is not installed. `pip install psycopg[binary]`, or use "
                "--sqlite for a local materialisation.",
                file=sys.stderr,
            )
            return 1
        with psycopg.connect(args.dsn) as connection:
            with connection.cursor() as cursor:
                if args.create:
                    cursor.execute(emit(POSTGRES))
                written = load(cursor, corpus, POSTGRES, append=args.append)
            connection.commit()

    print()
    for table, count in written.items():
        print(f"  {table:<12} {count:>4} rows written")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    emit_parser = sub.add_parser("emit", help="regenerate the DDL from the models")
    emit_parser.add_argument("--dialect", choices=sorted(DIALECTS), default="postgres")
    emit_parser.add_argument("--out")
    emit_parser.set_defaults(run=_emit)

    check_parser = sub.add_parser("check", help="fail if the checked-in DDL is stale")
    check_parser.add_argument("--dialect", choices=sorted(DIALECTS), default="postgres")
    check_parser.add_argument("--out")
    check_parser.set_defaults(run=_check)

    load_parser = sub.add_parser("load", help="load data/corpus/*.json")
    load_parser.add_argument("--corpus", default=str(CORPUS))
    load_parser.add_argument("--dsn", default="", help="Postgres connection string")
    load_parser.add_argument("--sqlite", default="", help="load into a SQLite file instead")
    load_parser.add_argument(
        "--create", action="store_true", help="create the schema before loading"
    )
    load_parser.add_argument(
        "--append",
        action="store_true",
        help="allow loading into a non-empty append-only records table",
    )
    load_parser.set_defaults(run=_load)

    args = parser.parse_args(argv)
    if args.command == "load" and not args.dsn and not args.sqlite:
        parser.error("load needs --dsn or --sqlite")
    result = args.run(args)
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
