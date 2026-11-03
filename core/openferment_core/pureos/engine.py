"""pureOS's trains as the engine `train` (docs/api/engines.md; ADR-015; alpha
2.2 D5).

Registered through the entry-point group like every engine, from
core/pyproject.toml (`train = "openferment_core.pureos.engine:ENGINE"`). It
stands beside pureOS, which the engine package imports none of
(test_boundaries.py), and wraps a train as pureOS runs it:

    things      the current project's trains, read afresh on every ask and
                never kept: each train pureOS's Builder saved (the project's
                `trains` rows of kind `made`, project_state.py) and each a
                model built (`pureos.kept.listed`), its id the train's, its
                title the train's name; none takes a configuration, and each
                replays exactly (precision rtol 0, atol 0): a train run
                keeps every digit BioSTEAM gives (`train_spec.replay_precision`)
    parameters  each place's values as a run of the train resolves them
                (`train_spec.resolved`): the inlet's, then every unit's in
                order, flattened to `inlet.<key>` and `<unit id>.<key>`, each
                default with the origin its resolution names: the class's own
                (a `library-default` naming BioSTEAM), a shelf flowsheet's own
                unit (a `library-default` naming its package), thermosteam's
                Stream default for the inlet's T and P (a `library-default`
                naming thermosteam), a convention, the records that bound it
                (a `record` naming them), the inlet's run, simulation or
                vessel (an `artifact` naming it), or a value a person typed
                into the train (a `person-assumption` naming them and the
                day). A value that waits has no default, and a run sets it. A
                value the train fills itself when a run leaves it unset (one
                the unit's class decides at run time, a component the inlet
                does not carry, a split left to the class) has none either,
                and its `note` says so and why (`FILLS_ITSELF`)
    run         the train the thing names, its inputs checked and converted
                at pureOS's own door (`train_spec.run_train`, through
                `converted`): every refusal at once, by place, in the words
                `POST /api/pureos/train/run` answers with, and nothing kept;
                then the run is kept by `train_spec.run_train`
                (`keep_train_run`, engine/runs.compute_kept): one `runs` row
                created by `by`, its SFF file the record `run-<id>` or the
                toolkit's words for why it has none. A value that waits
                refuses the run in words and keeps nothing; the worker's
                refusal of a train it cannot build or run (BioSTEAM's words)
                is kept as a receipt
    replay      artifacts.replay on the run's artifact
    export_sff  the file the run wrote, or its words for why none was

`worker` is the Proforma worker, where the train is built and run, and
`heavy` names what that worker computes with, as the biosteam engine
declares it: importing this module imports neither. `version()` names the
simulator's distributions as their installed metadata records them
(biosteam, thermosteam, biorefineries) and the train run's own version
(`train run`, train_spec.VERSION_WORDS), and starts no worker; each run's
row names the distributions its own basis names, the versions the worker
ran.

Every thing is a project's own, so `things_are` says what they are, and
conformance runs in a project that holds one (`python -m
openferment_core.engine.conform train --project <id>`, a project of a
development database: the checks refuse the production one).
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Sequence

from pydantic import ValidationError

from .. import artifacts, projects
from ..engine import EngineRefused, library, runs, simulator
from ..engine.biosteam import DISTRIBUTIONS, BiosteamEngine
from ..engine.contract import sff_of
from ..models import (THING_ID, Artifact, BasisInput, EngineInput, EngineParameter, EnginePrecision, EngineRun,
                      EngineThing, Origin, ParameterSpec, ParameterValue, ReplayResult, SFFFlowsheet, TrainSpec)
from . import catalogue, train_spec

NAME = "train"
# What a thing is, as GET /api/engines lists it: a train pureOS's Builder
# saved (the trains table's kind `made`), or one a model built (`kept`).
MADE, KEPT = "made", "kept"
# What the engine's things are, in words: every one is a project's own, so
# conformance runs in a named project (engine/conform.py `--project`).
THINGS_ARE = "a project's trains, each saved in pureOS's Builder or built by a model"
# The words a parameter's note gains when the train fills it itself as a run
# leaves it unset, the resolution's reason beside them.
FILLS_ITSELF = "A run may leave it unset, and the train then fills it itself"


def precision() -> EnginePrecision:
    """The precision every train replays to, exact (`train_spec.replay_precision`)."""
    rtol, atol = train_spec.replay_precision()
    return EnginePrecision(rtol=rtol, atol=atol)


def _trains() -> list[tuple[str, TrainSpec, str]]:
    """The current project's trains, read afresh, each (kind, train, title):
    the trains pureOS's Builder saved, in the order the project keeps them,
    then those a model built, the most recently changed first. A row whose
    train does not read as a train, or whose id is no thing's (THING_ID), is
    no thing a run can name. Nothing while no project is named."""
    from .. import project_state
    from . import kept

    if projects.current_or_none() is None:
        return []
    out: list[tuple[str, TrainSpec, str]] = []
    for row in project_state.kept("trains"):
        try:
            spec = TrainSpec.model_validate(row.get("train") if isinstance(row, dict) else None)
        except ValidationError:
            continue
        out.append((MADE, spec, spec.name))
    for k in kept.listed():
        out.append((KEPT, k.spec, f"{k.spec.name}, built by {k.madeBy}"))
    return [t for t in out if re.match(THING_ID, t[1].id)]


def _origin(v: ParameterValue, spec: ParameterSpec) -> Origin | None:
    """Where a resolved value comes from, as the contract states a default's
    origin; None for a value that waits or that the class reads for itself."""
    from ..basis import origin_of

    if v.value is None or v.source is None or v.origin in ("waiting", "not-read"):
        return None
    if v.origin == "library-default":
        return Origin(kind="library-default", ref=v.source.id or None, note=v.detail)
    if v.origin == "convention":
        return Origin(kind="convention", note=(v.detail or spec.note or "").strip() or f"{spec.key}'s stated convention")
    if v.origin == "record":
        return Origin(kind="record", ref=", ".join(v.recordIds) or None, note=v.detail)
    if v.origin in ("artifact", "simulation"):
        return Origin(kind="artifact", ref=v.source.id or None, note=v.detail)
    if v.origin == "assumption":
        return origin_of(v.source)
    return None


def _parameter(place: str, spec: ParameterSpec, v: ParameterValue) -> EngineParameter:
    """One value of a place as the contract states a parameter, keyed
    `<place>.<key>`. A value with no default that the train fills itself when
    a run leaves it unset (any but one that waits) says so in its `note`,
    with the resolution's reason."""
    origin = _origin(v, spec)
    held = {**spec.model_dump(), "key": f"{place}{catalogue.SEP}{spec.key}"}
    if origin is None and v.origin != "waiting":
        why = (v.detail or "").strip().rstrip(".") or "the unit's class decides it at run time"
        held["note"] = " ".join(x for x in ((spec.note or "").strip(), f"{FILLS_ITSELF} ({why}).") if x)
    return EngineParameter(**held, value=v.value if origin is not None else None, origin=origin)


def _refused(e: BaseException) -> Exception:
    """pureOS's refusal in the contract's terms: kept as a receipt
    (runs.RunRefused, naming it), else said in words with nothing kept."""
    words = str(e).strip().strip("'\"")
    if isinstance(e, artifacts.ArtifactNotFound):
        words = f"the project holds no artifact {words}"
    receipt = getattr(e, "run_id", None)
    return runs.RunRefused(words, receipt) if receipt else EngineRefused(words)


# The refusals a train's run or read says in words.
REFUSALS = (train_spec.TrainRefused, artifacts.ArtifactNotFound, artifacts.ArtifactDamaged)


class TrainEngine:
    """pureOS's trains behind the engine contract (the module's docstring)."""

    name = NAME
    worker: str | None = BiosteamEngine.worker
    heavy: tuple[str, ...] = BiosteamEngine.heavy
    things_are = THINGS_ARE

    def __repr__(self) -> str:
        return "TrainEngine()"

    @property
    def status(self) -> str:
        return str(simulator.status().get("status") or "cold")

    def version(self) -> dict[str, str]:
        """The simulator's distributions, as their installed metadata records
        them, and the train run's own version (the module's docstring)."""
        stem, _, number = train_spec.VERSION_WORDS.rpartition(" ")
        return {**{d: library._installed(d) for d in DISTRIBUTIONS}, stem: number}

    def things(self) -> list[EngineThing]:
        """The current project's trains, read afresh (the module's docstring)."""
        exact = precision()
        return [EngineThing(id=spec.id, title=title, kind=kind, precision=exact) for kind, spec, title in _trains()]

    def _train(self, thing: str, configuration: str | None) -> TrainSpec:
        """The train a request names, read from the project as it stands: one
        the project holds, and no configuration, which a train takes none of."""
        thing_id = (thing or "").strip()
        held = {spec.id: spec for _, spec, _ in _trains()}
        if thing_id not in held:
            raise EngineRefused(f"the {NAME} engine runs no thing {thing_id!r}; it runs "
                                f"{', '.join(held) or 'nothing: the project holds no train'}")
        cfg = (configuration or "").strip() or None
        if cfg is not None:
            raise EngineRefused(f"{thing_id} takes no configuration, and {cfg!r} was named")
        return held[thing_id]

    def _parameters(self, spec: TrainSpec) -> list[EngineParameter]:
        try:
            places = train_spec.resolved(spec)
        except REFUSALS as e:
            raise _refused(e) from None
        return [_parameter(place, s, v) for place, specs, values in places for s, v in zip(specs, values)]

    def parameters(self, thing: str, configuration: str | None) -> list[EngineParameter]:
        """Each place's values as a run of the train resolves them (the module's docstring)."""
        return self._parameters(self._train(thing, configuration))

    def run(self, thing: str, configuration: str | None, inputs: list[EngineInput], by: str) -> EngineRun:
        """One run of the train, its inputs checked at pureOS's own door and
        kept by `train_spec.run_train` as one runs row (the module's
        docstring); answered as the row."""
        spec = self._train(thing, configuration)
        try:
            made = train_spec.run_train(spec, list(inputs), by)
        except REFUSALS as e:
            raise _refused(e) from None
        return runs.get(made.artifactId)

    def replay(self, run: EngineRun) -> ReplayResult:
        if run.artifactId is None:
            raise EngineRefused(f"run {run.id} was refused, so there is nothing to replay")
        return artifacts.replay(run.artifactId)

    def export_sff(self, run: EngineRun) -> SFFFlowsheet | str:
        """The SFF file the run wrote when it was kept, as its flowsheet record, or its words for why none was."""
        return sff_of(run)


ENGINE = TrainEngine()


# ── keeping a train's run as the engine's ───────────────────────────────


def _versions(basis: Iterable[BasisInput]) -> dict[str, str]:
    """What a train run ran on, as its own basis names it: the BioSTEAM,
    thermosteam and biorefineries versions the worker ran."""
    return {i.name: str(i.value) for i in basis if i.name in DISTRIBUTIONS}


def keep_train_run(spec: TrainSpec, basis: Sequence[BasisInput], *, by: str = "",
                   records_by_id: Any = None) -> Artifact:
    """A train's `pureos.train_run` computed and kept as a run of `spec.id`,
    no configuration (train_spec.run_train): one `runs` row of the engine
    `train` created by `by`, its SFF file asked of the Proforma worker from
    the run's own basis (`train_spec.export_sff`) and kept as the record, or
    the toolkit's words kept as `sffRefused`; the worker's refusal of the run
    kept as a receipt and raised as `train_spec.TrainRefused` with its id as
    `run_id`; its row names the versions its basis names."""
    basis = list(basis)
    return runs.compute_kept(ENGINE, spec.id, None, tool=train_spec.TRAIN_RUN, basis=basis, by=by,
                             refusal=train_spec.TrainRefused, records_by_id=records_by_id,
                             write_sff=lambda art, project_id, who: train_spec.export_sff(art, project_id=project_id,
                                                                                         by=who),
                             versions=_versions(basis))
