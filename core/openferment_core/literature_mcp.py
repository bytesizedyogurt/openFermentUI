"""Sci RAG Kit's MCP server, over stdio, for one project (ADR-002).

    uv run --project core --all-extras python -m openferment_core.literature_mcp [--project <id>]

`.mcp.json` at the repository root starts it beside openFerment's own. Its
tools are the kit's (search the corpus, answer with citations, read a
document and its citations, the corpus's sources and size), served by
`kit.ProjectService`, so every read stays inside the project `--project`
names, else OPENFERMENT_PROJECT. The kit's two tools that read its concept
graph (`SCOPED`) query the store whole, every project's entities and edges,
so the server removes them and adds openFerment's own under the same names
and arguments, each reading the project's graph alone through the service
(`literature/graph.py`) and refusing in words a project whose passages no
build has read, with the command that builds its graph.
Like openFerment's own server it reads the database address and the project
from core/.env when the environment lacks them, and nothing else: an answer
needs the model, which llm.py reaches only with a key in the environment. It
lives outside `literature/` because it installs llm.py's client, which
`literature/` does not import (§7.2).

Every failure reaches the client in words, as openFerment's own server says
its own: the MCP SDK hands a client only "Error executing tool <name>" for an
exception other than its `ToolError`. `InWords` asks for a project before the
service is called, so that refusal holds with the database down too, and raises
the service's refusals (a document the project does not hold) and its failures
(a database that does not answer) as a `ToolError` in their words.
"""
from __future__ import annotations

import functools
import inspect
import os
from typing import Any, AsyncIterator

from mcp.server.mcpserver.exceptions import ToolError
from sci_rag.domain import load_domain
from sci_rag.server.errors import ApiError

from . import llm, mcp_server, projects
from .literature import DOMAIN_DIR, graph, kit

NO_PROJECT = ("This Sci RAG Kit server acts in no project. Start it with --project <id>, or set OPENFERMENT_PROJECT "
              "(in the environment or core/.env) to the project's id.")
#: The kit's tools that read its concept graph, which query the store whole,
#: every project's entities, relationships and evidence quotes. The server
#: serves openFerment's own under these names and arguments, each reading the
#: project's graph alone (`graph_tools`; ADR-002, Implementation F).
SCOPED = ("search_entities", "get_entity_relationships")


def _named() -> None:
    if projects.current_or_none() is None:
        raise ToolError(NO_PROJECT)


def _in_words(e: Exception) -> ToolError:
    if isinstance(e, ApiError):
        if e.code == "project_required":
            return ToolError(NO_PROJECT)
        return ToolError(f"{e.title}: {e.detail}" if e.detail else e.title)
    return ToolError(f"The kit's service failed: {type(e).__name__}: {e}")


class InWords:
    """The kit's service as its MCP tools call it: each call asks for a
    project first, and each refusal or failure reaches the client as a
    `ToolError` in its words."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def __getattr__(self, name: str) -> Any:
        found = getattr(self._service, name)
        if inspect.iscoroutinefunction(found):
            @functools.wraps(found)
            async def call(*args: Any, **kwargs: Any) -> Any:
                _named()
                try:
                    return await found(*args, **kwargs)
                except ToolError:
                    raise
                except Exception as e:
                    raise _in_words(e) from e

            return call
        if name == "answer_stream":
            # A stream refuses as it starts or once it is read.
            @functools.wraps(found)
            def stream(*args: Any, **kwargs: Any) -> AsyncIterator[Any]:
                _named()
                try:
                    events = found(*args, **kwargs)
                except Exception as e:
                    raise _in_words(e) from e

                async def each() -> AsyncIterator[Any]:
                    try:
                        async for event in events:
                            yield event
                    except ToolError:
                        raise
                    except Exception as e:
                        raise _in_words(e) from e

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


def _built(answer: dict[str, Any], key: str) -> dict[str, Any]:
    """`answer`, unless it says that no build has read the project's passages:
    then those words, as a refusal."""
    project = projects.current_or_none()
    if project is not None and answer.get(key) == graph.no_graph(project):
        raise ToolError(answer[key])
    return answer


def _kinds(specs: Any) -> str:
    return ", ".join(f"`{spec.name}`" for spec in specs)


def graph_tools(service: InWords) -> dict[str, tuple[Any, str]]:
    """The two graph tools as this server serves them, by name, each with its
    description: the kit's arguments, the reads `service` makes of the
    project's graph alone (`ProjectService.search_entities` and
    `entity_relationships`), a project with no graph refused in words."""
    domain = service.domain.config

    async def search_entities(name_contains: str, entity_type: str | None = None, limit: int = 20) -> dict[str, Any]:
        return _built(await service.search_entities(name_contains, entity_type, limit), "note")

    async def get_entity_relationships(entity_name: str) -> dict[str, Any]:
        return _built(await service.entity_relationships(entity_name), "hint")

    return {
        "search_entities": (search_entities, (
            "Look up the concept graph's entities by a part of their name (case aside), in this project's graph "
            "alone: an entity is listed where a passage of a document the project holds names it, with its type, "
            "its description where every document naming it is one the project holds, and the count of the "
            "project's passages that name it (`evidence_chunk_count`). A name the kit holds as an alias finds "
            f"nothing here. `entity_type` narrows the list to one of the domain's types: {_kinds(domain.entity_types)}. "
            "A project whose passages no build has read is refused in words naming the command that builds its "
            "graph.")),
        "get_entity_relationships": (get_entity_relationships, (
            "Show every stated relationship of one entity that this project's passages hold, each with its "
            "statement, its evidence quote where the quote's words stand in the passage it cites, its confidence, "
            "and the document and passage id (`p<index>`) it stands in. An edge is listed when its passage is the "
            "project's and both its ends are entities the project's passages name. The name is matched case aside "
            "and aliases are left out; search_entities lists the names. Its relation types are the domain's: "
            f"{_kinds(domain.relation_types)}. A project whose passages no build has read is refused in words "
            "naming the command that builds its graph.")),
    }


def build(service: Any) -> Any:
    """The kit's MCP server over `service`, its refusals in words, and its two
    graph tools served for the project alone (`graph_tools`)."""
    from sci_rag.server.mcp_server import build_mcp_server

    scoped = InWords(service)
    server, _tools = build_mcp_server(scoped)
    for name, (tool, description) in graph_tools(scoped).items():
        server.remove_tool(name)
        server.add_tool(tool, name=name, description=description)
    return server


class Unopened:
    """A service that holds the domain profile and opens nothing: the server
    built over it lists its tools as it serves them (tools/reference.py, the
    proof's step 3), and every call refuses."""

    def __init__(self) -> None:
        self.domain = load_domain(DOMAIN_DIR)

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"a server built to list its tools serves no {name}")


def main() -> None:
    mcp_server._settings()
    act_in()
    kit.install_model(llm.kit_client)
    build(kit.service("free")).run("stdio")


if __name__ == "__main__":
    main()
