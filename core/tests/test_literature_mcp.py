"""The kit's MCP server (literature_mcp.py): it acts in the project --project
names, a refusal of the kit's service reaches the client in its words, and the
kit's two concept graph tools are served under their names and arguments,
each reading through the service, which reads the project's graph alone
(test_literature_graph.py holds two projects' graphs apart through them).

The MCP SDK hands a client only "Error executing tool <name>" for an exception
other than its ToolError (seen 2026-10-30: corpus_stats asked of a server
started with no project, and again with the database down, since the kit's
stats query the database before they ask for a project). The service here is a
stand-in that refuses or fails as the kit's ProjectService does; the server is
the kit's, built as main() builds it.
"""
from __future__ import annotations

import asyncio
import json
import os

import pytest
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from sci_rag.domain import load_domain
from sci_rag.server.errors import ApiError
from sci_rag.server.mcp_server import build_mcp_server

from openferment_core import literature_mcp, projects
from openferment_core.literature import DOMAIN_DIR, graph

NO_PROJECT = ApiError(422, "project_required", "No project named",
                      f"Name the project in the {projects.HEADER} header, or set {projects.ENV} for a command.")
NO_DOCUMENT = ApiError(404, "document_not_found", "No such document", "d-unknown")


class Refusing:
    """A service that refuses every read with one of the kit's errors."""

    domain = load_domain(DOMAIN_DIR)

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def stats(self):
        raise self.error

    async def search_entities(self, *args, **kwargs):
        raise self.error

    async def entity_relationships(self, *args, **kwargs):
        raise self.error

    async def retrieve(self, *args, **kwargs):
        raise self.error

    async def get_document(self, *args, **kwargs):
        raise self.error

    def answer_stream(self, *args, **kwargs):
        async def events():
            raise self.error
            yield

        return events()


def _refused(server, tool: str, arguments: dict) -> ToolError:
    with pytest.raises(ToolError) as e:
        asyncio.run(server.call_tool(tool, arguments))
    assert not isinstance(e.value, UnexpectedToolError), "a refusal is anticipated, and keeps its words"
    return e.value


@pytest.mark.parametrize("tool, arguments", [
    ("corpus_stats", {}),
    ("list_sources", {}),
    ("search_corpus", {"query": "ethanol yield"}),
    ("answer_question", {"query": "What was the ethanol yield?"}),
    ("search_entities", {"name_contains": "placeholder"}),
    ("get_entity_relationships", {"entity_name": "placeholder"}),
])
def test_a_server_acting_in_no_project_says_so_in_words(tool, arguments):
    refused = _refused(literature_mcp.build(Refusing(NO_PROJECT)), tool, arguments)
    assert literature_mcp.NO_PROJECT in str(refused)


def test_a_document_the_project_does_not_hold_is_refused_in_words():
    refused = _refused(literature_mcp.build(Refusing(NO_DOCUMENT)), "get_document", {"document_id": "d-unknown"})
    assert "No such document: d-unknown" in str(refused)


def test_the_graph_tools_are_served_under_the_kits_names_and_arguments_for_the_project():
    ours = {t.name: t for t in asyncio.run(literature_mcp.build(literature_mcp.Unopened()).list_tools())}
    kits, _ = build_mcp_server(literature_mcp.Unopened())
    theirs = {t.name: t for t in asyncio.run(kits.list_tools())}
    assert set(ours) == set(theirs) >= {"search_corpus", "answer_question", "get_document", "get_citations",
                                        "list_sources", "corpus_stats", *literature_mcp.SCOPED}
    domain = load_domain(DOMAIN_DIR).config
    for name in literature_mcp.SCOPED:
        assert ours[name].input_schema == theirs[name].input_schema, name
        assert ours[name].description != theirs[name].description and "this project's" in ours[name].description
    assert all(f"`{t.name}`" in ours["search_entities"].description for t in domain.entity_types)
    assert all(f"`{t.name}`" in ours["get_entity_relationships"].description for t in domain.relation_types)


class Answering:
    """A service whose graph reads answer, and whose store a tool must not
    open itself (the kit's own two tools query `session_factory`)."""

    domain = load_domain(DOMAIN_DIR)

    def __init__(self, entities: dict, edges: dict) -> None:
        self.entities, self.edges, self.asked = entities, edges, []

    def session_factory(self):
        raise AssertionError("a graph tool opened the store itself")

    async def search_entities(self, name_contains, entity_type=None, limit=20):
        self.asked.append(("search_entities", name_contains, entity_type, limit))
        return self.entities

    async def entity_relationships(self, entity_name):
        self.asked.append(("entity_relationships", entity_name))
        return self.edges


def _answer(server, tool: str, arguments: dict) -> dict:
    return json.loads(asyncio.run(server.call_tool(tool, arguments)).content[0].text)


def test_the_graph_tools_read_through_the_service():
    entities = {"entities": [{"name": "organism-placeholder", "type": "Organism", "description": None,
                              "evidence_chunk_count": 1}]}
    edges = {"entity": "organism-placeholder", "found": True, "type": "Organism", "relationships": []}
    service = Answering(entities, edges)
    server = literature_mcp.build(service)
    with projects.using("p-lit"):
        assert _answer(server, "search_entities", {"name_contains": "organism", "entity_type": "Organism",
                                                   "limit": 5}) == entities
        assert _answer(server, "get_entity_relationships", {"entity_name": "organism-placeholder"}) == edges
    assert service.asked == [("search_entities", "organism", "Organism", 5),
                             ("entity_relationships", "organism-placeholder")]


def test_a_project_no_build_has_read_is_refused_with_the_command_that_builds_its_graph():
    with projects.using("p-lit"):
        words = graph.no_graph("p-lit")
        server = literature_mcp.build(Answering({"entities": [], "note": words},
                                                {"entity": "x", "found": False, "hint": words}))
        for tool, arguments in (("search_entities", {"name_contains": ""}),
                                ("get_entity_relationships", {"entity_name": "x"})):
            assert str(_refused(server, tool, arguments)).endswith(f": {words}")
        assert "pnpm lit:graph --project p-lit" in words
        # Words about the graph a build has read stay an answer.
        partly = {"entities": [], "note": "No entity is named in this project's passages."}
        assert _answer(literature_mcp.build(Answering(partly, {})), "search_entities", {"name_contains": ""}) == partly


def test_a_server_built_to_list_its_tools_opens_nothing():
    with pytest.raises(AttributeError, match="serves no session_factory"):
        literature_mcp.Unopened().session_factory


def test_the_server_acts_in_the_project_its_command_names(monkeypatch):
    # The service reads the project from OPENFERMENT_PROJECT in the server's process.
    monkeypatch.delenv(projects.ENV, raising=False)
    assert literature_mcp.act_in(["--project", "p-lit"]) == "p-lit"
    assert os.environ[projects.ENV] == "p-lit"
    monkeypatch.delenv(projects.ENV, raising=False)
    assert literature_mcp.act_in([]) is None and projects.ENV not in os.environ


DOWN = ConnectionRefusedError(111, "Connect call failed ('127.0.0.1', 5432)")


def test_a_server_acting_in_no_project_says_so_before_it_reaches_the_database():
    with projects.using(None):
        refused = _refused(literature_mcp.build(Refusing(DOWN)), "corpus_stats", {})
    assert literature_mcp.NO_PROJECT in str(refused)


@pytest.mark.parametrize("tool, arguments", [
    ("corpus_stats", {}),
    ("answer_question", {"query": "What was the ethanol yield?"}),
    ("search_entities", {"name_contains": "placeholder"}),
])
def test_a_database_that_does_not_answer_is_said_in_words(tool, arguments):
    refused = _refused(literature_mcp.build(Refusing(DOWN)), tool, arguments)
    assert "The kit's service failed: ConnectionRefusedError" in str(refused) and "5432" in str(refused)
