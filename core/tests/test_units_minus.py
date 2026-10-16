"""The minus sign journals print is a minus sign (live test, 2026-10-16).

Papers write exponents with U+2212 (−) and sometimes an en dash (–): `g L−1`,
`h−1`. The engine read only ASCII `-1` and superscript `⁻¹`, so 48 values the
extractor anchored were dropped as "does not normalise". These are every unit
string the 263 dropped values carried; each must normalise exactly as its
ASCII spelling does, and the ones that are plainly units must parse.
"""
from __future__ import annotations

import pytest

from openferment_core.units import normalize

DROPPED = [
    '$/kg', '%', '% (w w-1)', '% (w/v)', '% CDW', '% PHB/CDW', '% of CDW', '% w w-1', '% w/v',
    '%, w/w', '%PHA', '%protein', '%proteins', '-fold', 'P', 'colonies per µg of DNA',
    'colonies/μg DNA', 'day−1', 'dwt%', 'fold', 'g L−1', 'g L−1 h−1', 'g PHA/L/h',
    'g PHB/g PHB substrate', 'g g−1 cellobiose', 'g l−1', 'g mcl-PHA per g octanoic acid',
    'g per g', 'g/(L h)', 'g/(L·h)', 'g/L·h', 'g/g dried cell', 'g/mol', 'gL-1', 'gP(3HB)/L·h',
    'gP(3HB)/gxyl', 'h−1', 'kWh/kgDW', 'kWh/kgbiomass', 'mg L−1', 'mg PHB L−1',
    'mg PHB g−1 xylose', 'mg PHB g−1 xylose consumed', 'mg PHB/L', 'mg astaxanthin/L/h',
    'mg l−1 h−1', 'mg/g C-source', 'mg/g Xyl', 'mgPHA/gCDW', 'mgPHA/gTPA', 'phosphate groups',
    'times', 'transformants per µg of plasmid DNA', 'w w-1 h-1', 'weeks', 'wt %', 'µg mL−1',
    'µg/ml', '×10^3', '€ kg−1',
]


def _ascii(s: str) -> str:
    return s.replace("−", "-").replace("–", "-")


@pytest.mark.parametrize("raw", DROPPED)
def test_a_typographic_minus_reads_as_the_ascii_one(raw):
    assert normalize(raw) == normalize(_ascii(raw))


@pytest.mark.parametrize(
    "raw,key",
    [
        ("g L−1", "g L⁻¹"),
        ("g l−1", "g L⁻¹"),
        ("mg L−1", "mg L⁻¹"),
        ("g g−1", "g g⁻¹"),
        ("h−1", "h⁻¹"),
        ("g L−1 h−1", "g L⁻¹ h⁻¹"),
        ("g L–1", "g L⁻¹"),
    ],
)
def test_the_units_papers_print_parse(raw, key):
    assert normalize(raw) == key
