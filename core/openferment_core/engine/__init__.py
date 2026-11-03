"""The engine (execution prompt §7.2; ADR-003, ADR-004, ADR-015): every
engine behind one contract, BioSTEAM the first, and SFF as the flowsheet record.

    Engine      the protocol below: what the service asks of an engine
                (docs/api/engines.md)
    contract    `WorkerEngine`, the contract over four ops of a worker of
                the engine's own, and the version string a run is keyed by
    registry    the engines of the entry-point group `openferment.engines`,
                each loaded once, with what keeps one from use in words
    conform     the eight conformance checks, a verdict kept per engine
                (`python -m openferment_core.engine.conform <name>`)
    biosteam    BioSTEAM's engine: the library plants and openFerment's
                flowsheets through `library` and `runs`
    simulator   the Proforma worker, BioSTEAM in its own process: started,
                kept warm, and called by every BioSTEAM module
    sff         SFF flowsheet records: a run's export, an imported file, the
                toolkit's reference flowsheets fetched and hashed; each with
                its validation, completeness report, tags and graph
    library     the library plant runner: every plant the installed
                `biorefineries` exposes, on a shelf regenerated from
                discovery; its parameters read back as library defaults; a
                run with a person's values, priced, kept, held to the
                package's own test
    runs        every engine's runs on the `runs` table: a run's inputs
                with their origins, its artifact, its SFF file written and
                checked, its status (a refusal kept as a receipt)
    sample      the contract's own sample engine, for its tests; no entry
                point registers it

The engine imports what §7.2 lists (`db`, `models`, the `workers` client,
`params`, `binding`), and more until they move into it: the shelf's
package-test reader (`flowsheets/shelf.py`, no BioSTEAM) and the artifact
store a run is kept in (`artifacts`), the project a run belongs to
(`projects`), the provenance rules (`basis`), and the service's own route
and tool the conformance check sends a bare number to (`api`, `tools`).
BioSTEAM and the vendored SFF toolkit run in the worker alone
(workers/proforma_worker.py, workers/library_plants.py,
workers/sff_toolkit.py, flowsheets/). Importing this package imports none of
its modules.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..models import EngineInput, EngineParameter, EngineRun, EngineThing, ReplayResult, SFFFlowsheet

#: What every engine object declares, beside its three attributes.
METHODS = ("version", "things", "parameters", "run", "replay", "export_sff")


class EngineRefused(ValueError):
    """A request the engine cannot run, in its words (a receipt, never a traceback)."""


@runtime_checkable
class Engine(Protocol):
    """What the service asks of an engine (docs/api/engines.md, What it declares).

    `name` matches the entry point that registers it; `worker` is the module
    its heavy computation runs in, or None for an engine that computes in
    the service's process with nothing heavy; `heavy` names the modules the
    service process must never import (conformance check 6)."""

    name: str
    worker: str | None
    heavy: tuple[str, ...]

    def version(self) -> dict[str, str]: ...

    def things(self) -> list[EngineThing]: ...

    def parameters(self, thing: str, configuration: str | None) -> list[EngineParameter]: ...

    def run(self, thing: str, configuration: str | None, inputs: list[EngineInput], by: str) -> EngineRun: ...

    def replay(self, run: EngineRun) -> ReplayResult: ...

    def export_sff(self, run: EngineRun) -> SFFFlowsheet | str: ...
