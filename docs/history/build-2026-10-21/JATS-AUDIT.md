# The parser against the first real fetch (2026-10-14)

What `split_jats` (`core/openferment_core/intake.py`) made of the 31 articles
`pnpm intake:fetch --all` returned on 2026-10-14, compared with each article's
raw JATS from Europe PMC. Five auditors read the XML and the parsed sections,
six or seven papers each; one skeptic per kind of finding then tried to
refute every medium or high one against the XML and the code. All 52 medium
and high findings were confirmed; 26 can change or hide a number an
extractor would quote. 52 low findings were left unverified. Prose survives
well: 1,472 of 1,479 sampled body paragraphs appear in the parsed text.

Reproduced by hand, from the fetched JSON and the raw XML:
C6 "16–64 (i.e. 2<sup>4</sup>–2<sup>6</sup>)" reads "16–64 (i.e. 2–2)";
I6 "α ∼ 0.5" plus a table-footnote mark reads "α ∼ 0.51";
E6 "p-value <10<sup>− 15</sup>" reads "<10− 15";
C9's only table sits in `<floats-group>` and is absent from the sections.

## By cause, most damaging first

| Cause in `intake.py` | What it does to the text | Papers |
|---|---|---|
| `_table_rows` drops empty cells (`cells = [c for c in cells if c]`, line 305) | Every value after an empty cell, and every header over an empty stub corner, moves one column left | C2, C3, F3, H1, I6, M8, N4, O3, O5 |
| `_table_rows` ignores `colspan` and `rowspan` (lines 298–308) | Two-row headers misalign; a rowspan label (a component, a study, a population) appears on its first row alone | C3, C9, F3, F4, L7, N3, O3 |
| `_collect`'s superscript rules (lines 243–254) | A power of two is dropped (2⁴ → 2); an exponent holding a space or thin space loses its caret (10⁻¹⁵ → "10− 15", 10⁻⁵ → "10− 5"); a footnote mark ending in a period is glued to a number (0.5 → 0.51); a citation after a sentence-final period following a number is glued on; single citations stick to words ("alters17"-style tokens) | A2, C6, D2, E6, H10, I6, J10 |
| `<floats-group>` is never walked (lines 391, 398 walk `<body>` alone) | Tables and figure captions stored there are lost | A6, C9, F1 |
| `<table-wrap-foot>` is dropped (`_table_rows` reads `<tr>` alone) | Units, replicate counts and the meaning of significance letters and abbreviations go | A2, B5, F3, F4, G6, I6, M8, N4 |
| `<break/>` adds no space (`_collect`, lines 216–258) | A word and a number in one cell join into one token, which `parse_numbers` reads as an identifier | F3, G6, O5 |
| MathML flattened character by character | A fraction loses its bar (3/5 → "35"); exponents join their base | I6 |
| Back matter served as `<sec sec-type="ack">` and kin inside `<body>` | Acknowledgements, funding (with grant codes), contributions and data statements become prose sections; the parser drops only the `<ack>` element | C3, D2, F3, G3, G9, H1, H10, O3, O5 |
| An image-only table yields no rows, and its section is skipped | The caption appears nowhere | D2 |
| `<ali:license_ref>` is never read as the href | `license.href` is empty and the URL is glued to the licence sentence | G6, N4 |
| A structured abstract falls back to `_text(abstract)` | Its headings run into its sentences with no separator | O5 |

## The fixes, and a second audit (2026-10-14)

Sean answered "do what you need to do", so every cause above was fixed in
`intake.py` with a failing test first (commit `da606a7`). A second audit
then read the same 31 articles against the fixed parser: five auditors, six
or seven papers each, checking each earlier finding and hunting
regressions, and one skeptic per kind of serious finding. Its totals:

| | |
|---|---|
| Earlier findings resolved | 44 of 52; the other 8 were partly resolved back matter |
| Numbers checked against the XML | 8,632, of which 8,629 intact |
| Serious findings, all three confirmed by the skeptics | 3 |
| Low findings | 36 |

The three serious findings, and their fixes (each with a failing test, and
each fix undone once to watch its test fail):

| Paper | What the parser did | Fix |
|---|---|---|
| B5 | One `<fn>` held two notes, `<sup>1</sup> … <sup>2</sup> …`, so only `1` was a label and the cell `336 <sup>2</sup>` read `336^2` | Every superscript in a note that follows no number is a label (`_note_marks`); one that follows a number, `10<sup>6</sup>`, stays a power |
| G3 | eLife nests each figure supplement inside its figure; nine captions were lost, one with values stated nowhere else | `_floats` looks below a match too: 16 figures where there were 7 |
| M8 | Frontiers writes header cells as `<td>`; a group header stood over its first column alone | A cell in `<thead>` is a header, `<th>` or not |

Fixed among the low findings: a row ending in empty cells keeps every slot
(F3, F4, O3); a title row across the table is written once (N3); a signed
exponent on a number is a power, `2^−ΔΔCt` (A7); MathML `B^(^2)` reads
`B^2` and a summation limit is grouped, `∑_(j = 1)^jmax` (M8, I6); a
formula label stands apart, `(1)` (J10); a subscript loses its padding
(C2); a break after a slash adds no space (H1); back matter named by its
whole title alone is dropped, 70 sections in 18 papers; supplementary
legends are kept again (C4); a licence URL written only in the sentence
is the href (I6); a structured abstract leaves out its title, keywords and
supplement note (O5, C6); and a group of linked citations in brackets or
parentheses is dropped, `68% [10,56]` → `68%`, since a quote holding the
group holds its numbers beside the value (A6, B5, C4, L6, M4, O5 and
others). A linked citation outside such a group keeps its text.

Every number the second fix removed was accounted for, paper by paper,
old parse against new: 156 in dropped back matter, about 2,025 inside
linked citations, and the rest the B5 mark, the repeated N3 title, two
supplement DOIs in abstracts, and headings renamed or renumbered by the
fixes themselves. No other number left the text. Still open, all low: one
cell holding two values on two lines (C9) reads `679 676`; significance
stars sit on their number, `56.522***` (F4); an untitled how-to-cite note
(N3) stays as a section.

## What it means for the owed §1.5 run

The text the extractor will read is the text above, fetched again on
2026-10-14 with the fixed parser (31 of 59; B1 and D1 answered 500 again).
Nothing holds the extraction back but the key.
