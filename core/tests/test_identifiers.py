"""Identifiers proposed by machine, approved by a person (OF-BLD-012.1 F9).

73 of the 132 seed papers carry no PMCID, DOI or PMID, and 52 unverified
records sit on them; `biorepo.write` refuses a decision about any of them, so
they can never reach the committed file. Crossref can propose a DOI from a
title and a year — but a proposal is not a fact, and this module's whole job
is to keep the two apart.

Every test here is offline. The Crossref call is injected, so the matching,
the verdict and the patcher are pinned without a request; the one test that
actually asks Crossref is marked live and runs in `pnpm test:live`.
"""
from __future__ import annotations

import pytest

from openferment_core import identifiers as ids


# ── how close is close enough ──────────────────────────────────────────


def test_a_title_is_compared_without_its_punctuation_or_case():
    assert ids.normalize_title("Intron-containing algal transgenes!") == "intron containing algal transgenes"
    assert ids.normalize_title("  A   B  ") == "a b"


@pytest.mark.parametrize(
    "a,b,at_least",
    [
        ("the same title", "the same title", 1.0),
        ("Intron-containing algal transgenes", "Intron containing algal transgenes", 0.99),
        ("Expression of beta-casein in yeast", "Expression of β-casein in yeast", 0.9),
    ],
)
def test_near_identical_titles_score_near_one(a, b, at_least):
    assert ids.similarity(a, b) >= at_least


def test_a_different_paper_scores_low():
    assert ids.similarity("Intron-containing algal transgenes", "Micellar casein self-assembly") < 0.5


def test_a_proposal_needs_a_close_title_and_the_right_year():
    close, far = "Intron-containing algal transgenes", "Something else entirely"
    assert ids.verdict(close, 2018, close, 2018) == "PROPOSE"
    assert ids.verdict(close, 2018, close, 2019) == "PROPOSE", "a year either side is the same paper"
    assert ids.verdict(close, 2018, close, 2021) == "REVIEW", "three years out is a person's call"
    assert ids.verdict(close, 2018, far, 2018) == "REVIEW"
    assert ids.verdict(close, 2018, close, None) == "REVIEW", "no year is not a match"


# ── the proposal file ──────────────────────────────────────────────────

PAPERS = [
    {"id": "B2", "title": "Intron-containing algal transgenes", "year": 2018},
    {"id": "C5", "title": "Strategies to facilitate transgene expression", "year": 2009},
]


def fake_crossref(hits):
    """A Crossref that answers from a dict instead of the network."""

    def ask(title: str, year: int):
        return hits.get(title, [])

    return ask


def test_a_run_proposes_the_close_ones_and_sends_the_rest_to_a_person():
    ask = fake_crossref(
        {
            PAPERS[0]["title"]: [
                ids.Match(title="Intron containing algal transgenes", year=2018, doi="10.1/aaa", score=88.0)
            ],
            PAPERS[1]["title"]: [ids.Match(title="A quite different paper", year=2009, doi="10.1/bbb", score=41.0)],
        }
    )
    rows = ids.propose(PAPERS, ask)
    assert [r.paperId for r in rows] == ["B2", "C5"]
    assert rows[0].verdict == "PROPOSE" and rows[0].doi == "10.1/aaa"
    assert rows[1].verdict == "REVIEW", "a weak match is never proposed"
    assert rows[1].doi == "10.1/bbb", "but what it found is still shown, so a person can judge"


def test_a_paper_crossref_knows_nothing_about_is_a_row_with_no_doi():
    rows = ids.propose(PAPERS[:1], fake_crossref({}))
    assert rows[0].verdict == "REVIEW" and rows[0].doi == "" and rows[0].matchTitle == ""


def test_the_file_round_trips():
    rows = ids.propose(PAPERS, fake_crossref({}))
    text = ids.to_tsv(rows)
    assert text.splitlines()[0].split("\t")[0] == "verdict", "the column a person edits comes first"
    back = ids.from_tsv(text)
    assert [r.paperId for r in back] == [r.paperId for r in rows]
    assert [r.verdict for r in back] == [r.verdict for r in rows]


# ── the patch, which only an approved file may make ────────────────────

SEED = """export const PAPERS_AB: Paper[] = [
  {
    id: 'B2',
    title:
      'Intron-containing algal transgenes',
    authors: [],
    year: 2018,
    venue: 'Nucleic Acids Res',
    thread: 'B',
  },
  {
    id: 'B5',
    title: 'Already identified',
    authors: [],
    year: 2021,
    venue: 'Life',
    doi: '10.3390/life11090964',
    thread: 'B',
  },
];
"""


@pytest.fixture
def seed_dir(tmp_path):
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "threadAB.ts").write_text(SEED, encoding="utf-8")
    return d


def approved(**over):
    base = dict(
        verdict="APPROVED", paperId="B2", seedTitle="Intron-containing algal transgenes",
        seedYear=2018, matchTitle="Intron containing algal transgenes", matchYear=2018,
        doi="10.1/aaa", score=88.0, similarity=0.99,
    )
    base.update(over)
    return ids.Proposal(**base)


def test_an_approved_row_writes_the_doi_under_the_venue(seed_dir):
    changed = ids.apply_approved([approved()], seed_dir)
    text = (seed_dir / "threadAB.ts").read_text(encoding="utf-8")
    assert "    venue: 'Nucleic Acids Res',\n    doi: '10.1/aaa',\n" in text
    assert changed == ["B2: doi '10.1/aaa' added to threadAB.ts"]
    # and nothing else moved
    assert text.count("doi:") == 2 and "Already identified" in text


@pytest.mark.parametrize("verdict", ["PROPOSE", "REVIEW", "", "approved"])
def test_only_a_row_marked_APPROVED_is_written(seed_dir, verdict):
    before = (seed_dir / "threadAB.ts").read_text(encoding="utf-8")
    changed = ids.apply_approved([approved(verdict=verdict)], seed_dir)
    assert changed == []
    assert (seed_dir / "threadAB.ts").read_text(encoding="utf-8") == before


def test_a_row_with_no_doi_is_never_written(seed_dir):
    before = (seed_dir / "threadAB.ts").read_text(encoding="utf-8")
    assert ids.apply_approved([approved(doi="")], seed_dir) == []
    assert (seed_dir / "threadAB.ts").read_text(encoding="utf-8") == before


def test_a_paper_that_already_has_one_is_left_alone(seed_dir):
    before = (seed_dir / "threadAB.ts").read_text(encoding="utf-8")
    changed = ids.apply_approved([approved(paperId="B5")], seed_dir)
    assert changed == []
    assert (seed_dir / "threadAB.ts").read_text(encoding="utf-8") == before


def test_a_paper_the_seed_does_not_have_is_reported_not_guessed(seed_dir):
    with pytest.raises(ids.SeedPatchRefused) as caught:
        ids.apply_approved([approved(paperId="ZZ9")], seed_dir)
    assert "ZZ9" in str(caught.value)


def test_the_patch_is_one_line_and_nothing_else(seed_dir):
    """A patcher that also reflows, reindents or grows a trailing blank line
    makes a seed diff nobody can read, and the seed diff is the whole point."""
    before = (seed_dir / "threadAB.ts").read_text(encoding="utf-8")
    ids.apply_approved([approved()], seed_dir)
    after = (seed_dir / "threadAB.ts").read_text(encoding="utf-8")
    added = [line for line in after.split("\n") if line not in before.split("\n")]
    assert added == ["    doi: '10.1/aaa',"]
    assert len(after.split("\n")) == len(before.split("\n")) + 1
    assert after.endswith("];\n") and not after.endswith("\n\n"), "no blank line grown at the end"


def test_applying_twice_changes_nothing_the_second_time(seed_dir):
    assert len(ids.apply_approved([approved()], seed_dir)) == 1
    assert ids.apply_approved([approved()], seed_dir) == []


# ── the one part that needs the network ────────────────────────────────


@pytest.mark.live
def test_crossref_answers_with_a_doi_for_a_paper_it_knows():
    """Not in `pnpm verify` — it makes a request. `pnpm test:live` runs it.

    Crossref needs no key, but it does need to be reachable: some networks
    deny api.crossref.org, and this is where that shows up as a refusal
    rather than as 73 silent REVIEW rows.
    """
    hits = ids.crossref("Intron-containing algal transgenes mediate efficient recombinant "
                        "gene expression in the green microalga Chlamydomonas reinhardtii", 2018)
    assert hits, "Crossref returned nothing — is api.crossref.org reachable from here?"
    best = max(hits, key=lambda m: ids.similarity("Intron-containing algal transgenes mediate "
                                                  "efficient recombinant gene expression in the "
                                                  "green microalga Chlamydomonas reinhardtii", m.title))
    assert best.doi.startswith("10."), best
    assert best.year and 2017 <= best.year <= 2019
