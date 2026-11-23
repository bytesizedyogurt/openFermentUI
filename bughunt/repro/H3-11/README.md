# H3-11: what a model's estimate rests on is held to the number rule at the claim door alone

**Statement.** An estimate whose basis says "about 30% above the 2011 design report" drops its claim, and the same
words as `study_scenario`'s quantity note pass `numbers_in`, are stamped into the estimate's origin and enter the
run's basis as "estimated on <at>: about 30% above the 2011 design report".

**Verdict: reproduced, both runs `RESULT: DEFECT`.** Kind: inconsistency between two doors that keep the same field,
a `model-estimate` origin's `note`. Severity S3.

## Contract

- `docs/decisions/ADR-006-quantities-and-estimates.md:117-119` (the claim door): "A value with no single source, an
  id no tool returned, a label or a basis holding a number, or an estimate outside its own range drops its claim,
  counted with its reason".
- `docs/decisions/ADR-006-quantities-and-estimates.md:16-18`: "Every number a model, a person or a library supplies
  enters as `Quantity {value, unit, basis?, low?, high?, origin}`".
- `CLAUDE.md:55`: "A number in a Postdoc claim or a tool input stands only in a typed quantity with its origin; a
  claim with a number in its words is dropped and counted (ADR-006)."
- `core/openferment_core/postdoc_agent.py:279` (the plan schema): the basis is "What the estimate rests on, in words,
  with no number." `core/openferment_core/tools/__init__.py:318` (the tool's quantity): the note is "What the value
  rests on, in words." Both land in the same place, `Origin.note` of a `model-estimate`
  (`validate.py:357-358`; `tools/__init__.py:495`).
- The tree's other tool doors that keep a model's words hold them to the rule: a proposal's note, title and fields
  (`core/openferment_core/proposals.py:19` "hold no number (`validate.find_number`, Rule 1)", `:147-158`), and a
  runbook draft's title and labels (`core/openferment_core/runbook_draft.py:16-17`, `:39-42`).

What the tree says for the tool door, so the reader can weigh it:
`docs/decisions/ADR-006-quantities-and-estimates.md:120-128` says `numbers_in` "refuses every other number but `k`
and `limit`, so a module write's `fields` that hold a value and a unit in words stay words", and that the registry
"keeps the note the caller wrote and nothing else of what the caller put there". That sentence settles which parts
of the caller's origin survive the stamp; no line of the tree says a model's note may carry numbers, and the
module-write sentence names module writes' fields alone.

## Command

From the repository root: `bash bughunt/repro/H3-11/run.sh`

It makes the fresh test database `bh_r_h3_11_doors` and asks one question through the service's answer path
(`api._answer`, the body of `POST /api/ask`) of a stand-in model. The worker is the tests' own stand-in
(`core/tests/test_runs.py::StandIn`), so no BioSTEAM runs. In the one ask the stand-in writes the same words twice:

1. `study_scenario` on the sugarcane plant, one value (`stream.sugarcane.price`, 0.05 USD/kg) whose quantity note
   is `about 30% above the 2011 design report`;
2. `engine_run` on the scenario it kept;
3. the plan: claim c1 states one estimate whose basis is those words, and the control claim c2 one whose basis is
   `a delivered price above the package's`.

It prints the stores' rows, reads the `scenarios` and `runs` rows back with psql, checks that nothing under `core/`,
`src/`, `scripts/` or `examples/` changed, then drops the database and its scratch data directory. No service, no
key, no model call, no network.

## Expected

One rule for what a model's estimate rests on, in words. `find_number` finds `'3'` in the words, so c1 is dropped at
the claim door and `study_scenario` refuses the value in words at the tool door. No scenario, run or basis then
carries them. c2 is kept.

## Observed (run1.log and run2.log, the same both times apart from the ids and the moment)

```
plan: 1 kept, 1 dropped
  dropped  c1: value 1 (the cane's price): an estimate's basis holds a number ('3')
  kept     c2 (assumed) | origin model-estimate ... note "a delivered price above the package's"
  scenario ssc-… by claude-opus-5-5 | stream.sugarcane.price = 0.05 USD/kg | origin model-estimate by claude-opus-5-5
           at 2026-11-10T23:43:34.864946Z note 'about 30% above the 2011 design report'
  run … (done, assumed) by claude-opus-5-5
    input stream.sugarcane.price: origin model-estimate ... note 'estimated on 2026-11-10T23:43:34.864946Z: about 30% above the 2011 design report'
  artifact … (assumed) | basis input stream.sugarcane.price = 0.05 USD/kg | source model-estimate by claude-opus-5-5
           note 'estimated on 2026-11-10T23:43:34.864946Z: about 30% above the 2011 design report'
RESULT: DEFECT
```

The same model, the same ask and the same words: the answer screen never sees them, and the scenario row, the run's
inputs and the run's artifact keep them. The basis input's note joins the artifact's id hash
(`core/openferment_core/artifacts.py:137`), so the words stay in the kept artifact for good. They are shown on the
Studies screen (`src/screens/ProformaStudies.tsx:650`) and the run's page (`src/screens/ProformaRun.tsx:326`), and the
tool's own answer hands them back to the model (`core/openferment_core/tools/writes.py:606-607`).

## Likely cause

`core/openferment_core/tools/__init__.py:515-537` (`run`) calls `numbers_in` (`:400-422`), which reads JSON numbers
alone, then `stamped` (`:474-497`), which copies the caller's note into the origin as written (`:489-490`, `:495`).
Nothing on the tool path reads the note with `find_number`, the check `validate.claim_values` gives a claim's basis
at `core/openferment_core/validate.py:355-356`. Small fix: in `run`, when `ctx.author()` is a `model-estimate`, hold
each quantity's own note to `find_number` and refuse in words, as `proposals._held_to_rule_one` does. The service's
own words added later (the moment in `basis.estimate_source`, a reading's conversion) stay outside the check. One row
in `core/tests/test_tools_study.py` with a note that holds a number.

## Severity

S3: an edge case of the number rule. A model has to write numbers into its note, and the value keeps its
`model-estimate` mark and the model's name, and the run stays `assumed`, so no number is shown as sound. The numbers
carry no origin of their own, name a design report year nobody cited, and outlive the ask in a kept artifact.
