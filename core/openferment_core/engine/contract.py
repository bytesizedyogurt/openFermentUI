"""The engine contract (docs/api/engines.md; ADR-015).

An engine is one object a package registers under the entry-point group
`openferment.engines`. `Engine` (engine/__init__.py) names what the service asks of it.
`WorkerEngine` implements every method over four ops of a worker of the
engine's own (`things`, `parameters`, `run`, `sff_export`), so a package
outside this repository declares its name, its worker, its distributions and
the heavy modules its worker computes with, and writes the worker; its runs
are kept, keyed, replayed and filed by the service (`engine/runs.py`
`run_engine`), the same for every such engine.

The worker starts with the service's interpreter and its environment less
every variable `workers.withheld` names: those beginning ANTHROPIC_ or
SCI_RAG_, and those whose name holds KEY, TOKEN, SECRET, PASSWORD, PASSWD,
DATABASE_URL or CREDENTIAL. A worker that answers outside the protocol
raises `EngineBroken`; a `Refused` the worker raises is the engine's own
refusal (`EngineRefused`). This module imports no engine and nothing heavy;
the registry loads engines (`engine/registry.py`).
"""
from __future__ import annotations

import importlib.metadata
import json
import math
import threading
from typing import Any

from pydantic import ValidationError

from ..models import EngineInput, EngineParameter, EngineRun, EngineThing, ReplayResult, SFFFlowsheet
from ..workers import SimWorker, WorkerError
from . import Engine, EngineBroken, EngineRefused

# How long one op of an engine's worker may take before the process is killed.
WORKER_TIMEOUT_S = 120.0
# The stem of every contract engine's tool version: how `runs.run_engine` keys
# a run and shapes its outputs. A change to either moves it, so a run kept
# before reads as made by an earlier version (stale), and its id stays its own.
CONTRACT_RUN = "engine run 1"
# The longest name an output of an engine's run may have.
MAX_OUTPUT_NAME = 200


def version_string(engine: Engine) -> str:
    """The contract's stem, the engine's name and every distribution it runs
    on with its version, joined: the run's tool version, which enters every
    run's id."""
    return " · ".join([CONTRACT_RUN, engine.name, *(f"{d} {v}" for d, v in sorted(engine.version().items()))])


class WorkerEngine:
    """An engine over the four ops of its own worker (docs/api/engines.md,
    WorkerEngine). `version()` reads the installed distributions; `things()`
    asks the `things` op once a process; `parameters()` asks the
    `parameters` op; `run()` asks `things`, `parameters`, `run` and
    `sff_export` in turn through `runs.run_engine`; `replay()` asks the `run`
    op again through the run's artifact tool; `export_sff()` reads the record
    the run kept."""

    def __init__(self, *, name: str, worker: str, distributions: tuple[str, ...] | list[str] = (),
                 heavy: tuple[str, ...] | list[str] = (), timeout_s: float = WORKER_TIMEOUT_S) -> None:
        self.name = name
        self.worker = worker
        self.distributions = tuple(distributions)
        self.heavy = tuple(heavy)
        self.timeout_s = timeout_s
        self._sim: SimWorker | None = None
        self._lock = threading.Lock()
        # What the worker runs, kept for the life of this process after its
        # first answer: a WorkerEngine's things are its worker's own, the same
        # on every ask (docs/api/engines.md, Discovery).
        self._things: list[EngineThing] | None = None

    def __repr__(self) -> str:
        return f"WorkerEngine(name={self.name!r}, worker={self.worker!r})"

    # ── the worker ──────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        """`ready` while the worker's process answers, `cold` before its first use."""
        return "ready" if self._sim is not None and self._sim.alive else "cold"

    def call(self, op: str, args: dict[str, Any], *, timeout_s: float | None = None) -> Any:
        """One op of the worker, started on first use with its secrets
        withheld, given `timeout_s` (the engine's own per-op timeout when
        None); a `Refused` the worker raises comes back as EngineRefused, in
        its words."""
        with self._lock:
            if self._sim is None:
                self._sim = SimWorker(self.worker, timeout_s=self.timeout_s, withhold_secrets=True)
            sim = self._sim
        try:
            return sim.call(op, args, timeout_s=timeout_s)
        except WorkerError as e:
            said = str(e)
            if said.startswith("Refused: "):
                raise EngineRefused(said.removeprefix("Refused: ")) from None
            raise

    def _broken(self, op: str, what: str, got: Any) -> EngineBroken:
        return EngineBroken(f"the {self.name} worker's {op} op answered {what}, outside the protocol "
                            f"(docs/api/workers.md, Engine ops): {json.dumps(got, default=str)[:200]}")

    def _answer(self, op: str, args: dict[str, Any], key: str, *, timeout_s: float | None = None) -> Any:
        got = self.call(op, args, timeout_s=timeout_s)
        if not isinstance(got, dict) or key not in got:
            raise self._broken(op, f"no {key!r}", got)
        return got[key]

    def _listed(self, op: str, key: str, model: Any, args: dict[str, Any], *,
                timeout_s: float | None = None) -> list[Any]:
        got = self._answer(op, args, key, timeout_s=timeout_s)
        if not isinstance(got, list):
            raise self._broken(op, f"{key} that are no list", got)
        try:
            return [model.model_validate(x) for x in got]
        except ValidationError as e:
            problems = "; ".join(f"{'.'.join(str(p) for p in err['loc']) or key}: {err['msg']}" for err in e.errors())
            raise EngineBroken(f"the {self.name} worker's {op} op answered {key} outside their shape: {problems[:300]}") from None

    # ── what the service asks ───────────────────────────────────────────

    def version(self) -> dict[str, str]:
        """Each named distribution with the version its installed metadata
        records (an editable install keeps the version it was installed at,
        until it is installed again); one not installed reads `not
        installed`, and enters the version string so."""
        out: dict[str, str] = {}
        for d in self.distributions:
            try:
                out[d] = importlib.metadata.version(d)
            except importlib.metadata.PackageNotFoundError:
                out[d] = "not installed"
        return out

    def things(self, *, timeout_s: float | None = None) -> list[EngineThing]:
        """What the worker runs, asked once in this process and kept after
        its first answer; `timeout_s` bounds that first ask (the listing's
        short wait on a cold worker, `registry.info`)."""
        if self._things is None:
            self._things = self._listed("things", "things", EngineThing, {}, timeout_s=timeout_s)
        return list(self._things)

    def parameters(self, thing: str, configuration: str | None) -> list[EngineParameter]:
        return self._listed("parameters", "parameters", EngineParameter, {"thing": thing, "configuration": configuration})

    def compute(self, thing: str, configuration: str | None, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """The worker's `run` op on values already checked: each output a
        name, a finite number or a string, and a unit, every name its own."""
        outputs = self._answer("run", {"thing": thing, "configuration": configuration, "inputs": values}, "outputs")
        if not isinstance(outputs, list):
            raise self._broken("run", "outputs that are no list", outputs)
        seen: set[str] = set()
        for o in outputs:
            ok = (isinstance(o, dict) and isinstance(o.get("name"), str) and isinstance(o.get("unit"), str)
                  and isinstance(o.get("value"), (int, float, str)) and not isinstance(o.get("value"), bool))
            if not ok:
                raise self._broken("run", "an output that is no name, value and unit", o)
            if isinstance(o["value"], float) and not math.isfinite(o["value"]):
                raise self._broken("run", "an output whose number is NaN or infinite", o)
            name = o["name"]
            if not name.strip() or len(name) > MAX_OUTPUT_NAME:
                raise self._broken("run", f"an output whose name is blank or longer than {MAX_OUTPUT_NAME} characters", o)
            if name in seen:
                raise self._broken("run", f"two outputs named {name!r}", outputs)
            seen.add(name)
        return outputs

    def sff_document(self, thing: str, configuration: str | None, values: list[dict[str, Any]]) -> dict[str, Any]:
        """The worker's `sff_export` op: an SFF document, or EngineRefused in the engine's words."""
        doc = self._answer("sff_export", {"thing": thing, "configuration": configuration, "inputs": values}, "flowsheet")
        if not isinstance(doc, dict):
            raise self._broken("sff_export", "a flowsheet that is no JSON object", doc)
        return doc

    def run(self, thing: str, configuration: str | None, inputs: list[EngineInput], by: str) -> EngineRun:
        from . import runs

        return runs.run_engine(self, thing, configuration, inputs, by=by).run

    def replay(self, run: EngineRun) -> ReplayResult:
        from .. import artifacts

        if run.artifactId is None:
            raise EngineRefused(f"run {run.id} was refused, so there is nothing to replay")
        return artifacts.replay(run.artifactId)

    def export_sff(self, run: EngineRun) -> SFFFlowsheet | str:
        """The SFF file the run wrote, as its flowsheet record (validated and
        scored when it was kept), or the words the run kept for why none was."""
        return sff_of(run)


def sff_of(run: EngineRun) -> SFFFlowsheet | str:
    """A kept run's SFF file as its flowsheet record, or its words for why none was written."""
    from .. import projects
    from . import sff

    if run.sff is not None:
        return sff.get(run.sff.recordId, project_id=projects.current())
    return run.sffRefused or f"run {run.id} kept no SFF file"
