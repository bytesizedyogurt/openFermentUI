"""A worker for the engine contract's own tests (docs/api/engines.md; ADR-015).

The worker of `engine/sample.py`'s engine, which no entry point registers. It
computes nothing: its things and parameters are placeholders in placeholder
units, a run answers the values it was given and their count, and an SFF
export is refused in words, as the contract has an engine with no plant say
so. One thing refuses every run, so a receipt is exercised; `environment`
answers the names of the variables the worker was started with, so the tests
see that no key and no database address reaches it.
"""
from __future__ import annotations

import os
from importlib.metadata import version

from . import serve

PRECISION = {"rtol": 0.0, "atol": 0.0}
THINGS = [
    {"id": "placeholder", "title": "A placeholder thing", "kind": "placeholder", "configurations": [],
     "precision": PRECISION},
    {"id": "placeholder-configured", "title": "A placeholder thing in two configurations", "kind": "placeholder",
     "configurations": ["one way", "another way"], "defaultConfiguration": "one way", "precision": PRECISION},
    {"id": "refuses", "title": "A thing whose every run the worker refuses", "kind": "placeholder",
     "configurations": [], "precision": PRECISION},
]


class Refused(Exception):
    """A request the sample refuses, said in its words."""


def _thing(args: dict) -> dict:
    found = next((t for t in THINGS if t["id"] == args.get("thing")), None)
    if found is None:
        raise Refused(f"the sample engine runs no thing {args.get('thing')!r}")
    return found


def _things(args: dict) -> dict:
    return {"things": THINGS}


def _parameters(args: dict) -> dict:
    _thing(args)
    ref = f"openferment-core@{version('openferment-core')}"
    return {"parameters": [
        {"key": "a-parameter", "label": "A placeholder parameter", "unit": "placeholder-unit", "value": 1.5,
         "origin": {"kind": "library-default", "ref": ref}, "min": 0, "max": 10,
         "boundsReason": "placeholder bounds the sample states, so a value outside them is refused"},
        {"key": "a-setting", "label": "A placeholder setting", "unit": "", "value": "plain",
         "choices": ["plain", "another"], "origin": {"kind": "convention", "note": "a software setting the sample keeps"},
         "boundsReason": "a setting chosen from its words, with no bounds"},
    ]}


def _run(args: dict) -> dict:
    thing = _thing(args)
    if thing["id"] == "refuses":
        raise Refused("the sample engine refuses every run of this thing, in these words")
    values = list(args.get("inputs") or [])
    outputs = [{"name": f"given {v['name']}", "value": v["value"], "unit": v["unit"]} for v in values]
    outputs.append({"name": "count", "value": len(values), "unit": "1"})
    return {"outputs": outputs}


def _sff_export(args: dict) -> dict:
    _thing(args)
    raise Refused("the sample engine has no plant, so it writes no SFF file")


def _environment(args: dict) -> dict:
    return {"names": sorted(os.environ)}


HANDLERS = {"things": _things, "parameters": _parameters, "run": _run, "sff_export": _sff_export,
            "environment": _environment}

if __name__ == "__main__":
    serve(HANDLERS, name="sample")
