"""Stage C's pins (alpha 2.2, D1): each computation stage C carries, held to
its artifact id and its output hash, two literals captured before stage C
changed anything.

Every computation here is built the way the existing tests build theirs, on
their fixtures and stand-ins, and types no value of its own: fermOS's
batch_v1, fedbatch_v1 and chemostat_v1 simulations on test_fermos' and
test_kinetics' stand-ins; a growth forecast and the kinetic fit it rests on,
on test_fermos' synthetic batch; a vessel design on test_vessel's stand-in
worker; a pureOS train run on test_train's TrainWorker; a Proforma run on the
closed-form stand-in evaluator (standins.py); library runs on test_runs'
stand-in worker and on test_comparisons' priced one; a comparison of two
library runs on each; and a run of the contract's sample engine
(engine/sample.py).

The literals were captured at commit ed33c02, before step C.1 changed a line
of code. They must survive stage C bit for bit: the owner's gate. A change
that moves one stops there and says why it moved, and the literal stays as
captured.

What each pin computes through, owned by other test files: test_fermos'
`typed_for`, `batch`, `T`, `SD`, `BY`, `STANDIN_TYPED`, `CHEMO` and
`STANDIN_CHEMOSTAT_TYPED`; test_kinetics' `STANDIN_FED`, `STANDIN_FED_START`
and `STANDIN_FED_RUN_H`; test_vessel's `StandInWorker`, `keep`, `override`,
`standin_simulation` and `AEROBIC_ID`; test_train's `TrainWorker`, `spec_of`,
`AT` and `STANDIN`; standins' `_standin_call` and `_standin_yeast_records`;
test_proforma_runs' `ASSUMED`, `ETHANOL` and `MADE_HERE`; test_runs'
`StandIn`; test_comparisons' `PricedStandIn`; test_library's `over`; and
test_engines' `given` with its `DAY`. Each keeps its outputs through stage C:
an edit to one is an edit to these pins, reported under D1, and a moved pin
is read against them first.

D1's amendment at C.1, the dispatch. numpy and OpenBLAS choose their code
paths by the host's CPU, and least_squares, a pseudo-inverse, an SVD, a
multivariate normal draw and LSODA's linear algebra each round on the path
taken. The dispatch of the host the literals were first captured on (an
AVX-512 Xeon: numpy's X86_V4 loops, OpenBLAS's SkylakeX kernels) and an AVX2
host's (numpy's X86_V3 loops, OpenBLAS's Haswell or Zen kernels) give the
chemostat_v1 simulation, the kinetic fit and both forecasts different output
hashes, and every id the same, as an id hashes the basis alone. So every
output hash is computed under one fixed dispatch, FIXED_DISPATCH: OpenBLAS's
Haswell kernels on one thread and numpy's loops of X86_V3, the dispatch an
AVX2 host takes of itself and any x86-64 host with AVX2 and FMA3 can run.
Twelve literals read as first captured; the four above were captured again,
from ed33c02's code under the fixed dispatch (docs/PROGRESS.md, Departures).
Each test checks its ids in this process; a process of its own started
under the fixed dispatch checks every id and output hash
(`test_every_output_hash_holds_under_the_fixed_dispatch`). A host that is
not x86-64, or lacks AVX2 or FMA3, skips these pins and says why: every
literal is x86-64's, and the fit's id itself rests on readings numpy
computes in the test (test_fermos' `batch`).

D1's amendment at C.2 (the forecast): fermOS's forecast takes each start
value and its length as a typed quantity with its origin, and its basis then
writes the day a value was set, as every other typed value's basis does. The
forecast with a changed start value therefore gains a new id at C.2, and its
output hash holds; the pin then names both ids and that decision. The
forecast that changes nothing keeps its id.

One pin was captured at C.1 itself: a comparison of two runs of the sample
engine. From C.1 on, a comparison that holds a run of an engine beside
BioSTEAM's library reads its outputs.values, at the version `study
comparison 2` (D3); on the same basis at `study comparison 1`, its id is the
one ed33c02 gave it (ED33C02_SAMPLE_COMPARISON).

The basis of a Proforma run and of a train run names whether the host draws
the flowsheet's diagram (OF-BLD-019 §2.R: `proforma.DIAGRAM_DRAWN` or
`DIAGRAM_NOT_DRAWN`), so every pin here is made as on a host without
Graphviz's dot.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import standins
from openferment_core import artifacts, evidence_pool, fermos, intake, proforma, pureos, vessel
from openferment_core.engine import library, runs, simulator
from openferment_core.engine.sample import SAMPLE
from openferment_core.models import ComparisonCreate, Override, ProformaRunRequest, SimulationRequest, VesselRequest
from openferment_core.pureos import catalogue, train_spec
from openferment_core.studies import comparisons
from test_comparisons import PricedStandIn
from test_engines import given
from test_fermos import BY, CHEMO, SD, STANDIN_CHEMOSTAT_TYPED, STANDIN_TYPED, T, batch, typed_for
from test_kinetics import STANDIN_FED, STANDIN_FED_RUN_H, STANDIN_FED_START
from test_library import over
from test_proforma_runs import ASSUMED, ETHANOL, MADE_HERE
from test_runs import StandIn
from test_train import AT as TRAIN_AT
from test_train import STANDIN as TRAIN_STANDIN
from test_train import TrainWorker, spec_of
from test_vessel import AEROBIC_ID, keep, override, standin_simulation
from test_vessel import StandInWorker as VesselWorker

BATCH = "batch_v1"
FED = "fedbatch_v1"
# test_kinetics' constant feed, its start and its run length, as fermOS's
# panel takes them: each by its key, a start value by the state it fills.
FED_TYPED = {**{k: v for k, v in STANDIN_FED["constant"].items() if v is not None},
             **{key: STANDIN_FED_START[state] for key, state in (("x0", "X"), ("s0", "S"), ("p0", "P"), ("v0", "V"))},
             "t_end": STANDIN_FED_RUN_H["constant"]}
EMPTY = SimpleNamespace(records=[], records_by_id={})

# The dispatch every output hash is computed under (D1's amendment at C.1),
# read by numpy and OpenBLAS as a process starts: OpenBLAS's Haswell kernels
# on one thread, and numpy's loops above X86_V3 turned off (numpy turns off
# each group named, and a group the host lacks is off already).
FIXED_DISPATCH = {"OPENBLAS_CORETYPE": "Haswell", "OPENBLAS_NUM_THREADS": "1",
                  "NPY_DISABLE_CPU_FEATURES": "X86_V4 AVX512_ICL AVX512_SPR"}
# How long the process under the fixed dispatch may take: its own database and the pins, a few seconds here.
FIXED_DISPATCH_TIMEOUT_S = 600

# Each pin: what was computed, its artifact id and its output hash, at ed33c02
# under the fixed dispatch.
PINS: dict[str, tuple[str, str]] = {
    "fermos.simulation batch_v1": (
        "4215f23b6ea7d099", "842793dec0ae118d0329251c08fd5e61de590cc0873edad32dcbcea064a511bc"),
    "fermos.simulation fedbatch_v1": (
        "ddbde00e8c22fb07", "e031b39eaa9fc638d2a84c6f23cbf4fd74f0e6dcad7cad2f3f0dd3df495ef843"),
    # Captured again under the fixed dispatch (D1's amendment at C.1), as are the next three.
    "fermos.simulation chemostat_v1": (
        "a15b3917c47fa272", "ea77840641c03bb5d266fb996ab7b43411928d48bd52c03212f329573a679c5b"),
    "kinetic_fit": (
        "da66a3d1c22027a6", "905045fddf738d41c8c438af0ad7da999b53b1eff7f1cfda4115e22ecadf283f"),
    "growth_forecast": (
        "9e26015a728860bd", "5cb631e5e0ae170e9b15346173a974888a3319f4053ec63cda54846bc44de93e"),
    # Under D1's amendment at C.2: this id moves there, and the output hash holds.
    "growth_forecast with a changed start": (
        "611bd4b34eed98fd", "859f488203c5439f5b4c943a186ed684742703fdd4e9923b7659114d7c254d35"),
    "fermos.vessel": (
        "748146b8afbc21a1", "892d4c0bcbb7cf5d4d855fce3d1b3ff07f75ec0cd1745ccd64e0ae0c1e6fd35a"),
    "pureos.train_run": (
        "d8f5d3f56d34aff9", "9053c28f6bc8695044bc100184e800fcae3dbade808427232fbae4e50364f095"),
    "proforma.run": (
        "7fd5c088e90f6689", "865d88ab811e3553dfff6549983fca62a2cf1cf01410b20fa5599493646f0fcf"),
    "library.run": (
        "dfb8df271dc2f58d", "16534ffcf199ba8a7532b52c8fd28961fb997ee9bd7f0e5173950bb9ecafee10"),
    "library.run on its own defaults": (
        "0670677d562f3d03", "a9ac29a27fd904bba00ee1ec2705b73fd99f2dcf19066d89fc6d8810f0f53b88"),
    "study.comparison": (
        "865207a4ef20c0e2", "92a0a33b23360901b7220b81c6e37d005a1242bc62a3d3e84628d5f8d57c5771"),
    "library.run priced on its own defaults": (
        "0670677d562f3d03", "386b6f34d4c8edac74f7f20820379bd43cb2be1096ae9ea213ba613f305b57f8"),
    "library.run priced with a person's price": (
        "dfb8df271dc2f58d", "c2ec2b99a4b28e2121b49a7a5f0eb17def53bbfbabaf4d2ce25f4e86ca35f2d6"),
    "study.comparison of priced runs": (
        "865207a4ef20c0e2", "4dc4045b4dbdee26a1cab55402a264d581c2456d89f1588373f9f9c904e5728f"),
    "engine.sample": (
        "e969303b7d29de5e", "45093e0dd24d5d28a243b35dd7db86913fc8cd5821d8cead6c7d138d7d5d78da"),
    # Captured at C.1 (D3): the comparison's version is `study comparison 2`.
    "study.comparison of the sample engine's runs": (
        "827eabc32b1a659f", "41aff7dbb53287b847a6504dc79f0917859be71c1053bfa345e3241610515fac"),
}
# The same comparison's id at ed33c02, on its basis at `study comparison 1`.
ED33C02_SAMPLE_COMPARISON = "b939060b54056cec"


def under_fixed_dispatch() -> bool:
    """Whether this process computes under FIXED_DISPATCH, set before numpy and OpenBLAS loaded."""
    return all(os.environ.get(k) == v for k, v in FIXED_DISPATCH.items())


def why_no_fixed_dispatch() -> str | None:
    """Why this host cannot hold the pins, in words; None when it can."""
    machine = platform.machine()
    if machine.lower() not in ("x86_64", "amd64"):
        return (f"this host is {machine}: every pin is x86-64's under the fixed dispatch (OpenBLAS's Haswell kernels, "
                "numpy's X86_V3 loops), which it cannot run, and the fit's id rests on readings numpy computes here")
    from numpy._core._multiarray_umath import __cpu_features__ as features

    lacking = [f for f in ("AVX2", "FMA3") if not features.get(f)]
    if lacking:
        return f"this host lacks {' and '.join(lacking)}, which the fixed dispatch (OpenBLAS's Haswell kernels) needs"
    return None


NOT_HERE = why_no_fixed_dispatch()
pytestmark = pytest.mark.skipif(NOT_HERE is not None, reason=NOT_HERE or "")


def pinned(name: str, art) -> None:
    """The artifact's id is the pin's, bit for bit, in every process; its
    output hash is the pin's in a process computing under FIXED_DISPATCH."""
    pin_id, pin_hash = PINS[name]
    assert art.id == pin_id, (f"the pin {name!r} moved its id: {pin_id} at ed33c02, {art.id} now. D1 holds every pin "
                              "through stage C; the change that moved it says why")
    if under_fixed_dispatch():
        assert art.outputHash == pin_hash, (
            f"the pin {name!r} moved its output hash under the fixed dispatch: {pin_hash} at ed33c02, "
            f"{art.outputHash} now. D1 holds every pin through stage C; the change that moved it says why")


@pytest.fixture(autouse=True)
def as_on_any_host(monkeypatch, tmp_path):
    """A run's diagram drawn by no host (OF-BLD-019 §2.R), so a Proforma
    run's and a train run's basis read the same everywhere; each module's
    data folder the test's."""
    monkeypatch.setattr(proforma, "drawn_here", lambda: False)
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)


@pytest.fixture
def no_records(monkeypatch):
    """No record binds, as test_fermos' `store` holds it: each value is the one the test types."""
    monkeypatch.setattr(evidence_pool, "load", lambda *a, **k: EMPTY)


# ── fermOS ─────────────────────────────────────────────────────────────


def test_a_batch_v1_simulation_holds_its_pin(no_records):
    r = fermos.simulate(SimulationRequest(family=BATCH, overrides=typed_for(BATCH, **STANDIN_TYPED)))
    pinned("fermos.simulation batch_v1", artifacts.get(r.artifactId))


def test_a_fedbatch_v1_simulation_holds_its_pin(no_records):
    r = fermos.simulate(SimulationRequest(family=FED, overrides=typed_for(FED, **FED_TYPED)))
    pinned("fermos.simulation fedbatch_v1", artifacts.get(r.artifactId))


def test_a_chemostat_v1_simulation_holds_its_pin(no_records):
    r = fermos.simulate(SimulationRequest(family=CHEMO, overrides=typed_for(CHEMO, **STANDIN_CHEMOSTAT_TYPED)))
    pinned("fermos.simulation chemostat_v1", artifacts.get(r.artifactId))


def test_a_growth_forecast_and_the_fit_it_rests_on_hold_their_pins(no_records):
    fit = fermos.fit("dep-f", batch(T, np.random.default_rng(4), SD))
    pinned("kinetic_fit", artifacts.get(fit.kineticArtifactId))
    plain = fermos.forecast_run(fit_artifact=fit.kineticArtifactId)
    pinned("growth_forecast", artifacts.get(plain.artifactId))
    changed = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, start=fermos.StartValues(S0=60.0), changed_by=BY)
    pinned("growth_forecast with a changed start", artifacts.get(changed.artifactId))


@pytest.fixture
def vessel_worker(monkeypatch):
    """test_vessel's stand-in simulation kept under its id, and its stand-in worker."""
    keep(AEROBIC_ID, standin_simulation(True))
    w = VesselWorker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(vessel, "_SPECS", {})
    return w


def test_a_vessel_design_on_the_stand_in_worker_holds_its_pin(vessel_worker):
    d = vessel.design(VesselRequest(simulation=AEROBIC_ID, overrides=[override(AEROBIC_ID, "plant_scale", 1000.0),
                                                                     override(AEROBIC_ID, "theta_O2", 0.3)]))
    pinned("fermos.vessel", artifacts.get(d.artifactId))


# ── pureOS ─────────────────────────────────────────────────────────────


@pytest.fixture
def train_worker(monkeypatch):
    """test_train's TrainWorker, with no record pool, as its `worker` and `no_pool` hold it."""
    w = TrainWorker()
    monkeypatch.setattr(proforma, "call", w)
    monkeypatch.setattr(catalogue, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_SPECS", {})
    monkeypatch.setattr(train_spec, "_UNITS", {})
    monkeypatch.setattr(train_spec, "_pool", lambda: None)
    return w


def test_a_train_run_on_the_stand_in_worker_holds_its_pin(train_worker):
    run = pureos.run_train(spec_of(), [Override(scope="pureos:unit:t1:F1", key="V", value=0.2, by="Another Person",
                                                at=TRAIN_AT, note=TRAIN_STANDIN)])
    pinned("pureos.train_run", artifacts.get(run.artifactId))


# ── Proforma ───────────────────────────────────────────────────────────


@pytest.fixture
def evaluator(monkeypatch):
    """The closed-form stand-in evaluator and its records, as test_proforma_runs' `standin` holds them."""
    monkeypatch.setattr(proforma, "call", standins._standin_call)
    rs = standins._standin_yeast_records()
    return SimpleNamespace(records=rs, records_by_id={r["id"]: r for r in rs})


def test_a_proforma_run_on_the_stand_in_evaluator_holds_its_pin(evaluator):
    r = proforma.run(ProformaRunRequest(scenarioId=MADE_HERE, flowsheet=ETHANOL, assumptions=ASSUMED, samples=8),
                     pool=evaluator)
    pinned("proforma.run", artifacts.get(r.artifactId))


# ── the library, its comparisons, and the contract's sample engine ────


@pytest.fixture
def plant_worker(monkeypatch):
    """test_runs' stand-in worker, as its `worker` holds it."""
    stand_in = StandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


@pytest.fixture
def priced_worker(monkeypatch):
    """test_comparisons' stand-in: test_runs' worker with a run that is priced."""
    stand_in = PricedStandIn()
    monkeypatch.setattr(simulator, "call", stand_in)
    monkeypatch.setattr(library, "_PARAMETERS", {})
    return stand_in


def _two_runs_compared() -> tuple:
    """A plant's run on its own defaults and one with a person's price, compared in that order."""
    base = runs.run("sugarcane", by="Ada Moreno")
    priced = runs.run("sugarcane", None, [over("stream.sugarcane.price", 0.05, by="Ada Moreno")], by="Ada Moreno")
    rep = comparisons.make(ComparisonCreate(title="Dearer cane", runIds=[base.run.id, priced.run.id], by="Ada Moreno"))
    return base, priced, rep


def test_a_library_run_on_the_stand_in_worker_holds_its_pin(plant_worker):
    rep = runs.run("sugarcane", None, [over("stream.sugarcane.price", 0.05, by="Ada Moreno")], by="Ada Moreno")
    assert rep.run.id == rep.artifact.id
    pinned("library.run", rep.artifact)


def test_a_comparison_of_two_library_runs_holds_its_pin(plant_worker):
    base, _, rep = _two_runs_compared()
    pinned("library.run on its own defaults", base.artifact)
    pinned("study.comparison", rep.artifact)


def test_a_comparison_of_two_priced_library_runs_holds_its_pin(priced_worker):
    base, priced, rep = _two_runs_compared()
    pinned("library.run priced on its own defaults", base.artifact)
    pinned("library.run priced with a person's price", priced.artifact)
    pinned("study.comparison of priced runs", rep.artifact)


def _sample_run(value: float):
    return SAMPLE.run("placeholder", None, [given("a-parameter", value, note="a placeholder")], "Ada Moreno")


def test_a_run_of_the_contracts_sample_engine_holds_its_pin():
    run = _sample_run(2.5)
    pinned("engine.sample", artifacts.get(run.artifactId))


def test_a_comparison_of_the_sample_engines_runs_holds_its_pin():
    first, second = _sample_run(2.5), _sample_run(3.5)
    rep = comparisons.make(ComparisonCreate(title="Two placeholder runs", runIds=[first.id, second.id], by="Ada Moreno"))
    assert rep.artifact.toolVersion == comparisons.VERSION_ENGINES
    assert artifacts.artifact_id(comparisons.COMPARISON, comparisons.VERSION, rep.artifact.inputs) == \
        ED33C02_SAMPLE_COMPARISON, "the basis ed33c02 kept the comparison on"
    pinned("study.comparison of the sample engine's runs", rep.artifact)


# ── every output hash, under the fixed dispatch ────────────────────────


def test_every_output_hash_holds_under_the_fixed_dispatch():
    """Every pin of this file computed again in a process of its own,
    started under FIXED_DISPATCH, each id and output hash held."""
    if under_fixed_dispatch():
        pytest.skip("this process computes under the fixed dispatch: each pin held its output hash in place")
    here = Path(__file__).resolve()
    done = subprocess.run([sys.executable, "-m", "pytest", str(here), "-q", "-p", "no:cacheprovider"],
                          cwd=here.parents[1], env={**os.environ, **FIXED_DISPATCH}, capture_output=True, text=True,
                          timeout=FIXED_DISPATCH_TIMEOUT_S)
    pins = sum(1 for name in globals() if name.startswith("test_")) - 1
    assert done.returncode == 0 and f"{pins} passed, 1 skipped" in done.stdout, (
        f"under the fixed dispatch ({FIXED_DISPATCH}):\n{done.stdout[-6000:]}\n{done.stderr[-2000:]}")
