"""`python -m openferment_core.literature_live` — the literature lanes that
call a model, over one project (alpha 2.2 F.5; ADR-002, Implementation F).

    pnpm lit:graph --project <id> --by <name> [--limit N] [--rebuild] [--dry-run]
    pnpm lit:report                         the kit's demo corpus, offline (literature/report.py)
    pnpm lit:report --project <id> --by <name> [--judge] [--limit N] [--configs a,b] [--render]
    pnpm lit:report --project <id> --render --from <file>

`graph` builds the project's concept graph on the index route
(`literature/graph.py`). `--dry-run` reads the passages a build would send and
prints the batches, the prompts' characters, the kit's token estimate, and
what their input and the most a build could cost come to on the route's first
model (each batch's whole answer, the figure the day's cap holds against); it
calls no model.

`report --project` runs the project's lanes (`literature/report.py`): the
ground truth built from its kept candidates, retrieval in each configuration,
and with `--judge` the judge route's relevance grades and the answers graded
for grounding. The run whole, its questions, answers and rationales among it,
is written to `<data folder>/literature/<project>-<UTC time>.json`, the data
folder being OPENFERMENT_DATA_DIR or else core/data, outside git. `--render`
sets the run's public numbers beside the demo in
docs/reports/literature-retrieval.md and .json; with `--from` it renders a
kept run's file and spends nothing: the part it sets is rebuilt from the
kept run whole (`report.public`), so the committed report holds the numbers
`public` keeps and the part is filed under the run's own project. `--limit`
counts one at least.

The command reads core/.env as `python -m openferment_core.extract` does (a
setting the environment holds stands), installs llm.py's client for the kit
where it asks a model (a build, a run), and counts every call in a tally
(`llm.tally`): the first call no model
answers (no key, the account's usage limit, the day's cap) ends the build or
the run after its batch or question, in its words, with exit 1. Each build
and each run is audited under the person `--by` names (module `intake`,
actions `literature_graph` and `literature_report`).

It lives outside `literature/` because it imports llm.py, which `literature/`
does not (test_boundaries.py).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import audit, db, extract, llm, projects
from .literature import collectors, graph, kit, report

CORE = Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    """The service's data folder, as it stands once core/.env is read: a
    relative OPENFERMENT_DATA_DIR is taken from the repository's root, as
    intake.DATA_DIR takes it (read at import, before core/.env is)."""
    return collectors._env_path("OPENFERMENT_DATA_DIR", CORE / "data")


class Watch:
    """The stop the lanes read after each batch or question: the words of the
    first call in the command's tally that no model answered since the last
    read (`llm.Spent.outcome` `unavailable`: no key, the account's usage
    limit, the day's cap). A refusal stops nothing: the next batch or
    question may be answered."""

    def __init__(self, spent: list[Any]) -> None:
        self.spent, self.read = spent, 0

    def __call__(self) -> str | None:
        fresh, self.read = self.spent[self.read:], len(self.spent)
        for s in fresh:
            if s.outcome == "unavailable":
                return s.failure or "no model answered"
        return None


def _routes() -> dict[str, Any]:
    return {family: {"models": list(r.models), "effort": r.effort} for family, r in llm.routes().items()}


def _commit() -> str | None:
    try:
        done = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=CORE.parent, capture_output=True,
                              text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() or None


def _print(what: dict[str, Any]) -> None:
    print(json.dumps(what, ensure_ascii=False, default=str))


def graph_command(args: argparse.Namespace) -> int:
    with projects.using(args.project):
        if args.dry_run:
            rows = db.run(graph.pending(args.project, rebuild=args.rebuild, limit=args.limit))
            prompts = graph.prompts(rows)
            model = llm.chain("index")[0]
            chars = sum(len(p) for p in prompts)
            answer = max(graph.ANSWER_TOKENS, llm.KIT_ROOM[llm.routes()["index"].effort])
            _print({"project": args.project, "chunks": len(rows), "batches": len(prompts), "promptCharacters": chars,
                    "kitTokens": round(chars / 4), "model": model,
                    "inputUsd": round(llm.cost_usd(model, round(chars / 4), 0), 6),
                    "mostUsd": round(llm.cost_usd(model, chars // llm.CHARS_PER_TOKEN_ESTIMATE + len(prompts),
                                                  answer * len(prompts)), 6)})
            return 0
        with llm.tally() as spent:
            built = db.run(graph.build(args.project, llm=llm.kit_client("extraction"), limit=args.limit,
                                       rebuild=args.rebuild, stop=Watch(spent)))
        detail = {**dataclasses.asdict(built), "chunks_left": built.chunks_left,
                  **report.counted([report.as_spent(s) for s in spent])}
        audit.append(agent="person", who=args.by, module="intake", action="literature_graph",
                     state="stopped" if built.stopped else "done", detail=detail)
    _print(detail)
    if built.stopped:
        print(f"The build stopped: {built.stopped}", file=sys.stderr)
    return 1 if built.stopped else 0


def _keep(run: dict[str, Any]) -> Path:
    folder = _data_dir() / "literature"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{run['project']}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(run, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return path


def report_command(args: argparse.Namespace) -> int:
    if not args.project:
        return report.main([])
    if args.source:
        kept = json.loads(Path(args.source).read_text(encoding="utf-8"))
        held = kept.get("public") if isinstance(kept, dict) else None
        if (not isinstance(held, dict) or kept.get("kind") != "literature-lanes"
                or kept.get("project") != args.project):
            print(f"{args.source} holds no run of project {args.project} with its public numbers", file=sys.stderr)
            return 2
        try:
            part = report.public(kept, routes=held["routes"], commit=held.get("commit"))
        except (KeyError, TypeError) as e:
            print(f"{args.source} holds a run of project {args.project} that its numbers cannot be read from: "
                  f"{type(e).__name__}: {e}", file=sys.stderr)
            return 2
        report.write(part)
        _print({"rendered": str(report.OUT.with_suffix(".md")), "from": args.source})
        return 0
    configs = tuple(c.strip() for c in args.configs.split(",") if c.strip()) if args.configs else report.PROJECT_CONFIGS
    with projects.using(args.project), llm.tally() as spent:
        try:
            run = db.run(report.lanes(args.project, judge=args.judge, limit=args.limit, configs=configs,
                                      tally=llm.tally, stop=Watch(spent)))
        except report.Refused as e:
            print(e, file=sys.stderr)
            return 2
        run["by"] = args.by
        run["public"] = report.public(run, routes=_routes(), commit=_commit())
        path = _keep(run)
        cost = run["public"]["cost"]
        audit.append(agent="person", who=args.by, module="intake", action="literature_report",
                     state="stopped" if run["stopped"] else "done",
                     detail={"file": str(path), "questions": run["public"]["truth"]["questions"], "configs": list(configs),
                             "judge": args.judge, "usd": cost["total"], "stopped": run["stopped"]})
        if args.render:
            report.write(run["public"])
    _print({"file": str(path), "questions": run["public"]["truth"]["questions"], "stopped": run["stopped"],
            "cost": cost, "rendered": str(report.OUT.with_suffix(".md")) if args.render else None})
    if run["stopped"]:
        print(f"The run stopped: {run['stopped']}", file=sys.stderr)
    return 1 if run["stopped"] else 0


def _count(said: str) -> int:
    """A `--limit`: a whole number, one at least."""
    try:
        n = int(said)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{said!r} is no whole number") from None
    if n < 1:
        raise argparse.ArgumentTypeError(f"{n} counts nothing: a limit is one at least")
    return n


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m openferment_core.literature_live",
                                     description="The literature lanes that call a model, over one project.")
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("graph", help="build the project's concept graph on the index route")
    g.add_argument("--project", required=True)
    g.add_argument("--by", help="the person the build is audited under (required unless --dry-run)")
    g.add_argument("--limit", type=_count, default=None, help="the first N passages a build has yet to read")
    g.add_argument("--rebuild", action="store_true", help="read every passage of the project again")
    g.add_argument("--dry-run", action="store_true", help="measure what a build would send, and call nothing")
    r = sub.add_parser("report", help="the retrieval report: the kit's demo, or a project's lanes")
    r.add_argument("--project", default=None)
    r.add_argument("--by", help="the person the run is audited under (required with --project, unless --from)")
    r.add_argument("--judge", action="store_true", help="add the judge's relevance and the answers' grading")
    r.add_argument("--limit", type=_count, default=None, help="the first N questions, spread over the documents")
    r.add_argument("--configs", default=None, help=f"of {', '.join(report.PROJECT_CONFIGS)} (all by default)")
    r.add_argument("--render", action="store_true", help="set the run's public numbers in the committed report")
    r.add_argument("--from", dest="source", default=None, help="with --render: a kept run's file, rendered alone")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "report" and not args.project:
        if args.by or args.judge or args.render or args.source or args.limit is not None or args.configs:
            parser.error("--by, --judge, --limit, --configs, --render and --from need --project")
        return report_command(args)
    if args.command == "report" and args.source and not args.render:
        parser.error("--from renders a kept run: add --render")
    needs_by = not (args.command == "graph" and args.dry_run) and not (args.command == "report" and args.source)
    if needs_by and not (args.by or "").strip():
        parser.error("--by names the person this is audited under")
    extract.load_env()
    renders = args.command == "report" and bool(args.source)
    if not renders and projects.get(args.project) is None:
        print(f"The store holds no project {args.project!r}.", file=sys.stderr)
        return 2
    if not renders and not (args.command == "graph" and args.dry_run):
        kit.install_model(llm.kit_client)
    return graph_command(args) if args.command == "graph" else report_command(args)


if __name__ == "__main__":
    sys.exit(main())
