"""`python -m openferment_core.db` — the database commands.

    migrate        bring the configured database to the newest schema (pnpm db:migrate)
    reset NAME     drop database NAME, make it again and migrate it (pnpm db:reset NAME);
                   refuses the production database, `openferment`
    revision       print the revision the configured database is at

The address is OPENFERMENT_DATABASE_URL, from the environment or core/.env.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

from . import migrate
from .engine import DatabaseUnavailable, database_url


def main(argv: list[str]) -> int:
    load_dotenv(Path(__file__).parent.parent.parent / ".env", override=False)
    command, rest = (argv[0], argv[1:]) if argv else ("", [])
    try:
        if command == "migrate" and not rest:
            url = database_url()
            migrate.upgrade(url)
            print(f"{url.render_as_string(hide_password=True)} is at revision {migrate.revision(url)}")
            return 0
        if command == "reset" and len(rest) == 1:
            url = migrate.reset(rest[0])
            print(f"{url.render_as_string(hide_password=True)} was made again at revision {migrate.revision(url)}")
            return 0
        if command == "revision" and not rest:
            print(migrate.revision() or "none: the database has not been migrated")
            return 0
    except (DatabaseUnavailable, migrate.ResetRefused) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
