"""H1-07's stand-in worker, on the core's own `workers.serve` (docs/api/workers.md, Engine ops). Every
value is a placeholder, and every answer is JSON in the shapes of docs/api/openapi.json: the one thing
outside the ordinary is that its `things` answer lists the id `dup` twice, with two precisions."""
from openferment_core.workers import serve

REF = "openferment-engine-h107@0.1.0"
THINGS = [
    {"id": "dup", "title": "the first of two things of one id", "configurations": [],
     "precision": {"rtol": 0, "atol": 0}},
    {"id": "dup", "title": "the second of two things of one id", "configurations": [],
     "precision": {"rtol": 1, "atol": 1}},
    {"id": "single", "title": "a thing of its own id (the control)", "configurations": [],
     "precision": {"rtol": 0, "atol": 0}},
]
IDS = {t["id"] for t in THINGS}


class Refused(Exception):
    """A request the stand-in refuses, in its words."""


def _thing(args):
    if args.get("thing") not in IDS:
        raise Refused(f"the stand-in runs no thing {args.get('thing')!r}")


def things(args):
    return {"things": THINGS}


def parameters(args):
    _thing(args)
    return {"parameters": [{"key": "a", "label": "a placeholder", "unit": "u", "value": 1.0,
                            "origin": {"kind": "library-default", "ref": REF},
                            "min": 0, "max": 10, "boundsReason": "placeholder"}]}


def run(args):
    _thing(args)
    given = {v["name"]: v["value"] for v in args.get("inputs") or []}
    return {"outputs": [{"name": "x", "value": given.get("a", 1.0), "unit": "u"}]}


def sff_export(args):
    raise Refused("the stand-in has no flowsheet")


if __name__ == "__main__":
    serve({"things": things, "parameters": parameters, "run": run, "sff_export": sff_export}, name="h107")
