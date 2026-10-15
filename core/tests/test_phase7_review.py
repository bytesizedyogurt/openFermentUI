"""What the review of Phase 7 found (OF-BLD-014 §7.R). Each test failed
before its fix. Every series is SYNTHETIC, built in test_fermos."""
from __future__ import annotations

import numpy as np
import pytest

from openferment_core import fermos
from openferment_core.models import StartValues
from test_fermos import SD, T, batch, store  # noqa: F401


def _fit(seed=4):
    return fermos.kinetic_fit(batch(T, np.random.default_rng(seed), SD))


# R3 — the service decides identifiability from the numbers, never the flag.
def test_a_posted_identified_flag_is_not_trusted():
    k = _fit()
    xmax = fermos.param(k, "Xmax")
    xmax.low = -abs(xmax.value)  # the interval reaches zero …
    xmax.identified = True       # … whatever the flag says
    with pytest.raises(fermos.FitRefused, match="Xmax is not identified"):
        fermos.forecast(k)


def test_a_flag_without_the_covariance_behind_it_is_not_trusted():
    k = _fit()
    i = [p.name for p in k.params].index("Xmax")
    k.covariance[i][i] = (k.params[i].value * 10) ** 2  # the covariance says it is unpinned
    with pytest.raises(fermos.FitRefused, match="Xmax is not identified"):
        fermos.forecast(k)


# R4 — yield describes the process: reading scatter stays out of it.
def test_the_yield_interval_does_not_grow_with_reading_scatter():
    k = _fit()
    narrow = fermos.forecast(k)["yieldInterval"]
    for q in k.quality:
        q.scatter *= 20
    wide = fermos.forecast(k)["yieldInterval"]
    assert wide["high"] - wide["low"] == pytest.approx(narrow["high"] - narrow["low"], rel=1e-9)


# R5 — a starting value equal to the run's own is no change.
def test_the_runs_own_starting_value_is_not_an_assumption(store):  # noqa: F811
    fit = fermos.fit("dep-r5", batch(T, np.random.default_rng(4), SD))
    x0 = fermos.param(fit.kinetic, "X0").value
    same = fermos.forecast_run(fit_artifact=fit.kineticArtifactId, start=StartValues(X0=x0))
    assert same.evidence.provenance == "computed"
    own = fermos.forecast_run(fit_artifact=fit.kineticArtifactId)
    assert same.artifactId == own.artifactId


def test_a_start_for_a_series_the_run_lacks_is_refused(store):  # noqa: F811
    runs = batch(T, np.random.default_rng(4), SD)[:1]
    fit = fermos.fit("dep-r5b", runs)
    with pytest.raises(fermos.FitRefused, match="no product series"):
        fermos.forecast_run(fit_artifact=fit.kineticArtifactId, start=StartValues(P0=1.0), changed_by="Sean Creighton")
