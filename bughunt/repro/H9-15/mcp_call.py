"""H9-15: the openferment MCP server in its own process, over raw JSON-RPC lines on stdio.
A registry tool (literature_document, its `document` a required string) and the server's two
tools of its own (ask_postdoc, get_artifact) are each sent a missing and a mistyped argument.

    bh_py /home/user/openFermentUI/bughunt/repro/H9-15/mcp_call.py DBURL PROJECT

Prints one line per case: CASE <group> <tool> <label> | isError=<bool> | text=<the result's text>.
<group> is CONTROL (the registry tool, and get_artifact with a string id of no artifact's
shape) or PROBE (ask_postdoc and get_artifact with the argument missing or not a string).
No case can reach a model: the server's environment holds no key, and its proxy is a dead
loopback port, so a request to any outside host would fail at once.
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
env.update({"OPENFERMENT_DATABASE_URL": DBURL, "ANTHROPIC_API_KEY": "",
            "HTTPS_PROXY": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9",
            "https_proxy": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9",
            "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"})
proc = subprocess.Popen([f"{CORE}/.venv/bin/python", "-m", "openferment_core.mcp_server", "--project", PROJECT],
                        cwd=CORE, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, bufsize=1)
lines: list[str] = []
cv = threading.Condition()


def reader() -> None:
    for line in proc.stdout:  # type: ignore[union-attr]
        with cv:
            lines.append(line)
            cv.notify_all()


threading.Thread(target=reader, daemon=True).start()
threading.Thread(target=lambda: [None for _ in proc.stderr], daemon=True).start()  # type: ignore[union-attr]
ids = iter(range(1, 10**9))


def call(method: str, params_raw: str, timeout: float = 120) -> dict:
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
                               "clientInfo": {"name": "h9-15-raw-client", "version": "1.0"}}))
proc.stdin.write('{"jsonrpc": "2.0", "method": "notifications/initialized"}\n')  # type: ignore[union-attr]
proc.stdin.flush()  # type: ignore[union-attr]

CASES = [
    ("CONTROL", "literature_document", "no document", "{}"),
    ("CONTROL", "literature_document", "document=7", '{"document": 7}'),
    ("CONTROL", "literature_document", "document=null", '{"document": null}'),
    ("CONTROL", "get_artifact", "id=\"zz\" (a string of no artifact's shape)", '{"id": "zz"}'),
    ("PROBE", "ask_postdoc", "no question", "{}"),
    ("PROBE", "ask_postdoc", "question=7", '{"question": 7}'),
    ("PROBE", "ask_postdoc", "question=null", '{"question": null}'),
    ("PROBE", "get_artifact", "no id", "{}"),
    ("PROBE", "get_artifact", "id=7", '{"id": 7}'),
    ("PROBE", "get_artifact", "id=null", '{"id": null}'),
]
for group, tool, label, raw in CASES:
    msg = call("tools/call", f'{{"name": "{tool}", "arguments": {raw}}}')
    head = f"CASE {group} {tool} {label}"
    if msg.get("timeout"):
        print(f"{head} | no answer")
        continue
    if "error" in msg:
        print(f"{head} | JSON-RPC error {json.dumps(msg['error'])[:300]}")
        continue
    res = msg.get("result") or {}
    text = "".join(c.get("text", "") for c in res.get("content") or [])
    try:
        body = json.loads(text)
        shape = "JSON keys=" + ",".join(sorted(body)) if isinstance(body, dict) else "JSON non-object"
    except ValueError:
        shape = "no JSON"
    flat = text.replace("\n", " \\n ")
    print(f"{head} | isError={bool(res.get('isError'))} | {shape} | text={flat[:330]}")
proc.stdin.close()  # type: ignore[union-attr]
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.terminate()
    proc.wait(timeout=10)
