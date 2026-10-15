"""What the review of Phase 4 found (OF-BLD-014 §4.R). Each test failed
before its fix. STAND-IN text, not a paper's words."""
from __future__ import annotations

import json

import pytest

from openferment_core import embed, intake, llm, passages, rageval, rerank, retrieve
from openferment_core.models import FetchedSection, FetchResult, Usage

from test_retrieve import TEXTS, index  # noqa: F401


def _write(tmp, pid, sentences):
    r = FetchResult(paperId=pid, pmcid=None, status="complete", fetchedAt="2026-10-15T00:00:00Z",
                    sections=[FetchedSection(id=f"s{n}", heading="Results", text=t) for n, t in enumerate(sentences, start=1)])
    (tmp / "fulltext" / f"{pid}.json").write_text(r.model_dump_json(), encoding="utf-8")


# R1 — vectors made for other words are not used.
def test_vectors_for_changed_text_with_the_same_ids_are_refused(index):  # noqa: F811
    embed.build_dense(embed.HashEmbedder(64))
    _write(index, "X1", ["Entirely different words now stand here.", "And here too."])
    assert passages.build()["rebuilt"] == ["X1"]
    why = retrieve.why_unavailable("hybrid")
    assert why and "older index" in why


# R2 — the reader's sentence is a sentence.
def _p(text):
    return passages.Passage(id="A:s1:0", paperId="A", sectionId="s1", heading="h", kind="prose", text=text, start=0, end=len(text))


def test_a_fragment_is_not_a_sentence():
    p = _p("Cells grew on xylose. The PHB content rose steadily over four days of feeding.")
    for fragment in ("c", "PHB content", "rose steadily"):
        g = rerank.check([{"passageId": p.id, "grade": 3, "sentence": fragment}], {p.id: p})
        assert g.grades[p.id] == 0 and g.unverified == 1, fragment
    whole = rerank.check([{"passageId": p.id, "grade": 3, "sentence": "Cells grew on xylose."}], {p.id: p})
    assert whole.grades[p.id] == 3 and whole.unverified == 0
    row = _p("Table 2 Yields\nStrain | Feed | PHB\nH16 | xylose | high")
    g = rerank.check([{"passageId": row.id, "grade": 2, "sentence": "H16 | xylose | high"}], {row.id: row})
    assert g.grades[row.id] == 2, "a table row is a whole unit"


# R3 — the chosen lane that cannot run falls back to bm25, and says so.
def test_an_unavailable_chosen_lane_falls_back_to_bm25(index, monkeypatch):  # noqa: F811
    (index / "index" / "config.json").write_text(json.dumps({"lane": "hybrid"}))
    detail = retrieve.search_detail("casein calcium micelles", k=3)
    assert detail.lane == "bm25" and detail.hits
    assert detail.note and "hybrid" in detail.note
    with pytest.raises(retrieve.LaneUnavailable):
        retrieve.search_detail("casein", k=3, lane="hybrid")


# R6 — a refusal or a bad budget setting is a reason, not a 500.
def test_search_endpoint_reports_a_refusal_and_a_bad_setting(index, monkeypatch):  # noqa: F811
    from fastapi.testclient import TestClient

    from openferment_core import api, spend

    client = TestClient(api.app, base_url="http://127.0.0.1")

    def refuse(*a, **k):
        raise llm.ModelRefused("bio", ["claude-haiku-5-5"], Usage())

    monkeypatch.setattr(retrieve, "search_detail", refuse)
    r = client.post("/api/rag/search", json={"question": "x", "k": 3})
    assert r.status_code == 503 and "declined" in r.json()["detail"]

    def bad(*a, **k):
        raise spend.BudgetSettingInvalid("OPENFERMENT_DAILY_BUDGET_USD in core/.env is 'lots'")

    monkeypatch.setattr(retrieve, "search_detail", bad)
    r = client.post("/api/rag/search", json={"question": "x", "k": 3})
    assert r.status_code == 503 and "OPENFERMENT_DAILY_BUDGET_USD" in r.json()["detail"]


# R7 — discards count passages asked, never more.
def test_s_discards_never_exceed_what_was_asked(index, monkeypatch):  # noqa: F811
    def ask(**kw):
        return llm.Result(data={"questions": [{"passageId": "nowhere", "question": "anything at all here"}]}, model="m", usage=Usage())

    monkeypatch.setattr(rageval, "sample", lambda cuts, n, seed=rageval.SEED: cuts[:1])
    meta = rageval.write_questions(1, ask=ask)
    assert meta["asked"] == 1 and meta["kept"] == 0
    assert sum(meta["discarded"].values()) == 1 and meta["discarded"] == {"no question returned": 1}


# R8 — questions written for an older index are not scored as if current.
def test_s_written_for_an_older_index_is_set_aside(index, monkeypatch):  # noqa: F811
    def ask(**kw):
        ids = [line[1:].split("]")[0] for line in kw["user"].splitlines() if line.startswith("[")]
        return llm.Result(data={"questions": [{"passageId": i, "question": "How long does production take on a pentose feed?"} for i in ids]}, model="m", usage=Usage())

    monkeypatch.setattr(rageval, "sample", lambda cuts, n, seed=rageval.SEED: cuts[:1])
    rageval.write_questions(1, ask=ask)
    assert len(rageval.read_s()[0]) == 1
    _write(index, "X1", ["New words for the first paper.", "More of them."])
    passages.build()
    qs, meta = rageval.read_s()
    assert qs == [] and meta.get("stale")


def test_status_carries_the_manifest_hash(index):  # noqa: F811
    assert passages.status().manifestHash == passages.manifest_hash() != ""


# R9 — a K question names the strain, never an unrelated alias.
def test_k_names_the_strain_by_its_id():
    cut = passages.Cut(_p("Cells of cw15 secreted the reporter into the medium."), "c")
    item = {"id": "r-A-1", "paperId": "A", "field": "titer_secreted", "quote": "Cells of cw15 secreted the reporter", "strainId": "cw15"}
    qs, _ = rageval.build_k([item], [cut], {"titer_secreted": "Secreted titer"}, rageval._organism_labels({"cell-wall-deficient": "cw15", "cw15": "cw15"}))
    assert qs[0].text == "Secreted titer of cw15"


# R10 — an abstract half never passes CHUNK_MAX.
def test_no_abstract_half_passes_the_limit():
    # Over twice the limit: two halves cannot hold it, so it is cut as prose.
    text = " ".join(f"Sentence number {i} of a long stand-in abstract runs on a while." for i in range(60))
    assert len(text) > 2 * passages.CHUNK_MAX
    spans = passages._abstract_chunks(text)
    assert all(e - s <= passages.CHUNK_MAX for s, e in spans)
    assert spans[0][0] == 0 and spans[-1][1] == len(text)
