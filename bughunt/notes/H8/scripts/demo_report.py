"""`pnpm lit:report`'s demo run (literature/report.py `_run`) on a bh_ test database, written nowhere.

Usage (from core/): .venv/bin/python -I demo_report.py postgresql://.../bh_h8_demo OUT.md
`report.main` makes a database named lit_report_* and writes docs/reports/; this harness runs
the same `_run` on a database made and migrated by bh_db_fresh and prints the Markdown to OUT.md,
for comparison with the committed docs/reports/literature-retrieval.md.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")
from openferment_core import db  # noqa: E402
from openferment_core.literature import kit, report  # noqa: E402

url, out = sys.argv[1], sys.argv[2]
assert "/bh_" in url
db.use_engine(db.make_engine(url, pool_size=2, max_overflow=2))
kit.use_database(url)
try:
    markdown, payload = report._run()
finally:
    kit.use_database(None)
    engine = db.use_engine(None)
    if engine is not None:
        db.run(engine.dispose())
open(out, "w").write(markdown)
print(markdown[:3000])
