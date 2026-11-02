"""`pnpm eval`: Postdoc's evaluation set, asked through the service's answer path
(postdoc/evaluate.py; execution prompt §10 stage 6.4).

    python -m openferment_core.evaluation seed           the default questions into the project
    python -m openferment_core.evaluation run [--live]   ask, score and keep; the report as JSON

It acts in the project OPENFERMENT_PROJECT names, on the database
OPENFERMENT_DATABASE_URL names, each read from the environment or else from
core/.env. Offline (the default) the evaluation's stand-in answers and no key is
read; `--live` asks the routing table's models.
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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("seed", "run"):
        print("usage: python -m openferment_core.evaluation seed | run [--live]", file=sys.stderr)
        return 2
    if args[0] == "seed":
        print(json.dumps({"seeded": evaluate.seed()}))
        return 0
    from .api import _answer

    found, standins = evaluate.run(_answer, live="--live" in args)
    out = evaluate.report(found)
    # Offline: whether each follow-up's stand-in was handed the question it follows, read from the service.
    held = {q.id: q for q in evaluate.questions()}
    out["followUps"] = {qid: bool(s.seen) and held[held[qid].follows].question in json.dumps(s.seen[0])
                        for qid, s in standins.items() if held[qid].follows in held}
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    _settings()
    sys.exit(main())
