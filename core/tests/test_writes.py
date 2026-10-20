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
    # The seven, a pair a module, and thermo_props (OF-BLD-019 §4.2).
    assert len(tools.WHITELIST) == 7 + 2 * len(module_stores.MODULES) + 1


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
    # Asked for by the Guild person the browser acts as, by id; the reviewer
    # name goes on the proposal (OF-BLD-016 §1.R finding 11).
    done = proposals.carry_out(p.id, "Grace Hopper", acting="p-grace")
    assert asked[0].by == "p-grace" and asked[0].skillIds == ["SK-OD", "SK-DCW"] and "chk-1" in done.result
    assert done.carriedOutBy == "Grace Hopper"


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
    kept = extract.hand("X1")
    assert [c.id for c in kept.candidates] == [r.summary["candidateId"]] and kept.candidates[0].provenance == "unverified"
    assert kept.audit[-1].who == "claude-haiku-5-5" and "by hand" in kept.audit[-1].action
    [line] = audit.read()
    assert (line.agent, line.module, line.action, line.state, line.target) == ("model", "biorepo", "candidate", "proposed", r.summary["candidateId"])


def test_a_candidate_whose_value_is_not_in_the_sentence_is_refused_on_the_rule(pool, store):  # noqa: F811
    _fetched(store)
    r = write("biorepo", ctx(pool), "candidate", fields={"paperId": "X1", "sectionId": "s1", "field": "titer_secreted", "value": "9",
                                                       "unit": "g/L", "quote": "The culture reached a titre of 7 g/L of PHB on day three."})
    assert r.error and "refused on rule value" in r.error
    assert extract.all_cached() == [] and audit.read() == []


def test_a_candidate_on_an_unfetched_paper_is_refused(pool, store):  # noqa: F811
    r = write("biorepo", ctx(pool), "candidate", fields={"paperId": "X1", "sectionId": "s1", "field": "titer_secreted", "value": "7",
                                                       "unit": "g/L", "quote": "q"})
    assert "no cached full text" in r.error


HAND = {"paperId": "X1", "sectionId": "s1", "field": "titer_secreted", "value": "7", "unit": "g/L",
        "quote": "The culture reached a titre of 7 g/L of PHB on day three."}


def _every_cached_id() -> list[str]:
    return [c.id for r in extract.all_cached() for c in r.candidates]


def test_a_candidate_written_by_hand_is_not_an_extraction(pool, store, monkeypatch):  # noqa: F811
    """OF-BLD-016 §1.R finding 3: a hand-written candidate never makes the
    extractor's file, so the extractor still runs on the paper and the
    evidence pool still reads the candidate."""
    from openferment_core import biorepo, evidence_pool

    monkeypatch.setattr(biorepo, "PATH", store / "biorepo.json")
    _fetched(store)
    r = write("biorepo", ctx(pool), "candidate", fields=HAND)
    assert r.error is None, r.error
    cid = r.summary["candidateId"]
    assert not (store / "candidates" / "X1.json").exists() and extract.cached("X1") is None
    assert _every_cached_id() == [cid] and cid in evidence_pool.load().records_by_id

    asked = []

    def model(paper_id, user_text, tool):
        asked.append(paper_id)
        return {"candidates": []}, extract.Usage()

    monkeypatch.setattr(extract, "call_model", model)
    got = extract.extract_paper("X1")
    assert asked == ["X1"] and got.candidates == [] and extract.cached("X1") == got
    # A forced run replaces the extractor's file, and the hand-written one stays.
    extract.extract_paper("X1", force=True)
    assert asked == ["X1", "X1"] and _every_cached_id() == [cid]
    # A second one by hand is numbered after the first, and the extractor's file is untouched.
    again = write("biorepo", ctx(pool), "candidate", fields={**HAND, "unit": "g L-1"})
    assert again.error is None and again.summary["candidateId"] != cid
    assert extract.cached("X1").candidates == [] and len(_every_cached_id()) == 2


def test_a_decision_on_a_candidate_written_by_hand_finds_it(pool, store, monkeypatch):  # noqa: F811
    """The tool says a person accepts or rejects a hand-written candidate on
    Guild, so biorepo.write resolves its id (OF-BLD-016 §1.R, beside finding
    3): it was refused on rule `record` for every such id, whose tail is four
    digits and not the extractor's eight hex. X1 is no corpus paper, so the
    rule that holds now is the next one, `paper`."""
    from openferment_core import biorepo
    from openferment_core.models import ReviewDecision

    monkeypatch.setattr(biorepo, "PATH", store / "biorepo.json")
    _fetched(store)
    cid = write("biorepo", ctx(pool), "candidate", fields=HAND).summary["candidateId"]
    assert biorepo._resolve(cid).id == cid
    with pytest.raises(biorepo.WriteRefused) as refused:
        biorepo.write(ReviewDecision(status="rejected", provenance="unverified", reviewer="Sean Creighton", recordId=cid,
                                     at="2026-10-20T01:00:00Z", rejectReason="wrong sentence"), dry_run=True)
    assert refused.value.rule == "paper", refused.value
    assert biorepo._resolve("mw1-X1-0009") is None


def test_a_candidate_written_by_hand_leaves_an_earlier_runs_file_alone(pool, store):  # noqa: F811
    _fetched(store)
    (store / "candidates").mkdir()
    old = json.dumps({"paperId": "X1", "run": "haiku-1", "extractedAt": "2026-01-01T00:00:00Z", "candidates": [], "audit": []})
    (store / "candidates" / "X1.json").write_text(old)
    r = write("biorepo", ctx(pool), "candidate", fields=HAND)
    assert r.error is None, r.error
    assert (store / "candidates" / "X1.json").read_text() == old and extract.cached("X1") is None
    assert _every_cached_id() == [r.summary["candidateId"]]


@pytest.mark.parametrize("flags, negative, primary", [
    ({}, None, True),
    ({"negativeResult": "false", "isPrimary": "false"}, None, False),
    ({"negativeResult": " False", "isPrimary": "TRUE "}, None, True),
])
def test_a_hand_candidates_flags_are_read_as_the_words_true_and_false(pool, store, flags, negative, primary):  # noqa: F811
    """OF-BLD-016 §1.R finding 7: fields are strings, and bool('false') is True."""
    _fetched(store)
    r = write("biorepo", ctx(pool), "candidate", fields={**HAND, **flags})
    assert r.error is None, r.error
    [c] = [c for x in extract.all_cached() for c in x.candidates]
    assert (c.negativeResult, c.isPrimary, c.value) == (negative, primary, 7)


def test_a_hand_candidates_absence_anchors_on_true_and_is_refused_on_false(pool, store):  # noqa: F811
    quote = "Non-growth-associated ethanol production was not detected in the batch culture."
    _fetched(store, text=quote + " Growth was slow.")
    absent = {**HAND, "field": "ethanol_lp_beta", "value": "0", "unit": "g g-1 h-1", "quote": quote}
    no = write("biorepo", ctx(pool), "candidate", fields={**absent, "negativeResult": "false"})
    assert no.error and "refused on rule value" in no.error and extract.all_cached() == []
    yes = write("biorepo", ctx(pool), "candidate", fields={**absent, "negativeResult": "true"})
    assert yes.error is None, yes.error
    [c] = [c for x in extract.all_cached() for c in x.candidates]
    assert (c.negativeResult, c.value, c.valueBasis) == (True, 0, "negation")


@pytest.mark.parametrize("extra, named", [
    ({"negativeResult": "no"}, "negativeResult"),
    ({"isPrimary": ""}, "isPrimary"),
    ({"isPrimary": "yes"}, "isPrimary"),
    ({"confidence": "high"}, "confidence"),
    ({"status": "verified"}, "status"),
    ({"provenance": "gold", "valueBasis": "exact"}, "provenance, valueBasis"),
])
def test_a_hand_candidate_refuses_a_field_it_does_not_list_or_a_flag_that_is_not_true_or_false(pool, store, extra, named):  # noqa: F811
    _fetched(store)
    r = write("biorepo", ctx(pool), "candidate", fields={**HAND, **extra})
    assert r.error and r.error.startswith("biorepo_write refused") and named in r.error, r.error
    assert extract.all_cached() == [] and audit.read() == []


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


def test_the_audit_names_the_model_that_answered_not_the_chains_first(pool, store, monkeypatch):  # noqa: F811
    """§7.R finding 7: after a fallback, the writing model is the fallback."""
    c = ctx(pool)
    c.model = "claude-sonnet-5-5"
    write("home", c, "note", note="n")
    [line] = audit.read()
    assert line.who == "claude-sonnet-5-5" and proposals.open_ones()[0].by == "claude-sonnet-5-5"


def test_a_finding_is_audited_as_a_finding_not_as_open(pool, store, monkeypatch):  # noqa: F811
    """§7.R finding 3: a sugar the model cannot take up keeps nothing."""
    from types import SimpleNamespace

    from openferment_core import geneos

    monkeypatch.setattr(geneos, "ceiling", lambda *a, **k: SimpleNamespace(artifactId=None, output={}, evidence=None,
                                                                            finding="no uptake reaction for xylose"))
    r = write("geneos", ctx(pool), "ceiling", fields={"modelId": "e_coli_core", "product": "phb", "substrate": "xylose"})
    assert r.summary["state"] == "finding" and r.evidence == []
    assert [a.state for a in audit.read()] == ["finding"]
