"""BioSTEAM as an engine (docs/api/engines.md; ADR-004, ADR-015).

The first engine, registered through the entry-point group like any other
(core/pyproject.toml). Its things are of two kinds:

    library plants      the plants and flowsheets the library shelf found
                        buildable here (`library.shelf`), each in the
                        configurations it built in here: its parameters what
                        the package builds it with (`library.parameters`,
                        every default a `library-default` naming the package
                        it was read from), a run `runs.run`, the Proforma
                        worker building the plant fresh, every number and test
                        as before (the A→B→A gate, the replay precision, the
                        package-test values of ADR-013), kept to ten
                        significant digits within the package test's
                        absolute tolerance
    provided things     things of BioSTEAM's a module above the engine
                        package provides (`Provider`), registering its
                        provider here as it is imported (`provide`), so the
                        engine package imports none of those modules
                        (core/tests/test_boundaries.py): each thing listed,
                        its parameters read and its run made and kept by its
                        provider. Proforma provides the shelf's scenario
                        flowsheets (proforma.py, kind `scenario`): a
                        flowsheet's parameters the inputs a scenario of it
                        binds, as GET /api/proforma/bind binds one with no
                        scenario, and a run the run of an unsaved scenario
                        of it named by the flowsheet's own id, one
                        `proforma.run` row of this engine with its SFF file.
                        Every process that serves the engine imports
                        Proforma: the service's app through its tools, and
                        conformance, which reads an engine as the app holds
                        it (engine/conform.py)

`run_plant` is the one path a library plant's run takes from every door:
this engine's run, POST /api/library/{plant}/run, a study's scenario and the
engine tools. A plant that takes a configuration, asked with none, runs in
the default its thing names (the shelf's own, else the first configuration
it built in here), and its parameters are read in that default at every
door (`default_configuration`). A value a run sets is checked against the
plant's parameters (its key, set once, in the parameter's unit, a number
for a number, `runs.check_inputs`) before the plant is built, and converted
by the one converter, basis.override_of, into the `Override` of the plant's
scope the library takes, its origin the person or the model that set it and
the day its origin names. A value outside a plant's bounds is kept as set
and flagged on the run's parameters (`runs.parameters_of`). A thing neither
on the library's shelf nor provided is refused in words naming the things
the engine runs, and keeps nothing.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .. import artifacts
from ..basis import InputRefused, override_of
from ..models import (EngineInput, EngineParameter, EnginePrecision, EngineRun, EngineThing, Origin, ReplayResult,
                      RunReport, SFFFlowsheet)
from . import library, runs, simulator
from . import EngineRefused
from .contract import sff_of

NAME = "biosteam"
# BioSTEAM's distributions, as a run's versions name them.
DISTRIBUTIONS = ("biosteam", "thermosteam", "biorefineries")


@dataclass(frozen=True)
class Provider:
    """What a module above the engine package gives the engine (`provide`):
    its things as the engine lists them (`things`), whether a thing is one of
    them (`holds`), a thing's parameters with each default's origin
    (`parameters`), and a run of one (`run`), which the module keeps as one
    runs row of this engine and answers with the row's id. `refusal` is the
    exception the module refuses in words with: one that carries `run_id`
    names the receipt the module kept."""

    name: str
    things: Callable[[], list[EngineThing]]
    holds: Callable[[str], bool]
    parameters: Callable[[str, str | None], list[EngineParameter]]
    run: Callable[[str, str | None, list[EngineInput], str], str]
    refusal: type[Exception]


# The providers registered here, by name, in the order they first registered.
_PROVIDERS: dict[str, Provider] = {}


def provide(provider: Provider) -> None:
    """Register a module's provider of things (the module's docstring); a
    provider registered again under its name stands in place of the one
    before."""
    _PROVIDERS[provider.name] = provider


def provided(thing: str) -> Provider | None:
    """The provider that holds a thing; None for an id on the library's
    shelf, whose plant stands, and for an id no provider holds."""
    thing_id = (thing or "").strip()
    if any(p.id == thing_id for p in library.shelf().plants):
        return None
    return next((p for p in _PROVIDERS.values() if p.holds(thing_id)), None)


def unknown(thing: str) -> str | None:
    """The words refusing a thing neither on the library's shelf nor
    provided, naming every thing the engine runs, as `runs.thing_of` words
    it for a contract engine; None for a thing the engine knows. One the
    shelf holds that runs nothing (a subsystem) is the library's to refuse,
    in its own words."""
    thing_id = (thing or "").strip()
    if any(p.id == thing_id for p in library.shelf().plants) or provided(thing_id) is not None:
        return None
    return f"the {NAME} engine runs no thing {thing_id!r}; it runs {', '.join(t.id for t in ENGINE.things()) or 'nothing'}"


def _library_things() -> list[EngineThing]:
    """Every plant and flowsheet the library shelf found, in the
    configurations it built in here; a run keeps ten significant digits
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


def _library_parameters(thing: str, configuration: str | None) -> list[EngineParameter]:
    """What the package builds a library plant with, each default read back
    from it: a `library-default` naming the package and version."""
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


def default_configuration(thing: str, configuration: str | None) -> str | None:
    """The configuration a library plant's run runs in: the one named, else,
    for a plant that takes configurations, the default its thing names (the
    shelf's own, else the first it built in here); None for a plant that
    takes none, and for a plant the shelf lacks (its run says so)."""
    cfg = (configuration or "").strip() or None
    if cfg is not None:
        return cfg
    named = next((t for t in _library_things() if t.id == (thing or "").strip()), None)
    return named.defaultConfiguration if named is not None and named.configurations else None


def run_plant(thing: str, configuration: str | None, inputs: Sequence[EngineInput] = (), *, by: str = "",
              scenario_id: str | None = None) -> RunReport:
    """One run of a library plant or a composed flowsheet, kept as its runs
    row by `runs.run` and answered as its report: the one path every door
    takes (the module's docstring). The configuration is `default_configuration`'s.
    Each value is checked before the plant is built: a quantity carrying a
    basis is refused before the plant's parameters are read; then its key,
    set once, in the parameter's unit, a number for a number
    (`runs.check_inputs`, bounds False: a value outside them is kept and
    flagged); then basis.override_of converts it into the Override of the
    plant's scope (library.scope), the low and high of a quantity reaching
    the plant as the Override's, which the library takes only equal to the
    value (a range is a study's to sample). A value refused keeps nothing
    (EngineRefused). A run a study's scenario asks for names it
    (`scenario_id`)."""
    cfg = default_configuration(thing, configuration)
    inputs = list(inputs)
    for i in inputs:
        if i.quantity.basis is not None:
            raise EngineRefused(f"{i.name}: a library plant's parameter is set in its own unit, which says what it "
                                f"is reckoned on; this quantity also carries the basis {i.quantity.basis!r}")
    if not inputs:
        return runs.run(thing, cfg, [], by=by, scenario_id=scenario_id)
    params = _library_parameters(thing, cfg)
    runs.check_inputs(thing, params, inputs, bounds=False)
    units = {p.key: p.unit for p in params}
    scope = library.scope(thing, cfg)
    try:
        overrides = [override_of(scope, i, units[i.name]) for i in inputs]
    except InputRefused as e:
        raise EngineRefused(str(e)) from None
    return runs.run(thing, cfg, overrides, by=by, scenario_id=scenario_id)


def _refused(e: BaseException) -> Exception:
    """A provider's refusal in the contract's terms: kept as a receipt
    (runs.RunRefused, naming it), else said in words with nothing kept. A
    KeyError's words are its key's repr, read without its quotes; any
    other's are its own, whole."""
    words = str(e).strip()
    if isinstance(e, KeyError):
        words = words.strip("'\"")
    receipt = getattr(e, "run_id", None)
    return runs.RunRefused(words, receipt) if receipt else EngineRefused(words)


class BiosteamEngine:
    name = NAME
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
        """The library's plants and flowsheets, in the configurations each
        built in here, then each provider's things in the order the
        providers registered, an id the library holds left to the library
        (the module's docstring)."""
        out = _library_things()
        held = {t.id for t in out}
        for provider in _PROVIDERS.values():
            for th in provider.things():
                if th.id not in held:
                    out.append(th)
                    held.add(th.id)
        return out

    def parameters(self, thing: str, configuration: str | None) -> list[EngineParameter]:
        """What a run of the thing takes. A library plant's are what the
        package builds it with, read in the configuration its run runs in
        (`default_configuration`), each default read back from it: a
        `library-default` naming the package and version. A provided thing's
        are its provider's, each default with its origin, and none where
        nothing binds it."""
        provider = provided(thing)
        if provider is not None:
            try:
                return provider.parameters(thing.strip(), configuration)
            except provider.refusal as e:
                raise _refused(e) from None
        said = unknown(thing)
        if said:
            raise EngineRefused(said)
        return _library_parameters(thing, default_configuration(thing, configuration))

    def run(self, thing: str, configuration: str | None, inputs: list[EngineInput], by: str) -> EngineRun:
        """One run, kept as one `runs` row: a library plant's by `run_plant`,
        a provided thing's by its provider, whose refusal before it computes
        keeps nothing and whose refusal inside the computation is kept as a
        receipt; answered as the row."""
        provider = provided(thing)
        if provider is None:
            said = unknown(thing)
            if said:
                raise EngineRefused(said)
            return run_plant(thing, configuration, inputs, by=by).run
        try:
            run_id = provider.run(thing.strip(), configuration, list(inputs), by)
        except provider.refusal as e:
            raise _refused(e) from None
        return runs.get(run_id)

    def unready(self, thing: str, inputs: list[EngineInput]) -> str | None:
        """Why a thing cannot run with `inputs` as it stands, in words, or
        None: a provided thing whose parameters give no default to one the
        inputs leave unset waits for it, read in the first configuration it
        runs in (conformance refuses to check it so, engine/conform.py); a
        library plant runs on its package's own defaults. Runs nothing and
        keeps nothing."""
        if provided(thing) is None:
            return None
        thing_id = thing.strip()
        cfg = next((t.configurations[0] for t in self.things() if t.id == thing_id and t.configurations), None)
        try:
            params = self.parameters(thing_id, cfg)
        except EngineRefused as e:
            return str(e)
        given = {i.name for i in inputs}
        waiting = sorted(p.key for p in params if p.value is None and p.key not in given)
        if not waiting:
            return None
        n = len(waiting)
        return (f"{thing_id} waits for {n} value{'s' if n != 1 else ''} its parameters give no default, which a run "
                f"sets: {', '.join(waiting)}")

    def replay(self, run: EngineRun) -> ReplayResult:
        if run.artifactId is None:
            raise EngineRefused(f"run {run.id} was refused, so there is nothing to replay")
        return artifacts.replay(run.artifactId)

    def export_sff(self, run: EngineRun) -> SFFFlowsheet | str:
        """The file the run wrote when it was kept (engine/sff.py `export`), as its flowsheet record."""
        return sff_of(run)


ENGINE = BiosteamEngine()
