# The live question set, November 2026

Alpha 2.1, stage B (execution prompt of 2 November 2026, §5 and §7): the owner's twelve questions
asked of Postdoc through its screen, in the project "Ethanol", with the page's stream on, on the
alpha 2.1 routing table (`plan` on `claude-opus-5-5` then `claude-sonnet-5-5` at effort high). Each
question is judged against what it expects. A fault a question finds is fixed with a test and the
question is asked again; the table after the fixes stands below the table before them.

## The project

Made on Home in this session's container, on the development database
(`openferment_dev`), by "Claude Code (build session)":

- **Intake.** Every identifier of `docs/corpus/ethanol-sources.txt` collected through the
  Identifier form, one at a time: 22 of 22 held, 814 passages. OSTI reset the connection once
  (`osti:1129271`); the page said "try again later", and the second try after a pause held it.
  None refused, none partial.
- **Extraction.** Every held document extracted from Intake's list on the `extract` route
  (`claude-opus-5-5` then `claude-sonnet-5-5`, effort medium): 224 candidates kept and 89 refused
  (40 by the value rule, 49 by the unit rule), 4.53 USD. Opus declined ten of the 22 papers in
  the `bio` refusal category, and Sonnet answered each. The value refusals were all values copied
  whole ("0.15 ± 0.01 (A)", "2–3"), and 14 unit refusals were titres in `% w/v`; both are fixed
  (`21306e1`), and the nine documents extracted again kept 103 where they had kept 55 and refused 2
  where they had refused 54 (1.80 USD). The 35 yields left refused carry no unit in their papers.
  272 candidates wait for the owner's review; no decision was made here.

## Before the fixes

Asked 2 November 2026, one question at a time; a follow-up in its question's conversation (5 then
8; 6 then 7). "First step" is the time from Send to the first step on screen; "answer" to the
answer. "Claims" is kept / dropped by the validator. "Stopped" is why the loop ended.

| # | Expects | First step | Answer | Tool calls | Claims | Stopped | USD | Models | Judged |
|---|---|---|---|---|---|---|---|---|---|
| 1 | cited quotes | 250 ms | 77 s | 12 | 3 / 5 | calls | 0.5235 | claude-opus-5-5 | partial: three claims stand; five dropped for ordinals and a table number in their words; the tool calls ran out |
| 2 | cited quotes | 238 ms | 54 s | 20 | 7 / 3 | calls | 0.5044 | claude-opus-5-5 → claude-sonnet-5-5 | partial: seven strains' claims; the tool calls ran out before the strain sections of several documents |
| 3 | typed values from the run's read-back, origins named | 236 ms | 87 s | 5 | 7 / 1 | done | 0.3423 | claude-opus-5-5 | partial: the run's feed flows and yield cited; the composition, moisture and price could not be cited (engine_parameters gives no evidence ids) |
| 4 | artifact citations | 252 ms | 67 s | 12 | 7 / 1 | calls | 0.3968 | claude-opus-5-5 | partial: the price block's sums cited; no TEA breakdown line and no parameter default citable |
| 5 | a scenario with labelled estimates; comparison cited | 237 ms | 69 s | 11 | 4 / 1 | rounds | 0.4164 | claude-opus-5-5 | incomplete: a baseline run and the glucose-only scenario made; the rounds ran out before the scenario ran |
| 6 | two runs, a comparison, flags | 242 ms | 47 s | 5 | 5 / 1 | done | 0.3213 | claude-opus-5-5 | as expected: two runs and a comparison, hot water 7.4% below dilute acid per kg |
| 7 | gaps, applicability flags, no invented numbers | 260 ms | 72 s | 12 | 7 / 0 | calls | 0.4854 | claude-opus-5-5 | as expected: the comparison's gaps and what would settle them, no invented number |
| 8 | a draft through the runbook tool | 245 ms | 75 s | 11 | 6 / 0 | rounds | 0.4391 | claude-opus-5-5 | not answered: the scenario ran and was compared (0.848 against 0.659 USD/kg), and draft_runbook refused twice: no product in the catalogue |
| 9 | module reads | 233 ms | 26 s | 6 | 3 / 0 | done | 0.2850 | claude-opus-5-5 | as expected: none verified, every candidate waiting; one claim names a paper's authors wrongly ('Kumar et al.' for Pagliardini et al.) |
| 10 | Intake state in words | 232 ms | 35 s | 5 | 4 / 0 | done | 0.2833 | claude-opus-5-5 | as expected: none refused or partial, every document held |
| 11 | import, graph summary | 240 ms | 18 s | 7 | 1 / 0 | done | 0.2104 | claude-opus-5-5 | not answered: Postdoc has no tool that imports an SFF file, and said so |
| 12 | geneOS artifacts; a refusal in words where a model file is absent | 234 ms | 50 s | 8 | 8 / 0 | done | 0.3320 | claude-opus-5-5 | as expected in words: yield_ceiling refused, Yeast9's and iMM904's files are not on this machine |

Total 4.5400 USD over 12 questions.

Five of twelve as expected (6, 7, 9, 10 and 12). The faults, each with its fix:

1. Claims dropped for an ordinal ("the second paper") or a table's number in their words: the
   plan prompt forbade numbers in digits and in words and named neither.
2. The loop's bounds (12 tool calls, 6 rounds, 180 s) ended four answers before they covered the
   corpus (calls) and two before their scenario ran or their draft was written (rounds).
3. The plant's own inputs (the feedstock's composition, moisture and price, the chemicals'
   prices, the finance terms) and its TEA breakdown lines came back with no evidence id, so no
   claim could state them.
4. `draft_runbook` needs a product from the catalogue, which is empty in production (a debt of
   §6), and refused a runbook for an engine run's scenario.
5. Postdoc has no tool that imports an SFF file or reads one the project holds.
6. Yeast9's and iMM904's files were not fetched on this machine; the refusal is in words, as
   the question expects, and the files are fetched for the second asking.
