"""Proforma's flowsheets (OF-BLD-014 §8.1; the shelf, OF-BLD-019 §2.1).

The flowsheet modules are imported by the Proforma worker alone: `biosteam`
is imported in them and in workers/proforma_worker.py and nowhere else in
the package (E.6; test_workers greps for it). This package's own import, and
`shelf`, import no BioSTEAM, so the service serves the shelf without it.

KNOWN is the shelf's ids and the test-only toy's (shelf.py). A flowsheet
module in KNOWN that is evaluated case by case exposes:

    NAME      its id
    INPUTS    {key: (label, unit, default)} — what `evaluate` may set
    build()   the BioSTEAM system, built once and kept warm by the worker
    evaluate(system, values) -> dict
              set the inputs on the built objects, re-simulate, and return
              the outputs, each a number with its unit in the key's spec
    parts(built) -> dict
              the objects the worker reads the run's tables from after the
              base case: `system`, and where the flowsheet prices a product,
              `tea`, `product`, `feedstock`, the solved `price` (USD per kg
              of the product stream), `basis_flow` (kg/hr the price is per)
              and `basis` (what that flow is, in words)

A reference biorefinery (cornstover_benchmark, corn_drygrind) runs a
published model whole; the worker refuses to evaluate it case by case. For
its reference run (OF-BLD-019 §2.2, the worker's `reference` op) it exposes:

    load()          the package's plant, built afresh with every default its
                    own; the worker calls it inside `package_defaults()`
    parts(built)    as above, with `price` None: the package's own price
    outputs(built)  the package's result, its `package` and `references`
    read_back(built)  (optional) every input the shelf lists, read back

and cornstover_benchmark keeps `run()`, the benchmark's own (§8.2).
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType

from .shelf import SHELF, TEST_ONLY

KNOWN = (*SHELF, *TEST_ONLY)


def load(name: str) -> ModuleType:
    if name not in KNOWN:
        raise KeyError(f"there is no flowsheet {name}; there are {', '.join(KNOWN)}")
    return import_module(f"{__name__}.{name}")
