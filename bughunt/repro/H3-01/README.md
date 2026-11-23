# H3-01: anchoring takes a quote's number in a unit that does not convert into the candidate's

**Statement.** `validate.anchor_candidate` compares a quote's number bare whenever the quote's unit does not convert into the candidate's unit, so 2.15 USD kg⁻¹ anchors on "2.15 USD/gal", 45 g L⁻¹ on "45% (v/v)", 5 g L⁻¹ on "5 mol/L", 0.45 g g⁻¹ on "0.45 h-1", 2 mmol g⁻¹ h⁻¹ on "2 mg/g/h" and 1.2 USD kg⁻¹ on "1.2 EUR kg-1", each labelled `valueBasis: converted`, and `biorepo.write` promotes such a record to `verified` or `gold` through the same check.

## Contract

- `CLAUDE.md:54`: "A record's value stands inside the verbatim quote it anchors to, in a unit its field is denominated in".
- `core/tests/test_anchor.py:324-326`, the suite's own reading of rule 3 for a unit mismatch: "The row says 4200 mg L-1. A candidate calling that 4200 g/L is claiming a number the sentence does not state, and rule 3 now sees it."
- `core/openferment_core/units.py:24-27`: "a pair the engine refuses on principle (`% TSP` to `g/L`) is `UnitError` carrying the recorded reason. Nothing here invents a conversion factor."
- `core/openferment_core/schema/units.json:578`, the refusal of USD gal⁻¹ to USD kg⁻¹: "guessing it would fabricate a price."
- `core/openferment_core/schema/fields.yaml:219-222`, `ethanol_titre`: "A concentration given as a percentage by volume needs the density of ethanol to become a mass, and belongs to no field."
- `core/openferment_core/models.py:934`: `ValueBasis` says "How §2.4 rule 3 found the value in the sentence"; `converted` there names a conversion the code made.

## Command

```
bash bughunt/repro/H3-01/run.sh
```

From the repository root. It makes a fresh test database `bh_r_h3_01_anchor` (migrated to head), runs `repro.py` with the repository's Python, keyless and offline, and drops the database on exit. Part A calls `anchor_candidate` on one-section documents. Part B keeps three anchored candidates in a project of that database and sends a reviewer's decisions through `biorepo.write`; the document's passages reach `biorepo.write` through `extract.passages`, served the way the suite's `held_documents` fixture serves them (`core/tests/conftest.py:162`).

## Expected

Each of the six candidates whose quote states its number in a unit `units.convert` refuses to turn into the candidate's unit is refused on rule `value`, as the same-family control is (45 g/L on "45 mg/L"). `biorepo.write` refuses to verify 2.15 USD kg⁻¹ on "2.15 USD/gal" and refuses a gold 45 g/L on "45% (v/v)", with rule `quote`, as it refuses a gold 45 g/L on "45 mg/L".

## Observed (both runs)

- Six of six cross-unit candidates ANCHORED, each with `valueBasis 'converted'`, while `units.convert` raises `UnitError` for every pair (density for the price, the dated exchange rate for EUR, the molar mass for mg to mmol, incompatible families for % and mol L⁻¹ and h⁻¹).
- "$2.15/gal" parses with no unit, and 2.15 USD kg⁻¹ anchors on it as `exact`.
- Control: 45 g/L on "45 mg/L" refused on rule `value`.
- `biorepo.write`: the accept of `cl1-R1-00000001` (2.15 USD kg⁻¹ on "2.15 USD/gal") is stored with provenance `verified`; a gold 45 g/L on `cl1-R1-00000002` ("45% (v/v)") is stored with provenance `gold`; the control gold 45 g/L on "45 mg/L" is refused on rule `quote` ("fails anchoring on rule 'value'").
- `openferment.records` holds `minimum_selling_price | 2.15 | USD kg⁻¹ | verified | ...2.15 USD/gal...` and `ethanol_titre | 45 | g L⁻¹ | gold | ...45% (v/v)...`.

`run1.log` and `run2.log` beside this file hold the two runs; both end `RESULT: DEFECT`.

## Likely cause

- `core/openferment_core/validate.py:780-789`, `_as_candidate_unit`: on `UnitError` it returns the quote's number unchanged (line 789), so rule 3 compares 2.15 USD gal⁻¹ with 2.15 USD kg⁻¹ as equal numbers. Its docstring calls this deliberate ("bare when the two do not convert ... so conversion only ever lets more through"), and `test_anchor.py:324` shows conversion also refuses what bare comparison let through.
- `core/openferment_core/validate.py:846-849`, `value_basis`: the label is `converted` whenever the quote's unit differs from the candidate's, whether a conversion took place or the comparison ran bare.
- `core/openferment_core/validate.py:783-785`: a quote with no parsed unit compares bare as `exact`; "$2.15/gal" reaches it because the parser reads no unit after a leading `$`.
- `core/openferment_core/biorepo.py:380-399`: `write` re-anchors every promoted value through `anchor_candidate` (line 392), so the same bare comparison passes an accept and a gold decision.

Fix size: small (refuse on rule `value` when the quote names a unit and `convert` raises, and label `converted` only when `convert` ran).
