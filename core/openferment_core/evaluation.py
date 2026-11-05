"""`pnpm eval`: Postdoc's evaluation set, asked through the service's answer path
(postdoc/evaluate.py; execution prompt §10 stage 6.4; alpha 2.1 stage C).

    python -m openferment_core.evaluation seed [--suite S]             a suite's questions into the project
    python -m openferment_core.evaluation run [--live] [--suite S] [--tag T] [--judge] [--only Q,Q]
                                                                       ask, score and keep; the report as JSON
    python -m openferment_core.evaluation judge [--suite S] [--tag T] [--only Q,Q]
                                                                       judge the newest kept runs again
    python -m openferment_core.evaluation summary [--suite S] [--rows] each tag's runs side by side

A suite is `default` (the proof's two questions) or `ethanol` (the owner's
twelve and the base's two, fourteen in all). A tag names the route table a run
was asked on, so runs on different models sit side by side; `--judge` has the
`judge` route read each answer as it is kept, and `judge` has the judge route
as it now stands read the kept ones again (a second judge). `--only` names
question ids, comma-separated: `run` asks those alone under its tag, a
follow-up among them in the conversation of the newest run there of the
question it follows, and `judge` reads their newest runs alone. `--rows` adds
one row for each tag's newest run of each question to the summary.

It acts in the project OPENFERMENT_PROJECT names, on the database
OPENFERMENT_DATABASE_URL names, each read from the environment or else from
core/.env. `run` and `judge` read the rest of core/.env as the service does,
through the service module's own loader (api.py), a setting the environment
holds standing over the file's: the key, the routes and the budgets a model
call reads. Offline (the default) the evaluation's stand-in answers and no
model is called; `--live` asks the routing table's models.

A run or a judge pass that finds no model on the judge route answering (no
key, the account's usage limit, the day's cap) stops there with exit 1: its
JSON names what it kept or judged before, `stopped` says where and why with
the commands that go on, and the run it was judging gains no judgement. A
command asked of questions the suite cannot ask as named exits 2 in words,
having asked nothing.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import db, projects
from .postdoc import evaluate


def _settings() -> None:
    """The database address and the project, from core/.env when the
    environment does not set them: these two names alone."""
    from dotenv import dotenv_values

    held = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
    for name in (db.URL_SETTING, projects.ENV):
        if held.get(name) and not os.environ.get(name):
            os.environ[name] = str(held[name])


USAGE = ("usage: python -m openferment_core.evaluation seed [--suite S] | run [--live] [--suite S] [--tag T] "
         "[--judge] [--only Q,Q] | judge [--suite S] [--tag T] [--only Q,Q] | summary [--suite S] [--rows]")


def _option(args: list[str], name: str, default: str | None) -> str | None:
    """The value after `name` in the arguments, or the default."""
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def _only(args: list[str]) -> list[str] | None:
    """The question ids `--only` names, comma-separated; None when it is not given."""
    if "--only" not in args:
        return None
    return [x.strip() for x in (_option(args, "--only", "") or "").split(",") if x.strip()]


def _judge_with():
    """The judge, reading cited records and documents from the project's
    pool as it stands (the postdoc package does not import the pool)."""
    from . import evidence_pool

    pool = evidence_pool.load()
    return lambda q, plan: evaluate.judge(q, plan, record=pool.record, paper=pool.paper)


def _judged(done: list[evaluate.EvalRun]) -> list[dict]:
    return [{"questionId": r.questionId, "tag": r.tag, "judgement": r.judged[-1].model_dump(mode="json")}
            for r in done]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("seed", "run", "judge", "summary"):
        print(USAGE, file=sys.stderr)
        return 2
    suite = _option(args, "--suite", evaluate.DEFAULT) or evaluate.DEFAULT
    if suite not in evaluate.SUITES:
        print(f"there is no suite {suite!r}: the suites are {', '.join(evaluate.SUITES)}", file=sys.stderr)
        return 2
    if args[0] == "seed":
        print(json.dumps({"seeded": evaluate.seed(suite=suite)}))
        return 0
    if args[0] == "summary":
        out = evaluate.summary(suite)
        if "--rows" in args:
            out["rows"] = evaluate.rows(suite)
        print(json.dumps(out, ensure_ascii=False))
        return 0
    only = _only(args)
    if args[0] == "judge":
        # core/.env read as the run branch below reads it: the service module's
        # import loads the file (api.py), a setting the environment holds standing.
        from . import api  # noqa: F401

        try:
            done = evaluate.judge_kept(suite, _option(args, "--tag", None), judge_with=_judge_with(), only=only)
        except evaluate.Refused as e:
            print(e, file=sys.stderr)
            return 2
        except evaluate.JudgeUnavailable as e:
            print(json.dumps({"judged": _judged(e.done), "stopped": str(e)}, ensure_ascii=False))
            print(e, file=sys.stderr)
            return 1
        print(json.dumps({"judged": _judged(done), "stopped": None}, ensure_ascii=False))
        return 0
    from .api import _answer

    live = "--live" in args
    if "--judge" in args and not live:
        print("--judge needs --live: an answer is judged by a model on the judge route", file=sys.stderr)
        return 2
    try:
        found, standins = evaluate.run(_answer, live=live, suite=suite, tag=_option(args, "--tag", "") or "",
                                       judged="--judge" in args,
                                       judge_with=_judge_with() if "--judge" in args else None, only=only)
    except evaluate.Refused as e:
        print(e, file=sys.stderr)
        return 2
    except evaluate.JudgeUnavailable as e:
        print(json.dumps({**evaluate.report(e.done), "stopped": str(e)}, ensure_ascii=False))
        print(e, file=sys.stderr)
        return 1
    out = evaluate.report(found)
    # Offline: whether each follow-up's stand-in was handed the question it follows, read from the service.
    held = {q.id: q for q in evaluate.questions()}
    out["followUps"] = {qid: bool(s.seen) and held[held[qid].follows].question in json.dumps(s.seen[0])
                        for qid, s in standins.items() if held[qid].follows in held}
    out["stopped"] = None
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    _settings()
    sys.exit(main())
