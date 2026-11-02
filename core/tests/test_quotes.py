"""A quote is whole sentences or rows of its passage (quotes.py).

The passages here are test strings written for the rule, not any document's
words.
"""
from __future__ import annotations

from openferment_core.models import Passage
from openferment_core.quotes import is_whole_sentence, sentence_spans


def _p(text: str) -> Passage:
    return Passage(id="A:s1:0", paperId="A", sectionId="s1", heading="h", kind="prose", text=text, start=0, end=len(text))


def test_a_fragment_is_not_a_sentence():
    p = _p("Cells grew on the first sugar. The content rose steadily over the days of feeding.")
    for fragment in ("c", "content rose", "rose steadily"):
        assert not is_whole_sentence(fragment, p), fragment
    assert is_whole_sentence("Cells grew on the first sugar.", p)


def test_a_run_of_whole_sentences_is_whole():
    p = _p("One sentence here. Another sentence there. A third one ends it.")
    assert is_whole_sentence("One sentence here. Another sentence there.", p)
    assert not is_whole_sentence("here. Another sentence there.", p)


def test_a_table_row_is_a_whole_unit():
    row = _p("Table 2 Results\nStrain | Feed | Content\nA1 | sugar | high")
    assert is_whole_sentence("A1 | sugar | high", row)


def test_an_abbreviation_does_not_end_a_sentence():
    text = "Cells of E. coli grew. They stopped."
    spans = [text[s:e].strip() for s, e in sentence_spans(text)]
    assert spans == ["Cells of E. coli grew.", "They stopped."]
