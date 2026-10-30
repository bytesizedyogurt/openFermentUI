"""Proposals held to the rules (OF-BLD-016 §1.R findings 2, 5, 8, 9, 11, 12
and 13), on a throwaway data directory with no key and no network.

A proposal's words reach Home and the model's next ask, so they hold to Rule 1
like every other word on screen; a Guild proposal names nobody to someone the
check rules would not show it to; one ask makes one open proposal of a kind;
a server gate is marked done only when its server action ran; and the store's
lock is never held while an action runs.
"""
from __future__ import annotations

import threading
import time
from datetime import date, timedelta

import pytest

from openferment_core import audit, checks, extract, guild, llm, module_stores, postdoc_agent, proposals, tools
from openferment_core.models import EvidenceSource, GuildEvidence, GuildPerson
from openferment_core.tools import gates
from openferment_core.validate import find_number
from test_postdoc_agent import Script, plan
from test_tools import pool  # noqa: F401  (the stand-in pool fixture)
from test_writes import ctx, store, write  # noqa: F401  (every store under tmp_path)


def _home_rows(pool_):  # noqa: F811
    seen = module_stores.Stores(module_stores.Sources(**{**vars(module_stores.seed_sources(lambda: pool_)),
                                                         "proposals": proposals.open_ones}))
    return module_stores.find(seen, "home", kind="proposal")


# ── findings 5 and 8: Rule 1 on a proposal's words ────────────────────────


@pytest.mark.parametrize("module, action, target, fields, note, named", [
    ("home", "note", "", {}, "Brazzein reached 3.2 g/L at 30 C in the B5 shake flasks", "note"),
    ("home", "note", "", {}, "The titre doubled once the feed went in", "note"),
    ("runbooks", "lock", "rb-brazzein", {}, "lock it; expect 3.5 g/L", "note"),
    ("home", "note", "strain 7 at 55 percent", {}, "keep it", "target"),
    ("guild", "person", "", {"personId": "p-ada", "name": "yield 0.48 g/g"}, "add her", "name"),
])
def test_a_number_in_a_proposals_words_refuses_the_write(pool, store, module, action, target, fields, note, named):  # noqa: F811
    r = write(module, ctx(pool), action, target=target, fields=fields, note=note)
    assert r.error and r.error.startswith(f"{module}_write refused") and "number" in r.error and named in r.error, r.error
    assert "gaps" in r.error
    assert proposals.read().proposals == [] and audit.read() == []


def test_a_target_that_is_not_an_id_is_refused(pool, store):  # noqa: F811
    r = write("runbooks", ctx(pool), "lock", target="the brazzein runbook", note="lock it")
    assert r.error and "target" in r.error and "id" in r.error, r.error
    assert proposals.read().proposals == []


def test_the_store_refuses_a_proposal_whose_words_hold_a_number(store):
    for words in ({"note": "about 3 g/L"}, {"why": "twofold"}, {"title": "Runbooks: lock — at 30 C"},
                  {"fields": {"name": "0.48"}}, {"target": "strain 7"}):
        base = {"title": "Runbooks: lock", "why": "w", "note": "", "target": None, "fields": {}}
        with pytest.raises(proposals.ProposalRefused):
            proposals.propose(module="runbooks", action="lock", gate=gates.BY_ID["lock"], by="m", **{**base, **words})
    assert proposals.read().proposals == []


def test_a_gated_proposals_title_is_code_words_and_the_target_id(pool, store):  # noqa: F811
    r = write("runbooks", ctx(pool), "lock", target="rb-brazzein", note="lock before the pilot run")
    assert r.error is None, r.error
    [p] = proposals.open_ones()
    assert p.title == "Runbooks: lock a runbook's predictions before a run — rb-brazzein"
    assert find_number(p.title) is None and find_number(p.why) is None


def test_a_spend_proposals_why_holds_no_number(pool, store, monkeypatch):  # noqa: F811
    def broke(paper_id, **kw):
        raise llm.BudgetExhausted("Today's model spend is $4.20 of the $5.00 daily cap, and this call could pass it.")

    monkeypatch.setattr(extract, "extract_paper", broke)
    r = write("intake", ctx(pool), "extract", target="X1")
    assert r.error is None and r.summary["state"] == "proposed", r.error
    [p] = proposals.open_ones()
    assert "budget" in p.why and find_number(p.why) is None and find_number(p.title) is None


# ── finding 9: a Guild proposal names nobody ──────────────────────────────


ALEX = {"personId": "p-alex", "skillIds": "SK-OD"}


def test_a_guild_proposals_title_names_nobody(pool, store):  # noqa: F811
    r = write("guild", ctx(pool), "propose_check", target="p-alex", fields=ALEX, note="Alex Moreno has lapsed on pipetting")
    assert r.error is None, r.error
    [p] = proposals.open_ones()
    assert "alex" not in p.title.lower() and "lapsed" not in p.title
    assert p.title == "Guild: propose a competence check on a person's skills"


def test_a_guild_proposal_is_listed_without_its_words_and_kept_whole(pool, store):  # noqa: F811
    write("guild", ctx(pool), "propose_check", target="p-alex", fields=ALEX, note="Alex Moreno has lapsed on pipetting")
    write("runbooks", ctx(pool), "lock", target="rb-brazzein", note="lock before the pilot run")
    listed = {p.module: p for p in proposals.listed("proposed")}
    g = listed["guild"]
    shown = " ".join([g.title, g.why, g.note, g.target or ""]).lower()
    assert "alex" not in shown and "lapsed" not in shown
    # The ids stay, as Guild's checks serve them, so the browser can hold shownTo.
    assert g.fields == ALEX
    # Nothing else is redacted, and the store keeps what the model wrote.
    assert listed["runbooks"].note == "lock before the pilot run" and listed["runbooks"].target == "rb-brazzein"
    [kept] = [p for p in proposals.open_ones() if p.module == "guild"]
    assert kept.note == "Alex Moreno has lapsed on pipetting" and kept.target == "p-alex"


def test_home_read_names_nobody_on_a_guild_proposal(pool, store):  # noqa: F811
    write("guild", ctx(pool), "propose_check", target="p-alex", fields=ALEX, note="Alex Moreno has lapsed on pipetting")
    [row] = _home_rows(pool)
    said = " ".join([row.label, row.words, *(str(v) for v in row.detail.values())]).lower()
    assert "alex" not in said and "lapsed" not in said
    # A word from a guild note never finds the row either.
    assert module_stores.find(module_stores.Stores(module_stores.Sources(**{**vars(module_stores.seed_sources(lambda: pool)),
                                                                            "proposals": proposals.open_ones})),
                              "home", words="lapsed") == []


# ── finding 2: one open proposal of a kind per ask ────────────────────────


def test_an_open_duplicate_in_the_same_ask_is_refused(pool, store):  # noqa: F811
    c = ctx(pool)
    first = write("runbooks", c, "lock", target="rb-1", note="lock it before the run")
    again = write("runbooks", c, "lock", target="rb-1", note="predictions should be frozen")
    assert first.error is None and again.error and first.summary["proposalId"] in again.error and "gaps" in again.error
    assert len(proposals.open_ones()) == 1
    # Another target, or another ask, is another proposal.
    assert write("runbooks", c, "lock", target="rb-2", note="n").error is None
    assert write("runbooks", ctx(pool, ask="ask-other"), "lock", target="rb-1", note="n").error is None
    # Once the first is answered, the same ask may propose it again.
    proposals.dismiss(first.summary["proposalId"], "Ada Lovelace", "not yet")
    assert write("runbooks", c, "lock", target="rb-1", note="now").error is None
    assert len(proposals.open_ones()) == 3


def test_a_restart_does_not_propose_twice(pool, store, monkeypatch):  # noqa: F811
    monkeypatch.setenv("OPENFERMENT_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("OPENFERMENT_FALLBACK_MODEL", "claude-sonnet-5-5")
    w1 = ("runbooks_write", {"action": "lock", "target": "rb-1", "fields": {}, "note": "lock it before the run"})
    w2 = ("runbooks_write", {"action": "lock", "target": "rb-1", "fields": {}, "note": "predictions should be frozen"})
    c = tools.ToolContext(pool_factory=lambda: pool,
                          stores_factory=lambda: module_stores.Stores(module_stores.seed_sources(lambda: pool)))
    postdoc_agent.ask("Lock rb-1", converse=Script([w1], llm.ModelUnavailable("overloaded"), [w2], plan()), ctx=c)
    assert [(p.action, p.target) for p in proposals.open_ones()] == [("lock", "rb-1")]


# ── finding 11: a check is asked for in a Guild person's name ─────────────


@pytest.fixture()
def ledger(store, monkeypatch):
    monkeypatch.setattr(checks, "ENV_FILE", store / ".env")

    def person(pid, name, role="member", added_by="p-sean"):
        return GuildPerson(id=pid, name=name, role=role, joinedAt="2026-01-01", addedBy=added_by, addedAt="2026-01-01T00:00:00Z")

    guild.write_person(person("p-sean", "Sean Creighton", "lead", None))
    guild.write_person(person("p-eric", "Eric Habimana"))
    guild.write_person(person("p-patrick", "Patrick Mugisha"))
    day = (date.today() - timedelta(days=20)).isoformat()
    guild.write_evidence(GuildEvidence(id="e-desig-eric", personId="p-eric", skillId="SK-OD", kind="designation", at=day,
                                       observerId="p-sean", source=EvidenceSource(kind="lead", ref="PR-OD-01"), raw="seen"))
    return store


def test_a_check_proposal_needs_the_guild_person_acting(pool, ledger):  # noqa: F811
    write("guild", ctx(pool), "propose_check", fields={"personId": "p-patrick", "skillIds": "SK-OD"})
    [p] = proposals.open_ones()
    with pytest.raises(proposals.ProposalRefused) as no_one:
        proposals.carry_out(p.id, "Eric Habimana")
    assert "acting" in str(no_one.value) and "Guild" in str(no_one.value)
    assert proposals.get(p.id).state == "proposed" and not (ledger / "checks.json").exists()
    done = proposals.carry_out(p.id, "Eric Habimana", acting="p-eric")
    assert done.state == "done" and done.carriedOutBy == "Eric Habimana"
    [made] = checks.read().checks
    assert (made.personId, made.skillIds, made.proposedBy) == ("p-patrick", ["SK-OD"], "p-eric")


def test_the_carry_out_body_carries_the_acting_id():
    from openferment_core.models import ProposalAction

    assert ProposalAction(person="Eric Habimana").actingId is None
    assert ProposalAction(person="Eric Habimana", actingId="p-eric").actingId == "p-eric"


def test_the_routes_redact_a_guild_proposal_and_pass_the_acting_id(pool, ledger):  # noqa: F811
    from fastapi.testclient import TestClient

    from openferment_core import api

    client = TestClient(api.app, base_url="http://127.0.0.1")
    write("guild", ctx(pool), "propose_check", target="p-patrick", fields={"personId": "p-patrick", "skillIds": "SK-OD"},
          note="Patrick Mugisha has lapsed")
    [g] = client.get("/api/proposals?state=proposed").json()
    assert "patrick" not in (g["title"] + g["why"] + g["note"] + (g["target"] or "")).lower()
    bad = client.post(f"/api/proposals/{g['id']}/carry-out", json={"person": "Eric Habimana", "reason": ""})
    assert bad.status_code == 422 and "acting" in bad.json()["detail"]
    ok = client.post(f"/api/proposals/{g['id']}/carry-out",
                     json={"person": "Eric Habimana", "reason": "", "actingId": "p-eric"})
    assert ok.status_code == 200 and ok.json()["state"] == "done"
    assert "patrick" not in (ok.json()["note"] + (ok.json()["target"] or "")).lower()


# ── finding 12: nothing is marked done that did not run ───────────────────


def test_the_model_may_never_record_a_check(pool, store):  # noqa: F811
    r = write("guild", ctx(pool), "record_check", target="ck-1", fields={"checkId": "ck-1"})
    assert r.error and "record_check" in r.error and "bench" in r.error and "gaps" in r.error, r.error
    assert proposals.read().proposals == [] and gates.gated("guild", "record_check") is None


def test_a_server_gate_with_no_server_action_is_never_marked_done(store):
    made = proposals.propose(module="guild", action="record_check", gate=gates.BY_ID["personnel"], title="Guild: a check",
                             why="w", by="m", fields={"checkId": "ck-1"})
    with pytest.raises(proposals.ProposalRefused) as e:
        proposals.carry_out(made.id, "Sean Creighton", acting="p-sean")
    assert "nothing" in str(e.value)
    assert proposals.get(made.id).state == "proposed"
    assert [(a.agent, a.state) for a in audit.read()] == [("model", "proposed")]


# ── finding 13: the lock is not held while an action runs ─────────────────


def _spend_proposal():
    return proposals.propose(module="intake", action="extract", gate=gates.BY_ID["spend"], title="Extract X1 when the budget allows",
                             why="the model budget refused it", by="m", target="X1")


def test_carrying_out_releases_the_lock_while_the_action_runs(store, monkeypatch):
    from types import SimpleNamespace

    started, release = threading.Event(), threading.Event()

    def slow(paper_id, **kw):
        started.set()
        assert release.wait(10)
        return SimpleNamespace(candidates=[], rejected=0, usage=SimpleNamespace(costUsd=0.0))

    monkeypatch.setattr(extract, "extract_paper", slow)
    p = _spend_proposal()
    done: dict = {}
    worker = threading.Thread(target=lambda: done.setdefault("p", proposals.carry_out(p.id, "Sean Creighton")))
    worker.start()
    try:
        assert started.wait(5)
        t0 = time.monotonic()
        other = proposals.propose(module="runbooks", action="lock", gate=gates.BY_ID["lock"], title="Runbooks: lock — rb-1",
                                  why="w", by="m", target="rb-1")
        assert time.monotonic() - t0 < 1.0 and other.state == "proposed"
        # While it runs, the same proposal is neither carried out again nor dismissed.
        with pytest.raises(proposals.ProposalRefused):
            proposals.carry_out(p.id, "Ada Lovelace")
        with pytest.raises(proposals.ProposalRefused):
            proposals.dismiss(p.id, "Ada Lovelace", "no")
    finally:
        release.set()
        worker.join(10)
    assert done["p"].state == "done" and proposals.get(p.id).state == "done"
    # The proposal made while it ran is still there.
    assert proposals.get(other.id).state == "proposed"


def test_an_action_that_fails_leaves_the_proposal_open(store, monkeypatch):
    def broke(paper_id, **kw):
        raise llm.ModelUnavailable("overloaded")

    monkeypatch.setattr(extract, "extract_paper", broke)
    p = _spend_proposal()
    with pytest.raises(llm.ModelUnavailable):
        proposals.carry_out(p.id, "Sean Creighton")
    assert proposals.get(p.id).state == "proposed"
    gone = proposals.dismiss(p.id, "Sean Creighton", "later")
    assert gone.state == "dismissed"
