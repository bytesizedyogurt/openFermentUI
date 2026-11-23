# H3-16: a micro unit written with the Greek letter mu does not normalise, and its candidate is refused

**Statement.** The unit table spells micro with the micro sign U+00B5 in all ten keys and five aliases that hold
it, and `units.normalize` folds no Greek small letter mu U+03BC onto it, so `μg/mL`, `μL`, `μM` and every other
micro unit typed with U+03BC normalise to None, and a candidate that copies such a unit as the paper wrote it is
refused on rule `unit` ("does not normalise").

**Verdict: reproduced, both runs `RESULT: DEFECT`.** Kind: Broken use. Severity S3 (a value a paper reports is lost
from Intake for any text that carries U+03BC; a candidate written by hand with the unit retyped in U+00B5 anchors
against the same Greek-mu quote). Fix size: small.

## Contract

- `core/openferment_core/extract.py:91-92`, the extractor's system prompt: "Copy the quote verbatim from the
  passage you cite. Never paraphrase, never tidy, never translate a unit."
- `core/openferment_core/extract.py:111`: "Give the unit as the paper wrote it." The tool schema at
  `extract.py:186` repeats it: "The unit as the paper wrote it".
- `core/openferment_core/units.py:121`, `normalize`'s promise: "The table key for a unit as somebody wrote it, or
  None."
- `core/openferment_core/validate.py:1137-1140`, rule 4: "The unit normalises, into the field's family", refused
  as "unit ... does not normalise".

The extractor is told to keep the paper's unit untranslated, and the engine that judges it reads only one of the
two code points papers and PDF text use for micro. Unicode's own compatibility form of U+00B5 is U+03BC
(`NFKC('µ') == 'μ'`), and a live extraction of 2026-10-16 emitted `colonies/μg DNA` with U+03BC: it stands in
`core/tests/test_units_minus.py:18` among the units of dropped values.

The candidate also cites `units.py:17-22` ("a unit engine on the Python side that agrees with the browser about
what `mg·L⁻¹` means"). That part holds: the browser's `normalizeUnit` (`src/engine/units.ts:374-391`) returns null
for the same Greek-mu spellings, so the two engines agree with each other. The defect stands on the lines above.

## Command

```
bash bughunt/repro/H3-16/run.sh
```

A fresh database `bh_r_h3_16_svc`, a keyless service on the first free port of 9200 to 9209, project `h3-16`, two
pasted one-sentence documents ("Secreted protein reached 150 μg/mL ..." with U+03BC, and the same with U+00B5),
and three `biorepo_write` `candidate` calls at the HTTP tool door in the model's lane (`repro.py`). Before that it
prints the contract lines and `units.normalize` on seven spellings in each code point; after it, the browser's
`normalizeUnit` on three of them (`browser.mts`, through `tsx`, read only). No model call, no network, no worktree
(nothing is mutated or built); the service is stopped and the database dropped on exit.

## Expected

`μg/mL` (U+03BC) normalises to `µg mL⁻¹` as `µg/mL` (U+00B5) does, and a candidate whose unit is copied as the
paper wrote it is proposed under either spelling.

## Observed (both runs)

- `units.normalize`: the micro sign gives a key and the Greek mu gives None on 7 of 7 spellings (`µg/mL`,
  `µg/L`, `µL`, `µM`, `µl`, `µmol/m²/s`, `µg mL⁻¹`); `units.convert(150, 'μg/mL', 'g L⁻¹')` raises
  `UnitError: Unknown unit: μg/mL`.
- Table keys holding U+00B5: 10, holding U+03BC: 0; alias keys holding U+00B5: 5, holding U+03BC: 0.
- Greek-mu document, unit as written: `biorepo_write refused on rule unit: unit 'μg/mL' does not normalise`.
- Micro-sign document, unit as written: `state='proposed'`.
- Greek-mu document, unit retyped with U+00B5: `state='proposed'` (the quote rule reads the number; only the unit
  rule refuses).
- The browser's `normalizeUnit`: `"µg/mL" -> "µg mL⁻¹"`, `"μg/mL" -> null`; the same for `µL` and `µM`.

Logs: `run1.log`, `run2.log`.

## Likely cause

`core/openferment_core/units.py:91-101`: `_STRIP_STEPS` folds middots, the minus sign, the en dash and the
superscripts, and holds no step mapping U+03BC to U+00B5, so `normalize` (`units.py:120-146`) misses every key and
alias in `schema/units.json`, all spelled with U+00B5. The browser's twin `strip` at `src/engine/units.ts:384-385`
lacks the same step; `units.py:11-15` holds the two to the same sequence of replacements, so a fix adds the fold
on both sides (and the fixture `scripts/export-unit-fixtures.ts` records it). Confidence: high.
