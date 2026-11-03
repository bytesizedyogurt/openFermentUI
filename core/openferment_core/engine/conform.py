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
        [--project <id>]       check the things this project of the configured
                               database holds, in a copy of it, for an engine whose
                               things are a project's own (the train engine's trains)

The checks run on a database of their own, made on the server that
OPENFERMENT_DATABASE_URL names (core/.env) and dropped when they end, however
they end: a check that raises, Ctrl-C, SIGTERM or SIGHUP (`_scratch`). They
run in a project made for them, so nothing a person keeps is touched. An
engine whose things are all a project's own (it declares `things_are`, saying
what they are: the train engine's are a project's trains) lists nothing in a
fresh project, so it is checked with `--project <id>` (`in_project`) in a copy
of that project (`copy_of`): the rows its things rest on, as the engine names
them (`rests_on`), are read from the configured database and written under
the same ids into a project of the same id on the checks' own database. There
the checks run on each thing the copy holds that can run; each thing the
engine says cannot run as it stands (`unready`: a saved draft, a train whose
values wait for a source, a train whose run is refused before it computes) is
listed with its words in check 3's and left out. A run of the engine being
checked keeps no row in the copy, so every runs row the checks read is one
they made there. The command reads the production database (`openferment`) as
it reads any other. Without `--project` such an engine is refused in words
saying what its things are, and one that names nothing its things rest on is
refused either way (`unrested`). The verdict is kept in the `engine_checks`
table of the configured database (`keep`), where `GET /api/engines` and `pnpm
ready` read it: the checks' one write there, and the row is the machine's, so
the verdict of a project's things keeps counts in its words (`_counted`) and
the command's own table gives each thing's words. Exits 1 when any check
fails.

`checks(engine, ...)` runs the eight in whatever database and project are
current: a test's, or the copy's of a project.
"""
from __future__ import annotations

import contextlib
import json
import os
import secrets
import signal
import subprocess
import sys
import threading
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
# The name of every database the checks make begins with this, and as much of
# the engine's name joins it as a PostgreSQL name of 63 characters holds
# beside eight hex digits of its own.
SCRATCH = "openferment_conform"
SCRATCH_NAME_MAX = 32
# The signals a person or a supervisor ends a command with (a terminal that closes, `kill`, a process manager's
# stop): the checks turn each into SystemExit while their own database stands, so it is dropped as they end.
ENDING = tuple(s for s in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGHUP", None)) if s is not None)
# What each option of the command names.
OPTIONS = {"--thing": "a thing's id", "--inputs": "a file", "--project": "a project's id"}
# The checks made on every thing checked, each thing in turn (`checks`' `each`); check 2 reads every thing's
# parameters, and checks 1, 6 and 7 run once for the engine.
ON_EACH = (3, 4, 5, 8)


class ConformRefused(RuntimeError):
    """The checks could not be made at all, in words."""


def _words(e: BaseException) -> str:
    return str(e).strip().strip("'\"")


def _cut(said: str, most: int) -> str:
    """`said` whole when it holds `most` characters or fewer; else cut at the
    last space within them, an ellipsis marking the cut."""
    said = said.strip()
    if len(said) <= most:
        return said
    head = said[:most]
    space = head.rfind(" ")
    return (head[:space] if space > most // 2 else head).rstrip(" ,;:") + "…"


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


def as_served() -> None:
    """The engine as the service's process holds it: the service's app,
    which check 1 sends its numbers to, imported before anything is read, so
    every module that gives an engine things of its own as it is imported
    has given them (Proforma's scenario flowsheets, engine/biosteam.py
    `provide`). The checks call it first."""
    from .. import api  # noqa: F401


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
                + ("" if ok else f" (route said {_cut(json.dumps(detail), 200)}; tool said {tool.error!r})"))


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
            return _traceless(said) and not kept, (f"refused in words, {len(kept)} run kept: {_cut(said, 200)}")

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
                return False, f"refused with no receipt: {type(e).__name__}: {_cut(_words(e), 160)}"
    (once, first), (twice, again) = asked
    receipt = runs.get(once.run_id)
    said = (receipt.refused or "").strip()
    reached = first == 1
    from_receipt = twice.run_id == once.run_id and again == 0
    ok = receipt.status == "refused" and receipt.artifactId is None and _traceless(said) and reached and from_receipt
    return ok, ((f"its worker refused {NO_SUCH_THING!r}, kept as receipt {once.run_id} in its words: {_cut(said, 160)}; "
                 if reached else
                 f"the first ask reached its worker's run op {first} time{'s' if first != 1 else ''}, and the check "
                 f"holds when it reaches it once; it answered as receipt {once.run_id}: {_cut(said, 160)}; ")
                + ("asked again, answered from the receipt with the worker's run op never asked" if from_receipt else
                   f"asked again, answered as {twice.run_id} with the worker's run op asked {again} more "
                   f"time{'s' if again != 1 else ''}"))


def _model_path(engine: Any, chosen: list[Any], first: Any, inputs: list[EngineInput], run: EngineRun, *,
                door: bool = True) -> tuple[bool, str]:
    """Check 8's second run, in a model's name, on a basis the checked run did
    not make. With no values set and `door` open, through the tool door
    (`engine_run`, the model in the tool's context) on another thing or
    configuration; with values, with no second basis, or with `door` shut
    (every thing checked, each one's own run made by check 3: `checks`'
    `each`), through `runs.run_with` with the values as the model's estimates.
    Either way its created_by column is read."""
    from .. import tools
    from ..engine import runs

    other = None if inputs or not door else _second_basis(chosen, first)
    if other is not None:
        thing, configuration = other
        where = thing + (f" ({configuration})" if configuration else "")
        done = tools.run("engine_run", {"engine": engine.name, "plant": thing, "configuration": configuration or ""},
                         tools.ToolContext(model=MODEL))
        if done.error:
            return False, f"the model's run of {where} through the engine_run tool was refused: {_cut(done.error, 200)}"
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


def _run_twice(engine: Any, thing: Any, inputs: list[EngineInput], by: str) -> tuple[bool, str, EngineRun | None]:
    """Check 3 on one thing: its run, asked twice, is one row keyed by its
    basis. The run comes back with the words when it is done, for checks 4, 5
    and 8."""
    from .. import artifacts
    from ..engine import runs

    try:
        a = runs.run_with(engine, thing.id, _configuration_of(thing), inputs, by=by).run
        b = runs.run_with(engine, thing.id, _configuration_of(thing), inputs, by=by).run
        rows = _row_count(a.id)
        keyed = False
        if a.artifactId is not None:
            art = artifacts.get(a.artifactId)
            keyed = artifacts.artifact_id(art.tool, art.toolVersion, art.inputs, art.seed) == a.id
        ok = a.id == b.id and rows == 1 and a.status == "done" and a.engine == engine.name and keyed
        said = (f"run {a.id} of {thing.id}" + (f" with {len(inputs)} value{'s' if len(inputs) != 1 else ''} set"
                                                if inputs else "")
                + f", asked twice, is {rows} row{'s' if rows != 1 else ''}; engine {a.engine}, status {a.status}; "
                + ("its id the artifact id of its basis" if keyed else "its id is no artifact id of its basis")
                + (f"; the second answered {b.id}" if a.id != b.id else "")
                + (f"; refused: {a.refused}" if a.refused else "")
                # A run kept done that answers no output (a Proforma run whose samples priced nothing) says so.
                + ("; it answers no output: its outputs.values are empty" if a.status == "done"
                   and not (a.outputs or {}).get("values") else ""))
        return ok, said, a if a.status == "done" else None
    except Exception as e:  # a check that cannot be made fails in words
        return False, f"{thing.id} could not be run: {type(e).__name__}: {_words(e)}", None


def _replayed(engine: Any, run: EngineRun | None) -> tuple[tuple[bool, str], tuple[bool, str]]:
    """Checks 4 and 5 on one thing's run (check 3's): its replay held to the
    precision the thing states, and its SFF file or the words for why it has
    none."""
    if run is None:
        return (False, "no run to replay (check 3)"), (False, "no run to read its SFF file from (check 3)")
    try:
        r = engine.replay(run)
        # A replay with no tolerance holds when it is identical, and its words say that once.
        if r.tolerance is not None:
            state = ("identical" if r.identical else "within the precision" if r.withinTolerance else
                     "outside the precision") + f" (rtol {r.tolerance.rtol:g}, atol {r.tolerance.atol:g})"
        else:
            state = "identical" if r.identical else "different, where the thing's precision asks for identical outputs"
        four = (bool(r.withinTolerance or r.identical),
                f"{state}; {len(r.differences)} difference{'s' if len(r.differences) != 1 else ''}")
    except Exception as e:
        four = (False, f"the replay failed: {type(e).__name__}: {_words(e)}")
    if run.sff is not None:
        return four, (bool(run.sff.valid and run.sff.score is not None),
                      f"record {run.sff.recordId}: {'valid' if run.sff.valid else 'not valid'}, score {run.sff.score}")
    said = (run.sffRefused or "").strip()
    return four, (_traceless(said), f"no file, in words: {_cut(said, 200)}" if said else "no file, and no words for why")


def _asked_by(engine: Any, chosen: list[Any], thing: Any, inputs: list[EngineInput], run: EngineRun | None, by: str, *,
              door: bool) -> tuple[bool, str]:
    """Check 8 on one thing: check 3's run is the checks' own, and a second
    run in a model's name is the model's (`_model_path`)."""
    if run is None:
        return False, "no run to read created_by from (check 3)"
    who = _created_by(run.id)
    ok = who == by and run.by == by
    words = f"the checks' run: created_by {who!r}, its by {run.by!r}, asked by {by!r}"
    try:
        held, said = _model_path(engine, chosen, thing, inputs, run, door=door)
        return ok and held, f"{words}; {said}"
    except Exception as e:
        return False, words + f"; the model's run could not be made: {type(e).__name__}: {_cut(_words(e), 160)}"


def checks(engine: Any, *, by: str, things: list[str] | None = None, entry: str | None = None,
           inputs: list[EngineInput] | None = None, each: bool = False) -> list[EngineCheck]:
    """The eight checks of docs/api/engines.md on `engine`, in the current
    database and project. `things` narrows the checks to those things, in the
    order named, an id the engine runs none of refused in words: check 2
    reads the parameters of each, checks 3, 4, 5 and 8 run the first named,
    and check 8's model asks for the next. With `each`, checks 3, 4, 5 and 8
    run on every thing named, in order, each holding when it holds on every
    one, its words each thing's in turn, and check 8's model asks for each on
    a basis of its own on that thing (a project's things, checked in a copy
    of the project: `in_project`). `entry` is the entry point's `module:attr`
    for check 6; `inputs` are the values the checked run sets, for a thing
    that waits for values its parameters give no default. A thing runs in its
    default configuration, or in the first it names. The engine is read as
    the service's process holds it (`as_served`)."""
    as_served()
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

    ran = chosen if each else [first]
    made = [_run_twice(engine, th, inputs, by) for th in ran]
    replays = [_replayed(engine, run) for _, _, run in made]

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
        add(7, False, f"the check could not be made: {type(e).__name__}: {_cut(_words(e), 160)}")

    asked = [_asked_by(engine, chosen, th, inputs, run, by, door=not each) for th, (_, _, run) in zip(ran, made)]

    def on_each(n: int, held: list[tuple[bool, str]]) -> None:
        if len(held) == 1:
            add(n, *held[0])
        else:
            add(n, all(ok for ok, _ in held), "; ".join(f"{th.id}: {said}" for th, (_, said) in zip(ran, held)))

    on_each(3, [(ok, said) for ok, said, _ in made])
    on_each(4, [four for four, _ in replays])
    on_each(5, [five for _, five in replays])
    on_each(8, asked)
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
    """The engine's verdict, replacing its last: one row of the `engine_checks`
    table, the machine's and no project's, in the database the session binds
    (the configured one, as the command keeps it after its own database is
    gone)."""
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
        if flag not in OPTIONS:
            raise ConformRefused(f"unknown option {flag}: the options are --thing <id>, --inputs <file> and "
                                 "--project <id>")
        if not rest or rest[0] in OPTIONS:
            raise ConformRefused(f"{flag} needs {OPTIONS[flag]}")
        value = rest.pop(0)
        if flag == "--thing":
            things.append(value)
        elif flag == "--inputs":
            inputs = value
        else:
            project = value
    return things, inputs, project


# ── a project's things, checked in a copy of the project ────────────────


@contextlib.contextmanager
def _signals_end_the_block() -> Iterator[None]:
    """SIGTERM and SIGHUP raise SystemExit for the block (ENDING), its code
    128 and the signal's number as a shell reports it, so every finally
    clause runs and the checks' own database is dropped; each signal's
    handler is put back after. Python installs a handler on its main thread
    alone, so on any other thread the block runs with the handlers as they
    are."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def end(number: int, _frame: Any) -> None:
        raise SystemExit(128 + number)

    held = {s: signal.signal(s, end) for s in ENDING}
    try:
        yield
    finally:
        for s, handler in held.items():
            signal.signal(s, handler if handler is not None else signal.SIG_DFL)


def _drop_or_say(migrate: Any, scratch: str, server: Any) -> None:
    """The checks' database dropped as the block ends by an exception; a drop
    that fails too says so on stderr, with the command that drops it, and
    leaves the block's own exception to go on."""
    try:
        migrate.drop(scratch, server)
    except Exception as e:
        print(f"! the checks' database {scratch} is still on the server ({type(e).__name__}: {_cut(_words(e), 160)}); "
              f"python -m openferment_core.migrations drop {scratch} drops it", file=sys.stderr)


@contextlib.contextmanager
def _scratch(name: str) -> Iterator[Any]:
    """A database of the checks' own on the server the configured address
    names, migrated to the newest schema: its address, and the database
    dropped when the block ends, however it ends: a check that raises, Ctrl-C,
    SIGTERM or SIGHUP (`_signals_end_the_block`). A process killed outright
    (SIGKILL, a machine that stops) leaves it on the server, its name
    beginning SCRATCH and holding the migrated schema and no row, since every
    row the checks write stays in a transaction they never commit; `python -m
    openferment_core.migrations drop <name>` drops it. A database the server
    refuses to make is never dropped, since nothing of the checks' stands."""
    from ..db import migrate
    from ..db.engine import database_url

    server = database_url()
    scratch = f"{SCRATCH}_{name.replace('-', '_')[:SCRATCH_NAME_MAX]}_{secrets.token_hex(4)}"
    made = dropped = False
    with _signals_end_the_block():
        try:
            url = migrate.create(scratch, server)
            made = True
            migrate.upgrade(url)
            yield url
            migrate.drop(scratch, server)
            dropped = True
        except BaseException as e:
            # An interrupt can land as the server makes the database, before `made` is set: dropped too.
            if not dropped and (made or not isinstance(e, Exception)):
                _drop_or_say(migrate, scratch, server)
            raise


def _table(name: str) -> Any:
    """The table of a project's rows that an engine's things rest on, by its
    name in the openferment schema; refused in words for any other name."""
    table = t.metadata.tables.get(f"{db.SCHEMA}.{name}")
    if table is None or "project_id" not in table.c:
        raise ConformRefused(f"the name {name!r} is no table of a project's rows in the {db.SCHEMA} schema")
    return table


def unrested(engine: Any) -> str | None:
    """Why no command checks an engine whose things are a project's own (it
    declares `things_are`) and that names nothing they rest on (`rests_on`),
    which the checks copy, in words; None for every other engine. Such an
    engine loads and runs, and `pnpm ready` says these words in its row."""
    if getattr(engine, "things_are", None) and not callable(getattr(engine, "rests_on", None)):
        return (f"the {engine.name} engine's things are {engine.things_are}, and it declares no rests_on() naming the "
                "rows they rest on, which the checks copy into a database of their own to check them; an engine that "
                "declares things_are declares rests_on beside it (docs/api/engines.md, What it declares)")
    return None


def _resting(engine: Any, project_id: str) -> dict[str, list[dict[str, Any]]]:
    """What the engine's things rest on in project `project_id`, read from the
    database the session binds, with nothing written there: the project's own
    row, then each table's rows that `engine.rests_on()` names, by table, each
    row whole (its every column, as the table keeps it). A table it names with
    None gives every row of the project; with columns, the rows whose columns
    hold one of the values named. A runs row of the engine being checked is
    left out, so every runs row of its things the copy holds is one the
    checks made there. An artifact is copied as its id is named: a train run
    another train's inlet reads is copied as its artifact, so the checks' run
    of the first train at that run's values is answered from it (its row the
    checks' own), and check 4's replay computes it again."""
    from sqlalchemy import select

    asked = getattr(engine, "rests_on", None)
    if not callable(asked):
        raise ConformRefused(unrested(engine) or (
            f"the {engine.name} engine declares no things_are, so its things are checked in a project made for the "
            f"checks on a database of their own: python -m openferment_core.engine.conform {engine.name}, with no "
            "--project"))
    with projects.using(project_id):
        named = asked()
    chosen: list[tuple[str, Any, dict[str, list[str]]]] = []
    for name, where in named.items():
        table = _table(name)
        lacking = [c for c in where or {} if c not in table.c]
        if lacking:
            raise ConformRefused(f"the {engine.name} engine names columns {', '.join(lacking)} the table {name} lacks")
        chosen.append((name, table, dict(where or {})))

    async def read() -> dict[str, list[dict[str, Any]]]:
        async with db.session() as s:
            out = {"projects": [dict(r) for r in (await s.execute(
                select(t.projects).where(t.projects.c.id == project_id))).mappings()]}
            for name, table, where in chosen:
                q = select(table).where(table.c.project_id == project_id,
                                        *(table.c[c].in_(list(v)) for c, v in where.items()))
                if table is t.runs:
                    q = q.where(t.runs.c.engine != engine.name)
                out[name] = [dict(r) for r in (await s.execute(q)).mappings()]
        return out

    return db.run(read())


async def _plant(connection: Any, held: dict[str, list[dict[str, Any]]]) -> None:
    """The rows `_resting` read, written into the checks' own database as they
    were read, under the same keys, the project's own row first; each
    identity column's sequence then stands at the largest value copied, so a
    row the checks add there takes the next."""
    from sqlalchemy import insert, text

    for name in ("projects", *(n for n in held if n != "projects")):
        found = held.get(name) or []
        if not found:
            continue
        table = t.projects if name == "projects" else _table(name)
        await connection.execute(insert(table), found)
        for c in table.c:
            if c.identity is not None:
                await connection.execute(text(
                    f'SELECT setval(pg_get_serial_sequence(:table, :column), (SELECT max("{c.name}") FROM '
                    f'"{db.SCHEMA}"."{table.name}"))'), {"table": f"{db.SCHEMA}.{table.name}", "column": c.name})


@contextlib.contextmanager
def copy_of(engine: Any, project_id: str) -> Iterator[dict[str, int]]:
    """Project `project_id` as the engine's things see it, copied into a
    database of the checks' own: the rows they rest on read from the
    configured database (`_resting`), with nothing written there, and written
    under the same ids into a project of the same id on the checks' own.
    Inside the block every session is a savepoint of one transaction on that
    database, in that project; when the block ends the sessions bind as they
    did before it, the transaction is rolled back and its connection given
    up, and the database is dropped with all the block made there (`_scratch`).
    A rollback or a pool that cannot close (a connection still busy with a
    query an interrupt cut short) gives way to the drop, which ends that
    connection, so what ended the block is what the caller meets. Yields how
    many rows of each table were copied."""
    held = _resting(engine, project_id)
    with _scratch(engine.name) as url:
        made = db.make_engine(url, pool_size=1, max_overflow=0)
        binding = db.Binding(made, prepare=lambda connection: _plant(connection, held))
        previous = db.bind(binding)
        try:
            with projects.using(project_id):
                yield {name: len(found) for name, found in held.items()}
        finally:
            db.bind(previous)
            for step in (binding.close, made.dispose):
                with contextlib.suppress(Exception):
                    db.run(step())


def _listed(left: list[tuple[str, str]]) -> str:
    """The things the checks leave out, in words: each numbered, with its id
    and its words, so each stands apart from the next."""
    return (f"left out, {len(left)} thing{'s' if len(left) != 1 else ''}, each with its words: "
            + "; ".join(f"({n}) {thing}, {said}" for n, (thing, said) in enumerate(left, 1)))


def _checkable(engine: Any, things: list[str] | None, inputs: list[EngineInput]) -> tuple[list[str],
                                                                                         list[tuple[str, str]]]:
    """The things the checks run in a copy of a project, and each one left
    out with its words. Things named are checked as named. Otherwise every
    thing the copy holds that can run with `inputs`, the values set on every
    thing checked: one the engine says cannot run as it stands
    (`unready(thing, inputs)`: the train engine's saved draft, its train
    whose values wait for a source, and its train whose run is refused before
    it computes, a value naming a place the train lacks among them) is left
    out, with its words. One whose readiness cannot be read is checked, and
    check 3 says what its run met. A copy that holds no thing that can run is
    refused in words: one that holds no thing at all says what the engine's
    things are."""
    if things:
        return list(things), []
    ask = getattr(engine, "unready", None)
    chosen: list[str] = []
    left: list[tuple[str, str]] = []
    for th in engine.things():
        try:
            said = ask(th.id, list(inputs)) if callable(ask) else None
        except Exception:  # check 3 says what the run meets, in its words
            said = None
        if said:
            left.append((th.id, said))
        else:
            chosen.append(th.id)
    if not chosen and not left:
        raise ConformRefused(f"the project holds none of the {engine.name} engine's things, which are "
                             f"{getattr(engine, 'things_are', None) or 'what it lists in a project'}: make one there, "
                             "then run the checks again")
    if not chosen:
        raise ConformRefused(f"the project holds no thing of the {engine.name} engine that can run as it stands; "
                             f"{_listed(left)}. Make one that runs; set the values a waiting thing needs with --inputs "
                             "<file>; or name one with --thing <id> to check it as it stands")
    return chosen, left


def _counted(v: EngineConformance, checked: int, left: int) -> EngineConformance:
    """A verdict of a project's things as `engine_checks` keeps it. The row is
    the machine's, no project's, so each check's words give counts alone (the
    things checked, and the things left out) and name no project, thing or
    run; the command's own table gives each thing's words."""
    things = (f"the {checked} thing{'s' if checked != 1 else ''} of a project, checked in a copy of it"
              + (f", {left} more left out" if left else ""))

    def said(c: EngineCheck) -> str:
        if c.number in ON_EACH:
            scope = f"on {('each of ' if c.ok else 'one or more of ') if checked != 1 else ''}{things}"
        elif c.number == 2:
            scope = f"over the parameters of {things}"
        else:
            scope = "for the engine"
        return f"{'held' if c.ok else 'failed'} {scope}; the command's own table gives the words"

    return v.model_copy(update={"checks": [c.model_copy(update={"said": said(c)}) for c in v.checks]})


def in_project(name: str, project_id: str, *, by: str, things: list[str] | None = None,
               inputs: list[EngineInput] | None = None) -> EngineConformance:
    """The eight checks on engine `name`, whose things are a project's own,
    over project `project_id` of the configured database (`--project`), the
    verdict kept for `GET /api/engines`. The project is checked in a copy of
    it (`copy_of`): what its things rest on is read from the configured
    database, where the checks write their verdict alone, and the checks run
    on the copy in a database of their own, dropped after. They run on each
    thing `things` names, else on each thing the copy holds that can run
    (`_checkable`), checks 3, 4, 5 and 8 on every one (`checks`' `each`),
    with the values `inputs` sets on every one. Check 3's words end with
    where the checks ran and how many rows were copied, then each thing left
    out, numbered, with its words. The verdict returned carries every
    thing's words; the one kept in the configured database's `engine_checks`
    (`keep`) gives counts in their place (`_counted`). A project the database
    does not hold, and one that holds no thing that can run, are refused in
    words (ConformRefused), with nothing kept, the engine's last verdict
    standing. The production database is read as any other."""
    from ..db.engine import database_url
    from . import registry

    if projects.get(project_id) is None:
        raise ConformRefused(f"database {database_url().database or ''!r} holds no project {project_id!r}: name a "
                             "project it holds")
    engine = registry.get(name)
    entry = registry.found()[name].entry
    values = list(inputs or [])
    with copy_of(engine, project_id) as copied:
        chosen, left = _checkable(engine, things, values)
        found = checks(engine, by=by, entry=entry, things=chosen, inputs=values, each=True)
    rows = sum(copied.values())
    where = (f"made in a copy of project {project_id} on a database of the checks' own, {rows} row"
             f"{'s' if rows != 1 else ''} copied, and the verdict alone written to the database they were read from"
             + (f"; {_listed(left)}" if left else ""))
    found = [c.model_copy(update={"said": f"{c.said}; {where}"}) if c.number == 3 else c for c in found]
    v = verdict(engine, found, by)
    keep(_counted(v, len(chosen), len(left)))
    return v


def _inside(name: str, by: str, argv: list[str]) -> int:
    """In the scratch database: a project of its own, the checks, the verdict on stdout."""
    from . import registry
    from ..models import ProjectCreate

    things, inputs, _ = _options(argv)
    engine = registry.get(name)
    entry = registry.found()[name].entry
    # A thing the checks would run that cannot run as it stands (the engine's
    # `unready`: biosteam's scenario flowsheet with its values unset) is
    # refused in words before anything is made, so no failing verdict stands
    # in for the engine's.
    as_served()
    values = _read_inputs(inputs) if inputs else []
    ask = getattr(engine, "unready", None)
    first = (things or [t.id for t in engine.things()])[:1]
    said = ask(first[0], values) if callable(ask) and first else None
    if said:
        print(f"{first[0]} cannot be checked as it stands: {said}; set its values with --inputs <file>", file=sys.stderr)
        return 2
    made = projects.create(ProjectCreate(name=f"Conformance of {name}", by=by))
    with projects.using(made.id):
        found = checks(engine, by=by, entry=entry, things=things or None,
                       inputs=_read_inputs(inputs) if inputs else None)
    print(json.dumps(verdict(engine, found, by).model_dump(mode="json")))
    return 0


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

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
        print(f"✗ {unrested(engine)}" if unrested(engine) else
              f"✗ the {name} engine's things are {things_are}. A database made for the checks holds none, so the "
              f"checks run in a copy of a project of the configured database (core/.env) that holds one: python -m "
              f"openferment_core.engine.conform {name} --project <id>")
        return 2
    with _scratch(name) as url:
        env = {**os.environ, "OPENFERMENT_DATABASE_URL": url.render_as_string(hide_password=False)}
        done = subprocess.run([sys.executable, "-m", "openferment_core.engine.conform", "--inside", name, by, *options],
                              capture_output=True, text=True, cwd=str(CORE), env=env, timeout=1800)
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
