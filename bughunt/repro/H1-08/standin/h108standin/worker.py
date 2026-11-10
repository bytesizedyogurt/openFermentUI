"""A worker speaking the JSON-lines protocol by hand (docs/api/workers.md, Engine ops). Every value is
a placeholder. `python -m h108standin.worker` answers the things of engine h108: `cfg`, listed in the
configurations "one" and " two ", "one" its default. Each op it answers is logged to the file
H108_WORKER_LOG names, so run.sh can say which configuration, if any, reached the worker."""
import json
import os
import sys

from openferment_core import workers

REF = "openferment-engine-h108@0.1.0"
THINGS = [
    {"id": "cfg", "title": "a thing listed in two configurations, the second with a space on each side",
     "configurations": ["one", " two "], "defaultConfiguration": "one", "precision": {"rtol": 0, "atol": 0}},
]
LOG = os.environ.get("H108_WORKER_LOG")


def note(op, args):
    if LOG:
        with open(LOG, "a") as f:
            f.write(json.dumps({"op": op, "configuration": args.get("configuration")}) + "\n")


def main():
    out = os.fdopen(workers.RESPONSES_FD if workers.RESPONSES_FD is not None else os.dup(1), "w", buffering=1)

    def write(obj):
        out.write(json.dumps(obj) + "\n")
        out.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        rid, op, args = req.get("id"), req.get("op"), req.get("args") or {}
        if op in ("parameters", "run"):
            note(op, args)
        if op == "ping":
            write({"id": rid, "ok": True, "result": {"worker": "h108", "pid": os.getpid()}})
        elif op == "things":
            write({"id": rid, "ok": True, "result": {"things": THINGS}})
        elif op == "parameters":
            write({"id": rid, "ok": True, "result": {"parameters": [
                {"key": "a", "label": "a placeholder", "unit": "u", "value": 1.0,
                 "origin": {"kind": "library-default", "ref": REF}, "min": 0, "max": 10, "boundsReason": "placeholder"}]}})
        elif op == "run":
            given = {v["name"]: v["value"] for v in args.get("inputs") or []}
            write({"id": rid, "ok": True, "result": {"outputs": [{"name": "x", "value": given.get("a", 1.0), "unit": "u"}]}})
        elif op == "sff_export":
            write({"id": rid, "ok": False, "error": "Refused: the stand-in has no flowsheet"})
        else:
            write({"id": rid, "ok": False, "error": f"KeyError: {op}"})


if __name__ == "__main__":
    main()
