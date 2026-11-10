#!/usr/bin/env bash
# migrate_checks.sh: the head's migrations from an empty database to head, run a second time, compared with
# the table models (alembic's autogenerate comparison), taken down to alpha 2.1's head (0007) and up again.
# Every database is bh_h6_*; each is dropped at the end. Logs to stdout.
source /home/user/openFermentUI/bughunt/lib/env.sh
W=$BH_WORK/H6
DB=bh_h6_empty
URL=$BH_SERVER/$DB
mig() { (cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$URL" .venv/bin/python -m openferment_core.migrations "$@"); }
schema() { pg_dump -s -x -O -d "$URL" | grep -v '^--' | grep -v '^$' | grep -v 'SET \|set_config\|SELECT pg_catalog'; }
psql "$BH_SERVER/postgres" -qXc "DROP DATABASE IF EXISTS $DB WITH (FORCE)"; psql "$BH_SERVER/postgres" -qXc "CREATE DATABASE $DB"
echo "== first migrate (empty -> head)"; mig migrate; echo "exit $?"
schema > "$W/schema-1.sql"
echo "== second migrate"; mig migrate; echo "exit $?"
schema > "$W/schema-2.sql"
echo "== schema diff between the two runs (empty = nothing changed):"; diff "$W/schema-1.sql" "$W/schema-2.sql" && echo "(none)"
psql "$URL" -XAtc "select 'openferment', version_num from openferment.alembic_version union all select 'sci_rag', version_num from sci_rag.alembic_version"
echo "== the migrated schema against the table models (alembic compare_metadata):"
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$URL" .venv/bin/python - <<'EOF'
import asyncio, os
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from sqlalchemy import pool
from openferment_core.db.engine import make_engine, SCHEMA
from openferment_core.db.models import metadata

async def main():
    e = make_engine(os.environ["OPENFERMENT_DATABASE_URL"], poolclass=pool.NullPool)
    async with e.connect() as c:
        def cmp(sync):
            ctx = MigrationContext.configure(sync, opts={"include_schemas": True, "compare_type": True,
                "include_name": lambda name, type_, parent: type_ != "schema" or name == SCHEMA,
                "version_table_schema": SCHEMA})
            return compare_metadata(ctx, metadata)
        diffs = await c.run_sync(cmp)
    await e.dispose()
    print(f"{len(diffs)} differences")
    for d in diffs:
        print("  ", d)
asyncio.run(main())
EOF
)
echo "== downgrade to 0007 (alpha 2.1's head) and up again"
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$URL" .venv/bin/python - <<'EOF'
import os
from alembic import command
from openferment_core.db import migrate
cfg = migrate.config(os.environ["OPENFERMENT_DATABASE_URL"])
command.downgrade(cfg, "0007")
print("downgraded to", migrate.revision(os.environ["OPENFERMENT_DATABASE_URL"]))
EOF
)
psql "$URL" -XAtc "select to_regclass('openferment.protocols'), to_regclass('openferment.engine_checks'), (select count(*) from information_schema.columns where table_schema='openferment' and table_name='runs' and column_name='engine')"
mig migrate; echo "exit $?"
schema > "$W/schema-3.sql"
echo "== schema diff after down and up again (empty = the same):"; diff "$W/schema-1.sql" "$W/schema-3.sql" && echo "(none)"
echo "== downgrade below 0007 (base) and up again"
(cd "$BH_ROOT/core" && bh_env OPENFERMENT_DATABASE_URL="$URL" .venv/bin/python - <<'EOF'
import os
from alembic import command
from openferment_core.db import migrate
cfg = migrate.config(os.environ["OPENFERMENT_DATABASE_URL"])
try:
    command.downgrade(cfg, "base")
    print("downgraded to", migrate.revision(os.environ["OPENFERMENT_DATABASE_URL"]))
except Exception as e:
    print("downgrade to base refused:", type(e).__name__, str(e).splitlines()[0][:300])
EOF
)
mig migrate; echo "exit $?"
schema > "$W/schema-4.sql"
echo "== schema diff after base and up again:"; diff "$W/schema-1.sql" "$W/schema-4.sql" && echo "(none)"
mig revision
bh_db_drop $DB
