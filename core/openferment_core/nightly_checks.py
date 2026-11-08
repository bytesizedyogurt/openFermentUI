"""What the nightly job checks after intake: every
fetched model file against its pinned hash, and the ten newest artifacts of
each project replayed against what was kept. A replay holds when it is
identical, or when every number lies within the precision its basis states
(a BioSTEAM run's last kept digit); the log says which. It reports and
rewrites nothing; the exit code is non-zero when a file does not match or a
replay lies outside its precision, so the night's log says so.

    python -m openferment_core.nightly_checks

Its registrars are every artifact tool the service registers, BioSTEAM's
library runs and every engine's among them, so replaying a BioSTEAM run
starts the Proforma worker, where BioSTEAM runs (a cold import of about
thirty seconds), and builds that run's plant afresh.

A nightly command acts in the project OPENFERMENT_PROJECT names, or in every
project the database holds (`each_project`); the checks queue's commands
share it.
"""
from __future__ import annotations

import os
import sys

REPLAY_NEWEST = 10


def each_project() -> list[str]:
    """The projects a nightly command acts in: the one OPENFERMENT_PROJECT
    names, or every project the database holds, oldest first."""
    from . import projects

    named = os.environ.get(projects.ENV, "").strip()
    return [named] if named else [p.id for p in projects.listed()]


def check_models() -> list[str]:
    from . import geneos_models as shelf

    problems = []
    for m in shelf.SHELF.values():
        if not m.fetched:
            continue
        why = shelf.available(m)
        if why:
            problems.append(why)
        else:
            print(f"model {m.id}: present, sha256 matches")
    return problems


def load_registrars() -> None:
    """Every module that registers an artifact tool. A tool registers when
    its module is imported; the service imports them all, and a command
    run on its own must too, or nothing it kept can be replayed."""
    from . import fermos, geneos, proforma, tools  # noqa: F401
    from .engine import library  # noqa: F401  (library.run)
    from .engine import registry

    registry.found()  # every engine's tool (docs/api/engines.md)


def replay_newest(n: int = REPLAY_NEWEST) -> list[str]:
    """Problems: a replay at the tool's current version that lies outside
    the precision its basis states. One identical, or within that precision,
    holds, and the log says which. An artifact an earlier version made is
    reported as stale, and is no problem: what it holds is what that version
    computed."""
    from . import artifacts

    load_registrars()
    newest = sorted(artifacts.all_artifacts(), key=lambda a: a.createdAt, reverse=True)[:n]
    problems = []
    for a in newest:
        try:
            now = artifacts.registered(a.tool).version_for(a.inputs)
        except Exception as e:
            problems.append(f"artifact {a.id} ({a.tool}) could not be replayed: {type(e).__name__}: {e}")
            continue
        if now != a.toolVersion:
            print(f"artifact {a.id} ({a.tool}): stale, made by {a.toolVersion}; the tool is now {now}")
            continue
        try:
            r = artifacts.replay(a.id)
        except Exception as e:  # a tool that cannot run here is a finding, in words
            problems.append(f"artifact {a.id} ({a.tool}) could not be replayed: {type(e).__name__}: {e}")
            continue
        if r.identical:
            print(f"artifact {a.id} ({a.tool}): replays identically")
        elif r.withinTolerance:
            held = f"rtol {r.tolerance.rtol:g}, atol {r.tolerance.atol:g}" if r.tolerance else "its stated precision"
            print(f"artifact {a.id} ({a.tool}): replays within its precision ({held}), "
                  f"{len(r.differences)} difference{'s' if len(r.differences) != 1 else ''} inside it")
        else:
            problems.append(f"artifact {a.id} ({a.tool}) replays differently: {len(r.differences)} differences, "
                            f"first at {r.differences[0].path if r.differences else '?'}")
    return problems


def main(argv: list[str]) -> int:
    from . import projects

    problems = check_models()
    for project_id in each_project():
        print(f"project {project_id}")
        with projects.using(project_id):
            problems += [f"{project_id}: {p}" for p in replay_newest()]
    for p in problems:
        print(f"✗ {p}")
    print(f"nightly checks: {len(problems)} problem{'s' if len(problems) != 1 else ''}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
