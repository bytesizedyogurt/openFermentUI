"""-fold is a count of folds, and scaffold is not one (live test, 2026-10-16).

The magnitude pattern matched any word ending in "fold", so a claim about a
fibre scaffold was dropped as a quantity. It now matches only a count: a
number word, or several, many, multi, n or x, before "fold".
"""
from __future__ import annotations

import pytest

from openferment_core.validate import find_number

WORDS = [
    "PHB formed on a scaffold of fibres.",
    "The scaffolds were seeded.",
    "A manifold fed the fermenters.",
    "Proteins unfold above the melting point.",
    "The protein misfolds and refolds.",
    "Pages were in a billfold and a centerfold.",
    "The method was foldable.",
    "The paper folded the sample.",
]

COUNTS = [
    ("A twofold rise was seen.", "twofold"),
    ("A three-fold drop followed.", "three"),
    ("It rose eighty-fold.", "eighty"),
    ("Titres rose manyfold.", "manyfold"),
    ("A several-fold gain was seen.", "several-fold"),
    ("An x-fold change.", "x-fold"),
    ("Yields varied by orders of magnitude.", "orders of magnitude"),
    ("A 12-fold increase.", "1"),
]


@pytest.mark.parametrize("text", WORDS)
def test_a_word_ending_in_fold_is_not_a_count(text):
    assert find_number(text) is None, f"{text!r} tripped on {find_number(text)!r}"


@pytest.mark.parametrize("text,found", COUNTS)
def test_a_count_of_folds_still_fails(text, found):
    assert find_number(text) == found
