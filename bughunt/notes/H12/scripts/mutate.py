"""H12's mutation runner: apply one small mutation at a time to the H12 worktree, run the tests named for it,
restore the file, and record whether any test failed (the mutation is caught) or every test passed (a hollow
test: the mutation survives). Each mutation's patch is written under bughunt/notes/H12/mutations/<id>.patch.

    python3 mutate.py mutations.json [ids...]      # results appended to mutations/results.jsonl

Each entry: {"id", "target", "file" (relative to wt/core), "old", "new", "tests": [pytest args], "why"}.
The file is restored from a copy taken before the edit, whatever the run does.
"""
from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

WT = Path(os.environ.get("WT", "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H12/wt"))
NOTES = Path("/home/user/openFermentUI/bughunt/notes/H12")
RUN = NOTES / "scripts" / "wtpytest.sh"
OUT = NOTES / "mutations"
MARKERS = "not live and not sim and not slow and not lit"


def main(argv: list[str]) -> int:
    entries = json.loads(Path(argv[0]).read_text())
    only = set(argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    for m in entries:
        if only and m["id"] not in only:
            continue
        path = WT / "core" / m["file"]
        original = path.read_text()
        n = original.count(m["old"])
        if n != 1:
            print(f"{m['id']}: the old text occurs {n} times in {m['file']}; skipped", flush=True)
            continue
        mutated = original.replace(m["old"], m["new"])
        patch = "".join(difflib.unified_diff(original.splitlines(True), mutated.splitlines(True),
                                             f"a/core/{m['file']}", f"b/core/{m['file']}"))
        (OUT / f"{m['id']}.patch").write_text(patch)
        backup = path.with_suffix(path.suffix + ".h12bak")
        shutil.copy2(path, backup)
        started = time.time()
        try:
            path.write_text(mutated)
            args = [str(RUN), *m["tests"], "-x", "-m", m.get("markers", MARKERS)]
            done = subprocess.run(args, capture_output=True, text=True, timeout=m.get("timeout", 1500))
            tail = (done.stdout + done.stderr).strip().splitlines()[-1:] or [""]
            failed = [ln for ln in done.stdout.splitlines() if ln.startswith(("FAILED", "ERROR"))]
            caught = done.returncode != 0
            verdict = "caught" if caught else "SURVIVED"
        except subprocess.TimeoutExpired:
            tail, failed, verdict = ["timeout"], [], "timeout"
        finally:
            shutil.copy2(backup, path)
            backup.unlink()
        assert path.read_text() == original
        row = {"id": m["id"], "target": m["target"], "verdict": verdict, "seconds": round(time.time() - started),
               "summary": tail[0], "first_failure": failed[:2],
               "command": "bughunt/notes/H12/scripts/wtpytest.sh " + " ".join(m["tests"]) + f" -x -m '{m.get('markers', MARKERS)}'",
               "why": m.get("why", "")}
        with (OUT / "results.jsonl").open("a") as f:
            f.write(json.dumps(row) + "\n")
        print(json.dumps(row), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
