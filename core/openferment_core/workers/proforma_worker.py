"""The Proforma worker: BioSTEAM in a process of its own, kept warm
(OF-BLD-014 §8.1).

With flowsheets/, the only place in openferment_core that imports `biosteam`
(test_workers holds it to that). A cold import takes about forty seconds, so
the worker builds each flowsheet once and keeps it; every later request sets
its inputs on the built objects and re-simulates (Appendix 3, trap 3).

    ping        answered by `serve`
    benchmark   the published reference biorefinery (§8.2)
    evaluate    one case of a flowsheet: its inputs in, its outputs out
    grid        the outputs over a grid of up to three inputs
    montecarlo  Latin hypercube samples of the inputs, seeded
"""
from __future__ import annotations

import itertools
from typing import Any

import biosteam  # noqa: F401  (imported here so the cost is paid at start)
import numpy as np
from scipy.stats import qmc

from .. import flowsheets
from . import serve

_BUILT: dict[str, Any] = {}


class Refused(ValueError):
    """The request cannot be computed, in words."""


def built(name: str) -> tuple[Any, Any]:
    try:
        module = flowsheets.load(name)
    except KeyError as e:
        raise Refused(str(e)) from e
    if name not in _BUILT:
        _BUILT[name] = module.build()
    return module, _BUILT[name]


def evaluate(name: str, values: dict[str, float]) -> dict[str, float]:
    module, system = built(name)
    unknown = sorted(set(values) - set(module.INPUTS))
    if unknown:
        raise Refused(f"{name} has no input {', '.join(unknown)}; it takes {', '.join(module.INPUTS)}")
    return module.evaluate(system, values)


def grid(name: str, axes: dict[str, list[float]], base: dict[str, float]) -> dict[str, Any]:
    if not 1 <= len(axes) <= 3:
        raise Refused("a grid runs over one to three inputs")
    keys = list(axes)
    cells = []
    for combo in itertools.product(*(axes[k] for k in keys)):
        values = {**base, **dict(zip(keys, combo))}
        cells.append({"at": dict(zip(keys, combo)), "outputs": evaluate(name, values)})
    return {"axes": axes, "base": base, "cells": cells}


def _sample(spec: dict[str, Any], u: float) -> float:
    kind = spec["kind"]
    if kind == "fixed":
        return float(spec["value"])
    lo, hi = float(spec["low"]), float(spec["high"])
    if kind == "uniform":
        return lo + u * (hi - lo)
    if kind == "triangular":
        mode = float(spec["mode"])
        if hi == lo:
            return lo
        c = (mode - lo) / (hi - lo)
        return lo + (hi - lo) * (np.sqrt(u * c) if u < c else 1 - np.sqrt((1 - u) * (1 - c)))
    raise Refused(f"there is no distribution {kind}")


def montecarlo(name: str, specs: dict[str, dict[str, Any]], n: int, seed: int, base: dict[str, float]) -> dict[str, Any]:
    keys = list(specs)
    lhs = qmc.LatinHypercube(d=max(1, len(keys)), seed=seed).random(n)
    samples = []
    for row in lhs:
        values = {**base, **{k: _sample(specs[k], float(row[i])) for i, k in enumerate(keys)}}
        try:
            samples.append({"inputs": values, "outputs": evaluate(name, values), "infeasible": None})
        except Refused as e:
            samples.append({"inputs": values, "outputs": None, "infeasible": str(e)})
        except Exception as e:  # a case the simulator cannot close is a result, named
            samples.append({"inputs": values, "outputs": None, "infeasible": f"{type(e).__name__}: {e}"})
    return {"n": n, "seed": seed, "samples": samples}


def _op_evaluate(args):
    return evaluate(str(args["flowsheet"]), dict(args.get("values") or {}))


def _op_grid(args):
    return grid(str(args["flowsheet"]), dict(args["axes"]), dict(args.get("base") or {}))


def _op_montecarlo(args):
    return montecarlo(str(args["flowsheet"]), dict(args["specs"]), int(args.get("n", 500)), int(args.get("seed", 0)),
                      dict(args.get("base") or {}))


def _op_benchmark(args):
    from openferment_core.flowsheets import cornstover_benchmark

    return cornstover_benchmark.run()


HANDLERS = {"evaluate": _op_evaluate, "grid": _op_grid, "montecarlo": _op_montecarlo, "benchmark": _op_benchmark}

if __name__ == "__main__":
    serve(HANDLERS, name="proforma")
