# H3-10: a claim's estimate carries numbers in its unit, a field no rule reads

**Statement.** `validate.claim_values` holds an estimate's label and basis to the number rule and takes its
unit as any non-empty text, so `USD/gal, about 40 cents above the 2011 design` stands as the unit of a value
the service keeps in a Postdoc turn.

**Contract.**

- `docs/decisions/ADR-006-quantities-and-estimates.md:26`: "Claims carry numbers only in a typed `values`
  list. Text with a bare number is still dropped and counted."
- `docs/decisions/ADR-006-quantities-and-estimates.md:117-119`: "A value with no single source, an id no
  tool returned, a label or a basis holding a number, or an estimate outside its own range drops its claim,
  counted with its reason".
- `CLAUDE.md:55`: "A number in a Postdoc claim or a tool input stands only in a typed quantity with its
  origin; a claim with a number in its words is dropped and counted (ADR-006)."
- `docs/api/postdoc.md:46-47`: "A plan's claim states no number in its words; the numbers it states are its
  `values` (`ClaimValue`, ADR-006): a label in words and a `Quantity` whose origin the validator wrote."

The `40` and the `2011` in c1's unit are numbers the claim states in words. Neither is a value: each stands
with no quantity and no origin of its own. ADR-006 names the label and the basis as the words a value may
hold, and the unit is the one string of an estimate left open to a number in words.

**Command** (from the repository root): `bash bughunt/repro/H3-10/run.sh`

It makes a fresh test database (`bh_r_h3_10_claims`), makes a project in it, and asks one question through
the service's own answer path (`api._answer`, the body of `POST /api/ask`) of a stand-in model that answers
one plan with three claims, each stating one estimate of 2.1:

| claim | estimate's unit | estimate's basis |
|---|---|---|
| c1 | `USD/gal, about 40 cents above the 2011 design` | `the design report's price structure` |
| c2 (control) | `USD/gal` | `about 40 cents above the 2011 design` |
| c3 (control) | `USD/gal` | `the design report's price structure` |

It reads the kept turn back from the conversation store and from `openferment.turns`, then drops the
database. No service, no key, no model call and no network.

**Expected.** c1 dropped and counted as c2 is (its unit holds a number in words, and the unit table reads no
unit there); c3 kept; the plan's count `1 kept, 2 dropped`.

**Observed** (run1.log and run2.log, the same both times):

```
plan: 2 kept, 1 dropped
  dropped  c2: value 1 (the selling price): an estimate's basis holds a number ('4')
  kept     c1 (assumed) | value 2.1 unit 'USD/gal, about 40 cents above the 2011 design' origin model-estimate ...
  kept     c3 (assumed) | value 2.1 unit 'USD/gal' origin model-estimate ...
turn-… | answered | c1 | assumed | USD/gal, about 40 cents above the 2011 design
the unit table reads c1's unit as: None; it reads 'USD/gal' as 'USD gal⁻¹'
RESULT: DEFECT
```

The same words drop c2 from its basis and pass in c1's unit. The answer screen prints the unit beside the
value in the number font (`src/components/AnswerPlanView.tsx:73-75`), so the reader sees "2.1 USD/gal, about
40 cents above the 2011 design". The claim stays `assumed` under the model's name, so the extra numbers sit
under the estimate's mark; they carry no origin of their own and name a design report year nobody cited.

**Likely cause.** `core/openferment_core/validate.py:342` reads the unit with `str(...).strip()`, and
`validate.py:347-348` checks it for being non-empty alone; the basis gets `find_number` at
`validate.py:355-356`, the label at `validate.py:312-313`, and the unit nothing. The plan schema says "with no
number" for the label and the basis and leaves the unit's string bare (`core/openferment_core/postdoc_agent.py:268,276,279`).
`find_number` alone does not fit a unit: it finds `'⁻'` in a record's own `USD kg⁻¹`. The unit table
(`units.normalize`, `core/openferment_core/units.py:120`) reads `USD/gal`, `g L-1` and `USD kg⁻¹` and reads
nothing in c1's unit, so a check there, or a number rule that masks a unit's exponents, would hold the unit
to the same line as the label and the basis. Small fix, with one more row in
`core/tests/test_postdoc_agent.py::test_a_value_that_cannot_stand_drops_its_claim`.

**Severity.** S3: an edge case of the validator's number rule. A model has to write the words into the
unit, and the claim keeps its `assumed` mark and the model's name, so no number is shown as sound.
