"""Step labels and counting determiners are prose (live test, 2026-10-16).

"Flask B is a stage 1 culture on Day 3" names a step of a protocol, and "one
of the strains" picks out a strain; neither is a quantity. Both practice live
tests and many Postdoc claims were dropped for them. A closed list exempts
them; a quantity with a unit still fails, and so does a number a tool result
tells the model to state.
"""
from __future__ import annotations

import pytest

from openferment_core.validate import find_number

PROSE = [
    "Flask B is a stage 1 culture.",
    "The reading was taken on Day 3 of the protocol.",
    "Step 2 sets the inoculum.",
    "Phase 4 is the feed.",
    "In round 2 the strains were rescreened.",
    "After pass 3 the line was stable.",
    "One of the strains grew on xylose.",
    "Two strains made the polymer.",
    "Three studies reported it.",
    "Ten papers used this feed.",
    "Only one study measured it.",
]

QUANTITIES = [
    ("The culture ran for two days.", "two"),
    ("It took three hours.", "three"),
    ("Two grams were recovered.", "Two"),
    ("It was 3 g/L on day 3.", "3"),
    ("The titre reached 3 g/L in stage 2.", "3"),
    ("Stage 40 was reached.", "4"),
    ("Eleven strains grew.", "Eleven"),
    ("A first study reported it.", "first"),
    ("Day 3 gave 4 g/L.", "4"),
    ("Got two of the three points.", "three"),
]


@pytest.mark.parametrize("text", PROSE)
def test_a_step_label_or_a_counting_word_is_prose(text):
    assert find_number(text) is None, f"{text!r} tripped on {find_number(text)!r}"


@pytest.mark.parametrize("text,found", QUANTITIES)
def test_a_quantity_still_fails(text, found):
    assert find_number(text) == found
