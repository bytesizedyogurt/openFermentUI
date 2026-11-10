# H3-02: numbers in words pass Rule 1, and the claim keeps its record's class

**Statement.** `validate.find_number` finds no number in "two dollars per gallon", "ten per cent", "ten tonnes", "two thirds", "hundreds of litres" or a superscript "²", so `validate_plan` keeps a Postdoc claim stating any of them and marks it with its cited record's class (`verified`), while the same claim written with a digit or a word the rule knows is dropped and counted.

## Contract

- `CLAUDE.md:55`: "A number in a Postdoc claim or a tool input stands only in a typed quantity with its origin; a claim with a number in its words is dropped and counted (ADR-006)."
- `docs/decisions/ADR-006-quantities-and-estimates.md:26-27`: "Claims carry numbers only in a typed `values` list. Text with a bare number is still dropped and counted."
- `core/openferment_core/validate.py:11-12`: "A claim of the agent's plan is rejected when any of `validate_plan`'s six rules holds: among them, its text contains a number, in digits or in words".
- `core/openferment_core/validate.py:136-138`: "a determiner is one through ten before a word. Either still fails when the next word is a unit, so "3 g/L on day 3", "day 3 g/L" and "two days" keep tripping the rule."
- `core/openferment_core/validate.py:57-58`: "Digits in any form a model might reach for: ... ² (superscript)."
- `src/components/AnswerPlanView.tsx:7-8`: "Nothing here prints model prose containing a quantity, because the validator guarantees the prose has none". Line 177 prints `claim.text` as written.

## Command

```
bash bughunt/repro/H3-02/run.sh
```

From the repository root. It runs `repro.py` on the tree as it stands (core matches 2047f5a), keyless, with bytecode writing off. The defect lives in pure functions (`find_number`, `validate_plan`, `evidence_pool.build`, `postdoc_agent.held_to_rule_one`) that read no database and call no service, model or network, so the script makes no database or service and has nothing to clean up.

What it does:

1. Six pairs through `find_number`: a sentence stating a quantity in words, beside a twin stating it in digits or in a word the rule knows (2 dollars, ten percent, ten kilograms, half, a hundred, ½).
2. The real evidence pool (`evidence_pool.build`) over one candidate a named reviewer verified, its class computed by `biorepo.provenance_of`: `verified`.
3. All twelve sentences as claims citing that record, through `validate_plan`, the call `postdoc_agent.py:752` makes on the model's claims.
4. One gap through `held_to_rule_one`.

## Expected

Each of the six word-form claims dropped and counted with its reason, as each twin is.

## Observed (run1.log, run2.log)

- `find_number` returns None for all six word forms and finds the number in all six twins.
- `validate_plan` keeps all six word-form claims with provenance `verified` (the cited record holds 0.72 USD kg⁻¹), and drops and counts the six twins: `rejected 6`.
- `held_to_rule_one` keeps the gap "Two thirds of the plant's cost has no record behind it."
- On screen, `AnswerPlanView` prints the kept claim's words verbatim beside the record's verified value, so "two dollars per gallon", a number the model wrote, stands under a verified tick.

The run also prints three forms `practice.py:73-76` names as `find_number`'s gaps (pH5, x10, doubled). That comment says "Postdoc's claims keep the validator they were tuned against", so the code knows of those three; the verdict rests on the six pairs alone.

## Likely cause

- `core/openferment_core/validate.py:152-154` with `:157-166`: `_DETERMINER` blanks one to ten before any next word `_is_unit_word` misses. That test knows the closed list at `:141-148` and whatever `units.normalize` resolves, and `units.normalize` returns None for dollars, per, cent, tonnes, bar, kelvin and ppm. So "two dollars", "Ten per cent" and "Ten tonnes" are blanked as counting words.
- `core/openferment_core/validate.py:74-76`: `_WORD_NUMBER` requires no letter after the word, so the plurals "thirds", "quarters", "hundreds", "thousands" and "dozens" match nothing.
- `core/openferment_core/validate.py:60`: `_DIGIT`'s ranges (`\d`, U+00BC-U+00BE, U+2150-U+218F, U+2070-U+209F) leave out U+00B2, U+00B3 and U+00B9, the comment's own example "²" among them.
