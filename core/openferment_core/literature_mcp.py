"""Sci RAG Kit's MCP server, over stdio, for one project (ADR-002).

    uv run --project core --all-extras python -m openferment_core.literature_mcp

`.mcp.json` at the repository root starts it beside openFerment's own. Its
tools are the kit's (search the corpus, answer with citations, read a
document and its citations, the concept graph's entities and relationships,
the corpus's sources and size), served by `kit.ProjectService`, so every read
stays inside the project OPENFERMENT_PROJECT names. Like openFerment's own
server it reads the database address and the project from core/.env when the
environment lacks them, and nothing else: an answer needs the model, which
llm.py reaches only with a key in the environment. It lives outside
`literature/` because it installs llm.py's client, which `literature/` does
not import (§7.2).
"""
from __future__ import annotations

from . import llm, mcp_server
from .literature import kit


def main() -> None:
    mcp_server._settings()
    kit.install_model(llm.kit_client)
    from sci_rag.server.mcp_server import build_mcp_server

    server, _tools = build_mcp_server(kit.service("free"))
    server.run("stdio")


if __name__ == "__main__":
    main()
