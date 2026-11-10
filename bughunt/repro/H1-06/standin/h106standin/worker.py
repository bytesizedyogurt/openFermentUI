"""A worker speaking the JSON-lines protocol by hand (docs/api/workers.md, Engine ops), so its `things`
answer can carry a number `serve` would never write. Every value is a placeholder.

`python -m h106standin.worker` answers the things of engine h106: `fine` (precision 0, 0) and
`infprec` (atol infinite, written as JSON's `Infinity`, which Python's json.loads reads as inf)."""
import json
import os
import sys

from openferment_core import workers

REF = "openferment-engine-h106@0.1.0"
THINGS = [
    {"id": "fine", "title": "a thing of precision 0 and 0", "configurations": [], "precision": {"rtol": 0, "atol": 0}},
    {"id": "infprec", "title": "a thing whose stated absolute precision is infinite", "configurations": [],
     "precision": {"rtol": 0, "atol": float("inf")}},
]


def main(things):
    out = os.fdopen(workers.RESPONSES_FD if workers.RESPONSES_FD is not None else os.dup(1), "w", buffering=1)

    def write(obj):
        # json.dumps's default allow_nan=True writes inf as the bare token Infinity.
        out.write(json.dumps(obj) + "\n")
        out.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        rid, op, args = req.get("id"), req.get("op"), req.get("args") or {}
        if op == "ping":
            write({"id": rid, "ok": True, "result": {"worker": "h106", "pid": os.getpid()}})
        elif op == "things":
            write({"id": rid, "ok": True, "result": {"things": things}})
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
    main(THINGS)
