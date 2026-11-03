"""Conformance: an installed engine held to its contract (docs/api/engines.md,
Conformance; ADR-015).

    python -m openferment_core.engine.conform <name>     the eight checks, one row each

The checks run on a database of their own, made on the server that
OPENFERMENT_DATABASE_URL names (core/.env) and dropped after, in a project made
for them, so nothing a person keeps is touched. The verdict is kept in the
`engine_checks` table of the configured database, where `GET /api/engines`
and `pnpm ready` read it. Exits 1 when any check fails.

`checks(engine, ...)` runs the eight in whatever database and project are
current: a test's, or the proof's (scripts/prove.py).
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .. import db, projects
from ..db import models as t
from ..models import EngineCheck, EngineConformance, EngineRun
from . import EngineRefused
from .contract import version_string

CHECKS: dict[int, str] = {
    1: "a JSON number outside a quantity is refused in words before the worker is reached",
    2: "every parameter of every thing carries an origin: library-default with ref, or convention with note",
    3: "a run writes one runs row keyed by its basis, and the same request twice is that one row",
    4: "a replay holds every output within the precision the thing states",
    5: "the run's SFF file validates and scores, or sffRefused holds words",
    6: "importing the module the entry point names imports neither the worker module nor what the engine computes with",
    7: "a request the engine cannot run is refused with a receipt in words, with no traceback",
    8: "created_by on every run is the person or the model that asked for it",
}
CORE = Path(__file__).resolve().parent.parent.parent
NO_SUCH_THING = "conform-no-such-thing"


class ConformRefused(RuntimeError):
    """The checks could not be made at all, in words."""


def _words(e: BaseException) -> str:
    return str(e).strip().strip("'\"")


def _traceless(said: str) -> bool:
    return bool(said.strip()) and "Traceback" not in said and 'File "' not in said


# ── the eight checks ────────────────────────────────────────────────────


def _bare_number(engine: Any, thing: str, by: str) -> tuple[bool, str]:
    from fastapi.testclient import TestClient

    from .. import api, tools
    from ..engine import runs

    calls: list[str] = []
    saved = {m: getattr(engine, m) for m in ("run", "compute") if callable(getattr(engine, m, None))}
    own = {m for m in saved if m in getattr(engine, "__dict__", {})}

    def spy(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        def called(*a: Any, **k: Any) -> Any:
            calls.append(name)
            return fn(*a, **k)
        return called

    held = {r.id for r in runs.listed(engine.name)}
    client = TestClient(api.app, base_url="http://127.0.0.1")
    try:
        for m, fn in saved.items():
            setattr(engine, m, spy(m, fn))
        http = client.post(f"/api/engines/{engine.name}/run", headers={projects.HEADER: projects.current()},
                           json={"thing": thing, "inputs": [{"name": "a-parameter", "quantity": 1.5}], "by": by})
        tool = tools.run("engine_run", {"engine": engine.name, "plant": thing, "configuration": 7},
                         tools.ToolContext(model=by))
    finally:
        for m in saved:
            if m in own:
                setattr(engine, m, saved[m])
            else:
                delattr(engine, m)
        client.close()
    kept = {r.id for r in runs.listed(engine.name)} - held
    detail = http.json().get("detail") if http.headers.get("content-type", "").startswith("application/json") else None
    ok = http.status_code == 422 and bool(tool.error) and not calls and not kept
    return ok, (f"the route answered {http.status_code} and the tool {'refused' if tool.error else 'ran'}; the engine "
                f"was {'reached' if calls else 'never reached'}; {len(kept)} run kept"
                + ("" if ok else f" (route said {json.dumps(detail)[:160]}; tool said {tool.error!r})"))


def _origins(engine: Any, things: list[Any]) -> tuple[bool, str]:
    count, wrong = 0, []
    for th in things:
        for p in engine.parameters(th.id, th.defaultConfiguration):
            count += 1
            o = p.origin
            if not ((o.kind == "library-default" and (o.ref or "").strip())
                    or (o.kind == "convention" and (o.note or "").strip())):
                wrong.append(f"{th.id}:{p.key}")
    names = ", ".join(th.id for th in things)
    if wrong:
        return False, f"{len(wrong)} of {count} parameters lack an origin with what it names: {', '.join(wrong[:6])}"
    return True, f"{count} parameters of {len(things)} things ({names}), each in its default configuration"


def _row_count(run_id: str) -> int:
    from sqlalchemy import func, select

    async def counted() -> int:
        async with db.session() as s:
            q = select(func.count()).select_from(t.runs).where(t.runs.c.project_id == projects.current(),
                                                              t.runs.c.id == run_id)
            return int((await s.execute(q)).scalar_one())

    return db.run(counted())


def _created_by(run_id: str) -> str | None:
    from sqlalchemy import select

    async def read() -> str | None:
        async with db.session() as s:
            q = select(t.runs.c.created_by).where(t.runs.c.project_id == projects.current(), t.runs.c.id == run_id)
            return (await s.execute(q)).scalar_one_or_none()

    return db.run(read())


def checks(engine: Any, *, by: str, things: list[str] | None = None, entry: str | None = None) -> list[EngineCheck]:
    """The eight checks of docs/api/engines.md on `engine`, in the current
    database and project. `things` narrows checks 2 to those things (the
    first one runs checks 3, 4, 5, 7 and 8); `entry` is the entry point's
    `module:attr` for check 6."""
    from ..engine import runs

    out: list[EngineCheck] = []

    def add(n: int, ok: bool, said: str) -> None:
        out.append(EngineCheck(number=n, check=CHECKS[n], ok=ok, said=said))

    every = engine.things()
    chosen = [th for th in every if things is None or th.id in things]
    if not chosen:
        raise ConformRefused(f"the {engine.name} engine runs none of {things}; it runs "
                             f"{', '.join(th.id for th in every) or 'nothing'}")
    first = chosen[0]
    try:
        add(1, *_bare_number(engine, first.id, by))
    except Exception as e:  # a check that cannot be made fails in words
        add(1, False, f"the check could not be made: {type(e).__name__}: {_words(e)}")
    try:
        add(2, *_origins(engine, chosen))
    except Exception as e:
        add(2, False, f"the parameters could not be read: {type(e).__name__}: {_words(e)}")

    run: EngineRun | None = None
    try:
        a = runs.run_with(engine, first.id, first.defaultConfiguration, [], by=by).run
        b = runs.run_with(engine, first.id, first.defaultConfiguration, [], by=by).run
        rows = _row_count(a.id)
        ok = a.id == b.id and rows == 1 and a.status == "done" and a.engine == engine.name
        run = a if a.status == "done" else None
        add(3, ok, f"run {a.id} of {first.id}, asked twice, is {rows} row{'s' if rows != 1 else ''}; "
                   f"engine {a.engine}, status {a.status}" + (f"; the second answered {b.id}" if a.id != b.id else ""))
    except Exception as e:
        add(3, False, f"{first.id} could not be run: {type(e).__name__}: {_words(e)}")

    if run is None:
        add(4, False, "no run to replay (check 3)")
        add(5, False, "no run to read its SFF file from (check 3)")
    else:
        try:
            r = engine.replay(run)
            tol = f"rtol {r.tolerance.rtol:g}, atol {r.tolerance.atol:g}" if r.tolerance else "identical"
            add(4, bool(r.withinTolerance or r.identical),
                f"{'identical' if r.identical else 'within the precision' if r.withinTolerance else 'outside the precision'}"
                f" ({tol}); {len(r.differences)} difference{'s' if len(r.differences) != 1 else ''}")
        except Exception as e:
            add(4, False, f"the replay failed: {type(e).__name__}: {_words(e)}")
        if run.sff is not None:
            add(5, bool(run.sff.valid and run.sff.score is not None),
                f"record {run.sff.recordId}: {'valid' if run.sff.valid else 'not valid'}, score {run.sff.score}")
        else:
            said = (run.sffRefused or "").strip()
            add(5, _traceless(said), f"no file, in words: {said[:200]}" if said else "no file, and no words for why")

    module, attr = (entry or ":").split(":", 1)
    if module:
        try:
            add(6, *_imports_alone(module, engine))
        except Exception as e:
            add(6, False, f"the check could not be made: {type(e).__name__}: {_words(e)}")
    else:
        add(6, False, "no entry point was given to import")

    try:
        runs.run_with(engine, NO_SUCH_THING, None, [], by=by)
        add(7, False, f"a run of {NO_SUCH_THING!r} was kept where it should have been refused")
    except (EngineRefused, LookupError, ValueError) as e:
        said = _words(e)
        add(7, _traceless(said), f"refused: {said[:200]}")
    except Exception as e:
        add(7, False, f"refused with no words of the engine's: {type(e).__name__}: {_words(e)[:160]}")

    if run is None:
        add(8, False, "no run to read created_by from (check 3)")
    else:
        who = _created_by(run.id)
        add(8, who == by and run.by == by, f"created_by {who!r}, the run's by {run.by!r}, asked by {by!r}")
    return sorted(out, key=lambda c: c.number)


def _imports_alone(module: str, engine: Any) -> tuple[bool, str]:
    """Check 6, in a process of its own: what importing the entry point's
    module brings in, beside the worker module and the engine's heavy ones."""
    worker = engine.worker or ""
    heavy = list(engine.heavy)
    probe = ("import importlib, json, sys\n"
             f"importlib.import_module({module!r})\n"
             f"w, heavy = {worker!r}, {heavy!r}\n"
             "seen = sorted(m for m in sys.modules if (w and (m == w or m.startswith(w + '.'))) "
             "or m.split('.')[0] in heavy)\n"
             "print(json.dumps(seen))\n")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in (str(CORE), os.environ.get("PYTHONPATH", "")) if p)}
    done = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=120, cwd=str(CORE),
                          env=env)
    if done.returncode != 0:
        return False, f"importing {module} failed: {done.stderr.strip().splitlines()[-1] if done.stderr.strip() else done.returncode}"
    seen = json.loads(done.stdout.strip().splitlines()[-1])
    if seen:
        return False, f"importing {module} imported {', '.join(seen[:8])}"
    what = ", ".join([*(["the worker " + worker] if worker else []), *heavy]) or "nothing heavy, and no worker"
    return True, f"importing {module} imported none of {what}"


# ── the verdict, kept for GET /api/engines ──────────────────────────────


def verdict(engine: Any, found: list[EngineCheck], by: str) -> EngineConformance:
    return EngineConformance(engine=engine.name, version=version_string(engine), ok=all(c.ok for c in found),
                             checks=found, by=by, at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


def keep(v: EngineConformance) -> None:
    """The engine's verdict, replacing its last."""
    from sqlalchemy.dialects.postgresql import insert

    async def put() -> None:
        async with db.session() as s:
            stmt = insert(t.engine_checks).values(engine=v.engine, version=v.version, ok=v.ok,
                                                   body=v.model_dump(mode="json"), created_by=v.by)
            await s.execute(stmt.on_conflict_do_update(index_elements=[t.engine_checks.c.engine], set_={
                "version": stmt.excluded.version, "ok": stmt.excluded.ok, "body": stmt.excluded.body,
                "created_by": stmt.excluded.created_by, "created_at": stmt.excluded.created_at}))

    db.run(put())


def latest(name: str) -> EngineConformance | None:
    """The engine's last verdict, or None when it was never checked (or the store cannot be read)."""
    from sqlalchemy import select

    async def read() -> dict[str, Any] | None:
        async with db.session() as s:
            q = select(t.engine_checks.c.body).where(t.engine_checks.c.engine == name)
            return (await s.execute(q)).scalar_one_or_none()

    try:
        body = db.run(read())
    except Exception:  # no database, or one not migrated: no verdict to read
        return None
    return EngineConformance.model_validate(body) if body is not None else None


# ── the command line ────────────────────────────────────────────────────


def table(v: EngineConformance) -> str:
    lines = [f"{v.engine} ({v.version}): {'every check holds' if v.ok else 'a check fails'}", ""]
    for c in v.checks:
        lines.append(f"{'✓' if c.ok else '✗'} {c.number}  {c.check}")
        lines.append(f"     {c.said}")
    return "\n".join(lines)


def _inside(name: str, by: str) -> int:
    """In the scratch database: a project of its own, the checks, the verdict on stdout."""
    from . import registry
    from ..models import ProjectCreate

    engine = registry.get(name)
    entry = registry.found()[name].entry
    made = projects.create(ProjectCreate(name=f"Conformance of {name}", by=by))
    with projects.using(made.id):
        found = checks(engine, by=by, entry=entry)
    print(json.dumps(verdict(engine, found, by).model_dump(mode="json")))
    return 0


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    from ..db import migrate
    from ..db.engine import database_url
    from . import registry

    if argv[:1] == ["--inside"] and len(argv) == 3:
        return _inside(argv[1], argv[2])
    if len(argv) != 1 or argv[0].startswith("-"):
        print("usage: python -m openferment_core.engine.conform <engine name>")
        return 2
    name = argv[0]
    load_dotenv(CORE / ".env", override=False)
    try:
        engine = registry.get(name)
    except (registry.EngineNotFound, registry.EngineUnavailable) as e:
        print(f"✗ {_words(e)}")
        return 1
    by = f"conformance check of {name}"
    server = database_url()
    scratch = f"openferment_conform_{name.replace('-', '_')}_{secrets.token_hex(4)}"
    url = migrate.create(scratch, server)
    try:
        migrate.upgrade(url)
        env = {**os.environ, "OPENFERMENT_DATABASE_URL": url.render_as_string(hide_password=False)}
        done = subprocess.run([sys.executable, "-m", "openferment_core.engine.conform", "--inside", name, by],
                              capture_output=True, text=True, cwd=str(CORE), env=env, timeout=1800)
    finally:
        migrate.drop(scratch, server)
    lines = [ln for ln in done.stdout.strip().splitlines() if ln.startswith("{")]
    if done.returncode != 0 or not lines:
        tail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no words"]
        print(f"✗ the checks could not be made on {name}: {tail[0]}")
        return 1
    v = EngineConformance.model_validate(json.loads(lines[-1]))
    try:
        keep(v)
    except Exception as e:  # the verdict stands printed; the store says why it could not keep it
        print(f"! the verdict could not be kept for GET /api/engines: {type(e).__name__}: {_words(e)}")
    print(table(v))
    return 0 if v.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
