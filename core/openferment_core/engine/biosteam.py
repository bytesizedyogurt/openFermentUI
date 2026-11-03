"""BioSTEAM as an engine (docs/api/engines.md; ADR-004, ADR-015).

The first engine, registered through the entry-point group like any other
(core/pyproject.toml). It is the library adapter as it was: its things are the
plants and flowsheets the shelf found buildable here (`library.shelf`), its
parameters what the package builds each with (`library.parameters`, every
default a `library-default` naming the package it was read from), and a run is
`runs.run`, the Proforma worker building the plant fresh, every number and test
as before (the A→B→A gate, the replay precision, the package-test values of
ADR-013). A value a run sets is checked against the plant's parameters (its
key, unit and kind, `runs.check_inputs`) and reaches the plant as the
`Override` the adapter has always taken, its origin the person or the model
that set it and the day its origin names. A value outside a plant's bounds is
kept as set and flagged on the run's parameters (`runs.parameters_of`).
"""
from __future__ import annotations

from .. import artifacts
from ..models import (EngineInput, EngineParameter, EnginePrecision, EngineRun, EngineThing, Origin, Override,
                      ReplayResult, SFFFlowsheet)
from . import library, runs, simulator
from . import EngineRefused
from .contract import sff_of

# BioSTEAM's distributions, as a run's versions name them.
DISTRIBUTIONS = ("biosteam", "thermosteam", "biorefineries")


class BiosteamEngine:
    name = "biosteam"
    worker = "openferment_core.workers.proforma_worker"
    # What the Proforma worker computes with, which the service never imports.
    heavy = ("biosteam", "thermosteam", "biorefineries", "pisces_sff")

    def __repr__(self) -> str:
        return "BiosteamEngine()"

    @property
    def status(self) -> str:
        return str(simulator.status().get("status") or "cold")

    def version(self) -> dict[str, str]:
        return {d: library._installed(d) for d in DISTRIBUTIONS}

    def things(self) -> list[EngineThing]:
        """Every plant and flowsheet the shelf found, in the configurations it
        built in here, its own first; a run keeps ten significant digits
        (library.DIGITS), within the package test's absolute tolerance."""
        precision = EnginePrecision(rtol=10.0 ** (1 - library.DIGITS), atol=library.ALLCLOSE_ATOL)
        out: list[EngineThing] = []
        for p in library.shelf().plants:
            if p.kind not in ("plant", "flowsheet") or p.error:
                continue
            built = [b.configuration for b in p.builds if b.ok and b.configuration is not None]
            configurations = built if p.builds else list(p.configurations)
            if p.builds and not any(b.ok for b in p.builds):
                continue
            default = p.defaultConfiguration if p.defaultConfiguration in configurations else None
            if default is None and configurations:
                default = configurations[0]
            out.append(EngineThing(id=p.id, title=p.title or p.id, kind=p.kind, configurations=configurations,
                                   defaultConfiguration=default, precision=precision))
        return out

    def parameters(self, thing: str, configuration: str | None) -> list[EngineParameter]:
        """What the package builds the plant with, each default read back from
        it: a `library-default` naming the package and version."""
        found = library.parameters(thing, configuration)
        values = {v.key: v for v in found.values}
        out: list[EngineParameter] = []
        for s in found.specs:
            v = values.get(s.key)
            if v is None:
                continue
            default = v.libraryDefault if v.libraryDefault is not None else v.value
            if default is None:
                continue
            ref = (v.source.id if v.source is not None and v.source.id else None) or f"{library.PACKAGE}@{library._installed(library.PACKAGE)}"
            out.append(EngineParameter(**s.model_dump(exclude={"sourceRule"}), value=default,
                                       origin=Origin(kind="library-default", ref=ref)))
        return out

    def run(self, thing: str, configuration: str | None, inputs: list[EngineInput], by: str) -> EngineRun:
        """One run, kept as a `runs` row by the adapter's own path. A plant
        that takes a configuration, asked with none, runs in the one its thing
        names as its default (the first it built in here). Each value is
        checked against the plant's parameters before any is set (its key,
        once, in the parameter's unit, a number for a number): a value
        refused keeps nothing. A quantity's `low` and `high` reach the plant
        as the Override's, and the library takes them only equal to the value
        (a range is a study's to sample); a quantity carrying a `basis` is
        refused in words."""
        if configuration is None:
            named = next((t for t in self.things() if t.id == thing), None)
            if named is not None and named.configurations:
                configuration = named.defaultConfiguration
        for i in inputs:
            o = i.quantity.origin
            if o is None or o.kind not in ("person-assumption", "model-estimate"):
                raise EngineRefused(f"{i.name}: a value a run sets is a person's assumption or a model's estimate")
            if not (o.at or "").strip():
                raise EngineRefused(f"{i.name}: a value a run sets says when it was set (quantity.origin.at)")
            if i.quantity.basis is not None:
                raise EngineRefused(f"{i.name}: a library plant's parameter is set in its own unit, which says "
                                    f"what it is reckoned on; this quantity also carries the basis {i.quantity.basis!r}")
        if inputs:
            runs.check_inputs(thing, self.parameters(thing, configuration), inputs, bounds=False)
        scope = library.scope(thing, configuration)
        overrides = [Override(scope=scope, key=i.name, value=i.quantity.value, low=i.quantity.low, high=i.quantity.high,
                              by=i.quantity.origin.by or "", at=i.quantity.origin.at, note=i.quantity.origin.note,
                              origin=i.quantity.origin.kind) for i in inputs]
        return runs.run(thing, configuration, overrides, by=by).run

    def replay(self, run: EngineRun) -> ReplayResult:
        if run.artifactId is None:
            raise EngineRefused(f"run {run.id} was refused, so there is nothing to replay")
        return artifacts.replay(run.artifactId)

    def export_sff(self, run: EngineRun) -> SFFFlowsheet | str:
        """The file the run wrote when it was kept (engine/sff.py `export`), as its flowsheet record."""
        return sff_of(run)


ENGINE = BiosteamEngine()
