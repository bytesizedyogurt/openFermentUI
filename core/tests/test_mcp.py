"""The MCP server (OF-BLD-014 §10.1): outside assistants reach the same
tools through the same rules."""
from __future__ import annotations

import asyncio
import json
import sys

import pytest

from openferment_core import intake, mcp_server, tools


@pytest.fixture()
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    return tmp_path


def _text(result) -> dict:
    return json.loads(result.content[0].text)


def test_the_server_lists_the_registry_with_its_schemas_and_the_two_e6_names():
    listed = asyncio.run(mcp_server.build().list_tools())
    names = [t.name for t in listed]
    assert names == [i.name for i in tools.infos()] + ["ask_postdoc", "get_artifact"]
    by_name = {t.name: t for t in listed}
    for info in tools.infos():
        assert by_name[info.name].input_schema == info.inputSchema
        assert by_name[info.name].description == info.description


def test_a_call_through_the_server_returns_what_the_registry_returns(store):
    server = mcp_server.build()
    args = {"query": "", "field": "titer_secreted", "organism": "", "limit": 3}
    through = _text(asyncio.run(server.call_tool("search_records", args)))
    direct = json.loads(tools.run("search_records", args).model_dump_json(exclude_none=True))
    assert through == direct


def test_a_number_is_refused_at_this_boundary_as_at_the_others(store):
    server = mcp_server.build()
    out = _text(asyncio.run(server.call_tool("selling_price", {"scenarioId": "sc-pha-1", "price": 4})))
    assert "a number was typed into price" in out["error"]
    assert out["error"] == tools.run("selling_price", {"scenarioId": "sc-pha-1", "price": 4}).error


def test_get_artifact_reads_and_says_when_there_is_none(store):
    out = _text(asyncio.run(mcp_server.build().call_tool("get_artifact", {"id": "0000000000000000"})))
    assert "no readable artifact" in out["error"]


def test_no_tool_writes_to_a_store_a_person_signs():
    src = (mcp_server.__file__ and open(mcp_server.__file__).read())
    for forbidden in ("biorepo.write", "guild.write", "write_evidence", "write_person", "checks."):
        assert forbidden not in src


def test_the_server_answers_over_stdio():
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "openferment_core.mcp_server"])
        async with stdio_client(params) as streams, ClientSession(*streams) as session:
            await session.initialize()
            listed = await session.list_tools()
            return [t.name for t in listed.tools]

    names = asyncio.run(asyncio.wait_for(go(), timeout=120))
    assert "draft_runbook" in names and "ask_postdoc" in names
