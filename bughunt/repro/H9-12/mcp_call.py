"""H9-12: study_scenario through the openferment MCP server in its own process, over raw
JSON-RPC lines on stdio (so a 400-digit integer and 1e309 reach it as a client writes them).

    bh_py /home/user/openFermentUI/bughunt/repro/H9-12/mcp_call.py DBURL PROJECT

Prints one line per case: CASE <label> | isError=<bool> | text=<the result's text>.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time

DBURL, PROJECT = sys.argv[1:3]
CORE = "/home/user/openFermentUI/core"
env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
env.update({"OPENFERMENT_DATABASE_URL": DBURL, "ANTHROPIC_API_KEY": ""})
proc = subprocess.Popen([f"{CORE}/.venv/bin/python", "-m", "openferment_core.mcp_server", "--project", PROJECT],
                        cwd=CORE, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, bufsize=1)
lines: list[str] = []
errs: list[str] = []
cv = threading.Condition()


def reader() -> None:
    for line in proc.stdout:  # type: ignore[union-attr]
        with cv:
            lines.append(line)
            cv.notify_all()


def err_reader() -> None:
    for line in proc.stderr:  # type: ignore[union-attr]
        errs.append(line)


threading.Thread(target=reader, daemon=True).start()
threading.Thread(target=err_reader, daemon=True).start()
ids = iter(range(1, 10**9))


def call(method: str, params_raw: str, timeout: float = 180) -> dict:
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
                               "clientInfo": {"name": "h9-12-raw-client", "version": "1.0"}}))
proc.stdin.write('{"jsonrpc": "2.0", "method": "notifications/initialized"}\n')  # type: ignore[union-attr]
proc.stdin.flush()  # type: ignore[union-attr]

BIG = "9" * 400
for label, val in (("1e309 value (control)", "1e309"), ("400-digit integer value", BIG)):
    args = ('{"title": "t", "plant": "zz", "values": [{"key": "k", "quantity": '
            f'{{"value": {val}, "unit": "g/L"}}}}]}}')
    msg = call("tools/call", f'{{"name": "study_scenario", "arguments": {args}}}')
    if msg.get("timeout"):
        print(f"CASE {label} | no answer")
        continue
    if "error" in msg:
        print(f"CASE {label} | JSON-RPC error {json.dumps(msg['error'])[:300]}")
        continue
    res = msg.get("result") or {}
    text = "".join(c.get("text", "") for c in res.get("content") or [])
    print(f"CASE {label} | isError={bool(res.get('isError'))} | text={text[:300]}")
proc.stdin.close()  # type: ignore[union-attr]
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.terminate()
    proc.wait(timeout=10)
time.sleep(0.2)
over = [l.rstrip() for l in errs if "OverflowError" in l]
print(f"MCP server stderr lines naming OverflowError: {len(over)}" + (f" (first: {over[0][:200]})" if over else ""))
