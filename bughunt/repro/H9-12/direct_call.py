"""H9-12: tools.run itself, in this process, on the same input: a raise here breaks its
docstring's "nothing here raises". No store is reached: numbers_in runs before any write.

    bh_py /home/user/openFermentUI/bughunt/repro/H9-12/direct_call.py PROJECT
"""
from __future__ import annotations

import json
import sys
import traceback

from openferment_core import tools

PROJECT = sys.argv[1]
ctx = tools.ToolContext(project=PROJECT, person="Edge Tester")
for label, value in (("1e309 value (control)", json.loads("1e309")), ("400-digit integer value", int("9" * 400))):
    raw = {"title": "t", "plant": "zz", "values": [{"key": "k", "quantity": {"value": value, "unit": "g/L"}}]}
    try:
        r = tools.run("study_scenario", raw, ctx)
        print(f"DIRECT {label} | returned a ToolResult | error={r.error!r}")
    except Exception as e:  # the contract says none comes here
        tb = traceback.extract_tb(e.__traceback__)
        where = " <- ".join(f"{f.filename.split('openferment_core/')[-1]}:{f.lineno} {f.name}" for f in reversed(tb))
        print(f"DIRECT {label} | raised {type(e).__name__}: {e} | at {where}")
