"""The write tools, the gates, the proposals and the audit log (OF-BLD-015
§7.3, §7.4), on a throwaway data directory with no key and no network.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openferment_core import audit, extract, intake, module_stores, proposals, tools
from openferment_core.models import Candidate, ExtractResponse, FetchResult, FetchedSection, Usage
from openferment_core.tools import gates, writes
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)

WRITES = [f"{m}_write" for m in module_stores.MODULES]


@pytest.fixture()
def store(tmp_path, monkeypatch, pool):  # noqa: F811
    """Every store the writes reach, under tmp_path."""
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    monkeypatch.setattr(intake, "FULLTEXT_DIR", tmp_path / "fulltext")
    monkeypatch.setattr(extract, "CANDIDATES_DIR", tmp_path / "candidates")
    monkeypatch.setattr(audit, "PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(proposals, "PATH", tmp_path / "proposals.json")
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("OPENFERMENT_EFFORT", "medium")
    return tmp_path


def ctx(pool_, ask="ask-test"):  # noqa: F811
    c = tools.ToolContext(pool_factory=lambda: pool_, stores_factory=lambda: module_stores.Stores(module_stores.seed_sources(lambda: pool_)))
    c.ask_id = ask
    return c


def write(module, c, action, target="", fields=None, note="because"):
    return tools.run(f"{module}_write", {"action": action, "target": target, "fields": fields or {}, "note": note}, c)


# ── the pairs ─────────────────────────────────────────────────────────────


def test_every_read_tool_has_its_write_tool_in_the_whitelist():
    names = {t.name for t in tools.infos()}
    for m in module_stores.MODULES:
        assert {f"{m}_read", f"{m}_write"} <= names
    assert len(tools.WHITELIST) == 7 + 2 * len(module_stores.MODULES)


def test_a_write_tool_never_touches_a_store():
    """The rule check:tools holds too: a write goes through the module's own
    write function, never through a file."""
    src = Path(writes.__file__).read_text()
    for forbidden in ("write_text", "open(", "json.dump", ".write(", "atomic.", "_persist"):
        assert forbidden not in src, forbidden


@pytest.mark.parametrize("module", ["dominion", "pureos", "primer"])
def test_a_module_with_no_write_function_refuses_in_words(pool, store, module):  # noqa: F811
    r = write(module, ctx(pool), "anything")
    assert r.error and "no write function" in r.error and "gaps" in r.error
    assert audit.read() == [] and proposals.read().proposals == []
    # A gated action on a seed module is still a proposal (Dominion: publish).
    r = write(module, ctx(pool), "publish")
    if module == "dominion":
        assert r.error is None and r.summary["state"] == "proposed"
    else:
        assert "not an action" in r.error


@pytest.mark.parametrize("module, action", [("runbooks", "revise_protocol"), ("fermos", "fit"), ("proforma", "bind"),
                                            ("biorepo", "decide"), ("intake", "add"), ("runbooks", "draft")])
def test_an_action_with_no_write_function_refuses_and_names_who_can(pool, store, module, action):  # noqa: F811
    r = write(module, ctx(pool), action, target="x")
    assert r.error and action in r.error and "gaps" in r.error


def test_an_unknown_action_lists_the_actions(pool, store):  # noqa: F811
    r = write("geneos", ctx(pool), "fly")
    assert "not an action" in r.error and "ceiling" in r.error


def test_a_number_in_a_field_is_refused_before_the_tool_runs(pool, store):  # noqa: F811
    r = tools.run("geneos_write", {"action": "ceiling", "target": "", "fields": {"uptake": 10}, "note": ""}, ctx(pool))
    assert "a number was typed" in r.error


# ── the gates ─────────────────────────────────────────────────────────────


def test_the_gate_table_names_every_gate_the_build_document_lists():
    assert [g.id for g in gates.GATES] == ["publish", "spend", "lock", "sign", "personnel", "bench", "notebook"]
    assert all(g.covers and g.how and (g.server or g.route) for g in gates.GATES)
    assert gates.gated("runbooks", "lock").id == "lock" and gates.gated("geneos", "ceiling") is None


@pytest.mark.parametrize("module, action, gate", [("runbooks", "lock", "lock"), ("guild", "propose_check", "personnel"),
                                                  ("guild", "evidence", "sign"), ("home", "note", "notebook"),
                                                  ("runbooks", "deposit", "bench"), ("biorepo", "publish", "publish")])
def test_a_gated_action_writes_nothing_and_comes_back_proposed(pool, store, module, action, gate):  # noqa: F811
    r = write(module, ctx(pool), action, target="t-1", fields={"personId": "p-ada", "skillIds": "SK-OD"}, note="why")
    assert r.error is None and r.summary["state"] == "proposed" and r.summary["gate"] == gate
    [p] = proposals.open_ones()
    assert (p.module, p.action, p.gate, p.target, p.by, p.askId, p.note) == (module, action, gate, "t-1", "claude-haiku-5-5", "ask-test", "why")
    [line] = audit.read()
    assert (line.agent, line.who, line.module, line.action, line.state, line.askId, line.effort) == \
        ("model", "claude-haiku-5-5", module, action, "proposed", "ask-test", "medium")
    assert not (store / "guild.json").exists() and not (store / "checks.json").exists()


def test_a_proposal_shows_on_home_read(pool, store):  # noqa: F811
    c = ctx(pool)
    write("home", c, "note", note="keep the fructose ceiling as the only bound")
    seen = module_stores.Stores(module_stores.Sources(**{**vars(module_stores.seed_sources(lambda: pool)), "proposals": proposals.open_ones}))
    rows = module_stores.find(seen, "home", kind="proposal")
    assert len(rows) == 1 and rows[0].state == "proposed" and rows[0].status == "notebook"


def test_carrying_out_needs_a_named_person(pool, store):  # noqa: F811
    write("runbooks", ctx(pool), "lock", target="rb-brazzein")
    [p] = proposals.open_ones()
    for bad in ("", "me", "you", "model", "x"):
        with pytest.raises(proposals.ProposalRefused):
            proposals.carry_out(p.id, bad)
    assert proposals.get(p.id).state == "proposed"


def test_a_browser_side_gate_is_handed_to_the_person_and_logged(pool, store):  # noqa: F811
    write("runbooks", ctx(pool), "lock", target="rb-brazzein")
    [p] = proposals.open_ones()
    done = proposals.carry_out(p.id, "Ada Lovelace")
    assert done.state == "done" and done.carriedOutBy == "Ada Lovelace" and "Lock predictions" in done.result
    assert [(a.agent, a.who, a.state) for a in audit.read()] == [("model", "claude-haiku-5-5", "proposed"), ("person", "Ada Lovelace", "done")]
    with pytest.raises(proposals.ProposalRefused):
        proposals.carry_out(p.id, "Ada Lovelace")


def test_dismissing_keeps_the_reason(pool, store):  # noqa: F811
    write("home", ctx(pool), "note", note="n")
    [p] = proposals.open_ones()
    gone = proposals.dismiss(p.id, "Ada Lovelace", "not now")
    assert gone.state == "dismissed" and gone.result == "not now" and proposals.open_ones() == []


def test_a_check_proposal_is_asked_for_in_the_persons_name(pool, store, monkeypatch):  # noqa: F811
    from openferment_core import checks

    asked = []

    def request(req):
        asked.append(req)
        from openferment_core.models import Check
        return Check(id="chk-1", personId=req.personId, skillIds=req.skillIds, proposedAt="2026-10-20T00:00:00Z", proposedBy=req.by)

    monkeypatch.setattr(checks, "request", request)
    write("guild", ctx(pool), "propose_check", fields={"personId": "p-ada", "skillIds": "SK-OD, SK-DCW"})
    [p] = proposals.open_ones()
    done = proposals.carry_out(p.id, "Grace Hopper")
    assert asked[0].by == "Grace Hopper" and asked[0].skillIds == ["SK-OD", "SK-DCW"] and "chk-1" in done.result


# ── the free writes ───────────────────────────────────────────────────────


def _fetched(store, paper_id="X1", text="The culture reached a titre of 7 g/L of PHB on day three. Growth was slow."):
    f = FetchResult(paperId=paper_id, status="complete", sections=[FetchedSection(id="s1", heading="Results", text=text)],
                    fetchedAt="2026-10-20T00:00:00Z", pmcid="PMC1")
    (store / "fulltext").mkdir(parents=True, exist_ok=True)
    (store / "fulltext" / f"{paper_id}.json").write_text(f.model_dump_json())
    return f


def test_a_candidate_written_by_hand_is_anchored_and_marked(pool, store):  # noqa: F811
    _fetched(store)
    r = write("biorepo", ctx(pool), "candidate", fields={"paperId": "X1", "sectionId": "s1", "field": "titer_secreted", "value": "7",
                                                       "unit": "g/L", "quote": "The culture reached a titre of 7 g/L of PHB on day three."})
    assert r.error is None, r.error
    assert r.summary["state"] == "proposed" and r.summary["candidateId"].startswith("mw1-X1-")
    [row] = r.rows
    assert row.ref == f"biorepo/candidate/{r.summary['candidateId']}" and row.provenance == "unverified"
    kept = extract.cached("X1")
    assert [c.id for c in kept.candidates] == [r.summary["candidateId"]] and kept.candidates[0].provenance == "unverified"
    assert kept.audit[-1].who == "claude-haiku-5-5" and "by hand" in kept.audit[-1].action
    [line] = audit.read()
    assert (line.agent, line.module, line.action, line.state, line.target) == ("model", "biorepo", "candidate", "proposed", r.summary["candidateId"])


def test_a_candidate_whose_value_is_not_in_the_sentence_is_refused_on_the_rule(pool, store):  # noqa: F811
    _fetched(store)
    r = write("biorepo", ctx(pool), "candidate", fields={"paperId": "X1", "sectionId": "s1", "field": "titer_secreted", "value": "9",
                                                       "unit": "g/L", "quote": "The culture reached a titre of 7 g/L of PHB on day three."})
    assert r.error and "refused on rule value" in r.error
    assert extract.cached("X1") is None and audit.read() == []


def test_a_candidate_on_an_unfetched_paper_is_refused(pool, store):  # noqa: F811
    r = write("biorepo", ctx(pool), "candidate", fields={"paperId": "X1", "sectionId": "s1", "field": "titer_secreted", "value": "7",
                                                       "unit": "g/L", "quote": "q"})
    assert "no cached full text" in r.error


def test_a_ceiling_written_by_the_model_is_an_artifact_in_the_open_lane(pool, store, monkeypatch):  # noqa: F811
    from types import SimpleNamespace

    from openferment_core import geneos
    from openferment_core.models import Evidence

    def ceiling(model_id, product, substrate, **kw):
        ev = Evidence(id="ev-1", label="most PHB from glucose", value=0.48, unit="g/g", provenance="computed",
                      basis={"tool": "geneos.ceiling", "toolVersion": "1", "inputs": [], "artifactId": "a1", "at": "2026-10-20T00:00:00Z"})
        return SimpleNamespace(artifactId="a1", output={}, evidence=ev, finding=None)

    monkeypatch.setattr(geneos, "ceiling", ceiling)
    r = write("geneos", ctx(pool), "ceiling", fields={"modelId": "e_coli_core", "product": "phb", "substrate": "glucose"})
    assert r.error is None and r.summary["state"] == "open" and [e.id for e in r.evidence] == ["ev-1"]
    [line] = audit.read()
    assert (line.agent, line.module, line.action, line.state, line.target, line.detail["evidenceId"]) == \
        ("model", "geneos", "ceiling", "open", "e_coli_core", "ev-1")


def test_an_extraction_the_budget_refuses_becomes_a_spend_proposal(pool, store, monkeypatch):  # noqa: F811
    from openferment_core import llm

    def broke(paper_id, **kw):
        raise llm.BudgetExhausted("today's budget is spent")

    monkeypatch.setattr(extract, "extract_paper", broke)
    r = write("intake", ctx(pool), "extract", target="X1")
    assert r.summary["state"] == "proposed" and r.summary["gate"] == "spend"
    [p] = proposals.open_ones()
    assert p.server and "budget" in p.why


# ── the routes ────────────────────────────────────────────────────────────


@pytest.fixture()
def client(store):
    from openferment_core import api

    return TestClient(api.app, base_url="http://127.0.0.1")


def test_the_routes_list_carry_out_and_dismiss(pool, store, client):  # noqa: F811
    write("runbooks", ctx(pool), "lock", target="rb-1")
    write("home", ctx(pool), "note", note="n")
    listed = client.get("/api/proposals?state=proposed").json()
    assert [p["action"] for p in listed] == ["lock", "note"]
    bad = client.post(f"/api/proposals/{listed[0]['id']}/carry-out", json={"person": "you", "reason": ""})
    assert bad.status_code == 422 and "named person" in bad.json()["detail"]
    ok = client.post(f"/api/proposals/{listed[0]['id']}/carry-out", json={"person": "Ada Lovelace", "reason": ""})
    assert ok.status_code == 200 and ok.json()["state"] == "done" and ok.json()["carriedOutBy"] == "Ada Lovelace"
    gone = client.post(f"/api/proposals/{listed[1]['id']}/dismiss", json={"person": "Ada Lovelace", "reason": "later"})
    assert gone.json()["state"] == "dismissed" and gone.json()["result"] == "later"
    assert client.get("/api/proposals?state=proposed").json() == []
    log = client.get("/api/audit").json()
    assert [(a["agent"], a["state"]) for a in log] == [("model", "proposed"), ("model", "proposed"), ("person", "done"), ("person", "dismissed")]
    assert client.post("/api/proposals/pr-none/carry-out", json={"person": "Ada Lovelace", "reason": ""}).status_code == 422


def test_the_endpoint_runs_a_write_tool_like_the_loop(pool, store, client):  # noqa: F811
    r = client.post("/api/tools/runbooks_write", json={"action": "lock", "target": "rb-1", "fields": {}, "note": "n"})
    assert r.status_code == 200 and r.json()["summary"]["state"] == "proposed"
    assert [p.askId for p in proposals.open_ones()] == [None]


def test_the_log_survives_a_damaged_line(store):
    audit.append(agent="model", who="m", module="home", action="note", state="proposed")
    with audit.PATH.open("a") as f:
        f.write("{not json\n")
    audit.append(agent="person", who="Ada", module="home", action="note", state="done")
    assert [a.who for a in audit.read()] == ["m", "Ada"]
