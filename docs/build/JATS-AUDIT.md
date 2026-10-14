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

## What it means for the owed §1.5 run

Extraction over this text would anchor candidates to sentences whose numbers
the parser altered (the anchoring rule checks that a value sits in its
quote, so an altered quote can carry an altered value), and would misread
table columns. The fixes belong in `intake.py` and its tests, which no step
of Phase 1 names, so the choice of when to make them is Sean's. Until it is
made, `## Live owed` in `STATE.md` holds the extraction back.

The per-paper results and every finding's evidence are in the workflow
journal of the session that ran the audit; the four reproductions above
need nothing but the fetched JSON and Europe PMC.
