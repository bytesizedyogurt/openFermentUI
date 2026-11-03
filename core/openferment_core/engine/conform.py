"""Conformance: an installed engine held to its contract (docs/api/engines.md,
Conformance; ADR-015).

    python -m openferment_core.engine.conform <name>     the eight checks, one row each
        [--thing <id>]...      narrow the checks to these things, in the order named
                               (the first named is run); an id the engine runs none of
                               is refused in words
        [--inputs <file>]      a JSON list of EngineInputs the run is made with, for an
                               engine whose thing waits for values no default gives
                               (the kinetics engine's families: fermos_engine's
                               write_placeholder_inputs writes such a file)
        [--project <id>]       make the checks in this existing project of the
                               configured database, for an engine whose things are a
                               project's own (the train engine's trains)

The checks run on a database of their own, made on the server that
OPENFERMENT_DATABASE_URL names (core/.env) and dropped after, in a project made
for them, so nothing a person keeps is touched. An engine whose things are all
a project's own (it declares `things_are`, saying what they are: the train
engine's are a project's trains) lists nothing in a fresh project, so it is
checked with `--project <id>`, in that project of the configured database
itself (`in_project`). There the checks run one thing: the first `--thing`
names, else the first the project holds that runs, each thing passed over
before it said with its words (a thing whose parameters cannot be read, a
value that waits; nothing is kept for either). They run it on a basis of
their own: with no `--inputs`, check 3's run sets one parameter at its own
default as the checks' assumption, dated the day they run (`_own_basis`), so
the checks' rows and the rows of the runs the project's people ask for keep
apart; the rows the checks make stay in the project, each in the name of the
checks or of check 8's model. The production
database (`openferment`) is refused, as `pnpm db:reset` refuses it, and so is
a project the database lacks. Without `--project` such an engine is refused
in words saying what its things are. The verdict is kept in the
`engine_checks` table of the configured database, where `GET /api/engines` and
`pnpm ready` read it. Exits 1 when any check fails.

`checks(engine, ...)` runs the eight in whatever database and project are
current: a test's, or the proof's (scripts/prove.py).
"""
from __future__ import annotations

import contextlib
import json
import os
import secrets
import subprocess
import sys
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .. import db, projects
from ..db import models as t
from ..models import EngineCheck, EngineConformance, EngineInput, EnginePrecision, EngineRun, EngineThing, Origin, Quantity
from . import EngineRefused
from .contract import version_string

CHECKS: dict[int, str] = {
    1: "a JSON number outside a quantity is refused in words before the worker is reached",
    2: "every default carries an origin naming what it rests on (a library-default, a record or an artifact its ref, "
       "a convention its note, a person's assumption its by), and a parameter with none takes a run's value",
    3: "a run writes one runs row keyed by its basis, and the same request twice is that one row",
    4: "a replay holds every output within the precision the thing states",
    5: "the run's SFF file validates and scores, or sffRefused holds words",
    6: "importing the module the entry point names imports neither the worker module nor what the engine computes with",
    7: "a request the engine refuses is kept as a receipt in its words, with no traceback",
    8: "created_by on every run is the person or the model that asked for it",
}
CORE = Path(__file__).resolve().parent.parent.parent
NO_SUCH_THING = "conform-no-such-thing"
# Who the model path of check 8 is asked by.
MODEL = "conformance-model"


class ConformRefused(RuntimeError):
    """The checks could not be made at all, in words."""


def _words(e: BaseException) -> str:
    return str(e).strip().strip("'\"")


def _traceless(said: str) -> bool:
    return bool(said.strip()) and "Traceback" not in said and 'File "' not in said


def _configuration_of(thing: Any) -> str | None:
    """The configuration a check runs a thing in: its default, or the first
    it names, since a thing with configurations and no default is run with
    one named."""
    return thing.defaultConfiguration or (thing.configurations[0] if thing.configurations else None)


@contextlib.contextmanager
def _spied(engine: Any, wrappers: dict[str, Callable[[Callable[..., Any]], Callable[..., Any]]]) -> Iterator[None]:
    """Each named method of the engine stood in by its wrapper for the block,
    and put back after as it was: an attribute of the object's own restored,
    one its class gives deleted."""
    saved = {m: getattr(engine, m) for m in wrappers if callable(getattr(engine, m, None))}
    own = {m for m in saved if m in getattr(engine, "__dict__", {})}
    try:
        for m, fn in saved.items():
            setattr(engine, m, wrappers[m](fn))
        yield
    finally:
        for m in saved:
            if m in own:
                setattr(engine, m, saved[m])
            else:
                delattr(engine, m)


# ── the eight checks ────────────────────────────────────────────────────


def _bare_number(engine: Any, thing: str, by: str) -> tuple[bool, str]:
    from fastapi.testclient import TestClient

    from .. import api, tools
    from ..engine import runs

    calls: list[str] = []

    def spy(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
            def called(*a: Any, **k: Any) -> Any:
                calls.append(name)
                return fn(*a, **k)
            return called
        return wrap

    held = {r.id for r in runs.listed(engine.name)}
    client = TestClient(api.app, base_url="http://127.0.0.1")
    try:
        with _spied(engine, {"run": spy("run"), "compute": spy("compute")}):
            headers = {projects.HEADER: projects.current()}
            # A number in place of a quantity, then a stray number beside the
            # request's own fields: both refused at the route.
            http = [client.post(f"/api/engines/{engine.name}/run", headers=headers, json=body) for body in (
                {"thing": thing, "inputs": [{"name": "a-parameter", "quantity": 1.5}], "by": by},
                {"thing": thing, "inputs": [], "by": by, "n": 3})]
            tool = tools.run("engine_run", {"engine": engine.name, "plant": thing, "configuration": 7},
                             tools.ToolContext(model=by))
    finally:
        client.close()
    kept = {r.id for r in runs.listed(engine.name)} - held
    codes = [h.status_code for h in http]
    detail = [h.json().get("detail") if h.headers.get("content-type", "").startswith("application/json") else None
              for h in http]
    ok = codes == [422, 422] and bool(tool.error) and not calls and not kept
    return ok, (f"the route answered {' and '.join(map(str, codes))} (a number for a quantity, a stray number) and the "
                f"tool {'refused' if tool.error else 'ran'}; the engine was {'reached' if calls else 'never reached'}; "
                f"{len(kept)} run kept"
                + ("" if ok else f" (route said {json.dumps(detail)[:200]}; tool said {tool.error!r})"))


def _names_its_ground(o: Any) -> bool:
    """Whether a default's origin names what it rests on: a library-default
    its package and version, a record the records, an artifact the artifact
    (each `ref`); a convention what it is (`note`); a person's assumption the
    person who typed it (`by`)."""
    if o is None:
        return False
    if o.kind in ("library-default", "record", "artifact"):
        return bool((o.ref or "").strip())
    if o.kind == "convention":
        return bool((o.note or "").strip())
    return o.kind == "person-assumption" and bool((o.by or "").strip())


def _origins(engine: Any, things: list[Any]) -> tuple[bool, str]:
    """Check 2. Every default carries an origin naming what it rests on
    (`_names_its_ground`): a library-default its package and version, a
    convention what it is, and for a thing the project holds, the records,
    the artifact or the person its default was read from. A parameter with no
    default (value and origin null) takes a run's value: `assumption` stands
    in its source rule. A run sets it, the engine binds it, or the thing
    fills it itself when a run leaves it unset (its `note` says so)."""
    count, unset, wrong = 0, 0, []
    for th in things:
        for p in engine.parameters(th.id, _configuration_of(th)):
            count += 1
            o = p.origin
            if p.value is None and o is None:
                if "assumption" in p.sourceRule:
                    unset += 1
                else:
                    wrong.append(f"{th.id}:{p.key}")
                continue
            if not _names_its_ground(o):
                wrong.append(f"{th.id}:{p.key}")
    names = ", ".join(th.id for th in things)
    if wrong:
        return False, (f"{len(wrong)} of {count} parameters lack an origin with what it names, or a run's value where "
                       f"they have no default: {', '.join(wrong[:6])}")
    return True, (f"{count} parameters of {len(things)} thing{'s' if len(things) != 1 else ''} ({names}), each in its "
                  f"default configuration or its first: {count - unset} default{'s' if count - unset != 1 else ''}, "
                  f"each with its origin, and {unset} with none, {'each ' if unset != 1 else ''}taking a run's value")


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


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _model_inputs(engine: Any, thing: Any, inputs: list[EngineInput]) -> list[EngineInput] | None:
    """Check 8's model path on a basis of its own: the checked run's values set
    as the model's estimates, or, with none, one of the thing's parameters set
    to its own default as the model's estimate: the first whose source rule
    takes a run's value (`assumption`), else the first with a default (a
    parameter the train engine reads from its inlet's run takes no run's
    value, and BioSTEAM's rules name the package alone); None when the thing
    takes none. Each estimate is dated the day the check runs (its origin's
    `at`), so the model's run is a basis of that day."""
    at = _today()
    if inputs:
        return [EngineInput(name=i.name, quantity=i.quantity.model_copy(update={"origin": Origin(
            kind="model-estimate", by=MODEL, at=at, note="conformance check 8: the checked run's value")}))
            for i in inputs]
    held = [p for p in engine.parameters(thing.id, _configuration_of(thing)) if p.value is not None]
    p = next((p for p in held if "assumption" in p.sourceRule), held[0] if held else None)
    if p is None:
        return None
    return [EngineInput(name=p.key, quantity=Quantity(value=p.value, unit=p.unit, origin=Origin(
        kind="model-estimate", by=MODEL, at=at, note="conformance check 8: the parameter's own default")))]


def _second_basis(chosen: list[Any], first: Any) -> tuple[str, str | None] | None:
    """A basis the checked run did not make, for check 8's model to ask through
    the tool door: another thing checked, in its configuration, else another
    configuration of the first; None when there is neither."""
    for th in chosen:
        if th.id != first.id:
            return th.id, _configuration_of(th)
    ran = _configuration_of(first)
    other = next((c for c in first.configurations if c != ran), None)
    return (first.id, other) if other is not None else None


def _refused_unknown(engine: Any, by: str) -> tuple[bool, str]:
    """Check 7. An engine built on WorkerEngine is offered the thing
    NO_SUCH_THING as though it were one of its own, taking no parameters: the
    first ask reaches its worker's `run` op once, the worker's `Refused` is
    kept as a receipt in the worker's words, and the same request asked again
    is answered from the receipt with the worker's `run` op never asked. Any
    other engine refuses the unknown thing in words, keeping nothing."""
    from ..engine import runs

    held = {r.id for r in runs.listed(engine.name)}
    if not callable(getattr(engine, "compute", None)):
        try:
            runs.run_with(engine, NO_SUCH_THING, None, [], by=by)
            return False, f"a run of {NO_SUCH_THING!r} was kept where it should have been refused"
        except (EngineRefused, LookupError, ValueError) as e:
            said = _words(e)
            kept = {r.id for r in runs.listed(engine.name)} - held
            return _traceless(said) and not kept, (f"refused in words, {len(kept)} run kept: {said[:200]}")

    computed: list[str] = []
    offered = EngineThing(id=NO_SUCH_THING, title="a thing the conformance check offers the worker as one of its own",
                          precision=EnginePrecision(rtol=0, atol=0))

    def things(fn: Callable[..., Any]) -> Callable[..., Any]:
        return lambda *a, **k: [*fn(*a, **k), offered]

    def parameters(fn: Callable[..., Any]) -> Callable[..., Any]:
        return lambda thing, configuration, *a, **k: [] if thing == NO_SUCH_THING else fn(thing, configuration, *a, **k)

    def compute(fn: Callable[..., Any]) -> Callable[..., Any]:
        def called(*a: Any, **k: Any) -> Any:
            computed.append("compute")
            return fn(*a, **k)
        return called

    asked: list[Any] = []
    with _spied(engine, {"things": things, "parameters": parameters, "compute": compute}):
        for _ in range(2):
            before = len(computed)
            try:
                runs.run_with(engine, NO_SUCH_THING, None, [], by=by)
                return False, f"its worker computed {NO_SUCH_THING!r} where it should have refused it, and a run was kept"
            except runs.RunRefused as e:
                asked.append((e, len(computed) - before))
            except Exception as e:  # a refusal that is no receipt, or a failure: said as it came
                return False, f"refused with no receipt: {type(e).__name__}: {_words(e)[:160]}"
    (once, first), (twice, again) = asked
    receipt = runs.get(once.run_id)
    said = (receipt.refused or "").strip()
    reached = first == 1
    from_receipt = twice.run_id == once.run_id and again == 0
    ok = receipt.status == "refused" and receipt.artifactId is None and _traceless(said) and reached and from_receipt
    return ok, ((f"its worker refused {NO_SUCH_THING!r}, kept as receipt {once.run_id} in its words: {said[:160]}; "
                 if reached else
                 f"the first ask reached its worker's run op {first} time{'s' if first != 1 else ''}, and the check "
                 f"holds when it reaches it once; it answered as receipt {once.run_id}: {said[:160]}; ")
                + ("asked again, answered from the receipt with the worker's run op never asked" if from_receipt else
                   f"asked again, answered as {twice.run_id} with the worker's run op asked {again} more "
                   f"time{'s' if again != 1 else ''}"))


def _model_path(engine: Any, chosen: list[Any], first: Any, inputs: list[EngineInput], run: EngineRun) -> tuple[bool, str]:
    """Check 8's second run, in a model's name, on a basis the checked run did
    not make. With no values set, through the tool door (`engine_run`, the
    model in the tool's context) on another thing or configuration; with
    values, or with no second basis, through `runs.run_with` with the values
    as the model's estimates. Either way its created_by column is read."""
    from .. import tools
    from ..engine import runs

    other = None if inputs else _second_basis(chosen, first)
    if other is not None:
        thing, configuration = other
        where = thing + (f" ({configuration})" if configuration else "")
        done = tools.run("engine_run", {"engine": engine.name, "plant": thing, "configuration": configuration or ""},
                         tools.ToolContext(model=MODEL))
        if done.error:
            return False, f"the model's run of {where} through the engine_run tool was refused: {done.error[:200]}"
        run_id = str(done.summary.get("runId") or "")
        who = _created_by(run_id)
        return (who == MODEL and done.summary.get("by") == MODEL and run_id != run.id), (
            f"a model's run of {where} through the engine_run tool ({run_id}): created_by {who!r}, asked by {MODEL!r}")
    asked = _model_inputs(engine, first, inputs)
    if asked is None:
        return True, f"the model's path needs a value to set or a second thing, and {first.id} takes none"
    m = runs.run_with(engine, first.id, _configuration_of(first), asked, by=MODEL).run
    who = _created_by(m.id)
    return (who == MODEL and m.by == MODEL and m.id != run.id), (
        f"a model's run ({m.id}, {len(asked)} value{'s' if len(asked) != 1 else ''} its estimate): created_by {who!r}, "
        f"asked by {MODEL!r}")


def checks(engine: Any, *, by: str, things: list[str] | None = None, entry: str | None = None,
           inputs: list[EngineInput] | None = None) -> list[EngineCheck]:
    """The eight checks of docs/api/engines.md on `engine`, in the current
    database and project. `things` narrows the checks to those things, in the
    order named, an id the engine runs none of refused in words: check 2
    reads the parameters of each, checks 3, 4, 5 and 8 run the first named,
    and check 8's model asks for the next; `entry` is the entry point's
    `module:attr` for check 6; `inputs` are the values the checked run sets,
    for a thing that waits for values its parameters give no default. A
    thing runs in its default configuration, or in the first it names."""
    from .. import artifacts
    from ..engine import runs

    inputs = list(inputs or [])

    out: list[EngineCheck] = []

    def add(n: int, ok: bool, said: str) -> None:
        out.append(EngineCheck(number=n, check=CHECKS[n], ok=ok, said=said))

    every = engine.things()
    by_id = {th.id: th for th in every}
    unknown = [t for t in things or [] if t not in by_id]
    if unknown:
        raise ConformRefused(f"the {engine.name} engine runs no {', '.join(map(repr, unknown))}; it runs "
                             f"{', '.join(th.id for th in every) or 'nothing'}")
    chosen = [by_id[t] for t in dict.fromkeys(things)] if things else list(every)
    if not chosen:
        raise ConformRefused(f"the {engine.name} engine runs nothing to check")
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
        a = runs.run_with(engine, first.id, _configuration_of(first), inputs, by=by).run
        b = runs.run_with(engine, first.id, _configuration_of(first), inputs, by=by).run
        rows = _row_count(a.id)
        keyed = False
        if a.artifactId is not None:
            art = artifacts.get(a.artifactId)
            keyed = artifacts.artifact_id(art.tool, art.toolVersion, art.inputs, art.seed) == a.id
        ok = a.id == b.id and rows == 1 and a.status == "done" and a.engine == engine.name and keyed
        run = a if a.status == "done" else None
        add(3, ok, f"run {a.id} of {first.id}" + (f" with {len(inputs)} value{'s' if len(inputs) != 1 else ''} set"
                                                     if inputs else "")
                   + f", asked twice, is {rows} row{'s' if rows != 1 else ''}; engine {a.engine}, status {a.status}; "
                   + ("its id the artifact id of its basis" if keyed else "its id is no artifact id of its basis")
                   + (f"; the second answered {b.id}" if a.id != b.id else "")
                   + (f"; refused: {a.refused}" if a.refused else ""))
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
        add(7, *_refused_unknown(engine, by))
    except Exception as e:
        add(7, False, f"the check could not be made: {type(e).__name__}: {_words(e)[:160]}")

    if run is None:
        add(8, False, "no run to read created_by from (check 3)")
    else:
        who = _created_by(run.id)
        ok = who == by and run.by == by
        words = f"a person's run: created_by {who!r}, its by {run.by!r}, asked by {by!r}"
        try:
            held, said = _model_path(engine, chosen, first, inputs, run)
            ok, words = ok and held, f"{words}; {said}"
        except Exception as e:
            ok, words = False, words + f"; the model's run could not be made: {type(e).__name__}: {_words(e)[:160]}"
        add(8, ok, words)
    return sorted(out, key=lambda c: c.number)


def _imports_alone(module: str, engine: Any) -> tuple[bool, str]:
    """Check 6, in a process of its own: what importing the entry point's
    module brings in of what the service keeps out for the engine
    (`registry.kept_out`: the worker module, the heavy modules it declares and
    `workers.WORKER_LIBRARIES`, each with every module below it)."""
    from .registry import kept_out

    worker, kept = kept_out(engine)
    heavy = sorted(kept)
    probe = ("import importlib, json, sys\n"
             f"importlib.import_module({module!r})\n"
             "loaded = list(sys.modules)\n"
             "from openferment_core.engine.registry import in_worker\n"
             f"w, heavy = {worker!r}, set({heavy!r})\n"
             "seen = sorted(m for m in loaded if in_worker(m, w, heavy))\n"
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


def _read_inputs(path: str) -> list[EngineInput]:
    """The values a checked run sets, from a JSON list of EngineInputs."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ConformRefused(f"{path} holds no JSON list of inputs")
    return [EngineInput.model_validate(i) for i in raw]


def _options(argv: list[str]) -> tuple[list[str], str | None, str | None]:
    """`--thing <id>`, as often as asked, `--inputs <file>` and `--project <id>`."""
    things: list[str] = []
    inputs: str | None = None
    project: str | None = None
    rest = list(argv)
    while rest:
        flag = rest.pop(0)
        if flag not in ("--thing", "--inputs", "--project") or not rest:
            raise ConformRefused(f"{flag!r} is no option here: --thing <id>, --inputs <file> or --project <id>")
        value = rest.pop(0)
        if flag == "--thing":
            things.append(value)
        elif flag == "--inputs":
            inputs = value
        else:
            project = value
    return things, inputs, project


# What the value check 3 sets in a named project rests on, in words.
OWN_BASIS_NOTE = ("conformance check 3: the parameter's own default, set so the checks' runs are a basis of their own "
                  "in the project they check")


def _own_basis(engine: Any, thing: Any, by: str) -> list[EngineInput]:
    """The value check 3 sets in a named project, so the checks' runs are a
    basis of their own there: one parameter at its own default, the first
    with a default whose source rule takes a run's value (`assumption`), as
    the checks' assumption (`by`) dated the day they run, so the checks'
    runs and the runs the project's people ask for keep rows of their own.
    None for a thing with no such parameter."""
    held = [p for p in engine.parameters(thing.id, _configuration_of(thing))
            if p.value is not None and "assumption" in p.sourceRule]
    if not held:
        return []
    p = held[0]
    return [EngineInput(name=p.key, quantity=Quantity(value=p.value, unit=p.unit, origin=Origin(
        kind="person-assumption", by=by, at=_today(), note=OWN_BASIS_NOTE)))]


def _project_thing(engine: Any, by: str, inputs: list[EngineInput]) -> tuple[Any, list[EngineInput], list[str]]:
    """The thing `--project` checks when none is named, with the values its
    run sets: the first the project holds that runs, on a basis of its own
    (`_own_basis`) unless values were given. A thing whose parameters cannot
    be read, or whose run is refused in words with nothing kept (a value
    that waits), is passed over, its words kept; the first that runs, or
    whose run its engine keeps a receipt of, is the one checked, its run the
    first ask check 3 makes again."""
    from ..engine import runs

    passed: list[str] = []
    for th in engine.things():
        values = list(inputs)
        try:
            values = values or _own_basis(engine, th, by)
            runs.run_with(engine, th.id, _configuration_of(th), values, by=by)
        except runs.RunRefused:  # a receipt the engine kept: its refusal is check 3's to say
            return th, values, passed
        except EngineRefused as e:  # refused in words, nothing kept
            passed.append(f"{th.id}: {_words(e)[:200]}")
            continue
        except Exception:  # anything else is check 3's to say, in its words
            return th, values, passed
        return th, values, passed
    held = "; ".join(passed) or "it holds none"
    raise ConformRefused(f"the project holds no thing of the {engine.name} engine that runs ({held}): name one with "
                         "--thing <id>")


def in_project(name: str, project_id: str, *, by: str, things: list[str] | None = None,
               inputs: list[EngineInput] | None = None) -> EngineConformance:
    """The eight checks on engine `name` in an existing project of the
    configured database (`--project`), the verdict kept for `GET
    /api/engines`. The checks run one thing: the first `things` names, else
    the first the project holds that runs (`_project_thing`), the things
    passed over said in check 3's words; on a basis of their own (`inputs`,
    or `_own_basis`), so check 8's model runs that thing too, on its own
    basis. The production database is refused, as `pnpm db:reset` refuses
    it, and so is a project the database does not hold, each in words
    (ConformRefused)."""
    from ..db.engine import PRODUCTION_NAME, database_url
    from . import registry

    database = database_url().database or ""
    if database == PRODUCTION_NAME:
        raise ConformRefused(f"database {database!r} is the production one, and the checks make runs in the project "
                             "they check, so they run in a project of a development database (pnpm db:reset refuses "
                             "the production one too)")
    if projects.get(project_id) is None:
        raise ConformRefused(f"database {database!r} holds no project {project_id!r}: name a project it holds")
    engine = registry.get(name)
    entry = registry.found()[name].entry
    passed: list[str] = []
    with projects.using(project_id):
        if things:
            first = {th.id: th for th in engine.things()}.get(things[0])
            values = list(inputs or [])
            if not values and first is not None:
                try:
                    values = _own_basis(engine, first, by)
                except EngineRefused:  # its parameters cannot be read: checks 2 and 3 say so in words
                    values = []
            named = things
        else:
            first, values, passed = _project_thing(engine, by, list(inputs or []))
            named = [first.id]
        found = checks(engine, by=by, entry=entry, things=named, inputs=values)
    if passed:
        found = [c.model_copy(update={"said": f"{c.said}; passed over before {named[0]}, each refused in words with "
                                              f"nothing kept: {'; '.join(passed)}"}) if c.number == 3 else c
                 for c in found]
    v = verdict(engine, found, by)
    keep(v)
    return v


def _inside(name: str, by: str, argv: list[str]) -> int:
    """In the scratch database: a project of its own, the checks, the verdict on stdout."""
    from . import registry
    from ..models import ProjectCreate

    things, inputs, _ = _options(argv)
    engine = registry.get(name)
    entry = registry.found()[name].entry
    made = projects.create(ProjectCreate(name=f"Conformance of {name}", by=by))
    with projects.using(made.id):
        found = checks(engine, by=by, entry=entry, things=things or None,
                       inputs=_read_inputs(inputs) if inputs else None)
    print(json.dumps(verdict(engine, found, by).model_dump(mode="json")))
    return 0


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    from ..db import migrate
    from ..db.engine import database_url
    from . import registry

    if argv[:1] == ["--inside"] and len(argv) >= 3:
        return _inside(argv[1], argv[2], argv[3:])
    usage = ("usage: python -m openferment_core.engine.conform <engine name> [--thing <id>]... [--inputs <file>] "
             "[--project <id>]")
    if not argv or argv[0].startswith("-"):
        print(usage)
        return 2
    name, options = argv[0], argv[1:]
    try:
        things, inputs, project = _options(options)
        if inputs:
            _read_inputs(inputs)
            options = [*options[: options.index("--inputs") + 1], str(Path(inputs).resolve()),
                       *options[options.index("--inputs") + 2:]]
    except (ConformRefused, OSError, ValueError) as e:
        print(f"✗ {_words(e)}\n{usage}")
        return 2
    load_dotenv(CORE / ".env", override=False)
    try:
        engine = registry.get(name)
    except (registry.EngineNotFound, registry.EngineUnavailable) as e:
        print(f"✗ {_words(e)}")
        return 1
    by = f"conformance check of {name}"
    if project is not None:
        try:
            v = in_project(name, project, by=by, things=things, inputs=_read_inputs(inputs) if inputs else None)
        except ConformRefused as e:
            print(f"✗ {_words(e)}")
            return 2
        print(table(v))
        return 0 if v.ok else 1
    things_are = getattr(engine, "things_are", None)
    if things_are:
        print(f"✗ the {name} engine's things are {things_are}. A database made for the checks holds none, so the "
              f"checks run in a project of the configured database (core/.env) that holds one: python -m "
              f"openferment_core.engine.conform {name} --project <id>")
        return 2
    server = database_url()
    scratch = f"openferment_conform_{name.replace('-', '_')}_{secrets.token_hex(4)}"
    url = migrate.create(scratch, server)
    try:
        migrate.upgrade(url)
        env = {**os.environ, "OPENFERMENT_DATABASE_URL": url.render_as_string(hide_password=False)}
        done = subprocess.run([sys.executable, "-m", "openferment_core.engine.conform", "--inside", name, by, *options],
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
