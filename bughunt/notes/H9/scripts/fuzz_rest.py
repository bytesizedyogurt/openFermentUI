"""H9: call every registry tool at the REST tool door with missing, extra, wrongly
typed and boundary arguments, and record what each answered.

    bh_py ../bughunt/notes/H9/scripts/fuzz_rest.py ORIGIN PROJECT OTHER_PROJECT OUT.jsonl

A finding is any answer that is not a 200 ToolResult or a 404/422 in words: a 5xx, a
body holding "Traceback", or a ToolResult whose error reads "<tool> failed: <Exception>:".
Keyless, loopback only (trust_env off).
"""
from __future__ import annotations

import json
import re
import sys
import time

import httpx

ORIGIN, PROJECT, OTHER, OUT = sys.argv[1:5]
ONLY = set(sys.argv[5].split(",")) if len(sys.argv) > 5 and sys.argv[5] else None
http = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=httpx.Timeout(240.0, connect=10.0))
H = {"X-OpenFerment-Project": PROJECT, "content-type": "application/json"}

tools = http.get("/api/tools", headers=H).json()
BIG_INT = "9" * 400
HUGE = "A" * 100_000
EXC = re.compile(r"\bfailed: ([A-Z][A-Za-z]+(Error|Exception|Exit|Interrupt|Warning)|KeyError|StopIteration)\b")


def placeholder(schema: dict, defs: dict, name: str = "") -> object:
    if "$ref" in schema:
        return placeholder(defs[schema["$ref"].rsplit("/", 1)[-1]], defs, name)
    if "anyOf" in schema:
        for s in schema["anyOf"]:
            if s.get("type") != "null":
                return placeholder(s, defs, name)
        return None
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        if "value" in props and (props.get("unit") or {}).get("type") == "string":
            return {"value": 1.5, "unit": "g/L", "note": "fuzz"}
        req = schema.get("required") or list(props)
        return {k: placeholder(props[k], defs, k) for k in req if k in props}
    if t == "array":
        return []
    if t == "integer":
        return max(1, schema.get("minimum", 1))
    if t == "number":
        return 1.5
    if t == "boolean":
        return False
    if "enum" in schema:
        return schema["enum"][0]
    return "x"


def send(name: str, raw: str, *, by: str | None = "fuzzer", headers: dict | None = None) -> dict:
    params = {"by": by} if by else {}
    t0 = time.monotonic()
    try:
        r = http.post(f"/api/tools/{name}", content=raw.encode("utf-8", "surrogatepass"), params=params,
                      headers={**H, **(headers or {})})
        status, text = r.status_code, r.text
    except httpx.HTTPError as e:
        status, text = -1, f"{type(e).__name__}: {e}"
    return {"status": status, "text": text, "ms": int((time.monotonic() - t0) * 1000)}


def verdict(res: dict) -> str | None:
    s, text = res["status"], res["text"]
    if s == -1:
        return "no answer"
    if s >= 500:
        return f"HTTP {s}"
    if "Traceback" in text:
        return "traceback in body"
    if s == 200:
        try:
            body = json.loads(text)
        except ValueError:
            return "200 with no JSON"
        err = body.get("error") or ""
        m = EXC.search(err)
        if m:
            return f"exception surfaced: {m.group(1)}"
    elif s not in (404, 422):
        return f"HTTP {s}"
    else:
        try:
            detail = json.loads(text).get("detail")
        except ValueError:
            return f"{s} with no JSON"
        if not detail:
            return f"{s} with no detail"
    return None


out = open(OUT, "w")
for info in tools:
    name = info["name"]
    if ONLY and name not in ONLY:
        continue
    schema = info["inputSchema"]
    defs = schema.get("$defs") or {}
    props = schema.get("properties") or {}
    base = placeholder(schema, defs)
    cases: list[tuple[str, str]] = []
    cases.append(("base", json.dumps(base)))
    cases.append(("empty object", "{}"))
    cases.append(("extra field", json.dumps({**base, "zzzExtra": "x"})))
    cases.append(("raw NaN at top", json.dumps({**base, "zzz": "PLACE"}).replace('"PLACE"', "NaN")))
    for key, sub in props.items():
        others = {k: v for k, v in base.items() if k != key}
        cases.append((f"{key} missing", json.dumps(others)))
        for label, val in (("int", "7"), ("bool", "true"), ("null", "null"), ("list", '["a"]'),
                           ("object", '{"a": "b"}'), ("empty string", '""'), ("spaces", '"   "'),
                           ("huge string", json.dumps(HUGE)), ("NUL char", '"a\\u0000b"'),
                           ("lone surrogate", '"a\\ud800b"'), ("negative", "-1"), ("zero", "0"),
                           ("big int", BIG_INT), ("raw NaN", "NaN"), ("raw Infinity", "Infinity"),
                           ("raw -Infinity", "-Infinity"), ("float", "2.5"), ("1e308", "1e308"),
                           ("unknown id", '"zz-unknown-0000"'), ("string number", '"5"')):
            body = json.dumps({**others, key: "PLACE"}).replace('"PLACE"', val)
            cases.append((f"{key}={label}", body))
    # quantity boundaries for the tool that takes them
    if name == "study_scenario":
        for label, val in (("big int value", BIG_INT), ("NaN value", "NaN"), ("Infinity value", "Infinity"),
                           ("1e308 value", "1e308"), ("1e309 value", "1e309"), ("negative value", "-5"),
                           ("bool value", "true"), ("string value", '"5"')):
            q = '{"title": "t", "plant": "zz-unknown", "values": [{"key": "k", "quantity": {"value": PLACE, ' \
                '"unit": "g/L", "note": "n"}}]}'
            cases.append((f"quantity {label}", q.replace("PLACE", val)))
        for label, val in (("origin by", '{"kind": "measurement", "ref": "d/e", "by": "me"}'),
                           ("origin model-estimate", '{"kind": "model-estimate", "by": "me", "at": "2026-01-01"}'),
                           ("origin junk", '"junk"'), ("origin list", "[]")):
            q = '{"title": "t", "plant": "zz-unknown", "values": [{"key": "k", "quantity": {"value": 1, ' \
                '"unit": "g/L", "origin": PLACE}}]}'
            cases.append((f"quantity {label}", q.replace("PLACE", val)))
    for label, raw in cases:
        res = send(name, raw)
        v = verdict(res)
        out.write(json.dumps({"tool": name, "case": label, "status": res["status"], "ms": res["ms"], "verdict": v,
                              "answer": res["text"][:600]}) + "\n")
        out.flush()
        if v:
            print(f"{name} | {label} | {v} | {res['text'][:200]}", flush=True)
    print(f"done {name}", flush=True)
out.close()
