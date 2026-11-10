"""H3: what validate.find_number (Rule 1 for a claim's text, a value's label, an estimate's basis, a gap
and a decline) lets through. Each line is a sentence a model could write that states a quantity.

  cd /home/user/openFermentUI/core && .venv/bin/python /home/user/openFermentUI/bughunt/notes/H3/scripts/find_number_probe.py
Pure function, no database.
"""
from openferment_core.validate import find_number
from openferment_core.practice import PRACTICE_QUANTITY

PROBES = [
    # controls: caught
    "The titre reached 45 g/L.", "Yield rose twofold.", "Yield was ten percent higher.",
    "Roughly an order of magnitude higher.", "The titre reached ½ of theory.", "Ⅳ runs were made.",
    "The titre reached ４５ g/L.",
    # fractions as plural words
    "Two thirds of the glucose was consumed.", "Three quarters of the xylose remained.",
    "Two fifths of the solids were lignin.",
    # plural scale words
    "Hundreds of litres of broth were made.", "Thousands of tonnes of stover a day.", "Dozens of runs failed.",
    "Tens of grams per litre were reached.",
    # determiner before a unit the table does not know
    "Ten per cent of the sugar was lost.", "The price was two dollars per gallon.", "Ten tonnes of stover a day.",
    "Five bar of pressure in the reactor.", "Seven kelvin above the set point.", "Nine ppm of furfural remained.",
    "Six gallons of beer per batch.", "Three kilowatts of power per tonne.", "Eight euros per kilogram.",
    # decade words with a hyphen prefix (identifier carve-out)
    "Conversion was in the high-90s percent.", "The titre sat in the mid-40s g/L.", "Yields in the low-30s were common.",
    # identifier-shaped quantities
    "Ethanol was made at pH5 throughout.", "The titre improved x10 over the parent.", "Hold at T30 for the run.",
    # multiplying words
    "The titre doubled after the switch.", "Productivity tripled in fed-batch.", "The yield halved under stress.",
    "Double the titre of the parent strain.",
    # ordinals past tenth
    "The twentieth run was best.", "A hundredth of the sugar remained.", "A thousandth of the cells survived.",
    # enclosed digits, superscripts alone, CJK numerals
    "Strain ③ gave the highest titre.", "The yield was ² of theory.", "The titre was 五 g/L.",
    # numbers glued after letters and a hyphen
    "The titre was titre-45 in the table.", "Hold at temp-30 for a day.",
]

for p in PROBES:
    hit = find_number(p)
    extra = PRACTICE_QUANTITY.search(p)
    print(f"{'caught ' + repr(hit) if hit else 'PASSES':16} {'(practice also: ' + repr(extra.group(0)) + ')' if extra and not hit else '':28} {p}")
