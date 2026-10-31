"""The kit's MCP server (literature_mcp.py): it acts in the project --project
names, a refusal of the kit's service reaches the client in its words, and the
kit's tools that read the concept graph whole are left off.

The MCP SDK hands a client only "Error executing tool <name>" for an exception
other than its ToolError (seen 2026-10-30: corpus_stats asked of a server
started with no project, and again with the database down, since the kit's
stats query the database before they ask for a project). The service here is a
stand-in that refuses or fails as the kit's ProjectService does; the server is
the kit's, built as main() builds it.
"""
from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from sci_rag.server.errors import ApiError

from openferment_core import literature_mcp, projects

NO_PROJECT = ApiError(422, "project_required", "No project named",
                      f"Name the project in the {projects.HEADER} header, or set {projects.ENV} for a command.")
NO_DOCUMENT = ApiError(404, "document_not_found", "No such document", "d-unknown")


class Refusing:
    """A service that refuses every read with one of the kit's errors."""

    domain = SimpleNamespace(name="openFerment bioprocess literature", config=SimpleNamespace(description=""))

    def __init__(self, error: ApiError) -> None:
        self.error = error

    async def stats(self):
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
])
def test_a_server_acting_in_no_project_says_so_in_words(tool, arguments):
    refused = _refused(literature_mcp.build(Refusing(NO_PROJECT)), tool, arguments)
    assert literature_mcp.NO_PROJECT in str(refused)


def test_a_document_the_project_does_not_hold_is_refused_in_words():
    refused = _refused(literature_mcp.build(Refusing(NO_DOCUMENT)), "get_document", {"document_id": "d-unknown"})
    assert "No such document: d-unknown" in str(refused)


def test_the_tools_that_read_the_graph_whole_are_left_off():
    listed = {t.name for t in asyncio.run(literature_mcp.build(Refusing(NO_PROJECT)).list_tools())}
    assert listed.isdisjoint(literature_mcp.UNSCOPED)
    assert {"search_corpus", "answer_question", "get_document", "get_citations", "list_sources",
            "corpus_stats"} <= listed


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
])
def test_a_database_that_does_not_answer_is_said_in_words(tool, arguments):
    refused = _refused(literature_mcp.build(Refusing(DOWN)), tool, arguments)
    assert "The kit's service failed: ConnectionRefusedError" in str(refused) and "5432" in str(refused)
