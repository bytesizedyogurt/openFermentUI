#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2.3,<3"]
# ///
"""record-reader: a small client of openFerment's `openferment` MCP server.

It starts the server `.mcp.json` declares, in the project named and through the
running service named; lists the project's records with `biorepo_read`; keeps
one placeholder skill with `catalogue_write`, connected as `example-agent/0.1`;
then reads back what the service recorded about who made that write: the
write's own answer, the entry as `catalogue_read` reads it, and the write's row
in the service's audit log (`GET /api/audit`, which no tool reads). It prints
what it found.

From the repository's root, in an environment of its own (the header above):

    uv run examples/agents/record-reader/record_reader.py \\
        --project proof --service http://127.0.0.1:<port>

or in core's: `uv run --project core --all-extras python <this file> ...`.
`--root` names another checkout whose `.mcp.json` and `core` start the server.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation

ROOT = Path(__file__).resolve().parents[3]  # examples/agents/record-reader/ is three below the root

CLIENT = Implementation(name="example-agent", version="0.1")
WHO = f"{CLIENT.name}/{CLIENT.version}"  # the name the service keeps this client's writes under

# A placeholder, under an id of its own that starts with the client's name, its
# "/" written as "." (docs/TOOLS.md, catalogue_write). Words only: it names no
# real strain, species or product, since the repository ships software alone.
ENTRY = {
    "kind": "skill",
    "id": "example-agent.0.1-a-skill",
    "name": "A placeholder skill",
    "summary": "A placeholder the record-reader example keeps, to show whom the service records as its author.",
    "note": "A placeholder: it rests on no document or record and stands for nothing.",
}
TARGET = f"{ENTRY['kind']}/{ENTRY['id']}"  # how the audit row names what was written


class Refused(Exception):
    """A refusal in words: a tool's `error`, the server's own, or the service's."""


def server_parameters(root: Path, project: str, service: str) -> StdioServerParameters:
    """The `openferment` server as `.mcp.json` declares it, with the project and the service named."""
    declared = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["openferment"]
    env = dict(os.environ)  # uv needs the proxy variables; the SDK alone would pass a handful of names
    env.pop("VIRTUAL_ENV", None)  # this script's own environment, which uv would warn of and ignore
    return StdioServerParameters(
        command=declared["command"],
        args=[*declared["args"], "--project", project, "--service", service],
        cwd=str(root),
        env=env,
    )


async def call(session: ClientSession, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run one tool. Its answer is one text block of JSON; a refusal has `error` set."""
    result = await session.call_tool(tool, arguments)
    text = "".join(getattr(block, "text", "") for block in result.content)
    try:
        answer = json.loads(text)
    except json.JSONDecodeError:
        answer = None
    if not isinstance(answer, dict):
        raise Refused(f"{tool} answered with no JSON object: {text[:400]!r}")
    if result.is_error or answer.get("error"):
        raise Refused(f"{tool}: {answer.get('error') or text}")
    return answer


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None  # a redirect comes back as the error it is; the project header goes nowhere else


def read_audit(service: str, project: str) -> list[dict[str, Any]]:
    """The project's newest audit rows, newest last, read at the service itself."""
    request = urllib.request.Request(
        f"{service}/api/audit", headers={"X-OpenFerment-Project": project, "Accept": "application/json"}
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)  # loopback, no proxy
    try:
        with opener.open(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise Refused(f"GET /api/audit: {error.code} {error.read().decode('utf-8', 'replace')}") from None
    except urllib.error.URLError as error:
        raise Refused(f"GET /api/audit: the service did not answer ({error.reason})") from None


def show_records(answer: dict[str, Any]) -> None:
    summary = answer.get("summary", {})
    rows = answer.get("rows") or summary.get("rows") or []
    count = summary.get("count", len(rows))
    states = ", ".join(f"{state} {n}" for state, n in sorted((summary.get("states") or {}).items()))
    print("\nRecords (biorepo_read, kind record): " + (
        f"{count} in the project, {summary.get('returned', len(rows))} returned; by state: {states}" if count
        else "none in the project"))
    for row in rows:
        label = " ".join(str(row.get("label", "")).split())
        label = label if len(label) <= 96 else label[:95] + "…"
        print(f"  {row.get('ref', row.get('id', '?'))}  [{row.get('state', '?')} · {row.get('status', '?')} · "
              f"{row.get('provenance') or 'no provenance'}]  {label}")
    for key in ("note", "partial"):
        if summary.get(key):
            print(f"  {key}: {summary[key]}")


def show_fields(title: str, fields: dict[str, Any], keys: tuple[str, ...]) -> None:
    print(f"\n{title}")
    for key in keys:
        if key in fields:
            value = fields[key]
            print(f"  {key:<8} {value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)}")


async def run(root: Path, project: str, service: str) -> int:
    params = server_parameters(root, project, service)
    print(f"Starting the openferment MCP server that {root / '.mcp.json'} declares:")
    print(f"  {params.command} {' '.join(params.args)}")
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write, client_info=CLIENT) as session,
    ):
        await session.initialize()  # mcp 2.3 sends the handshake here; a call before it is refused
        tools = {tool.name for tool in (await session.list_tools()).tools}
        print(f"  connected as {WHO}; the server lists {len(tools)} tools")
        missing = sorted({"biorepo_read", "catalogue_write", "catalogue_read"} - tools)
        if missing:
            print(f"Refused: the server lists no {', '.join(missing)}", file=sys.stderr)
            return 1
        try:
            records = await call(
                session, "biorepo_read", {"ids": [], "words": "", "kind": "record", "state": "", "limit": 20}
            )
            show_records(records)
            kept = (await call(session, "catalogue_write", ENTRY)).get("summary", {})
            show_fields(f"The write (catalogue_write): {TARGET}", kept,
                        ("by", "agent", "via", "source", "at", "state", "meaning"))
            catalogue = (await call(
                session, "catalogue_read", {"kind": ENTRY["kind"], "words": ENTRY["id"], "limit": 40}
            )).get("summary", {})
        except Refused as refusal:
            print(f"Refused: {refusal}", file=sys.stderr)
            return 1
    entry = next((e for e in catalogue.get("entries", []) if e.get("id") == ENTRY["id"]), None)
    if entry is None:
        print(f"Refused: catalogue_read holds no {TARGET} ({catalogue.get('matched', 0)} matched)", file=sys.stderr)
        return 1
    show_fields("Read back, the entry as kept (catalogue_read):", entry, ("by", "agent", "via", "source", "at"))
    try:
        audit = read_audit(service, project)
    except Refused as refusal:
        print(f"Refused: {refusal}", file=sys.stderr)
        return 1
    writes = [row for row in audit if row.get("action") == "catalogue_write" and row.get("target") == TARGET]
    if not writes:
        print(f"Refused: the newest {len(audit)} audit rows hold no catalogue_write of {TARGET}", file=sys.stderr)
        return 1
    row = writes[-1]  # newest last
    show_fields(f"Read back, the audit row (GET /api/audit, the newest of {len(writes)} for {TARGET}):", row,
                ("at", "who", "agent", "module", "action", "state", "target", "detail", "effort", "askId"))
    via = (row.get("detail") or {}).get("via")
    agrees = entry.get("by") == WHO and row.get("who") == WHO and entry.get("via") == via
    print(f"\nWho made the write, as the service recorded it: {row.get('who')} (agent {row.get('agent')}, "
          f"door {via}); the entry says {entry.get('by')} (agent {entry.get('agent')}, door {entry.get('via')})"
          f" — {'they agree with' if agrees else 'they differ from'} the name declared, {WHO}.")
    return 0 if agrees else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="List a project's records, keep one placeholder catalogue entry "
                                     f"as {WHO}, and read back who the service recorded as its author.")
    parser.add_argument("--project", default=os.environ.get("OPENFERMENT_PROJECT"),
                        required=not os.environ.get("OPENFERMENT_PROJECT"),
                        help="the project the server acts in (default: OPENFERMENT_PROJECT)")
    parser.add_argument("--service", required=True,
                        help="the running service's own address, http://127.0.0.1:<port>")
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="the checkout whose .mcp.json and core start the server (default: this file's)")
    args = parser.parse_args()
    return asyncio.run(run(args.root.resolve(), args.project, args.service.rstrip("/")))


if __name__ == "__main__":
    sys.exit(main())
