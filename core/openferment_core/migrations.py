"""`python -m openferment_core.migrations` — both schemas' migrations, and the
database commands (execution prompt §8.1, §8.2).

    migrate        bring the configured database to the newest schemas (pnpm db:migrate)
    reset NAME     drop database NAME, make it again and migrate it (pnpm db:reset NAME);
                   refuses the production database, `openferment`
    drop NAME      drop database NAME; refuses the production database
    revision       print the revisions the configured database is at

One database holds two histories: ours in schema `openferment`
(db/alembic/), Sci RAG Kit's in schema `sci_rag`
(literature/kit_alembic/). `db` imports nothing of the service (§7.2), so
the two are run together here, ours first. The address is
OPENFERMENT_DATABASE_URL, from the environment or core/.env.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from sqlalchemy.engine import URL
from sqlalchemy.exc import ProgrammingError

from .db import migrate
from .db.engine import DatabaseUnavailable, as_async, database_url


def _kit_config(url: URL | str) -> Config:
    from .literature import kit

    cfg = Config()
    cfg.set_main_option("script_location", str(kit.MIGRATIONS))
    cfg.attributes["url"] = as_async(url)
    return cfg


def upgrade(url: URL | str | None = None) -> None:
    """Migrate both schemas of the database at `url` (the configured one by
    default)."""
    target = as_async(url or database_url())
    migrate.upgrade(target)
    command.upgrade(_kit_config(target), "head")


def kit_head() -> str:
    found = ScriptDirectory.from_config(_kit_config(URL.create("postgresql"))).get_current_head()
    if found is None:
        raise RuntimeError("the kit's alembic history holds no revision")
    return found


def kit_revision(url: URL | str | None = None) -> str | None:
    """The kit's revision in the database, or None before its first migration."""
    from .literature import kit

    target = as_async(url or database_url())
    try:
        return asyncio.run(migrate._scalar(target, f'SELECT version_num FROM "{kit.SCHEMA}".alembic_version')) or None  # type: ignore[return-value]
    except ProgrammingError:
        return None


def at_head(url: URL | str | None = None) -> dict[str, tuple[str | None, str]]:
    """Each schema's revision in the database and its newest: {schema: (at, head)}."""
    from .literature import kit

    target = as_async(url or database_url())
    return {
        migrate.SCHEMA: (migrate.revision(target), migrate.head()),
        kit.SCHEMA: (kit_revision(target), kit_head()),
    }


def reset(name: str, url: URL | str | None = None) -> URL:
    """Drop `name`, make it again and migrate both schemas; its address."""
    migrate.drop(name, url)
    target = migrate.create(name, url)
    upgrade(target)
    return target


def _revisions(url: URL) -> str:
    return ", ".join(f"{schema} at {at or 'none'}" for schema, (at, _) in at_head(url).items())


def main(argv: list[str]) -> int:
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
    command_, rest = (argv[0], argv[1:]) if argv else ("", [])
    try:
        if command_ == "migrate" and not rest:
            url = database_url()
            upgrade(url)
            print(f"{url.render_as_string(hide_password=True)}: {_revisions(url)}")
            return 0
        if command_ == "reset" and len(rest) == 1:
            url = reset(rest[0])
            print(f"{url.render_as_string(hide_password=True)} was made again: {_revisions(url)}")
            return 0
        if command_ == "drop" and len(rest) == 1:
            migrate.drop(rest[0])
            print(f"{rest[0]} dropped")
            return 0
        if command_ == "revision" and not rest:
            print(_revisions(database_url()))
            return 0
    except (DatabaseUnavailable, migrate.ResetRefused) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
