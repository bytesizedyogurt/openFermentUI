"""Programs as data (OF-BLD-016 §2.1, E.1′, E.2′).

The three programs are declared in src/data/programs.ts and reach the
service through the projections `pnpm export:corpus` writes (`pnpm test:core`
exports them first). These tests read the real corpus.json and modules.json:
the projection carries three programs, the letters partition the threads,
and a paper, a record, a strain and a row resolve to the program the browser
gives them. No key, no network, no service.
"""
from __future__ import annotations

import json

import pytest

from openferment_core import programs
from openferment_core.corpus import DATA as CORPUS_PATH, load_corpus
from openferment_core.models import Program


@pytest.fixture(scope="module")
def corpus_json():
    return json.loads(CORPUS_PATH.read_text())


@pytest.fixture(scope="module")
def modules_json():
    return json.loads(programs.MODULES_PATH.read_text())


def test_the_projection_carries_three_programs(corpus_json):
    declared = {p["id"]: p for p in corpus_json["programs"]}
    assert set(declared) == {"casein", "pha", "yeast"}
    assert declared["casein"]["letters"] == list("ABCDEFGHIJKLMNO")
    assert declared["pha"]["letters"] == ["P"]
    assert declared["yeast"]["letters"] == ["Q"]
    assert {k: v["status"] for k, v in declared.items()} == {"casein": "archived", "pha": "archived", "yeast": "active"}
    # Each is the shape models.Program mirrors from types.ts, and has a name
    # and a line of words.
    for p in corpus_json["programs"]:
        model = Program.model_validate(p)
        assert model.name and model.summary


def test_modules_json_carries_the_same_programs(corpus_json, modules_json):
    assert modules_json["programs"] == corpus_json["programs"]


def test_the_letters_partition_the_threads(corpus_json):
    owner: dict[str, str] = {}
    for p in programs.programs():
        for letter in p.letters:
            assert letter not in owner, f"thread {letter} is in {owner.get(letter)} and {p.id}"
            owner[letter] = p.id
    threads = {p["id"][0] for p in corpus_json["papers"]}
    assert threads == set(owner), "every thread a paper carries has a program, and every letter a paper"


def test_a_paper_resolves_by_its_thread_letter():
    corpus = load_corpus()
    p_paper = next(p["id"] for p in corpus.papers if p["id"].startswith("P"))
    q_paper = next(p["id"] for p in corpus.papers if p["id"].startswith("Q"))
    h_paper = next(p["id"] for p in corpus.papers if p["id"].startswith("H"))
    assert programs.program_of("paper", p_paper) == "pha"
    assert programs.program_of("paper", q_paper) == "yeast"
    assert programs.program_of("paper", h_paper) == "casein"
    # Every paper in the corpus has a program; an id that is no entry id has none.
    assert all(programs.program_of_paper(p["id"]) for p in corpus.papers)
    assert programs.program_of_paper("not-a-paper") is None
    assert programs.program_of_paper("Z1") is None


def test_a_record_resolves_by_the_paper_it_cites():
    corpus = load_corpus()
    for r in corpus.records:
        assert programs.program_of("record", r["id"]) == programs.program_of_paper(r["paperId"])
    # A candidate is asked about as a dict: it is not in corpus.json.
    assert programs.program_of_record({"id": "r-P3-1", "paperId": "P3"}) == "pha"
    assert programs.program_of("record", "no-such-record") is None


def test_strains_resolve_by_their_own_field():
    assert programs.program_of("strain", "s-cerevisiae-cenpk113-7d") == "yeast"
    assert programs.program_of("strain", "s-cerevisiae-s288c") == "yeast"
    assert programs.program_of("strain", "c-necator-h16") == "pha"
    assert programs.program_of("strain", "cw15") == "casein"
    # D6: the species catalogue entry stays general, and so do the platform
    # hosts Dominion's molecules are made in.
    assert programs.program_of("strain", "s-cerevisiae") is None
    assert programs.program_of("strain", "ecoli") is None


def test_rows_carry_the_program_the_browser_gives_them(modules_json):
    assert programs.program_of("product", "phb") == "pha"
    assert programs.program_of("product", "brazzein") is None
    assert programs.program_of("scenario", "sc-pha-1") == "pha"
    assert programs.program_of("scenario", "sc-s1") == "casein"
    assert programs.program_of("protocol", "PR-TAP-01") == "casein"
    assert programs.program_of("protocol", "PR-CIP-01") is None
    assert programs.program_of("lesson", "l1-1") == "casein"
    assert programs.program_of("lesson", "l6-1") is None
    # Every seed runbook names a general product or host, and is general.
    assert all(r["program"] is None for r in modules_json["runbooks"]["runbooks"])
    # Every row of every kind carries the field, even when it is null.
    for module, key in programs._ROWS.values():
        assert all("program" in row for row in modules_json[module][key]), f"{module}.{key}"


def test_examples_are_marked_in_the_projection_and_on_the_rows(modules_json):
    # OF-BLD-016 §3.3 (D3): the seed runbooks, the casein protocols, sc-s1…s3
    # and the lessons of m0–m5 describe runs nobody made; the generic
    # protocols and the bench track do not. The browser hides an example with
    # the archive; the service lists it, marked, so a read can say so.
    rb = modules_json["runbooks"]
    assert all(r["example"] is True for r in rb["runbooks"])
    flagged = {p["id"] for p in rb["protocols"] if p["example"]}
    assert {"PR-OD-01", "PR-CIP-01"}.isdisjoint(flagged) and "PR-TAP-01" in flagged
    assert {s["id"] for s in modules_json["proforma"]["scenarios"] if s["example"]} == {"sc-s1", "sc-s2", "sc-s3"}
    lessons = {l["id"]: l["example"] for l in modules_json["primer"]["lessons"]}
    assert lessons["l1-1"] is True and lessons["l6-1"] is False
    rows = {r.id: r for r in _stores(include_archived=True).rows("runbooks")}
    assert rows["rb-taq-kigali"].detail.get("example") is True
    assert "example" not in rows["PR-OD-01"].detail


def test_archived_is_a_status_and_general_is_never_archived():
    assert programs.archived_ids() == frozenset({"casein", "pha"})
    assert [p.id for p in programs.active_programs()] == ["yeast"]
    assert programs.is_archived("pha") and programs.is_archived("casein")
    assert not programs.is_archived("yeast")
    assert not programs.is_archived(None)
    assert not programs.is_archived("no-such-program")


def test_shows_hides_an_archived_entity_unless_asked():
    assert not programs.shows("strain", "c-necator-h16")
    assert programs.shows("strain", "c-necator-h16", include_archived=True)
    assert programs.shows("strain", "s-cerevisiae-cenpk113-7d")
    assert programs.shows("strain", "s-cerevisiae")
    assert not programs.shows("paper", "H4")
    assert programs.shows("paper", "H4", include_archived=True)


# ── the switch: the service honours it (OF-BLD-016 §2.3, E.2′) ──────────────
#
# Off is the default everywhere. The pool, the passages, the sweep and every
# read tool leave archived programs out; with the switch on, everything is as
# it was before the step. The switch rides in the request and the tools'
# context; no tool input carries it.

import asyncio  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from openferment_core import evidence_pool, module_stores, passages, retrieve, tools  # noqa: E402
from openferment_core.models import AnswerPlan, Candidate, Passage, Quantity, ReviewDecision  # noqa: E402
from openferment_core.validate import find_number  # noqa: E402

STAND_IN = "STAND-IN for test_programs: an invented sentence, not a paper's words."
QUESTION = "What PHB yield did Cupriavidus necator H16 reach on glucose?"


def _candidate(cid: str, paper_id: str) -> Candidate:
    return Candidate(id=cid, paperId=paper_id, sectionId="s1", quote=STAND_IN, field="titer_secreted", value=1.0,
                     unit="g L-1", si=Quantity(value=1.0, unit="g L-1"), organism="a stand-in organism")


def _first(corpus, letter: str) -> str:
    return next(p["id"] for p in corpus.papers if p["id"].startswith(letter))


def _archived(paper_id: str) -> bool:
    return programs.is_archived(programs.program_of_paper(paper_id))


def _before(corpus, candidates, decisions) -> list[str]:
    """The pool's ids as `build` made them before the switch: every seed
    record and candidate no decision rejected, in the same order."""
    rejected = {rid for rid, d in decisions.items() if d.status == "rejected"} | {
        r["id"] for r in corpus.records if r.get("status") == "rejected"}
    ids = [r["id"] for r in corpus.records if r["id"] not in rejected]
    seen = set(ids)
    for c in candidates:
        if c.id in seen or c.id in rejected or c.status == "rejected":
            continue
        ids.append(c.id)
        seen.add(c.id)
    return ids


@pytest.fixture()
def parts():
    corpus = load_corpus()
    cands = [_candidate(f"cl1-{_first(corpus, x)}-stand-in", _first(corpus, x)) for x in ("P", "Q", "H", "A")]
    rejected = ReviewDecision(status="rejected", provenance="unverified", recordId=cands[3].id, at="2026-10-20T00:00:00Z",
                              reviewer="Sean Creighton", rejectReason="stand-in")
    return corpus, cands, {cands[3].id: rejected}


def test_the_pool_with_the_switch_off_holds_no_casein_or_pha_record_or_candidate(parts):
    corpus, cands, decisions = parts
    off = evidence_pool.build(corpus, cands, decisions, [])
    assert off.records, "the yeast candidate stays"
    assert not [r["id"] for r in off.records if _archived(r["paperId"])]
    assert {r["paperId"][0] for r in off.records} == {"Q"}
    assert set(off.hidden) == {"casein", "pha"}
    # A tool reads the same pool, and finds nothing archived by any word.
    found = tools.run("search_records", {"query": "", "field": "titer_secreted", "organism": "", "limit": 10},
                      tools.ToolContext(pool_factory=lambda: off))
    assert found.recordIds and not [i for i in found.recordIds if _archived(off.record(i)["paperId"])]


def test_with_the_switch_on_the_pool_is_what_it_was_before(parts):
    corpus, cands, decisions = parts
    on = evidence_pool.build(corpus, cands, decisions, [], include_archived=True)
    off = evidence_pool.build(corpus, cands, decisions, [])
    assert [r["id"] for r in on.records] == _before(corpus, cands, decisions)
    assert on.hidden == {}
    assert len(on.records) == len(off.records) + sum(off.hidden.values())


def test_the_pool_this_checkout_holds_hides_the_archived_programs():
    off, on = evidence_pool.load(), evidence_pool.load(include_archived=True)
    assert not [r["id"] for r in off.records if _archived(r["paperId"])]
    assert sum(off.hidden.values()) > 0, "the seed's casein records are hidden"
    assert len(on.records) == len(off.records) + sum(off.hidden.values())


def _stores(include_archived: bool) -> module_stores.Stores:
    pool = evidence_pool.build(load_corpus(), [], {}, [], include_archived=include_archived)
    stores = module_stores.Stores(module_stores.seed_sources(lambda: pool), include_archived=include_archived)
    stores.pool_hidden = sum(pool.hidden.values())  # type: ignore[attr-defined]
    return stores


def test_with_the_switch_off_the_sweep_says_found_in_archived_program_pha_hidden():
    cmap = module_stores.coverage(QUESTION, _stores(False))
    assert cmap.includeArchived is False
    assert [a.name for a in cmap.archived] == ["PHA"]
    pha = cmap.archived[0]
    assert {"dominion", "geneos"} <= set(pha.modules) and pha.count >= 2
    assert module_stores.archived_line(pha) == "found in archived program PHA (hidden)"
    # The line stands in the trace's summary, the trace's lines and the map
    # the model reads; no hidden row's ref reaches the model.
    assert module_stores.footer(cmap).endswith("· found in archived program PHA (hidden)")
    assert module_stores.trace_lines(cmap)[-1] == "PHA · found in archived program PHA (hidden)"
    text = module_stores.for_model(cmap)
    assert "found in archived program PHA (hidden)" in text and "geneos/host/c-necator-h16" not in text
    assert all(h.id not in ("c-necator-h16", "phb") for m in cmap.modules for h in m.hits)
    # The gap names the program and the switch, and holds no number.
    gap = module_stores.archived_gap(pha)
    assert "PHA is an archived program" in gap and "Settings → Programs" in gap and not find_number(gap)


def test_a_question_naming_an_archived_program_by_name_is_told_it_is_hidden():
    cmap = module_stores.coverage("What do we know about casein?", _stores(False))
    assert "Casein" in [a.name for a in cmap.archived]


def test_with_the_switch_on_the_sweep_is_what_it_was_before():
    on, off = _stores(True), _stores(False)
    cmap = module_stores.coverage(QUESTION, on)
    assert cmap.includeArchived is True and cmap.archived == []
    assert "c-necator-h16" in [h.id for m in cmap.modules for h in m.hits]
    for module in module_stores.MODULES:
        assert on.rows(module) == on.all_rows(module) and on.hidden(module) == []
        # BioRepo's records come from the pool, which left them out first.
        from_pool = off.pool_hidden if module == "biorepo" else 0  # type: ignore[attr-defined]
        assert len(off.rows(module)) + len(off.hidden(module)) + from_pool == len(on.rows(module)), module
        assert not [r.id for r in off.rows(module) if programs.is_archived(r.program)], module
    # The switch hides something in every module a program reaches.
    assert {m for m in module_stores.MODULES if off.hidden(m)} >= {"dominion", "runbooks", "geneos", "proforma",
                                                                   "primer", "intake"}


def test_an_artifact_belongs_to_the_program_of_what_it_was_computed_from():
    def art(*inputs):
        return SimpleNamespace(inputs=[SimpleNamespace(name=n, value=v, source=SimpleNamespace(kind=k, id=i))
                                       for n, v, k, i in inputs])

    assert programs.program_of_artifact(art(("model", "m", "model", "RehMBEL1391"))) == "pha"
    assert programs.program_of_artifact(art(("model", "m", "model", "Yeast9"))) == "yeast"
    assert programs.program_of_artifact(art(("model", "m", "model", "e_coli_core"), ("product", "phb", "convention", None))) == "pha"
    assert programs.program_of_artifact(art(("record value", "1", "record", "r-B5-3"))) == "casein"
    assert programs.program_of_artifact(art(("model", "m", "model", "biorefineries.cornstover@2.35.1"))) is None


def test_with_the_switch_off_retrieval_leaves_archived_passages_out(monkeypatch):
    def cut(pid: str) -> passages.Cut:
        paper = pid.split(":")[0]
        return passages.Cut(Passage(id=pid, paperId=paper, sectionId="s1", heading="Results", kind="prose",
                                    text=f"Ethanol from glucose in the stand-in {paper}.", start=0, end=40), STAND_IN)

    def other(n: int) -> passages.Cut:
        return passages.Cut(Passage(id=f"Z9:s1:{n}", paperId="Z9", sectionId="s1", heading="Methods", kind="prose",
                                    text=f"Unrelated stand-in words, part {n}.", start=0, end=30), STAND_IN)

    corpus = load_corpus()
    ids = [f"{_first(corpus, x)}:s1:0" for x in ("P", "Q", "H")]
    index = passages.Bm25Index([cut(i) for i in ids] + [other(n) for n in range(4)])
    monkeypatch.setattr(passages, "bm25_index", lambda: index)
    off = retrieve.search_detail("ethanol glucose", k=8, lane="bm25")
    on = retrieve.search_detail("ethanol glucose", k=8, lane="bm25", include_archived=True)
    assert [h.passage.id for h in off.hits] == [ids[1]] and off.hidden == 2
    assert sorted(h.passage.id for h in on.hits) == sorted(ids) and on.hidden == 0


def test_the_api_passes_the_switch_through_and_no_tool_input_carries_it(monkeypatch):
    from openferment_core import api, postdoc_agent

    asked: list[bool] = []
    ran: list[bool] = []
    searched: list[bool] = []
    monkeypatch.setattr(evidence_pool, "load", lambda include_archived=False: SimpleNamespace(records=[]))

    def ask(question, *, ctx, **kw):
        asked.append(ctx.include_archived)
        return AnswerPlan(question=question)

    def run(name, raw, ctx=None):
        ran.append(ctx.include_archived)
        return tools.ToolResult()

    def search_detail(question, k=8, lane=None, include_archived=False, **kw):
        searched.append(include_archived)
        return retrieve.Detail(hits=[], lane="bm25")

    monkeypatch.setattr(postdoc_agent, "ask", ask)
    monkeypatch.setattr(tools, "run", run)
    monkeypatch.setattr(retrieve, "search_detail", search_detail)
    client = TestClient(api.app, base_url="http://127.0.0.1")
    for body in ({"question": "q"}, {"question": "q", "includeArchived": True}, {"question": "q", "includeArchived": False}):
        assert client.post("/api/ask", json=body).status_code == 200
        assert client.post("/api/ask/stream", json=body).status_code == 200
        assert client.post("/api/rag/search", json=body).status_code == 200
    assert asked == [False, False, True, True, False, False]
    assert searched == [False, True, False]
    read = {"ids": [], "words": "", "kind": "", "state": "", "limit": 5}
    client.post("/api/tools/geneos_read", json=read)
    client.post("/api/tools/geneos_read?includeArchived=true", json=read)
    assert ran == [False, True]
    monkeypatch.undo()
    # The switch is never a field a model can type into a tool's input.
    refused = tools.run("geneos_read", read | {"includeArchived": True})
    assert refused.error and "includeArchived" in refused.error


def test_the_mcp_server_takes_the_switch_from_its_environment_and_never_from_a_client(monkeypatch):
    from openferment_core import mcp_server

    monkeypatch.delenv(mcp_server.SWITCH_ENV, raising=False)
    assert mcp_server.include_archived_from_env() is False
    monkeypatch.setenv(mcp_server.SWITCH_ENV, "1")
    assert mcp_server.include_archived_from_env() is True
    seen: list[bool] = []
    monkeypatch.setattr(tools, "run", lambda name, raw, ctx=None: (seen.append(ctx.include_archived), tools.ToolResult())[1])
    read = {"ids": [], "words": "", "kind": "", "state": "", "limit": 5}
    asyncio.run(mcp_server.build().call_tool("geneos_read", read))
    asyncio.run(mcp_server.build(include_archived=False).call_tool("geneos_read", read))
    assert seen == [True, False]
