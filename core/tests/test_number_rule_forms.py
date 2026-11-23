"""Rule 1's detector on the number forms the bug hunt found it missed (H3-02,
H9-04): each is a quantity in a claim's words, dropped and counted; and the
names and counts the validator is tuned to let through, kept. Test sentences,
stated as such."""
from __future__ import annotations

import pytest

from openferment_core.validate import find_number

STATED = [
    # H3-02: a determiner before a money or mass word, a counting plural, a Latin-1 superscript.
    ("The price came to two dollars per gallon.", "two"),
    ("Ten per cent of the sugar remained.", "Ten"),
    ("Ten tonnes a day reached the plant.", "Ten"),
    ("Two thirds of the plant's cost has no record behind it.", "thirds"),
    ("Hundreds of litres were lost.", "Hundreds"),
    ("The area scaled with x² over the run.", "²"),
    ("The volume scaled with r³ over the run.", "³"),
    # H9-04: a multiplying verb, a table in Roman numerals, a pH or a multiplier against its number.
    ("Ethanol titre roughly doubled under anaerobic conditions", "doubled"),
    ("The titre halved after the shift.", "halved"),
    ("The titre quadrupled over the run.", "quadrupled"),
    ("Productivity kept doubling through the feed.", "doubling"),
    ("Table IV lists it.", "IV"),
    ("Dilute it x10 and read again.", "x10"),
    ("At pH7 the strain held its titre.", "pH7"),
    ("At pH-4 the strain held its titre.", "pH-4"),
]

KEPT = [
    "Ethanol yield on glucose in cenpk113-7d under anaerobic conditions",
    "A double mutant of the strain grew on xylose.",
    "A triple knockout strain made no acetate.",
    "Photosystem II was intact in the transformants.",
    "The type IV secretion system carried the protein out.",
    "one of the strains grew on xylose",
    "two studies agree on the pathway",
    "within seconds of the pulse the cells responded",
    "the ones that grew were kept",
    "the X33 strain of Pichia pastoris",
    "the half-saturation constant of glucose uptake",
    "the single largest cost in the plant",
    "Saccharomyces cerevisiae ferments glucose to ethanol under anaerobic conditions.",
]


@pytest.mark.parametrize("sentence, found", STATED)
def test_a_number_form_in_a_claims_words_is_found(sentence, found):
    assert find_number(sentence) == found


@pytest.mark.parametrize("sentence", KEPT)
def test_a_name_or_a_count_of_things_passes(sentence):
    assert find_number(sentence) is None
