"""H5's tool probe: every registry tool, from project bh-b, with project bh-a's ids in its arguments, through
three doors (POST /api/tools/<name>, the openferment MCP server in its own process and through the service
with --service), plus ask_postdoc and get_artifact, and every tool of the sci-rag MCP server; then the same
servers started with --project naming no project, a malformed id and an unknown one. Each answer is searched
for A's words and ids that the call did not carry; A's rows are read whole before and after.

    source bughunt/lib/env.sh; cd core && bh_env OPENFERMENT_DATABASE_URL=$BH_SERVER/bh_h5_main \
        .venv/bin/python ../bughunt/notes/H5/scripts/probe_tools.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H5/scripts")
from hlib import ORIGIN, OUT, call
import probe_ops as P

ids = P.ids
DOC = P.DOC
RUN, REC, RB, FS, SC = ids["run"], ids["record"], ids["runbook"], ids["flowsheet"], ids["scenario"]
MOD = {"ids": [RB, ids["state"]["depositions"], "p-a", REC, DOC, ids["proposals"][0], RUN, "strain-a", "SK-A",
               "lesson-a", ids["checks"][0], ids["state"]["trains"]], "words": "", "kind": "", "state": "", "limit": 20}
ARGS = {
    "search_records": {"query": "ethanol xylose titre", "field": None, "organism": None, "limit": 10},
    "convert_units": {"recordId": REC, "toUnit": "kg/m3"},
    "search_passages": {"query": "SECRETWORDA xylose RACEMARKZQ", "k": 6},
    "yield_ceiling": {"modelId": "iMM904", "product": "ethanol", "substrate": "glucose"},
    "growth_forecast": {"fitArtifactId": RUN},
    "selling_price": {"scenarioId": SC},
    "draft_runbook": {"title": "B", "items": [], "measures": []},
    **{f"{m}_read": MOD for m in ("runbooks", "geneos", "fermos", "pureos", "proforma", "biorepo", "guild", "primer",
                                  "intake", "home")},
    "runbooks_write": {"action": "lock", "target": RB, "fields": {}, "note": "B"},
    "geneos_write": {"action": "ceiling", "target": "", "fields": {"modelId": "iMM904", "product": "ethanol",
                                                                   "substrate": "glucose"}, "note": "B"},
    "fermos_write": {"action": "forecast", "target": "", "fields": {"fitArtifactId": RUN}, "note": "B"},
    "pureos_write": {"action": "new_train", "target": "", "fields": {"product": "product-a", "inletRef": RUN}, "note": "B"},
    "proforma_write": {"action": "run", "target": SC, "fields": {}, "note": "B"},
    "biorepo_write": {"action": "publish", "target": REC, "fields": {}, "note": "B"},
    "guild_write": {"action": "propose_check", "target": "p-a", "fields": {"personId": "p-a", "skillIds": "SK-A"}, "note": "B"},
    "primer_write": {"action": "lesson", "target": "lesson-a", "fields": {}, "note": "B"},
    "intake_write": {"action": "extract", "target": DOC, "fields": {}, "note": "B"},
    "home_write": {"action": "note", "target": "", "fields": {"text": "B"}, "note": "B"},
    "thermo_props": {"artifactId": RUN, "streamId": "s1", "preset": "", "recordId": REC},
    "run_flowsheet": {"scenarioId": SC},
    "stream_table": {"artifactId": RUN},
    "fermos_simulate": {"family": "batch_v1", "fitArtifact": RUN, "strain": "strain-a", "product": "product-a"},
    "fermos_vessel": {"simulationArtifact": RUN, "fitArtifact": "", "vesselType": "stirred-tank", "klaMethod": ""},
    "pureos_build": {"action": "add_unit", "trainId": ids["state"]["trains"], "unitType": "flash"},
    "pureos_propose": {"product": "product-a", "host": "strain-a", "inletRef": RUN},
    "engine_plants": {"engine": "train"},
    "engine_parameters": {"engine": "train", "plant": ids["state"]["trains"]},
    "engine_run": {"engine": "train", "plant": ids["state"]["trains"], "note": "B"},
    "engine_report": {"run": RUN},
    "study_scenario": {"title": "B", "plant": "cornstover", "values": []},
    "study_compare": {"title": "B", "runs": [RUN, ids["run2"]]},
    "study_read": {},
    "literature_sources": {},
    "literature_document": {"document": DOC},
    "flowsheet_library": {},
    "flowsheet_import": {"file": "SF_BST_01", "note": "B"},
    "flowsheet_read": {"record": FS},
    "catalogue_read": {"kind": "strain"},
    "catalogue_write": {"kind": "strain", "id": "strain-a", "name": "B's model strain", "note": "B"},
}
SKIP_HEAVY = {"run_flowsheet", "proforma_write", "yield_ceiling", "geneos_write", "study_scenario"}
RAG_ARGS = {
    "search_corpus": {"query": "SECRETWORDA RACEMARKZQ xylose"},
    "answer_question": {"question": "What did SECRETWORDA produce?"},
    "get_document": {"document_id": DOC},
    "get_citations": {"document_id": DOC},
    "list_sources": {}, "corpus_stats": {},
    "search_entities": {"name_contains": "a"},
    "get_entity_relationships": {"entity_name": "ethanol"},
}
rows = []
# B now holds rows under some of A's ids (made by probe_ops from B) and two documents A pasted first (H5-02),
# so the markers here are the words and ids B never wrote.
import re
P.CONTENT = ["only A holds", "alice", "SECRET-ALIAS-A", "Placeholder species A", "RACEMARKZQ", "A's private"]
P.ID_PATTERNS = [re.compile(re.escape(x)) for x in (ids["protocol"], "SK-A", "product-a", "lesson-a", "e-aaaa1",
                 ids["checks"][0], RB, RUN, ids["run2"], ids["comparison"], ids["proposals"][0], REC)]


def note(door, tool, text, sent):
    leak = P.leaked(text, sent)
    rows.append({"door": door, "tool": tool, "leak": leak, "answer": text[:300]})
    print(json.dumps(rows[-1], ensure_ascii=False)[:330])
    sys.stdout.flush()


def http_door():
    for name, args in ARGS.items():
        if name in SKIP_HEAVY:
            continue
        r = call("POST", f"/api/tools/{name}", "bh-b", headers={"X-OpenFerment-Assistant": "bh-h5-probe/0.1"}, json=args)
        note("http", name, r.text, json.dumps(args))


async def mcp_door(label, argv, tool_args, extra=None):
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    env = {k: v for k, v in os.environ.items()}
    params = StdioServerParameters(command=sys.executable, args=argv, env=env, cwd="/home/user/openFermentUI/core")
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        init = await session.initialize()
        listed = [t.name for t in (await session.list_tools()).tools]
        rows.append({"door": label, "tool": "(instructions)", "leak": [], "answer": str(init.instructions)[:300],
                     "listed": listed})
        print(label, "instructions:", init.instructions, "tools:", len(listed))
        for name in listed:
            if name in SKIP_HEAVY:
                continue
            args = (extra or {}).get(name, tool_args.get(name, {}))
            try:
                res = await asyncio.wait_for(session.call_tool(name, args), timeout=240)
                text = " ".join(getattr(c, "text", "") for c in res.content) + (" [isError]" if getattr(res, "isError", getattr(res, "is_error", False)) else "")
            except Exception as e:
                text = f"[{type(e).__name__}: {e}]"
            note(label, name, text, json.dumps(args))


def main():
    before = P.snapshot()
    http_door()
    extra = {"ask_postdoc": {"question": "What does my project hold?"}, "get_artifact": {"id": RUN}}
    py = ["-m", "openferment_core.mcp_server"]
    asyncio.run(mcp_door("mcp-own", py + ["--project", "bh-b"], ARGS, extra))
    asyncio.run(mcp_door("mcp-service", py + ["--project", "bh-b", "--service", ORIGIN], ARGS, extra))
    rag = ["-m", "openferment_core.literature_mcp"]
    asyncio.run(mcp_door("rag-own", rag + ["--project", "bh-b"], RAG_ARGS))
    for label, proj in (("mcp-unknown", "bh-zzz"), ("mcp-malformed", "../bh-a"), ("mcp-upper", "BH-A")):
        asyncio.run(mcp_door(label, py + ["--project", proj], {k: ARGS[k] for k in ("study_read", "catalogue_read",
                                                                                   "engine_report")},
                             {"get_artifact": {"id": RUN}, "ask_postdoc": {"question": "x"}}))
        asyncio.run(mcp_door(label + "-service", py + ["--project", proj, "--service", ORIGIN],
                             {k: ARGS[k] for k in ("study_read", "catalogue_read")}, {"get_artifact": {"id": RUN}}))
        asyncio.run(mcp_door("rag-" + label, rag + ["--project", proj], RAG_ARGS))
    after = P.snapshot()
    changed = [k for k in before if before[k] != after[k]]
    with open(f"{OUT}/probe_tools.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("CHANGED IN A:", changed)
    print("LEAKS:", [(r["door"], r["tool"], r["leak"]) for r in rows if r["leak"]])


if __name__ == "__main__":
    main()
