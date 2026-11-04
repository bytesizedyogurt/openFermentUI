"""The mirror engine's worker: it computes nothing, and answers the typed quantities a run gives it.

Its one thing, `reflect`, takes two placeholder parameters, each with a placeholder default in a
placeholder unit. A run answers each parameter's value as the run stands, the value it sets or else
the default that stands for a value left alone, under the parameter's key, in its unit and in key
order, then `values set`, how many values the run set. Every output is a function of the request
alone, so the thing states its precision as rtol 0, atol 0, and a replay is identical. The time the
run took is a diagnostic beside the outputs, since a replay compares the outputs alone and a clock
reading moves on every run (docs/api/engines.md, The worker). It has no plant, so it writes no SFF
file. One JSON request a line on stdin, one answer a line on stdout (docs/api/workers.md).
"""
import math
import time
from importlib.metadata import version

from openferment_core.workers import serve

DISTRIBUTION = "openferment-engine-mirror"
THING = "reflect"

THINGS = [{"id": THING, "title": "The typed quantities a run gives it, returned as they are",
           "kind": "placeholder", "configurations": [], "defaultConfiguration": None,
           "precision": {"rtol": 0, "atol": 0}}]

# Each parameter's key, label, unit and default, in key order: placeholders alone.
PARAMETERS = [("placeholder-a", "A placeholder the mirror returns", "placeholder-unit", 1.0),
              ("placeholder-b", "Another placeholder the mirror returns", "another-placeholder-unit", 2.0)]
UNITS = {key: unit for key, _, unit, _ in PARAMETERS}


class Refused(Exception):
    """A request the mirror engine refuses, said in its words."""


def _thing(args):
    if args.get("thing") != THING:
        raise Refused(f"the mirror engine runs no thing {args.get('thing')!r}; it runs {THING!r}")
    if args.get("configuration") is not None:
        raise Refused(f"the mirror's thing {THING!r} takes no configuration, "
                      f"and the request names {args['configuration']!r}")


def _finite(value):
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        return False


def _given(args):
    """The values the run sets, by key, each held to the parameter it sets."""
    _thing(args)
    inputs = args.get("inputs", [])
    if not isinstance(inputs, list):
        raise Refused("a run's inputs are a list of values, each a name, a value and a unit")
    given = {}
    for entry in inputs:
        if not isinstance(entry, dict) or not {"name", "value", "unit"} <= entry.keys():
            raise Refused(f"each value a run sets is a name, a value and a unit, and the run sent {entry!r}")
        name, value, unit = entry["name"], entry["value"], entry["unit"]
        if name not in UNITS:
            raise Refused(f"the mirror's thing {THING!r} takes no parameter {name!r}; "
                          f"it takes {', '.join(UNITS)}")
        if name in given:
            raise Refused(f"the run sets {name!r} twice")
        if unit != UNITS[name]:
            raise Refused(f"{name!r} is set in {unit!r}, and the mirror takes it in {UNITS[name]!r}")
        if not _finite(value):
            raise Refused(f"{name!r} takes a finite number, and the run set {value!r}")
        given[name] = value
    return given


def things(args):
    return {"things": THINGS}


def parameters(args):
    _thing(args)
    ref = f"{DISTRIBUTION}@{version(DISTRIBUTION)}"
    return {"parameters": [
        {"key": key, "label": label, "unit": unit, "value": default,
         "origin": {"kind": "library-default", "ref": ref},
         "boundsReason": "the mirror returns any finite number it is given, so it bounds none"}
        for key, label, unit, default in PARAMETERS]}


def run(args):
    started = time.perf_counter()
    given = _given(args)
    outputs = [{"name": key, "value": given.get(key, default), "unit": unit}
               for key, _, unit, default in PARAMETERS]
    outputs.append({"name": "values set", "value": len(given), "unit": ""})
    took = (time.perf_counter() - started) * 1000
    return {"outputs": outputs, "diagnostics": [{"name": "time taken", "value": took, "unit": "ms"}]}


def sff_export(args):
    _thing(args)
    raise Refused("the mirror engine has no plant, so it writes no SFF file")


HANDLERS = {"things": things, "parameters": parameters, "run": run, "sff_export": sff_export}

if __name__ == "__main__":
    serve(HANDLERS, name="mirror")
