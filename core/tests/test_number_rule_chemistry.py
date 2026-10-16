"""Chemistry names are names, and a number in prose is still a number
(live test, 2026-10-16).

Rule 1 blanks identifier-shaped spans before it looks for digits, and the
identifier pattern covered letters-then-digits alone. The PHA program's own
vocabulary leads with a digit: the monomers 3HB, 3HV and 4HB, the polymer
P(3HB), glycosidic linkages such as α2,6, and the locants of compound names
such as 4-hydroxybenzoic acid. Question 7 of the live batch lost every claim
to them, and the F-SIALYL flow failed on them.
"""
from __future__ import annotations

import pytest

from openferment_core.validate import find_number

NAMES = [
    "The polymer was P(3HB) in every strain.",
    "Cells accumulated P(3HB-co-3HV) on the hydrolysate.",
    "Xylose raised the 3HV fraction of the copolymer.",
    "The 3HB monomer dominated.",
    "Feeding the precursor gave P(3HB-co-4HB).",
    "The 4HB unit was incorporated.",
    "A 3HHx monomer appeared on oil feeds.",
    "PHBV was recovered by solvent extraction.",
    "An α2,6-sialyltransferase capped the glycan.",
    "A β1,4-galactosyltransferase extended it.",
    "The α-2,3 linkage was absent.",
    "The β(1→4) linkage was formed.",
    "Cells degraded 4-hydroxybenzoic acid.",
    "The strain made 2,3-butanediol as a by-product.",
    "Poly(3-hydroxybutyrate) granules formed.",
    "The 3-hydroxybutyrate monomer was released.",
    "It grew on 1,3-propanediol.",
]

NUMBERS = [
    ("The titre reached 3 g/L.", "3"),
    ("Content rose to 4 percent.", "4"),
    ("The yield was 0.4 on glucose.", "0"),
    ("A 12-fold increase was seen.", "1"),
    ("Cells grew in a 10-mL flask.", "1"),
    ("About 2,3 grams were recovered.", "2"),
    ("It took 6 hours.", "6"),
]


@pytest.mark.parametrize("text", NAMES)
def test_a_chemistry_name_is_not_a_number(text):
    assert find_number(text) is None, f"{text!r} tripped on {find_number(text)!r}"


@pytest.mark.parametrize("text,first", NUMBERS)
def test_a_number_in_prose_still_fails(text, first):
    assert find_number(text) == first
