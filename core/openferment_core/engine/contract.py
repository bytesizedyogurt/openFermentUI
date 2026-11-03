"""The engine contract (docs/api/engines.md; ADR-015).

An engine is one object a package registers under the entry-point group
`openferment.engines`. `Engine` (engine/__init__.py) names what the service asks of it.
`WorkerEngine` implements every method over four ops of a worker of the
engine's own (`things`, `parameters`, `run`, `sff_export`), so a package
outside this repository declares its name, its worker and its distributions
and writes the worker; its runs are kept, keyed, replayed and filed by the
service (`engine/runs.py` `run_engine`), the same for every such engine.

The worker starts with the service's interpreter and its environment less
every key, token, password and database address (`workers.withheld`). This
module imports no engine and nothing heavy; the registry loads engines
(`engine/registry.py`).
"""
from __future__ import annotations

import importlib.metadata
import json
import threading
from typing import Any

from ..models import EngineInput, EngineParameter, EngineRun, EngineThing, ReplayResult, SFFFlowsheet
from ..workers import SimWorker, WorkerError
from . import Engine, EngineRefused

# How long one op of an engine's worker may take before the process is killed.
WORKER_TIMEOUT_S = 120.0


def version_string(engine: Engine) -> str:
    """The engine's name and every distribution it runs on with its version,
    joined: the run's tool version, which enters every run's id."""
    return " · ".join([engine.name, *(f"{d} {v}" for d, v in sorted(engine.version().items()))])


class WorkerEngine:
    """An engine whose every method calls one op of its own worker
    (docs/api/engines.md, WorkerEngine)."""

    def __init__(self, *, name: str, worker: str, distributions: tuple[str, ...] | list[str] = (),
                 heavy: tuple[str, ...] | list[str] = (), timeout_s: float = WORKER_TIMEOUT_S) -> None:
        self.name = name
        self.worker = worker
        self.distributions = tuple(distributions)
        self.heavy = tuple(heavy)
        self.timeout_s = timeout_s
        self._sim: SimWorker | None = None
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"WorkerEngine(name={self.name!r}, worker={self.worker!r})"

    # ── the worker ──────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        """`ready` while the worker's process answers, `cold` before its first use."""
        return "ready" if self._sim is not None and self._sim.alive else "cold"

    def call(self, op: str, args: dict[str, Any]) -> Any:
        """One op of the worker, started on first use with its secrets
        withheld; a `Refused` the worker raises comes back as EngineRefused,
        in its words."""
        with self._lock:
            if self._sim is None:
                self._sim = SimWorker(self.worker, timeout_s=self.timeout_s, withhold_secrets=True)
            sim = self._sim
        try:
            return sim.call(op, args)
        except WorkerError as e:
            said = str(e)
            if said.startswith("Refused: "):
                raise EngineRefused(said.removeprefix("Refused: ")) from None
            raise

    def _answer(self, op: str, args: dict[str, Any], key: str) -> Any:
        got = self.call(op, args)
        if not isinstance(got, dict) or key not in got:
            raise EngineRefused(f"the {self.name} worker's {op} answered no {key!r}: {json.dumps(got)[:200]}")
        return got[key]

    # ── what the service asks ───────────────────────────────────────────

    def version(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for d in self.distributions:
            try:
                out[d] = importlib.metadata.version(d)
            except importlib.metadata.PackageNotFoundError:
                out[d] = "not installed"
        return out

    def things(self) -> list[EngineThing]:
        return [EngineThing.model_validate(t) for t in self._answer("things", {}, "things")]

    def parameters(self, thing: str, configuration: str | None) -> list[EngineParameter]:
        return [EngineParameter.model_validate(p)
                for p in self._answer("parameters", {"thing": thing, "configuration": configuration}, "parameters")]

    def compute(self, thing: str, configuration: str | None, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """The worker's `run` op on values already checked: each output a
        name, a number or a string, and a unit."""
        outputs = self._answer("run", {"thing": thing, "configuration": configuration, "inputs": values}, "outputs")
        if not isinstance(outputs, list):
            raise EngineRefused(f"the {self.name} worker's run answered outputs that are no list")
        for o in outputs:
            ok = (isinstance(o, dict) and isinstance(o.get("name"), str) and isinstance(o.get("unit"), str)
                  and isinstance(o.get("value"), (int, float, str)) and not isinstance(o.get("value"), bool))
            if not ok:
                raise EngineRefused(f"the {self.name} worker's run answered an output that is no name, value and unit: "
                                    f"{json.dumps(o)[:200]}")
        return outputs

    def sff_document(self, thing: str, configuration: str | None, values: list[dict[str, Any]]) -> dict[str, Any]:
        """The worker's `sff_export` op: an SFF document, or EngineRefused in the engine's words."""
        doc = self._answer("sff_export", {"thing": thing, "configuration": configuration, "inputs": values}, "flowsheet")
        if not isinstance(doc, dict):
            raise EngineRefused(f"the {self.name} worker's sff_export answered a flowsheet that is no JSON object")
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
