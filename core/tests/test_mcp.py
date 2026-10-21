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


def test_u1_ask_postdoc_declines_in_words_when_the_loop_fails(monkeypatch):
    from openferment_core import postdoc_agent

    def boom(question, **kw):
        raise FileNotFoundError("corpus.json not found. Generate it with `pnpm export:corpus`")

    monkeypatch.setattr(postdoc_agent, "ask", boom)
    out = _text(asyncio.run(mcp_server.build().call_tool("ask_postdoc", {"question": "What PHB yields?"})))
    assert out["declined"].startswith("Postdoc could not run") and "export:corpus" in out["declined"]


# ── OF-BLD-015 §7.5: the same registry, the reads and the writes, the gates ──


def test_the_server_counts_every_module_tool_with_its_marks_and_gates():
    from openferment_core import module_stores
    from openferment_core.tools import gates

    listed = asyncio.run(mcp_server.build().list_tools())
    names = [t.name for t in listed]
    reads = [f"{m}_read" for m in module_stores.MODULES]
    writes = [f"{m}_write" for m in module_stores.MODULES]
    # The registry's whole list and the server's two: the count is derived,
    # and test_tools.NAMES is the one literal list (OF-BLD-019 §6.1).
    assert len(names) == len(tools.WHITELIST) + len(mcp_server.EXTRA)
    assert {"thermo_props", "run_flowsheet", "stream_table", "fermos_simulate", "fermos_vessel",
            "pureos_build"} <= set(names)
    assert set(reads) | set(writes) <= set(names)
    by_name = {t.name: t for t in listed}
    # A read says what state it computes; a write says which actions a gate stops.
    assert all("computed by the service" in by_name[r].description for r in reads)
    for module, action in gates.BY_ACTION:
        assert f"{action}:" in by_name[f"{module}_write"].description and "gated" in by_name[f"{module}_write"].description


def test_a_gated_write_through_the_server_is_a_proposal_not_a_write(store, monkeypatch):
    from openferment_core import audit, proposals

    monkeypatch.setattr(audit, "PATH", store / "audit.jsonl")
    monkeypatch.setattr(proposals, "PATH", store / "proposals.json")
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-haiku-5-5")
    server = mcp_server.build()
    out = _text(asyncio.run(server.call_tool("guild_write", {"action": "evidence", "target": "", "fields": {"personId": "p-1"}, "note": "n"})))
    assert out["summary"]["state"] == "proposed" and out["summary"]["gate"] == "sign"
    assert not (store / "guild.json").exists() and len(proposals.open_ones()) == 1
    [line] = audit.read()
    assert line.agent == "model" and line.askId is None  # no ask owns a call from outside the app
    refused = _text(asyncio.run(server.call_tool("pureos_write", {"action": "add", "target": "", "fields": {}, "note": ""})))
    assert "no write function" in refused["error"]


# ── OF-BLD-019 §6.1: a flowsheet run and its stream table, with no change here ──


def test_the_server_offers_run_flowsheet_and_stream_table_as_the_registry_does(store):
    listed = {t.name: t for t in asyncio.run(mcp_server.build().list_tools())}
    for name in ("run_flowsheet", "stream_table"):
        assert listed[name].description == tools.REGISTRY[name].description
        assert listed[name].input_schema == tools.REGISTRY[name].info().inputSchema
    server = mcp_server.build()
    for name, args in (("stream_table", {"artifactId": "0123456789abcdef"}), ("run_flowsheet", {"scenarioId": "sc-pha-1"}),
                       ("run_flowsheet", {"scenarioId": "sc-pha-1", "samples": 9})):
        through = _text(asyncio.run(server.call_tool(name, args)))
        assert through == json.loads(tools.run(name, args).model_dump_json(exclude_none=True)) and through["error"]


# ── OF-BLD-020 §3.4: fermos_simulate, with no change here ──────────────────


def test_the_server_offers_fermos_simulate_as_the_registry_does(store):
    listed = {t.name: t for t in asyncio.run(mcp_server.build().list_tools())}
    assert listed["fermos_simulate"].description == tools.REGISTRY["fermos_simulate"].description
    assert listed["fermos_simulate"].input_schema == tools.REGISTRY["fermos_simulate"].info().inputSchema
    server = mcp_server.build()
    for args in ({"family": "batch_v1", "recordsByParam": {"mu_max": [0.4]}}, {"family": "light_v1"}):
        through = _text(asyncio.run(server.call_tool("fermos_simulate", args)))
        assert through == json.loads(tools.run("fermos_simulate", args).model_dump_json(exclude_none=True))
        assert through["error"]


# ── OF-BLD-020 §5.4: pureos_build, with no change here ─────────────────────


def test_the_server_offers_pureos_build_as_the_registry_does(store):
    listed = {t.name: t for t in asyncio.run(mcp_server.build().list_tools())}
    assert listed["pureos_build"].description == tools.REGISTRY["pureos_build"].description
    assert listed["pureos_build"].input_schema == tools.REGISTRY["pureos_build"].info().inputSchema
    server = mcp_server.build()
    for args in ({"action": "set_from_record", "trainId": "tr-x", "unitId": "C1", "recordsByParam": {"split.Ethanol": [9]}},
                 {"action": "run", "trainId": "tr-nowhere"}):
        through = _text(asyncio.run(server.call_tool("pureos_build", args)))
        assert through == json.loads(tools.run("pureos_build", args).model_dump_json(exclude_none=True))
        assert through["error"]
