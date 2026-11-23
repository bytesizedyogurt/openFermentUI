"""H13: the `openferment` MCP server started as docs/TOOLS.md ("Starting it", "A client") says, in each
of its modes, and the claims those lines make, each checked by a call.

Usage, from a checkout's root, in core's environment (TOOLS.md: "A client runs in core's environment"):
    uv run --project core --all-extras python <this file> --service http://127.0.0.1:<port> --project <id>
OPENFERMENT_DATABASE_URL must name the service's own database for the own-process mode.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.request
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation

ROOT = Path.cwd()


def params(*extra: str) -> StdioServerParameters:
    declared = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["openferment"]
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    return StdioServerParameters(command=declared["command"], args=[*declared["args"], *extra], cwd=str(ROOT), env=env)


async def one(label: str, p: StdioServerParameters, tool: str, args: dict, client_info: Implementation | None):
    async with stdio_client(p) as (r, w):
        kw = {"client_info": client_info} if client_info else {}
        async with ClientSession(r, w, **kw) as s:
            await s.initialize()
            res = await s.call_tool(tool, args)
            text = "".join(getattr(b, "text", "") for b in res.content)
            print(f"== {label}\n   is_error={res.is_error} structured={res.structured_content is not None}\n   {text[:600]}")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}


def audit(service: str, project: str, query: str = "") -> list[dict]:
    req = urllib.request.Request(f"{service}/api/audit{query}", headers={"X-OpenFerment-Project": project})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=30) as resp:
        return json.load(resp)


def entry(eid: str, name: str) -> dict:
    return {"kind": "skill", "id": eid, "name": name, "summary": "A placeholder.", "note": "A placeholder; stands for nothing."}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", required=True)
    ap.add_argument("--project", required=True)
    a = ap.parse_args()
    svc, proj = a.service, a.project

    # 1. A client that declares no name, through the service: TOOLS.md says it is marked `an assistant over MCP`.
    got = await one("nameless client through the service", params("--project", proj, "--service", svc),
                    "catalogue_write", entry("h13-nameless-svc", "A placeholder skill"), None)
    print("   by:", (got.get("summary") or {}).get("by"), "| source:", (got.get("summary") or {}).get("source"))
    # 2. The same in the server's own process.
    got = await one("nameless client in the server's own process", params("--project", proj),
                    "catalogue_write", entry("h13-nameless-own", "A placeholder skill"), None)
    print("   by:", (got.get("summary") or {}).get("by"), "| source:", (got.get("summary") or {}).get("source"))
    # 3. A named client in the server's own process: source `<name>/<version>, over MCP`, door mcp.
    got = await one("named client in its own process", params("--project", proj),
                    "catalogue_write", entry("h13-named-own", "A placeholder skill"), Implementation(name="h13-probe", version="0.1"))
    s = got.get("summary") or {}
    print("   by:", s.get("by"), "| via:", s.get("via"), "| source:", s.get("source"), "| auditIds:", got.get("auditIds"))
    # 4. An origin outside the rule: refused in words at start, every call answering with them.
    for bad in ("http://127.0.0.1", "http://example.org:80", "http://127.0.0.1:8930/api", "ftp://127.0.0.1:8930"):
        await one(f"origin {bad}", params("--project", proj, "--service", bad), "catalogue_read",
                  {"kind": "skill", "words": "", "limit": 5}, Implementation(name="h13-probe", version="0.1"))
    # 5. No project: every call answers in words.
    env_project = os.environ.pop("OPENFERMENT_PROJECT", None)
    await one("no project, through the service", params("--service", svc), "catalogue_read",
              {"kind": "skill", "words": "", "limit": 5}, Implementation(name="h13-probe", version="0.1"))
    if env_project:
        os.environ["OPENFERMENT_PROJECT"] = env_project
    # 6. The audit's filters and limits as TOOLS.md names them.
    rows = audit(svc, proj)
    print("== audit: rows", len(rows), "newest last:", [r.get("target") for r in rows][-4:])
    for q in ("?action=catalogue_write&target=skill/h13-named-own&who=h13-probe/0.1", "?limit=1", "?limit=600", "?limit=0"):
        try:
            got = audit(svc, proj, q)
            print(f"== audit{q}: {len(got)} rows", [(r.get('who'), r.get('target')) for r in got][:3])
        except urllib.error.HTTPError as e:
            print(f"== audit{q}: HTTP {e.code} {e.read().decode()[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
