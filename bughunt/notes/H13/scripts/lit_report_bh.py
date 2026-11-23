"""H13: `pnpm lit:report` (python -m openferment_core.literature_live report) with one change made at
run time, in memory: the demo's own database is named `bh_h13_lit_report_...` (the hunt's naming rule)
where the command names it `lit_report_...`. Every other line runs as it is; it writes
docs/reports/literature-retrieval.md and .json in the checkout it runs from (H13's worktree).

Usage (from a checkout's core/, its venv's python): python lit_report_bh.py
"""
import sys
import types

from openferment_core import literature_live
from openferment_core.literature import report

_real = report.migrate
report.migrate = types.SimpleNamespace(
    **{k: getattr(_real, k) for k in dir(_real) if not k.startswith("__")},
)
report.migrate.create = lambda name, server=None: _real.create("bh_h13_" + name, server)
report.migrate.drop = lambda name, server=None: _real.drop("bh_h13_" + name, server)
sys.exit(literature_live.main(["report", *sys.argv[1:]]))
