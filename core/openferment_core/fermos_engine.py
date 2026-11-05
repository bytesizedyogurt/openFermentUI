"""fermOS as the engine `kinetics` (docs/api/engines.md; ADR-015; alpha 2.2 D4).

Registered through the entry-point group like every engine, from
core/pyproject.toml (`kinetics = "openferment_core.fermos_engine:ENGINE"`).
It stands outside engine/, which imports no fermOS module (test_boundaries.py),
and wraps fermOS as it computes:

    things      each model family that simulates (kinetics.FAMILIES, the
                light_v1 socket left out: the contract has no kinetics
                socket), taking no configuration; `forecast`, a band for the
                next run, its configurations the project's kept kinetic fits a
                forecast draws from (logistic_v0); and `vessel`, the vessel a
                batch needs designed on BioSTEAM, its configurations the
                project's kept batch_v1 simulations, the kinetic fits a
                forecast draws from, and the forecasts. `forecast` and
                `vessel` are listed while the project holds one of their
                configurations, read afresh from the current project on
                every ask by the artifact store's tool column
                (artifacts.of_tools), each configuration titled with the
                kind of artifact it names and when the project kept it
                (`configuration_title`); each replays identically (precision
                rtol 0, atol 0).
    parameters  each parameter of the thing's own scope (fermos:family,
                fermos:forecast, fermos:vessel) as an EngineParameter: a
                convention keeps its default with origin `convention` and its
                note, BioSTEAM's own default for a vessel class keeps it with
                origin `library-default`, and every other parameter has no
                default (value and origin null): a run sets it, or fermOS binds
                it from what the project holds (its records, the fit or the
                simulation the configuration names), as a simulation always
                has.
    run         the request the thing names (a SimulationRequest, a forecast
                of the fit, a VesselRequest) with the inputs and `by`, through
                fermos.simulate, fermos.forecast_run or vessel.design, each of
                which keeps the run's row (`keep_simulation`, `keep_forecast`,
                `keep_design`, through engine/runs.compute_kept). The thing
                and its configuration are resolved by reading what they name
                alone (`_thing`): a family is fermOS's own, and a configuration
                is the one artifact it names. A value a
                parameter refuses is refused before anything runs
                (runs.check_inputs for a family and a forecast; a design's
                values by the vessel's own scope, whose keys are its kind's
                and whose choices follow the vessel type the run chooses, so
                a refusal names the scope's own keys). A parameter that waits refuses
                the run in words and keeps nothing; a refusal inside the
                computation is kept as a receipt.
    replay      artifacts.replay on the run's artifact
    export_sff  the run's words: a kinetics family is no plant, so no run of
                this engine writes an SFF file

`worker` is None and `heavy` is (): fermOS integrates with SciPy in the
service's process as it always has (test_workers.py allows SciPy in
kinetics.py and fermos.py), and a vessel design reaches BioSTEAM through the
Proforma worker the simulator starts. `version()` names what the engine as
a whole runs on: numpy and scipy (kinetics.versions()), and biosteam and
thermosteam as their installed metadata records them, the versions a vessel
design's tool version names (vessel.version()). Each run's row names what
its own thing ran on: numpy and scipy for a family's simulation and a
forecast; biosteam and thermosteam, as the design's tool version names
them, and biorefineries, the package its chemicals are read from, for a
vessel design (`_design_versions`).

`placeholder_inputs` and `write_placeholder_inputs` build the values the
conformance check sets on a family (`python -m openferment_core.engine.conform
kinetics --inputs <file>`, the proof's step 10): every parameter with no
default at 1 in its own unit, the product's start value at 0 and a parameter
chosen from words at its first choice, each a person's assumption dated `at`,
or the day the file is written. They are software's placeholders.
"""
from __future__ import annotations

import importlib.metadata
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from pydantic import ValidationError

from . import artifacts, fermos, kinetics, params, projects
from .engine import EngineRefused, runs
from .engine.contract import sff_of
from .models import (Artifact, BasisInput, EngineInput, EngineParameter, EnginePrecision, EngineRun, EngineThing,
                     Origin, ParameterSpec, ParameterValue, ParamScope, Quantity, ReplayResult, SFFFlowsheet,
                     SimulationRequest, VesselRequest)

NAME = "kinetics"
# The things beside the families, by their ids.
FORECAST = "forecast"
VESSEL = "vessel"
# What kind of thing each is, as GET /api/engines lists it.
FAMILY_KIND = "family"
# fermOS replays a computation identically, so a replay holds every output exactly.
EXACT = EnginePrecision(rtol=0.0, atol=0.0)
# The words a run keeps for why it wrote no SFF file, by its thing's kind.
SFF_WORDS = {
    FAMILY_KIND: "a kinetics family is no plant, so the kinetics engine writes no SFF file for its simulation",
    FORECAST: "a forecast draws a band from a kinetic fit and builds no plant, so the kinetics engine writes no SFF "
              "file for it",
    VESSEL: "a vessel design sizes one BioSTEAM unit for a batch and builds no plant, so the kinetics engine writes "
            "no SFF file for it",
}
FORECAST_TITLE = "A band for the next run, drawn from a kept kinetic fit"
VESSEL_TITLE = "The vessel a kept batch simulation or fit needs, designed on BioSTEAM"
# What a kept artifact is as a configuration, by its tool; a simulation names its family.
KEPT_KINDS = {fermos.KINETIC: "a kinetic fit", fermos.FORECAST: "a forecast"}
# The date, the hour and the minute an ISO time begins with.
KEPT_AT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
# The refusals a run of each thing says in words, beside the vessel's (`_refusals`).
REFUSALS = (fermos.SimulationRefused, fermos.FitRefused, params.ParamRefused, params.ScopeUnknown,
            artifacts.ArtifactNotFound, artifacts.ArtifactDamaged)
# What conformance's placeholders rest on, in words.
PLACEHOLDER_NOTE = ("a placeholder the conformance check sets, 1 in the parameter's own unit (0 for the product's "
                    "start value): software's value, measured by no one")


def _vessel() -> Any:
    """fermOS's vessel module, imported on first use, so loading this engine
    at startup imports no vessel: the vessel's tool registers through fermos's
    lazy hook when a design is first computed or replayed (test_review_8r)."""
    from . import vessel

    return vessel


def _refusals() -> tuple[type[BaseException], ...]:
    """Every refusal a run of a thing says in words: REFUSALS and the vessel's."""
    v = _vessel()
    return (*REFUSALS, v.VesselRefused, v.VesselNotFound)


def _installed(dist: str) -> str:
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def _families() -> list[kinetics.Family]:
    """The model families that simulate, in kinetics.FAMILIES' order."""
    return [fam for fam in kinetics.FAMILIES.values() if not fam.socket]


def _logistic(a: Artifact) -> bool:
    """Whether a kept kinetic fit is one a forecast draws from: a logistic_v0
    fit holding parameters (a fit kept before OF-BLD-020 names no model and
    reads as logistic_v0)."""
    o = a.output or {}
    return (o.get("model") or fermos.LOGISTIC) == fermos.LOGISTIC and bool(o.get("params")) and not o.get("reason")


def kept_at(at: str) -> str:
    """When an artifact was kept, as the screens write a time the service
    wrote (src/lib/proforma.ts `stamp`): its date and minute and `UTC`, or
    nothing for a time that names no ISO date and minute."""
    return f"{at[:10]} {at[11:16]} UTC" if KEPT_AT.match(at or "") else ""


def configuration_title(a: Artifact) -> str:
    """What a kept artifact is as a configuration of `forecast` or `vessel`,
    in the words a person reads: its kind (a simulation's names its family),
    and when the project kept it."""
    kind = (f"a {(a.output or {}).get('family') or 'kinetics'} simulation" if a.tool == fermos.SIMULATION
            else KEPT_KINDS.get(a.tool, a.tool))
    at = kept_at(a.createdAt)
    return f"{kind}, kept {at}" if at else kind


def _kept() -> tuple[dict[str, str], dict[str, str]]:
    """The project's kept artifacts the forecast and the vessel take as their
    configuration, newest first, each id with its title
    (`configuration_title`): the kinetic fits a forecast draws from, and the
    batch_v1 simulations, those fits and the forecasts a vessel is designed
    for. Nothing while no project is named."""
    if projects.current_or_none() is None:
        return {}, {}
    fits: dict[str, str] = {}
    designable: dict[str, str] = {}
    for a in artifacts.of_tools(fermos.KINETIC, fermos.FORECAST, fermos.SIMULATION):
        if _forecastable(a):
            fits[a.id] = configuration_title(a)
        if _designable(a):
            designable[a.id] = configuration_title(a)
    return fits, designable


def _forecastable(a: Artifact) -> bool:
    """Whether a kept artifact is a configuration of `forecast`: a kinetic
    fit a forecast draws from."""
    return a.tool == fermos.KINETIC and _logistic(a)


def _designable(a: Artifact) -> bool:
    """Whether a kept artifact is a configuration of `vessel`: a batch_v1
    simulation, a kinetic fit a forecast draws from, or a forecast."""
    if a.tool == fermos.SIMULATION:
        return (a.output or {}).get("family") in _vessel().DESIGNABLE
    return a.tool == fermos.FORECAST or _forecastable(a)


def _parameter(spec: ParameterSpec, v: ParameterValue | None) -> EngineParameter:
    """One parameter of a scope as the contract states it, from its value
    as the scope resolves it with nothing set: a convention's default with its
    note, a vessel class's library default naming BioSTEAM, else no default."""
    held = spec.model_dump()
    if v is not None and v.value is not None and v.origin == "convention":
        note = (v.detail or spec.note or "").strip() or f"{spec.key}'s stated convention"
        return EngineParameter(**held, value=v.value, origin=Origin(kind="convention", note=note))
    if v is not None and v.value is not None and v.origin == "library-default" and v.source and v.source.id:
        return EngineParameter(**held, value=v.value, origin=Origin(kind="library-default", ref=v.source.id,
                                                                     note=v.detail))
    return EngineParameter(**held, value=None, origin=None)


def _scope(thing: str, configuration: str | None) -> ParamScope:
    """The parameter scope a run of the thing binds in, resolved with nothing set."""
    if thing == FORECAST:
        return params.scope(fermos.forecast_scope(str(configuration)))
    if thing == VESSEL:
        return _vessel().scope(str(configuration))
    return params.scope(fermos.family_scope(thing))


def _refused(e: BaseException) -> Exception:
    """A refusal of fermOS's in the contract's terms: kept as a receipt
    (runs.RunRefused, naming it), else said in words with nothing kept."""
    words = str(e).strip().strip("'\"")
    if isinstance(e, artifacts.ArtifactNotFound):
        words = f"the project holds no artifact {words}"
    receipt = getattr(e, "run_id", None)
    return runs.RunRefused(words, receipt) if receipt else EngineRefused(words)


class KineticsEngine:
    """fermOS's families, forecasts and vessel designs behind the engine
    contract (the module's docstring)."""

    name = NAME
    worker: str | None = None
    heavy: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return "KineticsEngine()"

    def version(self) -> dict[str, str]:
        """What the engine as a whole runs on: numpy and scipy, and the
        BioSTEAM a vessel design runs on (the module's docstring)."""
        return {**kinetics.versions(), "biosteam": _installed("biosteam"), "thermosteam": _installed("thermosteam")}

    def things(self) -> list[EngineThing]:
        """Every family that simulates, then the forecast and the vessel
        while the project holds what each takes, each configuration titled
        with the kind of artifact it names and when the project kept it."""
        out = [EngineThing(id=fam.id, title=fam.title, kind=FAMILY_KIND, precision=EXACT) for fam in _families()]
        fits, designable = _kept()
        if fits:
            out.append(EngineThing(id=FORECAST, title=FORECAST_TITLE, kind=FORECAST, configurations=list(fits),
                                   configurationTitles=fits, precision=EXACT))
        if designable:
            out.append(EngineThing(id=VESSEL, title=VESSEL_TITLE, kind=VESSEL, configurations=list(designable),
                                   configurationTitles=designable, precision=EXACT))
        return out

    def _thing(self, thing: str, configuration: str | None) -> tuple[str, str | None]:
        """The thing a request names and the configuration it runs in, as
        runs.thing_of resolves them, read from what they name alone: a
        family is fermOS's own and takes no configuration, and a forecast's
        or a vessel's configuration is the one artifact it names, which must
        be one the thing lists. Anything else is resolved by runs.thing_of,
        whose refusal names what the project holds."""
        thing_id = (thing or "").strip()
        cfg = (configuration or "").strip() or None
        if thing_id in {fam.id for fam in _families()}:
            if cfg is not None:
                raise EngineRefused(f"{thing_id} takes no configuration, and {cfg!r} was named")
            return thing_id, None
        if thing_id in (FORECAST, VESSEL) and cfg is not None and projects.current_or_none() is not None:
            try:
                a = artifacts.get(cfg)
            except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged, ValueError):
                a = None
            if a is not None and (_forecastable(a) if thing_id == FORECAST else _designable(a)):
                return thing_id, cfg
        found, cfg = runs.thing_of(self, thing_id, configuration)
        return found.id, cfg

    def _parameters(self, thing_id: str, cfg: str | None) -> list[EngineParameter]:
        try:
            scope = _scope(thing_id, cfg)
        except _refusals() as e:
            raise _refused(e) from None
        values = {v.key: v for v in scope.values}
        return [_parameter(s, values.get(s.key)) for s in scope.specs]

    def parameters(self, thing: str, configuration: str | None) -> list[EngineParameter]:
        """What a run of the thing takes, each as the thing's scope binds it
        in the current project with nothing set (the module's docstring).
        The thing and its configuration are resolved as a run resolves them
        (`_thing`)."""
        return self._parameters(*self._thing(thing, configuration))

    def run(self, thing: str, configuration: str | None, inputs: list[EngineInput], by: str) -> EngineRun:
        """One run of the thing, kept by fermOS's own function as one runs
        row (the module's docstring); answered as the row."""
        thing_id, cfg = self._thing(thing, configuration)
        inputs = list(inputs)
        try:
            if thing_id != VESSEL and inputs:
                runs.check_inputs(thing_id, self._parameters(thing_id, cfg), inputs, bounds=False)
            if thing_id == FORECAST:
                made = fermos.forecast_run(fit_artifact=cfg, inputs=inputs, by=by).artifactId
            elif thing_id == VESSEL:
                simulated = artifacts.get(str(cfg)).tool == fermos.SIMULATION
                made = _vessel().design(VesselRequest(simulation=cfg if simulated else None,
                                                      fit=None if simulated else cfg, inputs=inputs,
                                                      by=by)).artifactId
            else:
                made = fermos.simulate(SimulationRequest(family=thing_id, inputs=inputs, by=by)).artifactId
        except _refusals() as e:
            raise _refused(e) from None
        except ValidationError as e:
            said = e.errors()[0]["msg"] if e.errors() else str(e)
            raise EngineRefused(f"the {NAME} engine cannot take this request: {said}") from None
        return runs.get(str(made))

    def replay(self, run: EngineRun) -> ReplayResult:
        if run.artifactId is None:
            raise EngineRefused(f"run {run.id} was refused, so there is nothing to replay")
        return artifacts.replay(run.artifactId)

    def export_sff(self, run: EngineRun) -> SFFFlowsheet | str:
        """The words the run kept for why it wrote no SFF file."""
        return sff_of(run)


ENGINE = KineticsEngine()


# ── keeping fermOS's computations as the engine's runs ─────────────────


def keep_simulation(family: str, basis: Sequence[BasisInput], *, by: str = "",
                    records_by_id: Mapping[str, Any] | None = None) -> Artifact:
    """A `fermos.simulation` computed and kept as a run of `family`, no
    configuration (fermos.simulate); its row names numpy and scipy."""
    return runs.compute_kept(ENGINE, family, None, tool=fermos.SIMULATION, basis=basis, by=by,
                             refusal=fermos.SimulationRefused, sff_refused=SFF_WORDS[FAMILY_KIND],
                             records_by_id=records_by_id, versions=kinetics.versions())


def keep_forecast(fit_id: str, basis: Sequence[BasisInput], *, by: str = "", seed: int | None = None) -> Artifact:
    """A kept fit's `growth_forecast` computed and kept as a run of
    `forecast`, its configuration the fit (fermos.forecast_run); its row
    names numpy and scipy."""
    return runs.compute_kept(ENGINE, FORECAST, fit_id, tool=fermos.FORECAST, basis=basis, by=by,
                             refusal=fermos.FitRefused, sff_refused=SFF_WORDS[FORECAST], seed=seed,
                             versions=kinetics.versions())


def _design_versions(basis: Sequence[BasisInput]) -> dict[str, str]:
    """What a vessel design ran on, as its own basis names it: biosteam and
    thermosteam as its tool version (vessel.version()) names them, and
    biorefineries, the package its chemicals are read from (the `chemicals`
    input's source, `biorefineries@<version>`)."""
    out: dict[str, str] = {}
    for part in _vessel().version().split(" · ")[1:]:
        name, _, version = part.partition(" ")
        if name and version:
            out[name] = version
    chemicals = next((i for i in basis if i.name == "chemicals"), None)
    ref = (chemicals.source.id or "") if chemicals is not None else ""
    if "@" in ref:
        package, _, version = ref.partition("@")
        out[package] = version
    return out


def keep_design(source_id: str, basis: Sequence[BasisInput], *, by: str = "") -> Artifact:
    """A `fermos.vessel` design computed and kept as a run of `vessel`, its
    configuration the simulation or fit it is designed for (vessel.design);
    its row names what the design ran on (`_design_versions`)."""
    v = _vessel()
    basis = list(basis)
    return runs.compute_kept(ENGINE, VESSEL, source_id, tool=v.TOOL, basis=basis, by=by,
                             refusal=v.VesselRefused, sff_refused=SFF_WORDS[VESSEL], records_by_id={},
                             versions=_design_versions(basis))


# ── conformance's placeholders (engine/conform.py --inputs) ────────────


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def placeholder_inputs(thing: str | None = None, *, by: str, at: str | None = None) -> list[EngineInput]:
    """The values the conformance check sets on a family (the first that
    simulates when none is named): each parameter with no default (a spec
    stating no convention) at 1 in its own unit, the product's start value at
    0, a parameter chosen from words at its first choice; each a person's
    assumption by `by`, dated `at` (the day they are built when none is
    given). Read from the family's own specs, with no database, as a
    project holding nothing binds them."""
    fam = kinetics.family(thing or _families()[0].id)
    if fam.socket:
        raise EngineRefused(fam.refusal())
    product = {k for k, state in kinetics.START_STATE.items() if state == fam.product_state()}
    day = at or _today()
    out: list[EngineInput] = []
    for spec in fam.specs():
        if spec.convention is not None and "convention" in spec.sourceRule:
            continue
        value: float | str = spec.choices[0] if spec.choices else (0.0 if spec.key in product else 1.0)
        out.append(EngineInput(name=spec.key, quantity=Quantity(value=value, unit=spec.unit, origin=Origin(
            kind="person-assumption", by=by, at=day, note=PLACEHOLDER_NOTE))))
    return out


def write_placeholder_inputs(path: str | Path, thing: str | None = None, *, by: str, at: str | None = None) -> Path:
    """`placeholder_inputs` written as the JSON list `conform --inputs` reads."""
    out = Path(path)
    out.write_text(json.dumps([i.model_dump(mode="json", exclude_none=True)
                               for i in placeholder_inputs(thing, by=by, at=at)], ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return out
