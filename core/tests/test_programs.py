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
