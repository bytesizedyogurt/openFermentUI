"""A worker that misbehaves on purpose, one thing a misbehaviour, speaking the JSON-lines protocol by
hand (no `serve`), so it can write what `serve` never would. Every value is a placeholder."""
import json
import os
import random
import sys
import time

from openferment_core import workers

OUT = os.fdopen(workers.RESPONSES_FD if workers.RESPONSES_FD is not None else os.dup(1), "w", buffering=1)
REF = "openferment-engine-h1probe@0.1.0"
PREC = {"rtol": 0, "atol": 0}
THINGS = [
    {"id": "ok", "title": "answers its value", "configurations": [], "precision": PREC},
    {"id": "slow", "title": "sleeps, then answers", "configurations": [], "precision": PREC},
    {"id": "garbage", "title": "writes a line that is no JSON", "configurations": [], "precision": PREC},
    {"id": "otherid", "title": "answers another request's id first, then its own", "configurations": [], "precision": PREC},
    {"id": "otheridonly", "title": "answers another request's id alone", "configurations": [], "precision": PREC},
    {"id": "exit", "title": "exits mid-run", "configurations": [], "precision": PREC},
    {"id": "big", "title": "answers an oversized line", "configurations": [], "precision": PREC},
    {"id": "nanout", "title": "answers NaN as JSON's NaN", "configurations": [], "precision": PREC},
    {"id": "extra", "title": "answers an output with a stray number beside it", "configurations": [], "precision": PREC},
    {"id": "infprec", "title": "states an infinite precision", "configurations": [], "precision": {"rtol": 0, "atol": float("inf")}},
    {"id": "dup", "title": "the first of two things of one id", "configurations": [], "precision": PREC},
    {"id": "dup", "title": "the second of two things of one id", "configurations": [], "precision": {"rtol": 1, "atol": 1}},
    {"id": "badsff", "title": "answers a flowsheet that is no object", "configurations": [], "precision": PREC},
    {"id": "nondet", "title": "answers a different number each run", "configurations": [], "precision": PREC},
    {"id": "nullresult", "title": "answers ok with no result", "configurations": [], "precision": PREC},
    {"id": "cfg", "title": "takes configurations", "configurations": ["one", " two "], "defaultConfiguration": "one",
     "precision": PREC},
    {"id": "extrakey", "title": "answers a result with a stray key", "configurations": [], "precision": PREC},
    {"id": "refuse", "title": "refuses every run", "configurations": [], "precision": PREC},
]


def params(thing):
    if thing == "slow":
        return [{"key": "seconds", "label": "how long it sleeps", "unit": "s", "value": 4.0,
                 "origin": {"kind": "library-default", "ref": REF}, "min": 0, "max": 100, "boundsReason": "placeholder"}]
    return [{"key": "a", "label": "a placeholder", "unit": "u", "value": 1.0,
             "origin": {"kind": "library-default", "ref": REF}, "min": 0, "max": 10, "boundsReason": "placeholder"}]


def write(obj, **kw):
    OUT.write(json.dumps(obj, **kw) + "\n")
    OUT.flush()


def run(rid, args):
    thing = args.get("thing")
    given = {v["name"]: v["value"] for v in args.get("inputs") or []}
    outputs = [{"name": "x", "value": given.get("a", 1.0), "unit": "u"}]
    if thing == "slow":
        time.sleep(float(given.get("seconds", 4.0)))
        return {"outputs": [{"name": "slept", "value": given.get("seconds", 4.0), "unit": "s"}]}
    if thing == "garbage":
        OUT.write("this is no JSON\n"); OUT.flush(); return None
    if thing == "otherid":
        write({"id": rid + 1000, "ok": True, "result": {"outputs": [{"name": "x", "value": 999.0, "unit": "u"}]}})
        return {"outputs": outputs}
    if thing == "otheridonly":
        write({"id": rid + 1000, "ok": True, "result": {"outputs": outputs}})
        time.sleep(60)
        return None
    if thing == "exit":
        sys.stderr.write("the probe worker exits mid-run\n"); sys.stderr.flush()
        os._exit(3)
    if thing == "big":
        return {"outputs": [{"name": "x", "value": "z" * (int(given.get("a", 1.0)) * 10_000_000), "unit": ""}]}
    if thing == "nanout":
        OUT.write(json.dumps({"id": rid, "ok": True, "result": {"outputs": [{"name": "x", "value": float("nan"), "unit": "u"}]}}) + "\n")
        OUT.flush(); return None
    if thing == "extra":
        return {"outputs": [{"name": "x", "value": 1.0, "unit": "u", "stray": 42}]}
    if thing == "nondet":
        return {"outputs": [{"name": "x", "value": random.random(), "unit": "u"}]}
    if thing == "nullresult":
        write({"id": rid, "ok": True}); return None
    if thing == "extrakey":
        return {"outputs": outputs, "stray": 42}
    if thing == "refuse":
        raise Refused("the probe refuses this in words")
    return {"outputs": outputs}


class Refused(Exception):
    pass


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        rid, op, args = req.get("id"), req.get("op"), req.get("args") or {}
        try:
            if op == "ping":
                result = {"worker": "probe", "pid": os.getpid()}
            elif op == "things":
                # Written by hand so Infinity can stand in a precision.
                OUT.write(json.dumps({"id": rid, "ok": True, "result": {"things": THINGS}}) + "\n"); OUT.flush()
                continue
            elif op == "parameters":
                result = {"parameters": params(args.get("thing"))}
            elif op == "run":
                result = run(rid, args)
                if result is None:
                    continue
            elif op == "sff_export":
                if args.get("thing") == "badsff":
                    result = {"flowsheet": ["no", "object"]}
                else:
                    raise Refused("the probe has no plant")
            else:
                raise KeyError(op)
            write({"id": rid, "ok": True, "result": result})
        except Exception as e:
            write({"id": rid, "ok": False, "error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    main()
