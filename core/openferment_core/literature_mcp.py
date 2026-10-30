"""Sci RAG Kit's MCP server, over stdio, for one project (ADR-002).

    uv run --project core --all-extras python -m openferment_core.literature_mcp [--project <id>]

`.mcp.json` at the repository root starts it beside openFerment's own. Its
tools are the kit's (search the corpus, answer with citations, read a
document and its citations, the corpus's sources and size), served by
`kit.ProjectService`, so every read stays inside the project `--project`
names, else OPENFERMENT_PROJECT. The kit's two tools that read its concept
graph whole, across every project's documents (`UNSCOPED`), are left off.
Like openFerment's own server it reads the database address and the project
from core/.env when the environment lacks them, and nothing else: an answer
needs the model, which llm.py reaches only with a key in the environment. It
lives outside `literature/` because it installs llm.py's client, which
`literature/` does not import (§7.2).

A refusal of the kit's service (no project named, a document the project does
not hold) reaches the client in its words: the MCP SDK hands a client only
"Error executing tool <name>" for an exception other than its `ToolError`,
so `InWords` raises the service's refusals as one.
"""
from __future__ import annotations

import functools
import inspect
import os
from typing import Any, AsyncIterator

from mcp.server.mcpserver.exceptions import ToolError
from sci_rag.server.errors import ApiError

from . import llm, mcp_server, projects
from .literature import kit

NO_PROJECT = ("This Sci RAG Kit server acts in no project. Start it with --project <id>, or set OPENFERMENT_PROJECT "
              "(in the environment or core/.env) to the project's id.")
#: The kit's tools that read its concept graph whole, every project's
#: documents' entities, relationships and evidence quotes (ADR-002: the graph
#: is the instance's). A server that acts in one project leaves them off.
UNSCOPED = ("search_entities", "get_entity_relationships")


def _words(e: ApiError) -> str:
    if e.code == "project_required":
        return NO_PROJECT
    return f"{e.title}: {e.detail}" if e.detail else e.title


class InWords:
    """The kit's service as its MCP tools call it: each refusal it raises
    reaches the client as a `ToolError` in its words."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def __getattr__(self, name: str) -> Any:
        found = getattr(self._service, name)
        if inspect.iscoroutinefunction(found):
            @functools.wraps(found)
            async def call(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await found(*args, **kwargs)
                except ApiError as e:
                    raise ToolError(_words(e)) from e

            return call
        if name == "answer_stream":
            # A stream refuses as it starts or once it is read.
            @functools.wraps(found)
            def stream(*args: Any, **kwargs: Any) -> AsyncIterator[Any]:
                try:
                    events = found(*args, **kwargs)
                except ApiError as e:
                    raise ToolError(_words(e)) from e

                async def each() -> AsyncIterator[Any]:
                    try:
                        async for event in events:
                            yield event
                    except ApiError as e:
                        raise ToolError(_words(e)) from e

                return each()

            return stream
        return found


def act_in(argv: list[str] | None = None) -> str | None:
    """The project this server acts in (`--project <id>`, else
    OPENFERMENT_PROJECT), set for the process the kit's service reads it in."""
    project = mcp_server.named_project(argv)
    if project:
        os.environ[projects.ENV] = project
    return project


def build(service: Any) -> Any:
    """The kit's MCP server over `service`, its refusals in words and its
    unscoped tools left off."""
    from sci_rag.server.mcp_server import build_mcp_server

    server, _tools = build_mcp_server(InWords(service))
    for name in UNSCOPED:
        server.remove_tool(name)
    return server


def main() -> None:
    mcp_server._settings()
    act_in()
    kit.install_model(llm.kit_client)
    build(kit.service("free")).run("stdio")


if __name__ == "__main__":
    main()
