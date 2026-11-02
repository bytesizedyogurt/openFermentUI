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

The judge's own words, cut short:

- haiku, Q3: "reads moisture, glucan share, flow and price back from a run, labels each as the
  package's own value, and checks the moisture and glucan values against the design report, with
  honest gaps. It overstates the mo[isture]…"
- haiku, Q4: "The cost lines, selling prices and package-set input prices are well cited and add
  up correctly… The part on which inputs a person could change…" is the weaker half.
- sonnet, Q1: "names three documents with record-backed titres, but conditions are given only
  thinly…"
- sonnet, Q2: "broad… the core CEN.PK claims are well cited. Several claims add strain names or
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

Once the account answers again (the date it names, or the owner raising the limit):

```
cd core
OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES='<the table>' pnpm eval run --live --suite ethanol --tag <tag> --judge
OPENFERMENT_PROJECT=ethanol OPENFERMENT_ROUTES='{"judge":{"models":["claude-sonnet-5-5"],"effort":"high"}}' pnpm eval judge --suite ethanol
OPENFERMENT_PROJECT=ethanol pnpm eval summary --suite ethanol
```

for each of the three tables above (a cloud session runs each with `OPENFERMENT_MODEL` and its
three kin unset). About 15 USD for the three tables and both judges, from stage B's costs.
