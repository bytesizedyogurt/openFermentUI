"""A worker speaking the JSON-lines protocol by hand (docs/api/workers.md, Engine ops). Every value is
a placeholder. `python -m h109standin.worker` answers the things of engine h109:

- `extra`: one output {"name": "x", "value": <a>, "unit": "u", "stray": N}, N being 41 plus the count
  of `run` ops of `extra` this process has answered (42 on the first, 43 on the next), so a replay
  shows whether the stray number enters the comparison;
- `nounit`: the control, one output {"name": "x", "value": <a>} with no unit."""
import json
import os
import sys

from openferment_core import workers

REF = "openferment-engine-h109@0.1.0"
PRECISION = {"rtol": 0, "atol": 0}
THINGS = [
    {"id": "extra", "title": "one output with a stray number beside its name, value and unit",
     "configurations": [], "defaultConfiguration": None, "precision": PRECISION},
    {"id": "nounit", "title": "one output with no unit (the control)",
     "configurations": [], "defaultConfiguration": None, "precision": PRECISION},
]
IDS = {t["id"] for t in THINGS}


def main():
    out = os.fdopen(workers.RESPONSES_FD if workers.RESPONSES_FD is not None else os.dup(1), "w", buffering=1)

    def write(obj):
        out.write(json.dumps(obj) + "\n")
        out.flush()

    answered = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        rid, op, args = req.get("id"), req.get("op"), req.get("args") or {}
        thing = args.get("thing")
        if op in ("parameters", "run", "sff_export") and thing not in IDS:
            write({"id": rid, "ok": False, "error": f"Refused: h109 runs no thing {thing!r}"})
        elif op == "ping":
            write({"id": rid, "ok": True, "result": {"worker": "h109", "pid": os.getpid()}})
        elif op == "things":
            write({"id": rid, "ok": True, "result": {"things": THINGS}})
        elif op == "parameters":
            write({"id": rid, "ok": True, "result": {"parameters": [
                {"key": "a", "label": "a placeholder", "unit": "u", "value": 1.0,
                 "origin": {"kind": "library-default", "ref": REF}, "min": 0, "max": 10,
                 "boundsReason": "placeholder"}]}})
        elif op == "run":
            given = {v["name"]: v["value"] for v in args.get("inputs") or []}
            a = given.get("a", 1.0)
            if thing == "extra":
                answered += 1
                o = {"name": "x", "value": a, "unit": "u", "stray": 41 + answered}
            else:
                o = {"name": "x", "value": a}
            write({"id": rid, "ok": True, "result": {"outputs": [o]}})
        elif op == "sff_export":
            write({"id": rid, "ok": False, "error": "Refused: the stand-in has no flowsheet"})
        else:
            write({"id": rid, "ok": False, "error": f"KeyError: {op}"})


if __name__ == "__main__":
    main()
