"""fill_prove.py ORIGIN DATA_DIR DB: fill an alpha 2.1 service through its own API with alpha 2.1's own proof steps.

Run with the alpha 2.1 worktree's Python from its core/ (wt-main/core/.venv/bin/python), keyless. It imports
wt-main/scripts/prove.py and runs its steps 2 to 7 against the service at ORIGIN (started by main_svc.sh over DB):
a project; the kit's demo corpus through Intake's upload; a stand-in's candidate extracted and accepted (a
decision); the cornstover library run; the cellulosic_ethanol_v0 run, sugarcane, a replay, a scenario with a
person's assumption and a model's estimate, its run, a comparison, a runbook locked, the export; Postdoc's
evaluation offline (a conversation, two turns, tool calls, eval rows); a reference SFF file imported. Steps 1
(database reset), 8 (restart) and 9 (walk) are left: the database is made by hand and the head reads it later.
It never reads core/.env and calls no model. Writes what the steps made to DATA_DIR/made.json.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

origin, data_dir, db = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
WT = Path(os.environ["BH_WT_MAIN"])
sys.path.insert(0, str(WT / "scripts"))
os.environ["OPENFERMENT_TEST_DATABASE_URL"] = "postgresql://openferment:openferment@127.0.0.1:5432/postgres"
os.environ.pop("OPENFERMENT_API_KEY", None)
os.environ["ANTHROPIC_API_KEY"] = ""
import prove  # noqa: E402  (alpha 2.1's own proof)

proof = prove.Proof(origin=origin, database=db, data_dir=data_dir, log=data_dir / "fill.log", live=False)
steps = [int(s) for s in (sys.argv[4] if len(sys.argv) > 4 else "2,3,4,5,6,7").split(",")]
for n in steps:
    print(f"step {n}: {prove.TITLES[n]}", flush=True)
    try:
        prove.RUNNERS[n](proof)
    except prove.Stop as e:
        proof.check(False, str(e))
print(json.dumps({"passed": proof.passed, "failed": proof.failed}))
(data_dir / "made.json").write_text(json.dumps({"project": proof.project, **{k: v for k, v in proof.made.items()}},
                                               default=list, indent=1))
