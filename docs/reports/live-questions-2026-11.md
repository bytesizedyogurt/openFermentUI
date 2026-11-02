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

## After the fixes

Asked again on 2 November 2026 after `fb03eb2`, in the same project and on the same routes, all
twelve through the Postdoc screen (5.01 USD). Q1 then ran out of room, Q5 lost two claims to
fractions in words, and Q8's draft was refused three times for measure units the unit table did
not hold; each was fixed with a test and those three were asked a third time (1.60 USD). The rows
for 1, 5 and 8 are the third asking's; the rest are the second's.

| # | Expects | First step | Answer | Tool calls | Claims | Stopped | USD | Models | Judged |
|---|---|---|---|---|---|---|---|---|---|
| 1 | cited quotes | 362 ms | 107 s | 22 | 5 / 5 | done | 0.7502 | claude-opus-5-5 | as expected, short in coverage: four documents' titres with their conditions in words, each citing its passages and records, and a claim that no other document's titre was found; five dropped (an ordinal, a numeral, a quote past 300 characters, a quote that was not a whole sentence), and the gaps say the candidate list was read in part |
| 2 | cited quotes | 238 ms | 68 s | 29 | 9 / 1 | done | 0.5692 | claude-opus-5-5 → claude-sonnet-5-5 | as expected: nine claims on the strains (CEN.PK113-7D and its engineered descendants, S288C, Ethanol Red, BY4743, AFY, the distillery isolates, the Tuscan wine isolates), each citing a passage; Opus declined in the `bio` category and Sonnet answered |
| 3 | typed values from the run's read-back, origins named | 235 ms | 90 s | 7 | 8 / 0 | done | 0.3710 | claude-opus-5-5 | as expected: the feedstock's composition (eleven shares), moisture, flow and price as typed values read back from the run, each named the package's own; their match to the Humbird report is labelled the model's comparison, and the report's price per dry ton converted is a labelled estimate |
| 4 | artifact citations | 269 ms | 73 s | 13 | 8 / 0 | done | 0.4472 | claude-opus-5-5 | as expected: the TEA lines per kilogram and per year, the capital, the package's prices and finance terms, each cited by its evidence id, and what a person could change in a scenario |
| 5 | a scenario with labelled estimates; comparison cited | 236 ms | 97 s | 11 | 8 / 0 | done | 0.4782 | claude-opus-5-5 | as expected: a glucose-only scenario (every reaction that consumes xylose set to none, the model's estimate) made, run and compared; ethanol down by a third, the solved price up 28.7 %, NPV negative, each cited; the claims are `assumed` and say why |
| 6 | two runs, a comparison, flags | 231 ms | 61 s | 7 | 7 / 0 | done | 0.3748 | claude-opus-5-5 | as expected: two runs and a comparison, hot water 7.4 % below dilute acid per kg, the gap in other materials; the flags name the IB-only runs, the single base case and the literature not searched |
| 7 | gaps, applicability flags, no invented numbers | 276 ms | 82 s | 15 | 8 / 0 | done | 0.5231 | claude-opus-5-5 | as expected: what is uncertain and what measurement would settle it, no number of its own; it found that the pretreatment reactor carries the same conversions under both pretreatments, which the package's code confirms (below) |
| 8 | a draft through the runbook tool | 387 ms | 54 s | 7 | 4 / 0 | done | 0.3750 | claude-opus-5-5 | as expected: a draft of the scenario's run with six point predictions read from it and four measures in kg/h, kg/kg and USD/kg; one measure in USD per year refused, said as a gap |
| 9 | module reads | 233 ms | 27 s | 5 | 4 / 0 | done | 0.2826 | claude-opus-5-5 | as expected: none verified, every candidate waiting, the papers named by title (the first asking's wrong authors are gone) |
| 10 | Intake state in words | 240 ms | 32 s | 5 | 4 / 1 | done | 0.2973 | claude-opus-5-5 | as expected: none refused or partial, every document held, the licences in words, and the gap that a fetch refused before a document was held leaves no row to read |
| 11 | import, graph summary | 256 ms | 45 s | 1 | 6 / 1 | done | 0.2489 | claude-opus-5-5 | as expected: SF_BST_15 imported as the model's and read as a sugarcane plant (a cane mill, juice clarification, fermentation, distillation, utilities) from its graph's counts and its boundary's flows, each cited; not valid against SFF 0.2.4, with the toolkit's findings |
| 12 | geneOS artifacts; a refusal in words where a model file is absent | 236 ms | 66 s | 7 | 6 / 2 | done | 0.3541 | claude-opus-5-5 | as expected: iMM904 and Yeast9 give the same ceiling on glucose (0.511 g g⁻¹) as geneOS artifacts, and every recorded yield sits below it; one value is labelled the molar basis while it carries the mass basis's number, for the judge of stage C to catch |

Eleven of twelve as expected (2 to 12), and Q1 as expected in kind while short in coverage: the
stage's gate of ten is met. 6.6155 USD over the fifteen answers.

The faults the second asking found, each with its fix:

7. The answer over 22 documents ran out of room: the plan's ceiling of 8,000 tokens holds the
   model's thinking too. A turn now writes as much as the question's budget has left to pay for,
   between 8,000 and 32,000 tokens, and the loop still holds back an 8,000-token answer before it
   asks another round; the owner's default ask budget (0.75 USD) keeps the old behaviour
   (`postdoc_agent._turn_tokens`; ADR-008, Implementation 9).
8. The unit table held no rate of mass and no kilogram per kilogram, so a runbook of a plant's run
   could not measure its feed or its ethanol: `kg h⁻¹` (with `g h⁻¹`, `kg d⁻¹`, `t d⁻¹`, `kg s⁻¹`)
   and `kg kg⁻¹` are in both tables, held equal by the unit fixtures.
9. Fractions in words ("a third", "a quarter") dropped two claims: the plan prompt names them
   beside the ordinals.

What the answers found that is the package's, for the owner: biorefineries 2.35.1 builds the
hot-water pretreatment with the same `PretreatmentReactorSystem` as dilute acid, at another
temperature and with the same reaction conversions (`biorefineries/cellulosic/systems/
pretreatment/hot_water.py` against `dilute_acid.py`), so question 6's comparison of the two rests
on dilute acid's conversions. A study of hot water needs measured conversions set as a scenario's
values.

## The screens

The owner's work on the plants, done from the screens in Chromium on 2 November 2026 in the same
project, signed "Claude Code (build session)" (the walk is kept beside this session's scratch
files; its steps and ids are below).

Before it, the screens could not do it: a person could list a project's engine runs, run a
scenario Postdoc had made, compare runs, make a runbook from a run and export, and could not run a
plant, make a scenario of their own, import an SFF file, or see the project's SFF records listed.
The service held every route (`POST /api/library/{plant}/run`, `POST /api/studies/scenarios`,
`POST /api/flowsheets/import`, `POST /api/flowsheets/library/{id}`, `GET /api/flowsheets`); the
screens did not call them. Studies now has **Run a plant** (every plant the installed package
built here, each in the configurations it built in, those that did not build named with the
package's words); a run's page has **A scenario from this run** (parameters found by words, each
value set as the person's assumption, made and run in their name); and **Flowsheets**
(`/flowsheets`) lists the project's SFF records, imports a file and keeps a reference file of the
toolkit. `pnpm check:state` holds the configuration offer and the refusals an import answers;
`scripts/walk.ts` (`pnpm prove` step 9) walks the three.

| Step | What the screen did |
|---|---|
| Run every plant | cane (S1), cellulosic, corn, cornstover, lipidcane, milk, oilcane (S1), sugarcane: each ran, each wrote its SFF file |
| The composed flowsheet | `cellulosic_ethanol_v0` in dilute acid with IB and with SCF, and hot water with IB and with SCF: each ran (dilute acid, IB and hot water, IB answered from the runs Postdoc had made) |
| Not offered, and why | fattyalcohols, gas_fermentation, lactic and LAOs do not build under biosteam 2.54.0; the composed flowsheet's AFEX configurations are infeasible here (BioSTEAM's InfeasibleRegion at M207) and its alkaline ones do not build (an undefined `Solids` alias at U302): each named on the card with the package's words |
| The package's own run | `e7efa2505b4633de`: its SFF graph (68 units drawn), its parameters and its cost breakdown |
| A glucose-only scenario | from that page, the xylose reactions of the seed train and the co-fermentation set to zero as the person's assumption, made and run: run `8f5684ad6d0602b8`, `assumed`, its eight values marked as the person's. (The walk's own filter left the two xylose-to-cell-mass reactions at the package's values; Postdoc's scenario of question 5 set all ten. The walk's check read the run's status before the page had loaded it; the service holds the run as done.) |
| Compare | the glucose-only run against the package's own (`ff404f1f5527d425`), and hot water against dilute acid (`58f76e9081e6449c`), 19 rows each |
| A runbook, locked | `rb-study-38d1b800d164` from the glucose-only run, three predictions, locked on its page, and Studies lists it locked |
| Export | the package downloaded: 20 files, `study.md` among them, each run's SFF file under `sff/` |
| Import | a run's SFF file taken from the export and imported on Flowsheets (`sff-800b7f0db55e3b19`); the toolkit's reference file SF_BST_01 kept (`sff-f9d0ac8162d24c6f`); Flowsheets lists 19 records: 16 written by runs, 2 reference files, 1 imported |
| Restart | the service stopped and started: Studies lists every run made before it, five comparisons and the locked runbook; every run's page, both comparisons, the runbook (locked), the imported record and Flowsheets read back as they were |

No console error on any page, in either phase.
