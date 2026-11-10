"""H9: every registry tool, and ask_postdoc and get_artifact, through the openferment MCP
server in its own process, over raw JSON-RPC lines on stdio (so NaN, Infinity and a
400-digit integer reach it as a client could write them).

    bh_py ../bughunt/notes/H9/scripts/fuzz_mcp.py DBURL PROJECT OUT.jsonl [MODULE]

MODULE is openferment_core.mcp_server (the default) or openferment_core.literature_mcp.

A finding is a JSON-RPC error, a result flagged isError, a result that is no JSON, a
traceback, or a tool error reading "<tool> failed: <Exception>".
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time

DBURL, PROJECT, OUT = sys.argv[1:4]
MODULE = sys.argv[4] if len(sys.argv) > 4 else "openferment_core.mcp_server"
CORE = "/home/user/openFermentUI/core"
env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
env.update({"OPENFERMENT_DATABASE_URL": DBURL, "ANTHROPIC_API_KEY": ""})
proc = subprocess.Popen([f"{CORE}/.venv/bin/python", "-m", MODULE, "--project", PROJECT],
                        cwd=CORE, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(OUT + ".stderr", "w"),
                        text=True, bufsize=1)
lines: list[str] = []
cv = threading.Condition()


def reader() -> None:
    for line in proc.stdout:  # type: ignore[union-attr]
        with cv:
            lines.append(line)
            cv.notify_all()


threading.Thread(target=reader, daemon=True).start()
ids = iter(range(1, 10**9))


def call(method: str, params_raw: str, timeout: float = 240) -> dict:
    rid = next(ids)
    proc.stdin.write(f'{{"jsonrpc": "2.0", "id": {rid}, "method": "{method}", "params": {params_raw}}}\n')  # type: ignore[union-attr]
    proc.stdin.flush()  # type: ignore[union-attr]
    end = time.monotonic() + timeout
    with cv:
        while True:
            for n, line in enumerate(lines):
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("id") == rid:
                    lines.pop(n)
                    return msg
            left = end - time.monotonic()
            if left <= 0:
                return {"timeout": True}
            cv.wait(left)


call("initialize", json.dumps({"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "h9-raw-client", "version": "1.0"}}))
proc.stdin.write('{"jsonrpc": "2.0", "method": "notifications/initialized"}\n')  # type: ignore[union-attr]
proc.stdin.flush()  # type: ignore[union-attr]
listed = call("tools/list", "{}")["result"]["tools"]
EXC = re.compile(r"\bfailed: [A-Z][A-Za-z]+(Error|Exception)\b")
BIG = "9" * 400
out = open(OUT, "w")


def verdict(msg: dict) -> str | None:
    if msg.get("timeout"):
        return "no answer"
    if "error" in msg:
        return f"JSON-RPC error {msg['error'].get('code')}: {str(msg['error'].get('message'))[:200]}"
    res = msg.get("result") or {}
    text = "".join(c.get("text", "") for c in res.get("content") or [])
    if res.get("isError"):
        return f"isError: {text[:200]}"
    if "Traceback" in text:
        return "traceback"
    try:
        body = json.loads(text)
    except ValueError:
        return f"no JSON: {text[:200]}"
    err = body.get("error") or body.get("declined") or ""
    if EXC.search(str(err)):
        return f"exception surfaced: {str(err)[:200]}"
    return None


for tool in listed:
    name, schema = tool["name"], tool["inputSchema"]
    props = list((schema.get("properties") or {}).keys())
    cases = [("empty object", "{}"), ("extra field", '{"zzzExtra": "x"}'), ("raw NaN", '{"zzz": NaN}'),
             ("raw Infinity", '{"zzz": Infinity}'), ("big int", f'{{"zzz": {BIG}}}')]
    for p in props:
        for label, val in (("int", "7"), ("object", '{"a": "b"}'), ("list", '["a"]'), ("null", "null"),
                           ("huge string", json.dumps("A" * 100_000)), ("NUL", '"a\\u0000b"'), ("NaN", "NaN"),
                           ("big int", BIG), ("negative", "-1")):
            cases.append((f"{p}={label}", f'{{"{p}": {val}}}'))
    if name == "study_scenario":
        for label, val in (("big int value", BIG), ("NaN value", "NaN"), ("1e309 value", "1e309")):
            cases.append((f"quantity {label}", '{"title": "t", "plant": "zz", "values": [{"key": "k", "quantity": '
                          f'{{"value": {val}, "unit": "g/L"}}}}]}}'))
    for label, raw in cases:
        msg = call("tools/call", f'{{"name": "{name}", "arguments": {raw}}}')
        v = verdict(msg)
        out.write(json.dumps({"tool": name, "case": label, "verdict": v, "answer": json.dumps(msg)[:600]}) + "\n")
        out.flush()
        if v:
            print(f"{name} | {label} | {v}", flush=True)
    print(f"done {name}", flush=True)
proc.stdin.close()  # type: ignore[union-attr]
proc.terminate()
