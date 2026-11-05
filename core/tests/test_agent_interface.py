"""The interface an outside agent builds against (alpha 2.2 E.16; the agent
builder's points, docs/reports/handoff-2026-11.md, round 1).

What a BioRepo record is, one rule that biorepo_read and search_records read
alike; a write's answer naming the audit rows it left; GET /api/audit read by
action, target and who, each row under its id with its null fields left out as
an answer over MCP leaves them out, and with the note its call carried; the
client recipe of docs/TOOLS.md, which hands the server no VIRTUAL_ENV, pointed
at from the page's top; a module read's summary typed (ModuleRead), its partial
a sentence; and each kind's detail named field by field (module_stores.DETAIL),
held to a row of every kind. Every value here is a placeholder.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from openferment_core import api, audit, evidence_pool, extract, module_stores, tools
from openferment_core.models import (
    Artifact,
    BasisInput,
    BasisSource,
    KeptTrain,
    ModuleRead,
    Proposal,
    TrainSpec,
)
from openferment_core.tools import reference
from test_evidence_pool import CANDIDATES, PAPERS, decision
from test_pureos import _art
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)
from test_tools_study import dearer_cane, worker  # noqa: F401  (the stand-in plant worker)
from test_writes import HAND, _fetched, store  # noqa: F401  (a held document, the throwaway stores)
from test_writes import ctx as writer
from test_writes import write

ROOT = Path(__file__).resolve().parents[2]
MODEL = "a-placeholder-model"
AT = "2026-11-05T00:00:00Z"
SKILL = {"kind": "skill", "id": "a-placeholder-skill", "name": "A placeholder skill", "note": "a placeholder note"}
# test_evidence_pool's placeholder candidates: one a reviewer verified, one kept gold, one rejected.
ACCEPTED, GOLD, REJECTED = "cl1-T4-00000001", "cl1-T5-00000001", "cl1-T5-00000002"


def _decided_pool():
    return evidence_pool.build(CANDIDATES, {
        ACCEPTED: decision(ACCEPTED, "verified"),
        GOLD: decision(GOLD, "verified", provenance="gold"),
        REJECTED: decision(REJECTED, "rejected", rejectReason="a placeholder reason")}, papers=PAPERS)


def _reader(pool_):  # noqa: F811
    return tools.ToolContext(pool_factory=lambda: pool_,
                             stores_factory=lambda: module_stores.Stores(module_stores.fixture_sources(lambda: pool_)))


def _read(module: str, ctx: tools.ToolContext, **asked):
    return tools.run(f"{module}_read", {"ids": [], "words": "", "kind": "", "state": "", "limit": 20, **asked}, ctx)


# ── what a BioRepo record is ─────────────────────────────────────────────


def test_a_record_is_read_by_one_rule_in_biorepo_read_and_search_records():
    ctx = _reader(_decided_pool())
    records = {r.id: r for r in _read("biorepo", ctx, kind="record").rows}
    candidates = {r.id: r for r in _read("biorepo", ctx, kind="candidate").rows}
    assert set(records) == {ACCEPTED, GOLD}, "a record is a candidate a reviewer verified"
    assert {r.provenance for r in records.values()} == {"verified", "gold"}
    assert {r.state for r in records.values()} == {"approved"}
    assert set(candidates) == {c.id for c in CANDIDATES} - {ACCEPTED, GOLD, REJECTED}
    assert {(r.provenance, r.state) for r in candidates.values()} == {("unverified", "proposed")}
    found = tools.run("search_records", {"query": "", "field": None, "organism": None, "limit": 10}, ctx)
    assert found.error is None, found.error
    kinds = {hit["recordId"]: hit["kind"] for hit in found.summary["records"]}
    assert kinds == {**{i: "record" for i in records}, **{i: "candidate" for i in candidates}}, \
        "search_records names each hit's kind as biorepo_read lists it, and neither holds the rejected one"
    for name in ("search_records", "biorepo_read"):
        assert module_stores.RECORD in tools.REGISTRY[name].description, name


def test_the_row_a_written_candidate_answers_is_the_row_biorepo_read_lists(pool, store):  # noqa: F811
    _fetched(store)
    made = write("biorepo", writer(pool), "candidate", fields=HAND)
    assert made.error is None, made.error
    (kept,) = extract.hand("X1").candidates
    listed = _read("biorepo", _reader(evidence_pool.build([kept], {})), ids=[kept.id])
    assert [r.model_dump() for r in listed.rows] == [r.model_dump() for r in made.rows]
    assert made.rows[0].kind == "candidate" and made.auditIds == [audit.read()[-1].id]


# ── a write's answer names its audit row ──────────────────────────────────


def test_a_writes_answer_names_its_audit_row_with_its_note_and_a_read_names_none():
    ctx = tools.ToolContext(model=MODEL)
    kept = tools.run("catalogue_write", SKILL, ctx)
    assert kept.error is None, kept.error
    (row,) = audit.read()
    assert kept.auditIds == [row.id] and row.id.isdigit()
    assert (row.action, row.target, row.detail["note"]) == ("catalogue_write", f"skill/{SKILL['id']}", SKILL["note"]), \
        "the row keeps the note its call carried, as AuditEntry.detail says"
    read = tools.run("catalogue_read", {"kind": "skill", "words": "", "limit": 5}, ctx)
    assert read.error is None and read.auditIds == []
    refused = tools.run("catalogue_write", {**SKILL, "kind": "nonesuch"}, ctx)
    assert refused.error and refused.auditIds == [] and len(audit.read()) == 1


def test_a_call_that_fails_after_its_write_names_the_row_that_stands(monkeypatch):
    """A write that committed before its tool raised keeps its audit row, and the failed call's answer names it; a
    row added inside a transaction the failure rolled back is gone, and no id is named for it."""
    import dataclasses

    from openferment_core import db, projects

    def committed_then_raises(parsed, ctx):
        audit.append(agent="model", who=MODEL, module="guild", action="catalogue_write", state="open",
                     target="skill/placeholder-a")
        raise RuntimeError("a placeholder failure after the write")

    async def rolled_back() -> None:
        async with db.session():
            await audit.add(projects.current(), agent="model", who=MODEL, module="guild", action="catalogue_write",
                            state="open", target="skill/placeholder-b")
            raise RuntimeError("a placeholder failure inside the write")

    def raises_inside(parsed, ctx):
        db.run(rolled_back())

    held = tools.REGISTRY["catalogue_write"]
    monkeypatch.setitem(tools.REGISTRY, "catalogue_write", dataclasses.replace(held, run=committed_then_raises))
    failed = tools.run("catalogue_write", SKILL, tools.ToolContext(model=MODEL))
    (row,) = audit.read()
    assert failed.error and "a placeholder failure after the write" in failed.error
    assert failed.auditIds == [row.id] and row.target == "skill/placeholder-a"
    monkeypatch.setitem(tools.REGISTRY, "catalogue_write", dataclasses.replace(held, run=raises_inside))
    gone = tools.run("catalogue_write", SKILL, tools.ToolContext(model=MODEL))
    assert gone.error and "a placeholder failure inside the write" in gone.error
    assert gone.auditIds == [] and [a.target for a in audit.read()] == ["skill/placeholder-a"]


def test_a_gated_writes_answer_names_the_row_its_proposal_left():
    """The proposal's row is written inside the proposal's own transaction,
    on the database's thread, and the answer names it all the same."""
    r = tools.run("runbooks_write", {"action": "lock", "target": "rb-a", "fields": {}, "note": "a placeholder note"},
                  tools.ToolContext(model=MODEL))
    assert r.error is None and r.summary["state"] == "proposed", r.error
    (row,) = audit.read()
    assert (row.action, row.state, row.detail["proposalId"]) == ("lock", "proposed", r.summary["proposalId"])
    assert r.auditIds == [row.id]


def test_a_scenarios_row_keeps_the_note_its_call_carried(worker):  # noqa: F811
    made = tools.run("study_scenario", {**dearer_cane(), "note": "a placeholder reason"}, tools.ToolContext(model=MODEL))
    assert made.error is None, made.error
    (row,) = [a for a in audit.read() if a.action == "study_scenario"]
    assert row.detail["note"] == "a placeholder reason" and made.auditIds == [row.id]


def test_the_rows_an_inner_block_collects_reach_the_outer_one():
    with audit.written() as outer:
        first = audit.append(agent="person", who="Ada Moreno", module="home", action="note", state="done")
        with audit.written() as inner:
            second = audit.append(agent="person", who="Ada Moreno", module="home", action="note", state="done")
    assert inner == [second.id] and outer == [first.id, second.id]


# ── GET /api/audit by action, target and who ──────────────────────────────


def _row(action: str, target: str | None, who: str):
    return audit.append(agent="person", who=who, module="home", action=action, state="done", target=target)


def test_the_audit_is_read_by_action_target_and_who_and_a_write_of_any_age_is_found():
    first = _row("keep", "skill/a-placeholder", "Ada Moreno")
    later = [_row("keep", "skill/another-placeholder", "Grace Hopper") for _ in range(3)]
    client = TestClient(api.app)

    def got(**asked) -> list[str]:
        answer = client.get("/api/audit", params=asked)
        assert answer.status_code == 200, answer.text
        return [r["id"] for r in answer.json()]

    assert got(limit=1) == [later[-1].id]
    assert got(limit=1, target="skill/a-placeholder") == [first.id], "older than the newest rows, found by its target"
    assert got(who="Grace Hopper") == [r.id for r in later], "newest last"
    assert got(action="keep", who="Ada Moreno") == [first.id]
    assert got(action="keep", target="skill/another-placeholder", who="Ada Moreno") == []
    assert got(who="Grace") == [] and got(action="kee") == [], "each matches a row's own word whole"


def test_the_http_audit_leaves_null_fields_out_as_mcp_does():
    row = _row("keep", None, "Ada Moreno")
    (served,) = [r for r in TestClient(api.app).get("/api/audit").json() if r["id"] == row.id]
    assert set(served) == {"id", "at", "agent", "who", "module", "action", "state", "detail"}
    assert served == json.loads(row.model_dump_json(exclude_none=True)), "the rule the MCP server writes a model by"


# ── docs/TOOLS.md: the client recipe, pointed at from the top ─────────────


def test_the_tools_page_points_a_client_at_its_recipe_and_the_recipe_hands_the_server_no_virtual_env():
    page = reference.render()
    assert (ROOT / "docs" / "TOOLS.md").read_text(encoding="utf-8") == page, "pnpm gen:tools writes the page"
    top = page.split("## The registry", 1)[0]
    anchors = {"the-mcp-server", "a-client", "module-reads"}
    assert all(f"(#{a})" in top for a in anchors)
    headings = {line.lstrip("#").strip().lower().replace(" ", "-") for line in page.splitlines() if line.startswith("#")}
    assert anchors <= headings, "each link names a heading of the page"
    assert 'env.pop("VIRTUAL_ENV", None)' in page and "env=dict(os.environ)" not in page
    recipe = page.split("### A client", 1)[1]
    assert "auditIds" in recipe and "?action=catalogue_write&target=skill/<id>&who=<name>/<version>" in recipe


# ── a module read's summary, and each kind's detail ───────────────────────


def test_a_module_reads_summary_is_a_module_read_its_partial_a_sentence(pool):  # noqa: F811
    r = _read("biorepo", _reader(pool))
    assert r.error is None, r.error
    summary = ModuleRead.model_validate(r.summary)
    assert set(r.summary) <= set(ModuleRead.model_fields)
    assert isinstance(summary.partial, str) and summary.partial == module_stores.PARTIAL["biorepo"]
    assert ModuleRead.model_json_schema()["properties"]["partial"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
    assert "partial, a sentence" in tools.REGISTRY["biorepo_read"].description
    assert "| `partial` | string or null | no |" in reference.render()


KEY = re.compile(r"`([A-Za-z]+)`")


def _keys(module: str, kind: str) -> set[str]:
    """The fields DETAIL names for a kind: its words in backticks."""
    return set(KEY.findall(module_stores.DETAIL[module][kind]))


def test_every_kind_has_its_detail_named_on_the_tools_page():
    assert {m: set(k) for m, k in module_stores.DETAIL.items()} == {m: set(k) for m, k in module_stores.KINDS.items()}
    page = reference.render()
    for module, kinds in module_stores.KINDS.items():
        for kind in kinds:
            assert _keys(module, kind), (module, kind)
            assert f"| `{module}` | `{kind}` |" in page, (module, kind)


def _artifact(aid: str, tool: str, output: dict) -> Artifact:
    return Artifact(id=aid, tool=tool, toolVersion="test", output=output, outputHash="0" * 64, provenance="computed",
                    createdAt=AT, durationMs=0, inputs=[BasisInput(name="placeholder", value="a placeholder", unit="",
                                                                   source=BasisSource(kind="convention"))])


def _every_kind() -> module_stores.Sources:
    """A row of every kind each module holds, from placeholder sources: no
    store, no network, no database."""
    pool_ = evidence_pool.build(CANDIDATES, {ACCEPTED: decision(ACCEPTED, "verified")}, papers=PAPERS)
    runbook = {"id": "rb-a", "title": "A placeholder runbook", "kind": "research", "status": "draft", "lockedAt": None,
               "productId": None, "strainId": None, "predictions": [],
               "measurementSchema": [{"id": "m-a", "label": "A placeholder measure", "unit": "placeholder-unit",
                                      "timepoint": "harvest", "predictionId": None}]}
    projection = {
        "runbooks": {"runbooks": [runbook],
                     "protocols": [{"id": "pr-a", "title": "A placeholder protocol", "category": "a-placeholder",
                                    "organisms": [], "purpose": "", "currentVersion": "1", "versions": ["1"]}]},
        "geneos": {"hosts": [{"id": "h-a", "name": "Placeholdera testii", "badges": [], "bsl": 1}],
                   "pathways": [{"id": "pw-a", "label": "A placeholder pathway", "products": ["a-placeholder"]}]},
        "proforma": {"scenarios": [{"id": "sc-a", "name": "A placeholder scenario", "kind": "biosteam",
                                    "product": "", "modelId": "a-placeholder-model"}]},
        "primer": {"lessons": [{"id": "l-a", "title": "A placeholder lesson", "moduleTitle": "A placeholder module",
                                "blurb": "", "skills": []},
                               {"id": "l-b", "title": "Another placeholder lesson", "skills": []}]},
    }
    deposition = {"id": "dep-a", "runbookId": "rb-a", "protocolId": None, "state": "running", "startedAt": AT,
                  "closedAt": None, "observations": [], "sampleTimes": {"de-a": 1},
                  "entries": [{"id": "de-a", "measureId": "m-a", "stepId": "s-a", "at": AT, "value": 1.0,
                               "unit": "placeholder-unit", "raw": "a placeholder reading", "confirmed": True}]}
    measured = {"id": "me-a", "depositionId": "dep-a", "runbookId": "rb-a", "productId": None, "predictionId": "p-a",
                "label": "A placeholder prediction", "value": 1.0, "unit": "placeholder-unit", "provenance": "measured",
                "conditions": {}, "deviations": [], "confirmed": True, "at": AT}
    run = _art(inputs=[BasisInput(name="flowsheet", value="test_line", unit="", source=BasisSource(kind="convention")),
                       BasisInput(name="scenario", value="sc-a", unit="", source=BasisSource(kind="convention"))])
    artifacts = [
        run,
        _artifact("00000000000000a1", "geneos.ceiling", {"note": "a placeholder"}),
        _artifact("00000000000000a2", "growth_fit", {"note": "a placeholder"}),
        _artifact("00000000000000a3", "fermos.simulation", {
            "family": "a-placeholder-family", "title": "A placeholder family", "strain": "h-a",
            "product": "a-placeholder", "sugar": "a-placeholder-sugar",
            "parameters": [{"key": "a-placeholder-key", "origin": "assumption"}], "start": [],
            "ceiling": {"flagged": False}, "aerobic": False, "flags": []}),
        _artifact("00000000000000a4", "fermos.vessel", {"source": "00000000000000a3", "sourceTool": "fermos.simulation",
                                                        "unitClass": "a-placeholder-class"}),
        _artifact("00000000000000a5", "pureos.train_run", {
            "train": {"id": "tr-a", "name": "A placeholder train", "product": "a-placeholder",
                      "units": [{"id": "C1", "type": "centrifugation"}],
                      "inlet": {"kind": "run-stream", "ref": "00000000000000a1"}},
            "productId": "a-placeholder", "product": "a-placeholder-chemical", "productStream": "s-a", "flags": []}),
    ]
    spec = TrainSpec.model_validate({
        "id": "tr-0123456789ab", "name": "A placeholder train", "program": "a-placeholder-set",
        "product": "a-placeholder", "inlet": {"kind": "run-stream", "ref": "00000000000000a1", "streamId": "s-a"},
        "units": [{"id": "C1", "type": "centrifugation", "records": {"split.Placeholder": ["r-a"]}}]})
    kept = KeptTrain(spec=spec, madeBy=MODEL, at=AT, updatedAt=AT)
    proposal = Proposal(id="pr-placeholder", at=AT, module="runbooks", action="lock", gate="lock",
                        title="A placeholder proposal", why="a placeholder", how="a placeholder", by=MODEL)
    return module_stores.Sources(
        projection=lambda: copy.deepcopy(projection),
        pool=lambda: pool_,
        artifacts=lambda: artifacts,
        guild=lambda: SimpleNamespace(people=[SimpleNamespace(id="p-a", name="Ada Moreno", active=True, role="lead")]),
        checks=lambda: SimpleNamespace(checks=[SimpleNamespace(id="chk-a", skillIds=["SK-A"], state="proposed")]),
        intake=lambda: {"doc-a": {"title": "A placeholder document", "year": 2026, "collector": "a-placeholder",
                                  "licenceClass": "a-placeholder", "passages": 1}},
        shelf=lambda: [SimpleNamespace(id="m-a", name="A placeholder model", host="h-a", unavailable=None)],
        strain_aliases=dict,
        witness=lambda: [SimpleNamespace(run="w-a", results=[SimpleNamespace(outcome="a-placeholder")],
                                         falsePositives=[], models=[MODEL])],
        proposals=lambda: [proposal],
        kept_trains=lambda: [kept],
        depositions=lambda: [(deposition, "Ada Moreno")],
        measured=lambda: [measured],
    )


def test_a_row_of_every_kind_holds_the_fields_its_kinds_words_name():
    stores = module_stores.Stores(_every_kind())
    held: dict[tuple[str, str], set[str]] = {}
    for module in module_stores.MODULES:
        assert stores.error(module) is None, stores.error(module)
        for row in stores.rows(module):
            fields = set(row.model().detail)
            assert fields <= _keys(module, row.kind), (module, row.kind, sorted(fields - _keys(module, row.kind)))
            held.setdefault((module, row.kind), set()).update(fields)
    every = {(m, k) for m, kinds in module_stores.KINDS.items() for k in kinds}
    assert set(held) == every, f"kinds no row was built of: {sorted(every - set(held))}"
    for (module, kind), fields in held.items():
        assert fields == _keys(module, kind), (module, kind, sorted(_keys(module, kind) - fields))
