"""H9: every gated write through three doors (REST as a person, REST with the assistant
header, the MCP server in its own process), then GET /api/audit: each row must name who
and the door.

    bh_py ../bughunt/notes/H9/scripts/gated_audit.py ORIGIN PROJECT DBURL OUT.json
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx

ORIGIN, PROJECT, DBURL, OUT = sys.argv[1:5]
CORE = "/home/user/openFermentUI/core"
sys.path.insert(0, CORE)
from openferment_core.tools import gates, writes  # noqa: E402

http = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=120)
H = {"X-OpenFerment-Project": PROJECT}

pairs = [(m, a) for g in gates.GATES for (m, a) in g.actions]


def args_for(module: str, action: str, tag: str) -> dict:
    _, needs = writes.ACTIONS[module][action]
    fields = {n: f"{tag}-{n.replace('.', '-')}" for n in needs if "<" not in n}
    # A target an id, distinct by door so no proposal is a twin of another door's.
    return {"action": action, "target": f"tgt-{module}-{action}-{tag}", "fields": fields, "note": f"why from {tag}"}


results = []
for module, action in pairs:
    name = f"{module}_write"
    r = http.post(f"/api/tools/{name}", params={"by": "Alice Person"}, json=args_for(module, action, "rest"),
                  headers=H).json()
    results.append({"door": "rest-person", "tool": name, "action": action, "result": r})
    r = http.post(f"/api/tools/{name}", json=args_for(module, action, "http"),
                  headers={**H, "X-OpenFerment-Assistant": "fuzzbot/1.0"}).json()
    results.append({"door": "rest-assistant", "tool": name, "action": action, "result": r})


async def mcp_calls() -> list[dict]:
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client

    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env.update({"OPENFERMENT_DATABASE_URL": DBURL, "ANTHROPIC_API_KEY": ""})
    params = StdioServerParameters(command=f"{CORE}/.venv/bin/python", cwd=CORE, env=env,
                                   args=["-m", "openferment_core.mcp_server", "--project", PROJECT])
    out = []
    async with stdio_client(params) as (read, write), ClientSession(
            read, write, client_info=types.Implementation(name="mcpbot", version="2.0")) as session:
        await session.initialize()
        for module, action in pairs:
            got = await session.call_tool(f"{module}_write", args_for(module, action, "mcp"))
            text = got.content[0].text if got.content else ""
            try:
                body = json.loads(text)
            except ValueError:
                body = {"raw": text, "isError": got.isError}
            out.append({"door": "mcp", "tool": f"{module}_write", "action": action, "result": body})
    return out


results += asyncio.run(asyncio.wait_for(mcp_calls(), timeout=300))

audit = http.get("/api/audit", params={"limit": 500}, headers=H).json()
by_id = {row["id"]: row for row in audit}
expect = {"rest-person": ("person", "Alice Person", None), "rest-assistant": ("model", "fuzzbot/1.0", "http"),
          "mcp": ("model", "mcpbot/2.0", "mcp")}
report = []
for res in results:
    r = res["result"]
    ids = r.get("auditIds") or []
    rows = [by_id.get(i) for i in ids]
    agent, who, via = expect[res["door"]]
    problems = []
    if (r.get("summary") or {}).get("state") != "proposed":
        problems.append(f"not proposed: {r.get('error') or r}")
    if not ids:
        problems.append("no auditIds")
    for row in rows:
        if row is None:
            problems.append("an auditId GET /api/audit does not serve")
            continue
        if row.get("agent") != agent or row.get("who") != who:
            problems.append(f"row names {row.get('agent')}/{row.get('who')}")
        if (row.get("detail") or {}).get("via") != via:
            problems.append(f"row's via is {(row.get('detail') or {}).get('via')}")
        if via and row.get("effort"):
            problems.append(f"row carries effort {row.get('effort')}")
    report.append({**{k: res[k] for k in ("door", "tool", "action")}, "auditIds": ids, "rows": rows,
                   "problems": problems, "error": r.get("error")})
    print(res["door"], res["tool"], res["action"], "OK" if not problems else problems)
json.dump(report, open(OUT, "w"), indent=1)
