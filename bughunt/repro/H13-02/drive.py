"""H13-02's driver: the report's own code, imported from a scratch worktree at 2047f5a.

Run with PYTHONPATH=<worktree>/core so the worktree's openferment_core is the one imported (the venv's
editable install points at the main checkout, which this never writes).

    python drive.py check  <wt>               the module paths; exit 3 unless both are the worktree's
    python drive.py render <wt> <out-stem>    report.write() of each project part the committed JSON holds,
                                              into <out-stem>.md and .json (copies of the committed pair):
                                              the step `lit:report --project <id> --render` ends with
    python drive.py demo   <wt> <db-url>      `pnpm lit:report` whole (literature_live.main(["report"])), one
                                              change made in memory: the scratch database it makes and drops is
                                              the one run.sh made with bh_db_fresh (run.sh drops it)
"""
import sys
import types
from pathlib import Path


def _imported(wt: Path):
    import openferment_core
    from openferment_core.literature import report

    pkg = Path(openferment_core.__file__).resolve()
    out = report.OUT.resolve()
    ok = str(pkg).startswith(str(wt.resolve()) + "/") and str(out).startswith(str(wt.resolve()) + "/")
    return report, pkg, out, ok


def main(argv: list[str]) -> int:
    mode, wt = argv[0], Path(argv[1])
    report, pkg, out, ok = _imported(wt)
    if mode == "check":
        print(f"openferment_core: {pkg}")
        print(f"report.OUT: {out}")
        return 0 if ok else 3
    if not ok:
        print(f"refusing: openferment_core at {pkg}, report.OUT at {out}, outside {wt}", file=sys.stderr)
        return 3
    if mode == "render":
        stem = Path(argv[2])
        _, parts = report.read(stem)
        for k in sorted(parts):
            report.write(parts[k], out=stem)
        print(f"rendered parts: {', '.join(sorted(parts))}")
        return 0
    if mode == "demo":
        from sqlalchemy.engine import make_url

        from openferment_core import literature_live
        from openferment_core.db import as_async

        url = as_async(make_url(argv[2]))
        real = report.migrate
        report.migrate = types.SimpleNamespace(
            **{k: getattr(real, k) for k in dir(real) if not k.startswith("__")},
        )
        report.migrate.create = lambda name, server=None: url
        report.migrate.drop = lambda name, server=None: None
        return literature_live.main(["report"])
    print(f"unknown mode {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
