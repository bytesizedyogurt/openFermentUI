"""A kinetic model's name is a name (thread Q, 2026-10-20).

Ks is "the half-saturation constant" in most of thread Q's papers, and claims
naming it were dropped for "half". The rule now reads a closed list of
whole hyphenated terms as names; the number word anywhere else still trips.
"""
from __future__ import annotations

import pytest

from openferment_core.validate import find_number

NAMES = [
    "The half-saturation constant for glucose in the Monod fit.",
    "Ks, the Half-Saturation constant, was fitted for CEN.PK113-7D.",
    "Ethanol formation followed first-order kinetics after the glucose ran out.",
    "A zero-order substrate term and a second-order decay were compared.",
    "The half-velocity constant of the uptake term.",
]

COUNTS = [
    ("Half the glucose was consumed by the end of the growth phase.", "Half"),
    ("The first of the strains grew fastest.", "first"),
    ("A half-saturating dose was added.", "half"),
    ("The half-saturation constant was 0.2 g/L.", "0"),
    ("Growth slowed to a third of its rate.", "third"),
]


@pytest.mark.parametrize("text", NAMES)
def test_a_kinetic_models_name_is_not_a_number(text):
    assert find_number(text) is None, f"{text!r} tripped on {find_number(text)!r}"


@pytest.mark.parametrize("text, found", COUNTS)
def test_the_number_word_elsewhere_still_trips(text, found):
    assert find_number(text) == found
