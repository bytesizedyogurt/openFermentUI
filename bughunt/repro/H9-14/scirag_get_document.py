"""H9-14: the sci-rag MCP server in its own process, over JSON-RPC lines on stdio, asked
get_document for an id holding a NUL and for an id of no document.

    bh_py /home/user/openFermentUI/bughunt/repro/H9-14/scirag_get_document.py DBURL PROJECT

Prints one line a case: CASE <name> <the tool's text, its newlines written \\n>.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

DBURL, PROJECT = sys.argv[1:3]
CORE = "/home/user/openFermentUI/core"
env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
env.update({"OPENFERMENT_DATABASE_URL": DBURL, "ANTHROPIC_API_KEY": ""})
proc = subprocess.Popen([f"{CORE}/.venv/bin/python", "-m", "openferment_core.literature_mcp", "--project", PROJECT],
                        cwd=CORE, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL, text=True, bufsize=1)
rid = 0


def call(method: str, params: dict) -> dict:
    global rid
    rid += 1
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}) + "\n")
    proc.stdin.flush()
    for line in proc.stdout:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("id") == rid:
            return msg
    raise SystemExit("the server closed its output")


try:
    call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "h9-14-repro", "version": "0.1"}})
    proc.stdin.write('{"jsonrpc": "2.0", "method": "notifications/initialized"}\n')
    proc.stdin.flush()
    for case, doc in (("unknown", "no-such-document"), ("nul", "a\u0000b")):
        msg = call("tools/call", {"name": "get_document", "arguments": {"document_id": doc}})
        res = msg.get("result") or {}
        text = " ".join(c.get("text", "") for c in res.get("content", [])) or json.dumps(msg.get("error"))
        print(f"CASE {case} isError={res.get('isError')} {text}".replace("\n", "\\n"))
finally:
    proc.stdin.close()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
