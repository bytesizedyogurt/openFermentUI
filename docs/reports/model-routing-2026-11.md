# Model routing, November 2026

Alpha 2.1, stage C (execution prompt of 2 November 2026, §4, §5 and §7): the owner's twelve
questions asked on three route tables and scored by code and by a judge model, so the routing
table's defaults rest on measurement. **The measurement stopped part way:** at 20:01 UTC on
2 November the Anthropic account behind `core/.env`'s key reached its own usage limit, and every
call since answers HTTP 400, "You have reached your specified API usage limits. You will regain
access on 2026-12-01 at 00:00 UTC." That limit is the account's, set in the Anthropic console,
and separate from openFerment's daily cap (150 USD; `openferment_dev`'s spend table holds
19.75 USD over 275 calls for the day). Only the account's owner can raise it. What was measured
before it is below; the defaults wait for the rest.

## Method

- **The suite.** The twelve questions of `docs/reports/live-questions-2026-11.md`, kept as the
  evaluation suite `ethanol` (`pnpm eval seed --suite ethanol`), each with what a good answer does
  in words. Asked in the project "Ethanol" (22 ethanol sources, 814 passages, 272 candidates) on
  this container's `openferment_dev`, through the service's answer path, one table at a time.
- **The tables**, each set by `OPENFERMENT_ROUTES` for one command, `index` on
  `claude-haiku-5-5` at low and `judge` on `claude-opus-5-5` at high in each:

  | Tag | `plan` and `explain` |
  |---|---|
  | `haiku` | `claude-haiku-5-5` alone, effort high |
  | `sonnet` | `claude-sonnet-5-5` alone, effort high |
  | `opus` | `claude-opus-5-5` then `claude-sonnet-5-5`, effort high (`core/.env`, the prompt's §4) |

- **The code's scores** (`postdoc/evaluate.py`): `tools`, the share of the question's tool groups
  the answer reached; `citations`, the share of kept claims citing what the question expects;
  `estimates`, a labelled estimate where one is asked for and none where one is forbidden;
  `bareNumbers`, 1 when no claim was dropped for a number in its words.
- **The judge's scores**, each the judge model's and kept with its id: `answers`, `grounded`,
  `labelled` and `coverage`, from 0 to 1, read from the question, what a good answer does, every
  claim with what it cites (evidence values, record quotes, passage words), the gaps and the
  tools called. A second judge on `claude-sonnet-5-5` was to read every answer again
  (`pnpm eval judge`); the limit came first.

## What was measured

| Table | Q | Tools | Citations | Estimates | Bare numbers | Claims kept / dropped | Tool calls | Seconds | USD | Judge (Opus): answers, grounded, labelled, coverage |
|---|---|---|---|---|---|---|---|---|---|---|
| haiku | 1 | 1.0 | 1.0 | 1.0 | 0.0 | 7 / 4 | 24 | 131 | 0.0780 | declined (`bio`) |
| haiku | 2 | 1.0 | 0.923 | 1.0 | 1.0 | 13 / 3 | 24 | 126 | 0.0288 | declined (`bio`) |
| haiku | 3 | 1.0 | 1.0 | 1.0 | 1.0 | 6 / 0 | 9 | 87 | 0.0145 | 0.85, 0.75, 0.95, 0.80 |
| haiku | 4 | 1.0 | 1.0 | 1.0 | 1.0 | 10 / 0 | 11 | 55 | 0.0138 | 0.85, 0.83, 1.00, 0.85 |
| sonnet | 1 | 1.0 | 1.0 | 1.0 | 0.0 | 3 / 4 | 10 | 44 | 0.2247 | 0.55, 0.78, 0.90, 0.50 |
| sonnet | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 12 / 1 | 23 | 70 | 0.3181 | 0.85, 0.68, 0.95, 0.80 |
| sonnet | 3 | 0.0 | 0.0 | 1.0 | 1.0 | 4 / 1 | 7 | 45 | 0.1481 | the limit came first |
| opus | 1 | 1.0 | 1.0 | 1.0 | 0.0 | 5 / 5 | 23 | 119 | 0.8214 | the limit came first |

Every other answer of the three tables was refused by the account's limit before any model read
it; those rows are kept with the refusal and left out of everything here. Stage B's three
askings of all twelve on the Opus table, judged by hand against what each question expects, stand
in `docs/reports/live-questions-2026-11.md` (eleven of twelve as expected, the twelfth short in
coverage; 0.21 to 0.82 USD and 27 to 107 seconds an answer).

The judge's words, cut short, and haiku's Q3 put in words of what the judge found:

- haiku, Q3: read four of the feedstock's values back from a run, each labelled the package's own,
  set two of them beside a design report the answer named in words, and kept honest gaps; the judge
  found one statement overstated.
- haiku, Q4: "The cost lines, selling prices and package-set input prices are well cited and add
  up correctly… The part on which inputs a person could change…" is the weaker half.
- sonnet, Q1: "names three documents with record-backed titres, but conditions are given only
  thinly…"
- sonnet, Q2: "broad… the core … claims are well cited. Several claims add strain names or
  details that their cited passage" does not bear out.

## What the measurements say, as far as they go

1. **Cost.** On the same questions Haiku answered for 0.014 to 0.078 USD, Sonnet for 0.15 to
   0.32, Opus for 0.82 (Q1; 0.21 to 0.82 in stage B). Haiku is twenty to fifty times cheaper than
   Opus per answer.
2. **Time.** Haiku took longest on the literature questions (126 and 131 s, using all 24 tool
   calls), Sonnet the least (44 and 70 s), Opus between (119 s on Q1).
3. **Quality, where judged.** On the plant questions Q3 and Q4 the Opus judge gave Haiku's answers
   0.85 for answering and 0.75 to 0.83 for grounding. On the literature questions it gave Sonnet's
   0.55 and 0.85 for answering and 0.78 and 0.68 for grounding, faulting claims that add details
   their passages do not hold. Sonnet's Q3 never ran the plant (tools and citations 0), where
   Haiku's and Opus's did. Five judgements are too few to rank three models on.
4. **Refusals.** Opus as judge declined Haiku's answers to Q1 and Q2 in the `bio` category (two of
   the seven judgements it was asked for), and stage B's Opus declined ten of the 22 extraction
   papers the same way, Sonnet answering each. A route that reads yeast literature on Opus needs a
   second model behind it, and the judge route as much as any.
5. **Dropped claims.** Every table dropped claims on Q1 for numbers in words (four to five), as
   stage B's Opus did; the validator holds them, and the prompt names the forms.

## Decision

The routing table's defaults stay as they are until the comparison is finished: no measurement
here ranks the three models, and setting a default on eight answers would claim more than was
measured. `core/.env` keeps the prompt's §4 table. Two things the measurements do show, for the
owner to act on:

- The `judge` route should name a second model: `{"models": ["claude-opus-5-5",
  "claude-sonnet-5-5"], "effort": "high"}`; each judgement is labelled with the model that gave
  it, so a mean per judge stays honest. The code's default judge route already falls back to
  Sonnet; `core/.env`'s, set from §4, does not.
- Haiku is worth measuring for `plan` on the plant questions, where its two judged answers stood
  with Opus's at a twentieth of the cost.

## To finish it

Finished in the section of 8 November 2026 below, as far as the account allowed: alpha 2.2's stage F
asked the fourteen of the rebuilt project on four tables, three of them whole, with one judge; its
own "To finish it" lists what the account's return allows. The commands as alpha 2.1 wrote them:

Once the account answers again (the date it names, or the owner raising the limit):

```
cd core
OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES='<the table>' pnpm eval run --live --suite ethanol --tag <tag> --judge
OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES='{"judge":{"models":["claude-sonnet-5-5"],"effort":"high"}}' pnpm eval judge --suite ethanol
OPENFERMENT_PROJECT=ethanol pnpm eval summary --suite ethanol
```

for each of the three tables above (a cloud session runs each with `OPENFERMENT_MODEL` and its
three kin unset). About 15 USD for the three tables and both judges, from stage B's costs.

---

# Alpha 2.2, stage F: the comparison asked again (8 November 2026)

Asked on 5 and 8 November 2026 for alpha 2.2's stage F (execution prompt of 2 November 2026, §4
and §6.7): the fourteen questions of the suite `ethanol` asked of the rebuilt Ethanol project on
four route tables that vary the `plan` family alone, each answer judged as it was kept. Three tables
were asked whole. The fourth, `opus-max`, asked four questions, each answer out of room at the
plan's ceiling, before the Anthropic account's own usage limit refused every call from 04:28 UTC on
8 November ("You will regain access on 2026-12-01 at 00:00 UTC"; `docs/PROGRESS.md`, Blockers).
The second judge was never asked, for the same limit. The defaults below rest on one judge.

## Method

- **The project.** Rebuilt on 5 November in this container's fresh `openferment_dev` from Home and
  `docs/corpus/ethanol-sources.txt` through Intake (stage F.1): 22 documents held, 814 passages,
  457 candidates extracted on the `extract` route and left for the owner's review, 0 records, 0
  decisions and 0 depositions, and three warm-up runs from Studies' run card on the package's own
  values (`cornstover`, and `cellulosic_ethanol_v0` in dilute acid and in hot water).
  `docs/reports/live-questions-2026-11.md` holds the rebuild in its section of 5 November. Alpha
  2.1's project is kept apart in `openferment_dev_alpha21`, so the tags here are this project's
  own.
- **The fourteen**, seeded on 5 November (`pnpm eval seed --suite ethanol`), each kept with what a
  good answer does in words (`postdoc/evaluate.py`, `ETHANOL_QUESTIONS`). Questions 4, 7, 8 and 14
  are follow-ups, asked in the conversation of the question they follow.

  | Q | Asks | A good answer |
  |---|---|---|
  | 1 | which documents report an ethanol titre, and under what conditions | names each such document with its conditions, each claim citing its passage or record |
  | 2 | which yeast strains the documents name, and which documents describe each | names the strains and their documents, each claim citing a passage or record |
  | 3 | what the library's reference cellulosic plant assumes about its feedstock, and where those values come from | gives the assumptions as typed values read back from a run, each named to the package or a document |
  | 4 | (follows 3) what drives that plant's selling price | shows the cost lines, each cited to the run's artifact, and which inputs the package sets and which a person could change |
  | 5 | a glucose-only scenario: propose it, run it, say what changed and what the change rests on | runs the scenario, compares it with the package's run, labels each estimate as the model's |
  | 6 | dilute-acid against hot-water pretreatment in the composed flowsheet on the package's defaults | runs both, compares them, flags what limits the comparison |
  | 7 | (follows 6) what is uncertain in the comparison, and what evidence would settle it | says both, with no number of its own |
  | 8 | (follows 5) a runbook for question 5's scenario | drafts it through the runbook tool, its predictions read from the run |
  | 9 | which records are verified and which candidates wait for review | says both from the module reads, documents named by title |
  | 10 | which documents were refused or partly ingested, and why | says so from Intake's state, in words |
  | 11 | import the toolkit's reference file SF_BST_15 and say what plant it describes | imports it and describes the plant from its graph, each claim cited to the record's evidence |
  | 12 | the theoretical ethanol ceiling on glucose from the shelf's genome-scale models, and the project's records beside it | gives the ceiling as geneOS artifacts and compares the records with it, or says in words that a model file is absent |
  | 13 | which engines are registered, what each takes and gives, and which of the project's runs came from each | one table from the engine reads, each run named by its id and cited |
  | 14 | (follows 5) the yield of the project's most recent deposition set as the scenario's yield, run and compared | reads the bench's readings; where the project holds no such reading, says so in words and runs nothing |

- **The four tables**, each laid by `OPENFERMENT_ROUTES` for its one command and read back
  through `llm.routes()` before the first, with `core/.env` and without it, each family as written.
  They vary `plan` alone; `explain` and `extract` stand at Opus then Sonnet at high,
  `index` at Haiku at low, and `judge` at Opus then Sonnet at max in every table:

  ```json
  {"haiku":     {"plan": {"models": ["claude-haiku-5-5"], "effort": "high"}},
   "sonnet":    {"plan": {"models": ["claude-sonnet-5-5"], "effort": "high"}},
   "opus-high": {"plan": {"models": ["claude-opus-5-5", "claude-sonnet-5-5"], "effort": "high"}},
   "opus-max":  {"plan": {"models": ["claude-opus-5-5", "claude-sonnet-5-5"], "effort": "max"}},
   "each":      {"explain": {"models": ["claude-opus-5-5", "claude-sonnet-5-5"], "effort": "high"},
                 "extract": {"models": ["claude-opus-5-5", "claude-sonnet-5-5"], "effort": "high"},
                 "index":   {"models": ["claude-haiku-5-5"], "effort": "low"},
                 "judge":   {"models": ["claude-opus-5-5", "claude-sonnet-5-5"], "effort": "max"}}}
  ```

  None of the fourteen reaches `explain`: Postdoc's loop answers on `plan`, and `explain` serves
  single calls (the kit's cited answers, Practice). Each table's cost and seconds are `plan`'s.
- **Asked** with `pnpm eval run --live --suite ethanol --tag <tag> --judge`, one table at a time,
  with the machine quiet: on 8 November the runner wrote a quiet flag the session's other work
  reads, waited for any suite started before it, and read the day's spend over every database
  before each table. The cloud session's four plain settings were unset for each command. A
  table's hours run from the runner's start to its exit, and its runs are kept from its first
  answer on: haiku 10:52 to 11:36 UTC on 5 November (its runs kept from 10:57); on 8 November
  sonnet 02:23 to 03:01 (from 02:27), opus-high 03:01 to 03:53 (from 03:07) and opus-max from
  03:53 (its four runs kept 04:00 to 04:22, eq-eth-05's at 04:28).
- **The judge.** The judge route, Opus then Sonnet at effort max, read each answer as it was kept:
  the question, what a good answer does, every claim with what it cites, the gaps and the tools
  called (`postdoc/evaluate.py`, `judge`). Its room is `JUDGE_TOKENS`, 32,000 (ADR-008,
  Implementation 15): haiku's fourteen were judged first at 16,000, where three judgements ran out
  of room (eq-eth-01, 02 and 03), and judged again at 32,000 on the same route, so all four tables
  share one judge setting and the summary reads each run's newer judgement. At 32,000 every one of
  the 46 judgements arrived whole, each given by `claude-opus-5-5` with no fallback, no decline and
  no refusal. The second judge (Sonnet alone at max over every tag's newest runs) waits on the
  account, so the summary's `judgesDisagree` is empty.
- **The scores** are alpha 2.1's: the code's `tools`, `citations`, `estimates` and `bareNumbers`,
  and the judge's `answers`, `grounded`, `labelled` and `coverage`, each from 0 to 1 (alpha 2.1's
  Method above). Every quantity below comes from `pnpm eval summary --suite ethanol --rows`
  over each tag's newest runs, from the runs and their judgements in `openferment_dev`'s
  `eval_runs`, and from its spend table.
- **opus-max's fifth.** eq-eth-05's run under `opus-max` keeps the account's refusal in words (its
  tool calls ran on Opus; the next call was refused on Opus, then on Sonnet). It is left out of
  every opus-max mean, median and count below, and its cost is named apart.

## What was measured, one row a table

opus-max's row holds its four questions, eq-eth-01 to eq-eth-04. Its judge means sit on answers that
hold no claim: each of the four ran out of room after the stop at the tool-call bound, so the judge
scored answering and coverage 0, and labelled 1 and grounded 1 (0 on eq-eth-04), each 1 given, in
the judge's own account, because nothing was asserted.

**Scores.**

| Table | Questions | Code: tools, citations, estimates, bare numbers | Judge (Opus): answers, grounded, labelled, coverage | Judged / declined / refused by the judge |
|---|---|---|---|---|
| haiku | 14 | 0.839, 0.748, 0.929, 0.643 | 0.601, 0.646, 0.938, 0.589 | 14 / 0 / 0 (the newer pass) |
| sonnet | 14 | 0.851, 0.718, 0.857, 0.643 | 0.656, 0.540, 0.882, 0.625 | 14 / 0 / 0 |
| opus-high | 14 | 0.923, 0.843, 0.929, 0.643 | 0.787, 0.662, 0.942, 0.760 | 14 / 0 / 0 |
| opus-max | 4 | 1.000, 0.000, 1.000, 1.000 | 0.000, 0.750, 1.000, 0.000 | 4 / 0 / 0 |

Every judgement was given by the judge route's first model, `claude-opus-5-5`, with no fallback
(`judgeRoutes`: 14, 14, 14 and 4 judgements, 0 fallen back, 0 declined).

**The answers' course.**

| Table | Postdoc's declines | The answering model's restarts | Claims kept / dropped | Dropped for a number in the words | Dropped claims by kind | Gaps dropped for a number | Tool calls, mean / median | Median seconds: first step, model's first step, answer | Stops |
|---|---|---|---|---|---|---|---|---|---|
| haiku | 0 | 0 | 78 / 23 | 6 | a number in the words 6, a typed value 1, a quote 3, citing nothing 13 | 8 | 12.6 / 13.5 | 0.17, 3.83, 40.3 | done 13, tool calls 1 (eq-eth-02) |
| sonnet | 1 (eq-eth-14, the refusal in words the question allows) | 0 | 56 / 14 | 6 | a number in the words 6, a typed value 1, a quote 1, citing nothing 6 | 5 | 8.1 / 6.5 | 0.15, 3.56, 25.1 | done 13, tool calls 1 (eq-eth-05) |
| opus-high | 0 | 0 | 82 / 15 | 11 | a number in the words 11, a quote 2, citing nothing 2 | 13 | 11.0 / 10 | 0.16, 4.99, 65.5 | done 13, tool calls 1 (eq-eth-02) |
| opus-max | 4 (each "Postdoc's answer did not arrive whole (it ran out of room)") | 0 | 0 / 0 | 0 | none | 0 | 24 / 24 | 0.16, 7.31, 393.9 | tool calls 4 |

No table stopped at the round bound, the question's budget or its time. The validator's reason for
a dropped gap ("a number in a gap or the decline") counts gaps; the claims dropped are the sum of
the other kinds. The opus-high table's plan route holds Sonnet behind Opus, and Opus declined none
of its fourteen plans; the haiku and sonnet tables' routes hold one model each.

**Cost**, in USD, from each run's kept cost and each judgement's; each whole table's total equals
the spend table's rows for its hours, and opus-max's spend in full follows its row.

| Table | Per question, mean / median (answers) | Answers | Judges | Table |
|---|---|---|---|---|
| haiku | 0.0199 / 0.0121 | 0.2780 | 4.6846 at 32,000 (the newer); 8.7834 for both passes (4.0988 at 16,000) | 4.9626 with the newer judges; 9.0614 with both passes |
| sonnet | 0.1784 / 0.1634 | 2.4974 | 4.4227 | 6.9201 |
| opus-high | 0.4669 / 0.4420 | 6.5359 | 5.3676 | 11.9036 |
| opus-max (4) | 1.3864 / 1.4183 | 5.5457 | 0.2421 | 5.7878 |

Beside opus-max's four: its first asking of eq-eth-05, cut off when the runner reached the
session's two-hour limit for a background command, spent 0.3909 on three calls with no run kept,
and left a hold of 0.9821 that settles nothing and expires; its second asking, refused by the
account, keeps 0.2822 for the tool calls before the refusal. The table spent 6.4608 in all (41
settled calls). Per answer, haiku cost 0.007 to 0.087, sonnet 0.12 to 0.28, opus-high 0.27 to
0.88 and opus-max 1.25 to 1.46; opus-high's answers cost 24 times haiku's and 2.6 times sonnet's at
the mean (23.5 and 2.62 from the unrounded means).

**The days**, over every database (`openferment_dev` and `openferment_dev_alpha21`): 5 November,
14.439322 USD settled over 140 calls (F.1's extraction 5.377950 over 31, the haiku table 4.376768
over 94, its second judge pass 4.684600 over 14, and F.0's probe 0.000004); 8 November, 25.284480
over 208 calls (sonnet 6.920110 over 75, opus-high 11.903559 over 92, opus-max 6.460811 over 41),
against the 150 USD cap each day.

## The judge's disagreement with itself

With one judge, the disagreement between two judges is unmeasured. The measure in hand is the
judge's disagreement with itself: Opus judged the same eleven haiku answers twice, each time whole
(eq-eth-04 to eq-eth-14, at 16,000 and at 32,000 on the same route and the same request;
eq-eth-01 to 03 ran out of room the first time and have no pair).

| Score | Mean absolute difference over the 11 pairs | Largest | Pairs that differ |
|---|---|---|---|
| answers | 0.023 | 0.05 | 5 |
| grounded | 0.041 | 0.10 | 8 |
| labelled | 0.032 | 0.15 | 5 |
| coverage | 0.045 | 0.10 | 9 |

Two judges are taken to disagree at least as much as one judge with itself, an assumption the
second judge's reading of the same answers will test, so this stands as a floor under the
disagreement the rule asks for. The floor holds the room's change with the judge's own noise (the
two passes differ in their room alone), and it rests on one table's answers.

## The rule, worked

The rule (the prompt's §6.7): keep the cheaper model in any family where it scored within the
judges' disagreement with each other. Worked on the `plan` family in cost order, `haiku`, `sonnet`,
`opus-high`; `opus-max` holds no whole answer and stays out of it. For a cheaper table A and a
dearer table B, B's Opus mean less A's on each score (from the unrounded means), beside the floor,
and the questions where B's answer scored above A's, below it and level with it:

| B less A | Score | B − A | Floor | Against the floor | B above / below / level |
|---|---|---|---|---|---|
| sonnet − haiku | answers | +0.054 | 0.023 | past it, B higher | 7 / 3 / 4 |
| | grounded | −0.106 | 0.041 | past it, B lower | 2 / 12 / 0 |
| | labelled | −0.056 | 0.032 | past it, B lower | 4 / 6 / 4 |
| | coverage | +0.036 | 0.045 | within | 7 / 3 / 4 |
| opus-high − haiku | answers | +0.186 | 0.023 | past it, B higher (8 times the floor) | 11 / 2 / 1 |
| | grounded | +0.016 | 0.041 | within | 7 / 6 / 1 |
| | labelled | +0.004 | 0.032 | within | 6 / 5 / 3 |
| | coverage | +0.171 | 0.045 | past it, B higher (4 times the floor) | 9 / 1 / 4 |
| opus-high − sonnet | answers | +0.131 | 0.023 | past it, B higher | 10 / 2 / 2 |
| | grounded | +0.122 | 0.041 | past it, B higher | 11 / 3 / 0 |
| | labelled | +0.060 | 0.032 | past it, B higher | 6 / 4 / 4 |
| | coverage | +0.135 | 0.045 | past it, B higher | 8 / 3 / 3 |

- **sonnet against haiku.** Sonnet stands above haiku past the floor on answering, and below it
  past the floor on grounding and labelling (lower on grounding in 12 of the 14). The two cross, so
  sonnet's price buys a lead on one score of the four, answering, and the opus-high pairs settle
  the family.
- **opus-high against haiku.** Opus at high stands above haiku past the floor on answering (11 of
  the 14 higher) and coverage (9 of the 14 higher); its grounding and labelling sit within the
  floor. The rule keeps haiku where it scores within the disagreement, and on answering and
  coverage it scores below by eight and four times the floor.
- **opus-high against sonnet.** Opus at high stands above sonnet past the floor on all four scores.

**What the decision rests on.** One judge, `claude-opus-5-5`, the same model as the opus tables'
plan model, so a judge's preference for its own model's answers is unmeasured until the Sonnet pass
reads the same answers. The floor marks a difference below it as within the judge's own noise.
The disagreement between two judges may be larger than the floor. The rule drops haiku while any
score stands past that disagreement, so opus-high's lead over haiku holds while the disagreement
proves smaller than 0.186 on answering or than 0.171 on coverage. The code's scores, computed from
each run's tools and claims, stand beside it and point the same way: opus-high reached more of
each question's tools (0.923 against 0.839 and 0.851) and cited more of what each question expects
(0.843 against 0.748 and 0.718), with bare numbers level (0.643 in each table, five questions of
fourteen dropping a claim for a number). Each whole table stopped once at the tool-call bound; no
answering model restarted, and Postdoc declined one question, sonnet's question 14, the refusal in
words that question allows. Opus at high costs 0.47 USD a question at the mean against Haiku's
0.02 and Sonnet's 0.18, and took a median 65 seconds to answer against 40 and 25. Effort medium,
the old default, was asked in no table, so the cost order holds no Opus setting below high to
weigh against it.

## Per question

Each tag's newest run of each question (`summary --rows`). The code's scores, then the judge's
(Opus), the tool calls, the claims, the stop, the seconds and the cost. haiku's judge column gives
the newer judgement's cost and, in brackets, both passes'. `—` marks a score the judge gave none.

**haiku**

| Q | Tools | Citations | Estimates | Bare numbers | Answers | Grounded | Labelled | Coverage | Tool calls | Claims kept / dropped (for numbers) | Stop | Seconds: first step, model, answer | USD answer | USD judge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.62 | 0.77 | 0.88 | 0.55 | 22 | 5 / 3 (0) | done | 0.22, 8.25, 170 | 0.0872 | 0.5167 (0.8747) |
| 2 | 1.00 | 0.93 | 1.00 | 0.00 | 0.80 | 0.78 | 0.90 | 0.70 | 24 | 14 / 3 (1) | calls | 0.13, 3.58, 118 | 0.0289 | 0.5183 (0.9036) |
| 3 | 1.00 | 0.43 | 1.00 | 0.00 | 0.65 | 0.85 | 0.95 | 0.60 | 14 | 7 / 1 (1) | done | 0.15, 3.99, 86 | 0.0178 | 0.4465 (0.7916) |
| 4 | 1.00 | 1.00 | 1.00 | 0.00 | 0.70 | 0.70 | 1.00 | 0.70 | 8 | 9 / 2 (1) | done | 0.13, 2.91, 42 | 0.0112 | 0.2959 (0.5102) |
| 5 | 0.00 | 0.50 | 0.00 | 1.00 | 0.15 | 0.55 | 1.00 | 0.20 | 22 | 2 / 3 (0) | done | 1.05, 4.82, 69 | 0.0184 | 0.3552 (0.5763) |
| 6 | 0.50 | 0.80 | 1.00 | 1.00 | 0.85 | 0.80 | 1.00 | 0.85 | 16 | 10 / 0 (0) | done | 0.12, 4.22, 74 | 0.0208 | 0.3073 (0.6429) |
| 7 | 1.00 | 0.90 | 1.00 | 1.00 | 0.85 | 0.85 | 1.00 | 0.90 | 20 | 10 / 0 (0) | done | 0.15, 4.06, 81 | 0.0230 | 0.3727 (0.6862) |
| 8 | 1.00 | 1.00 | 1.00 | 1.00 | 0.30 | 0.50 | 1.00 | 0.40 | 14 | 2 / 0 (0) | done | 0.19, 3.99, 38 | 0.0123 | 0.2750 (0.5425) |
| 9 | 1.00 | 0.67 | 1.00 | 1.00 | 0.70 | 0.65 | 0.90 | 0.60 | 2 | 3 / 0 (0) | done | 0.64, 4.70, 18 | 0.0074 | 0.2555 (0.5114) |
| 10 | 1.00 | 0.75 | 1.00 | 1.00 | 0.60 | 0.50 | 0.90 | 0.50 | 5 | 4 / 0 (0) | done | 0.20, 3.67, 27 | 0.0098 | 0.1845 (0.4927) |
| 11 | 1.00 | 0.67 | 1.00 | 0.00 | 0.40 | 0.40 | 0.90 | 0.45 | 2 | 3 / 1 (1) | done | 0.14, 3.11, 24 | 0.0079 | 0.3022 (0.5593) |
| 12 | 1.00 | 0.83 | 1.00 | 1.00 | 0.85 | 0.65 | 0.90 | 0.85 | 5 | 6 / 0 (0) | done | 0.20, 3.34, 36 | 0.0096 | 0.3075 (0.6144) |
| 13 | 1.00 | 1.00 | 1.00 | 0.00 | 0.15 | 0.45 | 0.90 | 0.15 | 10 | 1 / 9 (2) | done | 0.16, 2.45, 38 | 0.0119 | 0.2436 (0.4447) |
| 14 | 0.25 | 0.00 | 1.00 | 1.00 | 0.80 | 0.60 | 0.90 | 0.80 | 13 | 2 / 1 (0) | done | 0.17, 3.56, 38 | 0.0118 | 0.3037 (0.6329) |

**sonnet**

| Q | Tools | Citations | Estimates | Bare numbers | Answers | Grounded | Labelled | Coverage | Tool calls | Claims kept / dropped (for numbers) | Stop | Seconds: first step, model, answer | USD answer | USD judge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.60 | 0.70 | 0.90 | 0.55 | 7 | 4 / 4 (2) | done | 0.21, 7.01, 41 | 0.2164 | 0.4279 |
| 2 | 1.00 | 1.00 | 1.00 | 0.00 | 0.80 | 0.55 | 1.00 | 0.70 | 14 | 9 / 2 (1) | done | 0.15, 4.13, 40 | 0.2513 | 0.3171 |
| 3 | 1.00 | 0.33 | 1.00 | 1.00 | 0.60 | 0.73 | 0.95 | 0.58 | 7 | 6 / 0 (0) | done | 0.14, 3.36, 46 | 0.1691 | 0.3395 |
| 4 | 1.00 | 0.80 | 1.00 | 1.00 | 0.85 | 0.55 | 1.00 | 0.80 | 6 | 5 / 0 (0) | done | 0.14, 3.60, 31 | 0.1746 | 0.3404 |
| 5 | 0.00 | 0.67 | 0.00 | 0.00 | 0.20 | 0.75 | 0.80 | 0.30 | 24 | 3 / 1 (1) | calls | 0.14, 4.14, 63 | 0.2842 | 0.2784 |
| 6 | 1.00 | 1.00 | 1.00 | 1.00 | 0.85 | 0.78 | 1.00 | 0.87 | 6 | 4 / 0 (0) | done | 0.14, 2.99, 27 | 0.1765 | 0.4078 |
| 7 | 1.00 | 0.83 | 1.00 | 1.00 | 0.88 | 0.60 | 1.00 | 0.90 | 13 | 6 / 0 (0) | done | 0.15, 3.52, 47 | 0.2415 | 0.3767 |
| 8 | 1.00 | 0.50 | 1.00 | 1.00 | 0.30 | 0.40 | 0.85 | 0.35 | 8 | 2 / 0 (0) | done | 0.15, 5.66, 23 | 0.1576 | 0.4218 |
| 9 | 1.00 | 0.50 | 0.00 | 1.00 | 0.55 | 0.30 | 0.45 | 0.45 | 3 | 2 / 0 (0) | done | 0.15, 4.41, 10 | 0.1298 | 0.2031 |
| 10 | 1.00 | 0.75 | 1.00 | 1.00 | 0.75 | 0.40 | 1.00 | 0.70 | 4 | 4 / 0 (0) | done | 0.15, 2.55, 15 | 0.1362 | 0.2932 |
| 11 | 1.00 | 1.00 | 1.00 | 0.00 | 0.75 | 0.50 | 1.00 | 0.60 | 5 | 2 / 2 (1) | done | 0.14, 2.62, 16 | 0.1494 | 0.2167 |
| 12 | 1.00 | 1.00 | 1.00 | 1.00 | 0.85 | 0.60 | 0.85 | 0.85 | 4 | 4 / 0 (0) | done | 0.15, 4.13, 21 | 0.1323 | 0.3069 |
| 13 | 0.67 | 0.67 | 1.00 | 0.00 | 0.30 | 0.20 | 0.70 | 0.20 | 7 | 3 / 5 (1) | done | 0.18, 2.28, 20 | 0.1578 | 0.2456 |
| 14 | 0.25 | 0.00 | 1.00 | 1.00 | 0.90 | 0.50 | 0.85 | 0.90 | 5 | 2 / 0 (0) | done; declined in words | 0.16, 3.38, 12 | 0.1208 | 0.2474 |

**opus-high**

| Q | Tools | Citations | Estimates | Bare numbers | Answers | Grounded | Labelled | Coverage | Tool calls | Claims kept / dropped (for numbers) | Stop | Seconds: first step, model, answer | USD answer | USD judge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.00 | 0.75 | 1.00 | 0.00 | 0.50 | 0.55 | 0.95 | 0.45 | 23 | 4 / 5 (4) | done | 0.22, 5.16, 128 | 0.8830 | 0.4985 |
| 2 | 1.00 | 0.92 | 1.00 | 1.00 | 0.80 | 0.65 | 0.95 | 0.75 | 24 | 12 / 0 (0) | calls | 0.22, 5.49, 102 | 0.7022 | 0.5551 |
| 3 | 1.00 | 0.62 | 1.00 | 0.00 | 0.82 | 0.77 | 0.90 | 0.78 | 12 | 8 / 1 (1) | done | 0.17, 5.33, 91 | 0.4599 | 0.5439 |
| 4 | 1.00 | 0.85 | 1.00 | 1.00 | 0.90 | 0.88 | 1.00 | 0.91 | 18 | 13 / 0 (0) | done | 0.17, 5.45, 94 | 0.5780 | 0.5337 |
| 5 | 1.00 | 1.00 | 0.00 | 0.00 | 0.80 | 0.80 | 0.90 | 0.75 | 12 | 5 / 1 (1) | done | 0.13, 5.38, 78 | 0.5044 | 0.4932 |
| 6 | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 | 0.80 | 0.94 | 0.85 | 10 | 7 / 0 (0) | done | 0.18, 3.73, 75 | 0.5408 | 0.4266 |
| 7 | 1.00 | 0.83 | 1.00 | 1.00 | 0.90 | 0.55 | 1.00 | 0.90 | 18 | 6 / 0 (0) | done | 0.15, 3.95, 92 | 0.6283 | 0.4320 |
| 8 | 1.00 | 1.00 | 1.00 | 1.00 | 0.95 | 0.85 | 0.90 | 0.95 | 4 | 6 / 0 (0) | done | 0.19, 4.96, 30 | 0.3073 | 0.4150 |
| 9 | 1.00 | 0.75 | 1.00 | 1.00 | 0.85 | 0.75 | 1.00 | 0.80 | 4 | 4 / 0 (0) | done | 0.15, 4.83, 25 | 0.3137 | 0.2191 |
| 10 | 1.00 | 0.75 | 1.00 | 1.00 | 0.90 | 0.70 | 1.00 | 0.90 | 4 | 4 / 0 (0) | done | 0.16, 5.01, 29 | 0.2849 | 0.2082 |
| 11 | 1.00 | 1.00 | 1.00 | 0.00 | 0.80 | 0.25 | 1.00 | 0.70 | 1 | 4 / 1 (1) | done | 0.15, 3.65, 29 | 0.2659 | 0.2496 |
| 12 | 1.00 | 0.83 | 1.00 | 1.00 | 0.87 | 0.72 | 0.95 | 0.85 | 6 | 6 / 1 (0) | done | 0.16, 11.14, 56 | 0.3500 | 0.3120 |
| 13 | 0.67 | 1.00 | 1.00 | 0.00 | 0.10 | 0.30 | 0.90 | 0.15 | 10 | 1 / 6 (4) | done | 0.18, 4.00, 48 | 0.4242 | 0.1786 |
| 14 | 0.25 | 0.50 | 1.00 | 1.00 | 0.90 | 0.70 | 0.80 | 0.90 | 8 | 2 / 0 (0) | done | 0.15, 4.76, 28 | 0.2933 | 0.3020 |

**opus-max** (eq-eth-05 kept with the account's refusal, left out of every mean above)

| Q | Tools | Citations | Estimates | Bare numbers | Answers | Grounded | Labelled | Coverage | Tool calls | Claims kept / dropped (for numbers) | Stop | Seconds: first step, model, answer | USD answer | USD judge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 24 | 0 / 0 (0) | calls; out of room | 0.22, 7.05, 370 | 1.4055 | 0.0668 |
| 2 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 24 | 0 / 0 (0) | calls; out of room | 0.15, 9.47, 361 | 1.2504 | 0.0587 |
| 3 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 24 | 0 / 0 (0) | calls; out of room | 0.18, 7.17, 438 | 1.4588 | 0.0698 |
| 4 | 1.00 | 0.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 0.00 | 24 | 0 / 0 (0) | calls; out of room | 0.12, 7.44, 417 | 1.4310 | 0.0468 |
| 5 | refused by the account's limit, left out of every mean | | | | | | | | 14 | 0 / 0 (0) | done; refused by the account | 0.60, 7.29, 103 | 0.2822 | none |

## The judge's words, cut short

Paraphrased to what the judge found about each answer; the judge's notes name documents, strains and
values from the project's papers and the plants' results, which this report leaves out.

- haiku, Q1: named documents reporting a titre with their conditions, several cleanly; one claim
  widened what its record says and gave a single value for a reported range without saying so, and
  the validator's drops left documents the gaps mention unnamed.
- haiku, Q4: the cost lines, each cited to the run's artifact, carry their units and sum to the
  solved price; one claim named the wrong line as the largest, and the split between the inputs the
  package sets and those a person could change was the weaker half.
- haiku, Q5: proposed no valued scenario and ran nothing; it offered one well-grounded value from a
  shelf model and an uncited claim of absence that overreaches.
- haiku, Q13: one claim survived the validator, and it adds a state and settings its evidence does
  not show.
- sonnet, Q2: a well-organised map of strains to documents, six of its nine claims reaching past what
  their citations hold.
- sonnet, Q5: an honest non-answer: no scenario was run or compared, so it never says what changed.
- sonnet, Q8: drafted a runbook through the tool, its predictions taken from a shelf model's ceiling
  on the uncited ground that the scenario had no run.
- sonnet, Q9: the claim that no record is verified cites nothing, and a count of candidates is
  labelled both a module read and the model's estimate.
- opus-high, Q4: thorough and consistently sourced: the reference run's lines sum to the solved
  price, and every package-set price and finance term is cited with its label.
- opus-high, Q6: a thorough, internally consistent comparison of the two pretreatments on the
  package's defaults, checked against a second configuration.
- opus-high, Q11: imported the file, and every value it states matches its evidence; most of its
  description of the plant cites nothing.
- opus-high, Q13: one claim survived validation; its solved prices are borne out, and its other
  assertions are uncited.
- opus-high, Q14: took the good answer's fallback: its reads found no deposition holding an ethanol
  yield, so it said so in words and ran nothing.
- opus-max, Q1 to Q4: no answer arrived; the judge found nothing named, no claim and no gap, and said
  its scores of 1 (labelled on all four, grounded on Q1 to Q3; Q4's grounded is 0) rest on nothing
  being asserted.

**Question 14.** The project holds no deposition, so the expected answer is a refusal in words that
runs nothing (the good answer's last sentence). The question's tool groups are four (`runbooks_read`,
`study_scenario`, `engine_run`, `study_compare`), and the code's `tools` score is the share reached,
so an answer that reads the bench and stops scores 0.25 there and 0 or 0.5 on citations. So the
code's scores read question 14 short in every table. The judge read what a good answer does and
gave the three whole tables' answers 0.80 to 0.90 on answering. A deposited reading would let the
question run its four groups.

## What the account's limit left unasked

- `opus-max`, eq-eth-05 to eq-eth-14: eq-eth-05's run keeps the refusal; eq-eth-06, 07, 08, 09,
  10, 11, 12, 13 and 14 were never asked. So the effort-max plan route has no whole answer, and its
  four answers ran at the plan's ceiling of 32,000 tokens, which ADR-008's Implementation 16 has
  since raised to 128,000 at max.
- The measure of that larger room: eq-eth-01 to eq-eth-04 asked again on the opus-max table under a
  tag of their own.
- The second judge: Sonnet alone at effort max over every tag's newest runs (`pnpm eval judge`), and
  with it `judgesDisagree`, the measure the rule names.
- Beyond the comparison (Blockers): the fourteen on the Postdoc screen on the final routes (F.3),
  `pnpm prove --live` (F.4) and the retrieval lanes that call a model (F.5).

## Decision

The defaults in `core/openferment_core/llm.py`'s `ROUTES` (ADR-008, Implementation 17):

| Family | Models, in order | Effort | Rests on |
|---|---|---|---|
| `plan` | `claude-opus-5-5`, then `claude-sonnet-5-5` | high | this comparison: opus-high above haiku past the floor on answering and coverage, above sonnet past it on every judge score, and first on the code's tools and citations. Sonnet stands behind Opus for a refusal (stage B's lesson); Opus declined none of the fourteen plans here |
| `explain` | `claude-opus-5-5`, then `claude-sonnet-5-5` | high | held at extract's route until the retrieval report's answer lane measures it; none of the fourteen reaches it |
| `extract` | `claude-opus-5-5`, then `claude-sonnet-5-5` | high | F.1's extraction of the 22 documents: Opus declined nine in `bio`, and Sonnet answered each |
| `index` | `claude-haiku-5-5` | low | F.0's probe, its one call on Haiku at low; every table held `index` there, and none of the fourteen's calls reached it. Haiku alone, so a graph build's batch costs Haiku's price |
| `judge` | `claude-opus-5-5`, then `claude-sonnet-5-5` | max | the comparison's method, its room `JUDGE_TOKENS` 32,000 (Implementation 15), at which all 46 judgements arrived whole |

`routes()` now starts from these defaults and lays each plain setting of `core/.env` over the
families it covers when the environment sets it, an unset one leaving each default as it stands:
the answering chain and `OPENFERMENT_EFFORT` over `plan`, `explain` and `extract`, the index model
over index's first model. `judge` and index's effort keep their defaults under every plain setting,
so a setting chosen for answers leaves the grader as the comparison's method set it;
`OPENFERMENT_ROUTES`, laid last, moves them. The live-host runbook's four settings (Opus, Sonnet,
Haiku, high) leave every family at its default. This container's `core/.env` set
`OPENFERMENT_EFFORT=max` and laid the prompt's §4 table through `OPENFERMENT_ROUTES` (`plan` at
max), so the F.3 asking on the final routes needs its five routing lines commented out, the
defaults then standing. The Postdoc screen's "answers on" names the plan route's models, and
`pnpm ready`'s model row names its models and effort.

Effort max on the plan route stays unmeasured: four answers, each out of room at 32,000. Effort
medium, the old default, was asked in no table. The Sonnet pass and the opus-max table's fourteen
at the larger room may move `plan`; a default the second judge reverses returns here with its
numbers.

## To finish it

Once the account answers again (2026-12-01 at 00:00 UTC, or the owner raising the limit in the
Anthropic console), in this order, from the repository's root. In a cloud session prefix each with
`env -u OPENFERMENT_MODEL -u OPENFERMENT_FALLBACK_MODEL -u OPENFERMENT_INDEX_MODEL -u
OPENFERMENT_EFFORT`. `OPENFERMENT_MAX` below stands for the opus-max table as one line of JSON:

```
OPENFERMENT_MAX='{"plan":{"models":["claude-opus-5-5","claude-sonnet-5-5"],"effort":"max"},"explain":{"models":["claude-opus-5-5","claude-sonnet-5-5"],"effort":"high"},"extract":{"models":["claude-opus-5-5","claude-sonnet-5-5"],"effort":"high"},"index":{"models":["claude-haiku-5-5"],"effort":"low"},"judge":{"models":["claude-opus-5-5","claude-sonnet-5-5"],"effort":"max"}}'
```

1. `pnpm ready --probe`: one call on the `index` route (Haiku at low); its row green says the
   account answers.
2. The larger room's measure, on the opus-max table (plan Opus then Sonnet at max, its room now
   128,000; judge Opus then Sonnet at max) under a tag of its own: `OPENFERMENT_PROJECT=ethanol
   OPENFERMENT_ROUTES="$OPENFERMENT_MAX" pnpm eval run --live --suite ethanol --tag opus-max-room
   --judge --only eq-eth-01,eq-eth-02,eq-eth-03,eq-eth-04`. Each answer arriving whole closes
   Implementation 16's revisit; an answer that still runs out returns there with its measure, and
   step 3 waits on it.
3. The table's rest, on the same table and tag: `OPENFERMENT_PROJECT=ethanol
   OPENFERMENT_ROUTES="$OPENFERMENT_MAX" pnpm eval run --live --suite ethanol --tag opus-max-room
   --judge --only
   eq-eth-05,eq-eth-06,eq-eth-07,eq-eth-08,eq-eth-09,eq-eth-10,eq-eth-11,eq-eth-12,eq-eth-13,eq-eth-14`.
   With step 2 it gives the table's fourteen at the larger room under one tag, one summary row at
   one room setting. The tag `opus-max` keeps its four answers at 32,000 and eq-eth-05's refusal,
   the record of the old room.
4. The Sonnet pass, the second judge over every tag's newest runs (judge Sonnet alone at max):
   `OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES='{"judge":{"models":["claude-sonnet-5-5"],"effort":"max"}}'
   pnpm eval judge --suite ethanol`.
5. The summary: `OPENFERMENT_PROJECT=ethanol pnpm eval summary --suite ethanol --rows`, whose
   `judgesDisagree` then gives each score's disagreement between the two judges, pooled and per
   tag; the rule is worked again on it here, opus-max-room among the tables.

On 8 November's costs, opus-max's answers cost 1.25 to 1.46 USD each at 32,000 and an Opus
judgement 0.05 to 0.56; the larger room's answers are unmeasured, and the hold each plan call places
on the day's cap carries its whole room.
