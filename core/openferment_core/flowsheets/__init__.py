"""Proforma's flowsheets (OF-BLD-014 §8.1). Imported by the Proforma worker
alone: `biosteam` is imported here and in workers/proforma_worker.py and
nowhere else in the package (E.6; test_workers greps for it).

A flowsheet module in KNOWN exposes (the benchmark, cornstover_benchmark,
runs a published model whole and exposes `run()` alone):

    NAME      its id
    INPUTS    {key: (label, unit, default)} — what `evaluate` may set
    build()   the BioSTEAM system, built once and kept warm by the worker
    evaluate(system, values) -> dict
              set the inputs on the built objects, re-simulate, and return
              the outputs, each a number with its unit in the key's spec
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType

KNOWN = ("toy",)


def load(name: str) -> ModuleType:
    if name not in KNOWN:
        raise KeyError(f"there is no flowsheet {name}; there are {', '.join(KNOWN)}")
    return import_module(f"{__name__}.{name}")
